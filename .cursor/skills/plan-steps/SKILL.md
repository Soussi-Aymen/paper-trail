---
name: plan-steps
description: >-
  Writes a short docs/plan.md plus one copy-ready prompt file per step, grouped
  into parallel-safe waves. Each prompt names needed inputs and links the plan
  file. Plan mode must offer two run paths: paste one prompt per Agent session,
  or Cursor Build on the plan todos. Use in Plan mode or when creating a
  multi-step implementation plan, step prompts, agent sessions, docs/plan.md,
  docs/prompts/, parallel waves, or Build. Do not use for a single isolated
  change, code implementation, or rewriting application source.
---

# Plan + per-step prompts

When the work is more than one isolated change, the plan is not done until every step has a prompt file **and** both run paths are written.

Plan mode writes files + a todo list. Execution is the user's choice; do not assume Build or assume separate sessions.

## Owns

`docs/plan.md`, `docs/prompts/*.md`, wave grouping, what lives in the plan vs in each prompt, the two run paths.

## Does not cover

- How to implement the work (that is other skills)
- Always-on coding rules (Karpathy, repo conventions) — do not copy them into prompts
- Git branching beyond pull-rebase-before-commit for parallel agents

## Location

- Plan: `docs/plan.md` — not the repo root, not `.cursor/`
- Prompts: `docs/prompts/<id>-<slug>.md` (example: `step-02-guardrails.md`)
- Cursor Plan mode is the session that **writes** these files and the Build todos. The files in the repo are the handoff. Do not treat the Plan-mode canvas as the only artifact.

## Always emit both

In the same planning pass:

1. `docs/plan.md` — short source of truth, including a **Run** section with the two options
2. One prompt file per step — a complete first message (needed info + plan link)

Never a plan without prompts. Never paste full prompt bodies into the plan. The current anti-pattern is an 800-line plan that repeats every prompt: every "read the plan" then costs the whole build.

## Two run paths (required)

`docs/plan.md` must include a **Run** section that states both options as equivalent. Same files either way.

### Option A — separate Agent sessions (copy-paste)

One new Agent chat per step. The first message is the **entire** matching `docs/prompts/<id>-<slug>.md` (not a summary, not the plan). Parallelize only within a wave after `depends-on` is merged.

### Option B — Cursor Build

Use this Plan's todos / Build. Todos are indexed by wave. Each todo is one step and tells the agent to:

1. Read `[docs/plan.md](docs/plan.md)` (goal, decisions, wave graph, that step's paragraph)
2. Execute **only** `[docs/prompts/<id>-<slug>.md](docs/prompts/<id>-<slug>.md)`
3. Stop at that step's `VERIFY` / `COMMIT`

Do not start wave N+1 until every step in wave N is done (merged if using parallel agents; finished in-tree if Build is serial).

When writing Plan-mode todos, each todo body must include those two file links plus `OWNS`. That is what makes Build work without the user pasting prompts.

## Waves, not scrambled step numbers

Keep the wave model. Do not renumber steps into execution order (API stays "the API step" even if it runs in wave D).

Fix the presentation:

- **Index by wave.** List steps in wave order in the plan and in any todo list. Do not list story-order (4, then 5, then 3).
- **Name steps by what they produce** (`shared`, `guardrails`, `api`). Numbers are optional stable ids, not the schedule.
- A **wave** is every step whose `depends-on` is already merged and whose `OWNS` sets are pairwise disjoint.
- Linear todos cannot express parallelism. Each todo is one step, tagged with its wave, or one todo per wave listing the parallel steps.

```
Wave A: scaffold
Wave B: shared
Wave C: guardrails ∥ agent ∥ ui
Wave D: api ∥ redteam
Wave E: docker ∥ hooks
Wave F: readme
```

Two steps may share a wave only if all of these hold:

- Disjoint `OWNS` (no shared files)
- Neither mutates lockfiles, `uv.lock`, `pyproject.toml`, or other global config
- Every `depends-on` is already merged to the integration branch (or already completed in this tree if Option B is serial)

Do not start wave N+1 until every step in wave N is merged/done. File ownership is the parallel primitive — not "these features feel independent."

## Token split

**`docs/plan.md`** is read by every step, so keep it small (aim under ~150–200 lines):

- Goal in a few lines
- Decisions later steps must not re-litigate (short bullets)
- Wave graph + ownership table (`id`, wave, depends-on, owns, parallel-with)
- **Run** — Option A (paste prompt files) and Option B (Build todos) as above
- One short paragraph per step (what, not the full how)

No copy-paste prompt appendix. No stack/strictness/skill checklists (rules and skills already load).

**Each prompt file** is one session's full first message. Unique to that step only. It must include a markdown link to the plan file and a **NEEDED** block so a cold session does not guess.

```
# Execute: 02-guardrails

Paste this entire file as the first message of a new Agent session (Option A),
or run it from Plan Build (Option B). Either way, this file is the step.

PLAN: [docs/plan.md](docs/plan.md)
Read first: goal, decisions, wave graph, this step's paragraph.
Do not read other prompt files. Do not restate repo rules or skills.

STEP: 02-guardrails
WAVE: C — parallel with 03-agent, 05-ui
DEPENDS ON: 01-shared merged

NEEDED:
- Already on the integration branch: <what this step assumes exists>
- Read after the plan: <input files this step consumes>
- Env / secrets: <none | named vars>
- Out of scope unless listed: other steps' files

OWNS: <paths>
MUST NOT TOUCH: <paths>

DELIVERABLES:
- ...

VERIFY: <command>
COMMIT: git add <owns> && git commit -m "<msg>"
```

After COMMIT, do not push. The last line of the agent reply is: Ready to push

Leave out of every prompt: product grading essay, full stack list, TypeScript-strict paragraph, other steps' deliverables, duplicated architecture. One line is enough: follow loaded rules and skills.

`PLAN` / `NEEDED` / `OWNS` / `MUST NOT TOUCH` / `DELIVERABLES` / `VERIFY` stay in the prompt even though the plan has a summary — a pasted session and a Build agent must not reconstruct ownership from a table.

`NEEDED` is required. If there is nothing extra, write `Env / secrets: none` and still list the files to read. Never omit the plan link.

## Kickoff

After writing the files, tell the user they can:

1. **Option A:** open a new Agent session per step and paste that prompt file
2. **Option B:** Build this Plan (todos already point at plan + prompt)

Do not paste `docs/plan.md` into chat — the prompt tells the agent to read it via the link.

If Plan mode is asked only for a design discussion with no execution, still write the prompt files and the **Run** section; they are the deliverable that makes the plan runnable either way.
