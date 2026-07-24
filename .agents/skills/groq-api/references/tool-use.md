# Groq Tool Use Reference

Tool use transforms LLMs from conversational interfaces into autonomous agents. Groq supports three approaches.

## Three Approaches Comparison

| Pattern        | You Provide             | Execution    | Orchestration   | API Calls     |
| -------------- | ----------------------- | ------------ | --------------- | ------------- |
| **Built-In**   | List of enabled tools   | Groq servers | Groq manages    | Single call   |
| **Remote MCP** | MCP server URL + auth   | MCP server   | Groq manages    | Single call   |
| **Local**      | Tool definitions + code | Your code    | You manage loop | Multiple (2+) |

## 1. Built-In Tools (Simplest)

Pre-configured tools (web search, code execution) on Groq infrastructure. Single API call, zero setup.

**Supported models:** `groq/compound`, `groq/compound-mini`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`

```python
response = client.chat.completions.create(
    model="groq/compound",
    messages=[{"role": "user", "content": "Search for latest AI news"}]
)
# Model automatically uses web search and returns final answer
```

## 2. Remote MCP Tools

Connect to third-party MCP servers. Groq handles discovery and execution server-side.

**Use Responses API for best MCP experience:**

```python
import openai

client = openai.OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

response = client.responses.create(
    model="openai/gpt-oss-120b",
    input="What models are trending on Huggingface?",
    tools=[{
        "type": "mcp",
        "server_label": "Huggingface",
        "server_url": "https://huggingface.co/mcp",
        "server_description": "Search AI models on Hugging Face",
        "require_approval": "never"
    }]
)
```

### MCP Tool Structure

```json
{
  "type": "mcp",
  "server_label": "stripe",
  "server_url": "https://mcp.stripe.com",
  "headers": { "Authorization": "Bearer <TOKEN>" },
  "server_description": "Create invoices and manage payments",
  "require_approval": "never",
  "allowed_tools": ["create_invoice", "list_customers"]
}
```

### Multiple MCP Servers

```python
tools=[
    {"type": "mcp", "server_label": "search", "server_url": "https://mcp.parallel.ai/..."},
    {"type": "mcp", "server_label": "stripe", "server_url": "https://mcp.stripe.com", ...},
    {"type": "mcp", "server_label": "github", "server_url": "https://mcp.github.com/v1", ...}
]
```

### Popular MCP Servers

- **Hugging Face**: `https://huggingface.co/mcp` - AI models/datasets
- **Stripe**: `https://mcp.stripe.com` - Payments
- **Firecrawl**: `https://mcp.firecrawl.dev/<KEY>/v2/mcp` - Web scraping
- **Parallel**: `https://mcp.parallel.ai/v1beta/search_mcp/` - Web search

## 3. Local Tool Calling (Most Control)

You define tools, execute functions locally, manage the orchestration loop.

### Tool Definition

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location. Use when user asks about weather.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"]
        }
    }
}]
```

### Tool Implementation

```python
import json

def get_weather(location: str, unit: str = "celsius") -> str:
    # Your implementation
    return json.dumps({"temp": 22, "unit": unit, "condition": "sunny"})

available_functions = {
    "get_weather": get_weather,
}

def execute_tool_call(tool_call):
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    return available_functions[function_name](**function_args)
```

### Orchestration Loop

```python
from groq import Groq
import json

client = Groq()

def run_with_tools(user_query, tools, available_functions, max_iterations=10):
    messages = [{"role": "user", "content": user_query}]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        # No tool calls = final answer
        if not msg.tool_calls:
            return msg.content

        messages.append(msg)

        # Execute each tool call
        for tc in msg.tool_calls:
            func = available_functions[tc.function.name]
            args = json.loads(tc.function.arguments)
            result = func(**args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": str(result)
            })

    return "Max iterations reached"
```

## Tool Choice Options

```python
tool_choice="auto"      # Model decides (default)
tool_choice="none"      # Disable tools
tool_choice="required"  # Must use a tool
tool_choice={"type": "function", "function": {"name": "get_weather"}}  # Force specific
```

## Parallel Tool Calls

Some models return multiple tool calls simultaneously:

```python
# Model might return multiple tool_calls for efficiency
for tc in response.choices[0].message.tool_calls:
    result = execute_tool_call(tc)
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "name": tc.function.name,
        "content": result
    })
```

**Parallel support:** `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `kimi-k2-instruct-0905`, `qwen3-32b`, `llama-4-*`

## Model Support

