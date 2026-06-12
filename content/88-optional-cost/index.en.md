---
title: "Optional Lab: Cost Optimization"
weight: 88
---

**Optional** — This lab optimizes session lifecycle, evaluation sampling, and token monitoring for production FSI workloads. Skip it if you're short on time and continue to the Summary.

**⏱️ Estimated time: ~15 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays live**, so you can continue later today. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Labs 1–3 + Evaluations lab completed (deployed agent with evaluations configured)
:::

## Overview

Your portfolio advisor is deployed, secured, and evaluated — but in production, cost management is just as critical as functionality. High-frequency advisory interactions during market hours can drive unpredictable invocation spikes, and without tuning you'll pay for idle sessions, unnecessary evaluation overhead, and untracked token consumption.

### What You'll Learn

- Configure session idle timeout and max lifetime to free resources faster
- Reduce evaluation sampling from 100% to 20% for production-appropriate coverage
- Build a CloudWatch dashboard to track token usage and invocation costs

:::alert{header="FSI Cost Considerations" type="info"}
- **High-frequency interactions** during market hours drive unpredictable invocation spikes
- **Regulatory retention** requirements (SEC Rule 17a-4, MiFID II) may conflict with cost-optimal storage settings
- **Budget governance** requires per-team tagging and token-level visibility
- **Chargebacks** demand metrics broken down by business unit
:::

### What You're Optimizing

:::code{language=bash showCopyAction=false}
┌──────────────────────────────────────────────────────┐
│  Cost Levers  ← THIS LAB                            │
│                                                      │
│  1. Session lifecycle                                │
│     idle timeout: 15 min → 5 min                     │
│     max lifetime: 8 hr → 2 hr                        │
│                                                      │
│  2. Evaluation sampling                              │
│     100% → 20% (production-appropriate)              │
│                                                      │
│  3. Token monitoring dashboard                       │
│     input/output tokens per session                  │
│     cost allocation by session ID                    │
└──────────────────────────────────────────────────────┘
:::

## Step 1: Configure Session Lifecycle

Sessions hold agent state (conversation history, tool context) in memory. Idle sessions waste resources. The defaults — 15-minute idle timeout, 8-hour max lifetime — are generous for a workshop but expensive in production.

:::alert{header="CLI exception: session lifecycle parameters" type="warning"}
Session lifecycle parameters are not exposed as CLI flags. You must edit `agentcore/agentcore.json` directly.
:::

Open `agentcore/agentcore.json` in Kiro's editor and add a `sessionConfig` block **inside** your runtime configuration:

:::code{language=json}
"sessionConfig": {
  "idleRuntimeSessionTimeout": 300,
  "maxLifetime": 3600
}
:::

The full runtime block should look like:

:::code{language=json showCopyAction=false}
"runtimes": [
  {
    "name": "PortfolioAdvisor",
    "entrypoint": "main.py",
    "codeLocation": "app/PortfolioAdvisor/",
    "sessionConfig": {
      "idleRuntimeSessionTimeout": 300,
      "maxLifetime": 3600
    }
  }
]
:::

| Parameter | Value | Default | Rationale |
|-----------|-------|---------|-----------|
| `idleRuntimeSessionTimeout` | 300s (5 min) | 900s (15 min) | Advisory sessions occur in rapid bursts — 5 minutes covers most inter-message gaps |
| `maxLifetime` | 3600s (1 hour) | 28800s (8 hours) | Shorter max lifetime reduces compliance exposure window |

> **Cost impact:** Reducing idle timeout from 15 to 5 minutes frees session resources 3x faster during quiet periods between client interactions.

Deploy the updated configuration:

:::code{language=bash}
agentcore validate
agentcore deploy -y -v
:::

## Step 2: Reduce Evaluation Sampling Rate

In the Evaluations lab you configured 100% evaluation sampling — useful for testing, expensive in production. Reduce it to 20%.

:::code{language=bash}
# Remove the existing evaluation config (cannot re-add with the same name)
agentcore remove online-eval --name QualityMonitor -y

# Re-add with 20% sampling
agentcore add online-eval \
  --name QualityMonitor \
  --runtime PortfolioAdvisor \
  --evaluator Builtin.GoalSuccessRate Builtin.Correctness Builtin.ToolSelectionAccuracy \
  --sampling-rate 20 \
  --enable-on-create

agentcore deploy -y -v
:::

> **Cost impact:** Reducing sampling from 100% to 20% cuts evaluation costs by 80% while maintaining statistical significance. For 1,000+ daily interactions, 20% gives you 200+ evaluated samples per day — more than enough for reliable quality signals.

### Sampling Rate Guidelines

| Daily Interactions | Recommended Sampling | Rationale |
|-------------------|---------------------|-----------|
| < 100 | 100% | Low volume — evaluate everything |
| 100–1,000 | 20–50% | Moderate — 20% provides statistical significance |
| 1,000–10,000 | 10–20% | High volume — 10% gives 100–200 daily samples |
| > 10,000 | 5–10% | Very high — 5% still yields 500+ daily samples |

