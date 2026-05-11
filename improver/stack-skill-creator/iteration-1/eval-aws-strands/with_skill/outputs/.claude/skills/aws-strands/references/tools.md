# Strands Agents — Tools

Source: https://strandsagents.com/ (user-guide concepts: tools). Vendored from official docs; see `upstream.md`.

## The `@tool` decorator

> Define any Python function as a tool by using the `@tool` decorator.

The function's **type hints** become the tool input schema; the **docstring** becomes the tool description the model sees. Both are part of the contract — type hints are not advisory in Strands.

```python
from strands import Agent, tool


@tool
def get_user_location() -> str:
    """Get the user's location."""
    return "Seattle, USA"


@tool
def weather(location: str) -> str:
    """Get weather information for a location.

    Args:
        location: City or location name
    """
    return f"Weather for {location}: Sunny, 72F"
```

## Wiring tools to an agent

Pass tools at agent construction:

```python
agent = Agent(tools=[get_user_location, weather])
agent("What is the weather like in my location?")
```

The agent reads each tool's signature + docstring once and publishes them in the model's tool spec for the lifetime of the agent instance.

## Asynchronous tools

```python
import asyncio
from strands import tool


@tool
async def call_api() -> str:
    """Call API asynchronously.

    Strands will invoke all async tools concurrently.
    """
    await asyncio.sleep(5)
    return "API result"
```

Multiple async tool calls in one model turn are executed concurrently — this is the canonical Strands speedup for tool-heavy steps.

## Compact custom tool — `word_count`

```python
from strands import Agent, tool


@tool
def word_count(text: str) -> int:
    """Count words in text.

    This docstring is used by the LLM to understand the tool's purpose.
    """
    return len(text.split())


agent = Agent(tools=[word_count])
response = agent("How many words are in this sentence?")
```

## Module-based tools (no decorator)

For tools authored without the decorator (e.g., distributed in a separate package), a module exposes a `TOOL_SPEC` variable matched to a function of the same name. The decorator approach is recommended; module-based is the escape hatch.

## Hot-reload from `./tools/`

```python
from strands import Agent

agent = Agent(load_tools_from_directory=True)
response = agent("Use any tools you find in the tools directory")
```

The agent watches `./tools/` and reloads tool modules when files change. Useful during development; do not enable in production.

## MCP integration (Model Context Protocol)

Strands has native MCP server support: any MCP server can be wired as a tool source, so agents can call tools defined in external languages or processes. The pre-built tools package (`strands-agents-tools`) ships 30+ tools (Python) and 4 tools (TypeScript) — see the upstream docs for the catalogue.

## Tool authoring checklist

- The function MUST have type hints on every parameter and on the return.
- The function MUST have a docstring; the first line is the tool description the LLM sees, the `Args:` block is parsed for per-parameter descriptions.
- Tools SHOULD return a small, deterministic value (string or JSON-serialisable structure). Large opaque blobs (binary, multi-MB strings) hurt the loop — split into smaller tools or stream out-of-band.
- Tools SHOULD raise on invalid input rather than silently returning a sentinel — the agent loop catches the exception and feeds the error back to the model.
- Async tools SHOULD use `asyncio` primitives, not `time.sleep` / blocking I/O.
