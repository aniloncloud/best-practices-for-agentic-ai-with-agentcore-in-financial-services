---
title: "Lab 2: Connect Tools with Gateway + JWT Auth"
weight: 30
---

**⏱️ ~18 minutes (one deploy, ~2–3 min — you'll read through it)**

## Overview

Your harness answers from its system prompt today, but real-world agents need access to existing business logic — Lambda functions, REST APIs, databases. Rather than embedding those connections in agent code, AgentCore Gateway provides a centralized, governed control plane for tool access, and you attach it to the harness **by reference**.

In this lab you'll do three things in one deploy:

1. Create a Gateway **with JWT authentication from the start** — no unauthenticated window
2. Register two Lambda tools (portfolio risk check and trade execution) and attach the Gateway to the harness
3. Secure the harness with inbound JWT, and configure outbound M2M auth so the harness authenticates to the Gateway — **with zero agent code**, because the harness fetches and exchanges tokens for you

You'll end with a 5,000-share trade that goes through. Remember it — Lab 3 will stop it.

### What You're Building

:::code{language=bash showCopyAction=false}
End user (Cognito web-client JWT)
    ↓ Bearer token  —  inbound auth: who can call the agent
AgentCore Harness (PortfolioAdvisor)  ← JWT required  ← THIS LAB
    │   model + system prompt (reference data)
    └── Gateway tool  —  outbound auth: harness fetches an M2M token
              ↓            from a credential provider (no forwarding code)
    AgentCore Gateway (my-gateway)    ← validates M2M token  ← THIS LAB
         ├── PortfolioRiskCheck → Lambda: workshop-check-portfolio-risk
         └── ExecuteTrade       → Lambda: workshop-execute-trade
:::

Both the harness and the Gateway independently require a valid token: an end-user JWT to call the agent (inbound), and an M2M token that the harness fetches automatically to call the Gateway (outbound). No token-handling code anywhere.

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
export HARNESS_EXEC_ROLE_ARN=$(aws ssm get-parameter --name $P/harness_execution_role_arn --query 'Parameter.Value' --output text)
export GATEWAY_ROLE_ARN=$(aws ssm get-parameter --name $P/gateway_service_role_arn --query 'Parameter.Value' --output text)
export GATEWAY_M2M_CRED_ARN=$(aws ssm get-parameter --name $P/gateway_m2m_credential_provider_arn --query 'Parameter.Value' --output text)
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
agentcore add gateway --name my-gateway \
  --role-arn $GATEWAY_ROLE_ARN \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID \
  --allowed-scopes $COGNITO_SCOPE
```

You should see:

:::code{language=bash showCopyAction=false}
Added gateway 'my-gateway'
:::

`--role-arn` is the **pre-provisioned** gateway service role — it already has permission to invoke the Lambda targets *and* to call the policy engine you attach in Lab 3, so the governance step works without any manual IAM fix. `--discovery-url` tells the Gateway where to fetch Cognito's signing keys. The Gateway is reached by the **harness using a machine-to-machine (M2M) token**, so `--allowed-clients` is the M2M app client and `--allowed-scopes` is the gateway scope.

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

## Step 4: Your Outbound Credential Provider (pre-provisioned)

The harness calls the Gateway as a machine, using a Cognito M2M (client-credentials) token. The OAuth2 **credential provider** for this is **pre-provisioned** in AgentCore Identity — the client secret lives in the Token Vault, never in your config or code. Its ARN is already loaded as `$GATEWAY_M2M_CRED_ARN`:

```bash
echo "Credential provider: $GATEWAY_M2M_CRED_ARN"
```

You'll reference this ARN when you attach the Gateway tool in the next step. (Setup-time command, shown for reference — you don't run it: `agentcore add credential --name my-gateway-m2m --type oauth --discovery-url ... --client-id ... --client-secret ...`.)

---

## Step 5: Attach the Gateway to the Harness (with outbound M2M auth)

The harness gains the Gateway's tools by referencing the gateway — no MCP client code, no wiring. The `outbound-auth` flags tell the harness to authenticate to the Gateway with the pre-provisioned M2M credential:

```bash
agentcore add tool --harness PortfolioAdvisor \
  --type agentcore_gateway \
  --name my-gateway \
  --gateway my-gateway \
  --outbound-auth oauth \
  --credential-arn $GATEWAY_M2M_CRED_ARN \
  --scopes $COGNITO_SCOPE
```

Confirm it landed in `harness.json`:

```bash
cat app/PortfolioAdvisor/harness.json
```

You'll see a `tools` entry of type `agentcore_gateway` whose `config.agentCoreGateway` has the `gatewayArn` plus an `outboundAuth.oauth` block (`providerArn`, `scopes`, `grantType: CLIENT_CREDENTIALS`). On every tool call the harness fetches an M2M token from the credential provider and presents it to the Gateway.

---

## Step 6: Secure the Harness Inbound (who can call the agent)

Now configure inbound JWT so only authenticated **end users** (the Cognito web client) can invoke the harness. This is the harness `authorizerConfiguration` — a configuration change, no agent code:

```bash
python3 - <<'EOF'
import json, os
p = "app/PortfolioAdvisor/harness.json"
cfg = json.load(open(p))
cfg["authorizerConfiguration"] = {
    "customJWTAuthorizer": {
        "discoveryUrl": os.environ["COGNITO_DISCOVERY_URL"],
        "allowedClients": [os.environ["COGNITO_WEB_CLIENT_ID"]],
    }
}
json.dump(cfg, open(p, "w"), indent=2)
print("Harness inbound JWT configured (web client = end users).")
EOF
```

::::alert{header="No code edit — the harness handles token exchange" type="info"}
In a hand-written agent, this is where you'd add `import jwt`, an `extract_user_id()` helper, and code to fetch an M2M token and attach it to every Gateway call. **On the harness, you write none of it.** The `outboundAuth.oauth` config (Step 5) tells the harness to fetch and refresh the M2M token from the Token Vault automatically. Across this entire live session there are **zero agent code edits** — production hardening is configuration, not code.
::::

:::alert{header="Two tokens, two jobs" type="info"}
**Inbound** (this step): an end-user web-client JWT controls *who can call the agent*. **Outbound** (Step 5): the harness presents an *M2M* token to the Gateway — that is the identity the Gateway validates and that Cedar evaluates in Lab 3. The end-user JWT is not forwarded to the Gateway in this pattern. Threading the *end-user* identity all the way to tools is a separate on-behalf-of (OBO) flow — see the self-paced [OAuth Token Flows](../40-lab3-security/) lab.
:::

---

## Step 7: Deploy

Validate configuration first, then deploy:

```bash
agentcore validate
```

```bash
agentcore deploy -y -v
```

This is your **second deploy** (first was Lab 1) and the last one until Lab 3. While it runs (~2–3 min), work through Step 8.

---

## Step 8: While This Deploys — Credential Patterns and Tool Schemas

::::expand{header="Read while the deploy runs (click to open)"}

### Where credentials live

Notice what you did *not* do: you didn't paste a secret into the agent, and you didn't write code to fetch or attach tokens. Three credential patterns exist; this lab uses M2M outbound — the harness fetches the Gateway token from a credential provider for you.

| Pattern | How It Works | Best For |
|---------|-------------|----------|
| **IAM Service Credential** | Caller signs requests with SigV4 | Service-to-service; no user context needed |
| **M2M outbound (this lab)** | Harness fetches a client-credentials token from a credential provider to call the Gateway | Agent→gateway/tool auth without per-user scoping |
| **Workload Identity (OBO)** | A user token is exchanged for a scoped workload token so the end-user identity reaches the tool | Per-user authorization/audit at the tool |

The pattern to remember: credentials are injected **at the edge** (Gateway / Identity), never held in the agent process. A secret the agent never holds can't leak through a log line, a traceback, or a prompt-injection attempt. That's why "add auth" was a config change, not a code change.

> **Deep dive (self-paced):** credential patterns and on-behalf-of token exchange are covered in [OAuth Token Flows](../40-lab3-security/) and the AgentCore optimization companion guide.

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

> **Scaling note:** Once a Gateway catalog grows past ~20 tools, passing every schema to the model on every turn wastes tokens and hurts tool-selection accuracy. Gateway's built-in semantic tool search returns only the relevant tools for a query. With two tools you don't need it yet — but it's the right lever as the catalog grows.

::::

---

## Step 9: Prove Auth Works End-to-End

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

agentcore invoke --harness PortfolioAdvisor "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_ID --bearer-token "$TOKEN"
```

You'll see the agent call `check_portfolio_risk` through the Gateway. Both the harness and the Gateway validated the JWT before the Lambda was ever reached.

### Unauthenticated Invoke (should fail)

```bash
agentcore invoke --harness PortfolioAdvisor "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_ID
```

You'll see a `401 Unauthorized` response. The harness rejected the request before it reached the agent loop — no unauthenticated call ever touches the Lambda. Both the harness and Gateway now reject anonymous callers independently.

---

## Step 10: Execute a Trade — Remember This One

```bash
agentcore invoke --harness PortfolioAdvisor \
  "Buy 5000 shares of MSFT at limit price for a large client position" \
  --session-id $SESSION_ID --bearer-token "$TOKEN"
```

The agent calls `execute_trade` through the Gateway and the trade goes through.

:::alert{header="This trade just went through — note that" type="warning"}
An authenticated caller asked to buy 5,000 shares of MSFT and the agent executed it without hesitation. Authentication answered **who can call** — nothing yet says **what they may do**. There is no quantity limit, no restricted-ticker check, no role-based approval gate. Any authenticated user could run this same prompt.

In Lab 3 you'll attach a Cedar policy engine to the Gateway and run this exact prompt again. Watch what happens.
:::

---

## What Just Happened?

You created a Gateway with JWT authentication enabled from day one, registered two Lambda tools, registered an M2M credential provider, attached the Gateway to the harness with outbound M2M auth, configured inbound JWT on the harness, and deployed once. Critically, you wrote **no agent code** — the harness fetches and exchanges tokens for you. The token flow is:

```
End user → Cognito web client (authenticate) → JWT access token
JWT → Harness (validates inbound: signature + expiry + audience + issuer)
Agent decides to call a tool → Harness fetches an M2M token from the credential provider
M2M token → Gateway (validates inbound, independently)
Gateway → Lambda (via its IAM role)
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

- **Both layers need auth.** The harness and Gateway are independent HTTPS endpoints. Securing only the harness leaves the Gateway URL discoverable and directly callable — bypassing your agent entirely. Each layer must reject unauthorized requests on its own.
- **Use `allowedClients` for least privilege.** Issue separate Cognito app clients for users, pipelines, and other agents. List only the ones that need access. A compromised credential then affects only that one client.
- **Never embed tokens.** With the harness, you don't hold them at all — Identity manages credential injection at the edge. Don't log tokens, store them in environment variables, or include them in system prompts.
- **Restrict tools with `allowedTools`.** The harness ships with built-in `shell` and `file_operations` tools. In a regulated workload, scope the agent to only the tools it needs (the Gateway tools) so it can't run arbitrary shell commands.
- **Cognito rotates signing keys automatically.** AgentCore fetches public keys from the OIDC `discoveryUrl` on each validation — key rotation requires no manual action.

---

### What's Next

→ Next: [Lab 3: Govern Agent Actions with Cedar Policies](../50-lab4-governance/)

*(Optional: [Enterprise Tool Registry](../35-lab2b-tool-registry/) (self-paced) — tool approval workflow, security review, MCP server registration. ~20 min. Available after the live session.)*
