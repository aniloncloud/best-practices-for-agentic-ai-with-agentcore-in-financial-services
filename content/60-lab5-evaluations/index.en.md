---
title: "Optional Lab: Evaluations — Agent Quality"
weight: 65
---

**⏱️ Estimated time: ~15 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Labs 1–3 (Deploy to AgentCore Runtime + Connect Tools with Gateway + JWT Auth + Govern Agent Actions with Cedar Policies)
:::

## Overview

Your portfolio advisor agent is deployed with Gateway tools and Cedar-enforced authorization policies. But how do you know if it's performing well? Are clients getting accurate investment analysis? Is the agent selecting the right tools?

In this lab, you'll set up continuous quality monitoring using AgentCore Evaluations — automated assessment of every agent interaction using built-in LLM-as-a-Judge evaluators.

### What You'll Learn

- Configure and deploy online evaluation with built-in evaluators
- Generate test interactions and run on-demand evaluations
- View results via CLI and CloudWatch

### Built-in Evaluators

| Evaluator | Measures |
|-----------|----------|
| **Builtin.GoalSuccessRate** | How well the agent achieves the client's goal |
| **Builtin.Correctness** | Factual accuracy of responses |
| **Builtin.ToolSelectionAccuracy** | Whether the agent picks the right tools |

### How Online Evaluation Works

1. **Sampling** — A configurable percentage of sessions are selected for evaluation
2. **Evaluation** — Built-in evaluators assess each sampled session using LLM-as-a-Judge
3. **Monitoring** — Results flow into CloudWatch GenAI Observability dashboards automatically

### What You're Building

:::code{language=bash showCopyAction=false}
agentcore invoke ──▶ AgentCore Runtime ──▶ Gateway ──▶ Lambda
                         │
                         ▼
              ┌─────────────────────────────────────┐
              │   AgentCore Evaluations             │ ← THIS LAB
              │                                     │
              │   Sampled sessions evaluated by:    │
              │   ├── GoalSuccessRate               │
              │   ├── Correctness                   │
              │   └── ToolSelectionAccuracy          │
              │                                     │
              │   Results → CloudWatch dashboards   │
              └─────────────────────────────────────┘
:::

## Step 1: Refresh Your Token (if needed)

:::alert{header="JWT Token Required" type="warning"}
All invocations require a valid Cognito JWT (`$TOKEN`). If your token has expired or you're in a new terminal, source your environment and re-run the token retrieval commands from Lab 2 before continuing.
:::

:::code{language=bash}
source ~/portfolio-env.sh

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
:::

## Step 2: Configure Online Evaluation

Add an online evaluation configuration that monitors your PortfolioAdvisor agent with all three built-in evaluators:

:::code{language=bash}
agentcore add online-eval \
  --name QualityMonitor \
  --runtime PortfolioAdvisor \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness Builtin.ToolSelectionAccuracy \
  --sampling-rate 100 \
  --enable-on-create
:::

You should see:
:::code{language=bash showCopyAction=false}
Added online eval 'QualityMonitor'
:::

:::alert{header="Sampling Rate" type="info"}
We use `--sampling-rate 100` (100%) for this workshop so every interaction is evaluated. In production, use 10-20% to balance cost and coverage. The `--enable-on-create` flag activates evaluation immediately after the next deployment.
:::

## Step 3: Deploy

Deploy the evaluation configuration alongside your existing runtime resources:

:::code{language=bash}
agentcore deploy -y -v
:::

After deployment, verify the evaluation is active:

:::code{language=bash}
agentcore status
:::

If the status shows `DISABLED`, enable it with:

:::code{language=bash}
agentcore resume online-eval QualityMonitor
:::

## Step 4: Generate Test Interactions

Send five varied queries to give the evaluators representative data to assess:

:::code{language=bash}
SESSION_EVAL=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Stock analysis
agentcore invoke "What's the current analysis for AAPL? What are the key metrics?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Compliance rules
agentcore invoke "What are the compliance rules for options trading? What approvals are needed?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Portfolio risk via Gateway
agentcore invoke "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Multi-tool query
agentcore invoke "I'm looking at TSLA — what's the risk level? Also check the risk for portfolio PORT-005" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# General capabilities
agentcore invoke "What kind of investment analysis can you provide? List your capabilities." \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream
:::

