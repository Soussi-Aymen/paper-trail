# Papertrail

Give a research question and a few papers you already know. Papertrail finds related work, ranks it, and shows why each result is there — including whether the paper looks real, retracted, or only weakly supported.

Models run on [Nebius Token Factory](https://docs.tokenfactory.nebius.com/). Paper metadata comes from OpenAlex and Crossref. The browser app and the API are separate containers from the model endpoint.

## Run locally

Fill in `.env` from `.env.example`. You need a Token Factory key and three model ids (a small chat model, a large chat model, and an embedding model). List ids with the probe below. Set `SCHOLARLY_CONTACT_EMAIL` so OpenAlex and Crossref can see who is calling. Set `OPENALEX_API_KEY` from [openalex.org/settings/api](https://openalex.org/settings/api). The free key includes a daily request budget.

```bash
docker compose up db -d
cd app/backend
uv sync
uv run python -m scripts.check_token_factory
uv run uvicorn papertrail.main:app --reload --host 0.0.0.0 --port 8000
```

In another shell, from the repo root:

```bash
pnpm install
pnpm --filter frontend dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the API.

Create a project, paste DOIs or titles (or BibTeX), resolve the seeds, then click Analyze. The trace updates while the job runs. Each result has a trust badge, the checks behind it, a short explanation, and source links. Accept and reject re-rank from cached embeddings.

`EMBEDDING_DIMENSIONS` must match the embedding model. The probe prints the vector length. The default is 1024. If the probe prints another length, set `EMBEDDING_DIMENSIONS` and recreate the database volume before the first analyze (`docker compose down -v` removes it).

## Demo

`app/backend/scripts/fixtures/demo.json` holds the demo inputs. Nothing in the ranking or verification code hardcodes those papers.

```bash
docker compose up db -d
cd app/backend
uv run python -m scripts.load_fixture
```

The fixture has two COVID-19 vaccine trial seeds and one retracted Lancet DOI added as a candidate. After Analyze, that retracted paper should show a red badge. The evidence list names the OpenAlex or Crossref fact and a source URL.

## Architecture

`app/frontend` is the Vite React TypeScript app. `app/backend` is FastAPI. Postgres with pgvector stores projects, papers, verification rows, the agent trace, and a cache of HTTP, embedding, and chat responses.

Analyze runs in the API process:

1. Resolve seeds (DOI, title, or BibTeX) through OpenAlex, then Crossref.
2. Pull citation neighbors of those seeds.
3. Ask the small model for a few search queries and run them on OpenAlex.
4. Drop duplicates and the seeds themselves.
5. Embed the question, the seeds, and at most 15 prefiltered candidates. Rank with graph overlap, similarity to the question, similarity to the seed centroid, recency, and citations. Verify and explain only the top 3.
6. Run the checks below and ask the large model for a grounded explanation.

Every tool writes a row in `agent_events`. That list is the trace on the page.

Accept moves a paper toward the centroid. Reject moves the centroid away from it. Re-ranking uses stored vectors.

## Verification

Each check stores `pass`, `warn`, `fail`, or `unknown`, plus a source URL and the fact that was used.

| Check | Red when |
| --- | --- |
| DOI and cross-source match | A DOI is present and does not resolve, or the Crossref title does not match |
| Retraction | OpenAlex `is_retracted` or a Crossref retraction update |
| Authors | Warning or unknown only. ORCID or an OpenAlex author profile counts as pass |
| Venue | DOAJ or an OpenAlex source record. Missing data is unknown, not a failure |
| Citation context | Warning when nothing cites the paper, or the sample has only one author group |
| Paper-mill style | The small model may warn. It cannot turn the badge red by itself |

The badge is red if any check failed, yellow if anything warned or is unknown, and green when every check passed. A missing DOI is unknown, not red.

## Evaluation

Leave-one-out hides each seed, asks OpenAlex for neighbors of the other seeds, and records whether the hidden seed comes back in the top 10.

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/evaluate
```

`POST /projects/{id}/evaluate` returns `recall_at_10`. Cached OpenAlex responses are reused.

## Deploy

Backend and frontend images build separately from the model endpoint.

```bash
docker compose up --build
```

The API image is `app/backend/Dockerfile` (uv, non-root user, health check on `/health`). The UI image is `app/frontend/Dockerfile`. Its build context is the repo root because the pnpm lockfile lives there. Postgres keeps a data volume and is the one service with a writable data directory.

Do not commit `.env`.
