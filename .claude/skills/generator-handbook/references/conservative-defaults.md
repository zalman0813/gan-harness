# Conservative defaults

The discipline: implement what the AC says, no more.

## The temptation

When you read an AC, your training-data prior pulls you toward "safety"
that wasn't asked for: a try/catch that swallows errors silently, an
`if not user: return None` guard, a default value when the field is null,
a retry on transient failure. These feel like good engineering. In this
harness they are silent scope creep.

The AC is the contract. The planner-handbook's three-test gate already
filtered "real architectural decisions" into ADRs and "real feature-local
rules" into `spec.business_rules`. If neither place mentions a behaviour,
**that behaviour is not in scope**.

## The rule

For each line of code you're about to write, ask: which AC, business
rule, or ADR drives this? If you can't name one, delete the line.

## Worked examples

**Example 1 — invented validation.**

AC-01 says: *"user changes display name to 'Alice' and taps save → page
shows 'Saved'"*. business_rule says: *"display name 3-20 chars, no
leading/trailing whitespace"*.

Tempting addition: also reject names containing emoji, control characters,
homoglyph attacks. None of these are in AC or business_rule. Don't add
them. If they matter, the planner missed them — surface as
`open_questions[]` in your final response, do not add silently.

**Example 2 — invented fallback.**

AC-02 says: *"user's email update fails when format invalid → page shows
'Invalid email'"*. The implementation: validate format, if invalid raise
`ValidationError`, surface as 422.

Tempting addition: also catch network errors during the validate call and
show "Network error, please retry". The AC doesn't mention network errors.
If `kind: error` ACs exist for that, implement them; if not, don't.

**Example 3 — invented logging.**

No AC mentions logging. Don't add structured logging "for observability".
If observability is a cross-cutting concern, it's an ADR; if it isn't,
it's silent scope.

## What if the AC is genuinely too tight?

Surface it. Two options at the end of your generator turn:

1. Implement strictly to the AC and note in the commit body: *"NOTE: AC-02
   doesn't specify behaviour when email is null; implemented as 'reject
   with 422 Invalid email'."* This puts the gap on the evaluator's radar.

2. If the gap is structural enough that the implementation can't proceed
   without a decision, stop and surface in your final response: *"AC-02
   doesn't cover null email; I cannot proceed without one of: (a) accept
   null and clear, (b) reject with explicit error, (c) ignore and keep
   prior value. Please re-grill."* This forces a human decision before
   round-2 burns budget.

The pattern: silence is not safety. Either implement narrowly with a
visible note, or stop and ask. Never invent and ship.

## Why this discipline matters here

The harness's downstream tooling (the `ac_coverage` SubagentStop hook,
future mutation-score gate, /finalize archive) keys off AC presence.
Behaviour without an AC is invisible to those tools — it lands in code
without a verification target, and the next batch's generator can break
it without any test failing. Conservative defaults keep the
invisible-behaviour surface area near zero.

**On strict lint vs conservative-defaults**: the stack skill enforces
strict lint (mypy --strict, tsconfig strict, ruff). That catches
type/null bugs. It is NOT permission to add defensive scaffolding. The
AC defines what to validate; if strict lint flags a real type/null bug,
fix the bug — do not wrap with `try/except`.
