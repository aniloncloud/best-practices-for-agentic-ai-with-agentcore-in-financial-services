---
title: "Optional Lab 2B: Enterprise Tool Registry"
weight: 35
---

**⏱️ Estimated time: ~20 minutes**

:::alert{header="Optional Lab" type="info"}
This lab is optional. It can be done anytime after Lab 2 (Gateway). The core path continues directly from Lab 2 to Lab 3 (Security). No subsequent labs depend on the MarketData target added here.
:::

## Overview

In Lab 2, you registered Lambda functions as Gateway tools. But in an enterprise, tools don't just appear — they go through an approval process. A team deploys a new Market Data MCP server. Before any agent can use it, the platform team must review the tool schemas, verify the security posture, and explicitly approve it by adding it to the Gateway.

**AgentCore Gateway IS your enterprise tool registry.** Tools only exist for agents once they're registered as Gateway targets. Adding a target is the approval step — the act that makes a tool discoverable to agents.

### What You'll Learn

- List and inspect tools currently registered in the Gateway
- Review a candidate MCP server's tool schemas for security
- Add an MCP server as a Gateway target (the "approval" step)
- Verify the agent discovers and uses the new tool automatically
- Understand semantic search for tool discovery

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Gateway as Registry** | The Gateway is the single source of truth for which tools agents can access |
| **Target = Approved Tool** | Adding a target is the approval. Removing it revokes access. |
| **Synchronization** | For MCP server targets, the Gateway indexes all tools the server exposes |
| **Semantic Search** | Agents discover tools by intent ("get stock price") not just by exact name |
| **Default Deny** | Tools not in the Gateway don't exist to the agent — zero access by default |

## Step 1: Inspect the Current Registry

Your Gateway from Lab 2 already has two approved tools. Let's see what's registered:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore status --type gateway
```
:::
:::tab{label="Windows"}
```powershell
agentcore status --type gateway

```
:::
::::

You should see `my-gateway` with two targets:
- **PortfolioRiskCheck** — `check_portfolio_risk` (Lambda)
- **ExecuteTrade** — `execute_trade` (Lambda)

These were "approved" when you added them in Lab 2. Any tool NOT registered here is invisible to the agent — it simply cannot be called, even if the MCP server is running.

## Step 2: Discover the Candidate Tool

A market data team has deployed an MCP server that provides real-time quotes, historical prices, and sector performance data. It's running — but it's not yet approved for your agent to use.

Retrieve the MCP server endpoint (pre-provisioned):

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
MARKET_DATA_ENDPOINT=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/market_data_mcp_endpoint \
  --query 'Parameter.Value' --output text)

echo "Market Data MCP Server: $MARKET_DATA_ENDPOINT"
```
:::
:::tab{label="Windows"}
```powershell
$MARKET_DATA_ENDPOINT = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/market_data_mcp_endpoint `
  --query 'Parameter.Value' --output text

Write-Host "Market Data MCP Server: $MARKET_DATA_ENDPOINT"

