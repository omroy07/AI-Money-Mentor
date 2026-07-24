# Structured Outputs

Guarantee model responses conform to your JSON schema for reliable, type-safe data structures.

## Contents

- [Overview](#overview)
- [Modes](#modes)
- [Supported Models](#supported-models)
- [Basic Usage](#basic-usage)
- [Schema Requirements](#schema-requirements)
- [Examples](#examples)
- [Validation Libraries](#validation-libraries)
- [JSON Object Mode](#json-object-mode)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)

---

## Overview

Structured Outputs ensures model responses conform to your provided JSON Schema. Two modes available:

| Feature          | Strict Mode                                        | Best-effort Mode         |
| ---------------- | -------------------------------------------------- | ------------------------ |
| Schema adherence | 100% guaranteed                                    | Generally compliant      |
| Error handling   | Never produces invalid JSON                        | May occasionally error   |
| Requirements     | All fields required, `additionalProperties: false` | More flexible            |
| Model support    | Limited (GPT-OSS 20B, 120B)                        | All supported models     |
| Use case         | Production apps                                    | Development, prototyping |

---

## Modes

### Strict Mode (`strict: true`)

Uses constrained decoding to guarantee output matches schema exactly.

```python
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "Extract: John is 30"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                },
                "required": ["name", "age"],
                "additionalProperties": False
            }
        }
    }
)
```

**Requirements:**

- All fields must be in `required` array
- All objects must set `additionalProperties: false`
- Use union types with `null` for optional fields

### Best-effort Mode (`strict: false`)

Default mode. Attempts schema adherence without hard constraints.

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Extract: John is 30"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "strict": False,  # or omit (defaults to false)
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                },
                "required": ["name"]  # Optional fields allowed
            }
        }
    }
)
```

---

## Supported Models

### Strict Mode (`strict: true`)

| Model                 | Notes                    |
| --------------------- | ------------------------ |
| `openai/gpt-oss-20b`  | Full strict mode support |
| `openai/gpt-oss-120b` | Full strict mode support |

### Best-effort Mode (`strict: false`)

| Model                              | Notes                    |
| ---------------------------------- | ------------------------ |
| `llama-3.3-70b-versatile`          | Good schema adherence    |
| `llama-3.1-8b-instant`             | Basic support            |
| `moonshotai/kimi-k2-instruct-0905` | Good for complex schemas |
| `qwen/qwen3-32b`                   | Good schema adherence    |

---

## Basic Usage

### Python with Pydantic

```python
from groq import Groq
from pydantic import BaseModel
import json

client = Groq()

class Person(BaseModel):
    name: str
    age: int
    email: str | None = None

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "user", "content": "Extract: John Smith is 30 years old, email john@example.com"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person_extraction",
            "strict": True,
            "schema": Person.model_json_schema()
        }
    }
)

person = Person.model_validate(json.loads(response.choices[0].message.content))
print(person)
```

### TypeScript with Zod

```typescript
import Groq from 'groq-sdk';
import { z } from 'zod';

const client = new Groq();

const personSchema = z.object({
  name: z.string(),
  age: z.number(),
  email: z.string().nullable(),
});

const response = await client.chat.completions.create({
  model: 'openai/gpt-oss-20b',
  messages: [
    {
      role: 'user',
      content: 'Extract: John Smith is 30 years old, email john@example.com',
    },
  ],
  response_format: {
    type: 'json_schema',
    json_schema: {
      name: 'person_extraction',
      strict: true,
      schema: z.toJSONSchema(personSchema),
    },
  },
});

const person = personSchema.parse(
  JSON.parse(response.choices[0].message.content || '{}'),
);
console.log(person);
```

---

## Schema Requirements

### Supported Data Types

- **Primitives:** string, number, boolean, integer
- **Complex:** object, array, enum
- **Composition:** anyOf (union types)

### Strict Mode Constraints

**All fields required:**

```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "age": { "type": "number" }
  },
  "required": ["name", "age"]
}
```

**Closed objects:**

```json
{
  "type": "object",
  "properties": { ... },
  "additionalProperties": false
}
```

**Optional fields with union types:**

```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "nickname": { "type": ["string", "null"] }
  },
  "required": ["name", "nickname"],
  "additionalProperties": false
}
```

### Recursive Schemas

Use `$defs` for recursive structures:

```json
{
  "$defs": {
    "file_node": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "type": { "type": "string", "enum": ["file", "directory"] },
        "children": {
          "anyOf": [
            { "type": "array", "items": { "$ref": "#/$defs/file_node" } },
            { "type": "null" }
          ]
        }
      },
      "required": ["name", "type", "children"],
      "additionalProperties": false
    }
  },
  "type": "object",
  "properties": {
    "root": { "$ref": "#/$defs/file_node" }
  },
  "required": ["root"],
  "additionalProperties": false
}
```

---

## Examples

### SQL Query Generation

```python
from groq import Groq
from pydantic import BaseModel
import json

