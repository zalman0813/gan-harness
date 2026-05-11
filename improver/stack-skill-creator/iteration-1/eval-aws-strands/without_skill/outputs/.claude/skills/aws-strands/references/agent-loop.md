# Agent loop, lifecycle events, AgentResult

Vendored from <https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/>.

## The loop

> "A language model can answer questions. An agent can _do things_. The agent loop is what makes that difference possible."

The loop is dead simple in shape:

```
Input + Context  →  ┌──── Reasoning (LLM) ──── ┐
                    │              │            │
                    │              ▼            │
                    │       Tool Selection      │
                    │              │            │
                    │              ▼            │
                    └──── Tool Execution ───────┘
                                  │
                                  ▼
                              Response
```

What makes it powerful is **context accumulation**: each iteration adds the tool call + result to the conversation history, so the model sees every step it has taken. This is what enables multi-step reasoning.

## Lifecycle events

The agent emits events at key points in the loop:

- **Before / after each invocation** (the outer `agent(...)` call)
- **Before / after each model call** (each LLM round-trip)
- **Before / after each tool execution**

These let you attach metrics collection, logging, or behaviour modification without forking the loop. See [streaming.md](streaming.md) for the concrete event names emitted by `stream_async`.

## AgentResult and stop reasons

Every `agent(...)` call returns an `AgentResult` object. The key fields:

- `result.message` — the final assistant message
- `result.stop_reason` — why the loop exited (see below)
- `result.metrics` — an `EventLoopMetrics` with token usage, cycle durations, per-tool counts (see [streaming.md](streaming.md) and Observability docs)
- The full message history is also accessible via `agent.messages`

Possible `stop_reason` values:

| Stop reason | Meaning |
|---|---|
| `end_turn` | Normal completion — model produced a final response |
| `tool_use` | Model requested a tool (intermediate; you usually see this only when streaming) |
| `cancelled` | External `agent.cancel()` called |
| `max_tokens` | Output budget hit; response is truncated |
| `stop_sequence` | A configured stop sequence fired |
| `content_filtered` | Safety filter blocked the response |
| `guardrail_intervention` | Bedrock Guardrail policy enforced |

Always assert `stop_reason == "end_turn"` in production code that depends on the agent's answer — anything else means you got a partial / blocked / cancelled response.

## Cancellation

Strands supports cooperative cancellation via `agent.cancel()`. A typical timeout pattern:

```python
import threading
import time
from strands import Agent

def timeout_watchdog(agent: Agent, timeout: float) -> None:
    """Cancel the agent after a timeout period."""
    time.sleep(timeout)
    agent.cancel()

agent = Agent()
watchdog = threading.Thread(target=timeout_watchdog, args=(agent, 30.0))
watchdog.start()
result = agent("Analyze this large dataset")
watchdog.join()
if result.stop_reason == "cancelled":
    print("Agent was cancelled due to timeout")
```

In async code, use `asyncio.wait_for(...)` around `agent.stream_async(...)` instead of a separate watchdog thread — see [streaming.md](streaming.md).

## Anti-patterns

- **Treating the loop as a one-shot RPC.** It isn't — the model may invoke multiple tools, observe the results, and revise its plan. Design tools to be re-entrant.
- **Mutating shared state inside a tool without sync.** The loop runs sequentially per agent, but tools that share state across multiple agents need their own locking.
- **Returning huge blobs from a tool.** Tool results land in the conversation history and get fed back to the model. Trim aggressively; offload bulk data to disk/S3 and return a handle.
- **Forgetting to check `stop_reason`.** Failing silently on `max_tokens` or `guardrail_intervention` produces empty / wrong answers that look like normal completions.
