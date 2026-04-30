# Harness Reference — PRD → Plan → Execution-loop → Finalize

Language-agnostic reference for the four-stage coding-agent harness.
Dart / Flutter / Serverpod serves as the running example; the pipeline
works for any language when a matching stack skill exists.

## System diagram

![Harness pipeline](designs/svg/harness-system.svg)

The diagram above shows the full pipeline: four stage commands (cyan /
teal / orchestrator-cyan / purple) produce scratch artifacts (dashed)
that get drained into alive docs (gold) via `sink_feature.py` on
per-feature Evaluator PASS and via `/finalize` at batch end. The stack skill
(pink) is the plug-point rendering language-agnostic Planner intent
into language-specific syntax. Three sensor panels at the bottom
implement the Guides/Sensors/Steering loop control pattern.

## Stage map

```
/prd              /plan             /execution-loop         /finalize
  │                 │                  │                     │
  ▼                 ▼                  ▼                     ▼
requirement.md    plan.md           per-feature          dreamer review
× N               feature-list.json Generator↔Evaluator  + glossary/codemap
questions.md      research.md       up to 3 rounds       promote
glossary-draft.md                   sink on PASS         + archive
                                    + dreamer tail       + doc-garden scan
                                      (DREAM-*.md)       + single commit
```

Everything in the four stages is language-neutral except the **stack
skill** plugged in at execution time (see `Stack skill` below).

## Alive docs — the single source of truth tree

```
docs/
  decisions/NNNN-<slug>.md    MADR architectural decisions (per-batch drain target)
  decisions/index.md          MADR index
  glossary.md                 Ubiquitous language (shared term table)
  tech-debt-tracker.md        Cross-batch risks, auto-appended by sink
  feature-list.json           Current batch features + testContracts (lifted from plan.md)
app_docs/
  codemap.md                  Navigation index (scan-derived)
  test-fixtures.md            ADR-0010 scenario-tier fixture registry
specs/
  _batch/                     Current batch scratch:
    plan.md                   Drain bucket with named sinks
    research.md               Blindfold findings compiled by MAIN
    questions.md              Research questions (from /prd)
    glossary-draft.md         Batch-scoped new terms (merged into glossary.md)
  R{NN}/
    requirement.md            Per-R acceptance criteria (from /prd)
  completed/{slug}/           Archived plans (keep forever)
CLAUDE.md                     Project identity + invariants + pointers
```

## Stage 1 — /prd

Interview-driven grilling to reach shared design concept before any
artefact lands.

