# `feature-list.json` Spec

Batch-scope task manifest. The single artefact the generator implements
from and the evaluator verifies against. Every other harness stage
either feeds it (`/prd`, `/plan`) or reads from it (`/execution-loop`,
`/finalize`).

Canonical schema: `.claude/schemas/feature-list.schema.json` (JSON
Schema Draft 2020-12).

---

## Role in the harness

```
/prd grill  ──────►  feature-list.json  ──────►  generator implements
                          │                       │
                          │                       ▼
/plan        ─────────►   │                    codebase
   plan.md                │                       │
   architectural          │                       ▼
   decisions sink         └──────► evaluator (L1-L5 + arch reflection)
   to docs/decisions                              │
                                                  ▼
                                              /finalize
                                                  │
                                                  ├── plan.md → master sinks
                                                  ├── glossary-draft → glossary
                                                  ├── feature-list.json → archive
                                                  │   (specs/completed/{slug}/)
                                                  └── codebase = SSoT for spec
                                                      after archive
```

`feature-list.json` lives only during a batch (at
`specs/_batch/feature-list.json`). On `/finalize` it gets archived to
`specs/completed/{slug}/feature-list.json` for historical context. It
is **never a master** — there is no `docs/feature-list.json`. The
architectural delta produced during the batch flows to master files
through `plan.md`, not through `feature-list.json`.

---

## Top-level shape

```jsonc
{
  "batch_slug":  "<kebab-case>",
  "base_commit": "<git hash>",
  "features": [ <feature>, ... ]
}
```

Two top-level fields plus the feature array. Every feature is a
**vertical slice** — one module, one user-observable outcome,
end-to-end testable.

---

## Field reference

Each row: field → type → purpose → who reads it → who writes it.

### Top level

| Field | Type | Purpose | Read by | Written by |
|---|---|---|---|---|
| `batch_slug` | string (kebab) | Names `specs/completed/{slug}/`; tags master `.history.md` entries | `/finalize` | `/prd` Phase 0 |
| `base_commit` | string (git hash) | Anchors the batch to a commit; sensors detect drift if anyone pushes during the batch | `prd_lint`, evaluator | `/plan` opening |
| `features[]` | array | Vertical slices in this batch | all stages | `/prd` + `/plan` |

### Feature — identity (3)

| Field | Type | Purpose | Notes |
|---|---|---|---|
| `id` | `^F\d{2,3}$` | Greppable identifier | Never reused across batches |
| `name` | kebab-case slug | Human-readable handle | Last segment of `module_path` (under stack case rules) |
| `state` | enum | Lifecycle: `TODO` → `WIP` → `DONE` / `BLOCKED` | DONE = batch verified, not "shipped" |

### Feature — scheduling & linkage (3)

| Field | Type | Purpose | Notes |
|---|---|---|---|
| `priority` | `P1`/`P2`/`P3` | Feature-level severity | P1 blocker, P2 important, P3 nice-to-have |
| `depends_on` | `F##[]` | Same-batch ordering | Cross-batch deps go in `spec.preconditions` |
| `decision_refs` | path[] | Existing ADRs this feature relies on | Reference only — new ADRs come from `plan.md`, not here |

### Feature — placement (1)

| Field | Type | Purpose | Notes |
|---|---|---|---|
| `module_path` | repo-relative dir | Where the feature's code lives | Stack-neutral. `barrel_file` and `public_exports` were intentionally cut — let the codebase be the SSoT for exports |

### Feature — `spec` (4 + nested AC)

| Field | Type | Purpose | Notes |
|---|---|---|---|
| `spec.user_story` | string (10-200) | Cohn form: "As a {role} I {action} so that {value}" | One sentence |
| `spec.preconditions` | string[] | State the feature assumes (Cockburn / Pact `providerState`) | Cross-batch deps live here |
| `spec.business_rules` | string[] | Feature-local rules | Cross-feature rules → `plan.md` ## Architectural Decisions, not here |
| `spec.open_questions` | `<open_question>[]` | Questions raised in /prd grill | Each must declare resolution routing |
| `spec.ac` | `<ac>[]`, 1–10 items | Acceptance criteria — each is one discriminating eval | "10 great evals" cap |

### `open_question` — keystone for master routing

Each open question carries the **resolution routing decision**. This
is what makes "where does the answer live after the batch" machinery
instead of taste.

| Field | Type | Purpose |
|---|---|---|
| `id` | `^Q-\d{2,3}$` | Greppable |
| `question` | string ≥10 | The unresolved question |
| `resolution_kind` | enum | Where the answer goes — see routing below |
| `resolution` | string\|null | The answer text (required non-null when `resolution_kind ≠ deferred`) |

**Routing semantics**:

