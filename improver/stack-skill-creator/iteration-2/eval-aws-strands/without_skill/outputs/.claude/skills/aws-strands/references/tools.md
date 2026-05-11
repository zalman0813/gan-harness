# Tools — `@tool`, built-ins, hot-reload

Distilled from:
- <https://github.com/strands-agents/sdk-python>
- <https://pypi.org/project/strands-agents-tools/>
- <https://strandsagents.com/docs/user-guide/quickstart/python/>

A Strands tool is a Python function the agent may call mid-loop. The model
decides whether to call it based on the function's **docstring** and the
**type hints** on its parameters and return value.

## Defining a tool with `@tool`

```python
from strands import Agent, tool

@tool
def word_count(text: str) -> int:
    """Count words in a piece of text.

    Use this when the user asks how many words are in something.
    """
    return len(text.split())

agent = Agent(tools=[word_count])
agent("How many words in 'the quick brown fox'?")
```

Rules of thumb:

- **Docstring = LLM contract.** Write it as if explaining to a teammate
  when and why they should call this function. The first sentence is the
  most-read part — front-load the use case.
- **Every parameter needs a type hint.** Strands converts hints to JSON
  Schema. Untyped `def foo(text):` will not register cleanly.
- **Return type matters too.** Use `int`, `str`, `list[str]`, Pydantic
  models, etc. — anything JSON-serialisable. Avoid raw `dict` when a
  Pydantic model would document the shape.
- **Raise on bad input.** Strands surfaces tool exceptions back to the
  model as error tool-results, which it can react to. Do not silently
  return `None` on failure.

## Built-in tools (`strands-agents-tools`)

Install separately:

```bash
pip install strands-agents-tools
```

Import names live under `strands_tools` (underscore). Typical built-ins
include `calculator`, `current_time`, `http_request`, file-reading helpers,
and shell helpers — the exact roster grows over time; check
`pip show -f strands-agents-tools` for the current list.

```python
from strands import Agent
from strands_tools import calculator, current_time, http_request

agent = Agent(tools=[calculator, current_time, http_request])
agent("What time is it in UTC, and what's 2^10?")
```

## Hot-reloading tools from a directory

```python
agent = Agent(load_tools_from_directory=True)
# Agent scans ./tools/ (or configured path) and picks up every @tool-decorated
# function it finds. Edits hot-reload on next invocation.
agent("Use any tools you find.")
```

Useful in development; in production, prefer explicit `tools=[...]` lists so
you can audit what the agent is allowed to call.

## Structured tool returns

```python
from pydantic import BaseModel
from strands import tool

class WeatherReport(BaseModel):
    location: str
    temp_c: float
    conditions: str

@tool
def get_weather(city: str) -> WeatherReport:
    """Look up current weather for a city. Returns temperature in Celsius."""
    # ... fetch ...
    return WeatherReport(location=city, temp_c=18.5, conditions="cloudy")
```

The returned Pydantic model is serialised back to the LLM as JSON; the model
can then quote individual fields verbatim.

## Anti-patterns

- **Tools that do nothing but call the LLM again.** That is the agent's job;
  if you find yourself doing it, you want a sub-agent, not a tool.
- **Catching `Exception` inside a tool and returning a string error.** Raise
  instead — the framework already wraps exceptions into structured
  tool-error results the model can reason about.
- **Side-effects without explicit naming.** A `@tool` named `lookup_user`
  that also writes to the DB will be called speculatively by the model.
  Rename to `update_user_email_and_return_record` or split into two tools.
