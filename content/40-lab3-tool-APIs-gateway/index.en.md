---
title: "Lab 3: Plan for tooling and API integration with Gateway"
weight: 42
---

**⏱️ Estimated time: ~30 minutes**

## Build a deliberate tooling strategy
Tools are how your agent accesses the real world. They fetch data from databases, call external APIs, search documentation, and execute business logic. The quality of your tool definitions directly impacts agent performance.

When you define a tool, clarity matters more than brevity. Consider these two descriptions for the same function:

Bad: “Gets revenue data”
Good: "Retrieves quarterly revenue data for a specified region and time period.
Returns values in millions of USD. Requires region code (EMEA, APAC, AMER)
and quarter in YYYY-QN format (e.g., 2024-Q3)."

The first description forces the agent to guess what inputs are valid and how to interpret outputs. The second helps remove ambiguity. When you multiply this across twenty tools, the difference becomes dramatic. Your tooling strategy should address four areas:

1) Error handling and resilience. Tools fail. APIs return errors. Timeouts happen. Define the expected behavior for each failure mode, if the agent should retry, fallback to cached data, or tell the user the service is unavailable. Document this alongside the tool definition.
2) Reuse through Model Context Protocol (MCP). Many service providers already provide MCP servers for tools such as Slack, Google Drive, Salesforce, and GitHub. Use them instead of building custom integrations. For internal APIs, wrap them as MCP tools through AgentCore Gateway. This gives you one protocol across the tools and makes them discoverable by different agents.
3) Centralized tool catalog. Teams shouldn’t build the same database connector five times. Maintain an approved catalog of tools that have been reviewed by security and tested in production. When a new team needs a capability, they start by checking the catalog.
4) Code examples with every tool. Documentation alone isn’t enough. Show developers how to integrate each tool with working code samples that they can copy and adapt.
The following table shows what effective tool documentation includes:

![tool documenation](/static/40-lab3/lab3_tool-documenation.png)

In Lab 2, we deployed our agent to AgentCore Runtime and personalized it using AgentCore Memory. Now we turn our attention to scaling tool access by exposing our tools through AgentCore Gateway, a managed MCP-compatible proxy that enables multiple agents to discover, authenticate, and invoke tools through a unified endpoint.

We'll migrate from tools defined directly in our agent code to centralized, enterprise-ready tools managed through the Gateway.

## Why Use AgentCore Gateway?

Great agents need tools that take full advantage of proprietary and third-party APIs and data. However, building, securing, and scaling agent tools is difficult, becoming a significant blocker for customers moving from prototypes to production.

In most organizations, valuable business logic already exists — as Lambda functions, REST APIs, or internal services — but it wasn't built with AI agents in mind. AgentCore Gateway lets you "MCPify" those existing resources, turning them into tools that any agent can discover and use through the standard MCP protocol, without modifying the original code.

AgentCore Gateway supports a wide range of target types:
- **AWS Lambda functions** — Wrap existing serverless functions as MCP tools
- **Amazon API Gateway REST API stages** — Expose managed REST APIs directly
- **OpenAPI schema targets** — Point at any OpenAPI-described HTTP service
- **Smithy model targets** — Use Smithy service models as tool definitions
- **MCP server targets** — Proxy and secure existing MCP-compatible endpoints
- **Built-in templates from integration providers** — Pre-built connectors for popular third-party services

In this lab, we'll focus on the Lambda target type, but the same Gateway can mix and match all of these behind a single MCP endpoint.

AgentCore Gateway provides:

- **Simplify tool development and integration** — Turn existing Lambda functions, APIs, and services into agent-ready MCP tools without rewriting code
- **Accelerate agent development through unified access** — A single MCP endpoint gives every agent access to all registered tools
- **Scale with confidence through intelligent tool discovery** — Agents automatically discover available tools and their capabilities via the MCP protocol
- **Comprehensive authentication** — JWT-based inbound auth, plus outbound credentials (API keys, OAuth) for upstream services
- **Framework compatibility** — Works with any MCP-compatible agent framework (Strands, LangChain, CrewAI, etc.)
- **Serverless infrastructure** — Fully managed, no servers to provision or scale

## What You'll Build

### Tool Centralization & Reusability
- Take an existing Lambda function (warranty check) — imagine it's owned by another team in your organization — and MCPify it through AgentCore Gateway
- Expose it as an MCP-compatible tool so any agent can discover and call it
- Update the existing agent to access tools via Gateway alongside local tools

### Architecture Change

:::code{language=json showCopyAction=false}
Lab 1-2 (Local tools):
  Agent → [get_return_policy(), get_product_info()] (in code)
  Agent → [Exa AI MCP] (direct connection)

