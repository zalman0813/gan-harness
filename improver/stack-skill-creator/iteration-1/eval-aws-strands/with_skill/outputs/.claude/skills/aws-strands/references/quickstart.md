# Strands Agents — Python Quickstart

Source: https://strandsagents.com/docs/user-guide/quickstart/python/ and https://github.com/strands-agents/sdk-python (Apache-2.0). Vendored verbatim where possible; see `upstream.md` for fetched-at.

## Requirements

- Python 3.10+
- AWS credentials configured (Bedrock is the default provider; other providers can replace it — see `model-providers.md`)

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install strands-agents
pip install strands-agents-tools strands-agents-builder
```

Notes:
- Install name is `strands-agents`; the import is `from strands import ...`.
- Install name for the pre-built tools package is `strands-agents-tools`; the import is `from strands_tools import ...`.
- `strands-agents-builder` is optional and only useful for the agent-builder workflow.

## First agent (pre-built calculator tool)

```python
from strands import Agent
from strands_tools import calculator

agent = Agent(tools=[calculator])
agent("What is the square root of 1764")
```

## First agent with a custom tool

```python
from strands import Agent, tool
from strands_tools import calculator, current_time


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


agent = Agent(tools=[calculator, current_time, letter_counter])

message = """I have 4 requests:
1. What is the time right now?
2. Calculate 311169 / 740883
3. Tell me how many letter R's are in the word "strawberry"
"""

agent(message)
```

## Credentials (default Bedrock provider)

The default model is Claude Sonnet 4 via Amazon Bedrock. Configure AWS credentials through any of:

- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
- AWS credentials file (`~/.aws/credentials`)
- IAM role (when running on EC2 / ECS / EKS / Lambda)
- Bearer tokens for federated identity

IAM permissions required: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`.

## Debug logging

```python
import logging
from strands import Agent

logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()])

agent = Agent()
agent("Hello!")
```

## Model selection at construction

By string model ID (uses the default Bedrock provider):

```python
agent = Agent(model="anthropic.claude-sonnet-4-20250514-v1:0")
```

By explicit `BedrockModel` (region + parameters):

```python
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.3,
)
agent = Agent(model=bedrock_model)
```

See `model-providers.md` for non-Bedrock providers.

## Streaming with async iterators

```python
import asyncio
from strands import Agent

agent = Agent(callback_handler=None)


async def process_streaming_response():
    agent_stream = agent.stream_async("What is 25 * 48?")
    async for event in agent_stream:
        if "data" in event:
            print(event["data"], end="", flush=True)


asyncio.run(process_streaming_response())
```

## Custom callback handler

```python
def callback_handler(**kwargs):
    if "data" in kwargs:
        logger.info(kwargs["data"])
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        logger.info(f"Using tool: {tool.get('name')}")


agent = Agent(tools=[shell], callback_handler=callback_handler)
```

## Hot-reloading tools from a directory

```python
from strands import Agent

agent = Agent(load_tools_from_directory=True)
response = agent("Use any tools you find in the tools directory")
```

This scans `./tools/` for tool modules; see `tools.md` for module structure.
