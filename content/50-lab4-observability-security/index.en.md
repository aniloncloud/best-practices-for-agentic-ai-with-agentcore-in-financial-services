---
title: "Lab 4: Securing and Observing in Production"
weight: 52
---

**⏱️ Estimated time: ~15 minutes**

## Instrument everything from day one

One of the most significant mistakes teams can make with observability is treating it as something to add later. By the time you realize you need it, you’ve already shipped an agent, which can make it harder to debug effectively.

From your first test query, you need visibility into what your agent is doing. AgentCore services emit OpenTelemetry traces automatically. Model invocations, tool calls, and reasoning steps get captured. When a query takes twelve seconds, you can see whether the delay came from the language model, a database query, or an external API call.

The observability strategy should include three layers:

Enable trace-level debugging during development so you can see the steps of each conversation. When users report incorrect behavior, pull up the specific trace and see exactly what the agent did.
Set up dashboards for production monitoring using the Amazon CloudWatch Generative AI observability dashboards that come with AgentCore Observability.
Track token usage, latency percentiles, error rates, and tool invocation patterns. Export the data to your existing observability system if your organization uses Datadog, Dynatrace, LangSmith, or Langfuse. The figure below shows how AgentCore Observability allows you to deep dive into your agent’s trace and meta data information inside a session invocation
In the previous labs, you built a customer support agent (Lab 1), added persistent memory (Lab 2), and centralized tools through AgentCore Gateway (Lab 3). Along the way, your agent was already deployed to AgentCore Runtime — the CLI handled deployment incrementally with each `agentcore deploy`.

In this lab, you'll explore the production capabilities that are already active in your deployed agent:

- **Session continuity** — Multiple conversations with isolated context per session
- **Observability** — Traces, metrics, and logs via CloudWatch GenAI Observability
- **Runtime management** — Status, logs, and traces via the AgentCore CLI
- **Security** — JWT-based authentication to protect your runtime endpoint

### What's Already Running

By this point, your deployed infrastructure includes:

| Resource | Status | Created In |
|----------|--------|------------|
| AgentCore Runtime | ✅ READY | Lab 2 (first deploy) |
| AgentCore Memory | ✅ Deployed | Lab 2 |
| AgentCore Gateway | ✅ Deployed | Lab 3 |
| CloudWatch Observability | ✅ Active | Automatic with Runtime |

## Step 1: Verify Your Deployment

In Kiro's terminal, check the status of all deployed resources:

:::code{language=bash}
agentcore status
:::

You should see all resources deployed and ready:

:::code{language=bash showCopyAction=false}
AgentCore Status (target: default, us-east-1)

Agents
  CustomerSupport: Deployed - Runtime: READY (arn:aws:bedrock-agentcore:...)

Memories
  SharedMemory: Deployed (SEMANTIC, SUMMARIZATION) (arn:aws:bedrock-agentcore:...)

Gateways
  my-gateway: Deployed (1 target) (customersupport-my-gateway-...)
:::

## Step 2: Test Session Continuity

AgentCore Runtime provides built-in session management. You pass a `--session-id` with each invocation, and the Runtime keeps conversation context within that session while keeping different sessions completely isolated.

Each session runs in its own microVM, so a single user stays on the same execution environment for the entire conversation — up to 8 hours, which is the maximum session duration for AgentCore Runtime. In practice, there's a one-to-one mapping between a user and their session. Our memory module (from Lab 2) takes advantage of this — it stores and retrieves memories using the combination of `session_id` and `user_id`.

To see session discontinuity in action, we'll start a separate session and show that context from the first one doesn't carry over.

**Start a conversation in Session 1:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_1=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "My name is Carlos and I just bought a Mechanical Keyboard" \
  --session-id $SESSION_1 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_1 = [guid]::NewGuid().ToString()
agentcore invoke "My name is Carlos and I just bought a Mechanical Keyboard" `
  --session-id $SESSION_1 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" `
  --stream

```
:::
::::

**Continue the same session:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "What did I just buy?" \
  --session-id $SESSION_1 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "What did I just buy?" `
  --session-id $SESSION_1 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" `
  --stream

