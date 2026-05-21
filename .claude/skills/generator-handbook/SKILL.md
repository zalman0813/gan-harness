---
name: generator-handbook
description: Methodology handbook for the generator agent — sprint contract proposal patterns, obeying evaluator next_action (refine | restart_sprint | escalate_to_user), contract amendment heuristics, ADR sole-author patterns, vertical-slice self-check. The generator agent must invoke this skill via the Skill tool at the start of every /loop NEGOTIATE or IMPLEMENT round, before proposing a contract or writing code — registered in the agent skills frontmatter but NOT auto-injected, so load it first.
disable-model-invocation: false
---

# generator-handbook

The generator agent's identity and principles live in
`.claude/agents/generator.md`. This handbook holds the **methodology**: how
to propose contracts, how to obey evaluator's `next_action` directive,
what amendment looks like in practice.

## Two phases per sprint: NEGOTIATE then IMPLEMENT

Anthropic v2 frames this clearly: "Before each sprint, the generator and
evaluator negotiated a sprint contract: agreeing on what 'done' looked like
for that chunk of work before any code was written."

> **Cross-handbook layering.** This handbook covers contract-mechanics
> (how to construct done_looks_like / verification_plan / etc.). For
> sprints that touch modules, **also load
> `deep-module-handbook/references/generator-slice.md`** — it adds the
> per-module commitments that go INSIDE `done_looks_like[]` items
> (canonical embedding shape; C1 hides_decision, C4 entry-point budget,
> C5 two-adapter rule, C6 broad interface, optional C3 deletion test,
> recommended C7 sensor in verification_plan). The two handbooks
> compose: this one tells you the OUTER contract shape; the slice
> tells you what to write per module.

### Negotiation deliverable: contract draft

The contract is what gets appended to `contracts.jsonl` after the evaluator
approves. Schema lives at `.claude/schemas/contract.schema.json`. Required
fields when proposing:

- `done_looks_like[]` — 2-7 behavioral statements **plus** one item per
  module touched (per deep-module-handbook generator-slice §1.5
  canonical embedding); the union is your `done_looks_like[]`
- `verification_plan[]` — concrete steps the evaluator will run; for
  non-opt-out modules include a C7 interface-stability sensor of
  `kind: matrix` per generator-slice §1.5
- `criterion_mapping` — maps each of the 4 spec.md criteria to one or more
  verification step ids. **Keys MUST match spec.md `## Evaluation
  criteria` headings verbatim, case-sensitive** — evaluator parses by
  exact match
- `thresholds` — pass thresholds per kind

### How to construct done_looks_like

Read spec.md to find the features the active sprint delivers. For each
feature's user stories, restate as a behavioral outcome:

> User story: "As a user, I want to create a new project with name and
> description"
>
> done_looks_like: "User can create a project via /dashboard with name +
> description, project persists to DB, project appears in dashboard list
> within same session"

Three statements is typical for a normal sprint; up to seven for a complex
sprint. More than seven = sprint is too big, propose splitting via
amendment or reject the sprint plan.

### How to construct verification_plan

Cover every `done_looks_like` entry with at least one verification step,
preferring end-to-end (Playwright) over unit tests.

```yaml
verification_plan:
  - id: vp-01
    kind: playwright
    steps:
      - "Navigate to /dashboard"
      - "Click 'New Project' button"
      - "Fill name = 'Test Project'"
      - "Fill description = 'A test'"
      - "Click 'Create'"
      - "Assert URL is /editor/<some-id>"
      - "Navigate back to /dashboard"
      - "Assert 'Test Project' appears in project list"
  - id: vp-02
    kind: api
    steps:
      - "POST /api/projects with body {name: 'X', description: 'Y'}"
      - "Assert response 201"
      - "Assert response body.id is uuid"
      - "GET /api/projects/<id>"
      - "Assert response body.name == 'X'"
  - id: vp-03
    kind: test
    path: tests/test_project_create.py
  - id: vp-04
    kind: matrix
    checks:
      - "perf:budget"
      - "secret:scan"
      - "mutation:>=0.75"
```

### How to construct criterion_mapping

Each of the 4 criteria from spec.md must have ≥1 verification step
contributing evidence. Example for a frontend archetype:

```yaml
criterion_mapping:
  "Design quality":   ["vp-01"]              # Playwright sees the rendered UI
  "Originality":      ["vp-01"]              # same — visual judgement
  "Craft":            ["vp-03", "vp-04"]     # tests + matrix sensors
  "Functionality":    ["vp-01", "vp-02"]     # end-to-end + API
```

If you can't fill criterion_mapping (some criterion has no plausible
evidence step), the contract is too thin — add more verification steps.

### Threshold defaults

