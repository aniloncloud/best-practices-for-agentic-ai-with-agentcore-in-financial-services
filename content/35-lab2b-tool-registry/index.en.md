---
title: "Optional Lab: Enterprise Tool Registry"
weight: 60
---

**⏱️ Estimated time: ~15 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Labs 1–2 (Deploy to AgentCore Runtime + Connect Tools with Gateway + JWT Auth)
:::

:::alert{header="Optional Lab — Requires Pre-provisioned Infrastructure" type="warning"}
This lab requires an **AWS Agent Registry** pre-provisioned in your account, exposed as SSM parameter `/app/portfolioadvisor/agentcore/tool_registry_id`. If that parameter doesn't exist, skip this lab — the core path runs Lab 2 → Lab 3 (Cedar Policies) and nothing later depends on anything here.
:::

## Overview

In Lab 2, you registered Lambda functions as Gateway tools — you already know how to make a tool **callable** by your agent. But that's only half the enterprise story. Once a tool is approved, every other team that might reuse it needs to **find** it. Without a central catalog, teams rebuild MCP servers that already exist — duplication, drift, and no governance over what's in use.

This lab covers the layer Lab 2 didn't: **AWS Agent Registry** — a private, org-wide catalog where you publish MCP servers, tools, agents, and skills, govern them through an approval workflow, and discover them with hybrid search.

:::code{language=bash showCopyAction=false}
                        ┌─────────────────────────────────────────────┐
   This lab            │   AWS Agent Registry                          │
   discovery + govern  │   catalog • approval workflow • hybrid search  │
                        │   "which tools/MCP servers/agents exist?"     │
                        └─────────────────────────────────────────────┘
                        ┌─────────────────────────────────────────────┐
   Lab 2               │   AgentCore Gateway                            │
   connectivity + auth │   targets = tools an agent can actually call   │
                        │   "what can THIS agent invoke right now?"     │
                        └─────────────────────────────────────────────┘
:::

:::alert{header="Two layers, two jobs" type="info"}
The **Gateway** (Lab 2) makes a tool *callable* by a specific agent. The **AWS Agent Registry** (this lab) makes a tool *discoverable and governable* across the whole organization. You discover and approve a tool in the registry, then connect it to a Gateway for an agent to use — we close with exactly that handoff.
:::

### What You'll Learn

- Inspect the pre-provisioned AWS Agent Registry
- Publish the Market Data MCP server as a registry record
- Run the governance workflow: publish → submit → **review (the approval gate)** → approve
- Discover the tool with hybrid (semantic + keyword) search

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Registry** | A private, org-wide catalog. Holds records for MCP servers, tools, agents, skills, custom resources. |
| **Registry record** | Metadata describing one resource, validated against the MCP/agent protocol schema |
| **Approval workflow** | Records go Draft → Pending approval → Approved. Only approved records are searchable. |
| **Review gate** | A curator reviews a record's schemas and security posture before approving — separation of duties |
| **Hybrid search** | Combines semantic understanding with keyword matching, for both humans and agents |
| **Default deny** | A record that isn't approved is invisible to consumers — zero discovery by default |

### What You're Building

:::code{language=bash showCopyAction=false}
AWS Agent Registry (PortfolioAdvisorToolRegistry)        ← you build this
    └── MarketData (MCP record)   [Draft → Pending → Approved]
            ├── get_market_quote
            ├── get_historical_prices
            └── get_sector_performance
                    ↕  hybrid search (semantic + keyword)
                    └─► a consuming team connects it to their Gateway (Lab 2)
:::

The Registry is accessed via the `bedrock-agentcore-control` (management) and `bedrock-agentcore` (search) APIs — there's no harness CLI verb for it, so this lab uses the AWS CLI directly.

## Step 1: Use the Pre-Provisioned Registry

Your workshop account already has a registry provisioned for you. Retrieve its ID from SSM and inspect it:

:::code{language=bash}
REGISTRY_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/tool_registry_id \
  --query 'Parameter.Value' --output text)

aws bedrock-agentcore-control get-registry \
  --registry-id "$REGISTRY_ID" \
  --query '{name:name, status:status, authType:authorizerType}'
