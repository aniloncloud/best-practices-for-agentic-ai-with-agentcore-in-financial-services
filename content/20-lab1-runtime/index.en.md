---
title: "Lab 1: Deploy to AgentCore Runtime"
weight: 22
---

**⏱️ Estimated time: ~15 minutes**

## Overview

Your portfolio advisor agent code is ready — it has stock analysis and compliance tools, a system prompt, and a handler function. In this lab, you'll deploy it to AgentCore Runtime and verify it's working in the cloud with full observability.

### What You'll Learn

- Deploy an agent to AgentCore Runtime with `agentcore deploy`
- Invoke your deployed agent via the CLI
- Explore traces, logs, and metrics in CloudWatch GenAI Observability

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

## Step 1: Verify Your Project

Confirm the workspace is intact and the AgentCore CLI recognizes your project:

:::code{language=bash}
cd ~/PortfolioAdvisor
agentcore validate
:::

You should see:
:::code{language=bash showCopyAction=false}
Valid
:::

Review the runtime configuration:

:::code{language=bash}
cat agentcore/agentcore.json
:::

You'll see a single runtime named `PortfolioAdvisor` pointing to your agent code. The `codeLocation` is `app/PortfolioAdvisor/` and the `entrypoint` is `main.py`.

::::::expand{header="Understanding the Project Structure"}

Your pre-provisioned workspace at `~/PortfolioAdvisor/` has a specific layout that AgentCore CLI expects:

```
PortfolioAdvisor/
├── agentcore/
│   ├── agentcore.json              # Main configuration (runtimes, gateways, policies, evals)
│   ├── aws-targets.json            # Deployment targets (account, region)
│   ├── .cli/
│   │   └── deployed-state.json     # Tracks deployed resource ARNs (auto-managed)
│   └── cdk/                        # CDK infrastructure (auto-generated, don't edit)
├── app/
│   └── PortfolioAdvisor/
│       ├── main.py                 # Agent entry point (@app.entrypoint async generator)
│       ├── model/
│       │   └── load.py             # Model configuration (Claude Sonnet)
│       ├── mcp_client/
│       │   └── client.py           # Gateway MCP client (commented out until Lab 2)
│       ├── tool/
│       │   ├── portfolio_risk_schema.json   # Tool schema for Gateway target
│       │   └── trade_schema.json            # Tool schema for Gateway target
│       └── pyproject.toml          # Python dependencies (pre-installed)
└── .venv/                          # Virtual environment (pre-built)
```

**Key files:**

- **`agentcore/agentcore.json`** — The single source of truth for what gets deployed. Every lab modifies this file (directly or via CLI commands). It accumulates: runtime config → gateway → auth → policies → evaluations → VPC config.
- **`app/PortfolioAdvisor/main.py`** — The agent itself. Contains the system prompt, local tools, and the `@app.entrypoint` async generator. You'll make exactly TWO code changes across all 6 core labs: uncommenting the MCP client (Lab 2) and adding `extract_user_id` (Lab 3).
- **`app/PortfolioAdvisor/tool/*.json`** — JSON Schema definitions for Gateway tools. These schemas are how the LLM decides WHEN to use each tool and WHAT parameters to pass.
- **`agentcore/.cli/deployed-state.json`** — Starts empty (`{"targets": {}}`). After each `agentcore deploy`, the CLI records deployed resource ARNs here. Don't edit it manually.

::::::

## Step 2: Deploy to AgentCore Runtime

Deploy your agent to the cloud:

:::code{language=bash}
agentcore deploy -y -v
:::

This command:
1. Packages your agent code and dependencies
2. Uploads the package to an S3 bucket
3. Provisions an AgentCore Runtime (serverless container)
4. Creates an endpoint for invocations
5. Configures CloudWatch logging and tracing automatically

:::alert{header="First Deploy" type="info"}
The first deployment takes 3-5 minutes. Subsequent deployments are faster (~2 minutes) because the infrastructure already exists.
:::

Wait for the deployment to complete. You'll see a success message with the runtime ARN.

## Step 3: Verify Deployment

Check the status:

