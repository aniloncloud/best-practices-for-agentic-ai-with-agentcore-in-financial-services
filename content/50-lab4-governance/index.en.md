---
title: "Lab 3: Govern Agent Actions with Cedar Policies"
weight: 40
---

**⏱️ ~16 minutes (one deploy, ~2–3 min — you'll read through it)**

## Overview

Your harness is deployed, has Gateway tools, and is secured with JWT authentication. Authentication answered *"who is calling?"* — but nothing yet answers *"what are they allowed to do?"*

You just watched a 5,000-share MSFT trade go through in Lab 2. The authenticated caller had every right to ask; the agent had every reason to comply. There were no quantity limits, no restricted-ticker checks, no approval gates. Any authenticated user could run that same prompt right now.

**AgentCore Policy** solves this with [Cedar](https://www.cedarpolicy.com/) policies evaluated at the Gateway boundary. Policies are enforced deterministically *outside* the agent's code — the agent can't bypass them, even if tricked by a clever prompt injection attack.

:::alert{header="Compliance Disclaimer" type="warning"}
The compliance rules and trade policies in this workshop are **simulated for educational purposes only** and do not constitute actual regulatory guidance.
:::

### What You're Building

:::code{language=bash showCopyAction=false}
Client (authenticated)
    ↓
AgentCore Harness → AgentCore Gateway (my-gateway)
                                       │
                                       ▼
                         ┌─────────────────────────────┐
                         │  Cedar Policy Engine         │ ← THIS LAB
                         │                             │
                         │  permit: trades < 1000 qty  │
                         │  permit: risk checks (all)  │
                         │  default deny: everything   │
                         │  else blocked               │
                         └─────────────────────────────┘
                                       │
                              allow / deny
                                       ▼
                              Lambda (execute_trade)
:::

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Policy Engine** | Container for Cedar policies that evaluates authorization requests at the Gateway |
| **Cedar Policy** | Declarative rule that permits or forbids tool access based on conditions |
| **ENFORCE mode** | Denied requests are blocked at the Gateway — agent code never runs |
| **Default Deny** | All actions are denied unless an explicit `permit` matches |

---

## Step 1: Create a Policy Engine

```bash
agentcore add policy-engine \
  --name PortfolioAdvisorPolicyEngine \
  --description "Governs portfolio advisor agent tool access — trade limits and tool permissions" \
  --attach-to-gateways my-gateway \
  --attach-mode ENFORCE
```

You should see:

:::code{language=bash showCopyAction=false}
Added policy engine 'PortfolioAdvisorPolicyEngine'
:::

`--attach-mode ENFORCE` means the Gateway will actively block denied requests. An alternative mode, `LOG_ONLY`, lets you observe policy decisions without blocking — useful for validating policies before hardening. More on this in the best-practices section.

---

## Step 2: Write Two Cedar Policies

First, retrieve your Gateway ARN — you'll embed it in each policy statement:

```bash
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways \
  --query "items[?contains(name, 'my-gateway')].gatewayId | [0]" \
  --output text)

GATEWAY_ARN=$(aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --query "gatewayArn" --output text)

echo "Gateway ARN: $GATEWAY_ARN"
```

### Policy 1: Permit trades under 1,000 shares

```bash
agentcore add policy \
  --name trade_quantity_limit \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Allow trades under 1000 shares only" \
  --statement "permit(principal, action == AgentCore::Action::\"ExecuteTrade___execute_trade\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { context.input.quantity < 1000 };"
```

> **Cedar syntax note:** `action == AgentCore::Action::"ExecuteTrade___execute_trade"` — the format is `TargetName___tool_name` with **triple** underscores. `ExecuteTrade` is the gateway target name you registered in Lab 2; `execute_trade` is the Lambda tool name.

### Policy 2: Permit portfolio risk check (all authenticated users)

:::alert{header="Why is this needed?" type="info"}
Cedar uses **default deny**. Once a Policy Engine is attached in ENFORCE mode, *every* tool needs an explicit `permit` to work — including `check_portfolio_risk`, which worked fine before. Without this policy, the risk check would be silently blocked alongside the oversized trade.
:::

```bash
agentcore add policy \
  --name portfolio_risk_check_policy \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Allow all authenticated users to check portfolio risk" \
  --statement "permit(principal, action == AgentCore::Action::\"PortfolioRiskCheck___check_portfolio_risk\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\");" \
  --validation-mode IGNORE_ALL_FINDINGS
```

---

## Step 3: Deploy (your final deploy)

```bash
agentcore deploy -y -v
```

This is your **third and final deploy** of the session. While it runs (~2–3 min), work through the box below.

---

## Step 4: While This Deploys

::::expand{header="Read while the deploy runs (click to open)"}

### Cedar vs. Prompt-Based Rules

The most common governance mistake in agentic AI is writing rules as system-prompt instructions: *"Never execute trades over 1,000 shares."* Here's why that approach fails at production scale:

| Governance via prompt | Governance via Cedar policy |
|-----------------------|-----------------------------|
| LLM interprets the rule probabilistically | Evaluated deterministically, every time |
| Can be bypassed via prompt injection | Cannot be bypassed — evaluated before tool execution |
| No audit trail of enforcement | Every decision logged with full context |
| Changing the rule = changing code = redeploying | Changing the rule = updating policy — no redeploy |
| Agent must "understand" the rule | Agent doesn't even know the rule exists |

The key insight is the last row: Cedar policies operate entirely outside the agent. The Lambda function doesn't know there's a quantity limit. The agent doesn't know either. The Gateway enforces it silently — and logs the decision either way.

:::alert{header="Cost note" type="info"}
Authorization is per-request work, billed per call — so you attach a policy engine where it adds control, not reflexively to every gateway. It's the same "spend where it earns its keep" principle behind the model right-sizing you did in Lab 1 and the harness execution limits (`maxIterations`, `maxTokens`). Deep dive: the per-service cost table in the AgentCore optimization companion guide.
:::

---

### Re-read the Two Policies You Just Submitted

**Policy 1: trade_quantity_limit**

:::code{language=bash showCopyAction=false}
permit(
  principal,
  action == AgentCore::Action::"ExecuteTrade___execute_trade",
  resource == AgentCore::Gateway::"<your-gateway-arn>"
) when { context.input.quantity < 1000 };
:::

- `principal` — any authenticated caller (the Cognito user from the JWT)
- `action` — the specific tool being called, in `TargetName___tool_name` format
- `resource` — scoped to this specific Gateway ARN (policies don't cross gateway boundaries)
- `when { context.input.quantity < 1000 }` — the condition Cedar evaluates against the actual tool input at call time

**Policy 2: portfolio_risk_check_policy**

:::code{language=bash showCopyAction=false}
permit(
  principal,
  action == AgentCore::Action::"PortfolioRiskCheck___check_portfolio_risk",
  resource == AgentCore::Gateway::"<your-gateway-arn>"
);
:::

- `principal` — unconstrained: any caller the Gateway authenticates. In this workshop the harness reaches the Gateway with an **M2M token**, so the principal Cedar sees is the harness's machine client, not the end user (the end-user JWT is validated at the harness inbound layer)
- There is no `when` condition — all risk checks are permitted
- Because Cedar defaults to deny, this explicit permit is what keeps `check_portfolio_risk` working after the policy engine is attached

**What is NOT permitted:** Everything else. Any tool call that doesn't match one of these two permits is blocked. If you added a third Lambda tool to the Gateway tomorrow, it would be silently denied until you wrote a policy for it.

::::

---

## Step 5: The Before/After Moment

### Refresh Your Token

If you've been in the deploy box for a while, your Cognito token may have expired (they're valid 60 min). Refresh it now:

```bash
source ~/portfolio-env.sh

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "Token refreshed"
```

---

### Test 1: Small trade — should succeed ✅

```bash
agentcore invoke --harness PortfolioAdvisor \
  "Execute a trade: buy 500 shares of AAPL at market price for rebalancing" \
  --bearer-token "$TOKEN"
```

Quantity 500 < 1000 — the `trade_quantity_limit` permit matches. The Gateway forwards the request to the Lambda, and the trade executes.

---

### Test 2: The same trade that succeeded in Lab 2 — now denied ❌

:::alert{header="Run this exact prompt — you ran it in Lab 2" type="warning"}
In Lab 2 you ran this prompt and the trade went through. Nothing has changed in the agent code or the Lambda. Only the Cedar policies are new.
:::

```bash
agentcore invoke --harness PortfolioAdvisor \
  "Buy 5000 shares of MSFT at limit price for a large client position" \
  --bearer-token "$TOKEN"
```

The agent calls `execute_trade` with `quantity=5000`. The Gateway evaluates the Cedar policy: `5000 < 1000` is false — no permit matches — default deny applies. The Gateway returns an authorization error. **The Lambda is never invoked.**

The agent will respond with something like: *"I'm unable to execute this trade. The quantity exceeds the authorized per-trade limit."*

Zero lines of agent code changed since Lab 2. The only change was attaching a Cedar policy engine.

---

### Test 3: Portfolio risk check — should still succeed ✅

```bash
agentcore invoke --harness PortfolioAdvisor \
  "Check the portfolio risk for PORT-002" \
  --bearer-token "$TOKEN"
```

The `portfolio_risk_check_policy` permit matches — `check_portfolio_risk` still works for all authenticated users.

---

### What's Happening Behind the Scenes

:::code{language=bash showCopyAction=false}
User: "Buy 5000 shares of MSFT"
    ↓
Agent decides to call execute_trade(ticker="MSFT", quantity=5000, ...)
    ↓
Harness sends the tool request to Gateway (authenticated with an M2M token)
    ↓
Gateway → Policy Engine evaluates Cedar policies
    ↓
Cedar: quantity=5000, policy requires < 1000 → DENY
    ↓
Gateway returns authorization error (Lambda never invoked)
    ↓
Agent tells user: "I cannot execute this trade..."
    ↓
Decision logged to CloudWatch: {action, decision: DENY, matchingPolicy, context.input}
:::

---

## Step 6: Agentic Explainability — Audit Trails

For FSI, it's not enough that the agent works correctly — you need to *prove* it did. Explainability means answering three questions for any interaction:

1. **What did the agent decide to do?** (tool selection reasoning)
2. **Was it allowed?** (policy decision)
3. **Why or why not?** (the policy rule that matched or failed to match)

### View Agent Reasoning Traces

In the CloudWatch GenAI Observability dashboard (**GenAI Observability → Bedrock AgentCore → PortfolioAdvisor → DEFAULT**), each trace shows the agent's tool selection decision, input parameters, and success or failure result.

### View Policy Decisions

Policy decisions are logged at the Gateway. Each entry contains:

| Field | Example |
|-------|---------|
| `action` | `ExecuteTrade___execute_trade` |
| `decision` | `DENY` |
| `matchingPolicy` | `trade_quantity_limit` |
| `context.input` | `{"ticker": "MSFT", "quantity": 5000, ...}` |
| `principal` | M2M client the harness presented (end user logged at harness inbound) |

### Constructing an Audit Record

Join the agent trace with the policy log on `traceId` for a complete per-transaction record:

:::code{language=bash showCopyAction=false}
Audit Record for Trade Attempt:
├── Timestamp: 2025-01-15T14:23:07Z
├── End user (harness inbound JWT): workshopuser@example.com
├── Gateway principal (M2M token): harness machine client
├── Agent Decision: Call execute_trade with quantity=5000, ticker=MSFT
├── Policy Evaluation: DENY (matched policy: trade_quantity_limit)
├── Reason: quantity 5000 >= 1000 (exceeds per-trade limit)
└── Agent Response: "I cannot execute this trade. The quantity exceeds..."
:::

This audit trail is constructed automatically from CloudWatch data — no additional code required.

---

## Finished Early?

### Rung 1: Add a Restricted-Ticker Policy

Firms maintain a **restricted (grey) list** — securities employees can't trade because of a conflict, an active advisory engagement, or an earnings blackout. Suppose your firm is advising on a Goldman Sachs transaction, so **GS** is on the restricted list this quarter — regardless of the fact that the agent's own reference data rates GS a "Buy". Cedar's `forbid` keyword creates an absolute block that overrides any `permit`. Add a third policy:

```bash
agentcore add policy \
  --name restricted_ticker_policy \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Block trades on restricted securities" \
  --statement "forbid(principal, action == AgentCore::Action::\"ExecuteTrade___execute_trade\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { [\"GS\"].contains(context.input.ticker) };" \
  --validation-mode IGNORE_ALL_FINDINGS
```

```bash
agentcore deploy -y -v
```

Then test it — a **small** trade (well under the 1,000-share limit) on the restricted ticker:

```bash
agentcore invoke --harness PortfolioAdvisor \
  "Execute a trade: buy 100 shares of GS at market price" \
  --bearer-token "$TOKEN"
```

Denied — even though 100 < 1000. The agent's reference data even rates GS a "Buy", so it goes ahead and calls `execute_trade`; the Gateway then blocks it because the `forbid` on `GS` overrides the quantity `permit`. **Cedar `forbid` always wins over `permit`** — and it's enforced at the Gateway, not left to the model's judgment.

### Rung 2: Observability Deep Dive

Explore latency tracing, custom metrics, and the CloudWatch GenAI Observability dashboard:

→ [Observability Deep Dive](../25-lab1b-observability/)

### Rung 3: OAuth Token Flows — M2M and Token Lifecycle

Go deeper on machine-to-machine authentication, token exchange with Workload Identity, and multi-agent identity propagation:

→ [Lab 3 (Self-Paced): OAuth Token Flows](../40-lab3-security/)

**Your event account stays available for a limited time after the Summit** — the self-paced labs are available to continue then.

---

## Best Practices: Governance Outside the Agent

:::alert{header="Best Practice" type="info"}
**Enforce business rules deterministically at the Gateway — not in agent prompts.**
:::

**Common governance patterns:**

- **Quantity limits** — `context.input.quantity < 1000` prevents oversized operations
- **Restricted resources** — `forbid ... when { restricted_list.contains(resource_id) }` blocks specific securities or accounts
- **Action type restrictions** — `forbid ... unless { action_type == "read" }` enforces read-only access for certain roles
- **Role-based access** — `principal.getTag("role") == "admin"` for tiered authorization
- **Emergency shutdown** — `forbid(principal, action, resource)` — a single line disables all tool access instantly

**Explainability and audit:**
- Cedar audit logs capture every policy decision with full context (who, what, when, why denied/permitted)
- Combined with agent reasoning traces, you get a complete per-transaction decision record
- Start in `LOG_ONLY` mode to validate policies against real traffic before switching to `ENFORCE` — this prevents accidentally blocking legitimate tools
- Export decision logs to your compliance system via CloudWatch Logs subscription filters for long-term retention

---

## What Just Happened?

You added governance without changing agent code:

1. **Policy Engine** — Container for Cedar authorization rules, attached to the Gateway in ENFORCE mode
2. **Two Cedar policies** — One quantity limit, one blanket permit for risk checks; everything else default-denied
3. **Deterministic enforcement** — The 5,000-share trade was blocked at the Gateway boundary; the Lambda was never invoked
4. **Full audit trail** — Every policy decision is logged with who, what, and why — automatically, with no extra code

---

→ Next: you've completed the live session. Continue with the [self-paced labs](../25-lab1b-observability/) — or jump to the [Summary](../90-summary/).

---

::::expand{header="Troubleshooting: policy engine shows as not attached"}

If Test 2 (the 5,000-share trade) is **not** denied after deploying, the policy engine may not have attached to the gateway during the CDK deploy. Run these four commands, then retest:

```bash
# 1. Get the gateway role name
GATEWAY_ROLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name AgentCore-PortfolioAdvisor-default \
  --query "StackResources[?ResourceType=='AWS::IAM::Role' && contains(LogicalResourceId, 'McpGateway')].PhysicalResourceId | [0]" \
  --output text)

# 2. Grant the gateway role permission to call the policy engine
aws iam put-role-policy \
  --role-name $GATEWAY_ROLE_NAME \
  --policy-name PolicyEngineAccess \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:CheckAuthorizePermissions","bedrock-agentcore:IsAuthorized","bedrock-agentcore:IsAuthorizedWithToken","bedrock-agentcore:GetPolicyEngine"],"Resource":"*"}]}'

# 3. Get the policy engine ARN and gateway ID
PE_ARN=$(aws cloudformation describe-stacks \
  --stack-name AgentCore-PortfolioAdvisor-default \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'PolicyEngine') && contains(OutputKey, 'Arn')].OutputValue | [0]" \
  --output text)

GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name AgentCore-PortfolioAdvisor-default \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'GatewayMyGatewayId')].OutputValue | [0]" \
  --output text)

# 4. Attach the policy engine to the gateway
aws bedrock-agentcore-control update-gateway \
  --gateway-identifier $GATEWAY_ID \
  --policy-engine-configuration "{\"arn\":\"${PE_ARN}\",\"mode\":\"ENFORCE\"}"

echo "Policy engine attached to gateway: $GATEWAY_ID"
```

After running these commands, re-run Test 2 — the 5,000-share trade should now be denied.

::::