| Model                              | Local | Parallel | JSON Mode | Built-In |
| ---------------------------------- | ----- | -------- | --------- | -------- |
| `moonshotai/kimi-k2-instruct-0905` | Yes   | Yes      | Yes       | No       |
| `openai/gpt-oss-20b`               | Yes   | No       | Yes       | Yes      |
| `openai/gpt-oss-120b`              | Yes   | No       | Yes       | Yes      |
| `qwen/qwen3-32b`                   | Yes   | Yes      | Yes       | No       |
| `llama-3.3-70b-versatile`          | Yes   | Yes      | Yes       | No       |
| `llama-3.1-8b-instant`             | Yes   | Yes      | Yes       | No       |
| `groq/compound`                    | No    | N/A      | Yes       | Yes      |

## Streaming Tool Calls

```python
stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=messages,
    tools=tools,
    stream=True
)

collected_content = ""
collected_tool_calls = []

for chunk in stream:
    if chunk.choices[0].delta.content:
        collected_content += chunk.choices[0].delta.content
    if chunk.choices[0].delta.tool_calls:
        collected_tool_calls.extend(chunk.choices[0].delta.tool_calls)
    if chunk.choices[0].finish_reason == "tool_calls":
        # Execute tool calls
        pass
```

## Error Handling

### Retry on Tool Call Failures

```python
def call_with_retry(messages, tools, max_retries=3):
    temperature = 0.2

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=tools,
                temperature=temperature
            )
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 400:
                # Lower temperature reduces hallucinated tool calls
                temperature = min(temperature + 0.2, 1.0)
                continue
            raise
    raise Exception("Failed after retries")
```

### Return Errors to Model

```python
try:
    result = execute_function(args)
    content = str(result)
except Exception as e:
    # Let model know about error so it can adjust
    content = json.dumps({"error": str(e), "is_error": True})

messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "name": tc.function.name,
    "content": content
})
```

### Validate Arguments

```python
def validate_args(tool_call):
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return None, {"error": f"Invalid JSON: {e}"}

    if "location" not in args:
        return None, {"error": "Missing required: location"}

    return args, None
```

## Best Practices

### 1. Clear Descriptions

```json
{
  "name": "get_customer_order_history",
  "description": "Retrieves complete order history for a customer by email. Returns order IDs, dates, amounts, status. Use when user asks about past orders."
}
```

### 2. Detailed Parameters

```json
{
  "properties": {
    "search_query": {
      "type": "string",
      "description": "Search term for product names and descriptions"
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum results to return (1-50)"
    }
  }
}
```

### 3. Return Structured Data

```python
return json.dumps({
    "temperature": temp,
    "unit": "fahrenheit",
    "condition": condition,
    "timestamp": datetime.now().isoformat()
})
```

### 4. Limit Tool Count

- Optimal: 3-5 tools per request
- Maximum: 10-15 tools

### 5. Guide with System Prompts

```python
{
    "role": "system",
    "content": """Use get_order_status for order inquiries.
Use get_product_info for product questions.
Always confirm IDs before calling tools.
If a tool errors, ask user for clarification."""
}
```

## Complete Multi-Tool Example

```python
from groq import Groq
import json

client = Groq()

# Tools
def calculate(expression: str) -> str:
    return json.dumps({"result": eval(expression)})

def calculate_compound_interest(principal, rate, time, compounds=12):
    amount = principal * (1 + rate/compounds) ** (compounds * time)
    return json.dumps({"total": round(amount, 2), "interest": round(amount - principal, 2)})

available_functions = {
    "calculate": calculate,
    "calculate_compound_interest": calculate_compound_interest,
}

tools = [
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate math expression like '25 * 4 + 10'",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string"}
        }, "required": ["expression"]}
    }},
    {"type": "function", "function": {
        "name": "calculate_compound_interest",
        "description": "Calculate compound interest",
        "parameters": {"type": "object", "properties": {
            "principal": {"type": "number"},
            "rate": {"type": "number", "description": "Annual rate as decimal (0.05 = 5%)"},
            "time": {"type": "number", "description": "Years"},
            "compounds": {"type": "integer", "default": 12}
        }, "required": ["principal", "rate", "time"]}
    }}
]

# Run
query = "If I invest $10,000 at 5% for 10 years compounded monthly, what's my total?"
messages = [{"role": "user", "content": query}]

for i in range(10):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools
    )

    msg = response.choices[0].message

    if not msg.tool_calls:
        print(msg.content)
        break

    messages.append(msg)

    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = available_functions[tc.function.name](**args)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tc.function.name,
            "content": result
        })
```
