# Groq API Reference

Base URL: `https://api.groq.com/openai/v1`

## Chat Completions

`POST /chat/completions`

### Required Parameters

| Parameter  | Type   | Description              |
| ---------- | ------ | ------------------------ |
| `model`    | string | Model ID (see models.md) |
| `messages` | array  | Conversation messages    |

### Common Optional Parameters

| Parameter               | Type          | Default | Description                                      |
| ----------------------- | ------------- | ------- | ------------------------------------------------ |
| `temperature`           | number        | 1       | 0-2, lower = more deterministic                  |
| `top_p`                 | number        | 1       | 0-1, nucleus sampling                            |
| `max_completion_tokens` | integer       | -       | Max output tokens                                |
| `stream`                | boolean       | false   | Enable streaming                                 |
| `stop`                  | string/array  | -       | Stop sequences (up to 4)                         |
| `tools`                 | array         | -       | Function definitions                             |
| `tool_choice`           | string/object | auto    | `auto`, `none`, `required`, or specific function |
| `response_format`       | object        | -       | `{"type": "json_object"}` or JSON schema         |
| `seed`                  | integer       | -       | For deterministic outputs                        |

### Reasoning Parameters (Qwen3, GPT-OSS)

| Parameter           | Type    | Values                                     |
| ------------------- | ------- | ------------------------------------------ |
| `reasoning_effort`  | string  | `none`, `default`, `low`, `medium`, `high` |
| `reasoning_format`  | string  | `hidden`, `raw`, `parsed`                  |
| `include_reasoning` | boolean | Include reasoning in response              |

### Agentic Parameters

| Parameter          | Type   | Description               |
| ------------------ | ------ | ------------------------- |
| `documents`        | array  | Context documents for RAG |
| `search_settings`  | object | Web search configuration  |
| `citation_options` | string | `enabled` or `disabled`   |

### Service Tiers

| Tier          | Description                  |
| ------------- | ---------------------------- |
| `on_demand`   | Default, standard processing |
| `flex`        | Lower cost, may queue        |
| `performance` | Prioritized processing       |
| `auto`        | Auto-select based on limits  |

### Response Object

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1730241104,
  "model": "openai/gpt-oss-20b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "...",
        "tool_calls": []
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 556,
    "total_tokens": 574,
    "queue_time": 0.037,
    "prompt_time": 0.001,
    "completion_time": 0.463
  }
}
```

## Responses API (Beta)

`POST /responses` - Simpler interface for single-turn requests.

```python
response = client.responses.create(
    model="openai/gpt-oss-120b",
    input="Tell me a three sentence bedtime story."
)
```

### Parameters

| Parameter           | Type         | Description                |
| ------------------- | ------------ | -------------------------- |
| `input`             | string/array | Text input or conversation |
| `model`             | string       | Model ID                   |
| `instructions`      | string       | System message             |
| `max_output_tokens` | integer      | Output limit               |
| `reasoning`         | object       | Reasoning config           |
| `text`              | object       | Response format config     |
| `tools`             | array        | Available tools            |

## Audio Transcription

`POST /audio/transcriptions`

```python
with open("audio.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=f,
        language="en",  # ISO-639-1 code
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"]
    )
```

### Parameters

| Parameter                 | Type   | Default  | Description                                      |
| ------------------------- | ------ | -------- | ------------------------------------------------ |
| `model`                   | string | required | `whisper-large-v3` or `whisper-large-v3-turbo`   |
| `file`                    | file   | -        | Audio file (flac, mp3, mp4, m4a, ogg, wav, webm) |
| `url`                     | string | -        | Audio URL (alternative to file)                  |
| `language`                | string | -        | ISO-639-1 language code                          |
| `prompt`                  | string | -        | Guide transcription style                        |
| `response_format`         | string | json     | `json`, `text`, `verbose_json`                   |
| `timestamp_granularities` | array  | segment  | `word`, `segment`                                |

## Audio Translation

`POST /audio/translations` - Translates audio to English.

```python
translation = client.audio.translations.create(
    model="whisper-large-v3",
    file=audio_file
)
```

## Text-to-Speech

`POST /audio/speech`

```python
response = client.audio.speech.create(
    model="playai-tts",
    input="Hello, world!",
    voice="Fritz-PlayAI",
    response_format="wav",
    speed=1.0
)
response.write_to_file("output.wav")
```

### Parameters

| Parameter         | Type    | Default  | Description                          |
| ----------------- | ------- | -------- | ------------------------------------ |
| `model`           | string  | required | TTS model (e.g., `playai-tts`)       |
| `input`           | string  | required | Text to synthesize                   |
| `voice`           | string  | required | Voice ID                             |
| `response_format` | string  | mp3      | `flac`, `mp3`, `mulaw`, `ogg`, `wav` |
| `sample_rate`     | integer | 48000    | 8000-48000                           |
| `speed`           | number  | 1        | 0.5-5                                |

## Batch API

Process large volumes of requests asynchronously.

### Upload Batch File

```python
# Create JSONL file
requests = [
    {"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions",
     "body": {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "Hello"}]}}
]

