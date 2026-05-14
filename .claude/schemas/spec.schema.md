# spec.md schema (v3.8)

**Status**: contract for `specs/_epic/spec.md`. Validated by `spec_lint.py`.
**Lifecycle**: written once at `/init`; immutable through `/loop`; archived to `specs/epics/<slug>/spec.md` at `/finalize`.

This schema defines the **required structure** of an epic's spec.md. The planner agent produces a file conforming to this contract. The spec_lint.py script enforces every rule below at write time and pre-commit.

---

## Required top-level structure

```markdown
# Spec — <epic-slug>

## Vision
## Tech stack
## Archetype
## Features
## Sprint plan
## Evaluation criteria
## Cross-cutting constraints
## Overall success criteria
## References
```

All H2 sections above MUST appear, in this order. No other top-level H2 is permitted.

---

## Section schemas

### `# Spec — <epic-slug>` (H1, exactly one)

- `<epic-slug>` matches `^[a-z0-9][a-z0-9-]{0,39}$`
- This is also the directory name when archived (`specs/epics/<epic-slug>/`)

### `## Vision`

- Free-form prose, **2-4 sentences**.
- States: what this epic produces, who uses it, why now.
- No bullet lists, no headings deeper than this section.

### `## Tech stack`

- Bulleted list. One bullet per layer.
- Each bullet: `- <Layer>: <stack skill name or "n/a">` where stack skill name matches an existing `.claude/skills/<name>/` (or `n/a` if not applicable).
- Recommended layers: `Frontend`, `Backend`, `Database`, `Infra`, `Test runner`.

### `## Archetype`

- Single line, one of: `frontend`, `backend`, `library`, `cli`, `data-pipeline`, `hybrid`.
- Drives the default 4 evaluation criteria template (see `## Evaluation criteria`).

### `## Features`

Each feature is an `### F{NN} — <name>` H3 block with three or four required sub-fields:

```markdown
### F01 — Project Dashboard
**Sprint**: S01
**User stories**: As a user, I want to:
- Create a new project with a name and description
- See all my existing projects displayed as visual cards
- ...
**Data model** (only if archetype demands persistent state):
- Project { name: str, description: str, created_at: datetime, ... }
```

Rules:
- `F` followed by 2-3 digit zero-padded id, monotonically increasing within a spec (F01, F02, F03 — not F1, F02, F4)
- `<name>` must NOT contain phase markers: `backend`, `frontend`, `api layer`, `database layer`, `phase 1`, `phase 2`, `infrastructure`, `scaffolding`, `setup` (lint L02)
- `**Sprint**` references a sprint defined in `## Sprint plan` (lint L01)
- `**User stories**` uses the Cohn pattern: `As a <role>, I want to:` followed by bullet list. Each bullet is a complete user-observable goal.
- `**Data model**` is required for `archetype: backend | data-pipeline | hybrid`; optional otherwise

### `## Sprint plan`

Each sprint is an `### S{NN} — <name>` H3 block with three required sub-fields:

```markdown
### S01 — Project foundation + dashboard
- Delivers: F01
- Depends on: (none)
- Smoke check: User can navigate to the dashboard, create a project, and see it persist after page reload.
```

Rules:
- `S` followed by 2 digit zero-padded id, monotonically increasing
- `Delivers:` lists ≥1 F-id; the union of all sprint Delivers MUST exactly cover all F-ids in `## Features` (lint L01)
- `Depends on:` is `(none)` or a comma-separated list of S-ids that must complete before this sprint starts
- `Smoke check:` MUST start with a user-observable verb phrase: `user can`, `user sees`, `system shows`, `user receives`, `user navigates`, etc. (lint L04)
- Smoke check MUST NOT be `code compiles`, `tests pass`, `lint clean` (those are mechanical, not user-observable) (lint L04)
- A sprint that only delivers single-layer features (UI-only, backend-only, lib-only) MUST be tagged with one of `(pure-frontend)`, `(pure-backend)`, `(pure-lib)`, `(pure-cli)`, `(pure-data)` after the sprint name, OR provide `Reason for single-layer:` line. Otherwise the sprint must touch ≥2 layers (lint L05)

### `## Evaluation criteria`

Exactly 4 numbered criteria pulled from the archetype's template (see `archetypes/` references). Planner MAY reword for the specific epic but MUST keep 4 entries (lint L07).

Default templates (planner picks one matching `## Archetype`):

**frontend / hybrid (UI-prominent)**
1. **Design quality** — coherent visual identity, mood, distinct
2. **Originality** — custom decisions vs library defaults vs AI slop
3. **Craft** — typography, spacing, contrast, technical fundamentals
4. **Functionality** — usability independent of aesthetics

**backend**
1. **API design quality** — RESTful or RPC consistency, naming, versioning, documentation
2. **Robustness** — error handling, edge cases, idempotency, retry semantics
3. **Craft** — code structure, type safety, observability, test coverage
4. **Functionality** — endpoints work end-to-end, contracts honored, integrations correct

**library**
1. **Interface design** — minimal surface, deep modules, pit-of-success defaults
2. **Originality** — thoughtful defaults vs scaffolded noise
3. **Craft** — API stability, error types, docstring completeness
4. **Functionality** — examples work, edge cases handled, semantic versioning honored

**cli**
1. **UX quality** — helpful errors, consistent flag style, --help readability
2. **Robustness** — works in pipelines, signal handling, exit codes
3. **Craft** — code structure, subcommand organization, test coverage
4. **Functionality** — subcommands work, end-to-end flows reliable