Lab 3 (Gateway + Local):
  Agent → Gateway → [Lambda: check_warranty]
  Agent → [get_return_policy(), get_product_info()] (kept local)
  Agent → [Exa AI MCP] (kept as direct MCP client)
:::

![architecture](/static/40-lab3/lab3_architecture_diagram.png)


## Step 1: Verify the AWS Lambda Function

If you still have the dev server running from Lab 2, stop it first.

This lab uses a Lambda function (`workshop-warranty-check`) that simulates an enterprise warranty check API maintained by another team in your organization. This is a common real-world scenario: useful business logic already exists as Lambda functions, but it wasn't designed for AI agents. AgentCore Gateway lets you MCPify these existing functions — making them discoverable and callable by any agent — without touching the original Lambda code.

:::alert{type="info" header="Workshop Studio (AWS event)"}
If you are running this workshop from a **Workshop Studio** account, the Lambda function has already been created for you. Go check it out in the AWS Console:

👉 [Open the workshop-warranty-check Lambda function](https://console.aws.amazon.com/lambda/home#/functions/workshop-warranty-check)
:::

:::alert{type="info" header="Self-paced"}
If you are running this workshop **self-paced**, the Lambda function was created when you deployed the CloudFormation stack in the [Prerequisites / Self-paced](../10-intro/12-self-paced/) step.
:::

Take a moment to review the function code in the console. It's a simple lookup against a hardcoded warranty database:

:::code{language=python showCopyAction=false}
import json

WARRANTIES = {
    "PROD-001": {"product": "Wireless Headphones", "warranty_months": 12, "status": "active", "expires": "2027-03-01"},
    "PROD-002": {"product": "Smart Watch", "warranty_months": 24, "status": "active", "expires": "2028-01-15"},
    "PROD-003": {"product": "Laptop Stand", "warranty_months": 6, "status": "expired", "expires": "2026-01-01"},
    "PROD-004": {"product": "USB-C Hub", "warranty_months": 12, "status": "active", "expires": "2027-06-20"},
}

def handler(event, context):
    product_id = event.get("product_id", "").upper()
    if product_id in WARRANTIES:
        return {"statusCode": 200, "body": json.dumps(WARRANTIES[product_id])}
    return {"statusCode": 404, "body": json.dumps({"error": f"No warranty found for {product_id}"})}
:::

> **How the Gateway invokes Lambda:** AgentCore Gateway passes tool parameters directly in the Lambda `event` (not inside `event["body"]`). The tool name is available in `context.client_context.custom["bedrockAgentCoreToolName"]` with the format `<TargetName>___<tool_name>`. Since we have a single tool per Lambda, we only need to read the parameters from `event`.

Now retrieve the Lambda ARN from Parameter Store (it was saved there by the prerequisites stack):

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
WARRANTY_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/warranty_check_lambda_arn \
  --query 'Parameter.Value' --output text)

echo "Lambda ARN: $WARRANTY_LAMBDA_ARN"
```
:::
:::tab{label="Windows"}
```powershell
$WARRANTY_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/customersupport/agentcore/warranty_check_lambda_arn `
  --query 'Parameter.Value' --output text

Write-Host "Lambda ARN: $WARRANTY_LAMBDA_ARN"

```
:::
::::

## Step 2: Create Tool Schema

For an AI agent to use a tool, it needs to understand what the tool does, what parameters it expects, and what it returns — all described in natural language. This is exactly what the MCP protocol provides: a standard way for tools to advertise their capabilities so agents can reason about when and how to call them.

Lambda functions, however, don't carry that metadata. A Lambda is just code with an input event and an output — there's no built-in way for an agent to know what `workshop-warranty-check` does or what arguments to pass it.

This is where AgentCore Gateway bridges the gap. It wraps your Lambda (or API, or MCP server) behind an MCP-compatible endpoint, but it still needs you to provide the tool description — the name, a natural-language description, and the input schema. That's what we're creating here.

Create the schema file:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
mkdir -p app/CustomerSupport/tool
touch app/CustomerSupport/tool/__init__.py
touch app/CustomerSupport/tool/warranty_schema.json
```
:::
:::tab{label="Windows"}
```powershell
mkdir app\CustomerSupport\tool
New-Item app\CustomerSupport\tool\__init__.py -Force
New-Item app\CustomerSupport\tool\warranty_schema.json -Force

