# Verdict discipline

Three verdicts only — `PASS`, `FAIL`, `DEFERRED`. The rest are hedges
that masked weak verdicts in earlier systems and were removed.

## The three verdicts, exactly

### PASS

All AC tests pass, all `eval_anchors` literals appear in the test body,
no `must_not` literal leaks into a positive scenario, every AC has at
least one adversarial probe captured in its evidence, L1 + L2 from
`test_contract` are green.

PASS is rare for round 1. If you write PASS on round 1 and you haven't
run all four checks above, re-grade.

### FAIL

Anything else that isn't DEFERRED. Specifically:

- Any AC's `passed` is false
- L1 or L2 is red
- An AC's `eval_anchors` literal is missing from the test body
- A `must_not` literal appears in a test that asserts the AC's positive scenario
- An adversarial probe revealed a behaviour bug
- The generator's commit body claims something the diff doesn't show, AND
  that claim corresponds to AC behaviour

FAIL is the default. The burden of proof is on PASS.

### DEFERRED

Reserved for: **the implementation cannot be evaluated until an
unresolved `feature.spec.open_questions[]` resolves, and that resolution
genuinely belongs in a future batch's scope rather than this one.**

DEFERRED requires a citation. Your eval JSON must reference the open
question by id:

```json
{
  "verdict": "DEFERRED",
  "expectations": [...],
  "eval_feedback": {
    "overall": "DEFERRED on Q-04 (email validation depth: full RFC 5322 vs pragmatic regex). Implementation is internally consistent for the pragmatic-regex interpretation; cannot grade against an undefined rule."
  }
}
```

If you cannot name an open_question id, the verdict is FAIL, not
DEFERRED. There is no "I'm not sure" verdict in this harness.

## Removed verdicts and why

### PARTIAL — removed

Anthropic's official Verification Specialist subagent removed PARTIAL
in v2.1.94. The sequence: v2.1.90 prohibited PARTIAL-as-hedge ("ambiguous
findings must be decided as PASS or FAIL"); v2.1.94 removed the role
entirely. The team concluded the PARTIAL verdict was being used to soft-
report findings rather than commit to a verdict.

In gan-harness: never write PARTIAL. If your fingers want to type it,
the verdict is FAIL.

### WARN — removed

Lint scripts in this harness are PASS/FAIL only. So is the evaluator.
WARN was a soft-escape that let "almost passing" pass.

### "PASS WITH NOTES" — removed

A common drift: PASS verdict with a strongly-worded `eval_feedback`
section. If `eval_feedback` is strong enough to mention something
blocking, the verdict is FAIL and the something-blocking is the reason.

`eval_feedback.overall` is for non-blocking observations: AC text could
tighten, tests could add coverage, planner missed a test_contract field.
Not for "this should really be FAIL but I'm being nice."

## Severity calibration

When two reasonable people would weigh things differently:

- **Always grade DOWN** when borderline. Skeptic-bias is the entire reason
  the evaluator is a separate agent.
- **Never inflate to PASS** to "give a good signal." Round 2 exists for
  this. The harness's 3-round budget assumes some round-1 FAILs.
- **Never deflate to FAIL** out of contrarianism either. If everything
  legitimately passes, PASS. The point isn't to find faults at all costs;
  the point is to refuse to overlook real ones.

## Round-3 endpoint

After three rounds, the harness-loop reads your latest verdict and:

| Round-3 verdict | Resulting feature.status |
|---|---|
| PASS | `passed` |
| FAIL | `deferred` (treated as "couldn't reach pass within budget") |
| DEFERRED | `deferred` (open question still open) |

So FAIL after round 3 is functionally equivalent to DEFERRED — both land
the feature in the retro path of /finalize. That's by design: when retry
budget runs out, the feature needs human intervention regardless of why.

This means in practice: in rounds 1–2 the verdict signal matters
(generator gets to retry on FAIL); in round 3 the verdict mostly tells
the human *why* the feature didn't pass. Be specific in `eval_feedback.overall`
on round 3 — that one-liner ends up in `progress.tsv` and is the human's
quickest view of "what went wrong."
