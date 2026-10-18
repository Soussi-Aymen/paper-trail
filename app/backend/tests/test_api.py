from datetime import datetime

from papertrail.llm import TokenFactoryError
from papertrail.models import AgentEvent, Paper, Project, VerificationResult
from papertrail.scholarly import Work


def _project(client, name="Vaccine", question="Does it work?"):
    response = client.post("/projects", json={"name": name, "research_question": question})
    assert response.status_code == 201
    return response.json()


def _work(doi="10.1000/yes", title="Yes paper") -> Work:
    return Work(
        openalex_id="Wyes",
        doi=doi,
        title=title,
        abstract="An abstract.",
        authors=[{"name": "Ada Lovelace", "orcid": "", "openalex_id": "A1"}],
        year=2020,
        venue="Journal",
        citation_count=4,
        source_urls=[f"https://doi.org/{doi}"],
        is_retracted=False,
        referenced_works=[],
        raw={},
    )


def _refuse(_settings):
    raise TokenFactoryError("tests do not call a model")


def _save(db, project: Project, *rows) -> None:
    db.add(project)
    db.commit()
    for row in rows:
        db.add(row)
        db.commit()


def test_health_and_root(client):
    assert client.get("/").json()["status"] == "ok"
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"]["ok"] is True


def test_create_project_returns_the_location_and_zero_counts(client):
    response = client.post("/projects", json={"name": "Vaccine", "research_question": "Does it work?"})
    body = response.json()
    assert response.status_code == 201
    assert response.headers["location"] == f"/projects/{body['id']}"
    assert body["status"] == "draft"
    assert body["seed_count"] == 0
    assert body["found_count"] == 0
    listed = client.get("/projects").json()
    assert listed[0]["id"] == body["id"]


def test_create_project_rejects_an_empty_name_and_a_missing_question(client):
    assert client.post("/projects", json={"name": "", "research_question": "Q"}).status_code == 422
    assert client.post("/projects", json={"name": "N"}).status_code == 422
    assert client.post("/projects", json={}).status_code == 422


def test_create_project_accepts_the_maximum_name_and_rejects_one_past_it(client):
    assert _project(client, name="n" * 300)["name"] == "n" * 300
    assert client.post("/projects", json={"name": "n" * 301, "research_question": "Q"}).status_code == 422


def test_create_project_keeps_a_one_character_question_and_strips_a_blank_name(client):
    assert _project(client, question="Q")["research_question"] == "Q"
    blank = client.post("/projects", json={"name": "   ", "research_question": "Q"})
    assert blank.status_code == 201
    assert blank.json()["name"] == ""


def test_missing_project_is_a_not_found_problem(client):
    response = client.get("/projects/missing")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "No project has that id."
    assert client.get("/projects/missing/library").status_code == 404
    assert client.get("/projects/missing/results").status_code == 404
    assert client.get("/projects/missing/events").status_code == 404
    assert client.post("/projects/missing/analyze").status_code == 404
    assert client.post("/projects/missing/seeds", json={"dois": ["10.1000/x"]}).status_code == 404
    assert client.post("/projects/missing/evaluate").status_code == 404


def test_library_splits_seeds_the_short_list_and_the_rest(client, db):
    low = _row("low", "p", "Low paper", "candidate", 0.1, doi=None, source_urls=["https://openalex.org/Wlow"])
    _save(
        db,
        Project(id="p", name="Vaccine", research_question="Q", status="done"),
        _row("seed", "p", "Seed paper", "seed", None),
        _row("a", "p", "Alpha", "verified", 0.9),
        _row("b", "p", "Beta", "verified", 0.8),
        _row("c", "p", "Gamma", "candidate", 0.2),
        low,
        VerificationResult(
            id="check",
            paper_id="low",
            check_name="retraction",
            outcome="fail",
            evidence={"fact": "retracted"},
        ),
    )
    library = client.get("/projects/p/library")
    assert library.status_code == 200
    body = library.json()
    assert [item["title"] for item in body["seeds"]] == ["Seed paper"]
    assert [item["title"] for item in body["results"]] == ["Alpha", "Beta", "Gamma"]
    assert [item["title"] for item in body["found"]] == ["Low paper"]
    assert body["found"][0]["badge"] == "red"
    assert body["found"][0]["url"] == "https://openalex.org/Wlow"
    results = client.get("/projects/p/results").json()
    assert [item["id"] for item in results] == ["a", "b", "c"]
    listed = client.get("/projects").json()[0]
    assert listed["seed_count"] == 1
    assert listed["found_count"] == 4


def test_library_is_empty_when_the_project_has_no_papers(client):
    created = _project(client)
    library = client.get(f"/projects/{created['id']}/library").json()
    assert library == {"seeds": [], "results": [], "found": []}


def test_equal_scores_sort_by_title_and_a_missing_score_sorts_last(client, db):
    _save(
        db,
        Project(id="p", name="N", research_question="Q", status="done"),
        _row("b", "p", "Bravo", "candidate", 0.5),
        _row("a", "p", "Alpha", "candidate", 0.5),
        _row("z", "p", "Zulu", "candidate", None),
    )
    titles = [item["title"] for item in client.get("/projects/p/library").json()["results"]]
    assert titles == ["Alpha", "Bravo", "Zulu"]


