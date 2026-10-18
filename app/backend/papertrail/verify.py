from papertrail.llm import LanguageModel, parse_json_object
from papertrail.models import Paper
from papertrail.scholarly import Scholarly
from papertrail.textutil import titles_match


def badge_for(checks: list[dict]) -> str:
    outcomes = {item["outcome"] for item in checks}
    if "fail" in outcomes:
        return "red"
    if "warn" in outcomes or "unknown" in outcomes or not checks:
        return "yellow"
    return "green"


def run_checks(paper: Paper, scholarly: Scholarly, llm: LanguageModel | None) -> list[dict]:
    checks = [
        _doi_check(paper, scholarly),
        _retraction_check(paper, scholarly),
        _author_check(paper, scholarly),
        _venue_check(paper),
        _citation_check(paper, scholarly),
        _mill_check(paper, llm),
    ]
    return checks


def _evidence(source_url: str, fact: str, **extra: object) -> dict:
    body: dict[str, object] = {"source_url": source_url, "fact": fact}
    body.update(extra)
    return body


def _doi_check(paper: Paper, scholarly: Scholarly) -> dict:
    if not paper.doi:
        return {
            "check_name": "doi_cross_source",
            "outcome": "unknown",
            "evidence": _evidence("", "No DOI is recorded, so this is not a hard failure."),
        }
    crossref = scholarly.crossref(paper.doi)
    source_url = f"https://api.crossref.org/works/{paper.doi}"
    if crossref is None:
        if paper.openalex_id:
            return {
                "check_name": "doi_cross_source",
                "outcome": "warn",
                "evidence": _evidence(
                    source_url,
                    "DOI did not resolve in Crossref. OpenAlex still has a work id.",
                ),
            }
        return {
            "check_name": "doi_cross_source",
            "outcome": "fail",
            "evidence": _evidence(source_url, "DOI did not resolve in Crossref."),
        }
    same_title = titles_match(paper.title, crossref.title)
    same_year = paper.year is None or crossref.year is None or paper.year == crossref.year
    if same_title and same_year:
        return {
            "check_name": "doi_cross_source",
            "outcome": "pass",
            "evidence": _evidence(
                source_url,
                f"Crossref title matches and year is {crossref.year}.",
                crossref_title=crossref.title,
            ),
        }
    if not same_title:
        return {
            "check_name": "doi_cross_source",
            "outcome": "fail",
            "evidence": _evidence(
                source_url,
                "Crossref resolved the DOI but the title does not match.",
                crossref_title=crossref.title,
            ),
        }
    return {
        "check_name": "doi_cross_source",
        "outcome": "warn",
        "evidence": _evidence(source_url, "Title matches but the publication year differs."),
    }


def _retraction_check(paper: Paper, scholarly: Scholarly) -> dict:
    source_url = ""
    if paper.openalex_id:
        source_url = f"https://openalex.org/{paper.openalex_id}"
    retracted = bool(paper.is_retracted)
    fact = "OpenAlex marks this work retracted." if retracted else "OpenAlex is_retracted is false."
    if paper.doi:
        crossref = scholarly.crossref(paper.doi)
        if crossref is not None and crossref.is_retracted:
            retracted = True
            source_url = f"https://api.crossref.org/works/{paper.doi}"
            fact = "Crossref update-to marks a retraction."
    if retracted:
        return {
            "check_name": "retraction",
            "outcome": "fail",
            "evidence": _evidence(source_url, fact),
        }
    return {
        "check_name": "retraction",
        "outcome": "pass",
        "evidence": _evidence(source_url, "No retraction flag in OpenAlex or Crossref."),
    }


