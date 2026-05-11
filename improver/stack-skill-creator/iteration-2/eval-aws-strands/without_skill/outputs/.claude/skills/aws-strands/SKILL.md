---
name: aws-strands
description: Stack capsule for AWS Strands Agents — Anthropic-recommended open-source Python SDK for building model-driven AI agents (agent loop, @tool decorator, model providers, hooks, structured output). Use when reading or writing Python code that imports `strands` / `strands_tools`, when discussing agent loop / tool decorators / model provider switching for Strands, or when an epic targets a Strands-based agent.
---

# AWS Strands Agents — stack capsule

AWS Strands Agents is an open-source SDK (Python + TypeScript) for building
model-driven AI agents. This capsule covers the **Python** SDK only — that is
what the official docs lead with and what most production code uses.

Upstream sources (all vendored verbatim into `references/` from the URLs noted
inside each file):

- Site: <https://strandsagents.com/>
- Python SDK: <https://github.com/strands-agents/sdk-python>
- Tools package: <https://pypi.org/project/strands-agents-tools/>

## Core mental model

Strands is **model-driven**: you give the LLM a set of tools (decorated Python
functions) and let the model decide when to call them. The framework's job is
the loop — invoke model, run any requested tool, feed results back, repeat
until the model emits a final response.

The agent loop:

1. Model receives prompt + tool specs
2. Model emits either a final response **or** one-or-more tool-use requests
3. Framework runs the tools, captures results
4. Loop back to step 1 with results appended
5. Terminates on `end_turn`, `max_tokens`, cancellation, or guardrail trip

You build agents by composing four things: an `Agent`, one or more **tools**, a
**model provider**, and optional **hooks** that observe / modify lifecycle
events. Optionally, a Pydantic schema for **structured output**.

## Minimal Python example

```python
# Python 3.10+; `pip install strands-agents strands-agents-tools`
from strands import Agent, tool
from strands_tools import calculator, current_time

@tool
def letter_counter(word: str, letter: str) -> int:
    """Count occurrences of a specific letter in a word.

    The docstring is what the LLM reads to decide when to call this tool —
    write it as if explaining the tool to a teammate.
    """
    if len(letter) != 1:
        raise ValueError("letter must be a single character")
    return word.lower().count(letter.lower())

agent = Agent(tools=[calculator, current_time, letter_counter])
result = agent("What is 25 * 48? How many R's in 'strawberry'?")
```

Default model provider is **Amazon Bedrock with Claude Sonnet 4**, so AWS
credentials with `bedrock:InvokeModel` permission are required out-of-box.

## Conventions that matter when reading Strands code

- **Tool definition lives in the docstring.** A `@tool` function's docstring
  is the LLM-facing contract; type hints feed the JSON schema. Treat both as
  load-bearing — do not paraphrase docstrings during refactors.
- **Default Bedrock provider is implicit.** `Agent(...)` with no `model=` arg
  silently picks Bedrock. If you see no model passed and the code targets
  Anthropic API / OpenAI / Ollama, it is a bug.
- **Built-in tools live in `strands_tools` (note the underscore),** the
  package is `strands-agents-tools` (hyphenated). Both names are correct in
  context — do not "fix" one to match the other.
- **Sync vs async vs stream are three distinct methods:** `agent(prompt)` is
  sync, `agent.invoke_async(prompt)` is awaitable, `agent.stream_async(prompt)`
  yields events. Mixing them in one code path is usually wrong.
- **Hooks are subscribers, not middleware.** `BeforeToolCallEvent` /
  `AfterToolCallEvent` etc. are dispatched; subscribers can observe and in
  some cases modify, but they do not form a chain that has to call `next()`.
- **`structured_output_model=` is per-invocation;** an agent-level default can
  also be set at construction time. The validated object lands at
  `result.structured_output`, not in the message stream.

## Seed topics (read on demand)

| Topic                                 | When to load                                       | File |
|---------------------------------------|----------------------------------------------------|------|
| Quickstart — install, first agent     | bootstrapping a new Strands project                | [references/quickstart.md](references/quickstart.md) |
| Tools — `@tool`, built-ins, hot-reload | writing / reviewing tool functions                | [references/tools.md](references/tools.md) |
| Model providers — Bedrock, Anthropic, OpenAI, Ollama, … | swapping providers, multi-provider code  | [references/model-providers.md](references/model-providers.md) |
| Agent loop & hooks — lifecycle events, cancellation | observing / instrumenting the loop          | [references/agent-loop-and-hooks.md](references/agent-loop-and-hooks.md) |
| Structured output — Pydantic schemas, validation | extracting typed data from agent responses    | [references/structured-output.md](references/structured-output.md) |

Each `references/*.md` cites the upstream URL it was distilled from. When a
topic feels thin, re-fetch the source rather than guessing.
