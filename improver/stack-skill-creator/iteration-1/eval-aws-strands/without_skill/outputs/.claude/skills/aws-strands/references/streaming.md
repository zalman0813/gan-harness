# Streaming with `stream_async` + FastAPI integration

Vendored from <https://strandsagents.com/docs/user-guide/concepts/streaming/async-iterators/> and <https://strandsagents.com/docs/user-guide/observability-evaluation/metrics/>.

For async services (FastAPI, aiohttp, Django Channels) use `agent.stream_async(prompt)` — it returns an async iterator over events emitted by the agent loop.

## Minimal example

```python
import asyncio
from strands import Agent
from strands_tools import calculator

agent = Agent(
    tools=[calculator],
    callback_handler=None,   # suppress the default stdout printer
)

async def process_streaming_response():
    agent_stream = agent.stream_async("Calculate 2+2")
    async for event in agent_stream:
        print(event)

asyncio.run(process_streaming_response())
```

Set `callback_handler=None` whenever you're consuming the iterator yourself — otherwise the agent will _also_ print every chunk to stdout via the default handler, duplicating your output.

## Event types you will see

Each event is a dict. Common keys to branch on:

| Key | Meaning |
|---|---|
| `init_event_loop: True` | Loop is initialising (fires once per invocation) |
| `start_event_loop: True` | A new reasoning cycle is starting |
| `message` | A complete message was appended to the history (assistant or tool) — `event["message"]["role"]` |
| `current_tool_use` | A tool call is in progress; `event["current_tool_use"]["name"]` is the tool name |
| `data` | A chunk of streamed assistant text (string) |
| `result` | The final `AgentResult` (loop finished normally) |
| `force_stop: True` | Loop terminated abnormally; `event["force_stop_reason"]` carries the reason |

Reference pattern:

```python
from strands import Agent
from strands_tools import calculator

agent = Agent(
    tools=[calculator],
    callback_handler=None,
)

async for event in agent.stream_async(
    "What is the capital of France and what is 42+7?"
):
    if event.get("init_event_loop", False):
        print("🔄 Event loop initialized")
    elif event.get("start_event_loop", False):
        print("▶️ Event loop cycle starting")
    elif "message" in event:
        print(f"📬 New message: {event['message']['role']}")
    elif "result" in event:
        print("✅ Agent completed with result")
    elif event.get("force_stop", False):
        print(f"🛑 Force-stopped: {event.get('force_stop_reason', 'unknown')}")

    if "current_tool_use" in event and event["current_tool_use"].get("name"):
        tool_name = event["current_tool_use"]["name"]
        print(f"🔧 Using tool: {tool_name}")

    if "data" in event:
        snippet = event["data"][:20] + ("..." if len(event["data"]) > 20 else "")
        print(f"📟 Text: {snippet}")
```

## FastAPI integration (verbatim official pattern)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent
from strands_tools import calculator, http_request

app = FastAPI()


class PromptRequest(BaseModel):
    prompt: str


@app.post("/stream")
async def stream_response(request: PromptRequest):
    async def generate():
        agent = Agent(
            tools=[calculator, http_request],
            callback_handler=None,
        )

        try:
            async for event in agent.stream_async(request.prompt):
                if "data" in event:
                    yield event["data"]
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")
```

Notes:

- Construct the `Agent` **inside** the request handler when state must not bleed between requests (each request gets its own message history). Hoist the construction outside the handler only when you _want_ a shared agent (e.g., for shared in-memory caches).
- Filter for `"data" in event` to stream only the assistant text chunks. To stream tool progress too, also yield `current_tool_use` events.

## Cancellation in async code

Use `asyncio.wait_for(...)` around the iterator drain, _and_ call `agent.cancel()` in the timeout branch so any in-flight tool runs are stopped:

```python
import asyncio

async def run_with_timeout(agent, prompt, timeout):
    async def drain():
        async for _ in agent.stream_async(prompt):
            pass
        return agent  # actual result is on the last event; simplified for illustration

    try:
        return await asyncio.wait_for(drain(), timeout=timeout)
    except asyncio.TimeoutError:
        agent.cancel()
        raise
```

## Metrics (post-invocation)

After the iterator completes, the `AgentResult` (emitted as the `"result"` event) exposes `metrics`:

```python
result = agent("What is the square root of 144?")
print(f"Total tokens:   {result.metrics.accumulated_usage['totalTokens']}")
print(f"Execution time: {sum(result.metrics.cycle_durations):.2f} s")
print(f"Tools used:     {list(result.metrics.tool_metrics.keys())}")

if 'cacheReadInputTokens' in result.metrics.accumulated_usage:
    print(f"Cache read tokens: {result.metrics.accumulated_usage['cacheReadInputTokens']}")
```

`result.metrics` is an `EventLoopMetrics` carrying:

- `accumulated_usage` — input / output / total tokens (and cache-read tokens when prompt caching is on)
- `cycle_durations` — list of per-cycle wall times in seconds
- `tool_metrics` — keyed by tool name, with call count, success rate, and timing

For richer observability use OpenTelemetry — Strands emits OTel spans for invocations, model calls, and tool executions. See <https://strandsagents.com/docs/user-guide/observability-evaluation/observability/>.
