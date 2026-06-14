---
title: "Optional Lab: Observability Deep Dive"
weight: 50
---

**⏱️ Estimated time: ~15 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Lab 1 (Deploy to AgentCore Runtime)
:::

## Overview

In Lab 1, you deployed and invoked your agent. In this lab, you'll dig into what happened under the hood — examining traces, testing session isolation, and understanding the observability data that AgentCore captures automatically.

For FSI, observability isn't a nice-to-have — it's a regulatory requirement. SEC Rule 17a-4, FINRA Rule 3110, and SOX all require that AI interactions are logged and auditable. This lab shows you what's already being captured and how to access it.

### What You'll Learn

- Inspect end-to-end traces for individual invocations
- Test session isolation (context stays within a session, doesn't leak across sessions)
- Navigate the CloudWatch GenAI Observability dashboard
- Understand the three-layer observability model (traces, dashboards, evaluations)

### What You're Exploring

:::code{language=bash showCopyAction=false}
agentcore invoke ──▶ AgentCore Runtime (PortfolioAdvisor)
                         │
                         ▼
              ┌─────────────────────────────────────┐
              │   CloudWatch GenAI Observability     │ ← THIS LAB
              │                                     │
              │   ├── Traces (span waterfall)       │
              │   ├── Session isolation (A ≠ B)     │
              │   └── Metrics (tokens, latency)     │
              └─────────────────────────────────────┘
:::

## Step 1: Inspect a Trace

Every `agentcore invoke` produces a trace in CloudWatch. The managed harness streams its runtime logs to a CloudWatch log group. (`agentcore logs` targets code-agent *runtimes* only — this project is a harness, so we read the harness log group directly.) Capture the harness runtime ID once, then tail its logs:

:::code{language=bash}
HARNESS_RUNTIME_ID=$(aws bedrock-agentcore-control list-agent-runtimes --region us-west-2 \
  --query "agentRuntimes[?starts_with(agentRuntimeName, 'harness_PortfolioAdvisor')].agentRuntimeId | [0]" --output text)

aws logs tail "/aws/bedrock-agentcore/runtimes/${HARNESS_RUNTIME_ID}-DEFAULT" --since 15m --region us-west-2
:::

Each trace captures:

| Span | What It Shows |
|------|---------------|
| **Invocation** | User prompt, session ID, total latency |
| **Model inference** | Tokens in/out, model latency, which model was used |
| **Tool selection** | The agent's reasoning about which tool to call |
| **Tool execution** | Tool name, input parameters, output, execution time |
| **Response synthesis** | Final response construction, output tokens |

### Via CloudWatch Console

For a visual trace view:

1. Navigate to [CloudWatch console](https://console.aws.amazon.com/cloudwatch/) → **GenAI Observability** → **Bedrock AgentCore**
2. Click on **PortfolioAdvisor** → **DEFAULT** endpoint
3. Click on a recent session to see its traces
4. Click on a specific trace to see the span waterfall

The span waterfall shows the entire invocation timeline — model inference, tool calls, and response generation — with latency breakdown for each step.

:::alert{header="Trace Ingestion Delay" type="info"}
Traces take 1-2 minutes to appear in CloudWatch after an invocation. If you don't see traces, wait and refresh.
:::

## Step 2: Test Session Isolation

### How Sessions Work

AgentCore Runtime provides built-in session isolation. Before testing it, understand the model:

| Concept | How It Works |
|---------|-------------|
| **Session ID** | Unique identifier (min 33 characters) passed with each invocation. UUIDs work well. |
| **Session isolation** | Each session has its own conversation context. Session A cannot see Session B's messages. |
| **Session continuity** | Within a session, the agent maintains full conversation history. "What stock was I asking about?" works. |
| **MicroVM per session** | Each session runs in its own execution environment. No shared state between sessions. |
| **8-hour maximum** | Sessions can last up to 8 hours before requiring a new session ID. |

Sessions are isolated — context in one session doesn't leak to another. This is critical for multi-tenant FSI applications where different clients share the same agent.

**Start Session A:**

:::code{language=bash}
SESSION_A=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "My name is Sarah and I'm interested in analyzing TSLA for a large position" \
  --session-id $SESSION_A --stream
:::

**Verify Session A has context:**

:::code{language=bash}
agentcore invoke "What stock was I asking about?" \
  --session-id $SESSION_A --stream
:::

Expected: The agent remembers TSLA — it has conversation history within Session A.

**Start Session B (completely separate):**

:::code{language=bash}
SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What stock was I asking about?" \
  --session-id $SESSION_B --stream
:::

Expected: The agent does NOT know — Session B is a completely independent conversation with no context from Session A.

### Why This Matters for FSI

In a multi-client deployment:
- Client A's portfolio discussions cannot appear in Client B's session
- Each session runs in its own microVM — hardware-level isolation
- Session IDs map 1:1 to user sessions (one user, one session)
- No shared state between sessions unless explicitly wired through Memory (Optional Memory lab)

## Step 3: Examine Tool Call Traces

Send a multi-tool query and observe how the agent selects tools:

:::code{language=bash}
SESSION_TRACE=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "I want to buy 200 shares of TSLA. What's the current risk profile and what compliance rules apply for margin trading?" \
  --session-id $SESSION_TRACE --stream
:::

In the trace, you'll see two tool execution spans:
1. `get_stock_analysis("TSLA")` — risk level, analyst rating
2. `get_compliance_rules("margin_trading")` — leverage limits, approval level, restrictions

The agent selected both tools because the query asked about both risk and compliance. This tool selection decision is what the `ToolSelectionAccuracy` evaluator measures in the Evaluations lab.

### View the trace detail:

:::code{language=bash}
aws logs tail "/aws/bedrock-agentcore/runtimes/${HARNESS_RUNTIME_ID}-DEFAULT" --since 5m --region us-west-2
:::

(`HARNESS_RUNTIME_ID` was set in Step 1. If your shell was reset, re-run the `list-agent-runtimes` line from Step 1 to repopulate it.)

Look for:
- **Tool selection reasoning** — The model's internal decision about which tools to call
- **Tool inputs** — Exact parameters passed to each tool
- **Tool outputs** — What each tool returned
- **Response synthesis** — How the agent combined both results into a coherent answer

## Step 4: Understand Token Usage

Each trace includes token metrics:

| Metric | What It Tells You |
|--------|-------------------|
| **Input tokens** | Tokens sent to the model (system prompt + conversation history + tool results) |
| **Output tokens** | Tokens generated by the model (reasoning + response) |
| **Total tokens** | Combined cost driver — this is what you pay for |
| **Tool call tokens** | Additional tokens used for tool selection reasoning |

In the CloudWatch dashboard (**GenAI Observability** → **PortfolioAdvisor** → **DEFAULT**), token metrics are aggregated across all sessions. Watch for:
- Sessions with unusually high token counts (potential prompt injection or conversation loops)
- Steady growth in input tokens within a session (conversation history accumulates)
- Token spikes after system prompt changes (a common cause of cost regressions)

:::alert{header="FSI Cost Allocation" type="info"}
For financial services, token usage often needs to be allocated per client or per desk. The session ID in each trace makes this possible — aggregate token metrics by session, then map sessions to client IDs via your identity system.
:::

## Step 5: Observability Checklist

Before moving on, confirm you can access all three observability surfaces:

| Surface | How to Access | What It Shows |
|---------|---------------|---------------|
| **CLI logs** | `aws logs tail "/aws/bedrock-agentcore/runtimes/${HARNESS_RUNTIME_ID}-DEFAULT" --since 15m` | Recent invocation logs, errors, warnings |
| **CloudWatch traces** | Console → GenAI Observability → PortfolioAdvisor | Span waterfall, latency breakdown, tool calls |
| **CloudWatch metrics** | Console → GenAI Observability → PortfolioAdvisor → Metrics | Token usage, invocation count, error rate |

All three are active automatically — no additional configuration was needed. This is the baseline observability that every AgentCore deployment gets for free.

## Architecture

:::code{language=bash showCopyAction=false}
CLI (agentcore invoke)
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── Session management (isolated per session-id)
    └── OpenTelemetry instrumentation (automatic)
              ↓
        CloudWatch GenAI Observability
          ├── Traces (span waterfall per invocation)
          ├── Metrics (tokens, latency, error rate)
          └── Logs (structured JSON per invocation)
:::

## What Just Happened?

You explored the observability data that AgentCore captures automatically for every invocation:

1. **Traces** — End-to-end span waterfall showing model inference, tool selection, and tool execution
2. **Session isolation** — Proved that sessions are independent (Session A's context doesn't leak to Session B)
3. **Token metrics** — Understood what drives cost and how to allocate it per-client
4. **Three surfaces** — CLI logs for quick checks, CloudWatch traces for debugging, CloudWatch metrics for dashboards

---

## Best Practices: Instrument Everything from Day One

:::alert{header="Best Practice" type="info"}
**Never ship an agent without observability. By the time you realize you need it, you've already shipped something you can't debug.**
:::

**The three-layer observability model:**

| Layer | Purpose | When You Need It |
|-------|---------|-----------------|
| **Traces** | Debug individual invocations | When a user reports a bad response |
| **Dashboards** | Monitor aggregate health | Every day — is the agent performing normally? |
| **Evaluations** | Measure quality over time | Before and after every change (Evaluations lab) |

**What to monitor in production:**

| Signal | Threshold | Action |
|--------|-----------|--------|
| Error rate | > 5% | Investigate tool failures or model timeouts |
| p95 latency | > 15s | Check model congestion or tool backend health |
| Token usage per session | > 50K | Look for conversation loops or prompt injection attempts |
| Tool selection accuracy | < 80% | Improve tool descriptions or system prompt |

**Session ID as audit key:**

The session ID is the primary key for audit. Design your system so that:
- Each human user maps to exactly one session per conversation
- Session IDs are logged in your client application alongside user identity
- Compliance can query "show me all interactions for user X on date Y" by filtering traces on session ID

**Export to existing observability systems:**

If your organization uses Datadog, Dynatrace, Splunk, or LangSmith, CloudWatch traces can be streamed via subscription filters to Kinesis Data Firehose and forwarded to your existing tool. AgentCore doesn't lock you into CloudWatch-only observability.

---

### What's Next

You've now seen the full observability story behind the agent you hardened in the live session. Keep going with the other self-paced labs:

→ Continue with: [Enterprise Tool Registry](../35-lab2b-tool-registry/) | [Evaluations](../60-lab5-evaluations/) | [VPC Networking](../70-lab6-vpc/)