| `resolution_kind` | Sink target | Lifetime |
|---|---|---|
| `feature_local` | `spec.business_rules` | Dies with batch |
| `architectural` | `plan.md` ## Architectural Decisions → `docs/decisions/NNNN-*.md` | Master, forever |
| `glossary` | `glossary-draft.md` → `docs/glossary.md` | Master, forever |
| `deferred` | (none — carried forward to next batch) | Feature must remain `state: TODO` |

### AC entry (10 sub-fields)

| Field | Type | Purpose |
|---|---|---|
| `id` | `^AC-\d{2,3}$` | Greppable, never reused |
| `title` | string (3-80) | Short headline; appears in test group name |
| `kind` | `positive`/`negative`/`error` | EARS-aligned eval kind |
| `priority` | `P1`/`P2`/`P3` | P1 fail = batch BLOCKED; P2 = retry; P3 = WARN + AskUserQuestion |
| `given` | string ≥5 | Gherkin Given |
| `when` | string ≥5 | Gherkin When |
| `then` | string ≥5 | Gherkin Then. **Must contain `MUST NOT`** when `kind = negative` (schema-enforced) |
| `eval_anchors` | string[] | Literal strings the test file must contain (visible text or test IDs — language-neutral) |
| `must_not` | string[] | Literal strings the test file must **not** contain in the negative scenario. **Required non-empty** when `kind = negative` |
| `example` | string (≤200) | Worked example with real values; helps generator instantiate placeholders |

### `test_contract` (3 fields)

| Field | Type | Purpose |
|---|---|---|
| `l1_command` | string | Static-analysis command (template provided by stack skill) |
| `l2_path` | string | Unit/component test directory the runner targets |
| `l5_smoke_path` | string \| null | E2E smoke test path. `null` = feature does not need L5 (replaces the legacy `needs_l5` bool — one field doing two jobs) |

---

## Validation: schema vs. lint

The schema enforces **structural** rules. A separate lint pass enforces
**content/quality** rules that JSON Schema can't express.

### Schema-enforced (in `feature-list.schema.json`)

- All required fields present, types correct, regex patterns match
- AC count between 1 and 10 per feature
- `state`, `priority`, `kind`, `resolution_kind` are valid enums
- `id`, `name`, `batch_slug` follow regex rules
- `depends_on` items unique
- **Conditional**: when `kind = negative`, `then` must contain `MUST NOT` AND `must_not` array must have ≥1 item
- **Conditional**: when `resolution_kind ≠ deferred`, `resolution` must be a non-empty string

### Lint-enforced (in `prd_lint.py` — to be implemented)

- `base_commit` is a real commit (`git cat-file -e {hash}^{commit}`)
- `depends_on` references real ids in the same batch (no dangling)
- `depends_on` is acyclic (no `F01 → F02 → F01`)
- Each feature has ≥1 AC tagged `kind: negative` (forces "what user MUST NOT see" coverage)
- AC `eval_anchors` arrays for sibling ACs are not identical (forces discriminating evals)
- `module_path` does not collide with another feature's `module_path`
- `decision_refs` paths exist on disk
- `then` clauses do not start with horizontal-layer phrasing ("All endpoints…", "Every form…") — vertical slice rule
- `id` and `AC.id` are sequential within their scope (no gaps)

`architectural_reflection.py` (evaluator step 6 — to be implemented)
verifies the codebase reflects the manifest:

- `module_path` exists
- `l5_smoke_path` exists and was actually run (when non-null)
- Every `eval_anchors` entry appears in some test file under `l2_path`
- Every `must_not` entry does NOT appear in the negative scenario test

---

## Annotated example

A complete, schema-valid example with two ACs (one positive, one
negative) and two open questions (one architectural, one
feature-local).

> **Note**: this example is rendered with Dart/Flutter paths and ADR
> filenames for concreteness. The schema itself is stack-neutral —
> swap the `module_path`, `l1_command`, `l2_path`, and `l5_smoke_path`
> values to whatever the active stack skill produces (TypeScript,
> Rust, Go, etc.) and the validator accepts it identically.

