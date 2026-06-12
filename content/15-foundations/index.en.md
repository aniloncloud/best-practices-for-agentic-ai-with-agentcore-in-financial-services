---
title: "Foundations: Building Production Agents"
weight: 15
---

**⏱️ Reading time: ~10 minutes (no hands-on steps)**

Read this while your facilitator introduces the session — or while your first deploy is running in Lab 1. The key points are also summarized in Lab 1's "While this deploys" panel, so you won't miss anything by starting the deploy first.

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

## The Journey: Five Questions, Three Live Labs + Self-Paced

The live session answers questions 1, 2, and 3 directly. Questions 4 and 5 are answered in the self-paced labs after the session:

:::code{language=bash showCopyAction=false}
── LIVE SESSION (52 min hands-on) ──────────────────────────────────────────

Lab 1: Deploy to the AgentCore Harness
  │   "Here's the agent, running in the cloud"
  │   (observability is on from the first invoke)  ─── Question 3 begins ✓
  │
Lab 2: Connect Tools with Gateway + JWT Auth
  │   "Tools are centralized; only authenticated callers"  ── Question 1 ✓
  │
Lab 3: Govern Agent Actions with Cedar Policies
      "Cedar policies block oversized trades"  ─────────── Question 2 ✓
      "Every decision is logged for audit"  ──────────────  Question 3 ✓

── SELF-PACED (continue after the session) ─────────────────────────────────

Observability Deep Dive
      Traces, session isolation, token metrics, dashboards  Question 3 (deep) ✓

OAuth Token Flows: M2M & Token Lifecycle
      Full token lifecycle, M2M client credentials  ───────  Question 1 (deep) ✓

VPC Networking
      "All traffic stays on private networks"  ────────────  Question 4 ✓

Evaluations
      "Quality is measured continuously"  ─────────────────  Question 5 ✓
:::

By the end, you'll have a production-hardened agent — not by rewriting it, but by progressively layering security, governance, observability, and network isolation around the same core code.

---

## The Architecture You're Building

This is where you'll end up after the three live labs:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token ──────────────────────────── Lab 2
    ↓
AgentCore Harness (PortfolioAdvisor) ─────────────── Lab 1
    │   with OpenTelemetry traces ────────────────── (from first invoke)
    │
    ├── Model + system prompt (stock/compliance reference data)
    │
    └── Gateway tool (by reference) → AgentCore Gateway ─ Lab 2
                          │
                          ├── Cedar Policy Engine ── Lab 3
                          │   (permit/forbid rules)
                          │
                          ├── PortfolioRiskCheck → Lambda
                          └── ExecuteTrade → Lambda
                                ↓
                          CloudWatch GenAI Observability
:::

VPC private-subnet isolation (Lab: VPC Networking) and continuous Evaluations are added in the self-paced section.

You'll build this **incrementally** — the agent config stays virtually unchanged. Each lab adds a layer through configuration and CLI commands.

---

## Key Principles

### Work Backwards from the Problem

The first question isn't "what can this agent do?" — it's "what problem are we solving for a specific user?" Start with three use cases. Get those working reliably before expanding scope.

For our Portfolio Advisor, the scope is defined:
- **Does:** Stock analysis, compliance rules, portfolio risk, trade execution
- **Doesn't:** Portfolio construction, tax optimization, personalized advice

### Observability from Day One

Don't add logging after something breaks. AgentCore instruments every invocation automatically — traces, metrics, and audit records from the very first `agentcore invoke`. You'll see this in Lab 1.

### Governance Outside the Agent

Business rules don't belong in prompts. A prompt can be manipulated; a Cedar policy cannot. Trade limits and restricted securities are enforced deterministically at the Gateway boundary — the agent can't bypass them even if instructed to. You'll build this in Lab 3.

### Zero Code Changes for Production Hardening

The agent is a declarative **harness** (`harness.json`) — model, system prompt, and tools as configuration, with no orchestration code to write or maintain. Authentication (Lab 2), governance (Lab 3), evaluations, and VPC isolation are all **configuration changes**. Across the entire live session there are **zero agent code edits** — even outbound tool authentication is handled for you: the harness fetches and refreshes the Gateway's M2M token automatically. Gateway tools attach by reference. Platform teams own the guardrails; agent teams own the logic.

---

### Ready to Deploy?

→ Next: [Lab 1: Deploy to AgentCore Runtime](../20-lab1-runtime/)
