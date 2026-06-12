---
title: "Lab 1: Deploy to AgentCore Runtime"
weight: 20
---

**⏱️ ~10 minutes (2–3 of them are a deploy you'll read through)**

## Overview

Your portfolio advisor agent is pre-built and ready to deploy. In this lab you'll push it to AgentCore Runtime — a fully managed serverless container — verify it responds, and see your first traces in CloudWatch GenAI Observability.

### What You're Building

:::code{language=bash showCopyAction=false}
                        ┌─────────────────────────────────────┐
                        │   AgentCore Runtime  ← THIS LAB     │
agentcore invoke ──────▶│                                     │
                        │   PortfolioAdvisor                  │
                        │   ├── get_stock_analysis()          │
                        │   └── get_compliance_rules()        │
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

- Packages your agent code and dependencies
- Uploads the package to S3
- Provisions a serverless AgentCore Runtime (no Dockerfile, ECR, or CloudFormation to write)
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

### Code tour: open `app/PortfolioAdvisor/main.py`

The agent is short. Find these four things:

**Local tools** (simulated data for the workshop):

```python
def get_stock_analysis(ticker: str) -> dict:
    ...  # returns price, PE ratio, recommendation

def get_compliance_rules(category: str) -> dict:
    ...  # returns applicable compliance rules
```

**System prompt** — defines scope (stock analysis, compliance, portfolio risk, trade execution) and tone (institutional, cite rules).

**`@app.entrypoint` async generator** — the AgentCore Runtime entry point. AgentCore calls this for every invocation and streams back chunks.

**Gateway hook** — look for `get_or_create_agent`:

```python
gateway_client = get_gateway_mcp_client(auth_header)
if gateway_client:
    tools.append(gateway_client)
```

`get_gateway_mcp_client()` (in `mcp_client/client.py`) looks for a Gateway URL in the environment — for the gateway you'll create in Lab 2, that's `AGENTCORE_GATEWAY_MY_GATEWAY_URL` (the code also checks a legacy `..._SECURE_URL` name first; it's never set in this workshop). No Gateway exists yet, so the lookup returns `None` and the agent runs with local tools only. In Lab 2, you'll create a Gateway and the CLI automatically injects the URL — zero code changes needed. This is environment-driven wiring.

---

### Config tour: `agentcore/agentcore.json`

:::code{language=bash}
cat agentcore/agentcore.json
:::

This is the single source of truth for everything AgentCore manages. Right now it has one entry: the `PortfolioAdvisor` runtime pointing at `app/PortfolioAdvisor/` with `main.py` as the entrypoint. Gateway config, auth config, and Cedar policies will accumulate here in Labs 2–3 via CLI commands — not by editing code.

**Project layout for reference:**

```
PortfolioAdvisor/
├── agentcore/
│   ├── agentcore.json              # Single source of truth (runtimes, gateways, policies)
│   ├── aws-targets.json            # Deployment targets (account, region)
│   └── .cli/deployed-state.json    # Tracks deployed ARNs (auto-managed)
├── app/
│   └── PortfolioAdvisor/
│       ├── main.py                 # Agent: system prompt, local tools, @app.entrypoint
│       ├── model/load.py           # Model config (Claude Sonnet)
│       ├── mcp_client/client.py    # Gateway MCP client (env-driven, no edit needed)
│       ├── tool/*.json             # Tool schemas for Gateway targets (Labs 2–3)
│       └── pyproject.toml          # Python dependencies (pre-installed)
└── .venv/                          # Virtual environment (pre-built)
```

::::

---

## Step 3 — Verify and invoke

Check the deploy completed:

:::code{language=bash}
agentcore status
:::

You should see `PortfolioAdvisor` in `READY` state.

Generate a session ID and run your first invocation:

:::code{language=bash}
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What's the current analysis for AAPL? Include price, PE ratio, and recommendation." \
  --session-id $SESSION_ID --stream
:::

The agent should respond with Apple's stock data — price $178.52, PE ratio 28.4, Buy recommendation.

Try a compliance query in the same session:

:::code{language=bash}
agentcore invoke "What are the compliance rules for options trading?" \
  --session-id $SESSION_ID --stream
:::

---

## Step 4 — Session isolation A/B test

AgentCore gives each session-id its own microVM context. Let's prove it.

**Same session — context is remembered:**

:::code{language=bash}
agentcore invoke "I'm interested in tech stocks" \
  --session-id $SESSION_ID --stream

agentcore invoke "Compare the two biggest ones" \
  --session-id $SESSION_ID --stream
:::

The agent compares AAPL and MSFT without you naming them — it remembers the session context.

**New session — context is gone:**

:::code{language=bash}
NEW_SESSION=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "Compare the two biggest ones" \
  --session-id $NEW_SESSION --stream
:::

The agent doesn't know what "the two biggest ones" refers to — because the new session has no prior context. This is microVM-level session isolation: each session-id is a separate execution environment with no shared state.

---

## Step 5 — One trace in CloudWatch

View recent logs via CLI:

:::code{language=bash}
agentcore logs --runtime PortfolioAdvisor --since 10m
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

## Best Practices: Runtime-First Development

:::alert{header="Best Practice" type="info"}
**Deploy to the cloud on day one, even with a single tool.** Don't wait until the agent is "done."
:::

Traditional development runs local until deployment becomes a separate project — exposing IAM, networking, timeout, and quota issues late when they're expensive. Runtime-first flips that:

1. **Deploy immediately** — Cloud from day one, even with one tool
2. **Iterate fast** — `agentcore deploy` takes ~2 minutes for updates; infrastructure already exists after the first deploy
3. **Observe from the start** — Cold start times, model latency under load, token patterns are invisible locally
4. **Fail early on integration** — Discover IAM and quota issues when they're still cheap to fix

Use `agentcore dev` for rapid local prompt engineering and tool-logic debugging — but treat it as a supplement, not the primary workflow.

---

→ Next: [Lab 2: Connect Tools with Gateway + JWT Auth](../30-lab2-gateway/)
