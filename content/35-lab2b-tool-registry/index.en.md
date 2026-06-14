---
title: "Optional Lab: Enterprise Tool Registry"
weight: 60
---

**⏱️ Estimated time: ~30 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Labs 1–2 (Deploy to AgentCore Runtime + Connect Tools with Gateway + JWT Auth)
:::

:::alert{header="Optional Lab — Requires Pre-provisioned Infrastructure" type="warning"}
This lab is optional and requires two resources pre-provisioned in your workshop account:

- **Market Data MCP server** (Part A) — SSM parameter `/app/portfolioadvisor/agentcore/market_data_mcp_endpoint`
- **AWS Agent Registry** (Part B) — SSM parameter `/app/portfolioadvisor/agentcore/tool_registry_id`

If either parameter does not exist, the corresponding part cannot be completed. The registry is pre-created (with **auto-approval off**) so you don't wait on provisioning and don't need `CreateRegistry`/`DeleteRegistry` permissions — you only exercise the record + governance workflow. The IAM actions your participant role needs for Part B are: `bedrock-agentcore-control:GetRegistry`, `CreateRegistryRecord`, `SubmitRegistryRecordForApproval`, `UpdateRegistryRecordStatus`, and `bedrock-agentcore:SearchRegistryRecords`.

The core path continues directly from Lab 2 to Lab 3 (Govern Agent Actions with Cedar Policies). No subsequent labs depend on the MarketData target added here.
:::

## Overview

In Lab 2, you registered Lambda functions as Gateway tools. But in an enterprise, tools don't just appear — they go through an approval process, and once approved they need to be **findable** by every team that might reuse them. A market data team deploys a new MCP server. Two things have to happen before it delivers value across the org:

1. **Make it callable** — approve it for an agent to use. That's the **Gateway**: a tool only exists for your agent once it's registered as a Gateway target.
2. **Make it discoverable and governed** — publish it to a central catalog so other teams can find it, with an approval workflow controlling what's published. That's **AWS Agent Registry**.

These are two complementary layers, and this lab does both:

:::code{language=bash showCopyAction=false}
                        ┌─────────────────────────────────────────────┐
   Part B (org-wide)    │   AWS Agent Registry                         │
   discovery + govern   │   catalog • approval workflow • hybrid search │
                        │   "which tools/MCP servers/agents exist?"     │
                        └─────────────────────────────────────────────┘
                        ┌─────────────────────────────────────────────┐
   Part A (per-agent)   │   AgentCore Gateway                           │
   connectivity + auth  │   targets = tools an agent can actually call  │
                        │   "what can THIS agent invoke right now?"     │
                        └─────────────────────────────────────────────┘
:::

:::alert{header="Two layers, two jobs" type="info"}
The **Gateway** is the connectivity/authorization layer — it makes a tool *callable* by a specific agent and routes the MCP traffic. The **AWS Agent Registry** is the discovery/governance layer — a private, org-wide catalog of MCP servers, tools, agents, and skills with a publish → approve → search workflow. Adding a Gateway target approves a tool *for your agent*; publishing a registry record makes it *discoverable and governable across the organization*.
:::

### What You'll Learn

**Part A — Approve a tool for your agent (Gateway)**
- List and inspect tools currently connected to the Gateway
- Review a candidate MCP server's tool schemas for security
- Add an MCP server as a Gateway target (approve it for your agent)
- Verify the agent discovers and uses the new tool automatically

**Part B — Publish & govern it org-wide (AWS Agent Registry)**
- Inspect the pre-provisioned AWS Agent Registry
- Publish the Market Data MCP server as a registry record
- Run the publish → submit → approve governance workflow
- Discover the tool with hybrid (semantic + keyword) search

### Key Concepts