def _author_check(paper: Paper, scholarly: Scholarly) -> dict:
    authors = paper.authors or []
    if not authors:
        return {
            "check_name": "authors",
            "outcome": "unknown",
            "evidence": _evidence("", "No authors were returned by the source."),
        }
    for author in authors[:3]:
        if author.get("orcid"):
            return {
                "check_name": "authors",
                "outcome": "pass",
                "evidence": _evidence(
                    str(author.get("orcid")),
                    f"{author.get('name')} has an ORCID.",
                ),
            }
        author_id = author.get("openalex_id")
        if not author_id:
            continue
        profile = scholarly.author_profile(f"https://openalex.org/{author_id}")
        works_count = int((profile or {}).get("works_count") or 0)
        url = f"https://openalex.org/{author_id}"
        if works_count >= 1:
            return {
                "check_name": "authors",
                "outcome": "pass",
                "evidence": _evidence(
                    url,
                    f"{author.get('name')} has an OpenAlex profile with {works_count} works.",
                ),
            }
    return {
        "check_name": "authors",
        "outcome": "warn",
        "evidence": _evidence("", "Authors were listed without an ORCID or a usable OpenAlex profile."),
    }


def _venue_check(paper: Paper) -> dict:
    source = (paper.raw_source or {}).get("source") or {}
    name = source.get("display_name") or paper.venue or ""
    url = str((paper.raw_source or {}).get("openalex_url") or "")
    if source.get("is_in_doaj"):
        return {
            "check_name": "venue",
            "outcome": "pass",
            "evidence": _evidence(url, f"{name} is indexed in DOAJ according to OpenAlex."),
        }
    if name and source.get("type"):
        return {
            "check_name": "venue",
            "outcome": "pass",
            "evidence": _evidence(url, f"OpenAlex lists the source {name} ({source.get('type')})."),
        }
    if paper.venue:
        return {
            "check_name": "venue",
            "outcome": "unknown",
            "evidence": _evidence(url, f"Venue name is {paper.venue}, without DOAJ or source type."),
        }
    return {
        "check_name": "venue",
        "outcome": "unknown",
        "evidence": _evidence("", "No venue was returned."),
    }


def _citation_check(paper: Paper, scholarly: Scholarly) -> dict:
    if paper.citation_count <= 0:
        return {
            "check_name": "citation_context",
            "outcome": "warn",
            "evidence": _evidence("", "The work has no recorded citations."),
        }
    if not paper.openalex_id:
        return {
            "check_name": "citation_context",
            "outcome": "unknown",
            "evidence": _evidence("", "Citation count is present but there is no OpenAlex id to inspect."),
        }
    authors = scholarly.citing_authors(paper.openalex_id)
    unique = len(set(authors))
    url = f"https://openalex.org/{paper.openalex_id}"
    if unique >= 2:
        return {
            "check_name": "citation_context",
            "outcome": "pass",
            "evidence": _evidence(url, f"Cited by works from {unique} distinct author profiles."),
        }
    if unique == 1:
        return {
            "check_name": "citation_context",
            "outcome": "warn",
            "evidence": _evidence(url, "Citations found, but only one author profile in the sample."),
        }
    return {
        "check_name": "citation_context",
        "outcome": "unknown",
        "evidence": _evidence(url, "Could not read citing authors."),
    }


def _mill_check(paper: Paper, llm: LanguageModel | None) -> dict:
    if llm is None or not paper.abstract:
        return {
            "check_name": "paper_mill_style",
            "outcome": "unknown",
            "evidence": _evidence("", "No abstract or model was available. This check is never decisive."),
        }
    prompt = (
        "You screen an abstract for paper-mill style. Reply with JSON "
        '{"outcome":"pass" or "warn","fact":"one sentence"}. '
        "Use warn only for generic boilerplate, missing specifics, or tortured phrasing. "
        "Never claim the paper is fraudulent as a fact.\n\n"
        f"Title: {paper.title}\nAbstract: {paper.abstract[:2000]}"
    )
    raw = llm.chat(llm.settings.chat_model_small, prompt, max_tokens=200)
    parsed = parse_json_object(raw)
    if parsed is None:
        fact = "The style check did not return JSON. This check is never decisive."
        if raw is None:
            fact = "LLM budget was exhausted before the style check. This check is never decisive."
        return {
            "check_name": "paper_mill_style",
            "outcome": "unknown",
            "evidence": _evidence("", fact),
        }
    outcome = "warn" if parsed.get("outcome") == "warn" else "pass"
    return {
        "check_name": "paper_mill_style",
        "outcome": outcome,
        "evidence": _evidence("", str(parsed.get("fact") or "Style check completed.")),
    }