:::alert{header="Processing Delay" type="info"}
Evaluation results take a few minutes to process after interactions are generated. Continue to the next step, then return to view results.
:::

## Step 5: Run On-Demand Evaluation

In addition to continuous online evaluation, you can evaluate historical traces on demand:

:::code{language=bash}
agentcore run eval \
  --runtime PortfolioAdvisor \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness \
  --days 1
:::

This evaluates all traces from the last day using the specified evaluators — useful for retroactive analysis after a system prompt change.

## Step 6: View Results

### Via CLI

View past evaluation run results:

:::code{language=bash}
agentcore evals history --runtime PortfolioAdvisor --limit 5
:::

View streaming evaluation logs:

:::code{language=bash}
agentcore logs evals --runtime PortfolioAdvisor --since 30m
:::

### Via CloudWatch Console

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/) → **GenAI Observability** → **Bedrock AgentCore**
2. Click **PortfolioAdvisor** → **DEFAULT** endpoint
3. Review evaluation scores in the **Sessions** and **Traces** views

### Score Interpretation

| Score Range | Interpretation | Action |
|-------------|---------------|--------|
| 80-100% | Excellent | Monitor and maintain |
| 60-80% | Good but improvable | Review low-scoring sessions |
| Below 60% | Needs attention | Investigate and fix root causes |

**Common improvements by evaluator:**

- **Low Goal Success Rate** → Refine the system prompt; add more specific tool descriptions
- **Low Correctness** → Update market data; improve response formatting
- **Low Tool Selection Accuracy** → Improve tool descriptions; add examples to the system prompt

## Architecture

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Cedar policy enforcement (Lab 3)
    ├── Model + system prompt (stock/compliance reference data)
    └── Gateway tool (by reference) → AgentCore Gateway → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics)
                          ↓
                    AgentCore Evaluations (QualityMonitor)
                      ├── Builtin.GoalSuccessRate
                      ├── Builtin.Correctness
                      └── Builtin.ToolSelectionAccuracy
:::

## What Just Happened?

Two commands added continuous quality monitoring to your production agent:

1. `agentcore add online-eval` — Configure evaluators and sampling rate
2. `agentcore deploy` — Deploy alongside your existing runtime

The evaluators now automatically sample sessions, score them with LLM-as-a-Judge, and store results in CloudWatch — no additional instrumentation code required.

---

## Best Practices: Continuous Quality Monitoring

:::alert{header="Best Practice" type="info"}
**Evaluate early, evaluate often.** Set up evaluation before you have quality problems, not after a client complaint.
:::

**Sampling strategies — cost vs. coverage.** Use 100% sampling for critical flows (regulated advice, trade execution) and 10-20% for high-volume informational queries. Review CloudWatch cost metrics after the first week and adjust.

**Evaluation-driven development.** Baseline scores measured before launch become acceptance criteria. If a system prompt change drops Goal Success Rate by more than 5 points, reject it. Run `agentcore run eval --days 7` before merging any agent configuration change and treat a score regression the same way you'd treat a failing unit test.

**Acting on low scores.** A low score is a signal, not a verdict. Low Goal Success Rate usually points to an unclear system prompt or missing tool coverage. Low Tool Selection Accuracy often means tool descriptions are ambiguous — improve the descriptions before anything else.

**Custom evaluators for domain-specific quality.** Built-in evaluators measure general quality. Production agents often need domain-specific checks: "Did the agent cite relevant policies when discussing a restricted action?" Custom evaluators encode these requirements as scoreable criteria.

**Evaluation as evidence.** Regulators and auditors increasingly expect evidence that AI systems perform within defined bounds. Evaluation scores stored in CloudWatch provide a durable, timestamped record — respond to compliance inquiries with data rather than assertions.

---

### What's Next

→ Continue with: [VPC Networking](../70-lab6-vpc/) | [Memory](../80-optional-memory/) | [Cost Optimization](../88-optional-cost/)