| Concept | Layer | Description |
|---------|-------|-------------|
| **Gateway target = callable tool** | Gateway | A tool exists for an agent only when registered as a target. Remove it to revoke access. |
| **Synchronization** | Gateway | For MCP server targets, the Gateway indexes all tools the server exposes |
| **Registry** | Agent Registry | A private, org-wide catalog you create. Holds records for MCP servers, tools, agents, skills, custom resources. |
| **Registry record** | Agent Registry | Metadata describing one resource, validated against the MCP/agent protocol schema |
| **Approval workflow** | Agent Registry | Records go Draft → Pending approval → Approved. Only approved records are searchable. |
| **Hybrid search** | Agent Registry | Combines semantic understanding with keyword matching, for both humans and agents |
| **Default deny** | Both | A tool not approved (Gateway) and not published (Registry) is invisible — zero access, zero discovery |

### What You're Building

:::code{language=bash showCopyAction=false}
AWS Agent Registry (PortfolioAdvisorToolRegistry)        ← Part B: org-wide catalog
    └── MarketData (MCP record)   [Approved]
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance

AgentCore Gateway (my-gateway)                           ← Part A: agent connectivity
    ├── PortfolioRiskCheck (Lambda)     [Approved: Lab 2]
    ├── ExecuteTrade (Lambda)           [Approved: Lab 2]
    └── MarketData (MCP Server)         [Approved: THIS LAB]  ← NEW
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance
:::

---

# Part A — Approve a Tool for Your Agent (Gateway)

## Step 1: Inspect the Gateway (connectivity layer)

Your Gateway from Lab 2 already has two connected tools. Let's see what's registered:

:::code{language=bash}
agentcore status --type gateway
:::

You should see `my-gateway` with two targets:
- **PortfolioRiskCheck** — `check_portfolio_risk` (Lambda)
- **ExecuteTrade** — `execute_trade` (Lambda)

These were approved for your agent when you added them in Lab 2. Any tool NOT registered here is invisible to the agent — it simply cannot be called, even if the MCP server is running.

## Step 2: Discover the Candidate Tool

A market data team has deployed an MCP server that provides real-time quotes, historical prices, and sector performance data. It's running — but it's not yet approved for your agent to use.

Retrieve the MCP server endpoint (pre-provisioned):

:::code{language=bash}
MARKET_DATA_ENDPOINT=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/market_data_mcp_endpoint \
  --query 'Parameter.Value' --output text)

echo "Market Data MCP Server: $MARKET_DATA_ENDPOINT"
:::

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

✅ **Descriptions are specific** — Each tool clearly states what it does and what it returns. This helps the agent select the right tool (measurable via ToolSelectionAccuracy in the Evaluations lab).

