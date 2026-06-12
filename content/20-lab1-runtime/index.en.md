---
title: "Lab 1: Deploy to the AgentCore Harness"
weight: 20
---

**⏱️ ~10 minutes (2–3 of them are a deploy you'll read through)**

## Overview

Your portfolio advisor agent is defined as a **harness** — a declarative configuration, not hand-written orchestration code. In this lab you'll deploy it to AgentCore, verify it responds, right-size the model live, and see your first traces in CloudWatch GenAI Observability.

The AgentCore harness runs the full agent loop for you — reasoning, tool selection, action, response streaming — from a single config file. You declare *what* the agent does (model, instructions, tools); AgentCore provides the runtime, memory, identity, and observability. The harness is powered by [Strands Agents](https://strandsagents.com/).

### What You're Building

:::code{language=bash showCopyAction=false}
                        ┌─────────────────────────────────────┐
                        │   AgentCore Harness  ← THIS LAB     │
agentcore invoke ──────▶│                                     │
                        │   PortfolioAdvisor (harness.json)   │
                        │   ├── model: Claude Sonnet 4.6      │
                        │   ├── system prompt (+ reference)   │
                        │   └── tools: [] (Gateway added Lab2)│
                        │                                     │
                        │   ──▶ CloudWatch (auto-instrumented)│
                        └─────────────────────────────────────┘
:::

---

## Step 1 — Start the deploy now

:::alert{header="Run this BEFORE reading further" type="warning"}
The deploy takes 2–3 minutes. Start it now, then read Step 2 while it runs — that reading is the designated activity during the wait.
:::

:::code{language=bash}
cd ~/PortfolioAdvisor
agentcore validate
agentcore deploy -y -v
:::

What `agentcore deploy` does so you don't have to:

- Reads your `harness.json` and registers the managed harness
- Provisions the serverless AgentCore environment (no Dockerfile, ECR, or orchestration code to write)
- Pulls the managed harness image and attaches networking, identity, and observability
- Creates an invocation endpoint
- Wires CloudWatch logging and tracing automatically

---

## Step 2 — While this deploys

::::expand{header="While this deploys: what you're deploying and why (open me)"}

### The CISO's five questions

Every financial services agent hits the same wall before production. Your CISO asks:

1. **"Who can call this agent?"** — Right now, anyone with the endpoint URL.
2. **"What stops it from executing a $50M trade?"** — Nothing yet.
3. **"Can you prove what it did last Tuesday at 2:14 PM?"** — This lab starts answering that.
4. **"Does client data leave our network?"** — Covered in the self-paced VPC lab.
5. **"How do you know it's giving accurate advice?"** — Covered in the self-paced Evaluations lab.

The live labs close questions 1–3. Here's the map:

:::code{language=bash showCopyAction=false}
Lab 1 (this lab): observability on from first invoke  ──  Question 3 begins ✓
Lab 2 (Gateway + JWT):  only authenticated callers     ──  Question 1       ✓
Lab 3 (Cedar policies): Cedar blocks oversized trades  ──  Question 2       ✓
                        every decision logged           ──  Question 3 full  ✓

Self-paced after session:
  Observability Deep Dive  ──  Question 3 (deep)  ✓
  VPC Networking           ──  Question 4          ✓
  Evaluations              ──  Question 5          ✓
:::

---

### How AgentCore runs your agent (session model)

AgentCore runs every session in its own isolated microVM. The **first** request on a session pays a one-time startup cost; every later request carrying the same session ID skips it. That single fact drives most agent performance — so the highest-leverage optimization is simply **reusing a session for a unit of work** (a conversation, a batch), not minting a new session per request. You'll prove this isolation firsthand in the A/B test in Step 4.

Observability is already on. Every invoke emits an OpenTelemetry trace — model calls, tool calls, per-step timing — with no instrumentation from you. That's the start of answering the CISO's Question 3 ("prove what it did").

> **Deep dive (self-paced):** the session model, cold starts, and session reuse are covered in depth in the AgentCore optimization best-practices companion guide and the [Observability Deep Dive](../25-lab1b-observability/).

---

### Config tour: open `app/PortfolioAdvisor/harness.json`

This one file *is* the agent. Find these three things:

**`model`** — `global.anthropic.claude-sonnet-4-6` on Amazon Bedrock. Changing the model is a one-line edit, or a per-invocation override (you'll do this in Step 4). No code, no rebuild.

**`systemPrompt`** — defines the advisor's scope and tone, and carries a compact block of **stock and compliance reference data** directly in the prompt.

:::alert{header="Why is the reference data in the prompt?" type="info"}
A best practice: **if a tool would return the same static content on every call, put that content in the system prompt instead.** It's faster and cheaper than a tool round trip, and it lets Lab 1 work with zero external tools. The *dynamic* tools — portfolio risk and trade execution — come through the Gateway in Lab 2, because their results change per request and must be governed.
:::

**`tools`** — empty for now. In Lab 2 you'll attach the Gateway by reference and its tools appear automatically. **`allowedTools`** is also empty, which you'll use later to restrict the agent to exactly the tools it should have (least privilege).

**Project layout for reference:**

```
PortfolioAdvisor/
├── agentcore/
│   ├── agentcore.json              # Project config (harnesses, gateways, policies)
│   ├── aws-targets.json            # Deployment targets (account, region)
│   └── .cli/deployed-state.json    # Tracks deployed ARNs (auto-managed)
├── app/
│   └── PortfolioAdvisor/
│       ├── harness.json            # THE agent: model, system prompt, tools, limits
│       └── tool/*.json             # Tool schemas for Gateway targets (Labs 2–3)
└── ...
```

There is no `main.py`, no orchestration loop, and no MCP client code to maintain. That code is what the managed harness runs for you.

> **How this was scaffolded:** this project was created once with `agentcore create --name PortfolioAdvisor --model-provider bedrock` (which generates `harness.json`); we added the system prompt and reference data. Your harness **execution role** is pre-provisioned in your account, so `agentcore deploy` just works. (You'll create the outbound credential provider for the Gateway yourself in Lab 2.)

::::

---

## Step 3 — Verify and invoke

Check the deploy completed:

:::code{language=bash}
agentcore status
:::

You should see the `PortfolioAdvisor` harness in `READY` state.

Generate a session ID and run your first invocation:

:::code{language=bash}
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke --harness PortfolioAdvisor \
  --session-id $SESSION_ID \
  "What's the current analysis for AAPL? Include price, PE ratio, and recommendation."
:::

The agent should respond with Apple's stock data — price $178.52, PE ratio 28.4, Buy recommendation — answered directly from the reference data in its system prompt.

Try a compliance query in the same session:

:::code{language=bash}
agentcore invoke --harness PortfolioAdvisor \
  --session-id $SESSION_ID \
  "What are the compliance rules for options trading?"
:::

---

## Step 4 — Right-size the model live (no redeploy)

Because the harness makes the model a per-invocation override, you can feel the latency/cost/quality tradeoff in real time — without changing the agent.

First, a narrow extraction-style ask on a small, fast model:

:::code{language=bash}
agentcore invoke --harness PortfolioAdvisor \
  --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --session-id $(python3 -c 'import uuid; print(uuid.uuid4())') \
  "Which sector is JPM in? One word."
:::

Now the same agent on its default reasoning model for a multi-step ask:

:::code{language=bash}
agentcore invoke --harness PortfolioAdvisor \
  --session-id $(python3 -c 'import uuid; print(uuid.uuid4())') \
  "Compare AAPL and MSFT on valuation and risk, and flag any compliance concerns."
:::

:::alert{header="Best Practice: right-size the model per role" type="info"}
One agent, different model per task. Small models are roughly 10–30x cheaper per token and faster — right for classification, extraction, and routing. Reserve premium reasoning models for planning and synthesis. In a multi-agent system you make this choice per specialist, per evaluator, even for memory extraction. The harness even lets you **switch models mid-session** with context preserved. No code, no redeploy — just the model field.
:::

---

## Step 5 — Session isolation A/B test

AgentCore gives each session ID its own microVM context. Let's prove it.

**Same session — context is remembered:**

:::code{language=bash}
agentcore invoke --harness PortfolioAdvisor --session-id $SESSION_ID \
  "I'm interested in tech stocks"

agentcore invoke --harness PortfolioAdvisor --session-id $SESSION_ID \
  "Compare the two biggest ones"
:::

The agent compares AAPL and MSFT without you naming them — it remembers the session context.

**New session — context is gone:**

:::code{language=bash}
NEW_SESSION=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke --harness PortfolioAdvisor --session-id $NEW_SESSION \
  "Compare the two biggest ones"
:::

The agent doesn't know what "the two biggest ones" refers to — because the new session has no prior context. This is microVM-level session isolation: each session ID is a separate execution environment with no shared state. It's also a security property — one user's session can't read another's.

---

## Step 6 — One trace in CloudWatch

View recent logs via CLI:

:::code{language=bash}
agentcore logs --harness PortfolioAdvisor --since 10m
:::

For the visual trace view:

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Navigate to **GenAI Observability** → **Bedrock AgentCore**
3. Click **PortfolioAdvisor** → **DEFAULT** endpoint

You'll see a trace waterfall with spans for model inference, tool selection, and tool execution — each with timing, input/output, and token counts.

:::alert{header="Observability was free" type="info"}
You wrote zero instrumentation code. AgentCore auto-instruments every invocation with OpenTelemetry. Traces, logs, and metrics appeared on the first `agentcore invoke`.
:::

Deeper dive (X-Ray spans, token metrics, session isolation traces, dashboards) is in the self-paced [Observability Deep Dive](../25-lab1b-observability/).

---

## Best Practices: Declare, Deploy, Observe

:::alert{header="Best Practice" type="info"}
**Declare the agent as configuration and deploy to the cloud on day one.** Don't wait until the agent is "done."
:::

The harness model makes this natural: there's no orchestration code to write before you can deploy, and trying a different model or adding a tool is a config change, not a rewrite. Runtime-first development means:

1. **Deploy immediately** — Cloud from day one, even with zero external tools
2. **Iterate fast** — Change the model, prompt, or tools and redeploy in ~2 minutes; or override per invocation with no deploy at all
3. **Observe from the start** — Cold start times, model latency under load, and token patterns are invisible locally
4. **Fail early on integration** — Discover IAM and quota issues when they're still cheap to fix

Use `agentcore dev` for rapid local prompt iteration — but treat it as a supplement, not the primary workflow.

---

→ Next: [Lab 2: Connect Tools with Gateway + JWT Auth](../30-lab2-gateway/)
