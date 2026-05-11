# Strands Agents — Model Providers

Source: https://strandsagents.com/docs/user-guide/concepts/model-providers/ (Amazon Bedrock canonical), https://pypi.org/project/strands-agents/ (provider examples). Vendored from official docs; see `upstream.md`.

Supported providers (Python SDK): **Amazon Bedrock** (default), **Anthropic**, **OpenAI**, **Google Gemini**, **Ollama**, **LiteLLM**, **Llama**, **Writer**, and custom providers. The TypeScript SDK omits Ollama and LiteLLM and lacks bidirectional streaming and agent steering.

## Amazon Bedrock (default)

Default model: `anthropic.claude-sonnet-4-20250514-v1:0` via the user's default AWS region.

### Prerequisites

- AWS account with Bedrock access enabled in the target region.
- IAM permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`.
- AWS credentials via CLI / env / IAM role / custom boto3 session.

### Basic Python usage

```python
from strands import Agent

agent = Agent()
response = agent("Tell me about Amazon Bedrock.")
```

### Custom Bedrock configuration

```python
from strands import Agent
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="us.amazon.nova-premier-v1:0",
    temperature=0.3,
    top_p=0.8,
)
agent = Agent(model=bedrock_model)
response = agent("Tell me about Amazon Bedrock.")
```

### Common `BedrockModel` parameters

| Python key | Meaning |
|---|---|
| `model_id` | Bedrock model identifier (regional or base). |
| `region_name` | AWS region (e.g., `us-west-2`). |
| `temperature` | Sampling temperature 0–1. |
| `top_p` | Nucleus sampling probability. |
| `max_tokens` | Output token cap. |
| `streaming` | Enable or disable streaming. |
| `guardrail_id` | Bedrock guardrail to apply. |
| `cache_config` | Prompt caching strategy. |

### Guardrails

```python
from strands import Agent
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    guardrail_id="your-guardrail-id",
    guardrail_version="DRAFT",
)
agent = Agent(model=bedrock_model)
```

### On-demand throughput / regional prefix

Bare model IDs (e.g., `anthropic.claude-sonnet-4-20250514-v1:0`) often error with "on-demand throughput isn't supported". Use the regional prefix that matches the target inference profile:

```
us.anthropic.claude-sonnet-4-20250514-v1:0
eu.anthropic.claude-sonnet-4-20250514-v1:0
```

If the region does not support inference profiles, fall back to a base model that does — e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`.

### Multimodal call

```python
response = agent([
    {
        "document": {
            "format": "txt",
            "name": "example",
            "source": {"bytes": b"Document content"}
        }
    },
    {"text": "Tell me about the document."}
])
```

### Structured output (Bedrock + Pydantic)

```python
from pydantic import BaseModel, Field
from strands import Agent


class ProductAnalysis(BaseModel):
    name: str = Field(description="Product name")
    price: float = Field(description="Price in USD")


agent = Agent()
result = agent.structured_output(ProductAnalysis, "Analyze this product...")
```

## Google Gemini

```python
from strands import Agent
from strands.models.gemini import GeminiModel

gemini_model = GeminiModel(
    client_args={"api_key": "your_gemini_api_key"},
    model_id="gemini-2.5-flash",
    params={"temperature": 0.7}
)
agent = Agent(model=gemini_model)
agent("Tell me about Agentic AI")
```

## Other providers (high level)

- **Anthropic direct**: `from strands.models.anthropic import AnthropicModel`. Configure with `client_args={"api_key": ...}` and a `model_id` like `claude-sonnet-4-20250514`.
- **OpenAI**: `from strands.models.openai import OpenAIModel`. Same shape — `client_args` + `model_id` (`gpt-4.1`, `gpt-4o`, etc.).
- **Ollama**: `from strands.models.ollama import OllamaModel` for local model hosting.
- **LiteLLM**: `from strands.models.litellm import LiteLLMModel` proxies to 100+ providers via LiteLLM's router.
- **Writer / Llama**: similar interface; see upstream docs for each.

## System-prompt caching across providers

`SystemContentBlock(cachePoint={"type": "default"})` is Bedrock-specific (5-minute TTL). Anthropic direct and OpenAI have their own caching mechanisms — consult the per-provider page.