:::alert{header="Security Review Finding" type="info"}
In production, you would also verify:
- The `period` and `sector` parameters have server-side validation (don't trust client input)
- Error responses don't leak internal state
- The endpoint has rate limiting to prevent abuse
- Access logs are enabled on the MCP server
:::

## Step 4: Approve the Tool for Your Agent (Add to Gateway)

With the review complete, add the MCP server as a Gateway target — this approves it for your agent to call:

:::code{language=bash}
agentcore add gateway-target \
  --type mcp-server \
  --name MarketData \
  --endpoint $MARKET_DATA_ENDPOINT \
  --gateway my-gateway
:::

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

:::code{language=bash}
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
:::

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

The tool is now **callable by your agent**. But other teams in your org still can't *discover* it — there's no central catalog telling them it exists. That's Part B.

---

# Part B — Publish & Govern It Org-Wide (AWS Agent Registry)

The Gateway made the Market Data MCP server callable by *your* agent. Now publish it to **AWS Agent Registry** so any team can discover it through a governed catalog — with an approval workflow that controls what becomes discoverable.

:::alert{header="Why a separate registry?" type="info"}
A Gateway is scoped to the agents that use it. As an organization scales to dozens of agents and MCP servers, teams can't find what already exists — so they rebuild it, creating duplication and drift. AWS Agent Registry is the org-wide answer: one searchable catalog of MCP servers, tools, agents, and skills, with publish/approve governance and hybrid search for both humans and agents. The Registry doesn't route traffic (that's still the Gateway) — it answers *"what exists, and is it approved to use?"*
:::

The Registry is accessed via the `bedrock-agentcore-control` (management) and `bedrock-agentcore` (search) APIs — there's no harness CLI verb for it, so Part B uses the AWS CLI directly.

## Step 7: Use the Pre-Provisioned Registry

Your workshop account already has a registry provisioned for you (registries take a minute or two to reach `READY`, so we pre-create them to save you the wait — and so your participant role doesn't need `CreateRegistry` permission). Retrieve its ID from SSM, the same way you fetched the Market Data endpoint:

:::code{language=bash}
REGISTRY_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/tool_registry_id \
  --query 'Parameter.Value' --output text)

echo "Registry: $REGISTRY_ID"
:::

Inspect it so you can see what a registry is — its name, status, and inbound auth type:

:::code{language=bash}
aws bedrock-agentcore-control get-registry \
  --registry-id "$REGISTRY_ID" \
  --query '{name:name, status:status, authType:authorizerType}'
:::

You should see `status: READY` with IAM authorization. The registry was also created with **auto-approval off**, which is what lets you walk the full governance workflow in Step 9.

:::alert{header="What was pre-created (and what wasn't)" type="info"}
Provisioning created an empty registry with this one command (run for you, not by you):

```bash
aws bedrock-agentcore-control create-registry \
  --name PortfolioAdvisorToolRegistry \
  --description "FSI tool & MCP server catalog for the PortfolioAdvisor org"
# auto-approval is left disabled so the submit → approve workflow applies
```

That's the *only* part that's pre-baked. The record, its submission, its approval, and search are all yours to run below — that's the governance workflow that's the point of this lab.
:::

## Step 8: Publish the Market Data MCP Server as a Record

A record is the catalog entry describing the resource. For an MCP server, the descriptor carries the server definition and its tool schemas, validated against the MCP protocol schema.

Build the descriptor (using Python to handle the nested JSON cleanly):

:::code{language=bash}
python3 - <<'PY' > /tmp/market-data-descriptors.json
import json

server = {
    "name": "market-data/mcp-server",
    "description": "Real-time market quotes, historical prices, and sector performance data",
    "version": "1.0.0",
}

tools = {
    "tools": [
        {
            "name": "get_market_quote",
            "description": "Get real-time market quote for a ticker symbol including bid/ask, volume, and last trade price",
            "inputSchema": {
                "type": "object",
                "properties": {"ticker": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, MSFT)"}},
                "required": ["ticker"],
            },
        },
        {
            "name": "get_historical_prices",
            "description": "Get historical daily closing prices for a ticker over a specified period",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "period": {"type": "string", "description": "1W, 1M, 3M, or 1Y"},
                },
                "required": ["ticker", "period"],
            },
        },
        {
            "name": "get_sector_performance",
            "description": "Get performance metrics for a market sector including top/bottom performers",
            "inputSchema": {
                "type": "object",
                "properties": {"sector": {"type": "string", "description": "Technology, Financials, Healthcare, Energy, or Consumer Discretionary"}},
                "required": ["sector"],
            },
        },
    ]
}

descriptors = {
    "mcp": {
        "server": {"schemaVersion": "2025-12-11", "inlineContent": json.dumps(server)},
        "tools": {"protocolVersion": "2024-11-05", "inlineContent": json.dumps(tools)},
    }
}

print(json.dumps(descriptors))
PY
:::

Now create the record:

:::code{language=bash}
RECORD_ID=$(aws bedrock-agentcore-control create-registry-record \
  --registry-id "$REGISTRY_ID" \
  --name MarketData \
  --descriptor-type MCP \
  --descriptors file:///tmp/market-data-descriptors.json \
  --record-version "1.0.0" \
  --query 'recordId' --output text)

echo "Record: $RECORD_ID"
:::

The record is created in `CREATING` and transitions to `DRAFT` once processed. A draft record is **not** yet discoverable — that's the point of the governance workflow.

## Step 9: Run the Governance Workflow (Submit → Approve)

