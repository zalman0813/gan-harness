# Vendoring provenance — aws-strands stack skill

All references in this directory were vendored from public, Apache-2.0 sources. Re-vendor by re-fetching from the URL and updating the `fetched_at` column; do not edit vendored files in place.

| File | Source URL | Revision / version | License | Fetched_at |
|---|---|---|---|---|
| `quickstart.md` | https://strandsagents.com/docs/user-guide/quickstart/python/ | live (no public SHA) | Apache-2.0 | 2026-05-11 |
| `quickstart.md` | https://github.com/strands-agents/sdk-python (README) | `main` HEAD as of fetch | Apache-2.0 | 2026-05-11 |
| `quickstart.md` | https://pypi.org/project/strands-agents/ | strands-agents 1.39.0 (released 2026-05-08) | Apache-2.0 | 2026-05-11 |
| `agents.md` | https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/ | live (no public SHA) | Apache-2.0 | 2026-05-11 |
| `agents.md` | https://strandsagents.com/ (landing-page concept index) | live | Apache-2.0 | 2026-05-11 |
| `tools.md` | https://strandsagents.com/docs/user-guide/concepts/tools/ | live (no public SHA) | Apache-2.0 | 2026-05-11 |
| `tools.md` | https://pypi.org/project/strands-agents/ (custom-tool example) | strands-agents 1.39.0 | Apache-2.0 | 2026-05-11 |
| `model-providers.md` | https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/ | live (no public SHA) | Apache-2.0 | 2026-05-11 |
| `model-providers.md` | https://pypi.org/project/strands-agents/ (Gemini example) | strands-agents 1.39.0 | Apache-2.0 | 2026-05-11 |
| `testing.md` | https://strandsagents.com/docs/user-guide/evals-sdk/quickstart/ | live (no public SHA) | Apache-2.0 | 2026-05-11 |

## Notes on coverage and gaps

- Scope is **Starter** (5 seed topics) as requested. Topics deliberately omitted from this vendor pass: deployment (AgentCore / Lambda / Fargate / EKS / Docker / Terraform), multi-agent patterns deep dive (swarms / graphs / workflows), observability (OpenTelemetry tracing), session management (file / S3 / repo backends), conversation management strategies, guardrails-as-a-feature deep dive, bidirectional streaming. Re-run a Comprehensive vendor pass when those become needed.
- Several `strandsagents.com` URLs returned 404 during the initial vendor (e.g., `/concepts/agents/` index, `/concepts/multi-agent/`, `/concepts/tools/python-tools/`). The content under those branches was captured indirectly through landing pages, the GitHub README, and the PyPI page — all canonical. If those URLs come back online in a later doc revision, re-fetch and update this log.
- `strandsagents.com` does not publish a public commit SHA per page. The `Revision / version` column records the PyPI release closest in time for code-side material; doc-site fetches are tracked by `fetched_at` only.
- Licensing: SDK + docs repo (`strands-agents/sdk-python`, `strands-agents/docs`) are both Apache-2.0. Vendored code snippets and doc prose are usable here under the license terms; retain attribution to https://strandsagents.com/ and the `strands-agents` GitHub org in any downstream redistribution.
