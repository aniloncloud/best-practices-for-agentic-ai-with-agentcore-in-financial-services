---
title: "Lab 4: Govern Agent Actions with Policies"
weight: 52
---

**⏱️ Estimated time: ~25 minutes**

## Overview

Your agent is deployed, has Gateway tools, and is secured with JWT authentication. But authentication only answers *"who is calling?"* — it doesn't answer *"what are they allowed to do?"*

Should every authenticated user be able to execute trades of any size? What if a client asks the agent to buy 10,000 shares? Without governance, the agent will comply — it has no concept of business rules or position limits.

**AgentCore Policy** solves this with [Cedar](https://www.cedarpolicy.com/) policies at the Gateway boundary. Policies are evaluated deterministically *outside* the agent's code — the agent can't bypass them, even if tricked by a clever prompt.

### What You'll Learn

- Create a Policy Engine and attach it to your Gateway
- Write Cedar policies that restrict tool usage based on input parameters
- Test policy enforcement via CLI (allowed trades succeed, oversized trades denied)
- Surface agent reasoning and policy decisions for audit trails

:::alert{header="Compliance Disclaimer" type="warning"}
The compliance rules and trade policies in this workshop are **simulated for educational purposes only** and do not constitute actual regulatory guidance.
:::

### What You're Building

:::code{language=bash showCopyAction=false}
Client (authenticated)
    ↓
AgentCore Runtime → MCP Client → AgentCore Gateway
                                       │
                                       ▼
                         ┌─────────────────────────────┐
                         │  Cedar Policy Engine         │ ← THIS LAB
                         │                             │
                         │  permit: trades ≤ 1000 qty  │
                         │  forbid: restricted tickers │
                         │  forbid: large trades       │
                         └─────────────────────────────┘
                                       │
                              allow / deny
                                       ▼
                              Lambda (execute_trade)
:::

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Policy Engine** | Container for Cedar policies that evaluates authorization requests |
| **Cedar Policy** | Declarative rule that permits or forbids tool access based on conditions |
| **ENFORCE mode** | Denied requests are blocked at the Gateway |
| **Default Deny** | All actions denied unless explicitly permitted |

## Step 1: Create a Policy Engine

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy-engine \
  --name PortfolioAdvisorPolicyEngine \
  --description "Governs portfolio advisor agent tool access — trade limits and tool permissions" \
  --attach-to-gateways my-gateway-secure \
  --attach-mode ENFORCE
```
:::
:::tab{label="Windows"}
```powershell
agentcore add policy-engine `
  --name PortfolioAdvisorPolicyEngine `
  --description "Governs portfolio advisor agent tool access - trade limits and tool permissions" `
  --attach-to-gateways my-gateway-secure `
  --attach-mode ENFORCE

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added policy engine 'PortfolioAdvisorPolicyEngine'
:::

## Step 2: Create Cedar Policies

Retrieve your Gateway ARN:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways \
  --query "items[?contains(name, 'my-gateway-secure')].gatewayId | [0]" \
  --output text)

GATEWAY_ARN=$(aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --query "gatewayArn" --output text)

echo "Gateway ARN: $GATEWAY_ARN"
```
:::
:::tab{label="Windows"}
```powershell
$GATEWAY_ID = aws bedrock-agentcore-control list-gateways `
  --query "items[?contains(name, 'my-gateway-secure')].gatewayId | [0]" `
  --output text

$GATEWAY_ARN = aws bedrock-agentcore-control get-gateway `
  --gateway-identifier $GATEWAY_ID `
  --query "gatewayArn" --output text

Write-Host "Gateway ARN: $GATEWAY_ARN"

```
:::
::::

### Policy 1: Permit trades under 1000 shares

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name trade_quantity_limit \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Allow trades under 1000 shares only" \
  --statement "permit(principal, action == AgentCore::Action::\"ExecuteTrade___execute_trade\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { context.input.quantity < 1000 };"
```
:::
:::tab{label="Windows"}
```powershell
$statement = 'permit(principal, action == AgentCore::Action::"ExecuteTrade___execute_trade", resource == AgentCore::Gateway::"' + $GATEWAY_ARN + '") when { context.input.quantity < 1000 };'

agentcore add policy `
  --name trade_quantity_limit `
  --engine PortfolioAdvisorPolicyEngine `
  --description "Allow trades under 1000 shares only" `
  --statement $statement

```
:::
::::

