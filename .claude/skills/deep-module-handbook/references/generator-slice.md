# Deep Module Handbook — Generator Slice

How the generator applies deep-module principles when implementing
modules and their tests.

Read `references/foundation.md` first for shared definitions, scope,
red flags, and DDD calibration.

**Scope reminder:** this slice covers only the deep-module-specific
generator behaviors. The generator's general behavior (e.g.,
conservative-default for ambiguity, surfacing open_questions when
spec is silent) lives inline in `.claude/agents/generator.md`.

## §1 When the generator consults this slice

- Before writing the first line of a new module
- When the spec hands a `Module: <name>` block from
  `feature.business_rules` (per `planner-slice.md` §5)
- Before writing tests for a module
- When tempted to extract a helper out of an existing module

## §2 Implementation order (strict)

1. **Public signatures + docstring** first.
   - The docstring's first line states what design decision the
     module hides (Parnas check, foundation.md §1)
   - No implementation written yet
2. **Self-review** the public signatures against:
   - The `Module: <name>` block from spec (does interface match what
     planner specified?)
   - foundation.md §1 leaky-abstraction check (caller doesn't need to
     know internal facts)
   - foundation.md §5 temporal-coupling flag (no required call order)
3. **Tests against the public signatures.** See §4. Tests target the
   interface, not internals.
4. **Implementation body.** The body can be complex (that's the
   point of depth).
5. **Pass-through self-check** (foundation.md §5
   `fake-deep-pass-through` flag). For each public method written,
   ask: "If I removed this method, would callers only need to rename
   their call to an inner method (no other change)?" If yes → either
   delete (pass-through) or confirm as ACL (translation work
   justifies it).

If step 5 fires and is not an ACL, surface an open_question rather
than silently inlining; planner may have intended the wrapper for a
reason not visible in the spec.

## §3 Information hiding rules

These are constraints, not red flags — generator follows them
without negotiation.

- **Return interface types, not concrete classes.** Callers see the
  abstraction, not the implementation choice.
- **Do not expose third-party types in public signatures.** A
  third-party type in the public surface triggers ACL need (per
  foundation.md §1 ACL definition); this is a planner concern, not
  generator. If the spec's interface includes a third-party type,
  open_question to planner before implementing.
- **Internal helper methods stay private.** Never make a private
  method public for "ease of testing" — extract to a new module
  with its own public interface instead (see §4 and §5 below).
- **No public mutation methods on conceptually-immutable values.**
  If a value is mutating, say so in the docstring; if it is not,
  return new instances instead of mutating.

## §4 Test layer rules

- **Test the public interface.** Each test invokes a public method
  and asserts on observable result (return value, raised exception,
  or externally-observable side effect).
- **Use real internal collaborators.** Per foundation.md §4
  cross-cutting tension #2 (Mockist vs Classicist), this methodology
  is Classicist: internal collaborators inside the module are real,
  not mocked.
- **Mock only process boundaries.** Network, filesystem, subprocess,
  external API, LLM call. Mocking these isolates tests from
  environment; mocking your own domain types freezes internal
  collaboration and defeats deep-module value.
- **Mock budget red flag.** If a single test's mock setup feels like
  it encodes the module's internal collaboration graph, you have
  crossed into Mockist territory — back off. Surface as open_question
  if you cannot reduce mocks without losing meaningful coverage.

## §5 Pass-through self-check

After writing the implementation, walk every public method and
apply the foundation.md §5 `fake-deep-pass-through` trigger:

> "If I removed this method, would callers only need to rename their
> call to an inner method (no other change)?"

- **Yes**, and the method does not perform translation across a
  foreign vocabulary boundary → it's a pass-through. Either delete
  (callers call the inner method directly) or merge with the inner
  method.
- **Yes**, but the method translates a foreign type to a domain type
  → it's an ACL method. Keep, but verify the ACL is in the planner's
  spec (per foundation.md §1 ACL definition).
- **No** (removal would force callers to handle internal complexity)
  → the method earns its existence.

If unsure (the answer is "maybe"), surface as open_question. Do not
silently keep or silently delete.

## §6 Common Rationalizations (deep-module specific)

Supplements the generator agent's general rationalizations table inline
in `.claude/agents/generator.md`.

| Rationalization | Reality |
|---|---|
| "private method got complex, just test it directly" | Tests then couple to implementation; refactor breaks tests. Extract to a new module with public interface; test that. |
| "mock this collaborator to isolate" | Isolation = test the imagined collaboration, not the real one. Use real object; mock only process boundaries. |
| "extract this helper, it's used twice in this file" | Two private uses earn a private method, not a new module. Extraction passes the deletion test only when ≥ 2 *distinct* callers across modules concentrate complexity (foundation.md §5.5 deletion test). |
| "add an optional parameter for flexibility" | Public surface widens; foundation.md §5 `config-leak` flag. Overload, separate method, or refuse. |
| "external exception just propagates upward" | Foreign vocabulary leaks; foundation.md §5 `exception-leak` flag. Catch + re-raise as domain exception with `cause=` chain (Bloch Effective Java Item 73). |

## §7 What's NOT here

- Generator's general ambiguity-handling discipline
  (conservative-default decision table, when to surface as
  open_question, when to BLOCK) → inline in `.claude/agents/generator.md`.
- Stack-specific test runner / barrel / module conventions → active
  stack skill's `references/`.
- AC interpretation (what to implement) → spec's
  `acceptance_criteria` and stack skill.
- Evaluator's review checklist → `evaluator-slice.md`.
