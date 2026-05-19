---
title: "Foundations: Building Production Agents"
weight: 15
---

**⏱️ Reading time: ~10 minutes (no hands-on steps)**

Read this while your facilitator introduces the session. No commands to run.

---

## From Demo to Production: The Gap

You've built a prototype. It answers questions, calls tools, impresses stakeholders. Then your CISO asks five questions:

1. **"Who can call this agent?"** — Right now, anyone with the endpoint URL.
2. **"What stops it from executing a $50M trade?"** — Nothing. It does whatever the user asks.
3. **"Can you prove what it did last Tuesday at 2:14 PM?"** — Maybe, if someone thought to add logging.
4. **"Does client data ever leave our network?"** — You'd have to check.
5. **"How do you know it's giving accurate advice?"** — We tested it manually. Once.

Every one of these is a blocker in financial services. Not "nice to have" — a blocker. Your agent will not reach production until you can answer all five.

**This workshop closes that gap.** You'll start with a working agent and add each production layer — one lab at a time — until you can answer every question with confidence.

---

## The Journey: Five Questions, Six Labs

Each lab directly answers one (or more) of the CISO's questions:

:::code{language=bash showCopyAction=false}
Lab 1: Deploy                    "Here's the agent, running in the cloud"
  │
Lab 1B: Observability            "We can prove what it did, when, and why" ─── Question 3 ✓
  │
Lab 2: Gateway                   "Tools are centralized, discoverable, and auditable"
  │
Lab 3: Security                  "OAuth 2.0 — only authenticated callers" ──── Question 1 ✓
  │
Lab 4: Governance                "Cedar policies block oversized trades" ────── Question 2 ✓
  │                              "Every decision is logged for audit" ───────── Question 3 ✓
Lab 5: Evaluations               "Quality is measured continuously" ──────────  Question 5 ✓
  │
Lab 6: VPC                       "All traffic stays on private networks" ─────  Question 4 ✓
:::

By the end, you'll have a production-hardened agent — not by rewriting it, but by progressively layering security, governance, observability, and network isolation around the same core code.

---

## The Architecture You're Building

This is where you'll end up after the six core labs:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token ──────────────────────────── Lab 3
    ↓
AgentCore Runtime (PortfolioAdvisor) ─────────────── Lab 1
    │   in VPC private subnet ────────────────────── Lab 6
    │   with OpenTelemetry traces ────────────────── Lab 1B
    │   with continuous evaluations ──────────────── Lab 5
    │
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    │
    └── MCP Client → AgentCore Gateway ───────────── Lab 2
                          │
                          ├── Cedar Policy Engine ── Lab 4
                          │   (permit/forbid rules)
                          │
                          ├── PortfolioRiskCheck → Lambda
                          └── ExecuteTrade → Lambda
:::

You'll build this **incrementally** — the agent code stays virtually unchanged. Each lab adds a layer through configuration and CLI commands.

---

## Key Principles

### Work Backwards from the Problem

The first question isn't "what can this agent do?" — it's "what problem are we solving for a specific user?" Start with three use cases. Get those working reliably before expanding scope. 

For our Portfolio Advisor, the scope is defined:
- **Does:** Stock analysis, compliance rules, portfolio risk, trade execution
- **Doesn't:** Portfolio construction, tax optimization, personalized advice

### Observability from Day One

Don't add logging after something breaks. AgentCore instruments every invocation automatically — traces, metrics, and audit records from the very first `agentcore invoke`. You'll see this in Lab 1B.

### Governance Outside the Agent

Business rules don't belong in prompts. A prompt can be manipulated; a Cedar policy cannot. Trade limits and restricted securities are enforced deterministically at the Gateway boundary — the agent can't bypass them even if instructed to. You'll build this in Lab 4.

### No Code Changes for Production Hardening

Authentication (Lab 3), governance (Lab 4), evaluations (Lab 5), and VPC isolation (Lab 6) are all **configuration changes** — not application code changes. Your `main.py` changes in exactly two places across all six labs. Platform teams own the guardrails; agent teams own the logic.

---

### Ready to Deploy?

→ Next: [Lab 1: Deploy to AgentCore Runtime](../20-lab1-runtime/)