**data-pipeline**
1. **Correctness** — output invariants hold, schema match, deterministic
2. **Robustness** — idempotency, restart safety, error budget, observable
3. **Craft** — modular stages, structured logging, lineage tracking
4. **Functionality** — produces expected output for known input fixtures

### `## Cross-cutting constraints`

Bulleted list. Optional sub-headings allowed (e.g., `### Performance budget`, `### Design language`, `### Non-goals`). Items are constraints that apply to the whole epic, not a single sprint.

One sub-heading is reserved for /finalize consumption:

#### `### Domain terms` (optional)

When the epic introduces domain vocabulary that does NOT yet exist in
`CONTEXT.md`, list the new terms here. /finalize parses this block and
appends each new term to `CONTEXT.md`'s `## Language` section
(idempotently — terms already present are skipped). Format is strict —
the merge script is regex-only and refuses to guess.

Every entry must follow:

```markdown
### Domain terms
- **<term>** — <one-line definition>
- **<term-with-context>** — <definition that may span multiple lines, as
  long as continuation lines start with two spaces of indentation>
```

Rules (enforced by lint L08):
- Heading is exactly `### Domain terms` (no parenthetical suffix like `(draft)`)
- Every line under the heading until the next H2/H3 is either a `- **term** — definition` bullet, a 2-space continuation of the previous bullet, or blank
- `<term>` is the bold key — uniqueness within this section
- `—` is the em-dash separator (U+2014); the parser also accepts ` -- ` (two hyphens) as a fallback for keyboards that produce it

If the epic introduces no new terms, omit the sub-heading entirely.

### `## Overall success criteria`

Numbered list, **3-7 items**. Each item MUST be:
- Behavioral (something a user or test can observe)
- End-to-end (touches the user's actual workflow, not internal mechanics)
- At least one item must explicitly walk through a complete user flow (lint L06)

Examples (good):
1. A new user can sign up, create a project, edit it, and share a link to it within 5 minutes of first visit.
2. The exported game runs in any modern browser without external dependencies.

Examples (bad — fail lint L06):
1. ~~All features pass type-check.~~ (mechanical, not behavioral)
2. ~~Coverage exceeds 80%.~~ (mechanical)

### `## References`

Bulleted list of links to existing project artifacts the planner consulted. Common entries:
- `CONTEXT.md (existing domain language)`
- `ADR-NNNN: <title>` (one bullet per accepted ADR the spec respects)
- `specs/_epic/_research/<query-id>.md` (if fact-finder ran)
- `specs/epics/<previous-slug>/spec.md` (if this epic builds on a previous one)

References are **read-only context for downstream agents**. The spec itself does not duplicate their content.

---

## Lint rules summary (executed by `spec_lint.py`)

| ID | Rule |
|---|---|
| L01 | All H2 sections present in correct order; every F-id covered by exactly one sprint Delivers |
| L02 | Feature names contain no phase markers |
| L03 | Every sprint has Delivers + Depends on + Smoke check |
| L04 | Smoke check starts with user-observable verb; not mechanical |
| L05 | Sprint deliverables touch ≥2 layers OR are explicitly tagged pure-* |
| L06 | Overall success criteria has ≥1 end-to-end behavioral entry |
| L07 | Archetype is set; Evaluation criteria block has exactly 4 numbered entries |
| L08 | If `### Domain terms` appears under `## Cross-cutting constraints`, every bullet matches `- **<term>** — <definition>` (continuation lines allowed with 2-space indent) and `<term>` is unique within the section |

---

## Examples

A minimal valid spec (a 2-feature CLI tool epic):

```markdown
# Spec — kvstore-cli

## Vision
A small kv-store CLI for developers to inspect and edit JSON-backed local config files. Used in shell scripts and ad-hoc debugging where opening an editor is overkill.

## Tech stack
- Backend: python-stdlib
- Test runner: pytest

## Archetype
cli

## Features
### F01 — Get and set
**Sprint**: S01
**User stories**: As a developer, I want to:
- Run `kvstore get foo.bar` and see the value at that key path
- Run `kvstore set foo.bar=42` and have the change persist to the JSON file

### F02 — Atomic transaction
**Sprint**: S02
**User stories**: As a developer, I want to:
- Run `kvstore tx file.json -- get a; set b=2` and have all operations apply atomically (or none)

## Sprint plan
### S01 — Single-key read/write
- Delivers: F01
- Depends on: (none)
- Smoke check: User runs `kvstore set count=5` then `kvstore get count` and sees `5`.

### S02 — Transactional batch
- Delivers: F02
- Depends on: S01
- Smoke check: User runs a tx that writes two keys, with one operation invalid; user sees neither key persists.

## Evaluation criteria
1. UX quality — error messages name the offending key path; --help is one screen
2. Robustness — concurrent runs don't corrupt the file; SIGINT mid-tx leaves file intact
3. Craft — subcommand parser is consistent across `get`/`set`/`tx`; ≥80% test coverage
4. Functionality — every documented subcommand works end-to-end against a real JSON fixture

## Cross-cutting constraints
- Non-goals: GUI, network sync, schema validation
- Performance: a single get/set must complete in <50ms on a 1MB file

## Overall success criteria
1. A developer can install the CLI, run `kvstore get foo.bar` against an existing JSON file, and see the value within one minute of install.
2. A developer running `kvstore tx ... -- set a=1; set b=invalid_json` sees the entire transaction roll back; the file is unchanged.
3. The tool has zero external runtime dependencies (pure stdlib).

## References
- CONTEXT.md
- (no prior epics)
```