```jsonc
{
  "batch_slug":  "profile-mgmt",
  "base_commit": "abc1234",

  "features": [{
    "id":          "F03",
    "name":        "profile-edit",
    "status":      "todo",
    "priority":    "P2",
    "depends_on":  ["F01"],
    "decision_refs": [
      "docs/decisions/0008-riverpod-state.md",
      "docs/decisions/0012-form-validation.md"
    ],
    "module_path": "apps/student_mobile/lib/features/profile_edit",

    "spec": {
      "user_story": "As a logged-in student I edit my display name and email so my profile reflects my current identity.",

      "preconditions": [
        "user is authenticated (F01 DONE)",
        "user has an existing profile row in DB"
      ],

      "business_rules": [
        "display name 3-20 chars, no leading/trailing whitespace",
        "email format is RFC 5322"
      ],

      "open_questions": [
        {
          "id":              "Q-01",
          "question":        "Email uniqueness: per-tenant or global?",
          "resolution_kind": "architectural",
          "resolution":      "global — confirmed in /prd grill 2026-05-15"
        },
        {
          "id":              "Q-02",
          "question":        "Allow whitespace inside display name (e.g. \"Mary Jane\")?",
          "resolution_kind": "feature_local",
          "resolution":      "yes — single internal whitespace OK; trim edges"
        }
      ],

      "ac": [
        {
          "id":       "AC-01",
          "title":    "save valid changes",
          "kind":     "positive",
          "priority": "P1",
          "given":    "user is on profile edit page with display name \"Bob\"",
          "when":     "user changes display name to \"Alice\" and taps save",
          "then":     "page shows \"Saved\" and profile_saved_banner is visible",
          "eval_anchors": ["Saved", "profile_saved_banner"],
          "must_not":     [],
          "example":      "user_id=42, Bob → Alice"
        },
        {
          "id":       "AC-02",
          "title":    "reject duplicate email",
          "kind":     "negative",
          "priority": "P1",
          "given":    "user is on profile edit page",
          "when":     "user enters email already taken by another user and taps save",
          "then":     "page MUST NOT navigate away and shows \"Email already in use\"",
          "eval_anchors": ["Email already in use"],
          "must_not":     ["Saved", "navigates away"]
        }
      ]
    },

    "test_contract": {
      "l1_command":    "dart analyze apps/student_mobile/lib/features/profile_edit",
      "l2_path":       "apps/student_mobile/test/features/profile_edit/",
      "l5_smoke_path": "apps/student_mobile/integration_test/features/profile_edit_smoke_test.dart"
    }
  }]
}
```

---

## What this schema is NOT

To prevent scope creep — these are deliberate exclusions:

- **Not a master file.** It dies after archive. `docs/decisions/`, `docs/glossary.md`, `docs/tech-debt-tracker.md` are the masters.
- **Not the source for `docs/decisions/`.** `decision_refs` only **points** to existing ADRs. New ADRs originate in `plan.md` ## Architectural Decisions.
- **Not language-specific.** No `barrel_file`, no `public_exports`, no UI-component-vs-text distinction in anchors. Stack skill provides any language-specific rendering at sink time.
- **Not a plan.** `plan.md` carries module boundaries, architectural decisions, cross-R risks. `feature-list.json` carries vertical slices to implement.
- **Not a feature index.** The codebase (and `CODEMAP.md` scan-derived view) is the long-term index of what features exist.

---

## Decisions cross-referenced

The schema embeds these design decisions:

| Decision | Where in schema | Rationale |
|---|---|---|
| AC count ≤ 10 per feature | `ac.maxItems: 10` | "10 great evals" — over 10 = split feature |
| Vertical slice per feature | `module_path` + `l5_smoke_path` span the stack | Horthy: vertical AC, not horizontal layers |
| 3-tier priority (P1/P2/P3) | `feature.priority`, `ac.priority` enums | Industry standard (Linear/Jira), replaces invented `tier` |
| `kind` (positive/negative/error) at AC | `ac.kind` enum | EARS-aligned, replaces `anchors.negative: bool` |
| `eval_anchors` flat (no UI-component/text split) | `ac.eval_anchors` string[] | Language-neutral — UI component identifiers (test IDs, keys, selectors) and visible text collapse into one anchor list regardless of stack |
| `open_questions.resolution_kind` enum | nested in `spec.open_questions[]` | Routes answers to the right master at /finalize |
| No `barrel_file` / `public_exports` | absent | Codebase = SSoT; barrels are JS/TS-isms |
| No `fixture_requirements` | absent | Folded into `preconditions` (human side) + codebase `_fixtures/` (machine side) |

---

## Companion artefacts (next steps in the rebuild)

This schema is step 1 of the rebuild sequence. The following are
queued:

1. **`/plan` and planner skill** — produces `plan.md` (8-section drain bucket) that emits this `feature-list.json`. Stack skill provides language-specific recipes for `## Module Boundaries`, `## Model Intent`, `## Endpoint Intent`.
2. **`/prd` and PRD spec** — interview-driven requirements that feed `/plan` to produce this manifest. Drops `requirement.md × N` in favour of writing into this schema directly.
3. **Generator + Evaluator** — read this schema. Generator implements code from `spec` + `test_contract`. Evaluator runs L1–L5 + new `architectural_reflection.py` step that verifies codebase ↔ manifest alignment.
4. **`/finalize`** — already implemented (`batch-gc` skill); will be updated to route `open_questions[].resolution_kind` to the correct master.

The schema is the contract every later step plugs into. It changes only via explicit ADR (record decision in `docs/decisions/`).
