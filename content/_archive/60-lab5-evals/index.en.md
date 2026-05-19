---
title: "Lab 6: Evaluating Agent Quality"
weight: 62
---

**⏱️ Estimated time: ~15 minutes**

## Overview

Your portfolio advisor agent is deployed and running in production with full observability. But how do you know if it's actually performing well? Are clients getting accurate investment analysis? Is the agent selecting the right tools?

In this lab, you'll set up continuous quality monitoring using AgentCore Evaluations. This automatically assesses your agent's performance on every interaction (or a sample) using built-in evaluators.

### What You'll Learn

- Configure online evaluation with built-in evaluators
- Generate test interactions to populate evaluation data
- Run on-demand evaluations against historical traces
- View evaluation results via CLI and CloudWatch

### How Online Evaluation Works

Online evaluation continuously monitors your deployed agent in production:

1. **Sampling** — A configurable percentage of sessions are selected for evaluation
2. **Evaluation** — Built-in or custom evaluators assess each sampled session
3. **Monitoring** — Results appear in CloudWatch GenAI Observability dashboards

| Built-in Evaluator | What It Measures |
|-------------------|-----------------|
| **Builtin.GoalSuccessRate** | How well the agent achieves the client's goal |
| **Builtin.Correctness** | Factual accuracy of responses |
| **Builtin.ToolSelectionAccuracy** | Whether the agent picks the right tools |

## Step 1: Create Online Evaluation Configuration

In Kiro's terminal, add an online evaluation config that monitors your PortfolioAdvisor agent with all three built-in evaluators:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add online-eval \
  --name QualityMonitor \
  --runtime PortfolioAdvisor \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness Builtin.ToolSelectionAccuracy \
  --sampling-rate 100 \
  --enable-on-create
```
:::
:::tab{label="Windows"}
```powershell
agentcore add online-eval `
  --name QualityMonitor `
  --runtime PortfolioAdvisor `
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness Builtin.ToolSelectionAccuracy `
  --sampling-rate 100 `
  --enable-on-create

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added online eval 'QualityMonitor'
:::

> **Note:** We use `--sampling-rate 100` (100%) for this workshop so every interaction is evaluated. In production, you'd typically use 10-20% to balance cost and coverage. The `--enable-on-create` flag activates evaluation immediately after deployment.

## Step 2: Deploy the Evaluation Configuration

:::code{language=bash}
agentcore deploy -y -v
:::

This deploys the online evaluation configuration alongside your existing resources. The evaluators will start monitoring new interactions automatically.

After deployment, verify the evaluation is active:

:::code{language=bash}
agentcore status
:::

If the status shows `DISABLED`, enable it with:

:::code{language=bash}
agentcore resume online-eval QualityMonitor
:::

## Step 3: Generate Test Interactions

Since the runtime is now secured with Cognito (Lab 5), make sure you have a valid token. If your token has expired or you're in a new terminal session, retrieve it again:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
# Skip this block if $TOKEN is still set from Lab 5
COGNITO_POOL_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/pool_id \
  --query 'Parameter.Value' --output text)

COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "Token obtained successfully"
```
:::
:::tab{label="Windows"}
```powershell
# Skip this block if $TOKEN is still set from Lab 5
$COGNITO_POOL_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/pool_id `
  --query 'Parameter.Value' --output text

$COGNITO_WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/web_client_id `
  --query 'Parameter.Value' --output text

$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

Write-Host "Token obtained successfully"

```
:::
::::

In Kiro's terminal, let's generate varied interactions to give the evaluators something to assess:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_EVAL=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Stock analysis query
agentcore invoke "What's the current analysis for AAPL? What are the key metrics?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Compliance rules query
agentcore invoke "What are the compliance rules for options trading? What approvals are needed?" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Portfolio risk check (via Gateway)
agentcore invoke "Check the portfolio risk for PORT-001" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Multi-tool query
agentcore invoke "I'm looking at TSLA — what's the risk level? Also check the risk for portfolio PORT-005" \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# General capability query
agentcore invoke "What kind of investment analysis can you provide? List your capabilities." \
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_EVAL = [guid]::NewGuid().ToString()

