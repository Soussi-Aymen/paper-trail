"""Load a JSON fixture, resolve seeds, and run Analyze."""

import json
import sys
from pathlib import Path
from uuid import uuid4

from papertrail.config import get_settings
from papertrail.db import make_engine, prepare_database, session_factory
from papertrail.models import Project
from papertrail.pipeline import add_fixture_candidate, add_resolved_seeds, analyze_project
from papertrail.scholarly import Scholarly


def main() -> int:
    default = Path(__file__).parent / "fixtures" / "demo.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    payload = json.loads(path.read_text())
    settings = get_settings()
    engine = make_engine(settings.database_url)
    prepare_database(engine)
    session = session_factory(engine)()
    scholarly = Scholarly(settings, session)
    project_id = str(uuid4())
    try:
        project = Project(
            id=project_id,
            name=payload["name"],
            research_question=payload["research_question"],
            status="draft",
        )
        session.add(project)
        session.commit()
        resolved, unresolved = add_resolved_seeds(
            session,
            scholarly,
            project.id,
            [item["doi"] for item in payload.get("seeds") or []],
            [],
            "",
        )
        suspects: list[str] = []
        for item in payload.get("suspects") or []:
            paper = add_fixture_candidate(session, scholarly, project.id, item["doi"])
            if paper is None:
                unresolved.append(item["doi"])
            else:
                suspects.append(paper.title)
        print(
            json.dumps(
                {
                    "project_id": project.id,
                    "seeds": len(resolved),
                    "unresolved": unresolved,
                    "suspects": suspects,
                },
                indent=2,
            )
        )
    finally:
        scholarly.close()
        session.close()
        engine.dispose()
    analyze_project(project_id)
    print(json.dumps({"project_id": project_id, "status": "analyze-finished"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