:::code{language=bash}
agentcore status
:::

You should see your `PortfolioAdvisor` runtime in `READY` state.

## Step 4: Invoke Your Agent

Test with a stock analysis query:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What's the current analysis for AAPL? Include price, PE ratio, and recommendation." \
  --session-id $SESSION_ID --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_ID = [guid]::NewGuid().ToString()

agentcore invoke "What's the current analysis for AAPL? Include price, PE ratio, and recommendation." `
  --session-id $SESSION_ID --stream

```
:::
::::

The agent should respond with Apple's stock data — price $178.52, PE ratio 28.4, Buy recommendation.

Try a compliance query:

:::code{language=bash}
agentcore invoke "What are the compliance rules for options trading?" \
  --session-id $SESSION_ID --stream
:::

## Step 5: Explore Observability

Every invocation is automatically instrumented with OpenTelemetry. Let's see the traces.

### Via CLI

View recent logs:

:::code{language=bash}
agentcore logs --runtime PortfolioAdvisor --since 10m
:::

### Via CloudWatch Console

1. Navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Go to **GenAI Observability** → **Bedrock AgentCore**
3. Click on your **PortfolioAdvisor** agent
4. Click on the **DEFAULT** endpoint

You'll see:
- **Traces** — End-to-end invocation traces showing the agent's reasoning
- **Tool calls** — Which tools were invoked and their inputs/outputs
- **Latency** — Response time breakdown (model inference, tool execution)
- **Token usage** — Input and output tokens per invocation

:::alert{header="Screenshot" type="info"}
In the CloudWatch console, you'll see a trace waterfall view with spans for model inference, tool selection, and tool execution — each with timing and input/output data.
:::

## Step 6: Test Session Continuity

Send multiple messages in the same session to verify the agent maintains context:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "I'm interested in tech stocks" \
  --session-id $SESSION_ID --stream

agentcore invoke "Compare the two biggest ones" \
  --session-id $SESSION_ID --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "I'm interested in tech stocks" `
  --session-id $SESSION_ID --stream

agentcore invoke "Compare the two biggest ones" `
  --session-id $SESSION_ID --stream

```
:::
::::

The agent should compare AAPL and MSFT without you needing to specify them again — it remembers the session context.

## Architecture

:::code{language=bash showCopyAction=false}
CLI (agentcore invoke)
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── CloudWatch (traces, logs, metrics — automatic)
:::

## What Just Happened?

With a single `agentcore deploy`, you went from local code to a production-grade cloud deployment:

- **Serverless runtime** — No servers to manage, scales to zero when idle
- **Full observability** — Every invocation traced, logged, and metered automatically
- **Session management** — Built-in session isolation per session-id
- **No infrastructure code** — No Dockerfile, ECR, IAM roles, or CloudFormation to write

---

## Best Practices: Runtime-First Development

:::alert{header="Best Practice" type="info"}
**Deploy to cloud early and iterate there.** Don't spend weeks perfecting a local prototype before discovering cloud-specific issues.
:::

Traditional agent development follows a "local-first" pattern: build locally, test locally, then tackle deployment as a separate project. This creates a gap between what works on your laptop and what works in production — different IAM roles, network policies, timeout behaviors, and observability.

**Runtime-first development** flips this:

1. **Deploy immediately** — Get your agent into AgentCore Runtime on day one, even if it only has one tool
2. **Iterate in production** — Use `agentcore deploy` for fast iteration cycles (~2 minutes per deploy)
3. **Observe from the start** — Cloud traces reveal issues invisible locally: cold start times, model latency under load, token consumption patterns
4. **Fail fast on integration** — Discover IAM, networking, and quota issues early when they're cheap to fix

**When to use local dev (`agentcore dev`):** Rapid prompt engineering, testing new tool logic before deployment, debugging tool input/output formats. But treat it as a supplement, not the primary workflow.

---

### What's Next

Your agent is deployed and responding. In Lab 1B, you'll dive into the observability data AgentCore captures automatically — traces, session isolation, and token metrics.

→ Next: [Lab 1B: Observability Deep Dive](../25-lab1b-observability/)