# Stock analysis query
agentcore invoke "What's the current analysis for AAPL? What are the key metrics?" `
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Compliance rules query
agentcore invoke "What are the compliance rules for options trading? What approvals are needed?" `
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Portfolio risk check (via Gateway)
agentcore invoke "Check the portfolio risk for PORT-001" `
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# Multi-tool query
agentcore invoke "I'm looking at TSLA — what's the risk level? Also check the risk for portfolio PORT-005" `
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

# General capability query
agentcore invoke "What kind of investment analysis can you provide? List your capabilities." `
  --session-id $SESSION_EVAL --bearer-token "$TOKEN" --stream

```
:::
::::

> **Note:** Evaluation results take a few minutes to process after interactions are generated.

## Step 4: Run On-Demand Evaluation

In addition to continuous online evaluation, you can run evaluations on-demand against historical traces:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore run eval \
  --runtime PortfolioAdvisor \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness \
  --days 1
```
:::
:::tab{label="Windows"}
```powershell
agentcore run eval `
  --runtime PortfolioAdvisor `
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness `
  --days 1

```
:::
::::

This evaluates all traces from the last day using the specified evaluators.

## Step 5: View Evaluation Results

### Via CLI

View past evaluation run results:

:::code{language=bash}
agentcore evals history --runtime PortfolioAdvisor --limit 5
:::

View online evaluation logs:

:::code{language=bash}
agentcore logs evals --runtime PortfolioAdvisor --since 30m
:::

### Via CloudWatch Console

For a visual dashboard with trends and detailed scores:

1. Navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Go to **GenAI Observability** → **Bedrock AgentCore**
3. Click on your **PortfolioAdvisor** agent
4. Click on the **DEFAULT** endpoint
5. Look for evaluation scores in the **Sessions** and **Traces** views

The dashboard shows:
- **Goal Success Rate** — Are clients getting accurate investment guidance?
- **Correctness** — Is the information accurate?
- **Tool Selection Accuracy** — Is the agent using the right tools?

## Step 6: Understanding and Acting on Results

### What the Scores Mean

| Score Range | Interpretation | Action |
|------------|---------------|--------|
| 80-100% | Excellent | Monitor and maintain |
| 60-80% | Good but improvable | Review low-scoring sessions |
| Below 60% | Needs attention | Investigate and fix root causes |

### Common Improvements

- **Low Goal Success Rate** → Refine the system prompt, add more specific tool descriptions
- **Low Correctness** → Update market data, improve analysis formatting
- **Low Tool Selection** → Improve tool descriptions, add examples to the system prompt

## Step 7: Pause/Resume Evaluation (Optional)

You can pause online evaluation to reduce costs or during maintenance:

:::code{language=bash}
# Pause
agentcore pause online-eval QualityMonitor

# Resume
agentcore resume online-eval QualityMonitor
:::

## Architecture

After completing this lab, your deployed architecture includes continuous evaluation:

![Lab 6 Architecture](/static/60-lab5-evals/lab5_architecture_diagram.png)

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway (secured) → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics)
                          ↓
                    AgentCore Evaluations (QualityMonitor)
                      ├── Builtin.GoalSuccessRate
                      ├── Builtin.Correctness
                      └── Builtin.ToolSelectionAccuracy
:::

## What Just Happened?

With the AgentCore CLI, setting up continuous quality monitoring required just two commands:

1. `agentcore add online-eval` — Configure what to evaluate and how
2. `agentcore deploy` — Deploy the configuration

The evaluators now automatically:
- Sample sessions based on your configured rate
- Apply built-in LLM-as-a-Judge evaluators to each sampled session
- Store results in CloudWatch for analysis
- Enable trend tracking over time

## Congratulations!

Your PortfolioAdvisor agent now has continuous quality monitoring:

- ✅ **Online evaluation** — Automatic assessment of every interaction
- ✅ **Built-in evaluators** — Goal success, correctness, and tool selection
- ✅ **On-demand evaluation** — Run evaluations against historical traces
- ✅ **CLI management** — View results, pause/resume from your terminal

### What's Next

In Lab 7, you'll build a client-facing portal interface using Flask so clients can interact with your portfolio advisor through a web browser.

→ Next: [Lab 7: Build Client Portal Interface](../70-lab6-frontend/)