```
:::
::::

Expected: The agent remembers Carlos bought a Mechanical Keyboard within the same session.

**Start a different session (Session 2):**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_2=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "What did I just buy?" \
  --session-id $SESSION_2 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_2 = [guid]::NewGuid().ToString()
agentcore invoke "What did I just buy?" `
  --session-id $SESSION_2 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Carlos" `
  --stream

```
:::
::::

Expected: The agent does NOT know what was bought — this is a completely separate session with no context from Session A.

> **Note:** Session IDs must be at least 33 characters long. Using UUIDs (as shown above) is the easiest way to generate valid session IDs.

> **How it works:** AgentCore Runtime isolates each session. The `session_id` is passed to the agent's `context` object and used by the memory session manager to scope memory retrieval. Within a session, the agent maintains conversation history. Across sessions, only long-term memory (SEMANTIC facts) is shared.

## Step 3: Explore Observability

AgentCore Runtime automatically instruments your agent with OpenTelemetry and sends traces to CloudWatch. Every invocation generates traces that capture the full conversation flow.

### View Traces via CLI

List recent traces for your agent:

:::code{language=bash}
agentcore traces list --limit 10
:::

Download a specific trace for detailed inspection:

:::code{language=bash}
agentcore traces get <trace-id> --output trace.json
:::

### View Logs via CLI

Stream live logs from your agent:

:::code{language=bash}
agentcore logs
:::

Search for errors in the last hour:

:::code{language=bash}
agentcore logs --since 1h --level error
:::

Search for specific patterns:

:::code{language=bash}
agentcore logs --since 1h --query "warranty"
:::

### View in CloudWatch Console

For a visual dashboard, navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/):

1. In the left panel, find **GenAI Observability** → **Bedrock AgentCore**
2. Click on **Agents** to see your CustomerSupport agent
3. Click on **Sessions** to see all conversation sessions
4. Click on **Traces** to see detailed request traces

Each trace shows:
- The complete conversation flow (user prompt → tool selection → tool execution → response)
- Latency breakdown for each step
- Memory retrieval and storage operations
- Gateway tool invocations

> **Note:** It takes ~10 minutes after the first invocation for traces to appear in CloudWatch. If you enabled Transaction Search in the prerequisites, traces should already be indexed.

# Scale securely with personalization

Moving from a prototype that works for one developer to a production system serving thousands of users introduces new requirements around isolation and security.
Security and access control must be enforced before tools execute. Users should only access data they have permission to see. 

## Step 4: Secure Your Runtime with Cognito Authentication

So far, your agent runtime accepts unauthenticated requests — anyone with the endpoint URL can invoke it. For a production application, this is not acceptable. You need to ensure that only authorized clients can call your agent.

AgentCore Runtime supports JWT-based authentication using a custom JWT authorizer. In this step, you'll configure your runtime to require a valid Cognito JWT token on every request, using the Cognito User Pool that was created as part of the workshop prerequisites.

### Retrieve Cognito configuration from Parameter Store

The prerequisites CloudFormation stack stored the Cognito configuration in SSM Parameter Store. Retrieve the values you need:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
COGNITO_DISCOVERY_URL=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/cognito_discovery_url \
  --query 'Parameter.Value' --output text)

COGNITO_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/client_id \
  --query 'Parameter.Value' --output text)

COGNITO_POOL_ID=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/pool_id \
  --query 'Parameter.Value' --output text)

COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)

echo "Discovery URL: $COGNITO_DISCOVERY_URL"
echo "Client ID:     $COGNITO_CLIENT_ID"
echo "Pool ID:       $COGNITO_POOL_ID"
echo "Web Client ID: $COGNITO_WEB_CLIENT_ID"
```
:::
:::tab{label="Windows"}
```powershell
$COGNITO_DISCOVERY_URL = aws ssm get-parameter `
  --name /app/customersupport/agentcore/cognito_discovery_url `
  --query 'Parameter.Value' --output text

$COGNITO_CLIENT_ID = aws ssm get-parameter `
  --name /app/customersupport/agentcore/client_id `
  --query 'Parameter.Value' --output text

$COGNITO_POOL_ID = aws ssm get-parameter `
  --name /app/customersupport/agentcore/pool_id `
  --query 'Parameter.Value' --output text

$COGNITO_WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/customersupport/agentcore/web_client_id `
  --query 'Parameter.Value' --output text

