---
title: "Lab 4: Production Observability & Session Management"
weight: 52
---

**⏱️ Estimated time: ~15 minutes**

## Instrument everything from day one

One of the most significant mistakes teams can make with observability is treating it as something to add later. By the time you realize you need it, you've already shipped an agent, which can make it harder to debug effectively.

From your first test query, you need visibility into what your agent is doing. AgentCore services emit OpenTelemetry traces automatically. Model invocations, tool calls, and reasoning steps get captured. When a query takes twelve seconds, you can see whether the delay came from the language model, a database query, or an external API call.

The observability strategy should include three layers:

Enable trace-level debugging during development so you can see the steps of each conversation. When users report incorrect behavior, pull up the specific trace and see exactly what the agent did.
Set up dashboards for production monitoring using the Amazon CloudWatch Generative AI observability dashboards that come with AgentCore Observability.
Track token usage, latency percentiles, error rates, and tool invocation patterns. Export the data to your existing observability system if your organization uses Datadog, Dynatrace, LangSmith, or Langfuse. The figure below shows how AgentCore Observability allows you to deep dive into your agent's trace and meta data information inside a session invocation
In the previous labs, you built a portfolio advisor agent (Lab 1), added persistent memory (Lab 2), and centralized tools through AgentCore Gateway (Lab 3). Along the way, your agent was already deployed to AgentCore Runtime — the CLI handled deployment incrementally with each `agentcore deploy`.

In this lab, you'll explore the production capabilities that are already active in your deployed agent:

- **Session continuity** — Multiple conversations with isolated context per session
- **Observability** — Traces, metrics, and logs via CloudWatch GenAI Observability
- **Runtime management** — Status, logs, and traces via the AgentCore CLI

:::alert{header="FSI Security Best Practices" type="warning"}
In financial services, observability and security are not optional — they are regulatory requirements. Key considerations for production FSI deployments:
- **Audit logging** — All agent interactions must be logged for regulatory compliance (SEC, FINRA, MiFID II)
- **Data residency** — Financial data must remain within approved regions and jurisdictions
- **Session isolation** — Multi-tenant environments must ensure complete isolation between client sessions
- **Token-level monitoring** — Track token usage per client/session for cost allocation and anomaly detection
:::

### What's Already Running

By this point, your deployed infrastructure includes:

| Resource | Status | Created In |
|----------|--------|------------|
| AgentCore Runtime | ✅ READY | Lab 2 (first deploy) |
| AgentCore Memory | ✅ Deployed | Lab 2 |
| AgentCore Gateway | ✅ Deployed | Lab 3 |
| CloudWatch Observability | ✅ Active | Automatic with Runtime |

## Step 1: Verify Your Deployment

In Kiro's terminal, check the status of all deployed resources:

:::code{language=bash}
agentcore status
:::

You should see all resources deployed and ready:

:::code{language=bash showCopyAction=false}
AgentCore Status (target: default, us-west-2)

Agents
  PortfolioAdvisor: Deployed - Runtime: READY (arn:aws:bedrock-agentcore:...)

Memories
  SharedMemory: Deployed (SEMANTIC, SUMMARIZATION) (arn:aws:bedrock-agentcore:...)

Gateways
  my-gateway: Deployed (1 target) (portfolioadvisor-my-gateway-...)
:::

## Step 2: Test Session Continuity

AgentCore Runtime provides built-in session management. You pass a `--session-id` with each invocation, and the Runtime keeps conversation context within that session while keeping different sessions completely isolated.

Each session runs in its own microVM, so a single user stays on the same execution environment for the entire conversation — up to 8 hours, which is the maximum session duration for AgentCore Runtime. In practice, there's a one-to-one mapping between a user and their session. Our memory module (from Lab 2) takes advantage of this — it stores and retrieves memories using the combination of `session_id` and `user_id`.

To see session discontinuity in action, we'll start a separate session and show that context from the first one doesn't carry over.

**Start a conversation in Session 1:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_1=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "My name is David and I'm interested in analyzing TSLA for a potential position" \
  --session-id $SESSION_1 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_1 = [guid]::NewGuid().ToString()
agentcore invoke "My name is David and I'm interested in analyzing TSLA for a potential position" `
  --session-id $SESSION_1 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" `
  --stream

