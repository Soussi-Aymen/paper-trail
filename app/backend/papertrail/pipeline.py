from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from papertrail.config import Settings, get_settings
from papertrail.db import make_engine, prepare_database, session_factory
from papertrail.explain import explain_paper
from papertrail.llm import LanguageModel, SearchQueries, TokenFactoryError, build_client
from papertrail.models import AgentEvent, Paper, Project, VerificationResult
from papertrail.rank import question_similarity, score_paper
from papertrail.scholarly import Scholarly, Work
from papertrail.textutil import clean_doi, mean_vector, norm_title, parse_bibtex
from papertrail.verify import run_checks


def log_event(
    session: Session,
    project_id: str,
    step: str,
    tool: str,
    payload: dict,
    summary: str,
) -> None:
    session.add(
        AgentEvent(
            id=str(uuid4()),
            project_id=project_id,
            step=step,
            tool=tool,
            input=payload,
            output_summary=summary[:2000],
        )
    )
    session.commit()


def analyze_project(project_id: str) -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    prepare_database(engine)
    session = session_factory(engine)()
    scholarly: Scholarly | None = None
    try:
        project = session.get(Project, project_id)
        if project is None:
            return
        scholarly = Scholarly(settings, session)
        client = build_client(settings)
        llm = LanguageModel(settings, session, client)
        _analyze(session, settings, scholarly, llm, project)
        project.status = "done"
        session.commit()
        log_event(session, project_id, "finish", "pipeline", {}, "Analyze finished.")
    except Exception as exc:
        session.rollback()
        project = session.get(Project, project_id)
        if project is not None:
            project.status = "failed"
            session.commit()
            log_event(session, project_id, "finish", "pipeline", {}, f"Analyze failed: {exc}")
    finally:
        if scholarly is not None:
            scholarly.close()
        session.close()
        engine.dispose()


def _analyze(
    session: Session,
    settings: Settings,
    scholarly: Scholarly,
    llm: LanguageModel,
    project: Project,
) -> None:
    seeds = list(session.scalars(select(Paper).where(Paper.project_id == project.id, Paper.status == "seed")).all())
    if not seeds:
        raise TokenFactoryError("Add at least one resolved seed before Analyze.")
    iterations = 1
    log_event(
        session,
        project.id,
        "seeds",
        "openalex",
        {"seed_count": len(seeds)},
        f"Using {len(seeds)} resolved seeds.",
    )
    if iterations > settings.max_planner_iterations:
        log_event(session, project.id, "stop", "planner", {}, "Planner iteration cap reached.")
        return
    _citation_round(session, scholarly, project.id, seeds)
    iterations += 1
    queries = _queries(llm, project, seeds)
    log_event(
        session,
        project.id,
        "expand",
        "llm",
        {"queries": queries},
        f"Expanded into {len(queries)} searches.",
    )
    for query in queries:
        if iterations >= settings.max_planner_iterations:
            log_event(
                session,
                project.id,
                "stop",
                "planner",
                {},
                "Stopped search expansion because the planner iteration cap was reached.",
            )
            break
        iterations += 1
        found = scholarly.search(query)
        _save_works(
            session,
            project.id,
            found,
            [{"tool": "query_expansion", "detail": query}],
        )
        log_event(
            session,
            project.id,
            "search",
            "openalex",
            {"query": query},
            f"OpenAlex returned {len(found)} works.",
        )
    _rank(session, settings, llm, project, seeds)
    _verify_and_explain(session, scholarly, llm, project, seeds)


def _citation_round(
    session: Session,
    scholarly: Scholarly,
    project_id: str,
    seeds: list[Paper],
) -> None:
    total = 0
    for seed in seeds:
        if not seed.openalex_id:
            continue
        incoming, outgoing = scholarly.neighbors(seed.openalex_id)
        references = scholarly.by_ids((seed.raw_source or {}).get("referenced_works") or [])
        path = [{"tool": "citation", "seed_id": seed.id, "detail": "cites-or-cited-by"}]
        total += _save_works(session, project_id, incoming + outgoing + references, path)
    log_event(
        session,
        project_id,
        "citation",
        "openalex",
        {"seeds": [seed.openalex_id for seed in seeds]},
        f"Citation neighbors added or updated {total} works.",
    )


