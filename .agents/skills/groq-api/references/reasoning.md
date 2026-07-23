# Groq Reasoning Models Reference

Control how models think through complex problems with explicit reasoning parameters.

## Supported Models

| Model ID                       | Reasoning Effort Options | Reasoning Format          |
| ------------------------------ | ------------------------ | ------------------------- |
| `openai/gpt-oss-20b`           | `low`, `medium`, `high`  | `include_reasoning` only  |
| `openai/gpt-oss-120b`          | `low`, `medium`, `high`  | `include_reasoning` only  |
| `openai/gpt-oss-safeguard-20b` | `low`, `medium`, `high`  | `include_reasoning` only  |
| `qwen/qwen3-32b`               | `none`, `default`        | `raw`, `parsed`, `hidden` |

## Parameters

### reasoning_effort

Controls how much effort the model puts into reasoning.

**Qwen 3 32B:**

| Value     | Description                             |
| --------- | --------------------------------------- |
| `none`    | Disable reasoning (no reasoning tokens) |
| `default` | Enable reasoning                        |

**GPT-OSS models:**

| Value    | Description                         |
| -------- | ----------------------------------- |
| `low`    | Small number of reasoning tokens    |
| `medium` | Moderate number of reasoning tokens |
| `high`   | Large number of reasoning tokens    |

### reasoning_format (Qwen3 only)

Controls how reasoning is presented in the response.

| Value    | Description                                     |
| -------- | ----------------------------------------------- |
| `raw`    | Reasoning in `<think>` tags in content          |
| `parsed` | Reasoning in separate `message.reasoning` field |
| `hidden` | Only final answer returned                      |

**Note:** `raw` is not supported with JSON mode or tool use. Use `parsed` or `hidden` instead.

### include_reasoning (GPT-OSS only)

| Value   | Description                                              |
| ------- | -------------------------------------------------------- |
| `true`  | Include reasoning in `message.reasoning` field (default) |
| `false` | Exclude reasoning from response                          |

**Note:** Cannot be used together with `reasoning_format`.

## Quick Start

### Basic Reasoning (GPT-OSS)

```python
from groq import Groq

client = Groq()

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "How many r's are in strawberry?"}],
    reasoning_effort="high",
    temperature=0.6,
    max_completion_tokens=1024
)

print(response.choices[0].message.content)
print("Reasoning:", response.choices[0].message.reasoning)
```

### Parsed Reasoning (Qwen3)

```python
response = client.chat.completions.create(
    model="qwen/qwen3-32b",
    messages=[{"role": "user", "content": "Solve: If x + 5 = 12, what is x?"}],
    reasoning_format="parsed"
)

msg = response.choices[0].message
print("Answer:", msg.content)
print("Reasoning:", msg.reasoning)
```

### Raw Reasoning (Qwen3)

```python
response = client.chat.completions.create(
    model="qwen/qwen3-32b",
    messages=[{"role": "user", "content": "Explain quantum entanglement"}],
    reasoning_format="raw"
)

# Content includes <think>...</think> tags with reasoning
print(response.choices[0].message.content)
```

### Hidden Reasoning

```python
# Qwen3
response = client.chat.completions.create(
    model="qwen/qwen3-32b",
    messages=[{"role": "user", "content": "What is 15% of 80?"}],
    reasoning_format="hidden"
)

# GPT-OSS
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "What is 15% of 80?"}],
    include_reasoning=False
)
```

## Reasoning with Tool Use

Combine reasoning with function calling:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City and country"}
            },
            "required": ["location"]
        }
    }
}]

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    reasoning_effort="medium"
)
```

**Note:** When using tool use or JSON mode with Qwen3, `reasoning_format` must be `parsed` or `hidden` (not `raw`).

## Reasoning with JSON Mode

```python
response = client.chat.completions.create(
    model="qwen/qwen3-32b",
    messages=[{"role": "user", "content": "List 3 prime numbers as JSON"}],
    response_format={"type": "json_object"},
    reasoning_format="parsed"  # Required: raw not supported with JSON mode
)
```

## Streaming Reasoning

```python
stream = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "Explain relativity"}],
    reasoning_effort="high",
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Response Structure

### GPT-OSS Response

```json
{
  "role": "assistant",
  "content": "The answer is...",
  "reasoning": "Let me think through this step by step..."
}
```

### Qwen3 Parsed Response

```json
{
  "role": "assistant",
  "content": "The answer is...",
  "reasoning": "First I need to consider..."
}
```

### Qwen3 Raw Response

```json
{
  "role": "assistant",
  "content": "<think>First I need to consider...</think>The answer is..."
}
```

## Recommended Parameters

| Parameter               | Default | Recommended                | Description                            |
| ----------------------- | ------- | -------------------------- | -------------------------------------- |
| `temperature`           | 0.6     | 0.5-0.7                    | Lower = more deterministic             |
| `max_completion_tokens` | 1024    | Increase for complex tasks | May need higher for detailed reasoning |
| `top_p`                 | 0.95    | 0.95                       | Diversity of token selection           |
| `seed`                  | -       | Set for reproducibility    | Important for benchmarking             |

## Best Practices

### Prompt Engineering

1. **Include all instructions in user message** - Avoid system prompts with reasoning models
2. **Use zero-shot prompting** - Few-shot examples can confuse reasoning models
3. **Request explicit steps** - Ask for intermediate calculations and validation

### Temperature

- **0.5**: More consistent mathematical proofs
- **0.7**: More creative problem-solving
- Avoid very low (< 0.5) or high (> 0.8) temperatures

### Token Management

- Default `max_completion_tokens` (1024) may be too low for complex reasoning
- Monitor token usage and increase limits for detailed proofs
- Reasoning tokens count toward usage

## TypeScript

```typescript
import Groq from 'groq-sdk';

const client = new Groq();

// GPT-OSS with reasoning effort
const response = await client.chat.completions.create({
  model: 'openai/gpt-oss-20b',
  messages: [{ role: 'user', content: "How many r's in strawberry?" }],
  reasoning_effort: 'high',
  temperature: 0.6,
  max_completion_tokens: 1024,
});

console.log(response.choices[0].message.content);
console.log('Reasoning:', response.choices[0].message.reasoning);

// Qwen3 with parsed reasoning
const qwenResponse = await client.chat.completions.create({
  model: 'qwen/qwen3-32b',
  messages: [{ role: 'user', content: 'Explain gravity' }],
  reasoning_format: 'parsed',
});

console.log(qwenResponse.choices[0].message.content);
console.log('Reasoning:', qwenResponse.choices[0].message.reasoning);
```

## Use Cases

- **Math problems**: Step-by-step solutions with verification
- **Logic puzzles**: Explicit reasoning chains
- **Code debugging**: Systematic analysis of issues
- **Decision making**: Transparent reasoning for explainability
- **Complex analysis**: Multi-step research and synthesis
