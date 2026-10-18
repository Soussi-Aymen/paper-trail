from papertrail.rank import question_similarity, score_paper


def test_score_is_one_when_every_signal_is_full():
    total, breakdown = score_paper(
        seed_links=2,
        seed_count=2,
        question_similarity=1,
        centroid_similarity=1,
        year=2026,
        current_year=2026,
        citation_count=1000,
    )
    assert total == 1.0
    assert breakdown["graph_overlap"] == 1.0
    assert breakdown["recency"] == 1.0
    assert breakdown["citations"] == 1.0


def test_missing_year_and_zero_seed_count_contribute_nothing():
    total, breakdown = score_paper(
        seed_links=5,
        seed_count=0,
        question_similarity=0,
        centroid_similarity=0,
        year=None,
        current_year=2026,
        citation_count=0,
    )
    assert total == 0.0
    assert breakdown["graph_overlap"] == 0.0
    assert breakdown["recency"] == 0.0
    assert breakdown["citations"] == 0.0


def test_recency_is_zero_after_twenty_years_and_half_at_ten():
    _old, old_parts = score_paper(
        seed_links=0,
        seed_count=1,
        question_similarity=0,
        centroid_similarity=0,
        year=2000,
        current_year=2026,
        citation_count=0,
    )
    _mid, mid_parts = score_paper(
        seed_links=0,
        seed_count=1,
        question_similarity=0,
        centroid_similarity=0,
        year=2016,
        current_year=2026,
        citation_count=0,
    )
    assert old_parts["recency"] == 0.0
    assert mid_parts["recency"] == 0.5


def test_huge_citation_count_caps_at_one():
    _total, breakdown = score_paper(
        seed_links=0,
        seed_count=1,
        question_similarity=0,
        centroid_similarity=0,
        year=2026,
        current_year=2026,
        citation_count=10_000_000,
    )
    assert breakdown["citations"] == 1.0


def test_question_similarity_is_zero_for_an_empty_vector():
    assert question_similarity([], [1.0, 0.0]) == 0.0