> **Cedar syntax:** `action == AgentCore::Action::"ExecuteTrade___execute_trade"` — format is `TargetName___tool_name` with **triple** underscores.

### Policy 2: Permit portfolio risk check (all users)

:::alert{header="Why is this needed?" type="info"}
Cedar uses **default deny**. Once a Policy Engine is attached in ENFORCE mode, every tool needs an explicit `permit` to work — including tools that worked before.
:::

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name portfolio_risk_check_policy \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Allow all authenticated users to check portfolio risk" \
  --statement "permit(principal, action == AgentCore::Action::\"PortfolioRiskCheck___check_portfolio_risk\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { (principal is AgentCore::OAuthUser) };" \
  --validation-mode IGNORE_ALL_FINDINGS
```
:::
:::tab{label="Windows"}
```powershell
$statement = 'permit(principal, action == AgentCore::Action::"PortfolioRiskCheck___check_portfolio_risk", resource == AgentCore::Gateway::"' + $GATEWAY_ARN + '") when { (principal is AgentCore::OAuthUser) };'

agentcore add policy `
  --name portfolio_risk_check_policy `
  --engine PortfolioAdvisorPolicyEngine `
  --description "Allow all authenticated users to check portfolio risk" `
  --statement $statement `
  --validation-mode IGNORE_ALL_FINDINGS

```
:::
::::

### Policy 3: Block restricted tickers

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name restricted_ticker_policy \
  --engine PortfolioAdvisorPolicyEngine \
  --description "Block trades on restricted securities" \
  --statement "forbid(principal, action == AgentCore::Action::\"ExecuteTrade___execute_trade\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { [\"RESTRICTED-001\", \"RESTRICTED-002\"].contains(context.input.ticker) };" \
  --validation-mode IGNORE_ALL_FINDINGS
```
:::
:::tab{label="Windows"}
```powershell
$statement = 'forbid(principal, action == AgentCore::Action::"ExecuteTrade___execute_trade", resource == AgentCore::Gateway::"' + $GATEWAY_ARN + '") when { ["RESTRICTED-001", "RESTRICTED-002"].contains(context.input.ticker) };'

agentcore add policy `
  --name restricted_ticker_policy `
  --engine PortfolioAdvisorPolicyEngine `
  --description "Block trades on restricted securities" `
  --statement $statement `
  --validation-mode IGNORE_ALL_FINDINGS

```
:::
::::

## Step 3: Deploy

:::alert{header="Known Issue: Policy Engine Attachment" type="warning"}
The CDK deployment creates the policy engine and policies, but attaching the engine to the gateway may fail due to a circular dependency in IAM role policy creation. If `agentcore deploy` fails with a permissions error, follow the workaround steps below.
:::

First, temporarily remove the `--attach-to-gateways` from the policy engine configuration if the deploy fails. You can do this by editing `agentcore/agentcore.json` and removing the `policyEngineConfiguration` field from the gateway block, then redeploying. The policy engine and its policies will still be created — only the attachment step is deferred.

:::code{language=bash}
agentcore deploy -y -v
:::

### Workaround: Manual Policy Engine Attachment

If the deployment succeeded but the policy engine is not attached to the gateway, run these commands to attach it manually:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
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
  --query "Stacks[0].Outputs[?contains(OutputKey, 'GatewayMyGatewaySecureId')].OutputValue | [0]" \
  --output text)

# 4. Attach the policy engine to the gateway
aws bedrock-agentcore-control update-gateway \
  --gateway-identifier $GATEWAY_ID \
  --policy-engine-configuration "{\"arn\":\"${PE_ARN}\",\"mode\":\"ENFORCE\"}"

