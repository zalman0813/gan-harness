# Testing AWS Strands agents (Python)

Stack-specific testing idiom for `aws-strands`. Generators write
example-based unit tests by default; add Hypothesis-driven
property-based tests (PBT) for invariant-shaped acceptance criteria.

PBT does NOT add a separate row to the `## Commands` table — property
tests are decorated unit tests that run through the existing
`test.unit` command (pytest). See the harness-level
`references/pbt-patterns.md` doc inside `stack-skill-creator` for the
property-template catalogue (idempotency, round-trip, monotonicity,
etc.).

## Test runner

pytest. Hypothesis integrates as a plugin automatically once installed.

```bash
pip install pytest hypothesis
# Strands itself for the agent class under test:
pip install strands-agents
```

## Example-based test — a tool function

A Strands `@tool` is just a decorated callable. Tests it like any pure
Python function — no agent loop, no mocked LLM.

```python
# tests/test_word_count.py
from my_agent.tools import word_count


def test_AC_01_word_count_basic() -> None:
    """AC-01: word_count splits on whitespace."""
    assert word_count("hello world") == 2


def test_AC_02_word_count_empty() -> None:
    """AC-02: empty string is zero words."""
    assert word_count("") == 0
```

## Property-based test — a tool function

```python
# tests/test_word_count_pbt.py
from hypothesis import given, strategies as st

from my_agent.tools import word_count


@given(st.text())
def test_AC_03_word_count_non_negative(text: str) -> None:
    """AC-03: word_count is never negative."""
    assert word_count(text) >= 0


@given(st.lists(st.text(alphabet="abc ", min_size=1, max_size=10),
                min_size=1, max_size=5))
def test_AC_04_word_count_sum_of_parts(parts: list[str]) -> None:
    """AC-04: counting concatenated halves equals sum of halves."""
    a, b = " ".join(parts[: len(parts) // 2]), " ".join(parts[len(parts) // 2 :])
    assert word_count(a + " " + b) == word_count(a) + word_count(b)
```

When Hypothesis finds a failing input it prints a shrunk minimal repro.
Commit that repro as a pinned example test before fixing the bug.

## Testing the agent loop (model-faking)

Real Strands agents call out to Amazon Bedrock / Anthropic / etc. Don't
hit live LLMs from unit tests. Two practical strategies:

1. **Inject a fake model**. `strands.models.Model` is a protocol; build
   a tiny stub that returns canned `AgentResult`-shaped responses.
2. **Record-and-replay** via a fixture (e.g., capture one real response
   per test scenario, replay it on subsequent runs). Suitable for
   integration smoke tests, not unit tests.

Skeleton for strategy (1):

```python
# tests/test_agent_loop.py
from strands import Agent


class _StubModel:
    """Returns canned text; never calls the network."""

    def __init__(self, reply: str) -> None:
        self._reply = reply

    def invoke(self, *_args: object, **_kwargs: object) -> str:
        return self._reply


def test_AC_05_agent_returns_canned_reply() -> None:
    """AC-05: Agent forwards model output verbatim when no tools fire."""
    agent = Agent(model=_StubModel("forty-two"))
    response = agent("What is the answer?")
    assert "forty-two" in str(response)
```

The exact stub shape may shift with SDK versions — verify against the
installed `strands.models` protocol in your environment before relying
on the structure above.

## When to skip PBT

- The acceptance criterion is a single observable example (e.g.,
  "endpoint returns 200 on `/health`"). Example test is enough.
- The function is non-deterministic (clocks, randomness, LLM calls).
  PBT replays shrunk failures, so flakes break the shrink loop.
- Heavy per-call setup (DB seed, network mocks). 100+ runs compound the
  cost; keep PBT for in-memory pure functions.

## Anti-patterns

- **Calling the real LLM from a unit test** — slow, flaky, expensive,
  non-deterministic. Inject a fake model.
- **Asserting on the LLM's exact wording** — model outputs drift. Assert
  on structural properties (tool was called, JSON field exists, value
  in expected range) instead.
- **Skipping shrunk repros** — when Hypothesis finds a bug, commit the
  shrunk input as an example test so the regression is pinned even if
  the property test runner changes seeds.
