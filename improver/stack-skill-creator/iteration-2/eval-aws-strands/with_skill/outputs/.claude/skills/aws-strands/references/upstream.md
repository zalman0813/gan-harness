# Upstream provenance — aws-strands stack skill

All reference files in this directory were vendored verbatim from the
official AWS Strands Agents documentation repository. Re-vendor by
fetching the same paths at a newer revision and updating the
`revision` / `fetched_at` columns below.

The docs are MDX (Markdown + Astro components such as `<Tabs>` /
`<Tab>` and snippet directives `--8<-- "..."`). The MDX was preserved
as-is so downstream agents can see the original structure; renderers
that read pure Markdown will surface the JSX literally.

| File | Source URL | Revision (SHA) | License | Fetched at |
|---|---|---|---|---|
| `quickstart-python.md` | https://github.com/strands-agents/docs/blob/main/src/content/docs/user-guide/quickstart/python.mdx | `dea24563` | Apache-2.0 | 2026-05-12 |
| `agent-loop.md` | https://github.com/strands-agents/docs/blob/main/src/content/docs/user-guide/concepts/agents/agent-loop.mdx | `dea24563` | Apache-2.0 | 2026-05-12 |
| `tools-overview.md` | https://github.com/strands-agents/docs/blob/main/src/content/docs/user-guide/concepts/tools/index.mdx | `dea24563` | Apache-2.0 | 2026-05-12 |
| `model-provider-anthropic.md` | https://github.com/strands-agents/docs/blob/main/src/content/docs/user-guide/concepts/model-providers/anthropic.mdx | `dea24563` | Apache-2.0 | 2026-05-12 |
| `multi-agent-patterns.md` | https://github.com/strands-agents/docs/blob/main/src/content/docs/user-guide/concepts/multi-agent/multi-agent-patterns.mdx | `dea24563` | Apache-2.0 | 2026-05-12 |
| `testing.md` | Authored locally (no upstream Strands doc; distils Hypothesis + Strands `Agent.invoke` test patterns) | n/a | n/a | 2026-05-12 |

Repository: <https://github.com/strands-agents/docs>
SDK repository: <https://github.com/strands-agents/sdk-python>
SDK revision pinned in examples: `1847faec` (sdk-python, main, 2026-05-12)
Canonical site: <https://strandsagents.com/>

## Notes on fidelity

- `quickstart-python.md` is 557 lines and `tools-overview.md` is 575 —
  both slightly exceed the stack-skill-creator's ~500-line soft cap.
  They were kept as single files because the upstream document is a
  single canonical topic page; splitting would create artificial topic
  boundaries that diverge from the upstream table of contents. Re-vendor
  by replacing each file wholesale.
- The MDX `<Tabs>` blocks include both Python and TypeScript code
  samples. The TypeScript snippets are loaded by `--8<-- "..."`
  directives that reference sibling `.ts` files in the upstream repo —
  those `.ts` files are NOT vendored here because this stack skill is
  Python-only (`aws-strands` defaults to the Python SDK). If you later
  add TypeScript support, vendor the `.ts` siblings and unwrap the
  snippet directives.
- The default model provider documented in upstream is Amazon Bedrock
  with Claude Sonnet 4. The Anthropic provider page is vendored because
  the user request flagged Strands as the Anthropic-recommended Python
  agent framework; agents that talk to Anthropic's API directly use the
  `AnthropicModel` path shown in `model-provider-anthropic.md`.
