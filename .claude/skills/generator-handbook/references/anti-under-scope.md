# Anti-under-scope discipline

The discipline: do not narrow what the planner expanded.

## The temptation

Halfway through a feature you realize the planner's scope is bigger than
you wanted. The tempting move: implement the easy parts, leave the hard
parts as `# TODO`, declare the round done, hope round 2 picks up the
gap.

This is the **under-scoping failure mode** Anthropic documented in their
V2 harness post. When they removed the planner from V1, the generator
reliably under-scoped: started without speccing, shipped narrower than
the prompt asked. The planner came back specifically to fix this.

In gan-harness, the planner has already done the over-scoping work for
you. The feature-list.json's AC list is the deliberately-wide net. Don't
shrink it.

## The rule

If you realize you cannot complete every AC in the feature this round,
the round ends as a fail. Round 2 retries with what you've got committed.
You do **not**:

- Skip an AC and mark the feature DONE
- Implement an AC partially and write a stub for the rest
- Re-interpret an AC's `then` clause to be smaller
- Move an AC to a "future feature" by editing feature-list.json
- Mark a failing test as `.skip` / `xfail` / `it.skip` to make the gate pass

The lifeline if scope is genuinely wrong: surface in your final response
as a request to re-plan. Do not silently shrink.

## Quarantine — the only legal "skip"

If a test fails for reasons you genuinely cannot fix this round
(infrastructure flake, environmental race, third-party API instability),
the only legal path is a **quarantine entry** in
`feature.quarantined_tests[]`. NOT a `.skip` / `xfail` / `it.skip`
silently inserted into the test file.

Quarantine rules:

- Rate limit: ≤ 1 entry per round (harness-loop enforces).
- `quarantine_reason` must be ≥ 10 chars and SPECIFIC. "flaky" alone is
  rejected by schema. Write what you actually saw: "race between
  fixture cleanup and DB connection pool; reproduces ~1/30 runs".
- `expires_after_batch` must be a real future batch slug. Setting it to
  the current batch's own slug as a perpetual escape is the anti-pattern
  this field is designed to defeat: /finalize will refuse archive when
  the current slug matches.
- Adding a quarantine entry consumes the round's rate-limit budget; it
  does NOT extend the 3-round per-feature budget.

If you would have written a `.skip`, write a quarantine entry instead.
If you cannot write a quarantine entry that satisfies the schema (no
specific reason, no real future slug), the test is not flaky — it's
broken, and you must fix it or surface as a re-plan request.

## Worked examples

**Example 1 — three ACs, time pressure.**

F03 has AC-01, AC-02, AC-03. After your design step you estimate AC-03
will take longer than AC-01+02 combined. Tempting: ship 01+02, stub 03,
declare done.

Don't. Implement all three or none. If you genuinely cannot finish AC-03
this round, commit what you have (AC-01+02 only) and the evaluator will
mark FAIL on AC-03. Round 2 picks up. The harness's 3-round budget is
designed for this; don't burn it by claiming false completion.

**Example 2 — AC interpretation drift.**

AC-02 says: *"user uploads a 5MB image → server stores it and returns
url"*. You read the active stack skill and notice it doesn't mention
multipart upload handling. Tempting: re-interpret AC-02 as "endpoint
exists, returns 501 Not Implemented" and PASS the form-field changes.

Don't. The AC says "server stores it and returns url". 501 doesn't store
or return a url. Either implement multipart properly (likely needs an
ADR for `image_storage` since Anthropic V2 cites image-handling as a
recurring failure point), or surface as a re-plan request.

**Example 3 — "this should really be two features".**

You start implementing F03 and realize AC-01+02 are about display and
AC-03 is about API. Splitting into two features feels cleaner.

Don't split. The planner's three-test gate already vetted this. If
F03 should be two features, it's an `open_question` raised in your
final response, not a unilateral edit to feature-list.json.

## Test traceability

Every test you write must reference its AC id. The literal `AC-NN`
(or stack-skill-specific variant like `R03-AC-1`) appears in the test's
function name, group label, docstring, or body. The evaluator
independently re-greps test bodies as part of its grading; missing
literal = AC FAIL.

Comments are stripped before grep, so a `# AC-01 fake` reference will
not pass. The literal must live in code: function name, docstring, or a
real string in the body (e.g., `assert "AC-01" in label`).

Specifically:

```python
def test_AC_01_save_valid_changes(...):
    """AC-01: user changes display name to 'Alice' and taps save."""
    ...
    assert "Saved" in response.text  # eval_anchor literal
    assert_present(page, "profile_saved_banner")  # eval_anchor literal
```

The `eval_anchors` literals must appear in the assertion bodies, not
just in comments. The pre-commit gate's AC-coverage stage strips line
comments before grep, so a literal that lives only in a `# ...` comment
fails the gate.

For `kind: negative` ACs:

```python
def test_AC_02_invalid_email_blocks_save(...):
    """AC-02: invalid email format → save blocked, 'Invalid email' shown.

    must_not literals: 'Saved', 'profile_saved_banner'
    """
    ...
    assert "Invalid email" in response.text
    assert "Saved" not in response.text  # must_not literal
    assert_absent(page, "profile_saved_banner")  # must_not literal
```

The `must_not` literals must each have a `not in` / `findsNothing` /
`assert_absent` assertion paired against the negative scenario. The
pre-commit gate checks the pairing mechanically — a `must_not` literal
in a body without an absence-assertion marker fails the gate.

## Why this discipline matters here

Under-scoping is the #1 documented failure mode for autonomous coding
agents. The harness's defenses against it are: planner widens scope at
/plan time, evaluator enforces the AC list at /execution-loop time, and
generator's prompt + handbook block silent narrowing. All three layers
need to hold.
