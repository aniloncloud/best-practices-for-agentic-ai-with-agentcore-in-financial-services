---
title: "Lab 2: Centralize Tools with Gateway"
weight: 32
---

**⏱️ Estimated time: ~25 minutes**

## Overview

Your agent has local tools (stock analysis, compliance rules), but real-world agents need access to existing business logic — Lambda functions, REST APIs, databases. Rather than embedding these connections directly in agent code, AgentCore Gateway provides a centralized control plane for tool access.

In this lab, you'll create a Gateway, register two Lambda functions as tools (portfolio risk check and trade execution), and connect your agent to them via the MCP protocol.

### What You'll Learn

- Create an AgentCore Gateway and register Lambda function tools
- Connect your agent to Gateway tools via the MCP client
- Understand two credential patterns: JWT passthrough vs IAM service credentials
- Test tool invocation end-to-end

### Two Credential Patterns for Gateway

| Pattern | How It Works | When to Use |
|---------|-------------|-------------|
| **JWT Passthrough** | Agent forwards user's Cognito token to Gateway | User identity needed for per-user policies |
| **IAM Service Credential** | Agent's IAM execution role authenticates to Gateway | Service-to-service, no user context needed |

:::alert{header="This Lab Uses IAM Mode" type="info"}
We start with IAM-based Gateway access (simpler). In Lab 3, you'll add JWT authentication to both Runtime and Gateway for user-level identity.
:::

### What You're Building

:::code{language=bash showCopyAction=false}
agentcore invoke ──▶ AgentCore Runtime (PortfolioAdvisor)
                         │
                         │ MCP Client
                         ▼
              ┌─────────────────────────────────────┐
              │   AgentCore Gateway  ← THIS LAB     │
              │                                     │
              │   ├── PortfolioRiskCheck → Lambda    │
              │   └── ExecuteTrade → Lambda          │
              └─────────────────────────────────────┘
:::

## Step 1: Create a Gateway

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway \
  --name my-gateway \
  --runtimes PortfolioAdvisor
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway `
  --name my-gateway `
  --runtimes PortfolioAdvisor

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added gateway 'my-gateway'
:::

## Step 2: Add the Portfolio Risk Tool

Retrieve the Lambda ARN and add it as a Gateway target:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
RISK_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn \
  --query 'Parameter.Value' --output text)

agentcore add gateway-target \
  --type lambda-function-arn \
  --name PortfolioRiskCheck \
  --lambda-arn $RISK_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json \
  --gateway my-gateway
```
:::
:::tab{label="Windows"}
```powershell
$RISK_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn `
  --query 'Parameter.Value' --output text

agentcore add gateway-target `
  --type lambda-function-arn `
  --name PortfolioRiskCheck `
  --lambda-arn $RISK_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json `
  --gateway my-gateway

```
:::
::::

## Step 3: Add the Trade Execution Tool

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TRADE_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/execute_trade_lambda_arn \
  --query 'Parameter.Value' --output text)

agentcore add gateway-target \
  --type lambda-function-arn \
  --name ExecuteTrade \
  --lambda-arn $TRADE_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/trade_schema.json \
  --gateway my-gateway
```
:::
:::tab{label="Windows"}
```powershell
$TRADE_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/execute_trade_lambda_arn `
  --query 'Parameter.Value' --output text

agentcore add gateway-target `
  --type lambda-function-arn `
  --name ExecuteTrade `
  --lambda-arn $TRADE_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/trade_schema.json `
  --gateway my-gateway

```
:::
::::

## Step 4: How the Agent Connects to the Gateway (no code change needed)

Your agent is **already wired to use Gateway tools** — there's nothing to edit in `main.py`. Open `app/PortfolioAdvisor/main.py` and look at `get_or_create_agent`:

```python
def get_or_create_agent(session_id=None, user_id=None, auth_header=""):
    tools = [get_stock_analysis, get_compliance_rules]
    # Gateway tools are added automatically once a Gateway exists.
    gateway_client = get_gateway_mcp_client(auth_header)
    if gateway_client:
        tools.append(gateway_client)
    return Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
```

`get_gateway_mcp_client()` (in `mcp_client/client.py`) reads the Gateway URL from the `AGENTCORE_GATEWAY_MY_GATEWAY_URL` environment variable. In Lab 1 that variable didn't exist, so the function returned `None` and the agent ran with only its local tools. Now that you've added a Gateway, the next deploy injects that variable automatically — so `get_gateway_mcp_client()` returns a live MCP client and the Gateway's tools (`check_portfolio_risk`, `execute_trade`) become available to the agent.

:::alert{header="Why no edit?" type="info"}
The agent code is intentionally environment-driven: it picks up Gateway tools when a Gateway is present and falls back to local tools when it isn't. This keeps the agent code stable across every lab — you change configuration (`agentcore.json` and `agentcore add ...`), not application code.
:::

## Step 5: Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

This deploys the Gateway with both tool targets and updates your Runtime with the MCP client enabled. The Gateway URL is automatically injected as an environment variable (`AGENTCORE_GATEWAY_MY_GATEWAY_URL`).

## Step 6: Test Gateway Tools

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Test portfolio risk check
agentcore invoke "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_ID --stream

# Test trade execution
agentcore invoke "Execute a trade: buy 100 shares of AAPL at market price for rebalancing" \
  --session-id $SESSION_ID --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_ID = [guid]::NewGuid().ToString()

# Test portfolio risk check
agentcore invoke "Check the portfolio risk for PORT-001" `
  --session-id $SESSION_ID --stream

# Test trade execution
agentcore invoke "Execute a trade: buy 100 shares of AAPL at market price for rebalancing" `
  --session-id $SESSION_ID --stream

