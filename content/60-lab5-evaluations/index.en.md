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

In this lab, you'll score your agent's real interactions using AgentCore Evaluations — automated assessment with built-in LLM-as-a-Judge evaluators that read the traces your harness already emits to CloudWatch.

### What You'll Learn

- Run an on-demand **batch evaluation** over your agent's recorded sessions
- View per-evaluator scores via the CLI and CloudWatch
- Set up **continuous online evaluation** for production (reference pattern)

### Built-in Evaluators

| Evaluator | Measures |
|-----------|----------|
| **Builtin.GoalSuccessRate** | How well the agent achieves the client's goal |
| **Builtin.Correctness** | Factual accuracy of responses |
| **Builtin.ToolSelectionAccuracy** | Whether the agent picks the right tools |

### How Evaluation Works

AgentCore Evaluations reads the OpenTelemetry traces your harness writes to CloudWatch Logs (the same traces you saw in the Observability lab) and scores sessions with LLM-as-a-Judge — **no instrumentation code and no agent changes**.

- **Batch (on-demand)** — score a set of already-recorded sessions in one job. Great for "evaluate the last day of traffic after a prompt change." *(This lab.)*
- **Online (continuous)** — sample live traffic continuously and stream scores to dashboards. *(Production pattern shown at the end.)*

Both read from the same data source: your harness runtime's CloudWatch log group and OTEL `service.name`.

### What You're Building

:::code{language=bash showCopyAction=false}
agentcore invoke ──▶ AgentCore Harness ──▶ Gateway ──▶ Lambda
                         │
                         ▼  (OTEL traces → CloudWatch Logs)
              ┌─────────────────────────────────────┐
              │   AgentCore Evaluations             │ ← THIS LAB
              │                                     │
              │   Batch job scores sessions with:   │
              │   ├── GoalSuccessRate               │
              │   ├── Correctness                   │
              │   └── ToolSelectionAccuracy          │
              │                                     │
              │   Results → CloudWatch dashboards   │
              └─────────────────────────────────────┘
:::

:::alert{header="Why the AWS CLI here (not agentcore)" type="info"}
The `agentcore` CLI's eval commands target a code-agent **runtime** entry in `agentcore.json`. This workshop uses the declarative **harness**, so we drive evaluations with the `aws bedrock-agentcore` CLI directly against the harness's CloudWatch traces — the same API the SDK uses.
:::

## Step 1: Refresh Your Token (if needed)

:::alert{header="JWT Token Required" type="warning"}
All invocations require a valid Cognito JWT (`$TOKEN`). If your token has expired or you're in a new terminal, source your environment and re-run the token retrieval.
:::

:::code{language=bash}
source ~/portfolio-env.sh

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
:::

## Step 2: Identify Your Deployed Harness

Evaluations read traces from your harness's CloudWatch log group. Capture the runtime ID, log group, and OTEL service name once — the later commands reuse them:

:::code{language=bash}
HARNESS_RUNTIME_ID=$(aws bedrock-agentcore-control list-agent-runtimes --region us-west-2 \
  --query "agentRuntimes[?starts_with(agentRuntimeName, 'harness_PortfolioAdvisor')].agentRuntimeId | [0]" --output text)

LOG_GROUP="/aws/bedrock-agentcore/runtimes/${HARNESS_RUNTIME_ID}-DEFAULT"
SERVICE_NAME="harness_PortfolioAdvisor_PortfolioAdvisor.DEFAULT"

echo "Runtime:  $HARNESS_RUNTIME_ID"
echo "LogGroup: $LOG_GROUP"
echo "Service:  $SERVICE_NAME"
:::

## Step 3: Generate Test Interactions

Send five varied queries so the evaluators have representative sessions to score:

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

:::alert{header="Let traces land first" type="info"}
Traces take 1–2 minutes to appear in CloudWatch. Wait a couple of minutes before starting the evaluation so the job can discover these sessions.
:::

## Step 4: Run an On-Demand (Batch) Evaluation

Start a batch evaluation. The service discovers your sessions from the log group and scores each one with the three built-in evaluators:

:::code{language=bash}
DATA_SOURCE="{\"cloudWatchLogs\":{\"serviceNames\":[\"$SERVICE_NAME\"],\"logGroupNames\":[\"$LOG_GROUP\"]}}"

BATCH_ID=$(aws bedrock-agentcore start-batch-evaluation \
  --batch-evaluation-name "portfolio_eval_$(date +%s)" \
  --evaluators '[{"evaluatorId":"Builtin.GoalSuccessRate"},{"evaluatorId":"Builtin.Correctness"},{"evaluatorId":"Builtin.ToolSelectionAccuracy"}]' \
  --data-source-config "$DATA_SOURCE" \
  --client-token "$(python3 -c 'import uuid; print(uuid.uuid4())')" \
  --region us-west-2 \
  --query 'batchEvaluationId' --output text)

echo "Started batch evaluation: $BATCH_ID"
:::

:::alert{header="No extra IAM setup" type="info"}
Batch evaluation runs as a managed job — no execution role argument is required. The workshop environment already has the permissions it needs.
:::