```
:::
::::

**Continue the same session:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "What stock was I asking about?" \
  --session-id $SESSION_1 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "What stock was I asking about?" `
  --session-id $SESSION_1 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" `
  --stream

```
:::
::::

Expected: The agent remembers David was asking about TSLA within the same session.

**Start a different session (Session 2):**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_2=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "What stock was I asking about?" \
  --session-id $SESSION_2 \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" \
  --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_2 = [guid]::NewGuid().ToString()
agentcore invoke "What stock was I asking about?" `
  --session-id $SESSION_2 `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: David" `
  --stream

```
:::
::::

Expected: The agent does NOT know what stock was mentioned — this is a completely separate session with no context from Session 1.

> **Note:** Session IDs must be at least 33 characters long. Using UUIDs (as shown above) is the easiest way to generate valid session IDs.

> **How it works:** AgentCore Runtime isolates each session. The `session_id` is passed to the agent's `context` object and used by the memory session manager to scope memory retrieval. Within a session, the agent maintains conversation history. Across sessions, only long-term memory (SEMANTIC facts) is shared.

## Step 3: Explore Observability

AgentCore Runtime automatically instruments your agent with OpenTelemetry and sends traces to CloudWatch. Every invocation generates traces that capture the full conversation flow.

### View Traces via CLI

List recent traces for your agent:

:::code{language=bash}
agentcore traces list --limit 10
:::

Download a specific trace for detailed inspection:

:::code{language=bash}
agentcore traces get <trace-id> --output trace.json
:::

### View Logs via CLI

Stream live logs from your agent:

:::code{language=bash}
agentcore logs
:::

Search for errors in the last hour:

:::code{language=bash}
agentcore logs --since 1h --level error
:::

Search for specific patterns:

:::code{language=bash}
agentcore logs --since 1h --query "portfolio"
:::

### View in CloudWatch Console

For a visual dashboard, navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/):

1. In the left panel, find **GenAI Observability** → **Bedrock AgentCore**
2. Click on **Agents** to see your PortfolioAdvisor agent
3. Click on **Sessions** to see all conversation sessions
4. Click on **Traces** to see detailed request traces

Each trace shows:
- The complete conversation flow (user prompt → tool selection → tool execution → response)
- Latency breakdown for each step
- Memory retrieval and storage operations
- Gateway tool invocations

> **Note:** It takes ~10 minutes after the first invocation for traces to appear in CloudWatch. If you enabled Transaction Search in the prerequisites, traces should already be indexed.

## Architecture

After completing this lab, your deployed architecture includes full observability:

:::code{language=bash showCopyAction=false}
AgentCore Runtime (PortfolioAdvisor)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics)
                      ├── Conversation flow traces
                      ├── Tool invocation timing
                      └── Token usage metrics
:::

## What Just Happened?

You explored three production capabilities that are already active in your deployed agent:

1. **Verified the deployment** — Confirmed that Runtime, Memory, and Gateway are all active and healthy
2. **Tested session continuity** — Demonstrated that conversations are isolated per session while long-term memory (SEMANTIC facts) is shared across sessions
3. **Explored observability** — Used the CLI and CloudWatch console to inspect traces, logs, and the full conversation flow including tool calls

### Session Management

| Feature | How It Works |
|---------|-------------|
| Session isolation | Each `--session-id` creates an independent conversation context |
| Session continuity | Same `--session-id` maintains conversation history |
| Cross-session memory | SEMANTIC facts (names, preferences) are shared across all sessions |
| Session-scoped memory | SUMMARIZATION is scoped to the specific session |

## Congratulations!

Your agent has production-grade observability:

- ✅ **Session management** — Isolated conversations with continuity
- ✅ **Full observability** — Traces, logs, and metrics in CloudWatch
- ✅ **CLI management** — Status, logs, and traces from your terminal

But your agent still accepts unauthenticated requests — anyone with the endpoint URL can invoke it. In the next lab, you'll lock it down with JWT authentication.

### What's Next

In Lab 5, you'll secure your runtime and Gateway with Cognito JWT authentication so only authorized clients can invoke your agent.

→ Next: [Lab 5: Secure with JWT Authentication](../55-lab5-secure-with-auth/)
