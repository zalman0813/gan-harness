---
name: generator-handbook
description: Methodology handbook for the generator agent — sprint contract proposal patterns, strategic-decision rules (refine vs pivot), anti-oscillation discipline, contract amendment heuristics, vertical-slice self-check. Auto-loaded by .claude/agents/generator.md. Use whenever the generator is implementing a sprint inside /loop.
disable-model-invocation: false
---

# generator-handbook

The generator agent's identity and principles live in
`.claude/agents/generator.md`. This handbook holds the **methodology**: how
to propose contracts, when to refine vs pivot, what amendment looks like in
practice.

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

## Strategic decision after evaluator FAIL

Anthropic v2 line 50:

> "I also instructed the generator to make a strategic decision after each
> evaluation: refine the current direction if scores were trending well,
> or pivot to an entirely different aesthetic if the approach wasn't
> working."

### REFINE — when scores trend up

Symptoms:
- Round R-1 had 4 findings, round R has 2 findings, all of round R findings
  are subsets or refinements of R-1 findings
- Same approach is converging
- The current architecture/design is sound, just incomplete

Action: keep the same approach, address the specific findings.

### PIVOT — when scores stagnant or declining

Symptoms:
- Round R-1 had 4 findings, round R has 5 (regression)
- Same finding appearing 3 rounds in a row (mandatory pivot)
- New findings keep appearing in different parts of the system as you fix
  one — sign of a systemic mismatch with the contract

Action: write a one-line decision preamble in your trace:

> "PIVOT: same finding 'auth state lost on refresh' appeared in R1, R2, R3.
> Abandoning Redux + localStorage approach. Trying server-side session
> with httpOnly cookies."

Then implement the new approach from scratch (within the same contract).

### Anti-oscillation: hard rule

If the same finding appears in 3 rounds in a row, you MUST pivot. You may
not refine round 4 on the same approach. This is the only hard rule on
strategic decisions; everything else is judgment.

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

**Refining indefinitely.** The "anti-oscillation" rule exists because
generators get stuck in local minima. 3 rounds same finding = pivot.

**Submitting a contract you intend to amend.** Negotiate honestly the
first time. Frequent amendments = the contract was wrong; rare
amendments = the contract held.

**Gaming the inner gate.** The pre-commit hook is opaque by design. If
commit fails, fix the bug, don't read the hook source to understand
exactly which check tripped.