Poll until the job finishes (`COMPLETED`):

:::code{language=bash}
aws bedrock-agentcore get-batch-evaluation \
  --batch-evaluation-id "$BATCH_ID" --region us-west-2 \
  --query '{status:status,evaluators:evaluators[].evaluatorId}'
:::

Re-run that command until `status` is `COMPLETED` (usually ~1 minute). `PENDING`/`IN_PROGRESS` means it's still running.

## Step 5: View Results

### Via CLI

List recent batch evaluations and their status:

:::code{language=bash}
aws bedrock-agentcore list-batch-evaluations --region us-west-2 \
  --query 'batchEvaluations[].{name:batchEvaluationName,status:status,id:batchEvaluationId}' \
  --output table
:::

Detailed per-session scores are written to a CloudWatch log group. Tail it to see the raw evaluation records:

:::code{language=bash}
aws logs tail "/aws/bedrock-agentcore/evaluations/batch-evaluations/results/default" \
  --since 30m --region us-west-2
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

## Step 6: Continuous Evaluation in Production (reference)

Batch evaluation is on-demand. In production you'd run **online evaluation** to continuously sample live traffic and stream scores to dashboards. It uses the same CloudWatch data source, plus an IAM **evaluation execution role** (the role the managed job assumes to read your logs and call the judge model):

:::code{language=bash showCopyAction=false}
# Reference — requires an evaluation execution role ARN ($EVAL_ROLE_ARN)
aws bedrock-agentcore-control create-online-evaluation-config \
  --online-evaluation-config-name "PortfolioAdvisorQualityMonitor" \
  --rule '{"samplingConfig":{"samplingPercentage":100.0}}' \
  --data-source-config "$DATA_SOURCE" \
  --evaluators '[{"evaluatorId":"Builtin.GoalSuccessRate"},{"evaluatorId":"Builtin.Correctness"},{"evaluatorId":"Builtin.ToolSelectionAccuracy"}]' \
  --evaluation-execution-role-arn "$EVAL_ROLE_ARN" \
  --enable-on-create
:::

Pause or resume a running config at any time:

:::code{language=bash showCopyAction=false}
agentcore pause online-eval PortfolioAdvisorQualityMonitor
agentcore resume online-eval PortfolioAdvisorQualityMonitor
:::

:::alert{header="Sampling rate" type="info"}
Use `samplingPercentage: 100` so every interaction is evaluated in a demo. In production, 10–20% balances cost and coverage for high-volume informational queries; reserve 100% for critical flows (regulated advice, trade execution).
:::

## Architecture

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Harness (PortfolioAdvisor)
    ├── Cedar policy enforcement (Lab 3)
    ├── Model + system prompt (stock/compliance reference data)
    └── Gateway tool (by reference) → AgentCore Gateway → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics)
                          ↓
                    AgentCore Evaluations
                      ├── Batch (on-demand) — this lab
                      └── Online (continuous) — production
                            ├── Builtin.GoalSuccessRate
                            ├── Builtin.Correctness
                            └── Builtin.ToolSelectionAccuracy
:::

## What Just Happened?

You scored your agent's real sessions without changing the agent:

1. `aws bedrock-agentcore start-batch-evaluation` — score recorded sessions from CloudWatch traces with LLM-as-a-Judge
2. `get-batch-evaluation` / `list-batch-evaluations` — track status and results

The harness already emits the traces; evaluations read them. No instrumentation code, no runtime changes.

---

## Best Practices: Continuous Quality Monitoring

:::alert{header="Best Practice" type="info"}
**Evaluate early, evaluate often.** Set up evaluation before you have quality problems, not after a client complaint.
:::

**Sampling strategies — cost vs. coverage.** Use 100% sampling for critical flows (regulated advice, trade execution) and 10-20% for high-volume informational queries. Review CloudWatch cost metrics after the first week and adjust.

**Evaluation-driven development.** Baseline scores measured before launch become acceptance criteria. If a system prompt change drops Goal Success Rate by more than 5 points, reject it. Run a batch evaluation over the last week of traffic before merging any agent configuration change and treat a score regression the same way you'd treat a failing unit test.

**Acting on low scores.** A low score is a signal, not a verdict. Low Goal Success Rate usually points to an unclear system prompt or missing tool coverage. Low Tool Selection Accuracy often means tool descriptions are ambiguous — improve the descriptions before anything else.

**Custom evaluators for domain-specific quality.** Built-in evaluators measure general quality. Production agents often need domain-specific checks: "Did the agent cite relevant policies when discussing a restricted action?" Custom evaluators encode these requirements as scoreable criteria.

**Evaluation as evidence.** Regulators and auditors increasingly expect evidence that AI systems perform within defined bounds. Evaluation scores stored in CloudWatch provide a durable, timestamped record — respond to compliance inquiries with data rather than assertions.

---

### What's Next

→ Continue with: [VPC Networking](../70-lab6-vpc/) | [Memory](../80-optional-memory/) | [Cost Optimization](../88-optional-cost/)
