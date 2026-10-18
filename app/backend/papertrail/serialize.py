from papertrail.models import Paper, VerificationResult
from papertrail.schemas import CheckOut, PaperOut
from papertrail.verify import badge_for


def to_paper_out(paper: Paper, checks: list[VerificationResult], seed_titles: dict[str, str]) -> PaperOut:
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
        status=paper.status,
        rank_score=paper.rank_score,
        score_breakdown=paper.score_breakdown,
        badge=badge_for(payloads),
        checks=[CheckOut(**item) for item in payloads],
        explanation=paper.explanation,
        explanation_grounded=paper.explanation_grounded,
        connected_seeds=connected,
        discovery_paths=list(paper.discovery_paths or []),
    )