Write-Host "Discovery URL: $COGNITO_DISCOVERY_URL"
Write-Host "Client ID:     $COGNITO_CLIENT_ID"
Write-Host "Pool ID:       $COGNITO_POOL_ID"
Write-Host "Web Client ID: $COGNITO_WEB_CLIENT_ID"

```
:::
::::

### Update agentcore.json

Open `agentcore/agentcore.json` in Kiro's editor. 

In the `runtimes` array, find the `"CustomerSupport"` entry and add `Authorization` to the list of `requestHeaderAllowlist`, `authorizerType` and `authorizerConfiguration` fields:

:::code{language=json showCopyAction=false}
"runtimes": [
  {
    "name": "CustomerSupport",
    "build": "CodeZip",
    "entrypoint": "main.py",
    "codeLocation": "app/CustomerSupport/",
    "runtimeVersion": "PYTHON_3_13",
    "networkMode": "PUBLIC",
    "protocol": "HTTP",
    "requestHeaderAllowlist": [
      "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
      "Authorization"
    ],
    "authorizerType": "CUSTOM_JWT",
    "authorizerConfiguration": {
      "customJwtAuthorizer": {
        "discoveryUrl": "<COGNITO_DISCOVERY_URL value>",
        "allowedClients": ["<COGNITO_CLIENT_ID value>", "<COGNITO_WEB_CLIENT_ID value>"]
      }
    }
  }
]
:::

Replace `<COGNITO_DISCOVERY_URL value>`, `<COGNITO_CLIENT_ID value>` and `<COGNITO_WEB_CLIENT_ID value>` with the values you retrieved above. The result should look something like (but with your own values for discoveryUrl and allowedClients):

:::code{language=json showCopyAction=false}
"requestHeaderAllowlist": [
  "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
  "Authorization"
],
"authorizerType": "CUSTOM_JWT",
"authorizerConfiguration": {
  "customJwtAuthorizer": {
    "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_aBcDeFgHi/.well-known/openid-configuration",
    "allowedClients": ["1abc2def3ghi4jkl5mno6pqr", "1ej35ccfkb716pc1iiv3421luj"]
  }
}
:::

> **What this does:** The `discoveryUrl` points to the Cognito OIDC discovery endpoint, which tells AgentCore Runtime how to validate incoming JWT tokens (where to fetch the signing keys, the issuer, etc.). The `allowedClients` list restricts access to tokens issued for that specific Cognito app client — any token from a different client will be rejected. The `requestHeaderAllowlist` will be important for the next session, once we add the Cognito authentication to AgentCore Gateway. It is the header that will allow your agent to propagate the authentication token to your MCP client.

### Update agent to take authentication into account
Now that the inbound auth for the agent is set, the agent code needs to get the user_id information, for memory access, from the brearer token upon successful authentication. 

Update `app/CustomerSupport/main.py` to add the `extract_user_id()` method that extracts the username from the claims information. The method is also backward compatible with respect to the previous labs. It fallsback to `user-id` in custom header if `Authorization` is not present in header. In production scenarios, this is unlikely to happen:

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import jwt

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

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications
3. Web search - To search the web for troubleshooting help

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Customer Support Tools ---

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life", "warranty_months": 12},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery", "warranty_months": 24},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup", "warranty_months": 6},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet", "warranty_months": 12},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches", "warranty_months": 24},
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
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}, Warranty: {p['warranty_months']} months"
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

def extract_user_id(context) -> str | None:
    """Extract user_id from JWT bearer token (username claim) or fall back to custom header."""
    headers = context.request_headers or {}

    # Try Authorization header first (Bearer JWT)
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT for user_id: {e}")
    else:
        log.info(f"No Bearer token found. Auth header present: {auth_header is not None}")

    # Fall back to custom header
    return headers.get("x-amzn-bedrock-agentcore-runtime-custom-user-id")

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    user_id = extract_user_id(context)

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

### Validate and deploy the updated configuration

Before deploying, validate that your `agentcore.json` changes are correct:

:::code{language=bash}
agentcore validate
:::

If validation passes, you'll see a success message. If there are issues (e.g., a missing comma, invalid JSON, or a malformed discovery URL), the CLI will tell you exactly what's wrong so you can fix it before deploying.

:::code{language=bash}
agentcore deploy -y -v
:::

### Test with authentication

After deployment, unauthenticated requests will be rejected. You need to create a Cognito user and obtain a token first.

The prerequisites stack created two Cognito app clients: a machine client (for `client_credentials`) and a web client (for user-based flows). You'll use the web client here to authenticate as a real user.

**Create a test user in the Cognito User Pool:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws cognito-idp admin-create-user \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --temporary-password 'TempPass1!' \
  --user-attributes Name=email,Value=workshopuser@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

# Set a permanent password so the user is confirmed and ready to use
aws cognito-idp admin-set-user-password \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --password 'WorkshopPass1!' \
  --permanent

echo "User 'workshopuser@example.com' created and confirmed"
```
:::
:::tab{label="Windows"}
```powershell
aws cognito-idp admin-create-user `
  --user-pool-id $COGNITO_POOL_ID `
  --username workshopuser@example.com `
  --temporary-password "TempPass1!" `
  --user-attributes "Name=email,Value=workshopuser@example.com" "Name=email_verified,Value=true" `
  --message-action SUPPRESS

