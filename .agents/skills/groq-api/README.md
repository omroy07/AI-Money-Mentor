# Groq API Skill

> **Install:** `npx skills add diskd-ai/groq-api` | [skills.sh](https://skills.sh)

Integration skill for building AI-powered applications with Groq's ultra-fast LLM inference platform (300-1000+ tokens/sec).

---

## Scope and Purpose

This skill provides guidance and patterns for working with Groq's API, covering:

- Chat completions with production-optimized open-source models
- Vision/image understanding with Llama 4 multimodal models
- Audio transcription (Whisper) and text-to-speech
- Tool use/function calling
- Structured outputs and JSON mode
- Reasoning models with configurable effort levels
- Batch processing for high-volume workloads

---

## When to Use This Skill

**Triggers:**

- Mentions of Groq, GroqCloud, or fast LLM inference
- Working with the Python SDK (`groq`) or TypeScript SDK (`groq-sdk`)
- Tasks requiring high throughput or low latency inference

**Use cases:**

- Implementing chat completions with Llama, Qwen, or other supported models
- Adding vision capabilities with Llama 4 multimodal models
- Transcribing audio with Whisper
- Building agents with tool use/function calling
- Creating reasoning workflows with configurable effort levels

---

## Quick Reference

### Installation

```bash
# Python
pip install groq

# TypeScript/JavaScript
npm install groq-sdk
```

### Environment

```bash
export GROQ_API_KEY=<your-api-key>
```

### Basic Usage

**Python:**

```python
from groq import Groq

client = Groq()  # Uses GROQ_API_KEY env var

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

**TypeScript:**

```typescript
import Groq from 'groq-sdk';

const client = new Groq();

const response = await client.chat.completions.create({
  model: 'llama-3.3-70b-versatile',
  messages: [{ role: 'user', content: 'Hello' }],
});
console.log(response.choices[0].message.content);
```

---

## Model Selection Guide

| Use Case        | Model                            | Notes                         |
| --------------- | -------------------------------- | ----------------------------- |
| Fast + cheap    | `llama-3.1-8b-instant`           | Best for simple tasks         |
| Balanced        | `llama-3.3-70b-versatile`        | Quality/cost balance          |
| Highest quality | `openai/gpt-oss-120b`            | Built-in tools + reasoning    |
| Agentic         | `groq/compound`                  | Web search + code exec        |
| Reasoning       | `openai/gpt-oss-20b`             | Fast reasoning (low/med/high) |
| Vision/OCR      | `llama-4-scout-17b-16e-instruct` | Image understanding           |
| Audio STT       | `whisper-large-v3-turbo`         | Transcription                 |
| TTS             | `playai-tts`                     | Text-to-speech                |

---

## Skill Structure

```
groq-api/
  SKILL.md          # Full API reference and patterns
  README.md         # This file (overview)
  references/       # Supporting documentation
    models.md       # Complete model list and pricing
    tool-use.md     # Function calling patterns
    vision.md       # Image processing
    audio.md        # Transcription and TTS
    reasoning.md    # Reasoning model patterns
    structured-outputs.md # JSON Schema structured outputs
    prompt-caching.md # Automatic prompt caching
    moderation.md   # Content moderation and safety
    sdk.md          # Client libraries (Python, JS, community)
    api-reference.md # Full API reference
```

---

## Key Patterns

### Streaming Responses

```python
stream = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### JSON Mode

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "List 3 colors as JSON array"}],
    response_format={"type": "json_object"}
)
```

### Vision (Image from URL)

```python
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
)
```

### Audio Transcription

```python
with open("audio.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=f,
        response_format="verbose_json"
    )
print(transcription.text)
```

---

## Error Handling

```python
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError

client = Groq()

try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello"}]
    )
except RateLimitError:
    # Wait and retry with exponential backoff
    pass
except APIConnectionError:
    # Network issue
    pass
except APIStatusError as e:
    # API error (check e.status_code)
    pass
```

---

## Resources

- **Full skill reference**: [SKILL.md](SKILL.md)
- **Models and pricing**: [references/models.md](references/models.md)
- **Tool use guide**: [references/tool-use.md](references/tool-use.md)
- **Vision guide**: [references/vision.md](references/vision.md)
- **Audio guide**: [references/audio.md](references/audio.md)
- **Reasoning guide**: [references/reasoning.md](references/reasoning.md)
- **Structured outputs**: [references/structured-outputs.md](references/structured-outputs.md)
- **Prompt caching**: [references/prompt-caching.md](references/prompt-caching.md)
- **Moderation guide**: [references/moderation.md](references/moderation.md)
- **SDK reference**: [references/sdk.md](references/sdk.md)
- **Full API reference**: [references/api-reference.md](references/api-reference.md)
- **Official docs**: https://console.groq.com/docs
- **Python SDK**: https://github.com/groq/groq-python
- **TypeScript SDK**: https://github.com/groq/groq-typescript

---

## License

MIT