```
:::
::::

Open `app/CustomerSupport/tool/warranty_schema.json` in Kiro's editor and add the following:

:::code{language=json}
[
  {
    "name": "check_warranty",
    "description": "Check the warranty status of a product by its product ID (e.g. PROD-001). Returns warranty duration, status (active/expired), and expiration date.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "product_id": {
          "type": "string",
          "description": "The product ID to check warranty for (e.g. PROD-001)"
        }
      },
      "required": ["product_id"]
    }
  }
]
:::

Notice how the `description` fields use natural language — this is what the agent reads to decide whether to call the tool and how to fill in the parameters. Without this, the Gateway would have no way to present the Lambda as a meaningful tool to the agent.

⚠️ **Important:** The `inputSchema` must NOT have a nested `"json"` wrapper. Use `"type": "object"` directly inside `inputSchema`, otherwise the deployment will fail with "Attribute type null is not yet supported".

## Step 3: Add Gateway and Target via CLI

Now we wire it all together. We'll create a Gateway (a managed MCP endpoint) and register the Lambda function as a target. Remember, Lambda is just one of many target types — you could just as easily add an API Gateway REST API stage, an OpenAPI endpoint, a Smithy model, an existing MCP server, or a built-in provider template to the same Gateway.

In Kiro's terminal:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
# Create the gateway linked to the existing CustomerSupport agent
agentcore add gateway --name my-gateway --runtimes CustomerSupport

# Add warranty check Lambda as a target (using the ARN retrieved from Parameter Store in Step 1)
agentcore add gateway-target \
  --type lambda-function-arn \
  --name WarrantyCheck \
  --lambda-arn $WARRANTY_LAMBDA_ARN \
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json \
  --gateway my-gateway
```
:::
:::tab{label="Windows"}
```powershell
# Create the gateway linked to the existing CustomerSupport agent
agentcore add gateway --name my-gateway --runtimes CustomerSupport

# Add warranty check Lambda as a target (using the ARN retrieved from Parameter Store in Step 1)
agentcore add gateway-target `
  --type lambda-function-arn `
  --name WarrantyCheck `
  --lambda-arn $WARRANTY_LAMBDA_ARN `
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json `
  --gateway my-gateway

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added gateway 'my-gateway'
Added gateway target 'WarrantyCheck'
:::

> **Note:** The `--runtimes CustomerSupport` flag tells the CLI to inject the gateway URL as an environment variable (`AGENTCORE_GATEWAY_MY_GATEWAY_URL`) into the CustomerSupport agent runtime after deployment.

## Step 4: Update Your Agent to Use Gateway Tools

Instead of creating a new agent, we'll update the existing CustomerSupport agent to use the gateway tools alongside the local tools — just like the original workshop does.

First, update `app/CustomerSupport/mcp_client/client.py` in Kiro's editor to add the gateway MCP client:

:::alert{header="What this code does" type="info"}
This adds a new `get_gateway_mcp_client()` function alongside the existing Exa AI client. It reads the gateway URL from the `AGENTCORE_GATEWAY_MY_GATEWAY_URL` environment variable (injected by AgentCore Runtime after deployment) and creates an MCP client that connects to your gateway endpoint. If the URL isn't set (e.g., during local dev), it gracefully returns `None`.
:::

:::code{language=python}
import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# ExaAI MCP endpoint for web search
EXAMPLE_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client for Exa AI web search"""
    return MCPClient(lambda: streamablehttp_client(EXAMPLE_MCP_ENDPOINT))


def get_gateway_mcp_client() -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, if configured"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(url))
:::

Then update `app/CustomerSupport/main.py` to import and use the gateway client. The key change is adding `get_gateway_mcp_client` to the MCP clients list:

:::alert{header="What changed from Lab 2" type="info"}
The only changes are importing `get_gateway_mcp_client` and adding it to the `mcp_clients` list. This gives your agent access to the gateway tools (like the order lookup Lambda) alongside the existing Exa AI web search and local tools. Other changes include removing warranty information from the PRODUCTS data as that will be fetched from the AgentCore Gateway. The agent automatically discovers all available tools from both MCP clients.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import json

app = BedrockAgentCoreApp()
log = app.logger

# MCP clients: Exa AI (web search) + AgentCore Gateway (Lambda tools)
mcp_clients = [get_streamable_http_mcp_client(), get_gateway_mcp_client()]

SYSTEM_PROMPT="""You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following local tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications

You have access to tools outside of the local tools through MCP, use them as necessary.
Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Customer Support Tools ---

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life"},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery"},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup"},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet"},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches"},
}

@tool
def get_return_policy(product_category: str) -> str:
    """Get return policy information for a specific product category.

    Args:
        product_category: Product category (e.g., 'electronics', 'accessories', 'audio')

    Returns:
        Formatted return policy details including timeframes and conditions
    """
    category = product_category.lower()
    if category in RETURN_POLICIES:
        policy = RETURN_POLICIES[category]
        return f"Return policy for {category}: Window: {policy['window']}, Condition: {policy['condition']}, Refund: {policy['refund']}"
    return f"No specific return policy found for '{product_category}'. Please contact support for details."

