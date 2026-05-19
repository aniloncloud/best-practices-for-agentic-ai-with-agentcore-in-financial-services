---
title: "Lab 3: Secure with JWT Authentication"
weight: 42
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Authentication answers "who is calling?" — and you need it on both endpoints. Runtime and Gateway are independent HTTPS endpoints: securing only one leaves the other open. In this lab you apply the same Cognito JWT authorizer to both and propagate the token from Runtime to Gateway automatically.

### What You're Building

:::code{language=bash showCopyAction=false}
Client (+ JWT token)  ← THIS LAB adds auth
    ↓
┌──────────────────────────────────────────────────┐
│ Cognito validates token (signature + expiry)     │
└──────────────────────────────────────────────────┘
    ↓
AgentCore Runtime (JWT required)  ← secured
    │
    │ forwards token
    ▼
AgentCore Gateway (JWT required)  ← secured
    ├── PortfolioRiskCheck → Lambda
    └── ExecuteTrade → Lambda
:::

## Step 1: Retrieve Cognito Configuration

The prerequisites stack stored all Cognito values in SSM Parameter Store. Retrieve them now:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
COGNITO_DISCOVERY_URL=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/cognito_discovery_url \
  --query 'Parameter.Value' --output text)

COGNITO_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/client_id \
  --query 'Parameter.Value' --output text)

COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)

echo "Discovery URL: $COGNITO_DISCOVERY_URL"
echo "Client IDs:    $COGNITO_CLIENT_ID  $COGNITO_WEB_CLIENT_ID"
```
:::
:::tab{label="Windows"}
```powershell
$COGNITO_DISCOVERY_URL = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/cognito_discovery_url `
  --query 'Parameter.Value' --output text

$COGNITO_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/client_id `
  --query 'Parameter.Value' --output text

$COGNITO_WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/web_client_id `
  --query 'Parameter.Value' --output text

Write-Host "Discovery URL: $COGNITO_DISCOVERY_URL"
Write-Host "Client IDs:    $COGNITO_CLIENT_ID  $COGNITO_WEB_CLIENT_ID"

```
:::
::::

## Step 2: Secure the Runtime

Open `agentcore/agentcore.json` and add three fields to the `PortfolioAdvisor` runtime entry, replacing the placeholder values with the ones retrieved above:

:::code{language=json showCopyAction=false}
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
:::

> `discoveryUrl` tells AgentCore Runtime where to fetch Cognito's signing keys. `allowedClients` rejects tokens from any other app client. Adding `Authorization` to `requestHeaderAllowlist` lets your agent forward the token to the Gateway in Step 5.

Add `import jwt` at the top of `app/PortfolioAdvisor/main.py`, then add the `extract_user_id()` helper and update the `invoke` function. Everything else in the file stays the same:

:::code{language=python}
import jwt  # add to existing imports at top of main.py

def extract_user_id(context) -> str:
    """Extract user identity from JWT bearer token, or fall back to custom header."""
    headers = context.request_headers or {}
    auth_header = headers.get("Authorization") or headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username") or claims.get("sub")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT: {e}")
    return headers.get("x-amzn-bedrock-agentcore-runtime-custom-user-id", "anonymous")

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent...")
    session_id = context.session_id
    user_id = extract_user_id(context)
    agent = get_or_create_agent(session_id, user_id)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
:::

Deploy the updated configuration:

:::code{language=bash}
agentcore validate
:::

:::code{language=bash}
agentcore deploy -y -v
:::

## Step 3: Obtain a Token

The test user `workshopuser@example.com` is already provisioned in the Cognito User Pool. Authenticate to get an access token:

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

:::alert{header="Token expiry" type="info"}
Tokens are valid for 60 minutes. If you see an auth error later, re-run this block.
:::

## Step 4: Test Authenticated Access

Invoke the agent with the bearer token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_3=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What's the risk analysis for TSLA?" \
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_3 = [guid]::NewGuid().ToString()

agentcore invoke "What's the risk analysis for TSLA?" `
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream

```
:::
::::

Now verify that unauthenticated requests are rejected — omit the token and expect a 401:

:::code{language=bash}
agentcore invoke "What's the risk analysis for TSLA?" \
  --session-id $SESSION_3 --stream
:::

You should see a 401 Unauthorized error — the Runtime is now secured.

## Step 5: Secure the Gateway

Gateway authorizer configuration cannot be updated in-place. Remove the existing gateway and recreate it with JWT authentication enabled:

:::code{language=bash}
agentcore remove gateway --name my-gateway -y
:::

Create a new gateway with the Cognito JWT authorizer:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway --name my-gateway-secure --runtimes PortfolioAdvisor \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway --name my-gateway-secure --runtimes PortfolioAdvisor `
  --authorizer-type CUSTOM_JWT `
  --discovery-url $COGNITO_DISCOVERY_URL `
  --allowed-clients "$COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID"

```
:::
::::

Re-add the portfolio risk check target (retrieve its ARN from SSM, then add it):

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
PORTFOLIO_RISK_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn \
  --query 'Parameter.Value' --output text)
