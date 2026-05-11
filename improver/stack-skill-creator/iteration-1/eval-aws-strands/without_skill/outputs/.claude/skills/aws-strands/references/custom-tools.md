# Custom tools (`@tool` decorator, class-based, async, module)

Vendored from <https://strandsagents.com/docs/user-guide/concepts/tools/custom-tools/>.

Python supports three ways to define a tool:

1. A **function** with the `@tool` decorator (the common case).
2. A **class** with multiple `@tool`-decorated methods (when tools share resources).
3. A **module** with `TOOL_SPEC` + a matching function (for cases where you need full control of the JSON schema).

Tool schemas are generated from **type hints + docstrings** at import time. The first paragraph of the docstring becomes the tool description; the `Args:` section maps parameters to descriptions. Missing a type hint or having a vague docstring silently degrades the model's tool routing — treat tool signatures as part of the public contract.

## 1. Function tool (basic)

```python
from strands import tool

@tool
def weather_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: The name of the city
        days: Number of days for the forecast
    """
    return f"Weather forecast for {city} for the next {days} days..."
```

Default values (`days: int = 3`) appear in the generated JSON schema automatically.

## 2. Overriding name and description

```python
@tool(name="get_weather", description="Retrieves weather forecast for a specified location")
def weather_forecast(city: str, days: int = 3) -> str:
    """Implementation function for weather forecasting.

    Args:
        city: The name of the city
        days: Number of days for the forecast
    """
    return f"Weather forecast for {city} for the next {days} days..."
```

Use this when the function name internally differs from what you want the model to see, or when the docstring contains implementation notes that shouldn't leak into the prompt.

## 3. Custom input schema (when docstring inference is not enough)

```python
@tool(
    inputSchema={
        "json": {
            "type": "object",
            "properties": {
                "shape": {
                    "type": "string",
                    "enum": ["circle", "rectangle"],
                    "description": "The shape type"
                },
                "radius": {"type": "number", "description": "Radius for circle"},
                "width": {"type": "number", "description": "Width for rectangle"},
                "height": {"type": "number", "description": "Height for rectangle"}
            },
            "required": ["shape"]
        }
    }
)
def calculate_area(shape: str, radius: float = None, width: float = None, height: float = None) -> float:
    """Calculate area of a shape."""
    if shape == "circle":
        return 3.14159 * radius ** 2
    elif shape == "rectangle":
        return width * height
    return 0.0
```

Use this for `enum` constraints, conditional required fields, and other JSON-schema features that can't be expressed in Python type hints.

## 4. Context-aware tool

A tool can access the live `ToolContext` (agent reference, invocation state, message history) by setting `context=True`:

```python
from strands import tool, ToolContext

@tool(context=True)
def get_self_name(tool_context: ToolContext) -> str:
    return f"The agent name is {tool_context.agent.name}"

# or name the parameter explicitly:
@tool(context="context")
def get_invocation_state(context: ToolContext) -> str:
    return f"Invocation state: {context.invocation_state['custom_data']}"
```

The context parameter does **not** appear in the tool's JSON schema — the model never sees it.

## 5. Async tool with progress streaming

A tool may be an `async def` function. It may also `yield` intermediate progress strings (which surface in `stream_async` events) before returning a final value.

```python
import asyncio
from datetime import datetime
from strands import tool

@tool
async def process_dataset(records: int) -> str:
    """Process records with progress updates."""
    start = datetime.now()

    for i in range(records):
        await asyncio.sleep(0.1)
        if i % 10 == 0:
            elapsed = datetime.now() - start
            yield f"Processed {i}/{records} records in {elapsed.total_seconds():.1f}s"

    yield f"Completed {records} records in {(datetime.now() - start).total_seconds():.1f}s"
```

Async tools require the agent to be driven via `stream_async`; calling `agent(...)` synchronously when async tools are registered will still work but the progress yields are buffered.

## 6. Class-based tools (shared state)

Use a class when several tools share resources (DB pool, HTTP session, in-memory cache). Decorate **methods** with `@tool` and pass the bound methods into the agent:

```python
from strands import Agent, tool

class DatabaseTools:
    def __init__(self, connection_string):
        self.connection = self._establish_connection(connection_string)

    def _establish_connection(self, connection_string):
        # In real code, open a pool. Returning a dict here for illustration.
        return {"connected": True, "db": "example_db"}

    @tool
    def query_database(self, sql: str) -> dict:
        """Run a SQL query against the database.

        Args:
            sql: The SQL query to execute
        """
        return {"results": f"Query results for: {sql}", "connection": self.connection}

    @tool
    def insert_record(self, table: str, data: dict) -> str:
        """Insert a new record into the database.

        Args:
            table: The table name
            data: The data to insert as a dictionary
        """
        return f"Inserted data into {table}: {data}"

db_tools = DatabaseTools("example_connection_string")
agent = Agent(tools=[db_tools.query_database, db_tools.insert_record])
```

`self` is filtered out of the generated schema — the model only sees `sql` / `table` / `data`.

## 7. Module-based tool (full control)

If you need full control of the schema and dispatch, define a module with a `TOOL_SPEC` dict and a function that takes the raw `tool` dict:

```python
TOOL_SPEC = {
    "name": "weather_forecast",
    "description": "Get weather forecast for a city.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The name of the city"},
                "days": {
                    "type": "integer",
                    "description": "Number of days for the forecast",
                    "default": 3
                }
            },
            "required": ["city"]
        }
    }
}

def weather_forecast(tool, **kwargs):
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]

    city = tool_input.get("city", "")
    days = tool_input.get("days", 3)

    result = f"Weather forecast for {city} for the next {days} days..."

    return {
        "toolUseId": tool_use_id,
        "status": "success",
        "content": [{"text": result}]
    }
```

Async variant:

```python
TOOL_SPEC = {
    "name": "call_api",
    "description": "Call my API asynchronously.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

async def call_api(tool, **kwargs):
    await asyncio.sleep(5)
    result = "API result"

    return {
        "toolUseId": tool["toolUseId"],
        "status": "success",
        "content": [{"text": result}],
    }
```

## Tool response format

A tool's return value is normalised to a `ToolResult`:

```python
{
    "toolUseId": str,
    "status": "success" | "error",
    "content": list[dict],
}
```

Success example:

```python
{
    "toolUseId": "tool-123",
    "status": "success",
    "content": [
        {"text": "Operation completed successfully"},
        {"json": {"results": [1, 2, 3], "total": 3}},
    ]
}
```

Error example:

```python
{
    "toolUseId": "tool-123",
    "status": "error",
    "content": [
        {"text": "Error: Unable to process request due to invalid parameters"},
    ]
}
```

Return-value handling for `@tool`-decorated functions:

- Returning a string (or other simple value) → wrapped as `{"text": str(result)}` automatically.
- Returning a dict matching the `ToolResult` shape → used as-is.
- Raising an exception → converted to an error response automatically; the model sees the exception message.

## Anti-patterns

- **Tool function with no docstring or no type hints.** The schema gets generated with empty / `Any`-typed parameters and the model can't route correctly. Always include both.
- **Returning unbounded data.** Tool results land back in the prompt. Cap responses; offload large payloads to disk/S3 and return a handle.
- **Catching all exceptions inside the tool and returning a string.** Better to let it raise — Strands converts exceptions to structured errors and the model can plan a retry. Swallowing errors makes them invisible.
- **One mega-tool that takes a free-form `action: str` parameter.** Split it into N small tools, one per capability — the model is much better at picking from a typed menu than at populating an opaque action string.