```
:::
::::

The agent should use the Gateway tools — you'll see it call `check_portfolio_risk` and `execute_trade` through the MCP client.

## Step 7: Verify in CloudWatch

Check your traces to see the Gateway tool calls:

:::code{language=bash}
agentcore logs --runtime PortfolioAdvisor --since 5m
:::

In the CloudWatch GenAI Observability dashboard, you'll see tool call spans showing the Gateway MCP client invoking the Lambda functions.

## Understanding the Credential Patterns

### Current Setup: IAM Service Credential

Right now, your agent uses its **IAM execution role** to authenticate to the Gateway. The Runtime's role has permission to invoke the Gateway — no user token is involved.

```
Agent (Runtime IAM role) → SigV4-signed request → Gateway → Lambda
```

This is the simplest pattern: the Gateway trusts the Runtime's IAM identity. However, it doesn't carry user identity — the Gateway can't tell which end-user triggered the request.

### Next Lab: JWT Passthrough

In Lab 3, you'll switch to JWT authentication where the **user's Cognito token** flows from Runtime to Gateway:

```
User (JWT) → Runtime (validates JWT) → forwards JWT → Gateway (validates JWT) → Lambda
```

This enables per-user policies (e.g., "user X can only trade stocks in their approved list") because the Gateway knows WHO is calling, not just WHICH service.

### Advanced: Workload Identity (On Behalf Of)

For complex multi-agent scenarios, AgentCore Identity provides a **workload token** pattern:

```
User JWT → Runtime → GetWorkloadAccessTokenForJWT() → Workload Token → Gateway
```

The workload token carries the user's provenance while being scoped to what the agent is authorized to do. This is useful when:
- An agent calls another agent's Gateway (cross-agent tool sharing)
- You need to exchange the user token for tokens to third-party APIs
- Audit logs need to trace back to the originating user across multiple hops

## Architecture

:::code{language=bash showCopyAction=false}
CLI (agentcore invoke)
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── MCP Client → AgentCore Gateway (my-gateway, IAM auth)
                          ├── PortfolioRiskCheck → Lambda: workshop-check-portfolio-risk
                          └── ExecuteTrade → Lambda: workshop-execute-trade
:::

## What Just Happened?

You centralized tool access through AgentCore Gateway:

1. **Created a Gateway** — A central control plane for tools
2. **Registered Lambda tools** — Existing functions exposed as MCP-discoverable tools without code changes
3. **Connected via MCP** — Your agent discovers tools automatically through the Gateway MCP client
4. **Tool schemas** — JSON Schema descriptions let the agent understand when and how to use each tool

The Lambda functions didn't change at all. The Gateway MCPified them — making existing business logic discoverable by any agent.

---

## Best Practices: Tool Centralization and Credential Patterns

:::alert{header="Best Practice" type="info"}
**Centralize tools behind a Gateway — don't embed integrations directly in agent code.**
:::

**Why Gateway over direct integration:**
- **Discovery** — Agents discover available tools via MCP, not hardcoded imports
- **Governance** — Add Cedar policies at the Gateway without changing agent code (Lab 4)
- **Reuse** — Multiple agents can share the same Gateway tools
- **Audit** — Every tool call is logged at the Gateway boundary with full request/response payloads
- **Versioning** — Update tool implementations (Lambda code) without redeploying agents

**Choosing a credential pattern:**

| Scenario | Pattern | Why |
|----------|---------|-----|
| Single-user agent, no per-user policies | IAM Service Credential | Simplest; no token management |
| Per-user authorization needed | JWT Passthrough | Gateway applies policies based on user identity |
| Multi-agent collaboration | Workload Identity (OBO) | Preserves user provenance across agent hops |
| Third-party API access | Workload Identity + Token Vault | Exchange user JWT for external OAuth tokens |

**Schema design matters:** Tool schemas are how the LLM decides when to use a tool. Poor descriptions lead to low tool selection accuracy (which you'll measure in Lab 5). Treat schemas like API documentation for an AI reader:

| Schema Field | Good Example | Bad Example | Why It Matters |
|---|---|---|---|
| `description` | "Check portfolio risk metrics for a given portfolio ID (e.g., PORT-001). Returns risk score, VaR, and concentration data." | "Portfolio risk tool" | The LLM needs to know WHEN to call this tool and WHAT it returns |
| `inputSchema.properties.portfolio_id.description` | "Portfolio identifier in format PORT-XXX. Must be an active portfolio." | "The ID" | Specific format guidance reduces invalid calls |
| `inputSchema.required` | `["portfolio_id"]` | (empty array) | Without required fields, the LLM may call the tool with missing params |

**Tool description anti-patterns:**
- Don't use the same words in multiple tools ("processes the request" on 5 tools)
- Don't omit return value descriptions — the LLM can't decide between tools if it doesn't know what each returns
- Don't use internal jargon unless it's in the system prompt — "run DTC check" means nothing to the model
- Do include examples of when NOT to use a tool ("Do not use for individual stock lookups — use get_stock_analysis instead")

**External tool integration patterns:** This workshop uses Lambda functions via Gateway. The same pattern works for:
- REST APIs (Gateway target type: `http-endpoint`)
- Databases (wrap in Lambda, expose via Gateway)
- Third-party services (OAuth via Identity, tool via Gateway)
- Other agents (Agent A's Gateway exposes tools that Agent B discovers via MCP)

---

### What's Next

→ Next: [Lab 3: Secure with JWT Authentication](../40-lab3-security/)

*(Optional: [Lab 2B: Enterprise Tool Registry](../35-lab2b-tool-registry/) — tool approval workflow, security review, MCP server registration. ~20 min. Can be done anytime after Lab 2.)*
