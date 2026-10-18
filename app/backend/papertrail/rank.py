import math

from papertrail.textutil import cosine


def score_paper(
    *,
    seed_links: int,
    seed_count: int,
    question_similarity: float,
    centroid_similarity: float,
    year: int | None,
    current_year: int,
    citation_count: int,
) -> tuple[float, dict[str, float]]:
    graph = seed_links / seed_count if seed_count else 0.0
    if year is None:
        recency = 0.0
    else:
        recency = max(0.0, 1.0 - ((current_year - year) / 20))
    citations = min(1.0, math.log1p(citation_count) / math.log1p(1000))
    breakdown = {
        "graph_overlap": round(graph, 4),
        "question_similarity": round(question_similarity, 4),
        "centroid_similarity": round(centroid_similarity, 4),
        "recency": round(recency, 4),
        "citations": round(citations, 4),
    }
    total = 0.30 * graph + 0.30 * question_similarity + 0.20 * centroid_similarity + 0.10 * recency + 0.10 * citations
    return round(total, 4), breakdown


def question_similarity(question_vector: list[float], paper_vector: list[float]) -> float:
    return cosine(question_vector, paper_vector)
