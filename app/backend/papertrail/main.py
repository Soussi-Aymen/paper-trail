from collections.abc import Iterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from papertrail.config import Settings, get_settings
from papertrail.db import database_status, make_engine, prepare_database, session_factory
from papertrail.errors import problem
from papertrail.models import AgentEvent, Paper, Project, VerificationResult
from papertrail.pipeline import add_resolved_seeds, analyze_project, leave_one_out, rerank_project
from papertrail.schemas import (
    AnalyzeOut,
    EvalHit,
    EvalOut,
    EventOut,
    FeedbackIn,
    PaperOut,
    ProjectCreate,
    ProjectOut,
    SeedCreate,
    SeedResult,
)
from papertrail.scholarly import Scholarly
from papertrail.serialize import to_paper_out

_factory: sessionmaker[Session] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _factory
    settings = get_settings()
    engine = None
    try:
        engine = make_engine(settings.database_url)
        prepare_database(engine)
        _factory = session_factory(engine)
    except Exception:
        if engine is not None:
            engine.dispose()
        _factory = None
        engine = None
    app.state.engine = engine
    yield
    if engine is not None:
        engine.dispose()


app = FastAPI(title="papertrail", version="0.1.0", lifespan=lifespan)
_settings = get_settings()


class DatabaseUnavailable(Exception):
    pass


@app.exception_handler(DatabaseUnavailable)
def database_unavailable(_request: Request, _exc: DatabaseUnavailable):
    return problem(503, "database-unavailable", "Database unavailable", "Postgres is not reachable.", retry_after="5")


app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session() -> Iterator[Session]:
    if _factory is None:
        raise DatabaseUnavailable()
    session = _factory()
    try:
        yield session
    finally:
        session.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "papertrail", "status": "ok"}


@app.get("/health")
def health(settings: Settings = Depends(get_settings)):
    status = database_status(settings)
    if not status["ok"]:
        return problem(503, "database-unavailable", "Database unavailable", str(status["detail"]), retry_after="5")
    return {"service": "papertrail", "status": "ok", "database": status}


@app.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(body: ProjectCreate, response: Response, session: Session = Depends(get_session)):
    row = Project(
        id=str(uuid4()),
        name=body.name.strip(),
        research_question=body.research_question.strip(),
        status="draft",
    )
    session.add(row)
    session.commit()
    response.headers["Location"] = f"/projects/{row.id}"
    return _project_out(row)


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_session)):
    rows = session.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return [_project_out(row) for row in rows]


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, session: Session = Depends(get_session)):
    row = session.get(Project, project_id)
    if row is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    return _project_out(row)


@app.post("/projects/{project_id}/seeds", response_model=SeedResult)
def add_seeds(project_id: str, body: SeedCreate, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if project is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    if not body.dois and not body.titles and not body.bibtex.strip():
        return problem(422, "seeds-empty", "No seeds", "Provide a DOI, a title, or BibTeX.")
    settings = get_settings()
    scholarly = Scholarly(settings, session)
    try:
        papers, unresolved = add_resolved_seeds(session, scholarly, project_id, body.dois, body.titles, body.bibtex)
    finally:
        scholarly.close()
    checks = _load_checks(session, papers)
    resolved = [_paper_response(session, paper, papers, checks.get(paper.id, [])) for paper in papers]
    return SeedResult(resolved=resolved, unresolved=unresolved)


@app.post("/projects/{project_id}/analyze", status_code=202, response_model=AnalyzeOut)
def start_analyze(
    project_id: str,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if project is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    if project.status == "running":
        return problem(409, "analyze-running", "Analyze already running", "Wait for the current run to finish.")
    project.status = "running"
    session.commit()
    background.add_task(analyze_project, project_id)
    return AnalyzeOut(project_id=project_id, status="running")


@app.get("/projects/{project_id}/events", response_model=list[EventOut])
def list_events(project_id: str, session: Session = Depends(get_session)):
    if session.get(Project, project_id) is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    rows = session.scalars(
        select(AgentEvent).where(AgentEvent.project_id == project_id).order_by(AgentEvent.created_at)
    ).all()
    return [
        EventOut(
            id=row.id,
            step=row.step,
            tool=row.tool,
            input=row.input or {},
            output_summary=row.output_summary,
            created_at=row.created_at,
        )
        for row in rows
    ]


@app.get("/projects/{project_id}/results", response_model=list[PaperOut])
def list_results(project_id: str, session: Session = Depends(get_session)):
    if session.get(Project, project_id) is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    rows = list(session.scalars(select(Paper).where(Paper.project_id == project_id)).all())
    visible = [row for row in rows if row.status != "seed"]
    visible.sort(key=lambda row: row.rank_score or 0, reverse=True)
    visible = visible[: get_settings().max_candidates]
    checks = _load_checks(session, visible)
    return [_paper_response(session, row, rows, checks.get(row.id, [])) for row in visible]


@app.post("/papers/{paper_id}/feedback", response_model=PaperOut)
def feedback(paper_id: str, body: FeedbackIn, session: Session = Depends(get_session)):
    paper = session.get(Paper, paper_id)
    if paper is None:
        return problem(404, "paper-not-found", "Paper not found", "No paper has that id.")
    paper.status = "accepted" if body.action == "accept" else "rejected"
    session.commit()
    rerank_project(session, paper.project_id)
    session.refresh(paper)
    return _paper_response(session, paper)


@app.post("/projects/{project_id}/evaluate", response_model=EvalOut)
def evaluate(project_id: str, session: Session = Depends(get_session)):
    if session.get(Project, project_id) is None:
        return problem(404, "project-not-found", "Project not found", "No project has that id.")
    seeds = list(session.scalars(select(Paper).where(Paper.project_id == project_id, Paper.status == "seed")).all())
    if len(seeds) < 2:
        return problem(422, "evaluate-needs-seeds", "Need two seeds", "Leave-one-out needs at least two seeds.")
    settings = get_settings()
    scholarly = Scholarly(settings, session)
    try:
        hits = leave_one_out(session, scholarly, project_id)
    finally:
        scholarly.close()
    found = len([item for item in hits if item["found"]])
    recall = found / len(hits) if hits else 0.0
    return EvalOut(
        recall_at_10=round(recall, 4),
        seeds_checked=len(hits),
        hits=[EvalHit(**item) for item in hits],
    )


def _project_out(row: Project) -> ProjectOut:
    return ProjectOut(
        id=row.id,
        name=row.name,
        research_question=row.research_question,
        created_at=row.created_at,
        status=row.status,
    )


def _load_checks(session: Session, papers: list[Paper]) -> dict[str, list[VerificationResult]]:
    grouped: dict[str, list[VerificationResult]] = {paper.id: [] for paper in papers}
    if not papers:
        return grouped
    rows = session.scalars(select(VerificationResult).where(VerificationResult.paper_id.in_(list(grouped)))).all()
    for row in rows:
        grouped.setdefault(row.paper_id, []).append(row)
    return grouped


def _paper_response(
    session: Session,
    paper: Paper,
    all_papers: list[Paper] | None = None,
    checks: list[VerificationResult] | None = None,
) -> PaperOut:
    if checks is None:
        checks = list(session.scalars(select(VerificationResult).where(VerificationResult.paper_id == paper.id)).all())
    if all_papers is None:
        all_papers = list(session.scalars(select(Paper).where(Paper.project_id == paper.project_id)).all())
    titles = {item.id: item.title for item in all_papers if item.status == "seed"}
    return to_paper_out(paper, checks, titles, all_papers)
