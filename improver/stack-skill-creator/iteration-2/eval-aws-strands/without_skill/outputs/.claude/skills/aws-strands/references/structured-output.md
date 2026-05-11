# Structured output — Pydantic schemas, validation

Distilled from:
- <https://strandsagents.com/docs/user-guide/concepts/agents/structured-output/>

Structured output replaces "parse the model's free-form text" with "model
must return JSON matching this Pydantic schema, validated before you see
it." Use when the agent's response is an extraction / classification / form
fill, not a chat turn.

## Per-invocation schema

```python
from pydantic import BaseModel
from strands import Agent

class PersonInfo(BaseModel):
    name: str
    age: int
    occupation: str

agent = Agent(tools=[])  # tools optional for pure extraction
result = agent(
    "John Smith is a 30-year-old software engineer.",
    structured_output_model=PersonInfo,
)
person: PersonInfo = result.structured_output
print(person.name, person.age, person.occupation)
```

Notes:

- The validated object lives at `result.structured_output`, **not** in the
  text message stream. `str(result)` still returns the assistant's prose.
- Strands implements this by injecting a synthetic tool whose JSON schema
  matches the Pydantic model. The model "calls" the tool to emit its
  structured response, and Strands intercepts and validates.
- Validation errors raise `StructuredOutputException` — catch it if the
  caller should retry with a relaxed schema.

## Agent-level default schema

```python
agent = Agent(
    tools=[...],
    structured_output_model=PersonInfo,  # default for every invocation
)
result = agent("John Smith is 30 and writes code.")
# result.structured_output is a PersonInfo
```

A per-invocation `structured_output_model=` overrides the agent-level
default for that one call.

## Streaming + structured output

Streaming (`stream_async`) works alongside structured output — the
intermediate events flow as usual, and the validated object appears in the
terminal `AgentResult` once the loop ends.

## When NOT to use structured output

- **Open-ended chat / drafting.** A schema there is a straitjacket.
- **When tools already return Pydantic models.** The model can already
  quote those fields verbatim; a top-level schema is redundant.
- **When the schema would be enormous / deeply nested.** Token cost on the
  schema spec scales with shape; prefer a flat schema and post-process if
  you need depth.

## Common failure modes

| Symptom                                          | Fix                                                                  |
|---------------------------------------------------|----------------------------------------------------------------------|
| `StructuredOutputException: ValidationError`     | Loosen field types (`int` → `int | None`) or add `Field(..., description=...)` to guide the model |
| Model produces text but `result.structured_output is None` | The model returned an `end_turn` without emitting the structured tool call. Re-prompt or add an explicit instruction. |
| Pydantic v1 errors                                | Strands targets Pydantic v2; pin `pydantic>=2`                        |
