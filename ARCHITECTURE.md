# gan-harness Architecture

> "Inside, ARCHITECTURE.md should put aside boring details and focus only on
> unique constraints and invariants of the system." — matklad

This file records what does NOT change when code changes. The auto-regenerated
module map lives at [`app_docs/codemap.md`](app_docs/codemap.md). Decision
rationale lives at [`docs/adr/`](docs/adr/).

## Bird's-eye view

A four-stage pipeline (`/prd` → `/plan` → `/execution-loop` → `/finalize`)
that turns free-form requirement intent into vetted code in the codebase.
Each stage's behaviour is defined by a **skill** (filesystem-discovered
markdown references); each stage's heavy lifting is performed by **subagents**
(Task-spawned workers). The harness core is language-free; **stack skills**
plug in language/framework idioms.

## Invariants

These rules cannot be derived by grep / file-existence checks. Violating any
of them breaks the harness.

### Codebase as Single Source of Truth

The codebase is authoritative for everything per-feature. Alive docs at the
repo root supplement only what the codebase cannot express:

- `ARCHITECTURE.md` — invariants (this file; "absence of X" facts)
- `CONTEXT.md` — domain ubiquitous language (Pocock-style substrate)
- `docs/adr/` — decision rationale + rejected options (MADR, immutable)
- `app_docs/codemap.md` — auto-generated module map (read-only output)

If information lives in code (per-feature tests, API signatures, in-code
docstrings), it stays there. The alive docs are a filtered projection
(Martraire), not a parallel truth.

### Language-free core

Files under `.claude/skills/{plan-workflow,planner-handbook,prd-workflow,
harness-loop,batch-gc}/` MUST NOT contain language- or framework-specific
tokens. No `flutter`, `dart`, `tsc`, `pytest`, `cargo`, `kubectl`, etc.
Stack-specific content lives in `.claude/skills/<stack>/` and is consumed
via the active stack skill mechanism.

### Zero debt

`/plan` does NOT produce a `risks` / `cross_r_risks` / `tech_debt` field.
Every risk identified by the planner resolves into one of:

1. A proposed ADR under `docs/adr/` (only when the three-test gate passes:
   hard-to-reverse + surprising + real-trade-off)
2. A feature `spec.open_questions[]` entry with non-null `resolution`
3. A new feature or AC

The schema's `additionalProperties: false` at top level mechanically rejects
rogue debt fields.

**No deferred punt.** `open_question.resolution_kind` has only three values:
`feature_local`, `architectural`, `glossary`. Every question resolves
in-batch — there is no `deferred` escape. If the planner cannot recommend
a resolution, the batch scope is wrong: escalate at /plan Phase 2 walk and
re-grill at /prd. Pushing a question to the next batch is not allowed; it
manufactures hidden debt that propagates across batches.

### ADR immutability

Once an ADR has `status: accepted`, its body is never edited. To revise,
write a new ADR with `supersedes: [old_id]`. The only allowed mutation on
an existing ADR is the frontmatter fields `status` and `superseded_by`,
filled retroactively by `scripts/finalize_adr.py`.

### Vertical slices, not horizontal phases

Every feature in `feature-list.json` MUST cross every layer the feature
description implies (UI → API → service → DB if full-stack). Phase-named
features (`phase-1-database`, `migration-only`, `*-only`, etc.) are
rejected by `plan_lint.py L10a`. UI-touching features without
`l5_smoke_path` are rejected by `L10b`.

### Skill-shaped agent behaviour

All agent behaviour is defined via skills. There is no "agent code" outside
skills. New behaviour means a new skill or a new reference in an existing
skill, not a hardcoded prompt or a change to a core script.

### Single human checkpoint per stage

Each pipeline stage has exactly ONE human checkpoint via `AskUserQuestion`.
PRD: post-grill confirmation. Plan: post-self-verify checkpoint. Execution-
loop: per-round verdicts. Finalize: pre-archive sweep. Skipping or doubling
checkpoints breaks the orchestrator boundary contract.

## What this file is NOT

- Getting-started guide → [README.md](README.md)
- Module navigator → [`app_docs/codemap.md`](app_docs/codemap.md)
- Decision log → [`docs/adr/`](docs/adr/) + its `index.md`
- Domain language → [`CONTEXT.md`](CONTEXT.md)
