# Strands Agents — Testing & Evaluation

Source: https://strandsagents.com/docs/user-guide/evals-sdk/quickstart/ (Apache-2.0). Vendored from official docs; see `upstream.md`.

Strands ships a first-party evaluation SDK: `strands-agents-evals`. It is the recommended way to write tests for agents — covering output quality, tool-use trajectories, and deterministic gates suitable for CI / the harness inner gate.

## Install

```bash
pip install strands-agents-evals
pip install strands-agents strands-agents-tools
```

`strands-agents-evals` defaults to Bedrock + Claude 4 for any LLM-as-judge evaluator. Configure AWS credentials the same way as for an agent runtime — env vars, AWS credentials file, or IAM role.

## Core components

### `Case` — one test input + expected output

```python
from strands_evals import Case

test_cases = [
    Case[str, str](
        name="knowledge-1",
        input="What is the capital of France?",
        expected_output="The capital of France is Paris.",
        metadata={"category": "knowledge"}
    ),
]
```

### `@eval_task` — declare the agent under test

The decorator eliminates boilerplate. The decorated function may return:

- An `Agent` (auto-invoked with `case.input`)
- A string (used directly as the response)
- A dictionary (structured response)

```python
from strands_evals import eval_task
from strands import Agent


@eval_task()
def get_response():
    return Agent(
        system_prompt="You are a helpful assistant.",
        callback_handler=None,
    )
```

For trajectory inspection, decorate with the traced handler:

```python
from strands_evals import eval_task
from strands_evals.handlers import TracedHandler


@eval_task(TracedHandler())
def get_response_traced():
    return Agent(...)
```

## Evaluators

### `OutputEvaluator` — LLM-as-judge rubric

```python
from strands_evals import Experiment
from strands_evals.evaluators import OutputEvaluator

evaluator = OutputEvaluator(
    rubric="""
    Evaluate the response based on:
    1. Accuracy - Is the information factually correct?
    2. Completeness - Does it fully answer the question?
    3. Clarity - Is it easy to understand?
    """,
    include_inputs=True
)

experiment = Experiment[str, str](cases=test_cases, evaluators=[evaluator])
reports = experiment.run_evaluations(get_response)
reports[0].run_display()
```

### Deterministic evaluators (CI-friendly)

Fast, code-based checks — no LLM call, so safe for tight pre-commit / CI loops:

| Evaluator | What it checks |
|---|---|
| `Equals` | Exact match between agent output and `expected_output`. |
| `Contains` | `expected_output` substring is in agent output. |
| `ToolCalled` | Agent invoked a specific tool by name during the trajectory. |
| `StateEquals` | A given state field equals an expected value. |

### Other built-in evaluators

- `TrajectoryEvaluator` — scores tool selection, sequence, and efficiency.
- `HelpfulnessEvaluator` — 7-level scoring for response quality.

## Running an experiment

```python
# Synchronous
reports = experiment.run_evaluations(get_response)

# Asynchronous (concurrent cases)
reports = await experiment.run_evaluations_async(get_response_async)

for case_result in reports[0].case_results:
    print(f"Score: {case_result.evaluation_output.score}")
    print(f"Passed: {case_result.evaluation_output.test_pass}")
    print(f"Reason: {case_result.evaluation_output.reason}")
```

## Integration with pytest (gan-harness pattern)

The harness's `[test] unit` runner is `pytest -x --tb=short {scope}`. Wrap deterministic evaluators in pytest functions so they run through the same gate:

```python
# tests/test_agent_responses.py
import pytest
from strands import Agent
from strands_evals import Case, Experiment, eval_task
from strands_evals.evaluators import Contains, ToolCalled

from myproject.agents import build_weather_agent  # the function under test


@eval_task()
def task():
    return build_weather_agent()


CASES = [
    Case[str, str](
        name="weather_seattle",
        input="What is the weather in Seattle?",
        expected_output="Seattle",
        metadata={"tool_expected": "weather"},
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_agent_responds_with_location(case):
    exp = Experiment[str, str](cases=[case], evaluators=[Contains()])
    report = exp.run_evaluations(task)[0]
    assert report.case_results[0].evaluation_output.test_pass


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_agent_invokes_weather_tool(case):
    exp = Experiment[str, str](
        cases=[case],
        evaluators=[ToolCalled(tool_name="weather")],
    )
    report = exp.run_evaluations(task)[0]
    assert report.case_results[0].evaluation_output.test_pass
```

## Property-based testing (Hypothesis)

For pure helper functions (parsers, normalisers, format converters) used by tools, Hypothesis is the right complement to example-based tests. See the upstream `pbt-patterns.md` in the stack-skill-creator for idiom templates. Property tests are just decorated pytest functions — they run through the existing `[test] unit` command; there is no separate runner.

```python
from hypothesis import given, strategies as st
from myproject.text import normalize


@given(st.text())
def test_normalize_idempotent(text):
    """normalize(normalize(s)) == normalize(s)."""
    assert normalize(normalize(text)) == normalize(text)
```

## Best practices (vendored from upstream)

- Start with **output evaluation** (Contains / Equals) before adding trajectory analysis.
- Combine multiple evaluators per case for layered coverage.
- Use **extractors** to scope agent output before evaluation (prevents context overflow in LLM-judge evaluators).
- Save and version-control experiment definitions via JSON serialization.
- Reserve `OutputEvaluator` (LLM-as-judge) for higher-signal cases that deterministic evaluators cannot cover — judge calls cost tokens and add latency.
