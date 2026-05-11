---
name: aws-strands
description: AWS Strands Agents (Python) stack reference library for gan-harness. Vendors official docs and conventions for agent loop, tools, model providers, and multi-agent patterns. Make sure to use this skill whenever harness agents work on AWS Strands code or need Strands-specific idioms (agent loop, @tool decorator, MCP integration, multi-agent orchestration).
---

# AWS Strands Stack Skill

Reference library of AWS Strands Agents conventions, vendored from the
official Strands documentation repository
(<https://github.com/strands-agents/docs>) and SDK
(<https://github.com/strands-agents/sdk-python>). Downstream harness
agents (planner, generator, evaluator, /finalize) consult specific
references as needed; this SKILL.md is the index.

Strands is a Python (and TypeScript) framework for building
model-driven AI agents. It defaults to Amazon Bedrock with Claude
Sonnet 4 but is model-agnostic (Anthropic, OpenAI, Gemini, Ollama,
etc.). Agents are defined by a simple loop: invoke model → execute
tools → feed results back → repeat until done.

This stack skill is **Python-only**. If you add TypeScript support
later, vendor the `.ts` siblings of each upstream `.mdx` file and
unwrap the `--8<--` snippet directives.

## When to use

- Generator writes or edits Strands-based agent code in Python
- Planner needs Strands idioms (`@tool` decorator, `Agent(...)`
  constructor, `BedrockModel` / `AnthropicModel` provider config,
  `Graph` / `Swarm` / `Workflow` multi-agent patterns)
- Evaluator reviews a sprint contract that mentions Strands components
- /finalize regenerates CODEMAP.md for a Strands codebase

## Commands

Harness gate contract. Pre-commit hook reads this via
`.claude/scripts/parse_stack_commands.py`. Required keys:
`lint.fix`, `lint.check`, `typecheck`, `test.unit`. Optional:
`test.smoke`. `{scope}` is substituted at invocation time (changed
files for the pre-commit hook, `verification_plan` paths for the
evaluator).

| Key | Command |
|---|---|
| lint.fix | `ruff check --fix --silent {scope}` |
| lint.check | `ruff check {scope}` |
| typecheck | `mypy --strict {scope}` |
| test.unit | `pytest -x --tb=short {scope}` |
| test.smoke | `pytest --no-header {scope}` |

Rationale:

- **Ruff** is the de-facto Python lint+format runner in 2026 and is
  what `strands-agents/sdk-python` itself ships in CI. It covers both
  PEP 8 and many flake8 plugins in a single fast pass.
- **mypy --strict** is production-faithful: Strands uses heavy generics
  and protocols (`Model`, `Tool`, `AgentResult`), and strict mode
  catches the missing-annotation traps before they reach the runtime.
- **pytest** is the Strands docs' chosen runner; Hypothesis plugs in
  natively (see `references/testing.md`).
- **test.smoke** is `pytest --no-header` against any directory the
  sprint contract names. The pre-commit hook does NOT run smoke;
  evaluator runs it when the `verification_plan` mentions a smoke
  step.
- `{scope}` quoting: ruff / mypy / pytest all accept space-joined
  multi-path arguments. The pytest dual-consumer caveat applies — see
  `stack-skill-creator/references/commands-contract.md` (Known
  limitation: dual-consumer scope semantics).

## References

- [quickstart-python.md](references/quickstart-python.md) — install,
  configure credentials, project layout, run an agent, console output,
  debug logs, switch model providers, async streaming
- [agent-loop.md](references/agent-loop.md) — the reason / tool / act
  loop that defines a Strands agent; the foundational concept
- [tools-overview.md](references/tools-overview.md) — how to add,
  load, and invoke tools (function-based, module-based, MCP, vended,
  agents-as-tools); design best practices
- [model-provider-anthropic.md](references/model-provider-anthropic.md)
  — `AnthropicModel` configuration (api key, model_id, max_tokens,
  params) for agents that talk to Claude directly
- [multi-agent-patterns.md](references/multi-agent-patterns.md) —
  Graph, Swarm, Workflow comparison; when to use each
- [testing.md](references/testing.md) — pytest + Hypothesis idiom
  (example tests, PBT, fake-model injection for unit-testing agent
  loops). Locally authored; not vendored.

## Provenance

See [references/upstream.md](references/upstream.md) for source URL,
revision (`dea24563` for docs, `1847faec` for SDK), license
(Apache-2.0), and fetched-at per vendored file.

## Stack-specific anti-patterns

- **Hitting the real LLM from unit tests.** Strands defaults to Bedrock
  with Claude Sonnet 4 — every test call is a network round-trip plus a
  bill. Inject a fake `Model` (see `testing.md`) for unit tests; reserve
  live calls for explicit smoke / integration suites.
- **Forgetting AWS credentials in CI.** The Bedrock default fails fast
  if `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
  `AWS_BEARER_TOKEN_BEDROCK` are unset. Either configure them, switch
  the model provider explicitly to a fake / Ollama / Anthropic for
  CI, or skip Strands-touching tests when credentials are absent.
- **Shipping `load_tools_from_directory=True` to production.** The hot
  reloader watches `./tools/` for filesystem changes — convenient in
  dev, a directory-traversal / arbitrary-code-execution surface in
  prod. Use it during iteration; gate it behind an env flag before
  deploy.
- **Skipping `--strict` on mypy.** Strands' generics over `Model` and
  `Tool` lose their teeth without strict; you get `Any`-bleed across
  the agent loop and tools silently become untyped callables.
- **Defining a `@tool` without a docstring.** The LLM reads the
  docstring to decide when to invoke the tool. Empty / generic
  docstrings mean the agent will either over- or under-call the tool;
  ruff's `D103` (missing-docstring-in-public-function) catches this.
