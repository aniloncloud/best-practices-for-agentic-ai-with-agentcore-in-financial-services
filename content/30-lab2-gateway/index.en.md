---
title: "Lab 2: Connect Tools with Gateway + JWT Auth"
weight: 30
---

**⏱️ ~18 minutes (one deploy, ~2–3 min — you'll read through it)**

## Overview

Your agent has local tools (stock analysis, compliance rules), but real-world agents need access to existing business logic — Lambda functions, REST APIs, databases. Rather than embedding these connections directly in agent code, AgentCore Gateway provides a centralized control plane for tool access.

In this lab you'll do three things in one deploy:

1. Create a Gateway **with JWT authentication from the start** — no unauthenticated window
2. Register two Lambda tools (portfolio risk check and trade execution)
3. Secure the Runtime with the same Cognito authorizer, and make the **one code edit of this session** so the agent forwards the caller's identity

You'll end with a 5,000-share trade that goes through. Remember it — Lab 3 will stop it.

### What You're Building

:::code{language=bash showCopyAction=false}
User (Cognito JWT)
    ↓ Bearer token
AgentCore Runtime (PortfolioAdvisor)  ← JWT required  ← THIS LAB
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── MCP Client (forwards JWT)
              ↓
    AgentCore Gateway (my-gateway)    ← JWT required  ← THIS LAB
         ├── PortfolioRiskCheck → Lambda: workshop-check-portfolio-risk
         └── ExecuteTrade       → Lambda: workshop-execute-trade
:::

Both Runtime and Gateway now independently require a valid Cognito token. The same token flows from the caller through to each Lambda — you know **who** is calling at every hop.

---

## Step 1: Load Your Environment Variables

All Cognito and Lambda ARN values are pre-stored in SSM Parameter Store. Load them once now; both Lab 2 and Lab 3 need them.

Make sure you're in the project directory first — every command in this lab assumes it:

```bash
cd ~/PortfolioAdvisor
```

```bash
cat > ~/portfolio-env.sh <<'EOF'
P=/app/portfolioadvisor/agentcore
export COGNITO_DISCOVERY_URL=$(aws ssm get-parameter --name $P/cognito_discovery_url --query 'Parameter.Value' --output text)
export COGNITO_CLIENT_ID=$(aws ssm get-parameter --name $P/client_id --query 'Parameter.Value' --output text)
export COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter --name $P/web_client_id --query 'Parameter.Value' --output text)
export COGNITO_POOL_ID=$(aws ssm get-parameter --name $P/pool_id --query 'Parameter.Value' --output text)
export COGNITO_DOMAIN=$(aws ssm get-parameter --name $P/cognito_domain --query 'Parameter.Value' --output text)
export COGNITO_SCOPE=$(aws ssm get-parameter --name $P/cognito_auth_scope --query 'Parameter.Value' --output text)
export RISK_LAMBDA_ARN=$(aws ssm get-parameter --name $P/portfolio_risk_lambda_arn --query 'Parameter.Value' --output text)
export TRADE_LAMBDA_ARN=$(aws ssm get-parameter --name $P/execute_trade_lambda_arn --query 'Parameter.Value' --output text)
EOF
source ~/portfolio-env.sh
echo "Cognito client: $COGNITO_CLIENT_ID"
```

:::alert{header="Opening a new terminal later?" type="info"}
Run `source ~/portfolio-env.sh` again. Labs 2 and 3 both rely on these variables being set in the current shell.
:::

---

## Step 2: Create the Gateway (JWT-secured from the start)

```bash
agentcore add gateway --name my-gateway --runtimes PortfolioAdvisor \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID
```

You should see:

:::code{language=bash showCopyAction=false}
Added gateway 'my-gateway'
:::

`--discovery-url` tells the Gateway where to fetch Cognito's signing keys (the OIDC `/.well-known/openid-configuration` endpoint). `--allowed-clients` restricts access to only these two Cognito app clients — tokens issued for any other client are rejected outright.

In production you would never create a gateway unauthenticated even temporarily. We don't here either.

---

## Step 3: Register Both Lambda Tools

Add the portfolio risk tool:

```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name PortfolioRiskCheck \
  --lambda-arn $RISK_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json \
  --gateway my-gateway
```

Add the trade execution tool:

```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name ExecuteTrade \
  --lambda-arn $TRADE_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/trade_schema.json \
  --gateway my-gateway
```

The Lambda functions themselves are unchanged — the Gateway MCPifies them, making existing business logic discoverable by any agent.

---

## Step 4: Secure the Runtime with the Same Authorizer

Instead of hand-editing JSON (error-prone with multi-line strings), patch `agentcore/agentcore.json` with this one paste:

```bash
python3 - <<'EOF'
import json, os
p = "agentcore/agentcore.json"
cfg = json.load(open(p))
rt = cfg["runtimes"][0]
rt["requestHeaderAllowlist"] = ["X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id", "Authorization"]
rt["authorizerType"] = "CUSTOM_JWT"
rt["authorizerConfiguration"] = {"customJwtAuthorizer": {
    "discoveryUrl": os.environ["COGNITO_DISCOVERY_URL"],
    "allowedClients": [os.environ["COGNITO_CLIENT_ID"], os.environ["COGNITO_WEB_CLIENT_ID"]]}}
json.dump(cfg, open(p, "w"), indent=2)
print("Runtime authorizer configured.")
EOF
```

Verify the result:

```bash
cat agentcore/agentcore.json
```

You'll see three new fields on the runtime entry:

:::code{language=json showCopyAction=false}
"requestHeaderAllowlist": [
  "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
  "Authorization"
],
"authorizerType": "CUSTOM_JWT",
"authorizerConfiguration": {
  "customJwtAuthorizer": {
    "discoveryUrl": "<your-cognito-discovery-url>",
    "allowedClients": ["<client-id>", "<web-client-id>"]
  }
}
:::

Same `discoveryUrl` and `allowedClients` as the Gateway — one Cognito pool secures both endpoints. `Authorization` in `requestHeaderAllowlist` is what allows Step 5 to work: AgentCore passes that header into `context.request_headers` so the agent code can read and forward the token.

---

## Step 5: The One Code Edit — Forward the Caller's Identity

Open `app/PortfolioAdvisor/main.py`. Right now the `@app.entrypoint` function reads the session ID but ignores headers entirely:

:::code{language=python showCopyAction=false}
@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent...")
    session_id = context.session_id
    agent = get_or_create_agent(session_id)        # ← no auth_header passed
    ...
:::

The Gateway now requires a JWT on every request. Without this edit, the agent's MCP client will call the Gateway with no token and get a 401. The fix: read the `Authorization` header from the incoming context and pass it through.

Add `import jwt` to the imports at the top of `main.py`, then add the helper and replace the `invoke` function. Everything else in the file stays the same:

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
    headers = context.request_headers or {}
    auth_header = headers.get("Authorization") or headers.get("authorization", "")
    user_id = extract_user_id(context)
    agent = get_or_create_agent(session_id, user_id, auth_header)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
:::

`get_or_create_agent` already passes `auth_header` through to `get_gateway_mcp_client()` (see `mcp_client/client.py`) — that function attaches it as an `Authorization` header on every MCP request to the Gateway. This is **identity propagation**, not service identity: the agent forwards the caller's own token rather than presenting a separate service credential. The helper `extract_user_id` is defensive — it decodes the JWT without re-verifying the signature (the Runtime already validated it) and falls back to `"anonymous"` if anything fails.

---

## Step 6: Deploy

Validate configuration first, then deploy:

```bash
agentcore validate
```

```bash
agentcore deploy -y -v
```

This is your **second deploy** (first was Lab 1) and the last one until Lab 3. While it runs (~2–3 min), work through Step 7.

---

## Step 7: While This Deploys — Credential Patterns and Tool Schemas

::::expand{header="Read while the deploy runs (click to open)"}

### Credential Patterns for Agent-to-Tool Authentication

Three patterns exist; you're using JWT Passthrough in this lab.

| Pattern | How It Works | Best For |
|---------|-------------|----------|
| **IAM Service Credential** | Agent's execution role signs requests with SigV4 | Service-to-service; no user context needed |
| **JWT Passthrough** | Agent forwards the caller's Cognito token as-is | Per-user policies; user identity needed downstream |
| **Workload Identity (OBO)** | `GetWorkloadAccessTokenForJWT()` exchanges the user token for a scoped workload token | Multi-agent chains; third-party API OAuth exchange |

**Choosing a pattern:**

| Scenario | Pattern | Why |
|----------|---------|-----|
| Single-tenant agent, no per-user policies | IAM Service Credential | Simplest; no token management overhead |
| Per-user authorization or audit required | JWT Passthrough | Gateway applies policies based on user identity |
| Agent calls another agent's Gateway | Workload Identity (OBO) | Preserves user provenance across hops |
| Agent needs to call a third-party OAuth API | Workload Identity + Token Vault | Exchange user JWT for external OAuth tokens |

In this lab you're using JWT Passthrough: the user authenticates to Cognito, passes the token to the Runtime, and the Runtime's agent code forwards that same token to the Gateway. The Lambda tools receive requests whose identity traces back to the original user.

---

### Inspect the Tool Schemas

Open `app/PortfolioAdvisor/tool/portfolio_risk_schema.json` and `app/PortfolioAdvisor/tool/trade_schema.json` in the editor. These JSON Schema files are how the LLM decides when and how to use each tool — treat them like API documentation written for an AI reader.

| Schema Field | Good Example | Bad Example | Why It Matters |
|---|---|---|---|
| `description` | "Check portfolio risk metrics for a given portfolio ID (e.g., PORT-001). Returns risk score, VaR, and concentration data." | "Portfolio risk tool" | The LLM needs to know WHEN to call this tool and WHAT it returns |
| `inputSchema.properties.portfolio_id.description` | "Portfolio identifier in format PORT-XXX. Must be an active portfolio." | "The ID" | Format guidance reduces invalid calls |
| `inputSchema.required` | `["portfolio_id"]` | `[]` | Without required fields, the LLM may call the tool with missing params |

**Anti-patterns to avoid:**
- Generic descriptions ("processes the request") that apply to multiple tools — the LLM can't distinguish them
- Omitting return-value descriptions — the model can't choose between tools it doesn't understand
- Internal jargon absent from the system prompt — "run DTC check" means nothing without context
- Missing "do not use for X" guidance when tools overlap in purpose

::::

---

## Step 8: Prove Auth Works End-to-End

Wait for the deploy to complete, then work through these three invocations.

### Get a Token

The test user `workshopuser@example.com` is pre-provisioned in the Cognito User Pool:

```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "Token obtained successfully"
```

:::alert{header="Token expiry" type="info"}
Tokens are valid for 60 minutes. If you see an auth error in a later step, re-run this block.
:::

### Authenticated Invoke (should succeed)

```bash
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_ID --bearer-token "$TOKEN" --stream
```

You'll see the agent call `check_portfolio_risk` through the Gateway MCP client. Both the Runtime and the Gateway validated the JWT before the Lambda was ever reached.

### Unauthenticated Invoke (should fail)

```bash
agentcore invoke "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_ID --stream
```

You'll see a `401 Unauthorized` response. The Runtime rejected the request before it reached your agent code — no unauthenticated call ever touches the Lambda. Both Runtime and Gateway now reject anonymous callers independently.

---

## Step 9: Execute a Trade — Remember This One

```bash
agentcore invoke "Buy 5000 shares of MSFT at limit price for a large client position" \
  --session-id $SESSION_ID --bearer-token "$TOKEN" --stream
```

The agent calls `execute_trade` through the Gateway and the trade goes through.

:::alert{header="This trade just went through — note that" type="warning"}
An authenticated caller asked to buy 5,000 shares of MSFT and the agent executed it without hesitation. Authentication answered **who can call** — nothing yet says **what they may do**. There is no quantity limit, no restricted-ticker check, no role-based approval gate. Any authenticated user could run this same prompt.

In Lab 3 you'll attach a Cedar policy engine to the Gateway and run this exact prompt again. Watch what happens.
:::

---

## Architecture

:::code{language=bash showCopyAction=false}
Client (JWT token from Cognito)
    ↓ validated at Runtime
AgentCore Runtime (PortfolioAdvisor)
    ├── get_stock_analysis()       ← local tools, always available
    ├── get_compliance_rules()     ← local tools, always available
    └── MCP Client (forwards JWT)
              ↓ validated at Gateway
    AgentCore Gateway (my-gateway)
         ├── PortfolioRiskCheck → Lambda: workshop-check-portfolio-risk
         └── ExecuteTrade       → Lambda: workshop-execute-trade
:::

## What Just Happened?

You created a Gateway with JWT authentication enabled from day one, registered two Lambda tools, patched the Runtime config to require the same authorizer, made the one code edit that threads the caller's token through the agent, and deployed once. The token flow is:

```
User → Cognito (authenticate) → JWT access token
JWT → Runtime (validate: signature + expiry + audience + issuer)
JWT → agent code (extract user_id, hold auth_header)
JWT → Gateway MCP call (forwarded in Authorization header)
JWT → Gateway (validate again, independently)
Gateway → Lambda (user identity available if needed)
```

---

## Best Practices: Gateway Security Essentials

:::alert{header="Best Practice" type="info"}
**Centralize tools behind a Gateway and secure every layer independently.**
:::

**Why Gateway over direct Lambda integration:**
- **Discovery** — Agents find tools via MCP, not hardcoded imports
- **Governance** — Attach Cedar policies at the Gateway without touching agent or Lambda code (Lab 3)
- **Reuse** — Multiple agents share the same Gateway tools; update Lambda code without redeploying agents
- **Audit** — Every tool call is logged at the Gateway boundary with full request/response context

**Defense in depth:**

- **Both layers need auth.** Runtime and Gateway are independent HTTPS endpoints. Securing only the Runtime leaves the Gateway URL discoverable and directly callable — bypassing your agent entirely. Each layer must reject unauthorized requests on its own.
- **Use `allowedClients` for least privilege.** Issue separate Cognito app clients for users, pipelines, and other agents. List only the ones that need access. A compromised credential then affects only that one client.
- **Never embed tokens.** JWT tokens are credentials. Read the token from request context per invocation, forward it, and treat it as ephemeral. Do not log it, store it in environment variables, or include it in system prompts.
- **Cognito rotates signing keys automatically.** AgentCore fetches public keys from the OIDC `discoveryUrl` on each validation — key rotation requires no manual action.

---

### What's Next

→ Next: [Lab 3: Govern Agent Actions with Cedar Policies](../50-lab4-governance/)

*(Optional: [Enterprise Tool Registry](../35-lab2b-tool-registry/) (self-paced) — tool approval workflow, security review, MCP server registration. ~20 min. Available anytime after this lab.)*
