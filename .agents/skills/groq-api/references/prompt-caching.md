# Prompt Caching

Automatically reuse computation from recent requests to reduce latency and costs by 50% for cached portions.

## Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Supported Models](#supported-models)
- [Pricing](#pricing)
- [Tracking Cache Usage](#tracking-cache-usage)
- [Optimization Strategies](#optimization-strategies)
- [Examples](#examples)
- [Requirements and Limitations](#requirements-and-limitations)
- [FAQ](#faq)

---

## Overview

Prompt caching automatically reuses computation from recent requests when they share a common prefix. Benefits:

- **50% cost reduction** on cached tokens
- **Lower latency** for repeated prompts
- **No code changes required** - works automatically
- **No additional fees** - included free
- **Privacy preserved** - volatile-only storage, auto-expires

---

## How It Works

1. **Prefix Matching**: System identifies matching prefixes from recent requests (system prompts, tool definitions, few-shot examples)
2. **Cache Hit**: Matching prefix found - cached computation reused, 50% token cost reduction
3. **Cache Miss**: No match - prompt processed normally, prefix cached for future matches
4. **Auto Expiration**: Cached data expires after 2 hours without use

**Key points:**

- Cached tokens don't count toward rate limits
- Cache hits not guaranteed, but Groq maximizes them
- Discount only applies on successful cache hits

---

## Supported Models

| Model ID                           | Model                 |
| ---------------------------------- | --------------------- |
| `moonshotai/kimi-k2-instruct-0905` | Kimi K2               |
| `openai/gpt-oss-20b`               | GPT-OSS 20B           |
| `openai/gpt-oss-120b`              | GPT-OSS 120B          |
| `openai/gpt-oss-safeguard-20b`     | GPT-OSS-Safeguard 20B |

More models coming soon.

---

## Pricing

| Token Type              | Price         |
| ----------------------- | ------------- |
| Cached input tokens     | 50% discount  |
| Non-cached input tokens | Standard rate |
| Output tokens           | Standard rate |

---

## Tracking Cache Usage

Monitor cache performance via the `usage` field in API responses:

```json
{
  "usage": {
    "prompt_tokens": 1500,
    "completion_tokens": 100,
    "total_tokens": 1600,
    "prompt_tokens_details": {
      "cached_tokens": 1200
    }
  }
}
```

**Metrics:**

- `prompt_tokens`: Total input tokens
- `cached_tokens`: Tokens served from cache (50% discount applied)
- **Cache hit rate**: `cached_tokens / prompt_tokens`

**Python example:**

```python
response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[{"role": "user", "content": "..."}]
)

usage = response.usage
cached = usage.prompt_tokens_details.cached_tokens if usage.prompt_tokens_details else 0
hit_rate = cached / usage.prompt_tokens if usage.prompt_tokens > 0 else 0

print(f"Cached tokens: {cached}")
print(f"Cache hit rate: {hit_rate:.1%}")
```

---

## Optimization Strategies

### Structure Prompts for Caching

Place static content at the beginning, dynamic content at the end:

```
[SYSTEM PROMPT - Static]
[TOOL DEFINITIONS - Static]
[FEW-SHOT EXAMPLES - Static]
[COMMON INSTRUCTIONS - Static]
[USER QUERY - Dynamic]
[SESSION DATA - Dynamic]
```

### Static Content (Beginning)

- System prompts
- Tool definitions
- Few-shot examples
- Reference documents
- API schemas
- Common instructions

### Dynamic Content (End)

- User-specific queries
- Variable data
- Timestamps
- Session-specific information
- Unique identifiers

---

## Examples

### Multi-Turn Conversations

System message and conversation history cached between turns:

```python
from groq import Groq

client = Groq()

system_prompt = "You are a helpful AI assistant that provides detailed explanations."

# First request - creates cache
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is quantum computing?"}
]

first_response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=messages
)
print("First usage:", first_response.usage)

# Second request - system message cached
messages.append(first_response.choices[0].message)
messages.append({"role": "user", "content": "Can you explain superposition?"})

second_response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=messages
)
print("Second usage:", second_response.usage)
# cached_tokens will include system message and prior conversation
```

### Large Document Analysis

Same document cached across multiple queries:

```python
system_prompt = """You are a legal expert. Analyze this document:

LEGAL DOCUMENT:
<entire contents of large legal document>
"""

# First query
response1 = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "What are the termination provisions?"}
    ]
)
# cached_tokens: 0 (first request)

# Second query - document cached
response2 = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "What are the IP rights implications?"}
    ]
)
# cached_tokens: ~size of system_prompt

# Third query - document still cached
response3 = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Are there concerning liability clauses?"}
    ]
)
# cached_tokens: ~size of system_prompt
```

### Tool Definitions

Tool schemas cached across requests:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    }
]

system_message = "You are an assistant with access to tools."

# First request - caches system message + tools
response1 = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    tools=tools
)

# Second request - tools cached
response2 = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": "Search for AI news"}
    ],
    tools=tools
)
# cached_tokens includes all tool definitions
```

---

## Requirements and Limitations

### Requirements

- **Exact prefix matching**: Cache hits require exact matches at the beginning of prompt
- **Minimum prompt length**: 128-1024 tokens depending on model
- **Supported models only**: See supported models list

### Limitations

- Cache expires after 2 hours without use
- No manual cache management available
- Cache hits not guaranteed
- Batch requests: caching works but discount doesn't stack with batch discount (both are 50%)

---

## FAQ

### How do I know if caching is working?

Check `usage.prompt_tokens_details.cached_tokens` in API responses. Non-zero values indicate cache hits.

### Are there additional costs?

No. Prompt caching is free and reduces costs by 50% for cached tokens.

### Does caching affect rate limits?

Cached tokens don't count toward rate limits.

### Can I manually clear caches?

No. Cache expiration and cleanup is automatic (2 hour TTL).

### Does caching work with batch requests?

Yes, but the 50% cache discount doesn't stack with the 50% batch discount.
