# Model providers — Bedrock, Anthropic, OpenAI, Ollama, …

Distilled from:
- <https://strandsagents.com/docs/user-guide/concepts/model-providers/>
- <https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/>
- <https://strandsagents.com/docs/user-guide/concepts/model-providers/anthropic/>

A **model provider** is the service that actually runs the LLM. Strands ships
adapters for many providers behind a single `Agent(model=...)` interface so
you can swap providers without touching the rest of the agent.

## Officially supported (Python)

| Provider          | Import                                        |
|-------------------|------------------------------------------------|
| Amazon Bedrock    | `from strands.models.bedrock import BedrockModel`     |
| Amazon Nova       | `from strands.models.nova import NovaModel`           |
| Anthropic API     | `from strands.models.anthropic import AnthropicModel` |
| Google            | `from strands.models.google import GoogleModel`       |
| LiteLLM           | `from strands.models.litellm import LiteLLMModel`     |
| llama.cpp         | `from strands.models.llamacpp import LlamaCppModel`   |
| LlamaAPI          | `from strands.models.llamaapi import LlamaAPIModel`   |
| MistralAI         | `from strands.models.mistral import MistralModel`     |
| Ollama            | `from strands.models.ollama import OllamaModel`       |
| OpenAI            | `from strands.models.openai import OpenAIModel`       |
| SageMaker         | `from strands.models.sagemaker import SageMakerModel` |
| Writer            | `from strands.models.writer import WriterModel`       |

Community-maintained: Cohere, Fireworks AI, NVIDIA NIM, vLLM.

Custom providers can implement the `Model` protocol — see
<https://strandsagents.com/docs/user-guide/concepts/model-providers/custom_model_provider/>.

## Default behaviour

`Agent(...)` with **no** `model=` parameter falls back to:

```python
from strands.models.bedrock import BedrockModel
BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
```

So when you read a codebase with bare `Agent(tools=[...])` calls, mentally
substitute the Bedrock default — AWS credentials are an implicit dependency.

## Explicit examples

### Amazon Bedrock

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
)
agent = Agent(model=model, tools=[...])
```

Auth uses the standard AWS credential chain (`~/.aws/credentials`, env vars,
IAM role, etc.). The role needs `bedrock:InvokeModel` on the specific model
ARN.

### Anthropic API direct

```python
from strands import Agent
from strands.models.anthropic import AnthropicModel

model = AnthropicModel(
    model_id="claude-opus-4-20250514",
    api_key="...",  # or rely on ANTHROPIC_API_KEY env var
)
agent = Agent(model=model, tools=[...])
```

Use this when you don't have Bedrock access or want to avoid AWS dependency.

### OpenAI

```python
from strands import Agent
from strands.models.openai import OpenAIModel

model = OpenAIModel(model_id="gpt-4.1", api_key="...")  # or OPENAI_API_KEY env
agent = Agent(model=model, tools=[...])
```

### Ollama (local)

```python
from strands import Agent
from strands.models.ollama import OllamaModel

model = OllamaModel(host="http://localhost:11434", model_id="llama3")
agent = Agent(model=model, tools=[...])
```

Useful for offline development and tests — no network calls leave the box.

## Switching providers without breaking tools

Tool definitions (`@tool` functions) are provider-agnostic. The same tool
list works against Bedrock-Claude, Anthropic-API-Claude, OpenAI, Ollama,
etc. — Strands translates the tool spec into whichever schema the target
provider expects (Bedrock converse, Anthropic messages, OpenAI function
calling, etc.).

What **does** change across providers:

- Available models (Claude family only on Bedrock-Anthropic and Anthropic;
  OpenAI has GPT only; Ollama exposes whatever you've pulled locally)
- Tool-calling fidelity (smaller / older models drop tool calls more often)
- Cost / latency profile
- Streaming event shapes (Strands normalises most but not all)