```
:::
::::

## Step 3: Security Review

Before approving a tool for agent access, the platform team reviews:

### Review Checklist

| Check | What to Verify | Status |
|-------|---------------|--------|
| **Tool schemas** | Input parameters are typed and bounded. No unbounded `string` inputs that could accept injected payloads. | ⬜ |
| **Output surface** | Tool responses don't leak credentials, internal IPs, or PII in error messages. | ⬜ |
| **Authentication** | Endpoint requires authentication (OAuth, API key, or IAM). Never approve unauthenticated tools for production. | ⬜ |
| **Network posture** | Endpoint is in a trusted network (VPC, private subnet) or accessible only via PrivateLink. | ⬜ |
| **MCP version** | Server supports MCP protocol version 2025-06-18 or 2025-03-26. | ⬜ |
| **Data classification** | Understand what data the tool returns. Is it PII? Restricted? Market-sensitive? | ⬜ |

### Review the Tool Schemas

The market data MCP server exposes three tools. Review their schemas:

:::code{language=json showCopyAction=false}
{
  "tools": [
    {
      "name": "get_market_quote",
      "description": "Get real-time market quote for a ticker symbol including bid/ask, volume, and last trade price",
      "inputSchema": {
        "type": "object",
        "properties": {
          "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., AAPL, MSFT). Must be a valid NYSE/NASDAQ listed symbol."
          }
        },
        "required": ["ticker"]
      }
    },
    {
      "name": "get_historical_prices",
      "description": "Get historical daily closing prices for a ticker over a specified period",
      "inputSchema": {
        "type": "object",
        "properties": {
          "ticker": {
            "type": "string",
            "description": "Stock ticker symbol"
          },
          "period": {
            "type": "string",
            "description": "Time period: '1W' (1 week), '1M' (1 month), '3M' (3 months), '1Y' (1 year)"
          }
        },
        "required": ["ticker", "period"]
      }
    },
    {
      "name": "get_sector_performance",
      "description": "Get performance metrics for a market sector including top/bottom performers and sector-wide indicators",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sector": {
            "type": "string",
            "description": "Market sector: 'Technology', 'Financials', 'Healthcare', 'Energy', 'Consumer Discretionary'"
          }
        },
        "required": ["sector"]
      }
    }
  ]
}
:::

### Security Assessment

✅ **Input parameters are typed and bounded** — `ticker` is a string with format guidance, `period` is constrained to known values, `sector` is one of five options.

✅ **Required fields specified** — No optional parameters that could be omitted and cause unexpected behavior.

✅ **Descriptions are specific** — Each tool clearly states what it does and what it returns. This helps the agent select the right tool (measurable via ToolSelectionAccuracy in Lab 5).

:::alert{header="Security Review Finding" type="info"}
In production, you would also verify:
- The `period` and `sector` parameters have server-side validation (don't trust client input)
- Error responses don't leak internal state
- The endpoint has rate limiting to prevent abuse
- Access logs are enabled on the MCP server
:::

## Step 4: Approve the Tool (Add to Gateway)

With the review complete, add the MCP server as a Gateway target — this is the approval:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway-target \
  --type mcp-server \
  --name MarketData \
  --endpoint $MARKET_DATA_ENDPOINT \
  --gateway my-gateway
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway-target `
  --type mcp-server `
  --name MarketData `
  --endpoint $MARKET_DATA_ENDPOINT `
  --gateway my-gateway

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added gateway target 'MarketData'
:::

### What Happens on Add

When you add an MCP server target, the Gateway:

1. **Connects** to the MCP server endpoint
2. **Synchronizes** — calls `tools/list` to discover all tools the server exposes
3. **Indexes** the tool schemas for semantic search
4. **Makes tools available** — agents can now discover and call them

This synchronization is automatic on creation. If the upstream MCP server adds new tools later, remove and re-add the target to trigger a fresh synchronization, or use the AWS API `SynchronizeGatewayTargets` directly.

## Step 5: Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

## Step 6: Verify Tool Discovery

The agent should now discover and use the market data tools automatically — no code changes needed:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_REG=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Test the new market data tool
agentcore invoke "What's the current market quote for AAPL? Include bid/ask and volume." \
  --session-id $SESSION_REG --stream

# Test historical data
agentcore invoke "Show me MSFT's historical prices for the last 3 months" \
  --session-id $SESSION_REG --stream

# Test sector analysis
agentcore invoke "How is the Technology sector performing?" \
  --session-id $SESSION_REG --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_REG = [guid]::NewGuid().ToString()

# Test the new market data tool
agentcore invoke "What's the current market quote for AAPL? Include bid/ask and volume." `
  --session-id $SESSION_REG --stream

# Test historical data
agentcore invoke "Show me MSFT's historical prices for the last 3 months" `
  --session-id $SESSION_REG --stream

# Test sector analysis
agentcore invoke "How is the Technology sector performing?" `
  --session-id $SESSION_REG --stream

```
:::
::::

The agent now has five tools available:
- `get_stock_analysis` (local)
- `get_compliance_rules` (local)
- `check_portfolio_risk` (Gateway → Lambda)
- `execute_trade` (Gateway → Lambda)
- `get_market_quote`, `get_historical_prices`, `get_sector_performance` (Gateway → MCP Server) ← **newly approved**

### Verify in Traces

:::code{language=bash}
agentcore logs --runtime PortfolioAdvisor --since 5m
:::

In the trace, you'll see the agent calling the new `MarketData___get_market_quote` tool through the Gateway MCP client — the triple-underscore prefix shows it's routed through the MarketData target.

## Step 7: Revoke Access (Optional Demo)

To demonstrate the "remove = revoke" pattern:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
# Remove the target — immediately revokes agent access
agentcore remove gateway-target --name MarketData --gateway my-gateway

# Redeploy
agentcore deploy -y -v

# Try to use it — the agent will not have the tool available
agentcore invoke "What's the market quote for AAPL?" \
  --session-id $(python3 -c 'import uuid; print(uuid.uuid4())') --stream
```
:::
:::tab{label="Windows"}
```powershell
# Remove the target — immediately revokes agent access
agentcore remove gateway-target --name MarketData --gateway my-gateway

# Redeploy
agentcore deploy -y -v

# Try to use it — the agent will not have the tool available
agentcore invoke "What's the market quote for AAPL?" `
  --session-id ([guid]::NewGuid().ToString()) --stream

