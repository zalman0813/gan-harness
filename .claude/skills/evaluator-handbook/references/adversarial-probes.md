# Adversarial probes

The discipline: every AC gets at least one probe from one of four
categories, in addition to the happy-path test. Happy-path-only is a
named failure mode (Anthropic Verification Specialist v2.1.89 added
"mandatory adversarial verification protocol requiring at least one
probe per change area" specifically because evaluators were doing
superficial testing).

## The four categories

For each AC, pick the category that fits the AC's surface, run at least
one probe, capture the output as evidence in the eval JSON.

### 1. Boundary values

What changes at the edges of the input domain — empty / single /
maximum / off-by-one / unicode edge / negative / zero?

| AC surface | Probe |
|---|---|
| numeric input | 0, -1, MAX, MAX+1, NaN, ∞ |
| string input | "", " ", "a" * (max+1), unicode (combining marks, RTL, emoji) |
| collection input | [], [single], [N at limit], [N+1 at limit] |
| time input | 1970-01-01, 2038-01-19, leap day, leap second, DST transition |
| pagination | page 0, page out-of-range, page=null |

**Worked example.** AC says: *"display name 3-20 chars"*. Probes:

- 2 chars → expect reject ("Too short")
- 3 chars → expect accept (boundary)
- 20 chars → expect accept (boundary)
- 21 chars → expect reject ("Too long")
- 0 chars / null → expect reject (separate case from "too short")
- "  abc  " (whitespace at edges) → expect either trim-and-accept or
  reject, per the business_rule

If even one of these isn't handled correctly, AC is FAIL.

### 2. Concurrency

What happens under simultaneous access?

| AC surface | Probe |
|---|---|
| same-row update | two clients submit the same edit at once → one wins, other gets a clear error or correct merge |
| counter increment | N parallel +1 calls → final value = start + N (no lost updates) |
| reservation / booking | two users try to book the last slot → one succeeds, one gets "unavailable" |
| toggle action | rapid double-click (e.g. like/unlike) → idempotent or final state matches latest action |

**Worked example.** AC says: *"user can like a post"*. Probes:

- click like 5 times rapidly → like_count delta = +1 (debounced) OR delta
  cleanly tracks each click (per business_rule)
- two users like same post simultaneously → both succeed, count = +2
- like + immediate unlike → final state = unliked, no zombie like

### 3. Idempotency

What happens when the same operation runs twice?

| AC surface | Probe |
|---|---|
| POST a creation | submit same payload twice → either (a) second returns 409/duplicate, or (b) second is no-op returning same id; never two records |
| webhook handler | replay same event → handler runs once-per-event-id |
| email send | retry trigger → user gets at most one email |
| migration / setup | re-run → no errors, no duplicate rows |

**Worked example.** AC says: *"user updates email and gets confirmation
sent"*. Probes:

- click "Save" twice rapidly → either second submit is rejected or
  collapses to one update; user gets at most one confirmation email
- repeat the entire flow next minute → same address, no error, no extra email

### 4. Orphan operations

What happens when the action runs in a malformed context (missing
parent, deleted dependency, stale reference)?

| AC surface | Probe |
|---|---|
| update child of parent | parent deleted between fetch and submit → expect explicit error, not silent NPE |
| delete-cascade | delete parent with children → children handled per spec (cascaded / orphaned with audit / blocked) |
| auth-required action | session expires mid-flow → re-prompt login, do not silently 500 |
| reference id field | submit with id pointing to deleted record → 404 or "not found" surface, not 500 |

**Worked example.** AC says: *"user can edit their profile"*. Probes:

- session expired (delete cookie) → submit edit → expect 401 + redirect, not crash
- user_id in URL belongs to deleted user → expect 404, not 500
- attempt to edit with stale ETag (concurrent edit) → expect 409 or merge prompt

## How to pick a category for an AC

Look at the AC's `kind` and `then` clause:

- `kind: positive`, then-clause is "user does X and sees Y" → run **boundary**
- `kind: negative`, then-clause is "MUST NOT see Y" → run **boundary** (try
  to make the system fall into the forbidden state)
- `kind: error`, then-clause is "system errors gracefully" → run **orphan**
  (force the error condition)
- AC mentions counters, locks, dual writers → also run **concurrency**
- AC mentions external IO (POST, webhook, email) → also run **idempotency**

When in doubt, run two probes from different categories. The AC's
`evidence` field in your eval JSON should name the category and the
specific probe you ran.

## Recording probe results

Every probe goes into the eval JSON's `expectations[].evidence` field as
a one-liner:

```json
{
  "ac_id": "AC-01",
  "text": "user changes display name to 'Alice' and taps save → page shows 'Saved'",
  "passed": true,
  "evidence": "happy: pytest profile_edit_test::test_AC_01 PASS. probe(boundary): name='ab' (2 chars) → 422 'Too short'. probe(boundary): name='a'*21 → 422 'Too long'."
}
```

If a probe revealed a bug the happy-path missed, that AC is FAIL even if
the happy-path test passed:

```json
{
  "ac_id": "AC-01",
  "text": "user changes display name to 'Alice' and taps save → page shows 'Saved'",
  "passed": false,
  "evidence": "happy: PASS. probe(boundary): name='   Alice   ' (whitespace edges) saved without trim — business_rule says trim. test/profile_edit_test.py:42 doesn't cover."
}
```

## What's not here

- L5 / e2e workflow — methodology lives in
  [`e2e-workflow.md`](e2e-workflow.md); stack-specific commands (browser
  driver flags, screenshot syntax, selector idioms) live in the stack's
  e2e tool skill (e.g. `playwright-cli`, `flutter-driver`). The four
  adversarial probe categories above (boundary / concurrency /
  idempotency / orphan) DO apply at L5 — pick one per AC's L5 path
  and execute via the e2e tool.
- Stack-specific probe libraries (hypothesis for Python, fast-check for
  TypeScript) — those live in stack skills.