```yaml
thresholds:
  playwright_must_pass: all
  api_must_pass: all
  test_must_pass: ">=90%"
  matrix_must_pass: all
```

Be honest about thresholds. Hedging now means the evaluator will catch
real bugs at QA time and you'll cycle anyway. `>=80%` for a critical flow
is generator hedging; the evaluator will amend back to `all`.

## Obeying evaluator's next_action

You do NOT strategic-decide between refine and pivot. The evaluator
emits `next_action` in `_evals/S{NN}-R{R-1}.json`; you obey it.

### Data source

Read `_evals/S{NN}-R{R-1}.json`. Top-level fields you act on:

- `next_action` — load-bearing directive. One of `proceed` / `refine` /
  `restart_sprint` / `escalate_to_user`.
- `contract_axis.findings[]` and `standards_axis.findings[]` — verbatim
  diagnostic info to consume per the directive.

No MAIN merge, no top-N cap, no axis rerank.

### `next_action: refine`

Keep the same approach. Walk each finding's `gap` field and
`evidence` line range; fix the specific issues named. Preamble in your
trace:

> "REFINE R{R}: addressing finding '<id>' from R{R-1}. Keeping approach
> <approach-name>."

### `next_action: restart_sprint`

Discard the prior round's implementation entirely. Steps:

1. Read `_traces/S{NN}-gen-R{R-1}.jsonl` to enumerate files touched.
2. Revert those files to the sprint-start state (use `git checkout
   <sprint-start-sha> -- <path>` for tracked files; delete newly
   created files).
3. Re-design with a different strategy (different module shape,
   different adapter, different approach to the same `done_looks_like`).
4. Re-implement from scratch.

Preamble in your trace:

> "RESTART R{R}: evaluator ordered restart_sprint. Discarding prior
> approach <name>. New approach: <new-name>. Sprint-start sha: <sha>."

Do NOT carry over the prior round's design assumptions — that defeats
the restart. If you find yourself reusing >50% of the prior round's
code, you haven't actually restarted.

### `next_action: escalate_to_user`

STOP. Do NOT touch code. Write `specs/_epic/_pending/S{NN}-failure-R{R-1}.md`:

```markdown
# S{NN} Failure Report (R{R-1})

## Approaches tried
- R1: <approach name + one-line description>
- R2: <approach name + one-line description>
- R3: ...

## Blocking finding (from _evals/S{NN}-R{R-1}.json)
<copy the blocking finding verbatim — gap + evidence>

## Why this can't be fixed in-loop
<2-3 sentences explaining why refine and restart_sprint won't help —
typically: spec gap requiring epic re-open, or fundamental
incompatibility between spec and current architecture>

## Suggested next step
<one-line: e.g., "Operator decides whether to re-open epic and amend
spec.md ## Cross-cutting constraints > Domain terms" or "Operator
splits this sprint into two">
```

Return the IMPLEMENT escalate output line. Do NOT proceed.

### If you disagree with `next_action`

Surface in the escalate failure report (`escalate_to_user` path). Do
not silently refine after evaluator ordered restart, or restart after
evaluator ordered refine. The evaluator owns this decision; if you
think it's wrong, the operator decides — not you.

## Contract amendment patterns

Amendments are the **exception path**, not default. Most sprints complete
without any amendment. Use amendment only when:

### Legitimate amendment triggers

1. **Spec gap exposed by implementation** — the spec describes a behaviour
   that isn't realisable without an additional piece (e.g., spec says
   "user receives notification" but doesn't say where; you discover the
   notification surface needs a new entity in the data model).

2. **Verification step is impossible** — `vp-02` says "assert race
   condition impossible" but the contract doesn't specify the locking
   mechanism. Amendment proposes adding the locking mechanism to
   done_looks_like.

3. **Threshold mismatch with reality** — perf budget too tight given the
   stack you're on. Propose `>=80%` with justification; evaluator may
   accept or reject.

### Illegitimate amendments (evaluator should reject)

- "I want to drop verification step vp-02 because it's hard." → No.
  Implement harder.
- "I want to lower the threshold so I can ship." → No. The threshold is
  the rubric.
- "I want to remove a feature from features_covered." → That's scope
  reduction, requires escalation to operator (which doesn't exist in
  v3.8 — so write a contract amendment with a clear "spec-level gap"
  reason and let the evaluator decide whether to accept).

### How to write an amendment

```yaml
# _pending/S03-amendment-v2.yaml
contract_id: C-S03-v1   # the existing agreed contract
sprint: S03
proposed_changes:
  - field: verification_plan
    operation: add_step
    new_step:
      id: vp-05
      kind: api
      steps: ["..."]
reason: |
  During implementation, discovered that the email-send pathway has no
  observable side effect from the API surface — the test would only
  succeed if we mock the email service, which is mock-only verification
  (low signal). Adding vp-05 to assert the outbox table state directly
  gives us a real verification path.
evidence_ref: _traces/S03-gen-R1.jsonl:L1247-L1289
```