:::

You should see `status: READY` with IAM authorization. It was created with **auto-approval off**, which is what lets you walk the full governance workflow below.

:::alert{header="What was pre-created" type="info"}
Only an empty registry is pre-baked (one `create-registry` call, run for you — so you skip the ~1–2 min provisioning wait and don't need `CreateRegistry` permission). Everything below — publish, submit, review, approve, search — is yours to run. That's the governance workflow that's the point of this lab.
:::

## Step 2: Publish the Market Data MCP Server as a Record

A market data team has deployed an MCP server providing real-time quotes, historical prices, and sector performance. To make it discoverable org-wide, a publisher creates a **registry record** describing it.

The record's descriptor is pre-staged at `app/PortfolioAdvisor/tool/market_data_record.json` (it embeds the MCP `server` definition and three tool schemas as JSON — fiddly to hand-type, so we ship it as a file). Open it to see what's being published, then create the record:

:::code{language=bash}
RECORD_ID=$(aws bedrock-agentcore-control create-registry-record \
  --registry-id "$REGISTRY_ID" \
  --name MarketData \
  --descriptor-type MCP \
  --descriptors file://app/PortfolioAdvisor/tool/market_data_record.json \
  --record-version "1.0.0" \
  --query 'recordId' --output text)

echo "Record: $RECORD_ID"
:::

The record is created in `CREATING` and transitions to `DRAFT` — published, but **not yet discoverable**. That's the point of the governance workflow.

## Step 3: Submit for Approval

The publisher submits the record. Because auto-approval is off, it moves to `PENDING_APPROVAL` and waits for a curator:

:::code{language=bash}
aws bedrock-agentcore-control submit-registry-record-for-approval \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID"
:::

## Step 4: Review, Then Approve (The Curator Gate)

This is the enterprise control point. Before approving a record for org-wide discovery, a curator reviews its security posture. This gate is what makes a registry a *governance* tool, not just a list.

Open the record's descriptor (`market_data_record.json`) and check the tool schemas against this checklist:

| Check | What to Verify |
|-------|---------------|
| **Tool schemas** | Inputs are typed and bounded — no unbounded `string` that could accept injected payloads |
| **Authentication** | Endpoint requires auth (OAuth, API key, or IAM). Never approve unauthenticated tools for production |
| **Network posture** | Endpoint is in a trusted network (VPC / private subnet / PrivateLink) |
| **Data classification** | Know what the tool returns — PII? restricted? market-sensitive? |
| **Output surface** | Responses don't leak credentials, internal IPs, or PII in errors |

For this record, the three tools pass: `ticker` is a typed string with format guidance, `period` is constrained (`1W`/`1M`/`3M`/`1Y`), and `sector` is one of five values — all inputs typed and bounded, all with specific descriptions (which also powers hybrid search). With the review complete, approve it:

:::code{language=bash}
aws bedrock-agentcore-control update-registry-record-status \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID" \
  --status APPROVED \
  --status-reason "Schemas reviewed, auth + network posture verified"
:::

The record is now `APPROVED` and becomes discoverable in search.

:::alert{header="Separation of duties" type="info"}
In a real org, the **publisher** (market data team) and the **curator** (platform/security team) are different principals — `SubmitRegistryRecordForApproval` and `UpdateRegistryRecordStatus` go to different IAM roles, so no team can both publish and self-approve. Pair with Amazon EventBridge to alert curators when a record enters `PENDING_APPROVAL`.
:::

## Step 5: Discover the Tool with Hybrid Search

Now any consumer — a human or another agent — can find the tool by intent, not just exact name (`bedrock-agentcore` data-plane call):

:::code{language=bash}
# Semantic query — the words don't match the tool name
aws bedrock-agentcore search-registry-records \
  --search-query "how much is a stock worth right now" \
  --registry-ids "$REGISTRY_ID"

# Keyword query
aws bedrock-agentcore search-registry-records \
  --search-query "market data" \
  --registry-ids "$REGISTRY_ID"
:::

Both return the approved `MarketData` record — hybrid search matched *"how much is a stock worth"* to `get_market_quote` despite no shared words. Only `APPROVED` records appear; `DRAFT`, `PENDING_APPROVAL`, `REJECTED`, and `DEPRECATED` records stay invisible.

## Step 6: From Catalog to Agent

To actually *use* a discovered tool, a consuming team connects it to their Gateway — the same `agentcore add gateway-target` from Lab 2, just with `--type mcp-server`. Nothing to run here; you did that flow in Lab 2.

**The registry governs what's discoverable and approved; the Gateway makes an approved tool callable by a specific agent.**

## Step 7: Revoke (Optional)

Deprecate the record to pull it from discovery org-wide:

:::code{language=bash}
aws bedrock-agentcore-control update-registry-record-status \
  --registry-id "$REGISTRY_ID" \
  --record-id "$RECORD_ID" \
  --status DEPRECATED \
  --status-reason "Superseded by market-data v2"
:::

Re-run the Step 5 search — the record is gone. Deprecating stops discovery while existing Gateway integrations keep working until migrated (removing a Gateway target is the separate, independent revocation).

## What Just Happened?

You ran the org-wide tool governance workflow that Lab 2's Gateway alone doesn't provide:

1. **Used a pre-provisioned registry** — org-wide catalog, IAM auth, manual approval
2. **Published** the Market Data MCP server as a record (`DRAFT`)
3. **Submitted** for approval (`PENDING_APPROVAL`)
4. **Reviewed and approved** — the curator gate, separation of duties
5. **Discovered** via hybrid semantic + keyword search
6. Saw the **handoff** to the Gateway (Lab 2) for agent use
7. **(Optional) Revoked** by deprecating the record

---

## Best Practices: Enterprise Tool Governance

:::alert{header="Best Practice" type="info"}
**Two layers, default-deny on both.** A record not approved in the Registry can't be *discovered*; a tool not connected to a Gateway can't be *called*. Use the Registry to control what the org can find and reuse, the Gateway to control what an agent can do.
:::

**The end-to-end workflow:**

```
Team deploys MCP server / Lambda / API
    ↓
─── Discovery & governance (this lab) ────────
Publish record → submit → curator reviews → approve → org-wide hybrid search
    ↓
─── Connectivity (Lab 2) ─────────────────────
Consuming team adds it as a Gateway target → agent can call it
    ↓
─── Authorization (Lab 3) ────────────────────
Policy Engine governs WHO can call it
```

**When to use which:**

| Need | Use |
|---|---|
| Let teams across the org find an MCP server / agent / skill | **Agent Registry record** |
| Control what becomes discoverable (review, approval, deprecation) | **Agent Registry** workflow |
| Let a specific agent call a tool, with auth + traffic routing | **Gateway target** (Lab 2) |
| Control which agent/principal may invoke a given action | **Cedar policies** (Lab 3) |

**Why this works for FSI:**

| Requirement | How it's satisfied |
|---|---|
| **Audit trail** | Registry and Gateway API calls are logged in AWS CloudTrail |
| **Least privilege** | Default-deny on both layers — only approved tools are discoverable and callable |
| **Separation of duties** | Registry splits publisher vs. curator via IAM; policy team owns Cedar rules |
| **Emergency revocation** | Deprecate the record (stop discovery) and/or remove the target (stop calls) — no code deploy |
| **Reuse without sprawl** | A central catalog stops teams rebuilding MCP servers that already exist |

**Security review patterns:** verify inputs are typed (reject untyped `any`/unbounded strings); classify what the tool returns (PII may flow into agent responses); require auth on all outbound connections; prefer VPC/PrivateLink network paths for FSI; confirm the backend has rate limiting.

**Hybrid search** depends on high-quality descriptions — invest in the `description` field so *"how much is Apple stock worth"* matches `get_market_quote`. **Multi-team sharing:** Team A publishes once; Team B finds it in the catalog instead of rebuilding, connects it to their own Gateway, and Cedar policies (Lab 3) control who can call what.

---

### What's Next

→ Continue with: [Evaluations](../60-lab5-evaluations/) | [VPC Networking](../70-lab6-vpc/) | [Memory](../80-optional-memory/)