This is the enterprise approval step. A publisher submits; a curator approves. Because auto-approval is off, submission moves the record to `PENDING_APPROVAL`, where it waits for a reviewer.

**Submit for approval** (publisher action):

:::code{language=bash}
aws bedrock-agentcore-control submit-registry-record-for-approval \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID"
:::

The record moves to `PENDING_APPROVAL`.

**Approve the record** (curator action) — in production this is a different persona with separate IAM permissions; here you play both roles:

:::code{language=bash}
aws bedrock-agentcore-control update-registry-record-status \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID" \
  --status APPROVED \
  --status-reason "Schemas reviewed, auth + network posture verified (see Step 3 checklist)"
:::

The record is now `APPROVED` and becomes discoverable in search.

:::alert{header="Separation of duties" type="info"}
In a real org, the **publisher** (the market data team) and the **curator** (the platform/security team) are different principals. IAM permissions for `SubmitRegistryRecordForApproval` and `UpdateRegistryRecordStatus` are granted to different roles, so no single team can both publish and self-approve. Pair this with Amazon EventBridge notifications to alert curators when a record enters `PENDING_APPROVAL`.
:::

## Step 10: Discover the Tool with Hybrid Search

Now any consumer — a human, or another agent — can find the tool by intent, not just exact name. Search is a data-plane call (`bedrock-agentcore`):

:::code{language=bash}
# Semantic query — note the words don't match the tool name
aws bedrock-agentcore search-registry-records \
  --search-query "how much is a stock worth right now" \
  --registry-ids "$REGISTRY_ID"

# Keyword query
aws bedrock-agentcore search-registry-records \
  --search-query "market data" \
  --registry-ids "$REGISTRY_ID"
:::

Both queries return the approved `MarketData` record. Hybrid search matched *"how much is a stock worth"* to `get_market_quote` even though none of those words appear in the tool name — that's the semantic layer. Only `APPROVED` records appear; a `DRAFT`, `PENDING_APPROVAL`, `REJECTED`, or `DEPRECATED` record stays invisible to consumers.

## Step 11: Revoke (Optional Demo)

Governance includes pulling things back. You can revoke at either layer:

:::code{language=bash}
# Revoke org-wide discovery — deprecate the registry record (it disappears from search)
aws bedrock-agentcore-control update-registry-record-status \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID" \
  --status DEPRECATED \
  --status-reason "Superseded by market-data v2"

# Revoke your agent's access — remove the Gateway target, then redeploy
agentcore remove gateway-target --name MarketData -y
agentcore deploy -y -v
:::

Deprecating the record removes it from discovery (the catalog stops advertising it); removing the Gateway target removes the agent's ability to *call* it. The two layers revoke independently — you can keep a tool in the catalog while cutting a specific agent's access, or pull it from discovery while existing integrations keep working until they're migrated.

## Architecture

:::code{language=bash showCopyAction=false}
AWS Agent Registry (PortfolioAdvisorToolRegistry) — org-wide discovery & governance
    └── MarketData (MCP record)   [Draft → Pending → Approved]   ← publish/approve workflow
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance
                    ↕  hybrid search (semantic + keyword), for humans and agents

AgentCore Gateway (my-gateway) — per-agent connectivity & authorization
    ├── PortfolioRiskCheck (Lambda)     [Approved: Lab 2]
    ├── ExecuteTrade (Lambda)           [Approved: Lab 2]
    └── MarketData (MCP Server)         [Approved: this lab]
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance
                    ↑  Gateway synchronizes schemas; agent calls via MCP client
:::

## What Just Happened?

You implemented an enterprise tool approval and discovery workflow across two layers:

**Part A (Gateway — connectivity):**
1. **Inspected** the Gateway — saw what your agent can currently call (2 Lambda targets from Lab 2)
2. **Reviewed** a candidate — checked tool schemas, input types, security posture
3. **Approved for your agent** — added the MCP server as a Gateway target
4. **Verified** — the agent automatically discovered and used the new tools