client = Groq()

class ValidationStatus(BaseModel):
    is_valid: bool
    syntax_errors: list[str]

class SQLQuery(BaseModel):
    query: str
    query_type: str
    tables_used: list[str]
    estimated_complexity: str
    validation_status: ValidationStatus

response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": "Generate structured SQL queries from natural language."},
        {"role": "user", "content": "Find customers with orders over $500 in last 30 days"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sql_generation",
            "schema": SQLQuery.model_json_schema()
        }
    }
)

result = SQLQuery.model_validate(json.loads(response.choices[0].message.content))
print(result.query)
```

### Email Classification

```python
class EmailClassification(BaseModel):
    category: str  # urgent, support, sales, spam, etc.
    priority: str  # low, medium, high, critical
    confidence_score: float
    sentiment: str  # positive, negative, neutral
    requires_immediate_attention: bool
    suggested_actions: list[str]

response = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[
        {"role": "system", "content": "Classify emails with confidence scores and suggested actions."},
        {"role": "user", "content": email_content}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "email_classification",
            "schema": EmailClassification.model_json_schema()
        }
    }
)
```

### Data Extraction

```python
class Product(BaseModel):
    name: str
    price: float
    currency: str
    in_stock: bool
    features: list[str]

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "user", "content": "Extract product info: iPhone 15 Pro - $999 USD, available now. Features: A17 chip, 48MP camera, titanium design."}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "product_extraction",
            "strict": True,
            "schema": Product.model_json_schema()
        }
    }
)
```

---

## Validation Libraries

### Pydantic (Python)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    title: str
    priority: Priority
    tags: List[str]
    due_date: Optional[str] = Field(None, description="ISO datetime")

# Generate schema
schema = Task.model_json_schema()

# Validate response
task = Task.model_validate(json.loads(response_content))
```

### Zod (TypeScript)

```typescript
import { z } from 'zod';

const taskSchema = z.object({
  title: z.string(),
  priority: z.enum(['low', 'medium', 'high']),
  tags: z.array(z.string()),
  dueDate: z.string().datetime().nullable(),
});

type Task = z.infer<typeof taskSchema>;

// Generate schema
const schema = z.toJSONSchema(taskSchema);

// Validate response
const task = taskSchema.parse(JSON.parse(responseContent));
```

---

## JSON Object Mode

Basic JSON output without schema enforcement. Use when you need valid JSON but don't require strict schema compliance.

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "Respond with JSON: {sentiment, confidence, summary}"},
        {"role": "user", "content": "Analyze: I love this product!"}
    ],
    response_format={"type": "json_object"}
)
```

**Requirements:**

- Include explicit JSON instructions in your prompt
- Outputs are syntactically valid but may not match intended schema

| Feature          | Strict Mode | Best-effort Mode | JSON Object Mode |
| ---------------- | ----------- | ---------------- | ---------------- |
| Valid JSON       | Always      | Usually          | Usually          |
| Schema adherence | Guaranteed  | Best-effort      | None             |
| Requires schema  | Yes         | Yes              | No               |

---

## Migration Guide

### Upgrading to Strict Mode

**1. Verify model support** - Use `openai/gpt-oss-20b` or `openai/gpt-oss-120b`

**2. Update schema:**

```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "email": { "type": ["string", "null"] }
  },
  "required": ["name", "email"],
  "additionalProperties": false
}
```

**3. Add strict flag:**

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "my_schema",
        "strict": True,
        "schema": { ... }
    }
}
```

---

## Best Practices

**Schema design:**

- Keep schemas focused and minimal
- Use enums for constrained string values
- Add descriptions to complex fields
- Test schemas with representative inputs

**Error handling:**

- With strict mode, trust the output structure
- With best-effort mode, validate and retry on schema errors
- Consider fallback to JSON object mode for unsupported models

**Performance:**

- Simpler schemas process faster
- Strict mode may have slightly higher latency
- Cache validated Pydantic/Zod schemas

**Common pitfalls:**

- Forcing schema on unrelated inputs causes hallucinations
- Specify fallback responses for incompatible inputs
- Structured outputs guarantee format, not semantic accuracy
