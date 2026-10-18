from papertrail.models import Paper, VerificationResult
from papertrail.serialize import to_paper_brief, to_paper_out


def _paper(**kwargs) -> Paper:
    values = {
        "id": "p",
        "project_id": "j",
        "title": "A trial",
        "authors": [],
        "citation_count": 0,
        "source_urls": [],
        "status": "candidate",
        "discovery_paths": [],
        "is_retracted": False,
    }
    values.update(kwargs)
    return Paper(**values)


def _check(outcome: str) -> VerificationResult:
    return VerificationResult(id="c", paper_id="p", check_name="retraction", outcome=outcome, evidence={"fact": "x"})


def test_brief_uses_the_doi_and_keeps_named_authors():
    paper = _paper(
        doi="10.1000/abc",
        authors=[{"name": "Ada"}, {"orcid": "https://orcid.org/1"}, "skip"],
        year=2020,
        venue="Journal",
        citation_count=2,
    )
    brief = to_paper_brief(paper, [_check("fail")])
    assert brief.url == "https://doi.org/10.1000/abc"
    assert brief.authors == ["Ada"]
    assert brief.badge == "red"


def test_brief_falls_back_to_a_source_url_and_omits_a_badge_without_checks():
    with_url = to_paper_brief(_paper(source_urls=["https://openalex.org/W1"]), [])
    without = to_paper_brief(_paper(), [])
    assert with_url.url == "https://openalex.org/W1"
    assert with_url.badge is None
    assert without.url is None
    assert without.year is None


def test_paper_out_uses_a_pdf_url_and_names_a_referenced_project_paper():
    seed = _paper(id="seed", title="Seed paper", doi="10.1000/seed", openalex_id="Wseed", status="seed")
    paper = _paper(
        openalex_id="W1",
        raw_source={"pdf_url": "https://example.test/a.pdf", "referenced_works": ["Wseed", "Wother"]},
        discovery_paths=[{"seed_id": "seed"}],
        source_urls=["https://example.test/a.pdf"],
    )
    out = to_paper_out(paper, [_check("pass")], {"seed": "Seed paper"}, [seed, paper])
    assert out.pdf_url == "https://example.test/a.pdf"
    assert out.badge == "green"
    assert out.connected_seeds == ["Seed paper"]
    known = next(item for item in out.references if item.in_project)
    other = next(item for item in out.references if not item.in_project)
    assert known.title == "Seed paper"
    assert known.url == "https://doi.org/10.1000/seed"
    assert other.url == "https://openalex.org/Wother"
    assert other.title is None


def test_paper_out_finds_a_pdf_link_when_the_raw_record_has_none():
    paper = _paper(source_urls=["https://journal.test/page", "https://journal.test/a.pdf?download=1"])
    out = to_paper_out(paper, [], {}, [paper])
    assert out.pdf_url == "https://journal.test/a.pdf?download=1"
    assert out.badge == "yellow"
