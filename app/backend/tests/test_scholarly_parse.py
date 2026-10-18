from papertrail.scholarly import _with_openalex_key, crossref_item, openalex_work, short_id


def test_short_id_uses_the_last_path_segment():
    assert short_id("https://openalex.org/W1") == "W1"
    assert short_id("") == ""
    assert short_id(None) == ""


def test_openalex_key_is_added_only_for_openalex_urls():
    assert _with_openalex_key("https://api.openalex.org/works", "secret") == (
        "https://api.openalex.org/works?api_key=secret"
    )
    assert _with_openalex_key("https://api.crossref.org/works", "secret") == "https://api.crossref.org/works"
    assert _with_openalex_key("https://api.openalex.org/works?per_page=1", "") == (
        "https://api.openalex.org/works?per_page=1"
    )


def test_openalex_work_keeps_a_pdf_and_orders_the_abstract():
    work = openalex_work(
        {
            "id": "https://openalex.org/W9",
            "doi": "https://doi.org/10.1000/abc.",
            "title": "A trial",
            "publication_year": 2020,
            "cited_by_count": 4,
            "is_retracted": False,
            "authorships": [{"author": {"display_name": "Ada Lovelace", "id": "https://openalex.org/A1", "orcid": ""}}],
            "primary_location": {
                "source": {"display_name": "Journal", "type": "journal"},
                "landing_page_url": "https://journal.test/a",
                "pdf_url": "https://journal.test/a.pdf",
            },
            "abstract_inverted_index": {"trial": [1], "A": [0]},
            "referenced_works": ["https://openalex.org/W2"],
        }
    )
    assert work.doi == "10.1000/abc"
    assert work.abstract == "A trial"
    assert work.authors[0]["name"] == "Ada Lovelace"
    assert work.source_urls[0] == "https://journal.test/a.pdf"
    assert work.referenced_works == ["W2"]
    assert work.raw["pdf_url"] == "https://journal.test/a.pdf"


def test_openalex_work_ignores_a_landing_page_that_is_not_a_pdf():
    work = openalex_work(
        {
            "title": "",
            "open_access": {"oa_url": "https://journal.test/landing"},
            "best_oa_location": {"pdf_url": "https://journal.test/file?download=1"},
        }
    )
    assert work.title == ""
    assert work.raw["pdf_url"] is None
    assert work.citation_count == 0


def test_crossref_item_reads_authors_year_and_retraction():
    work = crossref_item(
        {
            "title": ["A trial"],
            "DOI": "10.1000/abc",
            "author": [{"given": "Ada", "family": "Lovelace", "ORCID": "https://orcid.org/0000"}],
            "issued": {"date-parts": [[2020, 5]]},
            "container-title": ["Journal"],
            "is-referenced-by-count": 3,
            "URL": "https://doi.org/10.1000/abc",
            "update-to": [{"type": "retraction"}],
        }
    )
    assert work is not None
    assert work.authors[0]["name"] == "Ada Lovelace"
    assert work.year == 2020
    assert work.venue == "Journal"
    assert work.is_retracted is True


def test_crossref_item_returns_none_without_a_title():
    assert crossref_item({"DOI": "10.1000/abc"}) is None
    assert crossref_item({"title": [], "issued": {}}) is None