# Set a permanent password so the user is confirmed and ready to use
aws cognito-idp admin-set-user-password `
  --user-pool-id $COGNITO_POOL_ID `
  --username workshopuser@example.com `
  --password "WorkshopPass1!" `
  --permanent

Write-Host "User 'workshopuser@example.com' created and confirmed"

```
:::
::::

> **Note:** The User Pool is configured with email as the username attribute, so the username must be a valid email address.

**Authenticate as the user and obtain a token:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "Token obtained successfully"
```
:::
:::tab{label="Windows"}
```powershell
$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

Write-Host "Token obtained successfully"

```
:::
::::

Now invoke the agent with the bearer token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_3=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "What's the return policy for electronics?" \
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_3 = [guid]::NewGuid().ToString()
agentcore invoke "What's the return policy for electronics?" `
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream

```
:::
::::

Try without the token to confirm it's rejected:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "What's the return policy for electronics?" \
  --session-id $SESSION_3 --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "What's the return policy for electronics?" `
  --session-id $SESSION_3 --stream

```
:::
::::

You should see an authentication error — your runtime is now secured.

## Step 5: Secure Your Gateway with Cognito Authentication

You've secured the runtime endpoint, but the AgentCore Gateway also accepts requests independently. To fully lock down your application, you should apply the same JWT authentication to the Gateway so that only authorized agents (or clients) can invoke the tools behind it.

> **Why secure the Gateway too?** The runtime and the Gateway are separate endpoints. Securing only the runtime means someone with the Gateway URL could still call your tools directly. By applying the same Cognito authorizer to both, you ensure end-to-end authentication — the client authenticates to the runtime, and the runtime's MCP client authenticates to the Gateway using the same token flow.

Gateway authorizer configuration can't be updated in-place, so we need to remove the existing gateway, deploy the removal, and then recreate it with authentication enabled.

### Remove the existing gateway

:::code{language=bash}
agentcore remove gateway --name my-gateway -y
:::


### Recreate the gateway with JWT authentication

Now create a new gateway with the Cognito JWT authorizer configured from the start. We'll use the same SSM parameter values retrieved in Step 4:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway --name my-gateway-secure --runtimes CustomerSupport \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway --name my-gateway-secure --runtimes CustomerSupport `
  --authorizer-type CUSTOM_JWT `
  --discovery-url $COGNITO_DISCOVERY_URL `
  --allowed-clients "$COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID"

```
:::
::::

### Re-add the warranty check target

The Lambda ARN should still be in your shell from Lab 3. If not, retrieve it again:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
WARRANTY_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/warranty_check_lambda_arn \
  --query 'Parameter.Value' --output text)
```
:::
:::tab{label="Windows"}
```powershell
$WARRANTY_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/customersupport/agentcore/warranty_check_lambda_arn `
  --query 'Parameter.Value' --output text

```
:::
::::

Add the target to the new gateway:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name WarrantyCheck \
  --lambda-arn $WARRANTY_LAMBDA_ARN \
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway-target `
  --type lambda-function-arn `
  --name WarrantyCheck `
  --lambda-arn $WARRANTY_LAMBDA_ARN `
  --tool-schema-file app/CustomerSupport/tool/warranty_schema.json `
  --gateway my-gateway-secure

