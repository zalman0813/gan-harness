---
name: aws-strands
description: AWS Strands Agents stack reference library for gan-harness. Vendors official docs and conventions for Strands Agents Python SDK — agent creation, @tool decorator, model providers (Amazon Bedrock default, Anthropic, OpenAI, Gemini, Ollama, LiteLLM, etc.), and the strands-agents-evals testing framework. Make sure to use this skill whenever harness agents work on AWS Strands Agents code or need Strands-specific idioms.
---

# AWS Strands Agents Stack Skill

Reference library of AWS Strands Agents (Python SDK) conventions, vendored from the official documentation at https://strandsagents.com/ and the `strands-agents/sdk-python` GitHub repository. Downstream harness agents (planner, generator, evaluator, /finalize) consult specific references as needed; this SKILL.md is the index.

Strands is Apache-2.0, model-driven, requires Python >=3.10, and the default model provider is Amazon Bedrock with Claude Sonnet 4. The SDK is published as `strands-agents` on PyPI; the optional pre-built tools package is `strands-agents-tools`; the evaluation framework is `strands-agents-evals`.

## When to use

- Generator writes or edits code that imports `from strands import Agent, tool` or `from strands_tools import ...`
- Generator builds custom tools via the `@tool` decorator (Python type hints + docstring drive the LLM-visible tool spec)
- Planner needs Strands-specific test-runner / module / tool conventions when scoping a sprint
- Evaluator runs lint / typecheck / tests against Strands code per `sensors.ini`
- /finalize regenerates docs from a Strands codebase

## References

- [quickstart.md](references/quickstart.md) — Python install, first Agent, custom tool, streaming, debug logging
- [agents.md](references/agents.md) — Agent construction, system prompts, callback handlers, agent loop semantics, cancellation, structured output
- [tools.md](references/tools.md) — `@tool` decorator patterns, async tools, module-based tools with `TOOL_SPEC`, hot-reload from `./tools/`, MCP integration
- [model-providers.md](references/model-providers.md) — Amazon Bedrock (default), other providers (Anthropic, OpenAI, Gemini, Ollama, LiteLLM), guardrails, prompt caching, multimodal, regional inference profiles
- [testing.md](references/testing.md) — `strands-agents-evals` framework: `Case`, `@eval_task`, `Experiment`, `OutputEvaluator`, `TrajectoryEvaluator`, deterministic evaluators (`Equals`, `Contains`, `ToolCalled`), pytest integration

## Provenance

See [references/upstream.md](references/upstream.md) for the source URL, fetched-at, and license of every vendored file.

## Stack-specific anti-patterns

- **Do NOT call agents synchronously inside async tools.** Async tools run concurrently inside the agent loop — call `await` on coroutines; never block on `agent(...)` from within a `@tool` coroutine.
- **Do NOT omit the docstring on a `@tool`-decorated function.** The docstring (and the type hints) are the canonical tool spec the LLM sees. A bare `@tool def foo(x): ...` ships a tool the model cannot call correctly.
- **Do NOT hard-code a Bedrock model ID without the regional prefix when running outside on-demand-throughput regions.** Use `us.anthropic.claude-sonnet-4-20250514-v1:0` (or `eu.` etc.) — bare IDs throw "on-demand throughput" errors in many regions.
- **Do NOT pin to TypeScript SDK feature parity assumptions.** The TS SDK is missing Ollama / LiteLLM, bidirectional streaming, agent steering, and most built-in tools. Stack target is Python.
- **Do NOT mix `strands_tools` (the pre-built-tools package import name) with `strands-agents-tools` (the pip install name).** Install name is `strands-agents-tools`; the import is `strands_tools`.
