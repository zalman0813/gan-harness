# Strands Agents — Agents and the Agent Loop

Source: https://strandsagents.com/ (user-guide concepts: agents, agent-loop). Vendored from official docs; see `upstream.md`.

## What an agent is

> A language model can answer questions. An agent can _do things_.

A Strands agent is the orchestrator over a model-driven loop centered on three components:

- A **language model** (any provider from `strands.models`; default = Bedrock + Claude Sonnet 4)
- A **system prompt** (string or list of `SystemContentBlock` for caching)
- A **set of tools** (Python functions decorated with `@tool`, or modules exposing `TOOL_SPEC`)

The model autonomously decides which tools to call and when, based on the current context.

## Constructing an agent

```python
from strands import Agent

agent = Agent()  # defaults: Bedrock + Claude Sonnet 4, no tools, default callback_handler

agent = Agent(
    model="anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="You are a helpful assistant.",
    tools=[],
    callback_handler=None,  # disable default streaming printout
)
```

## Invoking an agent

```python
response = agent("Tell me about Amazon Bedrock.")
```

Multi-modal input is also a single call:

```python
response = agent([
    {
        "document": {
            "format": "txt",
            "name": "example",
            "source": {"bytes": b"Document content"}
        }
    },
    {"text": "Tell me about the document."}
])
```

## Agent loop semantics

The loop:

1. Invoke the model with the running conversation history.
2. Check whether the model requests a tool.
3. Execute the tool if requested.
4. Feed the tool result back into the model as a tool-result message.
5. Repeat until the model produces a final response.

Each iteration accumulates conversation history — "the model's working memory for the task".

### Messages

- **User messages**: initial requests, follow-up instructions, tool results.
- **Assistant messages**: text responses, tool-use requests, reasoning traces.

### Tool execution

The execution system:

- Validates tool-call arguments against the tool schema (Python type hints).
- Locates the tool by name.
- Executes the tool with error handling.
- Formats the result back into a tool-result message.

> When a tool fails, the error information goes back to the model as an error result rather than throwing an exception that terminates the loop.

### Stop reasons (loop exit)

| stop_reason | meaning |
|---|---|
| `end_turn` | Normal completion — the model produced a final response. |
| `tool_use` | Continue to the next iteration. |
| `max_tokens` | Unrecoverable truncation. |
| `cancelled` | External `agent.cancel()` was triggered. |
| `content_filtered` / `guardrail_intervened` | Safety block. |

## Cancellation

```python
agent.cancel()
```

Cancellation is checked at:

- Before each model invocation.
- During streaming.
- Before each tool execution.

Tools can cooperatively respect cancellation via `AbortSignal` forwarding.

## Structured output

Use Pydantic to constrain the agent's reply to a typed schema:

```python
from pydantic import BaseModel, Field
from strands import Agent


class ProductAnalysis(BaseModel):
    name: str = Field(description="Product name")
    price: float = Field(description="Price in USD")


agent = Agent()
result = agent.structured_output(ProductAnalysis, "Analyze this product: ...")
# result is a validated ProductAnalysis instance
```

## System-prompt caching (Bedrock)

Long system prompts can be cached at the provider level using `SystemContentBlock`:

```python
from strands import Agent
from strands.types.content import SystemContentBlock

system_content = [
    SystemContentBlock(text="You are helpful..." * 1600),
    SystemContentBlock(cachePoint={"type": "default"}),
]
agent = Agent(system_prompt=system_content)
```

Cached content expires after 5 minutes.

## Common loop failure modes

- **Context exhaustion** — conversation history exceeds model context window. Mitigate by reducing tool output verbosity, simplifying tool schemas, or applying conversation management (`null`, `sliding_window`, `summarizing`).
- **Inappropriate tool selection** — usually a symptom of ambiguous tool descriptions, not model weakness. Fix by sharpening the tool docstring and type hints.

## Multi-agent patterns (overview)

Strands supports multi-agent compositions: `swarms`, `graphs`, `workflows`, and `agents-as-tools`. Wire details vary per pattern; agents-as-tools is the simplest — expose another agent's `__call__` via a `@tool`-decorated wrapper.
