# Groq Vision Reference

Process images with Llama 4 multimodal models for image understanding, OCR, and visual analysis.

## Supported Models

| Model ID                                        | Context | Notes                   |
| ----------------------------------------------- | ------- | ----------------------- |
| `meta-llama/llama-4-scout-17b-16e-instruct`     | 128K    | Faster, preview         |
| `meta-llama/llama-4-maverick-17b-128e-instruct` | 128K    | Higher quality, preview |

Both models support: multilingual, multi-turn conversations, tool use, and JSON mode with images.

## Limits

| Limit                       | Value                               |
| --------------------------- | ----------------------------------- |
| Image URL request size      | 20MB max                            |
| Image resolution            | 33 megapixels (33177600 pixels) max |
| Base64 encoded request size | 4MB max                             |
| Images per request          | 5 max                               |

## Image from URL

```python
from groq import Groq

client = Groq()

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }],
    max_completion_tokens=1024
)
print(response.choices[0].message.content)
```

## Local Image (Base64)

```python
from groq import Groq
import base64

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

client = Groq()
base64_image = encode_image("photo.jpg")

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }]
)
print(response.choices[0].message.content)
```

## Multiple Images

```python
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Compare these two images"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image1.jpg"}},
            {"type": "image_url", "image_url": {"url": "https://example.com/image2.jpg"}}
        ]
    }]
)
```

## JSON Mode with Images

Extract structured data from images:

```python
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract all text and objects as JSON"},
            {"type": "image_url", "image_url": {"url": "https://example.com/document.jpg"}}
        ]
    }],
    response_format={"type": "json_object"}
)
```

## Tool Use with Images

Model can infer context from images for tool calls:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City and state"}
            },
            "required": ["location"]
        }
    }
}]

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's the weather like in this city?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/city_skyline.jpg"}}
        ]
    }],
    tools=tools,
    tool_choice="auto"
)
# Model infers location from image and calls get_current_weather
```

## Multi-turn Conversations

Continue discussing images across turns:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What is in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
        ]
    },
    {
        "role": "assistant",
        "content": "This image shows the San Francisco skyline..."
    },
    {
        "role": "user",
        "content": "Tell me more about the area."
    }
]

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=messages
)
```

## OCR / Document Processing

Extract text from documents, receipts, screenshots:

```python
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract all text from this document"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]
    }]
)
```

For structured extraction:

```python
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract receipt data as JSON: {store, date, items: [{name, price}], total}"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    response_format={"type": "json_object"}
)
```

## Use Cases

- **Accessibility**: Generate image descriptions for text-to-speech
- **E-commerce**: Auto-generate product descriptions from photos
- **Document processing**: Extract data from receipts, invoices, forms
- **Content moderation**: Analyze images for policy compliance
- **Multilingual analysis**: Describe images in multiple languages

## TypeScript

```typescript
import Groq from 'groq-sdk';
import * as fs from 'fs';

const client = new Groq();

// From URL
const response = await client.chat.completions.create({
  model: 'meta-llama/llama-4-scout-17b-16e-instruct',
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: "What's in this image?" },
        {
          type: 'image_url',
          image_url: { url: 'https://example.com/image.jpg' },
        },
      ],
    },
  ],
});

// From local file
const base64Image = fs.readFileSync('photo.jpg').toString('base64');
const localResponse = await client.chat.completions.create({
  model: 'meta-llama/llama-4-scout-17b-16e-instruct',
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'Describe this image' },
        {
          type: 'image_url',
          image_url: { url: `data:image/jpeg;base64,${base64Image}` },
        },
      ],
    },
  ],
});
```
