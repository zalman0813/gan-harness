# Model providers — Amazon Bedrock (default)

Vendored from <https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/>.

The Strands SDK defaults to **Amazon Bedrock** with **Claude Sonnet 4** (`anthropic.claude-sonnet-4-20250514-v1:0`) in the region resolved from your AWS credentials. The `BedrockModel` class supports text generation, multimodal input, tool calling, guardrails, and prompt caching.

Other providers (OpenAI, Anthropic-direct, Google, Ollama, LiteLLM, custom) are documented upstream under `/docs/user-guide/concepts/model-providers/` but are **not** vendored in this Starter capsule. Add them if a future epic requires them.

## Basic setup

```python
from strands import Agent
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    temperature=0.3,
    top_p=0.8,
)
agent = Agent(model=bedrock_model)
response = agent("Tell me about Amazon Bedrock.")
```

## Configuration parameters

| Parameter | Purpose |
|---|---|
| `model_id` | Bedrock model identifier (e.g. `anthropic.claude-sonnet-4-20250514-v1:0`) |
| `temperature` | Randomness, 0–1 |
| `top_p` | Nucleus sampling cutoff |
| `max_tokens` | Maximum output tokens |
| `streaming` | Enable / disable streaming (default `True`); set `False` for non-streaming Bedrock models |
| `region_name` | AWS region (overrides credentials' default) |
| `guardrail_id` | Apply a Bedrock Guardrail policy |
| `cache_config` | Prompt-caching configuration |

## AWS credentials

Required IAM permissions:

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream` (for streaming, which is on by default)

Credentials resolution order (boto3 default):

1. Environment vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (and `AWS_SESSION_TOKEN` for SSO).
2. `~/.aws/credentials` via `aws configure`.
3. IAM instance / task roles (EC2 / ECS / Lambda — preferred for production).
4. Bedrock API key via `AWS_BEARER_TOKEN_BEDROCK`.

You can also pass a custom `boto3.Session` to `BedrockModel(..., boto_session=...)` for advanced scenarios (cross-account assume-role, custom retry config).

## Region handling

If you hit:

> "on-demand throughput isn't supported"

…prefix the model id with the regional inference-profile prefix (`us.` or `eu.`):

```python
BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")
```

If you hit:

> "invalid model identifier"

…the model isn't available in the region — either change region or fall back to a more widely available id without the inference-profile prefix:

```python
BedrockModel(model_id="anthropic.claude-3-5-sonnet-20241022-v2:0")
```

## Streaming behaviour

`BedrockModel(streaming=True)` (default) emits partial tokens that you can consume via `agent.stream_async(...)` — see [streaming.md](streaming.md).

If you must use a non-streaming Bedrock model (some embedding / classification variants don't stream), set `streaming=False` — the agent loop still works but `data` events are coalesced into a single chunk per cycle.

## Guardrails

```python
bedrock_model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    guardrail_id="my-guardrail-id",
)
```

When a guardrail intervenes, the `AgentResult.stop_reason` will be `"guardrail_intervention"`. Always handle this case explicitly — see [agent-loop.md](agent-loop.md#agentresult-and-stop-reasons).

## Prompt caching

Bedrock prompt caching is enabled via `cache_config`. Cache statistics surface on `AgentResult.metrics.accumulated_usage["cacheReadInputTokens"]`. The official docs recommend caching when:

- The system prompt is long and stable across invocations.
- The tool definitions are stable.
- Repeated invocations share a sizeable prefix.

For configuration details and exact `cache_config` shape, fetch <https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/> — this Starter capsule does not vendor the full reference.

## Multimodal inputs

Bedrock supports document and image inputs as either inline bytes or S3 references. See the upstream docs for the exact message-payload format; this is out of scope for the Starter capsule.

## Reasoning / extended thinking

Configure reasoning via the `additional_request_fields` parameter with a `thinking` budget tokens entry. Refer to upstream docs for current syntax — Anthropic / Bedrock keep tweaking the field names.

## Structured output

Strands implements structured output via tool calling — define a tool whose `inputSchema` is your target schema and instruct the model to call it. See [custom-tools.md](custom-tools.md) §3 for the schema-override pattern.

## Switching providers

Common alternatives (not vendored here — fetch upstream docs when needed):

- `strands.models.OpenAIModel` — OpenAI-compatible endpoints
- `strands.models.AnthropicModel` — Anthropic API direct
- `strands.models.LiteLLMModel` — LiteLLM proxy (100+ providers)
- `strands.models.OllamaModel` — local models

All of them accept `model=...` on `Agent(model=...)` interchangeably; the agent loop is provider-agnostic.