@tool
def get_product_info(query: str) -> str:
    """Search for product information by name, ID, or keyword.

    Args:
        query: Product name, ID (e.g., 'PROD-001'), or search keyword

    Returns:
        Product details including name, price, category, and description
    """
    query_lower = query.lower()
    # Search by ID
    if query.upper() in PRODUCTS:
        p = PRODUCTS[query.upper()]
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}"
    # Search by keyword
    results = [f"{pid}: {p['name']} - ${p['price']} - {p['description']}" for pid, p in PRODUCTS.items()
               if query_lower in p['name'].lower() or query_lower in p['description'].lower() or query_lower in p['category'].lower()]
    if results:
        return "Found products:\n" + "\n".join(results)
    return f"No products found matching '{query}'."

tools = [get_return_policy, get_product_info]

# Add MCP client (Exa AI web search) to tools
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)

# --- Agent Setup ---

_agent = None

def get_or_create_agent(session_id, user_id):
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            session_manager=get_memory_session_manager(session_id, user_id),
            system_prompt=SYSTEM_PROMPT,
            tools=tools
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    user_id = context.request_headers['x-amzn-bedrock-agentcore-runtime-custom-user-id']

    if not session_id or not user_id:
        raise ValueError("session_id and user_id are required. Pass --session-id and --user-id when invoking.")

    agent = get_or_create_agent(session_id, user_id)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
:::

The local tools (`get_return_policy`, `get_product_info`) remain in the agent code. The gateway tool (`check_warranty`) is discovered automatically via the MCP client at runtime.

**How it works:** After deployment, the AgentCore Runtime injects `AGENTCORE_GATEWAY_MY_GATEWAY_URL` as an environment variable. The `get_gateway_mcp_client()` function reads this URL and creates an MCP client that connects to the gateway. The gateway routes requests to the Lambda functions.

## Step 5: Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

This deploys everything in one command:
- Gateway + Lambda target
- Updated agent runtime (CustomerSupport) with gateway URL injected
- IAM roles and policies

**Note:** The first gateway deployment takes ~2 minutes.

## Step 6: Test Gateway Tools

Test the warranty check tool:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_C=$(python3 -c "import uuid; print(uuid.uuid4())")
agentcore invoke "Check the warranty for product PROD-003" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_C = [guid]::NewGuid().ToString()
agentcore invoke "Check the warranty for product PROD-003" `
  --session-id $SESSION_C `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream

```
:::
::::

Expected response:
:::code{language=bash showCopyAction=false}
The warranty for PROD-003 (Laptop Stand) is:
- Warranty Duration: 6 months
- Status: Expired
- Expiration Date: January 1, 2026
:::

Test with an active warranty:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "Is the warranty still valid for PROD-002?" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "Is the warranty still valid for PROD-002?" `
  --session-id $SESSION_C `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream

```
:::
::::

Expected: The agent calls `check_warranty` via the Gateway and returns that the Smart Watch warranty is active until 2028.

## What Just Happened?

### Before (Lab 1-2)
- Tools defined as Python functions in `main.py`
- Only one agent could use them
- No authentication or access control

### After (Lab 3)
- An existing Lambda function (owned by another team) is now MCPified through the Gateway
- Any agent in the project can discover and call it via the Gateway's MCP endpoint
- Gateway handles routing, discovery, and authentication
- The Lambda code was never modified — only a tool schema was added
- The same Gateway could expose API Gateway stages, OpenAPI services, Smithy models, MCP servers, or built-in provider templates

### How the Gateway Works

:::code{language=bash showCopyAction=false}
agentcore invoke "Check warranty for PROD-003"
    ↓
AgentCore Runtime (CustomerSupport)
    ↓
Agent reads AGENTCORE_GATEWAY_MY_GATEWAY_URL from env
    ↓
MCP Client connects to Gateway
    ↓
Gateway routes to WarrantyCheck Lambda target
    ↓
Lambda executes and returns result
    ↓
Agent synthesizes response
:::

## Congratulations!

You've MCPified an existing Lambda function and moved from local tools to enterprise-ready, centralized tool management:

- ✅ **Existing Lambda** turned into an MCP-compatible tool without code changes
- ✅ **Tool schema** bridges the gap between raw Lambda functions and agent-friendly MCP tools
- ✅ **Gateway** handles routing, discovery, and authentication
- ✅ **Multiple agents** can share the same tools
- ✅ **Multiple target types** — Lambda, API Gateway stages, OpenAPI, Smithy, MCP servers, and built-in provider templates behind one endpoint


### What's Next

In Lab 4, you'll deploy your agent to production with full observability using AgentCore Runtime and CloudWatch.

→ Next: [Lab 4: Securing and Observing in Production](../50-lab4-deploy/)