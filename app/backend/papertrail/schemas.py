from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    research_question: str = Field(min_length=1)


class ProjectOut(BaseModel):
    id: str
    name: str
    research_question: str
    created_at: datetime
    status: str


class SeedCreate(BaseModel):
    dois: list[str] = []
    titles: list[str] = []
    bibtex: str = ""


class ReferenceOut(BaseModel):
    title: str | None = None
    url: str
    in_project: bool = False


class CheckOut(BaseModel):
    check_name: str
    outcome: str
    evidence: dict


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list
    year: int | None
    venue: str | None
    citation_count: int
    doi: str | None
    openalex_id: str | None
    source_urls: list[str]
    pdf_url: str | None = None
    status: str
    rank_score: float | None
    score_breakdown: dict | None
    badge: str
    checks: list[CheckOut]
    explanation: str | None
    explanation_grounded: bool | None
    connected_seeds: list[str]
    references: list[ReferenceOut] = []
    discovery_paths: list


class SeedResult(BaseModel):
    resolved: list[PaperOut]
    unresolved: list[str]


class AnalyzeOut(BaseModel):
    project_id: str
    status: str


class EventOut(BaseModel):
    id: str
    step: str
    tool: str
    input: dict
    output_summary: str
    created_at: datetime


class FeedbackIn(BaseModel):
    action: Literal["accept", "reject"]


class EvalHit(BaseModel):
    seed_id: str
    title: str
    found: bool
    rank: int | None


class EvalOut(BaseModel):
    recall_at_10: float
    seeds_checked: int
    hits: list[EvalHit]
