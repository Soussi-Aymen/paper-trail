from papertrail.models import Paper, VerificationResult
from papertrail.schemas import CheckOut, PaperBrief, PaperOut, ReferenceOut
from papertrail.verify import badge_for


def _pdf_url(paper: Paper) -> str | None:
    raw = paper.raw_source or {}
    if isinstance(raw, dict) and raw.get("pdf_url"):
        return str(raw["pdf_url"])
    for url in paper.source_urls or []:
        if str(url).lower().split("?", 1)[0].endswith(".pdf"):
            return str(url)
    return None


def _references(paper: Paper, by_openalex: dict[str, Paper]) -> list[ReferenceOut]:
    raw = paper.raw_source or {}
    stored = raw.get("referenced_works") if isinstance(raw, dict) else None
    if not isinstance(stored, list):
        return []
    found: list[ReferenceOut] = []
    for item in stored:
        openalex_id = str(item).rstrip("/").split("/")[-1]
        if not openalex_id:
            continue
        known = by_openalex.get(openalex_id)
        if known is not None and known.id != paper.id:
            url = f"https://doi.org/{known.doi}" if known.doi else f"https://openalex.org/{openalex_id}"
            found.append(ReferenceOut(title=known.title, url=url, in_project=True))
        else:
            found.append(ReferenceOut(title=None, url=f"https://openalex.org/{openalex_id}", in_project=False))
    found.sort(key=lambda item: (not item.in_project, item.title or item.url))
    return found


def to_paper_out(
    paper: Paper,
    checks: list[VerificationResult],
    seed_titles: dict[str, str],
    papers: list[Paper],
) -> PaperOut:
    payloads = [{"check_name": item.check_name, "outcome": item.outcome, "evidence": item.evidence} for item in checks]
    connected: list[str] = []
    for path in paper.discovery_paths or []:
        if not isinstance(path, dict):
            continue
        seed_id = str(path.get("seed_id") or "")
        title = seed_titles.get(seed_id)
        if title and title not in connected:
            connected.append(title)
    return PaperOut(
        id=paper.id,
        title=paper.title,
        authors=paper.authors or [],
        year=paper.year,
        venue=paper.venue,
        citation_count=paper.citation_count,
        doi=paper.doi,
        openalex_id=paper.openalex_id,
        source_urls=list(paper.source_urls or []),
        pdf_url=_pdf_url(paper),
        status=paper.status,
        rank_score=paper.rank_score,
        score_breakdown=paper.score_breakdown,
        badge=badge_for(payloads),
        checks=[CheckOut(**item) for item in payloads],
        explanation=paper.explanation,
        explanation_grounded=paper.explanation_grounded,
        connected_seeds=connected,
        references=_references(paper, {item.openalex_id: item for item in papers if item.openalex_id}),
        discovery_paths=list(paper.discovery_paths or []),
    )


def to_paper_brief(paper: Paper, checks: list[VerificationResult]) -> PaperBrief:
    names = [str(author["name"]) for author in paper.authors or [] if isinstance(author, dict) and author.get("name")]
    payloads = [{"outcome": item.outcome} for item in checks]
    url = f"https://doi.org/{paper.doi}" if paper.doi else None
    if url is None:
        for item in paper.source_urls or []:
            url = str(item)
            break
    return PaperBrief(
        id=paper.id,
        title=paper.title,
        authors=names,
        year=paper.year,
        venue=paper.venue,
        citation_count=paper.citation_count,
        doi=paper.doi,
        url=url,
        rank_score=paper.rank_score,
        badge=badge_for(payloads) if payloads else None,
    )
