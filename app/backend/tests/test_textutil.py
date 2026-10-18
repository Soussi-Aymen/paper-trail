from papertrail.textutil import (
    clean_doi,
    cosine,
    mean_vector,
    norm_title,
    parse_bibtex,
    reconstruct_abstract,
    titles_match,
)


def test_clean_doi_extracts_a_doi_from_a_url():
    assert clean_doi("https://doi.org/10.1000/abc.") == "10.1000/abc"


def test_clean_doi_returns_empty_when_there_is_no_doi():
    assert clean_doi("not a doi") == ""


def test_clean_doi_strips_surrounding_space():
    assert clean_doi("  10.1000/abc  ") == "10.1000/abc"


def test_titles_match_equal_and_contained_titles():
    assert titles_match("Vaccine Efficacy", "vaccine efficacy")
    assert titles_match("Vaccine efficacy", "Vaccine efficacy in adults")


def test_titles_match_rejects_blank_and_unrelated_titles():
    assert titles_match("", "Vaccine") is False
    assert titles_match("   ", "Vaccine") is False
    assert titles_match("Solar panels", "mRNA vaccine trial") is False


def test_norm_title_collapses_punctuation():
    assert norm_title("COVID-19, trial!") == "covid 19 trial"


def test_cosine_of_equal_vectors_is_one():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_of_orthogonal_vectors_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_rejects_empty_mismatched_and_zero_vectors():
    assert cosine([], [1.0]) == 0.0
    assert cosine([1.0], [1.0, 0.0]) == 0.0
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_mean_vector_averages_aligned_vectors():
    assert mean_vector([[1.0, 3.0], [3.0, 5.0]]) == [2.0, 4.0]


def test_mean_vector_drops_a_different_width_and_an_empty_list():
    assert mean_vector([[1.0, 2.0], [9.0]]) == [1.0, 2.0]
    assert mean_vector([[], [1.0, 2.0]]) == [1.0, 2.0]
    assert mean_vector([]) == []


def test_reconstruct_abstract_orders_inverted_positions():
    assert reconstruct_abstract({"b": [1], "a": [0]}) == "a b"


def test_reconstruct_abstract_is_empty_without_positions():
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""
    assert reconstruct_abstract({"a": []}) == ""


def test_parse_bibtex_reads_doi_and_title():
    raw = "@article{a,\n  doi = {10.1000/bib.},\n  title = {A Trial}\n}"
    assert parse_bibtex(raw) == [{"doi": "10.1000/bib", "title": "A Trial"}]


def test_parse_bibtex_skips_an_entry_with_neither_doi_nor_title():
    assert parse_bibtex("@article{a, year = {2020}}") == []
    assert parse_bibtex("no entry here") == []
