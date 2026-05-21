# REVIEW_CONTRACT adverse-coverage gate — why the 7th check exists

> Maintainer-facing design memo. **Not loaded at runtime by any agent,
> skill, or hook.** Not referenced from any copied worker file by design —
> `.claude/agents/evaluator.md` is self-contained and states the rule in
> its own voice. This memo records the forensic that motivated the rule
> and the candidate fixes that were deliberately NOT applied.

## Trigger

An operator built a Manus-style agent app (Apollo) by copying a known-good
hand-written reference (`sample-strands-agent-with-agentcore`). Despite the
reference handling them correctly, Apollo shipped three operator-confirmed
defects in the browser-use surface:

- **A — live-view freeze + "Authentication failed: Failed to communicate
  with server" + stale Canvas**: DCV live-view had only a blind 240 s
  re-mint timer, zero event-driven reconnect. The blind teardown+re-auth
  on a fresh presigned URL was itself the auth-error trigger.
- **B — Canvas/artifact truncated, user must zoom the browser out**: no
  `viewport` meta export + a `vw`-clamped pane with a px floor.
- **C — conversation is a run-on wall, messages overlap**: flat
  `content+toolCalls[]` model discards text↔tool interleave order; the
  bubble re-runs its enter animation every stream tick.

All three are divergences FROM the reference, not inherited from it. None
were caught by any contract criterion or evaluator verdict; two
(S06 R1/R3) were false-PASSed and only an out-of-band operator live-test
reopened them.

## Forensic verdict

Primary cause is **(b) thin context/concept design**, not (a) low
adherence. The agents follow their prompts; the prompts never demand
failure-mode-observable criteria or reference-sample fidelity, so a
literal, happy-path, single-viewport, noun-satisfying implementation
**legitimately passes every gate**.

Load-bearing evidence (quoted in the full forensic, summarised here):

- `planner.md` forbids granular AC and pushes failure modes to "sprint
  contract negotiation"; the Smoke-check allow-list is all happy-path
  verbs (no `survives`/`recovers`/`reconnects`).
- The archetype evaluation-criteria templates for `frontend`/`hybrid`
  have no resilience axis (it exists only for backend/cli/data); the
  planner must pick exactly those and drop none.
- For Defect B the correct behaviour was affirmatively scoped OUT —
  Apollo `spec.md` Non-goals: "Mobile / responsive layouts — desktop web
  only". No verification can catch a defect the spec excludes.
- `contract.schema.json` requires no adverse-condition / fidelity field;
  a 100 %-happy-path verification_plan is schema-valid and
  evaluator-approvable.
- The evaluator rollup is contract-bounded by explicit instruction
  ("QA reads the contract, not spec"), so a thin contract yields a
  passing thin verdict with the evaluator fully obedient.

Secondary cause **(c) verification-gap** applies to Defect A
specifically: S06 R1/R3 accepted proxy evidence (synthetic URL;
CDP-mocked unit tests; an on-disk PNG from a non-representative path)
that structurally cannot exercise the real `connect_over_cdp` runtime.

The string "reference sample" / "parity" / "golden" appears nowhere in
`planner.md`, `spec.schema.md`, `evaluator.md`, or the handbooks. The
harness has no concept of "match the sample" even when the user copied one.

## Candidate fixes considered

1. **evaluator REVIEW_CONTRACT gains an adverse-condition check** —
   reject a draft whose verification_plan is all-happy-path / mock-only /
   proxy-evidence for a non-structural sprint. Moves the guardrail to
   contract-negotiation time, the only place the harness had none.
   Reuses the existing, well-enforced skeptical-evaluator machinery.
   Lowest churn (one prompt, one new check).
2. `contract.schema.json` — add a required `adverse_conditions[]` to
   `done_looks_like`/`verification_step`; `spec_lint` analog rejects an
   all-happy-path plan for non-`pure-*` sprints.
3. `spec.schema.md` / planner-handbook archetype templates — add a
   non-droppable resilience/fidelity criterion to the `frontend`/`hybrid`
   template; change planner "exactly 4, drop none" to "≥4 incl. one
   resilience-class".
4. `spec.schema.md` `## References` — add an optional `## Reference
   fidelity` block; when the user supplies a reference sample the planner
   records it and the evaluator standards axis gains a `reference:parity`
   sensor.

## Decision

**Applied #1 only** (operator-chosen: "doc + minimal gate fix"). Added a
7th REVIEW_CONTRACT check, `adverse_coverage`, to
`.claude/agents/evaluator.md` (heading "Seven checks", new amendment
enum token, the two checklist counters bumped 6→7). The rule is stated
self-contained and rules-only in the prompt; this memo holds the why.

Rationale for #1 over #2–#4: it is the single highest-leverage,
lowest-churn edit. The forensic showed the structural hole is that
*nothing fires before a thin contract is frozen*; #1 closes exactly that
point using machinery the harness already enforces well, without
re-touching planner, schema, or the archetype templates (which would
need a full /loop re-baseline to validate).

**Deferred #2–#4** — recorded as candidates, NOT applied. They remain
valid follow-ups if a thin contract still slips past #1 in practice;
revisit only with evidence (a post-#1 false-PASS of the same shape).

## Known divergence (separate follow-up, intentionally out of scope here)

Apollo's `.claude/agents/evaluator.md` already carries a VERIFY-side
"User-path re-drive rule" (post-S06 hardening: any step asserting a real
remote MUST be re-driven through the running runtime; mock/smoke/script
that connects differently is unacceptable). **gan-harness's
`evaluator.md` never received that back-port** — it is Apollo-local
hardening. The minimal change here adds the REVIEW_CONTRACT-time check to
both repos but does NOT back-port the VERIFY-side rule to gan-harness.
That back-port is a distinct decision; flag it if a future epic's VERIFY
phase false-PASSes on transport/session divergence.

## Propagation

The 7th check was hand-mirrored into both existing gan-harness-derived
targets' copied `.claude/agents/evaluator.md` — `Apollo-Agent-Harness`
(so its imminent browser-fix re-plan is gated immediately) and
`Apollo-Table-Prisma` — byte-identical check-7 text across all three
(gan-harness + both targets; 3-way md5 verified). Each target keeps its
own per-target frontmatter `skills:` stack binding (e.g.
`Apollo-Table-Prisma` carries `python-data`) — that legitimate
customization was deliberately NOT touched. Future target projects
receive the check via `setup-gan-harness-skills` (the agents dir is
full-copy). The Apollo browser-fix re-plan brief is at
`Apollo-Agent-Harness/specs/_epic/_handoff-browser-fixes.md`.