echo "Policy engine attached to gateway: $GATEWAY_ID"
```
:::
:::tab{label="Windows"}
```powershell
# 1. Get the gateway role name
$GATEWAY_ROLE_NAME = aws cloudformation describe-stack-resources `
  --stack-name AgentCore-PortfolioAdvisor-default `
  --query "StackResources[?ResourceType=='AWS::IAM::Role' && contains(LogicalResourceId, 'McpGateway')].PhysicalResourceId | [0]" `
  --output text

# 2. Grant the gateway role permission to call the policy engine
aws iam put-role-policy `
  --role-name $GATEWAY_ROLE_NAME `
  --policy-name PolicyEngineAccess `
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:CheckAuthorizePermissions","bedrock-agentcore:IsAuthorized","bedrock-agentcore:IsAuthorizedWithToken","bedrock-agentcore:GetPolicyEngine"],"Resource":"*"}]}'

# 3. Get the policy engine ARN and gateway ID
$PE_ARN = aws cloudformation describe-stacks `
  --stack-name AgentCore-PortfolioAdvisor-default `
  --query "Stacks[0].Outputs[?contains(OutputKey, 'PolicyEngine') && contains(OutputKey, 'Arn')].OutputValue | [0]" `
  --output text

$GATEWAY_ID = aws cloudformation describe-stacks `
  --stack-name AgentCore-PortfolioAdvisor-default `
  --query "Stacks[0].Outputs[?contains(OutputKey, 'GatewayMyGatewaySecureId')].OutputValue | [0]" `
  --output text

# 4. Attach the policy engine to the gateway
aws bedrock-agentcore-control update-gateway `
  --gateway-identifier $GATEWAY_ID `
  --policy-engine-configuration "{`"arn`":`"$PE_ARN`",`"mode`":`"ENFORCE`"}"

Write-Host "Policy engine attached to gateway: $GATEWAY_ID"

```
:::
::::

## Step 4: Test Policy Enforcement

Refresh your token if needed:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```
:::
:::tab{label="Windows"}
```powershell
$COGNITO_WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/web_client_id `
  --query 'Parameter.Value' --output text

$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

```
:::
::::

### Test 1: Small trade (should succeed ✅)

:::code{language=bash}
agentcore invoke "Execute a trade: buy 500 shares of AAPL at market price for rebalancing" \
  --bearer-token "$TOKEN" --stream
:::

### Test 2: Large trade (should be denied ❌)

:::code{language=bash}
agentcore invoke "Buy 5000 shares of MSFT at limit price for a large client position" \
  --bearer-token "$TOKEN" --stream
:::

The agent will report it cannot execute the trade — the Gateway blocked it before the request reached the Lambda.

### Test 3: Portfolio risk check (should succeed ✅)

:::code{language=bash}
agentcore invoke "Check the portfolio risk for PORT-002" \
  --bearer-token "$TOKEN" --stream
:::

### What's Happening Behind the Scenes

:::code{language=bash showCopyAction=false}
User: "Buy 5000 shares of MSFT"
    ↓
Agent decides to call execute_trade(ticker="MSFT", quantity=5000, ...)
    ↓
MCP Client sends request to Gateway
    ↓
Gateway → Policy Engine evaluates Cedar policies
    ↓
Cedar: quantity=5000, policy requires < 1000 → DENY
    ↓
Gateway returns authorization error
    ↓
Agent tells user: "I'm unable to execute this trade..."
:::

## Step 5: Agentic Explainability — Audit Trails

For FSI, it's not enough that the agent works correctly — you need to *prove* it did. Explainability means answering three questions for any interaction:
1. **What did the agent decide to do?** (tool selection reasoning)
2. **Was it allowed?** (policy decision)
3. **Why or why not?** (policy rule that matched)

### View Agent Reasoning in Traces

Every invocation captures the agent's tool selection reasoning in CloudWatch:

:::code{language=bash}
agentcore logs --runtime PortfolioAdvisor --since 5m
:::

