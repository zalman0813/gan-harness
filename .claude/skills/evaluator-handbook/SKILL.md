---
name: evaluator-handbook
description: Methodology handbook for the evaluator agent — contract review heuristics, behavioral verification patterns, criterion rollup mechanics, threshold check, finding format, transcript-as-evidence reading. Auto-loaded by .claude/agents/evaluator.md. Use whenever evaluator is reviewing a contract draft or running QA on a generator commit.
disable-model-invocation: false
---

# evaluator-handbook

The evaluator agent's identity and principles live in
`.claude/agents/evaluator.md`. This handbook holds the **methodology**:
how to review contract drafts, run behavioral verification, roll up to
criteria, and format findings.

## Two responsibilities

> **Cross-handbook layering.** This handbook covers contract-level
> reviewing and verification mechanics. **Module-level cognition is in
> `deep-module-handbook/references/evaluator-slice.md`** — load that
> slice alongside this handbook when the sprint touches modules.
> NEGOTIATE phase: §1.5 of the slice (markdown feedback with APPROVE /
> REQUEST_CHANGES / REJECT vocabulary). VERIFY phase: §1.6 + §7 of the
> slice (`module_design_verification` array inside the
> `contracts.jsonl` evaluator entry's `findings[]`).

### 1. Contract review (negotiation phase)

When generator proposes a contract draft (typically at
`_pending/S{NN}-draft-v{N}.yaml`), apply six checks before responding.
Checks 1-5 are contract-mechanics; Check 6 is module-level (delegated
to deep-module-handbook).

#### Check 1: Verification depth

Every `done_looks_like` entry must have at least one corresponding
`verification_plan[]` step. If a `done_looks_like` says "user can create
a project" but no playwright or API step exercises that flow, the
contract is incomplete → `amend_request`.

End-to-end coverage: at least one step should be `kind: playwright` for
UI-touching sprints, or `kind: api` for API-touching sprints, exercising
the user-facing behaviour. Unit-test-only contracts are weak signal.

#### Check 2: Mock honesty

Read each `kind: test` step's path. If the test file uses heavy mocking
of internal collaborators, the test asserts against the mock, not against
behaviour. Anthropic v2's lesson: agents who write their own tests skew
positive — mock honesty is your defense.

Heuristic: if `verification_plan` has only `kind: test` entries (no
playwright, no api), and you have any reason to suspect mock-heavy tests,
amend_request to add ≥1 integration or e2e step.

#### Check 3: Criterion coverage

`criterion_mapping` is required to have all 4 spec.md criteria as keys.
Each criterion must map to ≥1 verification step.

If a criterion has no mapping → `reject` (the contract claims to address
that criterion through "vibes"). If a criterion has only weak verification
(unit tests for a Design quality criterion that needs visual judgement)
→ `amend_request`.

#### Check 4: Threshold realism

Default thresholds are aggressive (`all` for must-pass, `>=90%` for tests).
Generator hedging looks like:

- `>=70%` on a critical flow → push back to `>=95%` or `all`
- `>=80%` on the matrix sensor → push back to `all` (matrix sensors are
  binary; partial credit doesn't make sense)
- `>=50%` on anything → contract is acknowledging weakness; amend to
  reduce scope instead

#### Check 5: Scope match

`features_covered[]` must match the features the sprint plan delivers
(read spec.md `## Sprint plan > ### S{NN}` to confirm). If `features_covered`
is missing any F-id from the sprint, reject.

#### Check 6: Deep-module spot-check (delegated)

If the sprint touches modules (not a pure config / docs / data sprint),
**consult** the deep-module-handbook `evaluator-slice.md` §1.5 NEGOTIATE-
phase vocabulary (C1-C8 PASS criteria from foundation §3.5; the visible
§5 red flags; §3 applicability rows). The slice is a **vocabulary
library**, not a walk-every-item checklist — cite only the criteria and
flags that genuinely informed your verdict, and stay silent on items
you didn't analyse.

Output discipline (the parsimony rule):
- **APPROVE on a clean contract** → cite the 2-3 most load-bearing
  PASS criteria (typically C1 + C4 + one of C5/C6/C7), NOT all 8.
  Exhaustive PASS enumeration is bureaucracy disguised as rigour;
  it weakens future readers' ability to spot which criteria you
  actually verified vs pattern-matched.
- **REQUEST_CHANGES** → cite each specific failing criterion or
  red flag with concrete evidence, and the PASS criteria that ARE
  load-bearing for the parts you accept. Don't list silent
  criteria.
- **REJECT** → cite the structural criterion failure that makes
  the contract un-amendable.

Use the slice's APPROVE / REQUEST_CHANGES / REJECT severity vocabulary.
**Do not re-implement the criteria here** — load the slice and use it
as a vocabulary source. Checks 1-5 above are not a substitute for
Check 6; an evaluator that emits APPROVE on Checks 1-5 without
consulting deep-module vocabulary has missed the module-level lens.

#### Output

Write to `_pending/S{NN}-review-v{N}.yaml`:

```yaml
contract_id: C-S03-v1
review_round: 2
verdict: amend_request   # or approve | reject
amendments:
  - check: verification_depth
    point: |
      done_looks_like[2] ("user can edit project metadata") has no
      corresponding verification step. Add a playwright or api step
      that exercises the edit path.
  - check: mock_honesty
    point: |
      vp-03 (kind: test, path: tests/test_project.py) appears to mock
      the database layer. Add a kind: api step that hits the real DB
      to verify edit persists.
narrative: |
  Contract is well-scoped on creation/listing but verification is too
  thin on editing. Amend the two points above and re-propose.
```

### 2. Behavioral verification (post-implementation phase)

After generator commits, you run QA against the agreed contract.

If the sprint touched modules, also run the **VERIFY-phase
deep-module review** per `deep-module-handbook/references/evaluator-slice.md`
§1.6 (three cross-checks per module) and emit a
`module_design_verification` array inside this round's
`contracts.jsonl` evaluator entry's `findings[]` per §7 of that
slice. The 5-checks-then-roll-up loop below covers contract mechanics;
the module-level array is the deep-module dimension that lint and
unit tests can't see.

#### Reading order (locked)

1. `specs/_epic/spec.md` (whole; the rubric)
2. `specs/_epic/contracts.jsonl` (filter: latest agreed contract for
   current sprint)
3. `specs/_epic/_traces/S{NN}-gen-R{N}.jsonl[start:end]` (transcript
   slice; runtime evidence — what the generator actually did)
4. `git diff HEAD~1..HEAD` (the resulting code state)

You may NOT read `.claude/agents/generator.md`. Hook blocks it.

#### Running the verification_plan

Each step in order:

| kind | what to do |
|---|---|
| `playwright` | Open the running app via Playwright MCP / `playwright-cli` skill. Execute every step in order. Assert on every step. Stop on first FAIL. |
| `api` | Send the HTTP request. Validate status, headers, body shape, body semantics. Inspect side effects (DB rows, queue messages) explicitly. |
| `test` | Run the test runner against the path. Don't trust generator's claim that tests pass — re-run. |
| `matrix` | Run each check listed (perf budget, race stress, locale, SCA, secret-scan, mutation kill rate). Each check is binary. |
| `manual` | Apply judgement against the criterion text. Use only for vision/aesthetic checks. Cite the visible evidence. |

#### Roll up to criteria

For each criterion in spec.md:

```python
criterion_passed = all(
    verification_step_passed[vp_id]
    for vp_id in criterion_mapping[criterion_name]
)
```

Sprint PASS = all 4 criteria PASS = `verdict: PASS`.

Otherwise: FAIL with findings (one per failed verification step plus any
criterion-level observations).

## Finding format

Bad finding (vague):
> tests fail

Better finding (Anthropic v2 example):
> **FAIL** — Delete key handler at `LevelEditor.tsx:892` requires both
> `selection` and `selectedEntityId` to be set, but clicking an entity
> only sets `selectedEntityId`. Condition should be `selection ||
> (selectedEntityId && activeLayer === 'entity')`.

Required fields per finding:

```json
{
  "kind": "blocking",
  "vp_id": "vp-02",
  "evidence": "src/auth.py:42 OR _traces/S01-gen-R1.jsonl:L1247-L1289",
  "gap": "<behavioral description, user-facing language>",
  "suggested_fix_hint": "<optional, hint only — never authoritative>"
}
```

`kind` is one of:
- `blocking` — generator must fix this round; sprint cannot complete
- `hint` — won't block this round but will accumulate; if it appears
  again next round it becomes blocking

`gap` is the **authoritative output**. Write it as user-observable
behaviour. "User cannot delete entity by clicking and pressing Delete"
beats "Delete handler condition wrong".

`suggested_fix_hint` is **never authoritative**. Generator may take it,
ignore it, pivot entirely. Hints are for accelerating obvious fixes; for
genuine pivots, hints are noise.

## Output JSON shape

```json
{
  "sprint": "S01",
  "round": 2,
  "contract_id": "C-S01-v1",
  "criteria": [
    { "name": "Design quality",  "passed": true,  "evidence": ["vp-01 PASS"] },
    { "name": "Originality",     "passed": true,  "evidence": ["vp-01 PASS"] },
    { "name": "Craft",           "passed": false, "evidence": ["vp-03 FAIL: missing test for delete path"] },
    { "name": "Functionality",   "passed": false, "evidence": ["vp-01 FAIL at step 7"] }
  ],
  "findings": [
    {
      "kind": "blocking",
      "vp_id": "vp-01",
      "evidence": "_traces/S01-gen-R2.jsonl:L1247 — Playwright step 7 timeout",
      "gap": "User clicks 'Delete' on a project but no confirmation modal appears; deletion silently fails",
      "suggested_fix_hint": "Wire up the existing ConfirmModal component to the delete button"
    },
    {
      "kind": "blocking",
      "vp_id": "vp-03",
      "evidence": "tests/test_project.py:42 — no test for delete_project",
      "gap": "delete_project handler has no test coverage; we cannot prove the audit log entry is written",
      "suggested_fix_hint": "Add test_delete_project_writes_audit"
    }
  ],
  "verdict": "FAIL"
}
```

## Anti-patterns specific to evaluators

**Approving with mock-only verification.** A test suite that's all unit +
mocks tells you nothing about whether the system works. If the contract
slipped through with this, that's your bug — amend it, don't approve.

**"Probably fine" reasoning.** "Tests fail but the failure is in test
infrastructure not the code itself, probably fine." NO. Test infra is
part of the deliverable. Findings cite the failure, generator decides
how to fix.

**Decaying standards.** Round 5 PASS != round 1 PASS. The bar is the
contract, not the generator's effort. If round 5 still fails the
contract, the contract still fails.

**Anchoring on commit message.** The generator's commit body says "all
features implemented". The transcript slice says they only ran tests on
2 of 5 features. Trust the transcript, not the message.

**Over-specifying suggested_fix_hint.** Don't write the fix for the
generator. Hints are accelerators, not solutions. The generator's
strategic-decision (refine vs pivot) needs space to operate.

**Too few findings (false PASS).** When you find one issue, look for
related ones. A failed delete handler likely means: (a) test missing, (b)
audit log missing, (c) keyboard shortcut also broken, (d) error path also
broken. Surface all related findings in one round; don't drip-feed.

**Too many findings (overload).** The generator reads all findings
directly from `_evals/*.json` — there is no MAIN cap. But 30 findings
in one round is still a signal: the contract was too ambitious. Use
`amend_request` to split the sprint instead of dumping the full list
on the next-round generator.