## Vertical-slice self-check (mandatory pre-implementation)

Before writing the first line of code for a sprint:

1. Does my proposed `verification_plan[]` include at least one
   **end-to-end** check exercising every layer this sprint touches?
2. If verification is entirely unit / integration without any
   user-observable smoke, am I about to ship a horizontal slice?
3. If yes to (2), the spec drew this sprint wrong — propose contract
   amendment that changes scope (add an e2e step, or split the sprint via
   asking the operator), don't silently ship mock-only.

If the spec.md sprint is tagged `(pure-frontend)` etc., the cross-layer
rule doesn't apply — single-layer verification is fine.

## Barrel docstrings (mandatory for every touched package)

When a sprint creates or modifies a Python package — defined as any
directory containing an `__init__.py` — that `__init__.py` MUST contain
a module-level docstring describing the package's responsibility in one
or two sentences. Likewise every `.py` module inside the package needs
its own module-level docstring.

```python
# onboarding/__init__.py
"""Option B onboarding pipeline — snapshot a source table, Bedrock-
batch-embed the rows, load vectors, and attach the runtime CDC trigger.
"""
```

```python
# onboarding/snapshot.py
"""Snapshot a source table to Bedrock batch-inference JSONL. Hides
cursor-batch sizing and the Bedrock input record format."""

def snapshot_table(conn, catalog_row, output_path):
    ...
```

### Why this is non-negotiable

`/finalize`'s `regen_codemap.py` (deep-module-handbook companion at
the epic-close boundary) walks every `__init__.py` to rebuild
`CODEMAP.md` deterministically. When a barrel docstring is missing, the
script can't invent one without surprising the operator, so it writes
`_(no barrel docstring — add one to surface this module)_` instead.
That cell shows up in the next epic's planner context, advertising that
nobody owns the module's purpose — which is the wrong default for code
we just shipped.

The same rule applies to sibling `.py` modules: missing docstring →
`_(no module docstring)_` in CODEMAP.md. Three rounds of evidence from
the Apollo epic (handoff D1/D2) showed that absent docstrings cause the
LLM to back-fill from filenames; barrel + module docstrings are the
cheapest place to plant the truth.

### What a useful docstring contains

- The **decision the module hides** (one phrase — see deep-module
  C1 named-hidden-decision).
- The **public entry-point names**, only if it helps a reader who lands
  in the file without grep context.

Two sentences max. The docstring is read by the operator AND by
`regen_codemap.py`'s `short_docstring()`, which truncates at the first
blank line, so put the headline in the first paragraph.

## Inner gate (commit-time discipline)

The active stack skill specifies the inner gate. Typical Python stack:

```
gate_gen_precommit.py:
  lint.fix     → ruff format
  lint.check   → ruff check
  typecheck    → mypy --strict
  unit tests   → pytest -m "not e2e"
  ac coverage  → grep verification_step ids in test files (literal pres)
  module ACL   → import boundaries match module_design
```

Any RED → don't commit. Read the failing tool's stderr; fix the bug;
re-stage; re-commit. **Never** `git commit --no-verify`.

## Three-strikes stop rule (still applies, no escalate alternative)

If the same gate stage FAILs three times in a row on the same item (same
verification_step ids three commits in a row, same typecheck error after
three fixes), STOP retrying within this round. Accumulated session
context degrades faster than incremental fixes converge. Emit a brief
final response naming the stuck point (which step / which file / what
you tried), then return without commit.

The evaluator at QA time will surface the bug as a finding; round R+1
with fresh context is the legitimate next step.

## Common pitfalls

**Implementing before contract is agreed.** Wasted work. The contract may
amend such that your implementation no longer fits.

**Stub-and-commit.** `raise NotImplementedError` in impl + happy-path
test. Inner gate may pass on literal coverage; evaluator's behavioral
verification trips it. Don't ship stubs.

**Overriding evaluator's next_action.** Evaluator owns the pivot
decision. If you silently refine when evaluator said restart_sprint,
or restart when evaluator said refine, you're breaking the harness
authority chain. If you disagree, surface in the escalate failure
report — operator decides, not you.

**Submitting a contract you intend to amend.** Negotiate honestly the
first time. Frequent amendments = the contract was wrong; rare
amendments = the contract held.

**Gaming the inner gate.** The pre-commit hook is opaque by design. If
commit fails, fix the bug, don't read the hook source to understand
exactly which check tripped.