**Part B (AWS Agent Registry — discovery & governance):**
5. **Used a pre-provisioned registry** — inspected an org-wide catalog with IAM auth and manual approval
6. **Published a record** — described the Market Data MCP server, validated against the MCP schema
7. **Governed** — ran the submit → approve workflow (separation of duties)
8. **Discovered** — found the tool via hybrid semantic + keyword search
9. **(Optional) Revoked** — deprecated the record and/or removed the Gateway target

---

## Best Practices: Enterprise Tool Governance

:::alert{header="Best Practice" type="info"}
**Two layers, default-deny on both.** A tool not connected to a Gateway can't be *called*; a tool not approved in the Registry can't be *discovered*. Use the Gateway to control what an agent can do, and the Registry to control what the org can find and reuse.
:::

**The end-to-end workflow:**

```
Team deploys MCP server / Lambda / API
    ↓
Platform team reviews (security checklist above)
    ↓
─── Connectivity layer ───────────────────────
Add as Gateway target (agentcore add gateway-target)
    → Gateway synchronizes & indexes; the agent can now call it
─── Discovery layer ──────────────────────────
Publish a registry record (create-registry-record)
    → submit for approval → curator approves
    → org-wide hybrid search can find it
─── Governance layer ─────────────────────────
Policy Engine governs WHO can call it (Lab 3)
```

**When to use which:**

| Need | Use |
|---|---|
| Let a specific agent call a tool, with auth + traffic routing | **Gateway target** |
| Let teams across the org find an MCP server / agent / skill | **Agent Registry record** |
| Control what becomes discoverable (approval, deprecation) | **Agent Registry** workflow |
| Control which agent/principal may invoke a given action | **Cedar policies** (Lab 3) |

**Why this works for FSI:**

| Requirement | How it's satisfied |
|---|---|
| **Audit trail** | Gateway registrations/invocations are logged; Registry API calls are logged in AWS CloudTrail |
| **Least privilege** | Default-deny on both layers — only approved tools are callable and discoverable |
| **Separation of duties** | Registry splits publisher vs. curator via IAM; platform approves Gateway targets; policy team writes Cedar rules |
| **Emergency revocation** | Deprecate the record (stop discovery) and/or remove the target (stop calls) — no code deploy needed |
| **Reuse without sprawl** | A central catalog stops teams rebuilding MCP servers that already exist |

**Security review patterns:**

- **Schema validation** — Verify all input parameters are typed. The Registry validates MCP records against the protocol schema; reject tools with untyped `any` or unbounded string inputs.
- **Output classification** — Understand what data the tool returns. If it returns PII, the agent's responses may contain PII — does your data handling policy allow this?
- **Authentication posture** — Never approve unauthenticated tools for production Gateways. Require OAuth, API key, or IAM on all outbound connections.
- **Network path** — For FSI, prefer tools deployed in the same VPC or accessible via PrivateLink. Public internet tools carry data residency risk.
- **Rate limiting** — Verify the tool backend has rate limits. An agent can generate high tool call volumes — without limits, a malfunctioning agent can overwhelm a backend.

**Hybrid search for tool discovery:**

The Registry combines semantic understanding with keyword matching, so the query *"how much is Apple stock worth"* matches `get_market_quote` even though the words don't overlap, while an exact name lookup still works. This is powerful but depends on high-quality descriptions — invest in the `description` field during the review/publish step. (The Gateway applies the same principle for the agent's own tool selection when `searchType: SEMANTIC` is enabled.)

**Multi-team tool sharing:**

Multiple agents can share the same Gateway, and multiple teams can discover from the same Registry. Team A publishes an MCP server once; Team B finds it in the catalog instead of rebuilding it, connects it to their own Gateway, and Cedar policies (Lab 3) control which agent can call which action — enabling reuse without over-permitting access.

---

### What's Next

→ Continue with: [Evaluations](../60-lab5-evaluations/) | [VPC Networking](../70-lab6-vpc/) | [Memory](../80-optional-memory/)
