---
name: aws-strands
description: Stack skill for AWS Strands Agents — Anthropic-recommended Python (and TypeScript) framework for building model-driven AI agents. Covers install, the canonical agent + tools pattern, agent loop semantics, streaming, and Amazon Bedrock model configuration. Use when planner / generator / evaluator are working on a Strands-based agent project (default provider: Amazon Bedrock + Claude Sonnet 4).
allowed-tools: Bash(python:*) Bash(pip:*) Bash(uv:*) Bash(pytest:*) Bash(ruff:*) Bash(mypy:*)
---

# AWS Strands Agents (Python)

Strands Agents is an open-source SDK for building production-ready AI agents in Python and TypeScript. The runtime is centred on three things: a **language model**, a **system prompt**, and a **set of tools**. The framework drives an agent loop (model → tool selection → tool execution → model) until the model emits a final answer.

This skill vendors the official documentation at <https://strandsagents.com/> so harness agents can implement and review Strands code without re-fetching.

> **Languages.** Strands ships SDKs for **Python** and **TypeScript**. This skill targets Python — that is what was requested. If a future epic adds the TypeScript SDK, add `aws-strands-ts` as a separate stack skill rather than fattening this one.

## Quick start

```bash
# Python 3.10+ required
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate.bat       # Windows CMD

pip install strands-agents                              # core SDK
pip install strands-agents-tools strands-agents-builder # optional helpers
```

Default model provider is **Amazon Bedrock** with **Claude Sonnet 4** (`anthropic.claude-sonnet-4-20250514-v1:0`). You need AWS credentials with `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream` reachable via env vars, `aws configure`, an IAM role, or a Bedrock API key (`AWS_BEARER_TOKEN_BEDROCK`).

The canonical "hello agent":

```python
# agent.py
from strands import Agent, tool
from strands_tools import calculator, current_time

@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word: The input word to search in
        letter: The specific letter to count
    """
    if not isinstance(word, str) or not isinstance(letter, str):
        return 0
    if len(letter) != 1:
        raise ValueError("The 'letter' parameter must be a single character")
    return word.lower().count(letter.lower())

agent = Agent(tools=[calculator, current_time, letter_counter])

agent("What time is it? Also, how many R's are in 'strawberry'?")
```

```bash
python -u agent.py
```

`agent(...)` returns an `AgentResult` carrying the message history, stop reason, and an `EventLoopMetrics` object (token usage, latency, per-tool counts).

## Project layout convention

Strands itself imposes no specific layout, but the official quickstart uses:

```
my_agent/
├── __init__.py
├── agent.py
└── requirements.txt
```

`requirements.txt`:

```
strands-agents>=1.0.0
strands-agents-tools>=0.2.0
```

`__init__.py`:

```python
from . import agent
```

For multi-tool projects, prefer a flat `tools/` package of `@tool`-decorated functions and a single `agent.py` wiring them in. Class-based tools (state + multiple `@tool` methods on one class) are the idiomatic way to share resources (DB connections, HTTP clients, caches) across tool calls — see [references/custom-tools.md](references/custom-tools.md).

## Inner gate (recommended)

Strands is plain Python — the inner-gate script (`gate_gen_precommit.py`) should run the standard Python stages plus an agent-specific smoke test:

```
lint.fix     → ruff format
lint.check   → ruff check
typecheck    → mypy --strict src/      # tools must be fully typed for schema gen
unit tests   → pytest -m "not e2e"
agent smoke  → pytest tests/agent_smoke_test.py   # one canned prompt, asserts AgentResult.stop_reason == "end_turn"
```

Why an agent smoke is non-optional: Strands generates tool JSON schemas from docstrings + type hints at import time. A missing type hint, an ambiguous docstring, or a renamed parameter silently degrades tool routing — typecheck won't catch it. The smoke test catches it.

For evaluation cost control, mock the model in unit tests and reserve real Bedrock calls for the smoke + e2e tier.

## What's in references/

* **Quickstart, install, AWS credentials** → [references/quickstart.md](references/quickstart.md)
* **Agent loop, lifecycle events, AgentResult / stop reasons, cancellation** → [references/agent-loop.md](references/agent-loop.md)
* **Custom tools (`@tool` decorator, class-based tools, async tools, module tools)** → [references/custom-tools.md](references/custom-tools.md)
* **Streaming with `stream_async` + FastAPI integration** → [references/streaming.md](references/streaming.md)
* **Amazon Bedrock model configuration (default), region handling, guardrails, caching** → [references/model-providers.md](references/model-providers.md)

## Out of scope for this Starter capsule

The following are documented upstream but **not** yet vendored here. Add them as follow-up topics if an epic needs them:

- Multi-agent patterns (Swarm, Graph, Workflow, Agent2Agent)
- MCP tool integration (`mcp-tools`)
- Hooks / steering / plugins
- Bidirectional streaming (voice / realtime)
- Other model providers (OpenAI, Anthropic-direct, Google, Ollama, LiteLLM, …)
- Deploy targets (Lambda, Fargate, EKS, EC2, Terraform)
- Strands Evals SDK
- Guardrails configuration details

When the user asks for one of these, fetch from <https://strandsagents.com/docs/> and add a new `references/<topic>.md` plus a pointer here.

## Upstream

- Site: <https://strandsagents.com/>
- Docs root: <https://strandsagents.com/docs/>
- Source: <https://github.com/strands-agents>
- PyPI: `strands-agents`, `strands-agents-tools`, `strands-agents-builder`
