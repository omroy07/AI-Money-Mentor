# Groq Models Reference

## Production Models

Use these for production environments. They meet Groq's standards for speed, quality, and reliability.

| Model ID                       | Speed    | Input/Output Price  | Context | Max Output |
| ------------------------------ | -------- | ------------------- | ------- | ---------- |
| `llama-3.1-8b-instant`         | 560 t/s  | $0.05/$0.08 per 1M  | 131K    | 131K       |
| `llama-3.3-70b-versatile`      | 280 t/s  | $0.59/$0.79 per 1M  | 131K    | 32K        |
| `meta-llama/llama-guard-4-12b` | 1200 t/s | $0.20/$0.20 per 1M  | 131K    | 1K         |
| `openai/gpt-oss-120b`          | 500 t/s  | $0.15/$0.60 per 1M  | 131K    | 65K        |
| `openai/gpt-oss-20b`           | 1000 t/s | $0.075/$0.30 per 1M | 131K    | 65K        |
| `whisper-large-v3`             | -        | $0.111/hour         | -       | -          |
| `whisper-large-v3-turbo`       | -        | $0.04/hour          | -       | -          |

## Production Systems (Agentic)

Systems combine models with built-in tools (web search, code execution).

| Model ID             | Speed   | Context | Max Output |
| -------------------- | ------- | ------- | ---------- |
| `groq/compound`      | 450 t/s | 131K    | 8K         |
| `groq/compound-mini` | 450 t/s | 131K    | 8K         |

## Preview Models

Evaluation only. May be discontinued without notice.

| Model ID                                        | Speed    | Input/Output Price  | Context | Max Output |
| ----------------------------------------------- | -------- | ------------------- | ------- | ---------- |
| `meta-llama/llama-4-maverick-17b-128e-instruct` | 600 t/s  | $0.20/$0.60 per 1M  | 131K    | 8K         |
| `meta-llama/llama-4-scout-17b-16e-instruct`     | 750 t/s  | $0.11/$0.34 per 1M  | 131K    | 8K         |
| `moonshotai/kimi-k2-instruct-0905`              | 200 t/s  | $1.00/$3.00 per 1M  | 262K    | 16K        |
| `qwen/qwen3-32b`                                | 400 t/s  | $0.29/$0.59 per 1M  | 131K    | 40K        |
| `openai/gpt-oss-safeguard-20b`                  | 1000 t/s | $0.075/$0.30 per 1M | 131K    | 65K        |

## Model Selection Guide

**Fast + Cheap (simple tasks):**

- `llama-3.1-8b-instant` - Best price/performance for simple tasks
- `openai/gpt-oss-20b` - Fastest for medium complexity

**High Quality (complex tasks):**

- `llama-3.3-70b-versatile` - Best quality/cost balance
- `openai/gpt-oss-120b` - Highest capability with built-in tools

**Agentic (tools needed):**

- `groq/compound` - Full-featured with web search and code execution
- `openai/gpt-oss-120b` - Best for tool use with local calling

**Audio transcription:**

- `whisper-large-v3-turbo` - Faster, cheaper
- `whisper-large-v3` - Higher accuracy

**Vision/OCR:**

- `meta-llama/llama-4-scout-17b-16e-instruct` - Faster, image understanding
- `meta-llama/llama-4-maverick-17b-128e-instruct` - Higher quality vision

**Reasoning:**

- `openai/gpt-oss-20b` - Fast reasoning with low/medium/high effort
- `openai/gpt-oss-120b` - Best reasoning quality
- `qwen/qwen3-32b` - Reasoning with format control (raw/parsed/hidden)

**Safety/Moderation:**

- `meta-llama/llama-guard-4-12b` - Content safety classification
- `openai/gpt-oss-safeguard-20b` - Safety-focused model

## Tool Use Support

| Model                              | Local Tools | Parallel | JSON Mode | Built-In |
| ---------------------------------- | ----------- | -------- | --------- | -------- |
| `moonshotai/kimi-k2-instruct-0905` | Yes         | Yes      | Yes       | No       |
| `openai/gpt-oss-20b`               | Yes         | No       | Yes       | Yes      |
| `openai/gpt-oss-120b`              | Yes         | No       | Yes       | Yes      |
| `llama-3.3-70b-versatile`          | Yes         | Yes      | Yes       | No       |
| `llama-3.1-8b-instant`             | Yes         | Yes      | Yes       | No       |
| `groq/compound`                    | No          | N/A      | Yes       | Yes      |

## Vision Support

| Model                                           | Vision | Tool Use | JSON Mode | Context |
| ----------------------------------------------- | ------ | -------- | --------- | ------- |
| `meta-llama/llama-4-scout-17b-16e-instruct`     | Yes    | Yes      | Yes       | 128K    |
| `meta-llama/llama-4-maverick-17b-128e-instruct` | Yes    | Yes      | Yes       | 128K    |

**Limits:**

- Image URL request: 20MB max
- Image resolution: 33 megapixels max
- Base64 request: 4MB max
- Images per request: 5 max

## Reasoning Support

| Model                          | reasoning_effort        | reasoning_format          | include_reasoning |
| ------------------------------ | ----------------------- | ------------------------- | ----------------- |
| `openai/gpt-oss-20b`           | `low`, `medium`, `high` | -                         | `true`/`false`    |
| `openai/gpt-oss-120b`          | `low`, `medium`, `high` | -                         | `true`/`false`    |
| `openai/gpt-oss-safeguard-20b` | `low`, `medium`, `high` | -                         | `true`/`false`    |
| `qwen/qwen3-32b`               | `none`, `default`       | `raw`, `parsed`, `hidden` | -                 |

**Notes:**

- GPT-OSS: Use `reasoning_effort` + `include_reasoning`
- Qwen3: Use `reasoning_effort` + `reasoning_format`
- `raw` format not supported with JSON mode or tool use

## Rate Limits

Limits apply at organization level. You hit whichever threshold comes first.

### Rate Limit Types

- **RPM**: Requests per minute
- **RPD**: Requests per day
- **TPM**: Tokens per minute
- **TPD**: Tokens per day
- **ASH/ASD**: Audio seconds per hour/day

Cached tokens do not count toward limits.

### Free Plan Limits

| Model                     | RPM | RPD   | TPM | TPD  |
| ------------------------- | --- | ----- | --- | ---- |
| `llama-3.1-8b-instant`    | 30  | 14.4K | 6K  | 500K |
| `llama-3.3-70b-versatile` | 30  | 1K    | 12K | 100K |
| `openai/gpt-oss-120b`     | 30  | 1K    | 8K  | 200K |
| `openai/gpt-oss-20b`      | 30  | 1K    | 8K  | 200K |
| `groq/compound`           | 30  | 250   | 70K | -    |

### Developer Plan Limits

Higher limits available. Check console.groq.com/settings/limits for current limits.

### Rate Limit Headers

```
retry-after: 2                          # Seconds (only on 429)
x-ratelimit-limit-requests: 14400       # RPD limit
x-ratelimit-limit-tokens: 18000         # TPM limit
x-ratelimit-remaining-requests: 14370   # RPD remaining
x-ratelimit-remaining-tokens: 17997     # TPM remaining
x-ratelimit-reset-requests: 2m59.56s    # RPD reset time
x-ratelimit-reset-tokens: 7.66s         # TPM reset time
```

### Handling 429 Errors

```python
import time
from groq import Groq, RateLimitError

client = Groq()

def call_with_retry(messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # Exponential backoff
            time.sleep(wait)
```