In the CloudWatch GenAI Observability dashboard (**GenAI Observability → Bedrock AgentCore → PortfolioAdvisor → DEFAULT**), each trace shows:
- The agent's tool selection decision (which tool it chose and why)
- Input parameters passed to the tool
- Success or failure result

### View Policy Decisions

Policy decisions are logged separately at the Gateway. Each log entry contains:

| Field | Example |
|-------|---------|
| `action` | `ExecuteTrade___execute_trade` |
| `decision` | `DENY` |
| `matchingPolicy` | `trade_quantity_limit` |
| `context.input` | `{"ticker": "MSFT", "quantity": 5000, ...}` |
| `principal` | `workshopuser@example.com` |

### Constructing an Audit Record

For a complete audit trail, join the agent trace with the policy log using the `traceId`:

:::code{language=bash showCopyAction=false}
Audit Record for Trade Attempt:
├── Timestamp: 2025-01-15T14:23:07Z
├── User: workshopuser@example.com (via JWT sub claim)
├── Agent Decision: Call execute_trade with quantity=5000, ticker=MSFT
├── Policy Evaluation: DENY (matched policy: trade_quantity_limit)
├── Reason: quantity 5000 >= 1000 (exceeds per-trade limit)
└── Agent Response: "I cannot execute this trade. The quantity exceeds..."
:::

This audit trail is constructed automatically from CloudWatch data — no additional code required.

## Architecture

:::code{language=bash showCopyAction=false}
CLI (agentcore invoke --bearer-token)
    ↓
AgentCore Runtime (JWT validated)
    ├── Local tools (no policy needed)
    └── MCP Client → Gateway (JWT + Policy Engine)
                        ├── Cedar evaluates policies
                        ├── ✅ check_portfolio_risk (always permitted)
                        ├── ✅ execute_trade (quantity < 1000)
                        └── ❌ execute_trade (quantity >= 1000) → DENIED
                                    ↓
                        CloudWatch (policy decisions logged)
:::

## What Just Happened?

You added governance without changing agent code:

1. **Policy Engine** — Container for authorization rules
2. **Cedar policies** — Declarative rules based on tool inputs (quantity, ticker)
3. **ENFORCE mode** — Denials are enforced at the Gateway boundary
4. **Explainability** — Full audit trail from agent reasoning through policy decisions

---

## Best Practices: Governance Outside the Agent

:::alert{header="Best Practice" type="info"}
**Enforce business rules deterministically at the Gateway — not in agent prompts.**
:::

**Why governance belongs outside the agent:**

| In-prompt rules | Cedar policies |
|----------------|---------------|
| LLM interprets them probabilistically | Evaluated deterministically, every time |
| Can be bypassed via prompt injection | Cannot be bypassed — evaluated before tool execution |
| No audit trail of enforcement | Every decision logged with full context |
| Changing rules = changing code = redeploying | Changing rules = updating policy = no redeploy |
| Agent must "understand" the rule | Agent doesn't even know the rule exists |

**Common governance patterns:**

- **Quantity limits** — `context.input.quantity < 1000` prevents oversized operations
- **Restricted resources** — `forbid ... when { restricted_list.contains(resource_id) }` blocks access to specific resources
- **Action type restrictions** — `forbid ... unless { action_type == "read" }` enforces read-only access for certain roles
- **Role-based access** — `principal.getTag("role") == "admin"` for tiered authorization
- **Emergency shutdown** — `forbid(principal, action, resource)` — a single line disables all tool access instantly

**Explainability and audit:**
- Cedar audit logs capture every policy decision with full context (who, what, when, why denied/permitted)
- Combined with agent reasoning traces, you get a complete per-transaction decision record
- Use `LOG_ONLY` mode first to validate policies don't break existing workflows, then switch to `ENFORCE`
- Export decision logs to your compliance system for long-term retention

---

### What's Next

In Lab 5, you'll add continuous quality monitoring to automatically evaluate your agent's performance on every interaction.

→ Next: [Lab 5: Evaluate Agent Quality](../60-lab5-evaluations/)