```
:::
::::



> **Note:** The new gateway name is `my-gateway-secure`, so the injected environment variable will be `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL`. You also need to configure the Authorization header of your MCPClient. You need to update `app/CustomerSupport/mcp_client/client.py` to read the new variable name and pass the authorization header:

Open `app/CustomerSupport/mcp_client/client.py` and change the environment variable name:

:::alert{header="What changed from Lab 3" type="info"}
Two changes: (1) The gateway URL environment variable changed from `AGENTCORE_GATEWAY_MY_GATEWAY_URL` to `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL` to match the new secured gateway name. (2) The `get_gateway_mcp_client` function now accepts an `auth_header` parameter and passes it as an `Authorization` header to the gateway, so the JWT token from the runtime is forwarded to authenticate gateway requests.
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


def get_gateway_mcp_client(auth_header: str) -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, if configured"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(
        url=url,
        headers={"Authorization": auth_header}
    ))
:::

Since we are using the same Cognito client for AgentCore Runtime and AgentCore Gateway, you will need to update your `app/CustomerSupport/main.py` file to pass the authorization header to your gateway and let's use the Cognito username as the actor id for the agent memory:

:::alert{header="What changed from Lab 3" type="info"}
The `invoke` function now extracts the `Authorization` header from the incoming request context and passes it to `get_gateway_mcp_client`. This propagates the caller's JWT token from the Runtime to the Gateway, enabling end-to-end authentication. The gateway MCP client is now created per-request (inside `invoke`) instead of at startup, since each request may carry a different token.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import jwt

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT="""You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications
3. Web search - To search the web for troubleshooting help

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Customer Support Tools ---

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life", "warranty_months": 12},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery", "warranty_months": 24},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup", "warranty_months": 6},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet", "warranty_months": 12},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches", "warranty_months": 24},
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
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}, Warranty: {p['warranty_months']} months"
    # Search by keyword
    results = [f"{pid}: {p['name']} - ${p['price']} - {p['description']}" for pid, p in PRODUCTS.items()
               if query_lower in p['name'].lower() or query_lower in p['description'].lower() or query_lower in p['category'].lower()]
    if results:
        return "Found products:\n" + "\n".join(results)
    return f"No products found matching '{query}'."

# --- Agent Setup ---

_agent = None

def get_or_create_agent(session_id, user_id, auth_header):
    global _agent

    session_manager = get_memory_session_manager(session_id, user_id)

    # MCP clients: Exa AI (web search) + AgentCore Gateway (Lambda tools)
    mcp_clients = [get_streamable_http_mcp_client(), get_gateway_mcp_client(auth_header)]
    tools = [get_return_policy, get_product_info]

    # Add MCP client (Exa AI web search) to tools
    for mcp_client in mcp_clients:
        if mcp_client:
            tools.append(mcp_client)

    if _agent is None:
        _agent = Agent(
            model=load_model(),
            session_manager=session_manager,
            system_prompt=SYSTEM_PROMPT,
            tools=tools
        )
    return _agent

def extract_user_id(auth_header) -> str | None:
    """Extract user_id from JWT bearer token (username claim) or fall back to custom header."""

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT for user_id: {e}")
    else:
        log.info(f"No Bearer token found. Auth header present: {auth_header is not None}")
        raise Exception("No authorization header")

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    request_headers = context.request_headers

    # Access request headers - handle None case
    request_headers = context.request_headers or {}

    # Get Client JWT token
    auth_header = request_headers.get('Authorization', '')

    if not auth_header:
        raise Exception("No authorization header")

    user_id = extract_user_id(auth_header)

    if not session_id or not user_id:
        raise ValueError("session_id and user_id are required. Pass --session-id and --user-id when invoking.")

    agent = get_or_create_agent(session_id, user_id, auth_header)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()
:::

### Validate and deploy

:::code{language=bash}
agentcore validate
:::

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the secured Gateway

The warranty check tool goes through the Gateway. If the Gateway auth is working, this should succeed with a valid token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_E=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Check the warranty for PROD-001" \
  --session-id $SESSION_E --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_E = [guid]::NewGuid().ToString()
agentcore invoke "Check the warranty for PROD-001" `
  --session-id $SESSION_E --bearer-token "$TOKEN" --stream

