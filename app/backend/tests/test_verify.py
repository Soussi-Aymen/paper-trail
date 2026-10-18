from papertrail.models import Paper
from papertrail.scholarly import Work
from papertrail.verify import badge_for, run_checks


class Catalog:
    def __init__(self, crossref=None, profile=None, authors=None):
        self._crossref = crossref
        self._profile = profile
        self._authors = [] if authors is None else authors

    def crossref(self, _doi):
        return self._crossref

    def author_profile(self, _url):
        return self._profile

    def citing_authors(self, _openalex_id):
        return self._authors


class ModelMustNotRun:
    def chat_json(self, *_args, **_kwargs):
        raise AssertionError("tests must not call a model")


def _paper(**kwargs) -> Paper:
    values = {
        "id": "p",
        "project_id": "j",
        "title": "Vaccine trial",
        "authors": [],
        "citation_count": 0,
        "source_urls": [],
        "is_retracted": False,
    }
    values.update(kwargs)
    return Paper(**values)


def _crossref(**kwargs) -> Work:
    values = {
        "openalex_id": None,
        "doi": "10.1000/abc",
        "title": "Vaccine trial",
        "abstract": "",
        "authors": [],
        "year": 2020,
        "venue": "Journal",
        "citation_count": 1,
        "source_urls": [],
        "is_retracted": False,
        "referenced_works": [],
    }
    values.update(kwargs)
    return Work(**values)


def _outcome(paper: Paper, catalog: Catalog, name: str) -> str:
    checks = run_checks(paper, catalog, None)  # type: ignore[arg-type]
    return next(item["outcome"] for item in checks if item["check_name"] == name)


def test_badge_is_green_only_when_every_check_passed():
    assert badge_for([{"outcome": "pass"}, {"outcome": "pass"}]) == "green"


def test_badge_is_red_when_any_check_failed():
    assert badge_for([{"outcome": "pass"}, {"outcome": "fail"}, {"outcome": "warn"}]) == "red"


def test_badge_is_yellow_for_a_warning_an_unknown_or_no_checks():
    assert badge_for([{"outcome": "warn"}]) == "yellow"
    assert badge_for([{"outcome": "unknown"}]) == "yellow"
    assert badge_for([]) == "yellow"


def test_missing_doi_is_unknown_and_does_not_fail():
    paper = _paper(doi=None)
    assert _outcome(paper, Catalog(), "doi_cross_source") == "unknown"


def test_unresolved_doi_fails_without_an_openalex_id_and_warns_with_one():
    missing = _paper(doi="10.1000/missing")
    listed = _paper(doi="10.1000/missing", openalex_id="W1")
    assert _outcome(missing, Catalog(crossref=None), "doi_cross_source") == "fail"
    assert _outcome(listed, Catalog(crossref=None), "doi_cross_source") == "warn"


def test_matching_crossref_title_passes_even_when_both_years_are_absent():
    paper = _paper(doi="10.1000/abc", year=None)
    catalog = Catalog(crossref=_crossref(year=None))
    assert _outcome(paper, catalog, "doi_cross_source") == "pass"


def test_crossref_title_mismatch_fails_and_year_mismatch_warns():
    paper = _paper(doi="10.1000/abc", year=2020)
    mismatch = Catalog(crossref=_crossref(title="A different paper"))
    year = Catalog(crossref=_crossref(year=1999))
    assert _outcome(paper, mismatch, "doi_cross_source") == "fail"
    assert _outcome(paper, year, "doi_cross_source") == "warn"


def test_retraction_fails_from_openalex_or_crossref_and_passes_otherwise():
    flagged = _paper(is_retracted=True, openalex_id="W1")
    cross = _paper(doi="10.1000/abc", is_retracted=False)
    clear = _paper(doi="10.1000/abc")
    assert _outcome(flagged, Catalog(), "retraction") == "fail"
    assert _outcome(cross, Catalog(crossref=_crossref(is_retracted=True)), "retraction") == "fail"
    assert _outcome(clear, Catalog(crossref=_crossref()), "retraction") == "pass"


def test_authors_pass_on_orcid_or_a_profile_and_warn_without_either():
    orcid = _paper(authors=[{"name": "Ada", "orcid": "https://orcid.org/0000-0001-0000-0000"}])
    profile = _paper(authors=[{"name": "Ada", "orcid": "", "openalex_id": "A1"}])
    bare = _paper(authors=[{"name": "Ada", "orcid": "", "openalex_id": "A1"}])
    assert _outcome(orcid, Catalog(), "authors") == "pass"
    assert _outcome(profile, Catalog(profile={"works_count": 2}), "authors") == "pass"
    assert _outcome(bare, Catalog(profile={"works_count": 0}), "authors") == "warn"


def test_authors_are_unknown_when_the_list_is_empty():
    assert _outcome(_paper(authors=[]), Catalog(), "authors") == "unknown"


def test_venue_passes_for_doaj_or_a_typed_source_and_is_unknown_otherwise():
    doaj = _paper(raw_source={"source": {"display_name": "Journal", "is_in_doaj": True}})
    typed = _paper(venue="Journal", raw_source={"source": {"type": "journal"}})
    name_only = _paper(venue="Journal", raw_source={})
    assert _outcome(doaj, Catalog(), "venue") == "pass"
    assert _outcome(typed, Catalog(), "venue") == "pass"
    assert _outcome(name_only, Catalog(), "venue") == "unknown"
    assert _outcome(_paper(), Catalog(), "venue") == "unknown"


def test_citation_context_covers_none_one_and_many_author_groups():
    quiet = _paper(citation_count=0, openalex_id="W1")
    unlinked = _paper(citation_count=4, openalex_id=None)
    one = _paper(citation_count=4, openalex_id="W1")
    many = _paper(citation_count=4, openalex_id="W1")
    assert _outcome(quiet, Catalog(), "citation_context") == "warn"
    assert _outcome(unlinked, Catalog(), "citation_context") == "unknown"
    assert _outcome(one, Catalog(authors=["A", "A"]), "citation_context") == "warn"
    assert _outcome(many, Catalog(authors=["A", "B"]), "citation_context") == "pass"
    assert _outcome(one, Catalog(authors=[]), "citation_context") == "unknown"


def test_paper_mill_check_does_not_call_a_model():
    without_model = _paper(abstract="A specific methods abstract.")
    without_abstract = _paper(abstract=None)
    checks = run_checks(without_model, Catalog(), None)  # type: ignore[arg-type]
    mill = next(item for item in checks if item["check_name"] == "paper_mill_style")
    assert mill["outcome"] == "unknown"
    checks = run_checks(without_abstract, Catalog(), ModelMustNotRun())  # type: ignore[arg-type]
    mill = next(item for item in checks if item["check_name"] == "paper_mill_style")
    assert mill["outcome"] == "unknown"