agentcore add gateway-target \
  --type lambda-function-arn \
  --name PortfolioRiskCheck \
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
$PORTFOLIO_RISK_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn `
  --query 'Parameter.Value' --output text
agentcore add gateway-target `
  --type lambda-function-arn `
  --name PortfolioRiskCheck `
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json `
  --gateway my-gateway-secure

```
:::
::::

Update `app/PortfolioAdvisor/mcp_client/client.py` — two changes: the env var name changes to `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL`, and `get_gateway_mcp_client` now accepts and forwards an `auth_header`:

:::code{language=python}
import os, logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)
EXAMPLE_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"

def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client for Exa AI web search"""
    return MCPClient(lambda: streamablehttp_client(EXAMPLE_MCP_ENDPOINT))

def get_gateway_mcp_client(auth_header: str = "") -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, forwarding the caller's JWT"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(
        url=url, headers={"Authorization": auth_header}
    ))
:::

:::code{language=bash}
agentcore deploy -y -v
:::

## Step 6: Test End-to-End

Verify that both local tools and Gateway tools work with authentication:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_4=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Local tool — compliance rules
agentcore invoke "What are the compliance rules for options trading?" \
  --session-id $SESSION_4 --bearer-token "$TOKEN" --stream

# Gateway tool — portfolio risk via Lambda
agentcore invoke "Check the risk profile for PORT-005" \
  --session-id $SESSION_4 --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_4 = [guid]::NewGuid().ToString()

# Local tool — compliance rules
agentcore invoke "What are the compliance rules for options trading?" `
  --session-id $SESSION_4 --bearer-token "$TOKEN" --stream

# Gateway tool — portfolio risk via Lambda
agentcore invoke "Check the risk profile for PORT-005" `
  --session-id $SESSION_4 --bearer-token "$TOKEN" --stream

```
:::
::::

## Architecture

:::code{language=bash showCopyAction=false}
Client (JWT token)
    ↓ Cognito validates
AgentCore Runtime (PortfolioAdvisor)  [requires JWT]
    ├── get_stock_analysis(), get_compliance_rules()
    └── MCP → AgentCore Gateway (my-gateway-secure)  [requires JWT]
                    ↓
              Lambda: check_portfolio_risk
:::

## What Just Happened?

Both endpoints now require a valid Cognito JWT. Unauthenticated requests are rejected at the Runtime before reaching agent code. The same token flows from the Runtime to the Gateway, so the caller's identity is validated at every layer. The Lambda tools remain unchanged — only the access path is now secured.

---

## Best Practices: Defense in Depth for Agent Systems

:::alert{header="Best Practice" type="info"}
**Secure every layer independently.** An agent system has multiple callable surfaces — Runtime, Gateway, and upstream APIs. Assume each endpoint will be discovered and called directly. Authenticate at all of them.
:::

- **Both layers need auth.** Runtime and Gateway are independent HTTPS endpoints. Securing only the Runtime leaves the Gateway URL open — callers can bypass your agent and invoke Lambda tools directly. Each layer must reject unauthorized requests on its own.

- **Design for token expiry.** Cognito access tokens expire after 60 minutes. Production systems should refresh proactively using the `REFRESH_TOKEN_AUTH` flow — do not wait for a 401 error to trigger a refresh.

- **Least privilege with `allowedClients`.** Issue separate Cognito app clients for different callers (users, pipelines, other agents) and list only the ones that need access. A compromised credential then affects only that one client.

- **Cognito rotates signing keys automatically.** AgentCore Runtime fetches the public keys from the OIDC `discoveryUrl` on each validation, so key rotation is transparent — no manual steps required.

- **Never embed tokens in code or prompts.** JWT tokens are credentials. Do not log them, store them in persistent environment variables, or include them in system prompts or tool descriptions. Read the token from the request context per invocation, forward it, and treat it as ephemeral.

**Multi-tenant isolation:**

When a single agent deployment serves multiple users or teams, the security architecture must guarantee:

| Requirement | How AgentCore Addresses It |
|---|---|
| User A can't see User B's data | Session isolation (microVM per session) + JWT `sub` claim scoping |
| Role-based permissions | JWT custom claims (`role`, `team`) → Cedar policies evaluate them (Lab 4) |
| Audit per-user | JWT `sub` claim logged in every trace → query by user identity |
| Emergency revocation | Disable the Cognito app client → all tokens issued by that client immediately fail validation |
| Key rotation | Cognito rotates JWKS automatically; AgentCore re-fetches from `discoveryUrl` on each validation |

**Token lifecycle in production:**

```
User authenticates → Cognito issues access token (60 min TTL)
    ↓
Client stores token (memory only — never disk)
    ↓
Client passes token on each invocation (Authorization header)
    ↓
AgentCore Runtime validates (signature + expiry + audience + issuer)
    ↓
Runtime forwards to Gateway (same token, re-validated)
    ↓
Token expires → Client uses refresh token → New access token (no re-login)
```

For long-running sessions (up to 8 hours in AgentCore), the client application is responsible for proactive refresh. A common pattern: refresh when the token has < 5 minutes remaining, not when a 401 is received.

---

### What's Next

In Lab 4, you'll govern what your agent is allowed to do — applying action-level policies that constrain tool calls even for authenticated users.

→ Next: [Lab 4: Govern Agent Actions with Policies](../50-lab4-governance/)
