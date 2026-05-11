# Quickstart — installing Strands and writing your first agent

Distilled from:
- <https://strandsagents.com/>
- <https://strandsagents.com/docs/user-guide/quickstart/python/>
- <https://github.com/strands-agents/sdk-python>
- <https://pypi.org/project/strands-agents/>

## Prerequisites

- Python 3.10+
- AWS credentials with permission to invoke Claude Sonnet 4 via Bedrock,
  **if** you use the default model provider. Other providers (Anthropic API,
  OpenAI, Ollama, etc.) have their own credential requirements — see
  [model-providers.md](model-providers.md).

## Install

```bash
# Core SDK
pip install strands-agents

# Optional: pre-built built-in tools (calculator, current_time, http_request, ...)
pip install strands-agents-tools

# Optional: the `strands` CLI / agent-builder helpers
pip install strands-agents-builder
```

The PyPI package name uses hyphens (`strands-agents`) but the import name uses
no separator (`from strands import ...`). The built-in tools package is
`strands-agents-tools` but imports as `from strands_tools import ...`.

## Minimal agent

```python
from strands import Agent, tool
from strands_tools import calculator, current_time

# Custom tool — docstring + type hints are the LLM-facing contract.
@tool
def letter_counter(word: str, letter: str) -> int:
    """Count occurrences of a specific letter in a word."""
    if len(letter) != 1:
        raise ValueError("letter must be a single character")
    return word.lower().count(letter.lower())

agent = Agent(tools=[calculator, current_time, letter_counter])

# Sync invocation. Default provider is Amazon Bedrock + Claude Sonnet 4.
result = agent("What is 25 * 48? How many R's in 'strawberry'?")
print(result)
```

## Streaming invocation

For long-running answers or token-by-token UIs, use `stream_async`:

```python
import asyncio

async def main():
    async for event in agent.stream_async("Explain transformers."):
        if "data" in event:
            print(event["data"], end="", flush=True)

asyncio.run(main())
```

`agent.invoke_async(prompt)` exists too — same return as sync `agent(...)`
but awaitable, with no event stream.

## What happens under the hood

The default agent loop:

1. Strands serialises your tool list to a JSON-Schema tool spec
2. Sends prompt + spec to the model (Bedrock + Claude Sonnet 4 by default)
3. If the model emits a tool-use block, Strands locates the matching Python
   function, validates arguments, runs it, captures the return value
4. Tool result is appended to the conversation; loop continues
5. When the model returns `stop_reason="end_turn"`, the loop ends and
   `agent(...)` resolves with the final `AgentResult`

This is what "model-driven" means in the docs: the model — not your code —
decides when to call which tool.

## Common first-run failures

| Symptom                              | Likely cause                                                                                  |
|--------------------------------------|------------------------------------------------------------------------------------------------|
| `AccessDeniedException` from Bedrock | AWS creds missing or lack `bedrock:InvokeModel` on `anthropic.claude-sonnet-4-*`               |
| `ModuleNotFoundError: strands_tools` | Installed `strands-agents` but not `strands-agents-tools`                                     |
| Tool never gets called               | Docstring too vague — the model has no signal that this tool is relevant. Rewrite docstring.   |
| `ValidationError` on tool arguments  | Type hints don't match what the model emitted; tighten hints or widen acceptance              |
