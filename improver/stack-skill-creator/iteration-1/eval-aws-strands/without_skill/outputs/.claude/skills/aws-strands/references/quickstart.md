# Quickstart — install, credentials, first agent

Vendored from <https://strandsagents.com/docs/user-guide/quickstart/python/>.

## Prerequisites

- **Python 3.10+**
- **AWS credentials** with permissions to invoke Amazon Bedrock and Claude Sonnet 4 (the default model). See [Credentials](#credentials) below.

## Install

```bash
python -m venv .venv
source .venv/bin/activate           # macOS / Linux
# .venv\Scripts\activate.bat        # Windows CMD

pip install strands-agents
pip install strands-agents-tools strands-agents-builder   # optional but recommended
```

Packages:

| Package | Purpose |
|---|---|
| `strands-agents` | Core SDK (`Agent`, `@tool`, model providers, agent loop) |
| `strands-agents-tools` | Community-maintained ready-made tools (`calculator`, `current_time`, `http_request`, `file_read`, `python_repl`, …) |
| `strands-agents-builder` | Development helper for scaffolding/inspection |

## Credentials

The SDK defaults to Amazon Bedrock with Claude Sonnet 4. Required IAM permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`.

Any of these works:

- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `~/.aws/credentials` via `aws configure`
- IAM roles (EC2 / ECS / Lambda — recommended in production)
- Bedrock API key: `AWS_BEARER_TOKEN_BEDROCK`

If your region does not have Claude Sonnet 4 on-demand, use a regional prefix on the model id (`us.` or `eu.`) — see [model-providers.md](model-providers.md).

## Project layout

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

`agent.py` (complete working example, verbatim from the official quickstart):

```python
from strands import Agent, tool
from strands_tools import calculator, current_time

# Define a custom tool as a Python function using the @tool decorator
@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word (str): The input word to search in
        letter (str): The specific letter to count

    Returns:
        int: The number of occurrences of the letter in the word
    """
    if not isinstance(word, str) or not isinstance(letter, str):
        return 0

    if len(letter) != 1:
        raise ValueError("The 'letter' parameter must be a single character")

    return word.lower().count(letter.lower())


# Create an agent with tools from the community-driven strands-tools package
# as well as our custom letter_counter tool
agent = Agent(tools=[calculator, current_time, letter_counter])

# Ask the agent a question that uses the available tools
message = """I have 4 requests:

1. What is the time right now?
2. Calculate 3111696 / 740883
3. Tell me how many letter R's are in the word "strawberry" 🍓
4. Output a 5-line summary of what you just did
"""

agent(message)
```

Run:

```bash
python -u my_agent/agent.py
```

`agent(message)` invokes the agent loop synchronously and prints the final answer. Calling `agent(...)` returns an `AgentResult` with metrics — see [agent-loop.md](agent-loop.md).

## Inspecting the configured model

```python
from strands import Agent

agent = Agent()
print(agent.model.config)
```

## Overriding the default model with a string id

```python
from strands import Agent

agent = Agent(model="anthropic.claude-sonnet-4-20250514-v1:0")
```

## Overriding the default model with explicit BedrockModel config

```python
from strands import Agent
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.3,
)

agent = Agent(model=bedrock_model)
```

See [model-providers.md](model-providers.md) for the full parameter list.
