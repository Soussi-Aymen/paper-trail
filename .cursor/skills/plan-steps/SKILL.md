---
name: plan-steps
description: >-
  Writes a short docs/plan.md plus one executable prompt file per step, grouped
  into parallel-safe waves, without inlining prompts into the plan. Use in Plan
  mode or when creating a multi-step implementation plan, step prompts, agent
  sessions, docs/plan.md, docs/prompts/, or parallel waves. Do not use for a
  single isolated change, code implementation, or rewriting application source.
---

# Plan + per-step prompts

When the work is more than one isolated change, the plan is not done until every step has a prompt file.

## Owns

`docs/plan.md`, `docs/prompts/*.md`, wave grouping, what lives in the plan vs in each prompt.

## Does not cover

- How to implement the work (that is other skills)
- Always-on coding rules (Karpathy, repo conventions) — do not copy them into prompts
- Git branching beyond pull-rebase-before-commit for parallel agents

## Location

- Plan: `docs/plan.md` — not the repo root, not `.cursor/`
- Prompts: `docs/prompts/<id>-<slug>.md` (example: `step-02-guardrails.md`)
- Cursor Plan mode is the session that **writes** these files. The files in the repo are what later sessions execute. Do not treat the Plan-mode canvas as the handoff.

## Always emit both

In the same planning pass:

1. `docs/plan.md` — short source of truth
2. One prompt file per step — the only thing pasted into (or opened as) an execution session

Never a plan without prompts. Never paste full prompt bodies into the plan. The current anti-pattern is an 800-line plan that repeats every prompt: every "read the plan" then costs the whole build.

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
- Neither mutates lockfiles, root `package.json`, or other global config
- Every `depends-on` is already merged to the integration branch

Do not start wave N+1 until every step in wave N is merged. File ownership is the parallel primitive — not "these features feel independent."

## Token split

**`docs/plan.md`** is read by every step, so keep it small (aim under ~150–200 lines):

- Goal in a few lines
- Decisions later steps must not re-litigate (short bullets)
- Wave graph + ownership table (`id`, wave, depends-on, owns, parallel-with)
- One short paragraph per step (what, not the full how)

No copy-paste prompt appendix. No stack/strictness/skill checklists (rules and skills already load).

**Each prompt file** is one session's instructions. Unique to that step only:

```
STEP: 02-guardrails
WAVE: C — parallel with 03-agent, 05-ui
DEPENDS ON: 01-shared merged

FIRST ACTION: read docs/plan.md (goal, decisions, wave graph, this step's paragraph).
Do not read other prompt files. Do not restate repo rules or skills.

OWNS: <paths>
MUST NOT TOUCH: <paths>

DELIVERABLES:
- ...

VERIFY: <command>
COMMIT: git pull --rebase origin <integration-branch> && git add <owns> && git commit -m "<msg>" && git push
```

Leave out of every prompt: product grading essay, full stack list, TypeScript-strict paragraph, other steps' deliverables, duplicated architecture. One line is enough: follow loaded rules and skills.

`OWNS` / `MUST NOT TOUCH` / `DELIVERABLES` / `VERIFY` stay in the prompt even though the plan has a summary — parallel agents must not have to reconstruct ownership from a table.

## Kickoff

One execution session per prompt file. Point the agent at that file ("execute `docs/prompts/step-02-guardrails.md`"). Do not paste `docs/plan.md` into the chat — the prompt tells the agent to read it.

If Plan mode is asked only for a design discussion with no execution, still write the prompt files; they are the deliverable that makes the plan runnable.