# Upload file (use requests library)
import requests
response = requests.post(
    "https://api.groq.com/openai/v1/files",
    headers={"Authorization": f"Bearer {api_key}"},
    files={"file": ("batch.jsonl", open("batch.jsonl", "rb"))},
    data={"purpose": "batch"}
)
file_id = response.json()["id"]
```

### Create Batch

```python
batch = client.batches.create(
    input_file_id=file_id,
    endpoint="/v1/chat/completions",
    completion_window="24h"  # 24h to 7d
)
```

### Monitor Batch

```python
batch = client.batches.retrieve(batch.id)
print(batch.status)  # validating, in_progress, completed, failed, expired

if batch.status == "completed":
    results = client.files.content(batch.output_file_id)
```

### Cancel Batch

```python
client.batches.cancel(batch.id)
```

## Files API

### Upload

```python
# Using requests library
response = requests.post(
    "https://api.groq.com/openai/v1/files",
    headers={"Authorization": f"Bearer {api_key}"},
    files={"file": ("data.jsonl", open("data.jsonl", "rb"))},
    data={"purpose": "batch"}
)
```

### List / Retrieve / Delete

```python
files = client.files.list()
file_info = client.files.info(file_id)
content = client.files.content(file_id)
client.files.delete(file_id)
```

## Models API

```python
# List all models
models = client.models.list()

# Get specific model
model = client.models.retrieve("llama-3.3-70b-versatile")
print(model.context_window)
```

## Fine-Tuning (Closed Beta)

```python
# Create fine-tuning job
ft = client.fine_tunings.create(
    input_file_id=file_id,
    name="my-fine-tune",
    type="lora",
    base_model="llama-3.1-8b-instant"
)

# List / Get / Delete
fts = client.fine_tunings.list()
ft = client.fine_tunings.get(id=ft_id)
client.fine_tunings.delete(id=ft_id)
```

## Structured Outputs (JSON Schema)

Force model output to match a schema with guaranteed or best-effort compliance.

### Two Modes

| Mode                              | Guarantee              | Requirements                                       |
| --------------------------------- | ---------------------- | -------------------------------------------------- |
| **Strict** (`strict: true`)       | 100% schema compliance | All fields required, `additionalProperties: false` |
| **Best-effort** (`strict: false`) | Best-effort, may error | More flexible constraints                          |

### Model Support

**Strict mode (`strict: true`):** `openai/gpt-oss-20b`, `openai/gpt-oss-120b`

**Best-effort (`strict: false`):** Above plus `kimi-k2-instruct-0905`, `llama-4-*`, `gpt-oss-safeguard-20b`

### Strict Mode (Recommended for Production)

Guaranteed schema compliance using constrained decoding:

```python
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "system", "content": "Extract product review information."},
        {"role": "user", "content": "I love the UltraSound Headphones! Great noise cancellation. 4.5/5 stars."}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "product_review",
            "strict": True,  # Guaranteed compliance
            "schema": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "rating": {"type": "number"},
                    "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                    "key_features": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["product_name", "rating", "sentiment", "key_features"],
                "additionalProperties": False  # Required for strict mode
            }
        }
    }
)
```

### Best-Effort Mode

More flexible, broader model support, but may occasionally error:

```python
response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "schema_name",
            "strict": False,  # Or omit (defaults to false)
            "schema": {...}
        }
    }
)
```

### Schema Requirements for Strict Mode

1. **All fields must be required:**

```json
{ "required": ["field1", "field2", "field3"] }
```

2. **All objects need `additionalProperties: false`:**

```json
{ "additionalProperties": false }
```

3. **Optional fields use union with null:**

```json
{ "nickname": { "type": ["string", "null"] } }
```

### Using Pydantic (Python)

```python
from pydantic import BaseModel
import json

class Review(BaseModel):
    product_name: str
    rating: float
    sentiment: str

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "review",
            "strict": True,
            "schema": Review.model_json_schema()
        }
    }
)
review = Review.model_validate(json.loads(response.choices[0].message.content))
```

### JSON Object Mode (Simple)

Valid JSON without schema enforcement (works with all models):

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "Respond with JSON: {\"sentiment\": \"...\", \"score\": 0.0}"},
        {"role": "user", "content": "Analyze: Great product!"}
    ],
    response_format={"type": "json_object"}
)
```

## Documents (RAG)

Provide context documents:

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Summarize the documents"}],
    documents=[
        {"content": "Document 1 text..."},
        {"content": "Document 2 text..."}
    ],
    citation_options="enabled"
)
```