def test_events_are_oldest_first_and_empty_when_none_exist(client, db):
    created = _project(client)
    assert client.get(f"/projects/{created['id']}/events").json() == []
    _save(
        db,
        Project(id="p", name="N", research_question="Q", status="done"),
        _event("e2", "p", "finish"),
        _event("e1", "p", "seeds"),
    )
    steps = [item["step"] for item in client.get("/projects/p/events").json()]
    assert steps == ["seeds", "finish"]


def test_empty_seeds_are_rejected(client):
    created = _project(client)
    response = client.post(f"/projects/{created['id']}/seeds", json={"dois": [], "titles": [], "bibtex": "  "})
    assert response.status_code == 422
    assert response.json()["detail"] == "Provide a DOI, a title, or BibTeX."


def test_resolve_seed_unresolved_title_and_bibtex_without_a_catalog_call(client, monkeypatch):
    created = _project(client)
    seen: list[str] = []

    def by_doi(_self, doi: str):
        seen.append(doi)
        if doi == "10.1000/yes":
            return _work()
        return None

    def by_title(_self, title: str):
        seen.append(title)
        return None

    monkeypatch.setattr("papertrail.scholarly.Scholarly.by_doi", by_doi)
    monkeypatch.setattr("papertrail.scholarly.Scholarly.by_title", by_title)
    bibtex = "@article{a, doi = {10.1000/missing}, title = {Missing paper}}"
    response = client.post(
        f"/projects/{created['id']}/seeds",
        json={"dois": ["10.1000/yes"], "titles": ["Unknown title"], "bibtex": bibtex},
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["resolved"]] == ["Yes paper"]
    assert body["unresolved"] == ["Unknown title", "10.1000/missing"]
    assert "10.1000/yes" in seen
    library = client.get(f"/projects/{created['id']}/library").json()
    assert library["seeds"][0]["title"] == "Yes paper"


def test_blank_seed_line_is_ignored_and_a_repeat_doi_stays_one_seed(client, monkeypatch):
    created = _project(client)
    monkeypatch.setattr("papertrail.scholarly.Scholarly.by_doi", lambda _self, doi: _work(doi=doi))
    monkeypatch.setattr("papertrail.scholarly.Scholarly.by_title", lambda _self, _title: None)
    blank = client.post(f"/projects/{created['id']}/seeds", json={"dois": ["   "], "titles": [], "bibtex": ""})
    assert blank.status_code == 200
    assert blank.json() == {"resolved": [], "unresolved": []}
    first = client.post(f"/projects/{created['id']}/seeds", json={"dois": ["10.1000/yes"]})
    second = client.post(f"/projects/{created['id']}/seeds", json={"dois": ["10.1000/yes"]})
    assert first.json()["resolved"][0]["id"] == second.json()["resolved"][0]["id"]
    listed = client.get("/projects").json()
    saved = next(item for item in listed if item["id"] == created["id"])
    assert saved["seed_count"] == 1


def test_analyze_conflicts_when_a_run_is_already_going(client, db):
    _save(db, Project(id="p", name="N", research_question="Q", status="running"))
    response = client.post("/projects/p/analyze")
    assert response.status_code == 409
    assert response.json()["detail"] == "Wait for the current run to finish."


def test_evaluate_needs_two_seeds(client, db):
    _save(
        db,
        Project(id="p", name="N", research_question="Q", status="done"),
        _row("only", "p", "Only seed", "seed", None),
    )
    response = client.post("/projects/p/evaluate")
    assert response.status_code == 422
    assert response.json()["detail"] == "Leave-one-out needs at least two seeds."


def test_feedback_accepts_or_rejects_without_calling_a_model(client, db, monkeypatch):
    monkeypatch.setattr("papertrail.llm.build_client", _refuse)
    _save(
        db,
        Project(id="p", name="N", research_question="Q", status="done"),
        _row("paper", "p", "A paper", "verified", 0.4),
    )
    accepted = client.post("/papers/paper/feedback", json={"action": "accept"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    rejected = client.post("/papers/paper/feedback", json={"action": "reject"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_feedback_rejects_an_unknown_paper_and_an_unknown_action(client):
    missing = client.post("/papers/missing/feedback", json={"action": "accept"})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No paper has that id."
    assert client.post("/papers/missing/feedback", json={"action": "maybe"}).status_code == 422


def _row(paper_id, project_id, title, status, rank, doi="10.1000/x", source_urls=None) -> Paper:
    return Paper(
        id=paper_id,
        project_id=project_id,
        title=title,
        authors=[{"name": "Ada Lovelace"}],
        year=2020,
        venue="Journal",
        citation_count=1,
        doi=doi,
        source_urls=source_urls or [],
        status=status,
        rank_score=rank,
        discovery_paths=[],
        is_retracted=False,
    )


def _event(event_id: str, project_id: str, step: str) -> AgentEvent:
    return AgentEvent(
        id=event_id,
        project_id=project_id,
        step=step,
        tool="test",
        input={},
        output_summary=step,
        created_at=datetime(2020, 1, 1 if step == "seeds" else 2),
    )