def _queries(llm: LanguageModel, project: Project, seeds: list[Paper]) -> list[str]:
    titles = "\n".join(f"- {seed.title}" for seed in seeds[:8])
    prompt = (
        'Return JSON {"queries": [..]} with 4 short scholarly search queries. '
        "Cover methods, synonyms, and an adjacent field. Do not include DOIs.\n\n"
        f"Question: {project.research_question}\nSeeds:\n{titles}"
    )
    parsed = llm.chat_json(llm.settings.chat_model_small, prompt, SearchQueries, max_tokens=300)
    queries = [item.strip() for item in (parsed.queries if parsed else []) if item.strip()]
    if not queries:
        queries = [project.research_question]
    return queries[:4]


def _rank(
    session: Session,
    settings: Settings,
    llm: LanguageModel,
    project: Project,
    seeds: list[Paper],
) -> None:
    candidates = list(
        session.scalars(select(Paper).where(Paper.project_id == project.id, Paper.status == "candidate")).all()
    )
    candidates.sort(key=lambda paper: (_link_count(paper), paper.citation_count), reverse=True)
    chosen = candidates[: settings.prefilter_limit]
    question_vector = llm.embed(project.research_question)
    seed_vectors: list[list[float]] = []
    for seed in seeds:
        vector = _vector(llm, seed)
        if vector:
            seed_vectors.append(vector)
    centroid = mean_vector(seed_vectors)
    year = datetime.now().year
    for paper in chosen:
        vector = _vector(llm, paper)
        score, breakdown = score_paper(
            seed_links=_link_count(paper),
            seed_count=max(1, len(seeds)),
            question_similarity=question_similarity(question_vector, vector),
            centroid_similarity=question_similarity(centroid, vector),
            year=paper.year,
            current_year=year,
            citation_count=paper.citation_count,
        )
        paper.rank_score = score
        paper.score_breakdown = breakdown
    session.commit()
    log_event(
        session,
        project.id,
        "rank",
        "embeddings",
        {"embedded": len(chosen), "cap": settings.max_candidates},
        f"Ranked {len(chosen)} candidates and will verify the top {settings.max_candidates}.",
    )


def _verify_and_explain(
    session: Session,
    scholarly: Scholarly,
    llm: LanguageModel,
    project: Project,
    seeds: list[Paper],
) -> None:
    candidates = list(
        session.scalars(select(Paper).where(Paper.project_id == project.id, Paper.status == "candidate")).all()
    )
    candidates.sort(key=lambda paper: paper.rank_score or 0, reverse=True)
    top = candidates[: project_cap(llm.settings)]
    extra = [paper for paper in candidates if _from_fixture(paper) and paper not in top]
    targets = top + extra
    for paper in targets:
        checks = run_checks(paper, scholarly, llm)
        _replace_checks(session, paper, checks)
        if paper.status == "candidate":
            paper.status = "verified"
        text, grounded = explain_paper(paper, seeds, llm)
        paper.explanation = text
        paper.explanation_grounded = grounded
        session.commit()
    log_event(
        session,
        project.id,
        "verify",
        "checks",
        {"count": len(targets)},
        f"Verified and explained {len(targets)} papers.",
    )


def project_cap(settings: Settings) -> int:
    return settings.max_candidates


