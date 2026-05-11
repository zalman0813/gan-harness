# Agent loop and hooks

Distilled from:
- <https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/>
- <https://strandsagents.com/docs/user-guide/concepts/agents/hooks/>
- <https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/>

## The loop

> "Invoke the model, check if it wants to use a tool, execute the tool if so,
> then invoke the model again with the result." — Strands docs

Cycle:

1. **Reasoning** — model processes accumulated context
2. **Tool selection** — model may emit one-or-more tool-use blocks
3. **Tool execution** — Strands runs each tool, captures result/exception
4. **Loop** — results appended to context, back to step 1
5. **Termination** — happens when one of these stop reasons fires:
   - `end_turn` — model emitted a final text-only response (success path)
   - `tool_use` — loop continues, this is not a terminal stop
   - `max_tokens` — model hit context limit
   - `cancelled` — `agent.cancel()` was called externally
   - `content_filtered` / `guardrail_intervention` — safety blocks

The `AgentResult` object exposes the final response plus a stop reason and
metrics (latency, token counts, tool-call count).

## Invocation surfaces

| Method                          | Returns                                  | Use when                                       |
|---------------------------------|-------------------------------------------|------------------------------------------------|
| `agent(prompt)`                 | `AgentResult` (sync, blocks)             | scripts, tests                                 |
| `agent.invoke_async(prompt)`    | `Awaitable[AgentResult]`                 | inside `async def`, no per-token streaming     |
| `agent.stream_async(prompt)`    | `AsyncIterator[dict]` of events          | UIs, token-by-token rendering, live progress   |

## Cancellation

```python
import asyncio
from strands import Agent

agent = Agent(tools=[...])

async def run():
    task = asyncio.create_task(agent.invoke_async("long task"))
    await asyncio.sleep(2)
    agent.cancel()  # thread-safe, idempotent
    result = await task
    assert result.stop_reason == "cancelled"
```

In TypeScript the equivalent is an `AbortSignal` passed into `invoke`. In
Python, `agent.cancel()` is the canonical cancellation primitive.

## Hooks

Hooks are lifecycle subscribers. Strands emits events at:

- before / after each **invocation** (whole `agent(...)` call)
- before / after each **model call** (one LLM round-trip)
- before / after each **tool execution** (one tool function call)

Key events you'll see in Python code:

- `BeforeInvocationEvent` / `AfterInvocationEvent`
- `BeforeModelCallEvent` / `AfterModelCallEvent`
- `BeforeToolCallEvent` / `AfterToolCallEvent`

Subscriber pattern (paraphrased — refer back to upstream docs for the exact
import paths in your installed version):

```python
from strands import Agent
from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent

def log_tool_call(event: BeforeToolCallEvent) -> None:
    print(f"calling {event.tool_name} with {event.arguments}")

agent = Agent(tools=[...])
agent.hooks.subscribe(BeforeToolCallEvent, log_tool_call)
```

What hooks are good for:

- **Logging / tracing** — emit OpenTelemetry spans around tool calls
- **Metrics** — count tool invocations, measure tool latency
- **Validation** — assert tool arguments meet policy before execution
- **Steering** — the official "soft-guardrail" pattern: an `AfterToolCallEvent`
  subscriber can rewrite the tool result with guidance like "Add a WHERE
  clause and LIMIT" instead of hard-blocking

What hooks are **not**:

- Not middleware. There is no `next()` to call; events are dispatched to all
  subscribers and the loop proceeds.
- Not authorisation in the security sense. Treat as defence-in-depth, not
  as a sandbox.

## Observability tie-in

The SDK integrates with OpenTelemetry — each lifecycle event maps to a span,
so production deployments commonly wire hooks into an OTLP exporter and view
agent traces in their existing observability stack.
