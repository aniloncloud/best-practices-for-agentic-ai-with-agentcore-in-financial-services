---
title: "Foundations: Building Production Agents"
weight: 15
---

**⏱️ Reading time: ~10 minutes (no hands-on steps)**

Read this while your facilitator introduces the session. No commands to run.

---

## The Financial Services Challenge

Financial services firms operate under constraints that most industries don't face:

- **Regulatory scrutiny** — SEC Rule 17a-4, FINRA Rule 3110, SOX, MiFID II all require complete records of client interactions and decision trails
- **Deterministic controls** — Trade limits, restricted securities, and position size rules must be enforced with zero exceptions — regardless of how cleverly a prompt is crafted
- **Data residency** — Market-sensitive data, PII, and trading signals cannot traverse public networks
- **Audit at any time** — Regulators can request a complete history of every decision an AI system made on behalf of a client

These constraints don't disappear because you're using AI. They intensify. An AI agent that executes trades, assesses risk, or advises clients must meet the same bar as the humans it augments.

**This workshop addresses each constraint directly:**

| Constraint | Workshop Answer | Lab |
|------------|----------------|-----|
| Regulatory record-keeping | Automatic OpenTelemetry traces for every invocation | Lab 1B |
| Deterministic controls | Cedar policies enforced at the Gateway boundary | Lab 4 |
| Data residency | VPC isolation with private subnets and VPC endpoints | Lab 6 |
| Audit trail | Agentic Explainability combining reasoning + policy decisions | Lab 4 |
| Authentication | JWT-based identity on Runtime and Gateway | Lab 3 |

---

## Work Backwards from the Problem

The first question isn't "what can this agent do?" — it's "what problem are we solving for a specific user?"

Too many teams start by building an agent that handles every scenario. This leads to complexity, slow iteration, and agents that don't excel at anything. Instead, work backwards from a specific use case. Start with the three most common analyst tasks. Get those working reliably before expanding scope.

### Four Planning Deliverables

Your initial planning should produce four concrete artifacts:

| Deliverable | What It Contains | Why It Matters |
|-------------|-----------------|----------------|
| **Scope definition** | What the agent should and should NOT do. Written down, shared with stakeholders. | Lets you say "no" to feature creep. Prevents prompt bloat. |
| **Tone and personality** | Formal or conversational? How does it handle questions outside its scope? | Consistency builds trust. Clients expect precision, not chattiness. |
| **Tool specifications** | Unambiguous definitions for every tool, parameter, and knowledge source. | Vague descriptions cause the LLM to make incorrect tool selections. You'll measure this with ToolSelectionAccuracy in Lab 5. |
| **Ground truth dataset** | Expected interactions covering common queries AND edge cases. | Becomes your evaluation baseline. Without it, you can't measure if a change improved or degraded the agent. |

### What This Looks Like for Our Portfolio Advisor

In this workshop, these decisions are already made:

- **Scope:** Stock analysis, compliance rule lookups, portfolio risk assessment, trade execution. NOT: portfolio construction, tax optimization, or personalized investment advice.
- **Tone:** Professional and precise. Always caveats "this is informational only, not personalized investment advice."
- **Tools:** `get_stock_analysis` (local), `get_compliance_rules` (local), `check_portfolio_risk` (Gateway → Lambda), `execute_trade` (Gateway → Lambda).
- **Ground truth:** The test queries in Labs 1–5 serve as a basic ground truth. Production agents need hundreds of test cases.

---

## Observability Strategy

One of the most significant mistakes teams make is treating observability as something to add later. By the time you realize you need it, you've shipped an agent that's difficult to debug.

From your first invocation, you need visibility into what your agent is doing:

| Layer | What It Provides | When You Use It |
|-------|-----------------|-----------------|
| **Traces** | End-to-end spans: prompt → tool selection → tool execution → response | Debugging a specific bad response |
| **Dashboards** | Aggregate metrics: latency, error rate, token usage, invocation volume | Daily production monitoring |
| **Evaluations** | Quality scoring: accuracy, tool selection, response faithfulness | Before and after every change |

AgentCore Runtime produces traces automatically via OpenTelemetry. CloudWatch GenAI Observability provides the dashboards. You'll explore both in Lab 1B and add evaluations in Lab 5.

---

## The "No Code Changes" Philosophy

A recurring theme across Labs 4, 5, and 6: **you don't change the agent code.** Governance (Cedar policies), quality monitoring (evaluations), and network isolation (VPC) are all configuration changes — not application code changes.

This is intentional:
- Code changes require code review, testing, and deployment pipelines
- Configuration changes can be applied by platform teams without touching application code
- Separation of concerns: the agent team owns the logic; the platform team owns the guardrails
- Emergency shutdown (forbid all tool access) is a one-line policy change, not a code deploy

By the end of this workshop, you'll have added authentication, authorization, governance, evaluation, and network isolation — and your `main.py` will have changed in exactly two places.

---

## What You're Building

```
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor) — in VPC private subnet
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── MCP Client → AgentCore Gateway (JWT + Cedar Policy Engine)
                          ├── PortfolioRiskCheck → Lambda
                          ├── ExecuteTrade → Lambda (governed by Cedar policies)
                          ↓
                    CloudWatch GenAI Observability
                          ↓
                    AgentCore Evaluations (QualityMonitor)
```

You'll build this incrementally — one layer per lab — starting with a bare deploy in Lab 1.

---

### Ready to Deploy?

→ Next: [Lab 1: Deploy to AgentCore Runtime](../20-lab1-runtime/)