def rerank_project(session: Session, project_id: str) -> None:
    settings = get_settings()
    papers = list(session.scalars(select(Paper).where(Paper.project_id == project_id)).all())
    project = session.get(Project, project_id)
    if project is None:
        return
    positives = [
        paper.embedding_json for paper in papers if paper.status in {"seed", "accepted"} and paper.embedding_json
    ]
    negatives = [paper.embedding_json for paper in papers if paper.status == "rejected" and paper.embedding_json]
    centroid = mean_vector([list(item) for item in positives])
    negative = mean_vector([list(item) for item in negatives])
    if centroid and negative and len(centroid) == len(negative):
        centroid = [left - 0.35 * right for left, right in zip(centroid, negative, strict=True)]
    question = []
    client = None
    try:
        client = build_client(settings)
        question = LanguageModel(settings, session, client).embed(project.research_question)
    except TokenFactoryError:
        question = []
    year = datetime.now().year
    seed_count = len([paper for paper in papers if paper.status == "seed"]) or 1
    for paper in papers:
        if paper.status in {"seed", "rejected"} or not paper.embedding_json:
            continue
        vector = list(paper.embedding_json)
        score, breakdown = score_paper(
            seed_links=_link_count(paper),
            seed_count=seed_count,
            question_similarity=question_similarity(question, vector),
            centroid_similarity=question_similarity(centroid, vector),
            year=paper.year,
            current_year=year,
            citation_count=paper.citation_count,
        )
        paper.rank_score = score
        paper.score_breakdown = breakdown
    session.commit()


def leave_one_out(session: Session, scholarly: Scholarly, project_id: str) -> list[dict]:
    seeds = list(session.scalars(select(Paper).where(Paper.project_id == project_id, Paper.status == "seed")).all())
    hits: list[dict] = []
    for hidden in seeds:
        others = [seed for seed in seeds if seed.id != hidden.id]
        ranked: dict[str, int] = {}
        for seed in others:
            if not seed.openalex_id:
                continue
            incoming, outgoing = scholarly.neighbors(seed.openalex_id)
            for work in incoming + outgoing:
                key = _identity(work)
                ranked[key] = ranked.get(key, 0) + 1
        ordered = sorted(ranked, key=lambda key: ranked[key], reverse=True)
        hidden_keys = []
        if hidden.doi:
            hidden_keys.append(f"doi:{hidden.doi.lower()}")
        if hidden.openalex_id:
            hidden_keys.append(f"oa:{hidden.openalex_id}")
        hidden_keys.append(f"title:{norm_title(hidden.title)}")
        found_at = None
        for index, key in enumerate(ordered, start=1):
            if key in hidden_keys:
                found_at = index
                break
        hits.append(
            {
                "seed_id": hidden.id,
                "title": hidden.title,
                "found": found_at is not None and found_at <= 10,
                "rank": found_at,
            }
        )
    return hits


def add_resolved_seeds(
    session: Session,
    scholarly: Scholarly,
    project_id: str,
    dois: list[str],
    titles: list[str],
    bibtex: str,
) -> tuple[list[Paper], list[str]]:
    queries: list[str] = []
    for doi in dois:
        queries.append(doi)
    for title in titles:
        queries.append(title)
    for entry in parse_bibtex(bibtex):
        queries.append(entry["doi"] or entry["title"])
    resolved: list[Paper] = []
    unresolved: list[str] = []
    for query in queries:
        text = query.strip()
        if not text:
            continue
        work = scholarly.by_doi(text) if clean_doi(text) else scholarly.by_title(text)
        if work is None or not work.title:
            unresolved.append(text)
            continue
        paper = _upsert(session, project_id, work, "seed", [])
        resolved.append(paper)
    session.commit()
    return resolved, unresolved


def add_fixture_candidate(
    session: Session,
    scholarly: Scholarly,
    project_id: str,
    doi: str,
) -> Paper | None:
    work = scholarly.by_doi(doi)
    if work is None:
        return None
    paper = _upsert(
        session,
        project_id,
        work,
        "candidate",
        [{"tool": "fixture", "detail": "demo suspect"}],
    )
    session.commit()
    return paper


