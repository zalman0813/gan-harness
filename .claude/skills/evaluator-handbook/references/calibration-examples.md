# Calibration examples

Anthropic's harness post: "I calibrated the evaluator using few-shot
examples with detailed score breakdowns. This ensured the evaluator's
judgment aligned with my preferences, and reduced score drift across
iterations."

Below are five worked cases. Read them once at the start of an
evaluation; re-read whenever a specific case feels borderline.

The pattern is:

1. **Setup** — what the AC says and what the generator did
2. **Naive evaluator's instinct** — the wrong call you might be tempted to make
3. **Calibrated verdict** — what you should write
4. **Why** — the calibration principle

---

## Example 1 — happy path passes, AC literal missing

**Setup.** AC-01: *"user changes display name to 'Alice' and taps save →
page shows 'Saved'"*. `eval_anchors: ["Saved", "profile_saved_banner"]`.
Generator's test asserts `assert "name updated successfully" in
response.text`.

**Naive instinct.** Test passes; the user-facing message conveys success;
PASS.

**Calibrated verdict.** FAIL.

```json
{
  "ac_id": "AC-01",
  "passed": false,
  "evidence": "Test asserts 'name updated successfully' but eval_anchor 'Saved' is the literal contract. Anchor not present in any test body or in the rendered response. AC says 'page shows Saved'."
}
```

**Why.** `eval_anchors` is the contract, not the spirit. If the team wants
"name updated successfully" instead, the AC should change at /plan time, not
silently at /execution-loop time. Approving here normalises drift between
AC text and rendered text — over batches that drift compounds.

---

## Example 2 — generator commit message overstates

**Setup.** AC-02: *"user uploads JPEG → server stores it"*. Commit body
says: *"AC-02: implemented full upload pipeline with virus scanning, EXIF
stripping, and CDN replication."* Git diff: 8 lines that POST to S3 with
no scanning, stripping, or replication code.

**Naive instinct.** S3 upload works in the test; commit's other claims
are nice-to-haves; PASS.

**Calibrated verdict.** PASS on the AC, **but** populate `claims[]` with
unverified-claim entries:

```json
{
  "expectations": [{
    "ac_id": "AC-02",
    "passed": true,
    "evidence": "test/upload_test.py::test_AC_02 PASS. probe(boundary): 0-byte file → 422; probe(boundary): 50MB → 413."
  }],
  "claims": [
    {"claim": "virus scanning", "verified": false, "evidence": "no scanning code in diff; AC-02 doesn't mention scanning"},
    {"claim": "EXIF stripping", "verified": false, "evidence": "no PIL/exiftool/sharp call in diff"},
    {"claim": "CDN replication", "verified": false, "evidence": "single PUT to S3 only; no CloudFront invalidation"}
  ],
  "eval_feedback": {
    "overall": "AC-02 passes on its narrow contract. Generator commit body overstates by ~3 features that aren't required and aren't implemented — flagged in claims[] for /finalize awareness."
  }
}
```

**Why.** The AC is the contract; the AC passed. But `claims[]` is the
hostile-evaluator channel — when the generator says it did X and X
isn't in the diff, that's evidence either of (a) generator over-claiming,
or (b) silent scope expansion that AC didn't cover. Either way it
matters. Don't bury it; record it. Future planners reading
`progress.tsv` + claims will tighten AC text.

---

## Example 3 — happy path passes, no adversarial probe

**Setup.** AC-01: *"display name 3-20 chars"*. Generator's test only
asserts the happy path: name="Alice" (5 chars) saves successfully. No
probe at the 2-char or 21-char boundary.

**Naive instinct.** AC's `then` is satisfied; PASS.

**Calibrated verdict.** FAIL.

```json
{
  "ac_id": "AC-01",
  "passed": false,
  "evidence": "Happy path: name='Alice' saves and 'Saved' renders — confirmed. Adversarial probe missing: no test for 2-char (rejected per business_rule), 21-char (rejected per business_rule), or 0-char/null. Run my own probe: name='ab' → 200 saved (BUG, should reject). Test gap + behaviour bug."
}
```

**Why.** Happy-path-only verification is the named failure mode. ≥1
adversarial probe per AC is doctrine. The probe surfaced a real bug
the test would have caught — that's exactly what probes are for.

---

## Example 4 — borderline DEFERRED vs FAIL

**Setup.** AC-03 depends on `business_rule: "email format is RFC 5322"`.
The generator's implementation uses a simple regex that handles common
cases but rejects obscure-but-RFC-valid forms (e.g. `"local"@example.com`
with quoted local-parts).

**Naive instinct.** RFC 5322 is the rule; regex doesn't fully implement
it; FAIL.

**Or alternatively:** RFC 5322 is famously almost-unimplementable; what
exists is "good enough"; DEFERRED with note about open question on email
validation depth.

**Calibrated verdict.** Check `feature.spec.open_questions[]`. If there's
an open question pointing to "email validation depth", DEFERRED is
legitimate:

```json
{
  "ac_id": "AC-03",
  "passed": false,
  "evidence": "Regex handles 99% of real emails per common patterns. Quoted local-parts and IP-literal hosts rejected. spec.open_questions[Q-04] flags this exact ambiguity ('full RFC 5322 vs pragmatic regex?'). Cannot give a non-arbitrary verdict until Q-04 resolves."
}
```

And the round verdict is `DEFERRED` with feature.status → `deferred`.

If there's NO open_question, the verdict is `FAIL`:

```json
{
  "ac_id": "AC-03",
  "passed": false,
  "evidence": "business_rule says 'RFC 5322'. Implementation rejects valid quoted local-parts. No open_question covers this — the rule is unambiguous, the implementation is wrong."
}
```

**Why.** DEFERRED is reserved for "the rule itself is open". When the
rule is closed and the impl violates it, FAIL. Don't conflate "this is
hard" with "this is undefined".

---

## Example 5 — test passes but L1 fails

**Setup.** All AC tests pass; `test_contract.l1_command` (e.g.
`mypy --strict .`) reports 3 type errors in the new code.

**Naive instinct.** Tests cover behaviour; types are stylistic; PASS
with note.

**Calibrated verdict.** FAIL.

```json
{
  "ac_id": "AC-01",
  "passed": false,
  "evidence": "AC behaviour test PASS. L1 (mypy --strict) FAIL: 3 errors at services/profile.py:42, :58, :73. Type check is L1 of the test_contract — explicit gate, not advisory."
}
```

Or, if AC tests pass cleanly but L1 fails, you can structure the JSON
verdict as one consolidated FAIL on the round (not duplicating the L1
errors per-AC):

```json
{
  "verdict": "FAIL",
  "expectations": [...],
  "summary": {"passed": 3, "failed": 0, "total": 3},
  "eval_feedback": {
    "overall": "All AC behaviour PASS. Round FAIL on L1: mypy --strict reported 3 errors. Fix at services/profile.py:42 (Optional missing), :58 (Any leak), :73 (return type)."
  }
}
```

**Why.** `test_contract.l1_command` is part of the contract. If the
team wanted to allow type errors, mypy wouldn't be in `l1_command`. The
contract is binary; "almost passing" doesn't pass.

---

## Drift-detection: things to watch in your own grading

If you find yourself doing any of these, re-read the calibration line at
the top of `evaluator.md` and re-grade:

- "The behaviour is right, just the literal differs" → FAIL (Example 1)
- "The generator probably meant to do X" → ignore intent, grade output
- "This is a small thing in a big feature" → priorities are spec-defined
- "I'll PASS but write strong eval_feedback" → if it's strong enough to
  flag, it's strong enough to FAIL on
- "DEFERRED feels nicer than FAIL here" → check Example 4; only when an
  open_question exists
