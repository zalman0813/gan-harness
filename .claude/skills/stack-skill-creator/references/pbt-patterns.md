# Property-Based Testing (PBT) Patterns

Reference doc for stack-skill authors deciding whether and how to
include PBT support in a new stack skill.

## What it is

Instead of hand-writing examples (`assert add(2, 3) == 5`), you state
a property that should hold across many inputs (`add(a, b) == add(b, a)`),
and the test runner generates 100s of random inputs to try to break it.
When it finds a failing input, it shrinks to a minimal repro.

## When to use

PBT shines on **invariants over a value space**:

| Property | Example template |
|---|---|
| **Idempotency** | `f(f(x)) == f(x)` (e.g., normalising a path twice = once) |
| **Round-trip** | `decode(encode(x)) == x` (serialisation, parse/format) |
| **Commutativity** | `merge(a, b) == merge(b, a)` (set union, max) |
| **Associativity** | `op(op(a, b), c) == op(a, op(b, c))` (concat, plus) |
| **Monotonicity** | `if a ≤ b, then f(a) ≤ f(b)` (sort key extractors) |
| **Inverse pair** | `decompress(compress(x)) == x` |
| **Reference oracle** | `optimised(x) == naive(x)` (cache layer = direct) |

PBT is a **complement** to example-based tests, not a replacement.
Keep example-based tests for the canonical happy path; add PBT for
edge-case coverage.

## When NOT to use

- **UI / browser tests** — the value space is non-numeric and hard to
  generate meaningfully. Stick to example tests.
- **Heavy setup per call** — DB seed, network mocks. PBT runs the
  property 100+ times; setup cost compounds.
- **Non-deterministic results** — clocks, randomness, threading.
  PBT replays shrunk failures, so flakes break the shrink loop.
- **Properties you can't articulate** — if the only "property" you
  can write is "the test passes", you don't have one.

## Python — Hypothesis

```python
from hypothesis import given, strategies as st


@given(st.text())
def test_AC_03_normalize_idempotent(text):
    """AC-03: normalize(normalize(s)) == normalize(s)."""
    assert normalize(normalize(text)) == normalize(text)


@given(st.lists(st.integers()))
def test_AC_04_sort_round_trip(items):
    """AC-04: sorted(sorted(xs)) == sorted(xs)."""
    once = sorted(items)
    assert sorted(once) == once


@given(st.dictionaries(st.text(min_size=1), st.integers()))
def test_AC_05_json_round_trip(d):
    """AC-05: json.loads(json.dumps(d)) preserves d."""
    assert json.loads(json.dumps(d)) == d
```

Run via the active stack skill's `[test] unit` command (Hypothesis
integrates with pytest by default). No special runner — just import
`hypothesis` and decorate.

For stateful systems use `RuleBasedStateMachine`:

```python
from hypothesis.stateful import RuleBasedStateMachine, rule


class CartMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cart = Cart()

    @rule(item=st.text(min_size=1), qty=st.integers(min_value=1, max_value=10))
    def add_item(self, item, qty):
        self.cart.add(item, qty)

    @rule()
    def total_is_non_negative(self):
        assert self.cart.total() >= 0
```

## TypeScript / JavaScript — fast-check

```typescript
import * as fc from 'fast-check';

test('AC-03: normalize is idempotent', () => {
  fc.assert(
    fc.property(fc.string(), (s) => {
      expect(normalize(normalize(s))).toEqual(normalize(s));
    })
  );
});

test('AC-04: encode/decode round-trip', () => {
  fc.assert(
    fc.property(fc.record({ id: fc.uuid(), n: fc.integer() }), (obj) => {
      expect(JSON.parse(JSON.stringify(obj))).toEqual(obj);
    })
  );
});
```

Runs through the active stack skill's `[test] unit` command (fast-check
plugs into Jest / Vitest as a regular test). No separate runner.

## Stack skill author guidance

When you create a new stack skill that should support PBT:

1. **Add the PBT library to the stack's expected dependencies**
   (`hypothesis` for Python, `fast-check` for TS). Document in the
   stack skill's own README which version you target.

2. **In `references/`, add a `testing.md`** (or augment if exists) with
   the stack-specific PBT idiom — generator-side guidance points to
   this when the planner asks for property tests.

3. **Do NOT add a `[pbt]` section to `sensors.ini`.** Property tests
   are just decorated unit tests; they run via `[test] unit` like any
   other test. Adding a PBT-specific runner is wrong unless your stack
   genuinely separates the two (none we know of as of 2026-05).

4. **Mention shrink-output handling** in the stack skill: when a PBT
   test fails, the runner prints a shrunk minimal repro. Generators
   should commit the failing input as a regression-pinning example
   test, then fix the bug.

## Out of scope for the stack skill

The harness ships no PBT-specific gate. PBT failures surface through
the unit-test runner, get caught by gate_gen_precommit's
`[test] unit` step, and are FAILed in the round just like any other
test failure.

The `e2e-approach` skill (T15, deferred) will package PBT alongside
Playwright + computer-use as a behaviour-harness bundle, but that's
about how to *invoke* PBT for behaviour testing — not about the unit
PBT idiom this doc covers.