def _save_works(session: Session, project_id: str, works: list[Work], paths: list[dict]) -> int:
    count = 0
    for work in works:
        if not work.title:
            continue
        if _is_seed(session, project_id, work):
            continue
        _upsert(session, project_id, work, "candidate", paths)
        count += 1
    session.commit()
    return count


def _upsert(
    session: Session,
    project_id: str,
    work: Work,
    status: str,
    paths: list[dict],
) -> Paper:
    existing = _find(session, project_id, work)
    if existing is None:
        paper = Paper(
            id=str(uuid4()),
            project_id=project_id,
            openalex_id=work.openalex_id,
            doi=work.doi,
            title=work.title,
            abstract=work.abstract or None,
            authors=work.authors,
            year=work.year,
            venue=work.venue,
            citation_count=work.citation_count,
            source_urls=work.source_urls,
            status=status,
            discovery_paths=paths,
            is_retracted=work.is_retracted,
            raw_source=work.raw,
        )
        session.add(paper)
        session.flush()
        return paper
    existing.discovery_paths = _merge_paths(existing.discovery_paths or [], paths)
    pdf_url = (work.raw or {}).get("pdf_url")
    if pdf_url:
        raw = dict(existing.raw_source or {})
        raw["pdf_url"] = pdf_url
        existing.raw_source = raw
        urls = list(existing.source_urls or [])
        if pdf_url not in urls:
            existing.source_urls = [pdf_url, *urls]
    if work.abstract and not existing.abstract:
        existing.abstract = work.abstract
    if work.is_retracted:
        existing.is_retracted = True
    if status == "seed":
        existing.status = "seed"
    return existing


def _find(session: Session, project_id: str, work: Work) -> Paper | None:
    rows = list(session.scalars(select(Paper).where(Paper.project_id == project_id)).all())
    target = _identity(work)
    for row in rows:
        if _paper_identity(row) == target:
            return row
    return None


def _is_seed(session: Session, project_id: str, work: Work) -> bool:
    found = _find(session, project_id, work)
    return found is not None and found.status == "seed"


def _identity(work: Work) -> str:
    if work.doi:
        return f"doi:{work.doi.lower()}"
    if work.openalex_id:
        return f"oa:{work.openalex_id}"
    return f"title:{norm_title(work.title)}"


def _paper_identity(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.openalex_id:
        return f"oa:{paper.openalex_id}"
    return f"title:{norm_title(paper.title)}"


def _merge_paths(existing: list, extra: list[dict]) -> list:
    merged = list(existing)
    for item in extra:
        if item not in merged:
            merged.append(item)
    return merged


def _link_count(paper: Paper) -> int:
    ids = set()
    for path in paper.discovery_paths or []:
        if isinstance(path, dict) and path.get("seed_id"):
            ids.add(str(path["seed_id"]))
    return len(ids)


def _from_fixture(paper: Paper) -> bool:
    return any(isinstance(path, dict) and path.get("tool") == "fixture" for path in paper.discovery_paths or [])


def _vector(llm: LanguageModel, paper: Paper) -> list[float]:
    if paper.embedding_json:
        return [float(item) for item in paper.embedding_json]
    text = paper.abstract or paper.title
    vector = llm.embed(text)
    if not vector:
        return []
    paper.embedding_json = vector
    if len(vector) == llm.settings.embedding_dimensions:
        paper.embedding = vector
    return vector


def _replace_checks(session: Session, paper: Paper, checks: list[dict]) -> None:
    old = list(session.scalars(select(VerificationResult).where(VerificationResult.paper_id == paper.id)).all())
    for item in old:
        session.delete(item)
    for item in checks:
        session.add(
            VerificationResult(
                id=str(uuid4()),
                paper_id=paper.id,
                check_name=item["check_name"],
                outcome=item["outcome"],
                evidence=item["evidence"],
            )
        )
    session.commit()
