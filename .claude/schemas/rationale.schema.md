# commit-rationale schema (v3.8)

**Status**: contract for `specs/_epic/_pending/S{NN}-commit-R{R}-rationale.yaml`.
**Lifecycle**: written by generator before each IMPLEMENT commit; read by evaluator at VERIFY time.

This file forces the generator to articulate **what evidence backs each `outer_gate` step** before commit, instead of post-hoc rationalisation. The anchor ledger + divergence diff scripts cross-check the rationale against actual diff + traces. (The `inner_gate` is hermetic lint/typecheck/unit/smoke — it needs no per-step anchor; its result lives in the inner-gate artifact.)

---

## Required structure

```yaml
contract_id: C-S{NN}-v{R}
sprint: S{NN}
round: {R}
outer_gate_evidence:
  - og_step: og-01
    evidence_file: tests/e2e/test_login.py
    evidence_lines: "42-58"
    anchor_used: "user enters email and sees confirmation"
    anchor_verified_at: "spec.md:142"
  - og_step: og-02
    evidence_file: src/api/forgot_password.py
    evidence_lines: "15-30"
    anchor_used: "user submits forgot-password form"
    anchor_verified_at: "spec.md:144"
new_anchors_introduced: []  # if non-empty, each must justify why anchor source extension was needed
deviations_from_contract: []  # if non-empty, each must explain what changed and why
```

## Field rules

- `contract_id` — verbatim from the active `phase: agreed` contract.
- `sprint` / `round` — match the active sprint/round.
- `outer_gate_evidence[]` — one entry per `outer_gate` step in the contract; missing entries = generator did not exercise that step.
  - `og_step` — `outer_gate` step id from contract.
  - `evidence_file` — file:line range where the test or check lives.
  - `evidence_lines` — `<start>-<end>` line range string.
  - `anchor_used` — the literal user-language phrase from spec.md / research / intent the step verifies.
  - `anchor_verified_at` — file:line in the anchor source.
- `new_anchors_introduced[]` — list of anchors the generator added during IMPLEMENT that were NOT in the agreed contract. Should be empty in the common case. Non-empty requires a `reason` per entry.
- `deviations_from_contract[]` — list of contract fields the generator did not fully satisfy. Should be empty in the common case.

## Why this exists

Without forced pre-commit rationale, generator's reasoning becomes
post-hoc rationalisation — written after the code is decided. Forcing
the rationale BEFORE the commit ties each `outer_gate` step to its
evidence and surfaces un-anchored claims to evaluator and to anchor_ledger.py.

## Related scripts

- `.claude/skills/harness-loop/scripts/anchor_ledger.py` — verifies each `anchor_used` against approved sources.
- `.claude/skills/harness-loop/scripts/divergence_diff.py` — lists new identifiers in the round's diff vs anchor sources.