## Step 3: Monitor Token Usage

Token usage is the primary cost driver. Use the AWS CLI to query consumption from the `Bedrock-AgentCore` CloudWatch namespace:

:::code{language=bash}
# Invocations for the last hour
START_TIME=$(python3 -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'))")
END_TIME=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'))")

aws cloudwatch get-metric-statistics \
  --namespace "AWS/Bedrock-AgentCore" \
  --metric-name "Invocations" \
  --start-time $START_TIME \
  --end-time $END_TIME \
  --period 300 \
  --statistics Sum Average Maximum \
  --output table
:::

:::alert{header="Typical token ranges per invocation" type="info"}
| Metric | Typical range | Cost driver |
|--------|--------------|-------------|
| Input tokens | 1,000–5,000 | System prompt + conversation history + tool results |
| Output tokens | 200–1,500 | Agent response + tool call parameters |
| Tool calls per turn | 1–3 | Gateway invocations (Lambda, API calls) |

**System prompt tip:** Every token in the system prompt is sent on every invocation. A concise system prompt with identical behavior can reduce per-invocation input costs by 20–40%.
:::

## Step 4: Build a Cost Monitoring Dashboard

Create a CloudWatch dashboard to track token consumption and invocation count over time:

:::code{language=bash}
aws cloudwatch put-dashboard \
  --dashboard-name "PortfolioAdvisor-CostMonitor" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "title": "Invocations and Duration",
          "metrics": [
            ["AWS/Bedrock-AgentCore", "Invocations",  {"stat": "Sum", "period": 3600}],
            ["AWS/Bedrock-AgentCore", "Duration", {"stat": "Average", "period": 3600}]
          ],
          "view": "timeSeries",
          "region": "us-west-2",
          "period": 3600
        }
      },
      {
        "type": "metric",
        "x": 12, "y": 0, "width": 12, "height": 6,
        "properties": {
          "title": "Invocation Count",
          "metrics": [
            ["AWS/Bedrock-AgentCore", "Invocations", {"stat": "Sum", "period": 3600}]
          ],
          "view": "timeSeries",
          "region": "us-west-2",
          "period": 3600
        }
      },
      {
        "type": "metric",
        "x": 0, "y": 6, "width": 12, "height": 6,
        "properties": {
          "title": "Errors and Spend",
          "metrics": [
            ["AWS/Bedrock-AgentCore", "Errors",  {"stat": "Sum", "period": 3600}],
            ["AWS/Bedrock-AgentCore", "SpendAmount", {"stat": "Sum", "period": 3600}]
          ],
          "view": "timeSeries",
          "region": "us-west-2",
          "period": 3600
        }
      }
    ]
  }'
:::

Open the dashboard in the CloudWatch console:

:::code{language=bash showCopyAction=false}
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards/dashboard/PortfolioAdvisor-CostMonitor
:::

## Architecture After This Lab

:::code{language=bash showCopyAction=false}
AgentCore Runtime (PortfolioAdvisor)
    ├── Session lifecycle: idle=5min, max=1hr
    ├── Evaluations: 20% sampling (QualityMonitor)
    └── All metrics → CloudWatch (Bedrock-AgentCore namespace)
                          ↓
              PortfolioAdvisor-CostMonitor dashboard
                ├── Token usage (input / output, hourly)
                ├── Invocation count (hourly)
                └── Average tokens per invocation
:::

## FSI Cost Optimization Best Practices

:::alert{header="Production checklist" type="info"}
- **Right-size session timeouts** — Match to actual usage patterns: shorter during market-hours bursts, consider longer for end-of-day analysis workflows
- **Evaluation sampling** — Start at 20%; increase if quality issues appear, decrease when quality is stable
- **System prompt hygiene** — Every token sent on every invocation; keep instructions concise without sacrificing behavioral clarity
- **Memory tiering** — Use AgentCore Memory for active data; archive to S3 with lifecycle policies for regulatory retention (SEC 17a-4, MiFID II require 3–7 years)
- **Cost allocation tags** — Tag runtime, gateway, and memory resources for accurate chargeback to business units
- **Budget alarms** — Set CloudWatch billing alarms to detect unexpected spikes during market volatility events
:::

## What You Accomplished

| Optimization | Before | After | Impact |
|-------------|--------|-------|--------|
| Idle session timeout | 15 min | 5 min | 3x faster resource release during quiet periods |
| Max session lifetime | 8 hours | 1 hour | Reduced compliance exposure window |
| Evaluation sampling | 100% | 20% | 80% reduction in evaluation invocation costs |
| Token visibility | None | CloudWatch dashboard | Data-driven cost decisions |

---

→ Next: [Summary](../90-summary/)