```
:::
::::

The agent should return the warranty details for PROD-001 (Wireless Headphones, active, expires 2027-03-01). Both the runtime and the Gateway are now secured with the same Cognito identity provider.

## Step 6: Generate Test Traffic

Let's generate some varied interactions to populate the observability dashboard. Since the runtime is now secured, include the bearer token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_D=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What's the return policy for accessories?" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Tell me about the USB-C Hub" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Check the warranty for PROD-002" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Do you remember my name?" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_D = [guid]::NewGuid().ToString()

agentcore invoke "What's the return policy for accessories?" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Tell me about the USB-C Hub" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Check the warranty for PROD-002" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Do you remember my name?" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

```
:::
::::

After running these, wait a few minutes and check the CloudWatch dashboard to see the traces for each interaction, including which tools were called and how long each step took.

:::alert{type="info" header="Token expired?"}
The Cognito access token is valid for 60 minutes (as configured in the prerequisites stack). If you get an authentication error after some time, just re-run the token command from Step 4:
:::

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```
:::
:::tab{label="Windows"}
```powershell
$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

```
:::
::::

If you've started a new terminal session and lost the environment variables, re-run the full retrieval block from Step 4 ("Retrieve Cognito configuration" and "Test with authentication") to set them again.
:::

## Architecture

After completing this lab, your deployed architecture looks like this:

![Lab 4 Architecture](/static/50-lab4-deploy/lab4_architecture_diagram.png)

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (CustomerSupport)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION)
    ├── Local tools: get_return_policy(), get_product_info()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway → Lambda: check_warranty
                          ↓
                    CloudWatch (traces, logs, metrics)
:::

> **Observability still works as before.** Adding JWT authentication doesn't change how traces, logs, and metrics are collected. AgentCore Runtime continues to instrument every invocation with OpenTelemetry automatically — the only difference is that unauthenticated requests are now rejected before they reach your agent code, so you'll only see traces for legitimate, authorized calls.

## What Just Happened?

In this lab you took your agent from a working prototype to a production-ready deployment:

1. **Verified the deployment** — Confirmed that Runtime, Memory, and Gateway are all active and healthy
2. **Tested session continuity** — Demonstrated that conversations are isolated per session while long-term memory (SEMANTIC facts) is shared across sessions
3. **Explored observability** — Used the CLI and CloudWatch console to inspect traces, logs, and the full conversation flow including tool calls
4. **Secured the runtime** — Configured JWT-based authentication with Cognito so only authorized clients can invoke the agent
5. **Secured the Gateway** — Applied the same Cognito JWT authorizer to the Gateway for end-to-end authentication
6. **Generated test traffic** — Populated the observability dashboard with varied interactions to see the full picture

### What the CLI Does Behind the Scenes

When you run `agentcore deploy`, the CLI:

1. **Packages your code** — Zips your agent code with all dependencies from `.venv`
2. **Uploads to S3** — Stores the package in an S3 bucket managed by CDK
3. **Creates/Updates Runtime** — Provisions the AgentCore Runtime with your code, including the JWT authorizer configuration
4. **Creates/Updates Gateway** — Deploys the Gateway with targets and JWT authorizer configuration
5. **Injects environment variables** — Memory IDs, Gateway URLs, and credentials are automatically injected
6. **Enables observability** — OpenTelemetry instrumentation is enabled by default

### Session Management

| Feature | How It Works |
|---------|-------------|
| Session isolation | Each `--session-id` creates an independent conversation context |
| Session continuity | Same `--session-id` maintains conversation history |
| Cross-session memory | SEMANTIC facts (names, preferences) are shared across all sessions |
| Session-scoped memory | SUMMARIZATION is scoped to the specific session |

## Congratulations!

Your agent is running in production with:

- ✅ **Serverless runtime** — Auto-scaling, no infrastructure to manage
- ✅ **Session management** — Isolated conversations with continuity
- ✅ **Full observability** — Traces, logs, and metrics in CloudWatch
- ✅ **JWT authentication** — Only authorized clients can invoke your agent
- ✅ **CLI management** — Status, logs, and traces from your terminal

### What's Next

In Lab 5, you'll set up continuous quality monitoring with AgentCore Evaluations to ensure your production agent maintains high performance standards.

→ Next: [Lab 5: Evaluating Agent Quality](../60-lab5-evals/)