```
:::
::::

The agent will fall back to `get_stock_analysis` (which has basic price data) or tell the user it doesn't have real-time market data. The tool is gone from the registry — it no longer exists for the agent.

:::alert{header="Note about Lab 3" type="info"}
Lab 3 (Security) removes `my-gateway` and creates `my-gateway-secure`. If you want MarketData tools available after Lab 3, you'll need to re-add the MarketData target to the new secured gateway after completing Lab 3:
```bash
agentcore add gateway-target \
  --type mcp-server \
  --name MarketData \
  --endpoint $MARKET_DATA_ENDPOINT \
  --gateway my-gateway-secure
agentcore deploy -y -v
```
This is optional — the core labs do not depend on the MarketData target.
:::

## Architecture

:::code{language=bash showCopyAction=false}
AgentCore Gateway (my-gateway) — Enterprise Tool Registry
    ├── PortfolioRiskCheck (Lambda)     [Approved: Lab 2]
    ├── ExecuteTrade (Lambda)           [Approved: Lab 2]
    └── MarketData (MCP Server)         [Approved: Lab 2B — this lab]
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance
                    ↑
        Gateway synchronizes tool schemas from MCP server
        Agent discovers tools via MCP client (semantic search)
:::

## What Just Happened?

You implemented an enterprise tool approval workflow:

1. **Inspected the registry** — Saw what's currently approved (2 Lambda targets from Lab 2)
2. **Reviewed a candidate** — Checked tool schemas, input types, security posture
3. **Approved** — Added the MCP server as a Gateway target (the approval act)
4. **Verified** — Agent automatically discovered and used the new tools
5. **(Optional) Revoked** — Removed the target, instantly revoking agent access

---

## Best Practices: Enterprise Tool Governance

:::alert{header="Best Practice" type="info"}
**The Gateway is your enterprise tool registry. A tool not in the Gateway doesn't exist to agents — that's your default-deny posture.**
:::

**The approval workflow:**

```
Team deploys MCP server / Lambda / API
    ↓
Platform team reviews (security checklist above)
    ↓
Platform team adds as Gateway target (agentcore add gateway-target)
    ↓
Gateway synchronizes and indexes tools
    ↓
Agents discover tools automatically
    ↓
Policy Engine governs WHO can call them (Lab 4)
```

**Why Gateway-as-registry works for FSI:**

| Requirement | How Gateway Satisfies It |
|---|---|
| **Audit trail** | Every tool registration, removal, and invocation is logged |
| **Least privilege** | Only approved tools are accessible. Default deny. |
| **Separation of duties** | Platform team approves tools; agent team writes logic; policy team writes Cedar rules |
| **Emergency revocation** | Remove the target — instant revocation, no code deploy needed |
| **Version control** | Target configurations live in `agentcore.json` — git-trackable approvals |

**Security review patterns:**

- **Schema validation** — Verify all input parameters are typed. Reject tools with untyped `any` or unbounded string inputs.
- **Output classification** — Understand what data the tool returns. If it returns PII, the agent's responses may contain PII — does your data handling policy allow this?
- **Authentication posture** — Never approve unauthenticated tools for production Gateways. Require OAuth, API key, or IAM on all outbound connections.
- **Network path** — For FSI, prefer tools deployed in the same VPC or accessible via PrivateLink. Public internet tools carry data residency risk.
- **Rate limiting** — Verify the tool backend has rate limits. An agent can generate high tool call volumes — without limits, a malfunctioning agent can overwhelm a backend.

**Semantic search for tool discovery:**

When `searchType: SEMANTIC` is enabled on the Gateway, agents can discover tools by intent rather than exact name. The query "how much is Apple stock worth" will match `get_market_quote` even though the words don't overlap. This is powerful but requires high-quality tool descriptions — invest in the `description` field during the review step.

**Multi-team tool sharing:**

Multiple agents can share the same Gateway. Team A's agent and Team B's agent both discover tools from the same registry. Combined with Cedar policies (Lab 4), you can control which agent can call which tools — enabling tool sharing without over-permitting access.

---

### What's Next

In Lab 3, you'll secure both Runtime and Gateway with Cognito JWT authentication — so only authorized users can invoke your agent and its tools.

→ Next: [Lab 3: Secure with JWT Authentication](../40-lab3-security/)