**Owner**: MAIN (must call `AskUserQuestion` — subagents can't).

**Inputs**:
- Free-form user intent or rough batch dump.

**Outputs**:
- `specs/R{NN}/requirement.md` × N (one per Requirement R) — 5 mandatory
  sections: §User Story / §Roles & Permissions / §Pre-conditions /
  §Business Rules & Constraints / §Acceptance Criteria
- `specs/_batch/questions.md` (objective research questions for /plan)
- `specs/_batch/glossary-draft.md` (new ubiquitous-language terms)

### AC discipline (sets up the deterministic L3a gate in Stage 4)

Each AC in §Acceptance Criteria has a single-line header
`- [ ] **AC-N** — title` followed by indented `**Given** / **When** /
**Then**` bullets. The `Then` clause encodes machine-verifiable anchors:

- User-facing strings in `"double quotes"`
- Widget keys / test IDs in `` `backticks` ``
- Negative behaviour with `MUST NOT` keyword AND/OR `(negative)` tag in
  title

Edge cases are AC entries tagged `(edge)` — there is **no** separate
Edge Cases section. Every R MUST contain ≥1 `(negative)` AC. These
conventions are what `ac_content_gate.py` (Stage 4 L3a sensor) greps
for. Legacy single-line ACs are skipped gracefully so migration is
incremental.

**Skill**: `prd-workflow` (grill-protocol + decompose).

## Stage 2+3 — /plan

Blindfold research + planner with self-verify loop.

**Owner**: MAIN spawns `codebase-fact-finder × N` (blindfold) → compiles
`specs/_batch/research.md` → spawns `planner` agent → one human
`AskUserQuestion` checkpoint.

**Inputs**:
- `specs/R*/requirement.md` × N (from /prd)
- `specs/_batch/questions.md` (from /prd)
- Alive docs (glossary, codemap, decisions index, tech-debt)

**Outputs**:
- `specs/_batch/plan.md` — drain bucket with 8 named-sink sections:

  | Section | Sink | Stack-agnostic? |
  |---|---|---|
  | `## Architectural Decisions` | `docs/decisions/NNNN-*.md` | yes |
  | `## Module Boundaries` | feature module interface docs | **no** — stack recipe |
  | `## Model Intent` | data-model class docs | **no** — stack recipe |
  | `## Endpoint Intent` | API entry class docs | **no** — stack recipe |
  | `## Capabilities` | `docs/feature-list.json` | yes |
  | `## Test Contracts` | `feature-list.json[].testContract` | yes |
  | `## Cross-R Risks` | `docs/tech-debt-tracker.md` | yes |
  | `## Codemap Diff` | `app_docs/codemap.md` regen | yes |

- `docs/feature-list.json` — lifted from plan.md via `lift_capabilities.py`

**Self-verify gates** (all must PASS before human checkpoint):
- `plan_lint.py` — L1-L7 structural checks
- `lift_capabilities.py` — parses plan.md, emits feature-list.json
- `plan_validator.py` — S1-S6 schema + DAG + refs + testContract + module boundary

**Skill**: `plan-workflow`.

### Planner's `## Module Boundaries` format (language-agnostic)

```markdown
### Feature: {name}
Path: {repo-relative feature directory}

**Public exports**:
- {Symbol1} — {one-line purpose}

**Internal (NOT public)**:
- {HelperA}, {WidgetB} (feature-local only)

**Reads from**:
- {other-feature-path} via barrel ({listed public symbols})

**Writes to**:
- {shared-path} on {trigger}

**MUST NOT depend on**:
- {forbidden-path} ({reason})
```

The stack skill's `recipes/barrel-materialization.md` renders this into
the language's barrel syntax at sink time (see mapping table below).

## Stage 4 — /execution-loop

Serial per-feature Generator↔Evaluator, up to 3 retry rounds.

**Owner**: MAIN loop that spawns one Generator subagent, one Evaluator
subagent, and runs the sink script on PASS.

**Per feature**:

```
Round 1..3:
  Generator
    reads feature.testContract from feature-list.json
    writes code
    self-verify: L1 analyze + L2 tests
                  + ac_coverage   (presence)
                  + ac_content_gate (content / L3a)
    produces F{NN}-progress-R{N}.md
  Evaluator
    quality-gate L1/L1b/L2/L3
    ac_coverage L3 gate (presence)
    ac_content_gate L3a gate (content — punctuation-anchored)
    L4 (if contract asks)
    L5 drive via testContract.l5SmokePath (mandatory for UI features)
    produces F{NN}-eval-R{N}.md
  PASS:
    git commit + DONE
    sink_feature.py  ← drain plan.md sections to alive docs
    → next feature
  FAIL:
    inject remediation hints into next round
  FAIL at R3:
    BLOCKED + commit audit
```

The L3 gate is two-layer: `ac_coverage.py` checks AC-id presence in test
group strings; `ac_content_gate.py` then checks that quoted literals,
backticked widget keys, and `MUST NOT` negative anchors from each AC's
`Then` clause actually appear inside the matching test group's
`find.*` / `expect` / `Key()` calls. The content gate is what catches
"lazy test wrapping the AC-id but asserting `expect(true, isTrue)`"
cheating. Anything not anchored by the punctuation discipline falls back
to LLM L3b judgment via Evaluator's reading of test code.

**Post-loop tail**: `gen-dreamer` + `eval-dreamer` spawn in parallel.
They emit **proposal lists** — `docs/progress/DREAM-gen.md` and
`docs/progress/DREAM-eval.md` — never writing directly to capsules /
SKILL.md / anti-patterns. /finalize Phase 1 drains those proposals via
`AskUserQuestion`. Both DREAM files must exist before /finalize will run.

**Skill**: `harness-loop`.

### Per-feature sink on PASS (ADR-0008 Layer A)

`.claude/skills/harness-loop/scripts/sink_feature.py` runs as a
deterministic node. Language-agnostic portion drains:
- `## Cross-R Risks` → `docs/tech-debt-tracker.md` (append, hash dedup)
- `## Architectural Decisions` → checks for matching `docs/decisions/*.md`
  (does NOT auto-create; reports missing)

Stack-specific portion (delegated to active stack skill's `recipes/`):
- `## Model Intent` → data-model class docs
- `## Endpoint Intent` → API entry class docs
- `## Module Boundaries` → feature module interface docs

## Stage 5 — /finalize

Post-batch ceremony. Drain dreamer proposals, promote glossary/codemap,
archive batch, scan for drift, single commit.

**Owner**: MAIN. Runs only after all features are terminal (DONE or
BLOCKED) AND `gen-dreamer` + `eval-dreamer` (post-loop tail of Stage 4)
have written `docs/progress/DREAM-gen.md` + `docs/progress/DREAM-eval.md`
as **proposal lists** — dreamers never write directly to capsules /
SKILL.md / anti-patterns; they propose, /finalize disposes.

**Skill**: `batch-gc` (`.claude/skills/batch-gc/SKILL.md`).
**Command**: `/finalize` (legacy name `/gc` retired).

### Pre-flight (Phase 1a)

`scripts/preflight.py` aborts the ceremony unless:
- `docs/feature-list.json` exists and every feature is terminal
- `specs/_batch/plan.md` exists (slug source — H1 is `# Plan — batch {slug}`)
- both `DREAM-gen.md` and `DREAM-eval.md` are present

If the batch was already archived, the empty `specs/_batch/` is detected
and /finalize aborts (idempotent).

### Phase 1 — Dreamer Review (the heart of /finalize)

`parse_dream.py` walks each `P-NN` proposal in `DREAM-{gen,eval}.md`
(gen first, then eval; preserve emit order). For each proposal MAIN
asks the user **one** `AskUserQuestion(Approve / Reject / Edit)` with
the full payload rendered in the preview.

Dispatch table for approved proposals:

| Category | Applied action |
|---|---|
| `[create-recipe]` | Write a new capsule file. **Liveness gate**: `recipe_liveness.py --gate --threshold 30` exit 1 ⇒ REFUSE (promotion-only mode), record `skipped: gate-tripped`. |
| `[append-fm]` | Append `FM-NN:` line under target capsule's `## Failure Modes`; bump `version:` frontmatter, record prior version in `parents:`. |
| `[update-heuristic]` | Replace matching line in target's `## Heuristics`; bump version + parents. |
| `[update-worked-example]` | Replace target's `## Worked Example` block; bump version + parents. |
| `[skill-md-quick-ref]` | Insert row into target SKILL.md's Quick Reference table at natural L1→L5 position. |
| `[anti-pattern]` | Append NEVER/ALWAYS bullet under specified H2 in `learned-anti-patterns/<domain>.md`; bump occurrence counts at top. |
| `[prune]` | `git rm` the capsule + update `recipes/README.md`. **Refuses** if any active config path still references it (reverse-grep first). |

End of Phase 1: append an `## Applied (by /finalize on {date})` section
to each DREAM file with per-proposal verdict (`approved/rejected/edited+applied/skipped`).
This is the **only** edit allowed to DREAM files before archive.

### Phase 2 — Promote

Push batch facts into the canonical places the next batch will read.

- **Glossary draft merge**: diff each term in `specs/_batch/glossary-draft.md`
  against `docs/glossary.md`; per-term `AskUserQuestion` (approve/reject/edit);
  approved terms append in existing sort order.
- **Codemap sync**: walk `feature-list.json[].touches` of DONE features;
  for each new `apps/*/lib/features/<dir>/` not in `app_docs/codemap.md`,
  per-dir `AskUserQuestion`; approved lines append under the right section
  (`<dir>/ — <≤15-char purpose>`).
- **Feature-barrel backlog**: `feature_barrel_audit.py` (if present)
  appends features lacking a barrel to `docs/tech-debt-tracker.md` under
  the "Feature barrel backlog" H2 — silent, no prompt (backlog accumulates).

### Phase 3 — Archive

`scripts/finalize_archive.sh {slug}` (slug from `plan.md` H1):

1. `mkdir -p specs/completed/{slug}/`
2. Move `specs/_batch/*` (plan, research, glossary-draft, questions,
   dep-hints, tmp/) → `specs/completed/{slug}/`
3. Move `docs/feature-list.json` → `specs/completed/{slug}/feature-list.json`
4. Move both `DREAM-{gen,eval}.md` → `specs/completed/{slug}/`
5. Generate `BATCH_SUMMARY.md` via `summarize_progress.py` (table of
   per-feature state / round / headline / `infraBlocked` flag, +
   "Notes" line with applied-proposal counts)
6. `git rm` raw progress files: `F*-progress-R*.md`, `F*-eval-R*.md`,
   `F*-gen-trace-R*.md`, `F*-eval-trace-R*.md`, `F*-contract.md`
7. Re-create empty `docs/progress/.gitkeep` + `specs/_batch/.gitkeep`
8. Move `docs/progress/.traces/` → `specs/completed/{slug}/traces/` if
   non-empty, else delete

### Phase 4 — Scan

Spawn `doc-garden` agent (sub-agent). Scope:
1. `docs/design-docs/` reference integrity
2. `docs/decisions.md` AD lint vitality
3. `learned-anti-patterns/*.md` currency
4. Recipe liveness via `recipe_liveness.py`

Trivial drift auto-fixed; everything else logged to
`docs/tech-debt-tracker.md` under a new H2
`## Post-{slug} drift scan ({YYYY-MM-DD})`. Agent's 1-3 line summary
is captured for Phase 5's commit message.

### Phase 5 — Commit + Report

Single commit:

```
chore(finalize): close batch {slug}

- Dreamer proposals: {applied}/{total} applied ({rejected} rejected, {skipped} skipped)
- Archived to specs/completed/{slug}/
- Doc-garden: {scan-summary}
```

Empty commit ⇒ abort with diagnostic (/finalize never lands an empty
commit). Final report block enumerates proposals/glossary/codemap/
barrels/archive/progress-deletes/doc-garden-findings, then "Next step:
`/prd` (for next batch)".

### /finalize verification checklist (post-run)

- `docs/progress/` contains only `.gitkeep` (no `F*-*.md`, no `DREAM-*.md`)
- `specs/_batch/` contains only `.gitkeep`
- `specs/completed/{slug}/` contains plan + research + glossary-draft +
  questions + dep-hints + feature-list.json + DREAM-{gen,eval}.md +
  BATCH_SUMMARY.md (+ tmp/ and traces/ if any)
- `docs/feature-list.json` does NOT exist (archived)
- `docs/tech-debt-tracker.md` has the `## Post-{slug} drift scan` H2
- single clean `chore(finalize):` commit

### Hard rules

- NEVER apply a proposal without explicit `AskUserQuestion` approval
- NEVER skip Phase 4 (doc-garden) — drift matters even when nothing else changed
- NEVER modify `apps/*` / `dandan_server/*` source code from /finalize
- ALWAYS commit exactly once at the end — no partial /finalize state in working tree

## Rot prevention — two-layer sensor

### Layer B1 — Change-lifecycle (pre-commit hook)

`.claude/hooks/pre-commit-doc-lint.sh` runs before every commit:
- Staged source files in the stack's API-entry directory must have
  class-level docstrings
- Staged data-model files must have class-level intent docs
- `codemap.md` referenced feature paths must exist

Blocks commit on failure.

### Layer B2 — Continuous (Phase 4 of /finalize)

`/finalize` Phase 4 spawns `doc-garden` as a sub-agent. It scans:
- codemap path validity
- ADR `## Linters` grep patterns → non-empty is rot
- `learned-anti-patterns` example file refs
- Recipe liveness via `recipe_liveness.py`

Trivial drift auto-fixed inline; non-trivial findings logged to
`docs/tech-debt-tracker.md` under
`## Post-{slug} drift scan ({YYYY-MM-DD})`. The agent's 1-3 line
summary is folded into the single `chore(finalize):` commit.

## Stack skill — the language plug-point

Each supported stack has a skill at `.claude/skills/<stack-name>/` that
provides:

```
<stack-name>/
  SKILL.md                        Stack identity + MCP/tool conventions
  reference/                      Stack references (APIs, patterns, gotchas)
    plan-lint-patterns.md         Concrete patterns for L2/L3/L6 delegation
  recipes/                        Sink materialization recipes
    barrel-materialization.md     ## Module Boundaries → language barrel
    sink-model-intent.md          ## Model Intent → data-model doc block
    sink-endpoint-intent.md       ## Endpoint Intent → API class doc block
    <other stack-specific recipes>
```

### Active stack for this project: `flutter-serverpod`

Dart / Flutter / Serverpod / Riverpod / GoRouter. Uses:
- Feature barrel = `features/{name}/{name}.dart` with `library;` + `export`
- Model intent = `###` block in `.spy.yaml` (propagates via `serverpod generate`)
- Endpoint intent = class-level `///` dartdoc on `*Endpoint` classes

### Adapting to a new stack

1. Copy `.claude/skills/flutter-serverpod/` to `.claude/skills/<new-stack>/`
2. Replace `SKILL.md` with new stack identity (tooling, MCP servers, etc.)
3. Replace `reference/*.md` with new stack's framework references
4. Replace `recipes/barrel-materialization.md` and
   `recipes/sink-*.md` with new-language equivalents using the table below
5. Replace `reference/plan-lint-patterns.md` with new-language patterns

**Barrel mechanism per language**:

| Language | Barrel file | Entry syntax | Module doc |
|---|---|---|---|
| Dart | `<name>.dart` | `library;` + `export '...'` | `/// library` |
| TypeScript | `index.ts` | `export * from './...'` | `/** @module */` JSDoc |
| Python | `__init__.py` | `__all__ = [...]` | `"""module docstring"""` |
| Rust | `mod.rs` / `lib.rs` | `pub mod` / `pub use` | `//!` inner doc |
| Go | package-level file | Capitalized exports | `// Package foo ...` |
| Java | `package-info.java` | public class exports | `/** package javadoc */` |

Harness core skills (`harness-loop`, `plan-workflow`, `execution-loop`,
`ac-coverage`, `recipe-authoring`) do not change when swapping stacks.

## Computational sensors — the deterministic spine

| Sensor | Input | Output | Runs at |
|---|---|---|---|
| `plan_lint.py` | plan.md | JSON rules (L1-L8; L8 = ADR-0010 fixture-declaration) | /plan self-verify |
| `lift_capabilities.py` | plan.md | feature-list.json (incl. `testContract.fixtureRequirements`) | /plan self-verify |
| `plan_validator.py` | feature-list.json (+ plan.md for S6) | JSON rules (S1-S10; S7-S10 = ADR-0010 plan-time gates) | /plan self-verify |
| `gen_local_gate.sh` | staged files + current-context | L1 analyze + format + R8 seed-boundary check | Generator pre-PASS |
| `quality-gate.sh` | feature files | L1/L1b/L2/L3 JSON | Evaluator |
| `ac_coverage.py` | requirement.md + test files | presence JSON (L3 structural) | Generator + Evaluator |
| `ac_content_gate.py` | requirement.md (G/W/T body) + test files | content violations JSON (L3a deterministic) | Generator + Evaluator |
| `seed_coverage.py` | feature-list.json + seed sources + fixtures | l5SmokePath ↔ seed factories cross-check (ADR-0010) | Generator pre-PASS, Evaluator step 5 |
| `pre-commit-doc-lint.sh` | staged files | block/pass | every git commit |
| `sink_feature.py` | plan.md + feature-id | sink result JSON | Evaluator PASS |

All scripts are pure stdlib Python or POSIX shell — no external deps.

## Test data tier (ADR-0010)

Three tiers, three owners, one decision question
("does **every** L1-5 feature need this row before its first setUp?"):

| Tier | Lives in | Owner | Reset / loaded by |
|---|---|---|---|
| **Baseline** | `dandan_server/lib/src/seed/baseline_seed_runner.dart` | F00 only | `make reset-dev-db` |
| **Scenario (per-feature)** | `apps/*/integration_test/_fixtures/<feat>/` | the feature's integration test | per-test setUp / tearDown (Tier B) or import (Tier A) |
| **Dev-playground** | `dandan_server/lib/src/seed/seed_runner.dart` + `factories/admin_seed_factory.dart` | legacy / open-ended | `dart run bin/seed.dart` after baseline (manual dev) |

The `seed-design` skill is loaded by Planner, Generator, and Evaluator —
common vocabulary lives there; role-specific reactions (R8 / I2 / plan
anti-patterns) live in each role's behavior skill. `seed_coverage.py`
is the deterministic sensor that catches drift between
`testContract.l5SmokePath` and the actual seed sources.

Reset discipline: every L5 evaluator drive on student_mobile starts
with `make reset-dev-db` followed by the feature's
`testContract.fixtureRequirements` builders. VM-script route mutations
(`mcp__dart__connect_dart_tooling_daemon` writes) are forbidden — the
evaluation path must mirror what a real user can tap. Violations =
L5 FAIL with `seedDiscoverability: true` (distinct from
`infraBlocked: true`).

See ADR-0010 for the full decision record and `app_docs/test-fixtures.md`
for the per-feature registry.

## Invariants

- **Code is SSoT**, alive docs are derived. Drift is detected by sensors.
- **Sink is deterministic**, not LLM-interpreted. Human approves,
  agent commits.
- **plan.md stays language-neutral**; stack skill renders target syntax.
- **Completed plans live at `specs/completed/{slug}/` forever** — future
  agents read them for historical context.
- **Feature dir barrel is the deep-module interface**. Consumers import
  via barrel; reach-through into `domain/data/presentation/` is banned.
- **Per-feature sink fires on Evaluator PASS** — not attended to batch
  end. Atomic with the feature commit.
- **Test data has three tiers** (ADR-0010): baseline (F00 only), scenario
  (per-feature `_fixtures/`), dev-playground (legacy `seed_runner.dart`).
  Generator R8 forbids non-F00 features from touching baseline; Evaluator
  I2 forbids dirty-DB / VM-route L5 drives.
- **`make reset-dev-db` is mandatory** before any student_mobile L5
  drive. dev DB residue from prior rounds is never trusted.
- **AC has G/W/T body + punctuation discipline** — `requirement.md`
  ACs use single-line header + indented `Given/When/Then` bullets;
  user-facing strings in `"…"`, widget keys in `` `…` ``, negative
  behaviour with `MUST NOT`. This is what `ac_content_gate.py` greps
  for. Legacy single-line ACs are skipped gracefully (not gated).
- **Every R has ≥1 negative AC.** `(negative)`-tagged AC catches
  silent regressions (the user observing what they should NOT see).
  Edge cases are AC entries tagged `(edge)`, not a separate prose
  section.

## Related files

- `docs/decisions/0008-doc-lifecycle-architecture.md` — ADR for this design
- `docs/decisions/0009-language-agnostic-harness.md` — ADR for stack split
- `docs/decisions/0010-test-data-architecture.md` — ADR for the three-tier
  baseline / scenario / dev-playground model
- `CLAUDE.md` — project-level invariants and skill pointers (incl. § Database Roles)
- `app_docs/codemap.md` — current project navigation index
- `app_docs/test-fixtures.md` — ADR-0010 scenario-tier fixture registry
- `.claude/skills/seed-design/SKILL.md` — three-role-shared seed doctrine
- `docs/designs/svg/harness-system.svg` — the system diagram at top

---

## References

The four-stage harness design draws on four external sources. Each row
lists the concept this project borrows and where it shows up in our
architecture.

### 1. Birgitta Böckeler — *Harness engineering for coding agent users*

- Published 2026-04-02 · <https://martinfowler.com/articles/harness-engineering.html>
- Local copy: `~/person_project/Second-Brains/raw/articles/Harness engineering for coding agent users.md`

| Böckeler concept | Where in our harness |
|---|---|
| **Guides (feedforward)** + **Sensors (feedback)** + **Steering loop** — three-layer control | SVG bottom panel. Guides = `docs/glossary.md`, `docs/decisions/*.md`, `learned-anti-patterns`, plan.md `## Test Contracts`, stack skill recipes. Sensors = pre-commit hook, `quality-gate.sh`, `ac_coverage.py`, `ac_content_gate.py`, `/doc-garden`. Steering = `AskUserQuestion` + chat approval. |
| **Computational vs inferential controls** | Computational = `pre-commit-doc-lint.sh`, `plan_lint.py`, `plan_validator.py`, `sink_feature.py`, `ac_content_gate.py` (L3a token presence). Inferential = `/doc-garden` scan, Generator / Evaluator LLM judgment (L3b semantic). |
| **Change-lifecycle vs continuous sensor timing** | Change-lifecycle = pre-commit hook (blocks commit). Continuous = `doc-garden` agent spawned in /finalize Phase 4 (outside the change cycle). |
| "Whenever an issue happens multiple times, improve the feedforward and feedback controls" | Generator failures → remediation hints in retry round. Recurring issues → new `learned-anti-patterns` entry via dreamer agent. |

### 2. Matt Pocock — *It Ain't Broke: Why Software Fundamentals Matter More Than Ever*

- AI Engineer channel, 2026-04-23 · <https://www.youtube.com/watch?v=v4F1gFy-hqg>
- Local transcript: `~/person_project/Second-Brains/raw/youtube/2026-04-24-it-aint-broke-*.md`

| Pocock concept | Where in our harness |
|---|---|
| **Deep modules** (Ousterhout, *A Philosophy of Software Design* Ch.4) — simple interface hiding large implementation; AI navigability collapses in shallow-module codebases | `## Module Boundaries` section in plan.md with `**Public exports**` / `**Internal**` / `**MUST NOT depend on**` fields. Stack skill's `recipes/barrel-materialization.md` renders it into a barrel file with `export` restricting what's public. |
| **Code is SSoT, docs are derived** | Alive docs prioritised by rot-resistance: code-adjacent docs (barrel `/// library`, data-model intent block, API class docstring) beat stand-alone `docs/*.md`. `codemap.md` is scan-derived, not hand-written. |
| **Interface-level docs resist rot best** (compile-time visible) | `sink_feature.py` priority order: `1` model class docs, `2` API class docs, `3` feature barrel, `4` MADR, `5` tech-debt. Higher priority = closer to code = harder to let drift unnoticed. |
| **Gray-box principle**: human designs the interface; AI fills the implementation | Planner writes `## Module Boundaries` (interface). Generator writes code inside (implementation). Sink transcribes interface to code-adjacent docs. |
| **Ubiquitous language as scan-derived glossary** | `docs/glossary.md` + `specs/_batch/glossary-draft.md` merge in /finalize Phase 2 (per-term `AskUserQuestion`). Synonyms-to-avoid become lint errors. |

### 3. Dexter Horthy — *Everything We Got Wrong About Research-Plan-Implement*

- MLOps.community, 2026-03-24 · <https://www.youtube.com/watch?v=YwZR6tc7qYg>
- Local transcript: `~/person_project/Second-Brains/raw/youtube/2026-04-15-everything-we-got-wrong-*.md`

| Horthy concept | Where in our harness |
|---|---|
| **Plan is transient tactical doc for agent consumption, not for human deep review** | `specs/_batch/plan.md` is drain-bucket only; sinks out to alive docs per-feature. After /finalize Phase 3 it moves to `specs/completed/{slug}/` for archive (readable but not the SSoT). |
| **Read code, not plan** | Evaluator runs L5 smoke path against the running app (Playwright / flutter driver / computer-use). Acceptance tests live with code, not plan. |
| **Blindfold research prevents opinion contamination** | `codebase-fact-finder × N` agents spawn without access to requirement.md — they only answer "how does the code work today?" |
| **Design decisions are the real human-review artefact (~200 lines, not 1000-line plans)** | `## Architectural Decisions` block is the subset of plan.md that human inspects carefully at the checkpoint. It sinks to MADR (`docs/decisions/NNNN-*.md`). |
| **Static artefacts for session resume** (don't trust auto-compaction) | Every decision/intent block is a `docs/` file after sink. New agent session starts by reading `docs/decisions/index.md`, `glossary.md`, `feature-list.json` — no reliance on prior conversation memory. |

### 4. Coding Agent Harness Implementations — overview (OpenAI / Stripe / Anthropic / Thoughtworks)

- Local wiki overview: `~/person_project/Second-Brains/wiki/overviews/coding-agent-harness-implementations.md`
- Synthesizes: OpenAI Codex, Stripe Minions, Anthropic long-running builds, Thoughtworks (Böckeler) mental model.

| Borrowed concept | Where in our harness |
|---|---|
| **OpenAI `exec-plans/active/ → completed/`** archive model — completed plans stay in repo forever for agent historical context | `specs/_batch/` → `specs/completed/{slug}/` in /finalize Phase 3, never deleted. |
| **OpenAI recurring doc-gardening agent** — scans for stale rules, auto-opens fix PR | `doc-garden` sub-agent spawned in /finalize Phase 4: scan → trivial auto-fix + non-trivial findings to `tech-debt-tracker.md` → folded into single `chore(finalize):` commit (no PR, local workflow). |
| **OpenAI three-layer rot prevention** — custom linters feed next agent context; doc-gardening removes stale; auto-mergeable PRs | Custom linters: `pre-commit-doc-lint.sh` + `ADR ## Linters` grep. Stale remover: `/doc-garden`. Instead of auto-merge, we do chat-approve. |
| **Stripe "Blueprint": deterministic node vs agent node** — lint and doc-write are deterministic nodes, not LLM calls | `sink_feature.py` is deterministic; so are `plan_lint.py`, `plan_validator.py`, `ac_coverage.py`. LLM only invoked in Generator / Evaluator / Planner. |
| **Stripe "shift feedback left"** — pre-push hooks over CI | `.claude/hooks/pre-commit-doc-lint.sh` blocks at commit time, before push / CI. |
| **Rule files co-located with code** — scoped `AGENTS.md` / `CLAUDE.md` per subdirectory | `.claude/skills/learned-anti-patterns/{serverpod-models,flutter-testing,server-runtime}.md` split by domain. |
| **Thoughtworks change-lifecycle vs continuous sensor split** | Two separate sensor tracks in our SVG bottom panel. |

### Internal record

- `.claude/tmp/doc-lifecycle-research/00-synthesis.md` — detailed synthesis that drove the Q1–Q7 design decisions (gitignored; `.claude/tmp/`).
- `docs/decisions/0008-doc-lifecycle-architecture.md` — ADR locking the three-layer Sink / Rot / Archive design.
- `docs/decisions/0009-language-agnostic-harness.md` — ADR locking the core-vs-stack-skill split.
