# Groq Client Libraries

Official and community client libraries for accessing the Groq API.

## Contents

- [Python SDK](#python-sdk)
- [JavaScript/TypeScript SDK](#javascripttypescript-sdk)
- [Community Libraries](#community-libraries)

---

## Python SDK

The [Groq Python library](https://pypi.org/project/groq/) provides convenient access to the Groq REST API from Python 3.7+. Includes type definitions for all request params and response fields, with both synchronous and asynchronous clients.

### Installation

```bash
pip install groq
```

### Basic Usage

```python
import os
from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),  # default, can be omitted
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain the importance of fast language models"}
    ]
)

print(response.choices[0].message.content)
```

### Async Client

```python
import asyncio
from groq import AsyncGroq

async def main():
    client = AsyncGroq()
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response.choices[0].message.content

print(asyncio.run(main()))
```

### Streaming

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

### Environment Variables

Recommended: Use [python-dotenv](https://github.com/theskumar/python-dotenv) to load API key from `.env` file:

```bash
# .env
GROQ_API_KEY=your-api-key
```

```python
from dotenv import load_dotenv
load_dotenv()

from groq import Groq
client = Groq()  # Automatically uses GROQ_API_KEY
```

### Error Handling

```python
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError

client = Groq()

try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Hello"}]
    )
except RateLimitError:
    # Implement exponential backoff retry
    pass
except APIConnectionError:
    # Network connectivity issue
    pass
except APIStatusError as e:
    # API returned an error status
    print(f"Status code: {e.status_code}")
```

### Links

- **PyPI**: https://pypi.org/project/groq/
- **GitHub**: https://github.com/groq/groq-python

---

## JavaScript/TypeScript SDK

The [Groq JavaScript library](https://www.npmjs.com/package/groq-sdk) provides convenient access to the Groq REST API from server-side TypeScript or JavaScript. Includes type definitions for all request params and response fields.

### Installation

```bash
npm install groq-sdk
# or
yarn add groq-sdk
# or
pnpm add groq-sdk
```

### Basic Usage

```typescript
import Groq from 'groq-sdk';

const client = new Groq({
  apiKey: process.env.GROQ_API_KEY, // default, can be omitted
});

async function main() {
  const response = await client.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      {
        role: 'user',
        content: 'Explain the importance of fast language models',
      },
    ],
  });

  console.log(response.choices[0]?.message?.content);
}

main();
```

### Streaming

```typescript
const stream = await client.chat.completions.create({
  model: 'llama-3.3-70b-versatile',
  messages: [{ role: 'user', content: 'Tell me a story' }],
  stream: true,
});

for await (const chunk of stream) {
  const content = chunk.choices[0]?.delta?.content;
  if (content) {
    process.stdout.write(content);
  }
}
```

### Error Handling

```typescript
import Groq from 'groq-sdk';

const client = new Groq();

try {
  const response = await client.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [{ role: 'user', content: 'Hello' }],
  });
} catch (error) {
  if (error instanceof Groq.RateLimitError) {
    // Implement exponential backoff retry
  } else if (error instanceof Groq.APIConnectionError) {
    // Network connectivity issue
  } else if (error instanceof Groq.APIError) {
    console.log(`Status: ${error.status}`);
  }
}
```

### Links

- **npm**: https://www.npmjs.com/package/groq-sdk
- **GitHub**: https://github.com/groq/groq-typescript

---

## Community Libraries

Community-built libraries for other languages. **Note:** Groq does not verify the security of these projects. Use at your own risk.

### C#

- [jgravelle/GroqApiLibrary](https://github.com/jgravelle/GroqApiLibrary) by jgravelle

### Dart/Flutter

- [TAGonSoft/groq-dart](https://github.com/TAGonSoft/groq-dart) by TAGonSoft

### PHP

- [lucianotonet/groq-php](https://github.com/lucianotonet/groq-php) by lucianotonet

### Ruby

- [drnic/groq-ruby](https://github.com/drnic/groq-ruby) by drnic

---

## Response Format

Both SDKs return responses in the same format:

```json
{
  "id": "34a9110d-c39d-423b-9ab9-9c748747b204",
  "object": "chat.completion",
  "created": 1708045122,
  "model": "llama-3.3-70b-versatile",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response content here..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 377,
    "total_tokens": 401,
    "prompt_time": 0.009,
    "completion_time": 0.774,
    "total_time": 0.783
  },
  "x_groq": {
    "id": "req_01htzpsmfmew5b4rbmbjy2kv74"
  }
}
```

**Key fields:**

- `choices[0].message.content`: The model's response text
- `choices[0].finish_reason`: Why generation stopped (`stop`, `length`, `tool_calls`)
- `usage`: Token counts and timing information
- `x_groq.id`: Request ID for debugging
