---
title: "Lab 8: Governing Agent Actions with Policies"
weight: 82
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Your portfolio advisor agent is deployed, secured with JWT authentication, and monitored with evaluations. But authentication only answers *"who is calling?"* — it doesn't answer *"what are they allowed to do?"*

Consider this scenario: you add a trade execution tool to your agent. Should every authenticated user be able to execute trades of any size? What if a client asks the agent to execute a 10,000-share trade? Without governance, the agent will happily comply — it has no concept of business rules or position limits.

**AgentCore Policy** solves this by adding fine-grained authorization at the Gateway boundary using [Cedar](https://www.cedarpolicy.com/) policies. Policies are evaluated deterministically *outside* the agent's code, so the agent can't accidentally bypass them — even if it's tricked by a clever prompt.

### What You'll Learn

- Add a new trade execution tool to your existing Gateway
- Create a Policy Engine to store authorization rules
- Write Cedar policies that restrict tool usage based on input parameters
- Attach the Policy Engine to your Gateway in ENFORCE mode
- Test that allowed actions succeed and denied actions are blocked — all from the chat UI

:::alert{header="Compliance Disclaimer" type="warning"}
The compliance rules and financial data in this workshop are **simulated for educational purposes only** and do not constitute actual regulatory guidance. Consult your compliance team for real-world implementations.
:::

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Policy Engine** | A container for Cedar policies that evaluates authorization requests |
| **Cedar Policy** | A declarative rule that permits or forbids access to a tool based on conditions |
| **ENFORCE mode** | Policy decisions are enforced — denied requests are blocked at the Gateway |
| **LOG_ONLY mode** | Policy decisions are logged but not enforced (useful for testing) |
| **Default Deny** | All actions are denied unless explicitly permitted by a Cedar policy |

## Step 0: Set Up Your Terminals

Lab 8 uses both the chat UI (to test policy enforcement) and the CLI (to create policies). You'll need two terminals running side by side.

**Split your terminal** in Kiro — click the split terminal icon (⊞) in the terminal panel, or use `` Cmd+\ `` (macOS) / `` Ctrl+\ `` (Windows/Linux).

**Terminal 1 — Frontend server:**

Start the frontend from Lab 7:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd app/PortfolioAdvisor/frontend
uv run python frontend.py
```
:::
:::tab{label="Windows"}
```powershell
cd app\PortfolioAdvisor\frontend
uv run python frontend.py

```
:::
::::

You should see the server running on `http://localhost:8501`.

**Terminal 2 — CLI commands:**

In the second terminal, make sure you're in the project root:

:::code{language=bash}
cd ../../..
:::

All CLI commands in this lab should be run in this terminal.

## Step 1: Add the Trade Execution Tool to Your Gateway

The prerequisites stack includes a Lambda function (`workshop-execute-trade`) that simulates executing stock trades. Let's expose it through your secured Gateway so the agent can call it.

### Retrieve the Lambda ARN

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TRADE_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/execute_trade_lambda_arn \
  --query 'Parameter.Value' --output text)

echo "Trade Lambda ARN: $TRADE_LAMBDA_ARN"
```
:::
:::tab{label="Windows"}
```powershell
$TRADE_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/execute_trade_lambda_arn `
  --query 'Parameter.Value' --output text

Write-Host "Trade Lambda ARN: $TRADE_LAMBDA_ARN"

```
:::
::::

### Create the tool schema

Create the schema file that describes the trade execution tool to the agent:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
touch app/PortfolioAdvisor/tool/trade_schema.json
```
:::
:::tab{label="Windows"}
```powershell
New-Item app\PortfolioAdvisor\tool\trade_schema.json -Force

```
:::
::::

Open `app/PortfolioAdvisor/tool/trade_schema.json` in Kiro's editor and add:

:::code{language=json}
[
  {
    "name": "execute_trade",
    "description": "Execute a stock trade. Requires the ticker symbol, number of shares, order type (market or limit), and a reason for the trade.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "ticker": {
          "type": "string",
          "description": "Stock ticker symbol (e.g., AAPL, MSFT, JPM)"
        },
        "quantity": {
          "type": "integer",
          "description": "Number of shares to trade"
        },
        "order_type": {
          "type": "string",
          "description": "Order type: 'market' or 'limit'"
        },
        "reason": {
          "type": "string",
          "description": "Reason for the trade"
        }
      },
      "required": ["ticker", "quantity", "order_type", "reason"]
    }
  }
]
:::

> **Why `"type": "integer"`?** Cedar uses Long type for whole numbers, which maps directly from JSON Schema `integer`. This lets us write simple comparisons like `context.input.quantity < 1000` in our policies. If we used `"type": "number"` (which maps to Cedar Decimal), we'd need the more verbose `.lessThan(decimal("1000.00"))` syntax.

### Add the trade execution target to the Gateway

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name ExecuteTrade \
  --lambda-arn $TRADE_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/trade_schema.json \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway-target `
  --type lambda-function-arn `
  --name ExecuteTrade `
  --lambda-arn $TRADE_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/trade_schema.json `
  --gateway my-gateway-secure

```
:::
::::

### Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the trade execution tool (no policy yet)

At this point, the trade execution tool is available but has no policy restrictions. Open your browser at **http://localhost:8501** (the Flask frontend from Lab 7) and try:

:::code{language=bash showCopyAction=true}
Execute a trade: buy 500 shares of AAPL at market price for portfolio rebalancing
:::

The agent should successfully execute the trade — there's nothing stopping it. Any authenticated user can request a trade of any size. Let's fix that.

## Step 2: Create a Policy Engine and Attach to Gateway

A Policy Engine is a container that holds your Cedar policies and evaluates them against incoming requests. Create one for your portfolio advisor application and attach it to your gateway:

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

You should see output like:

:::code{language=bash showCopyAction=false}
Added policy engine 'PortfolioAdvisorPolicyEngine'
:::

> **ENFORCE vs LOG_ONLY:** In `ENFORCE` mode, denied requests are blocked and the tool call fails. In `LOG_ONLY` mode, all requests are allowed but policy decisions are logged to CloudWatch — useful for testing policies before enforcing them.

## Step 3: Create Cedar Policies

Now write the authorization rules. We'll create three policies:

1. **Permit trades under 1000 shares** — allows the trade execution tool only for smaller position sizes
2. **Permit portfolio risk check access** — explicitly allows the existing portfolio risk check tool for all users
3. **Block restricted tickers** — forbids trading in securities on the restricted list

First, retrieve your Gateway ARN — you'll need it in the Cedar policy statements:

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

> **Note:** You can also find the Gateway ARN in `agentcore/.cli/deployed-state.json` or from the `agentcore status` output.

### Policy 1: Trade quantity limit

This policy permits the `execute_trade` tool only when the quantity is less than 1000 shares:

:::code{language=cedar showCopyAction=false}
permit(
  principal,
  action == AgentCore::Action::"ExecuteTrade___execute_trade",
  resource == AgentCore::Gateway::"<YOUR_GATEWAY_ARN>"
)
when {
  context.input.quantity < 1000
};
:::

> **Understanding the Cedar syntax:**
> - `permit` — allows the action (Cedar also supports `forbid` to deny)
> - `principal` — any authenticated user (from the JWT token)
> - `action == AgentCore::Action::"ExecuteTrade___execute_trade"` — the specific tool (format: `TargetName___tool_name` with triple underscores)
> - `resource == AgentCore::Gateway::"<arn>"` — scoped to your Gateway ARN
> - `when { context.input.quantity < 1000 }` — only when the trade quantity is under 1000 shares

Now create this policy using the CLI:

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

### Policy 2: Portfolio risk check access

This policy permits the portfolio risk check tool unconditionally for all authenticated users:

:::alert[Cedar uses **default deny** — once you attach a Policy Engine in ENFORCE mode, every tool call through the Gateway needs an explicit `permit` policy to succeed. Without this policy, the portfolio risk check tool (which worked fine before) would start failing with authorization errors. This policy preserves existing functionality.]{header="Why is this policy needed?"}
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

### Policy 3: Restricted ticker block

This policy forbids trading in securities that appear on the firm's restricted list — regardless of any permit policies that would otherwise apply. Cedar's `forbid` always overrides `permit`:

:::code{language=cedar showCopyAction=false}
forbid(
  principal,
  action == AgentCore::Action::"ExecuteTrade___execute_trade",
  resource == AgentCore::Gateway::"<YOUR_GATEWAY_ARN>"
)
when {
  ["RESTRICTED-001", "RESTRICTED-002"].contains(context.input.ticker)
};
:::

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

### Deploy the policies

:::code{language=bash}
agentcore deploy -y -v
:::

## Step 4: Test Policy Enforcement via the Chat UI

Open your browser at **http://localhost:8501**. The agent now has the trade execution tool available, but it's governed by your Cedar policies.

Use the credentials you created in Lab 5:

- **Email:** `workshopuser@example.com`
- **Password:** `WorkshopPass1!`

### Test 1: Small trade (should succeed ✅)

Type in the chat:

:::code{language=bash showCopyAction=true}
Execute a trade: buy 500 shares of AAPL at market price for portfolio rebalancing
:::

**Expected:** The agent calls `execute_trade` with quantity=500. The policy permits it (500 < 1000), and the trade is executed successfully.

### Test 2: Large trade (should be denied ❌)

Type in the chat:

:::code{language=bash showCopyAction=true}
I need to buy 5000 shares of MSFT at limit price for a large client position
:::

**Expected:** The agent tries to call `execute_trade` with quantity=5000. The policy denies it (5000 ≥ 1000), and the Gateway returns an authorization error. The agent should inform the client that the trade cannot be executed and suggest escalating to a senior advisor.

### Test 3: Portfolio risk check (should succeed ✅)

Type in the chat:

:::code{language=bash showCopyAction=true}
Check the portfolio risk for PORT-002
:::

**Expected:** The portfolio risk check works as before — the policy explicitly permits it for all authenticated users.

### What's happening behind the scenes

:::code{language=bash showCopyAction=false}
User: "Buy 5000 shares of MSFT at limit price"
    ↓
Agent decides to call execute_trade(ticker="MSFT", quantity=5000, order_type="limit", reason="large client position")
    ↓
MCP Client sends request to Gateway
    ↓
Gateway intercepts request → Policy Engine evaluates Cedar policies
    ↓
Cedar evaluation: quantity=5000, policy requires quantity < 1000 → DENY
    ↓
Gateway returns authorization error to agent
    ↓
Agent tells user: "I'm unable to execute this trade..."
:::

The key insight: **the agent code never changed, and neither did the Lambda function code**. The trade execution tool was discovered automatically via the Gateway MCP client, and the policy enforcement happens entirely at the Gateway boundary — before the request ever reaches the Lambda. The agent simply receives an error when a policy denies the action.

## Step 5: (Bonus) Generate a Policy from Natural Language

AgentCore Policy can generate Cedar policies from plain English descriptions. This is useful when you want to add new rules without learning Cedar syntax:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name order_type_restriction \
  --engine PortfolioAdvisorPolicyEngine \
  --generate "Forbid trades unless the order_type is limit" \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add policy `
  --name order_type_restriction `
  --engine PortfolioAdvisorPolicyEngine `
  --generate "Forbid trades unless the order_type is limit" `
  --gateway my-gateway-secure

```
:::
::::

The CLI translates your natural language into a valid Cedar policy, validates it against the tool schema, and checks for safety issues — all before you deploy it.

### Inspect the generated Cedar

Open `agentcore/agentcore.json` and look at the new policy entry under `policyEngines` and `policies`. You should see something like:

:::code{language=json showCopyAction=false}
{
  "name": "order_type_restriction",
  "statement": "forbid(\n  principal,\n  action == AgentCore::Action::\"ExecuteTrade___execute_trade\",\n  resource == AgentCore::Gateway::\"<YOUR_GATEWAY_ARN>\"\n) unless {\n  ((context.input).order_type) == \"limit\"\n};",
  "validationMode": "FAIL_ON_ANY_FINDINGS"
}
:::

Notice how the CLI automatically:
- Identified the correct action name (`ExecuteTrade___execute_trade`)
- Scoped the policy to your gateway ARN
- Translated "unless the order_type is limit" into Cedar's `forbid ... unless { order_type == "limit" }` pattern
- Used `forbid` with `unless` — this means the trade is **blocked** unless the order type is `limit`. Since Cedar's `forbid` overrides `permit`, this policy takes precedence over the quantity-based permit policy

### Deploy the generated policy

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the order type restriction

Try a limit order (should succeed ✅):

:::code{language=bash showCopyAction=true}
Execute a trade: buy 200 shares of JPM as a limit order for dividend capture
:::

Try a market order (should be denied ❌):

:::code{language=bash showCopyAction=true}
Execute a trade: buy 200 shares of JPM as a market order for dividend capture
:::

## Architecture

After completing this lab, your architecture includes policy enforcement at the Gateway:

:::code{language=bash showCopyAction=false}
User (browser at localhost:8501)
    ↓
Flask backend → AgentCore Runtime (with JWT)
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Local tools: get_market_data(), get_portfolio_info()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway (secured + policy enforced)
                          ↓
                    Policy Engine evaluates Cedar policies
                          ↓
                    ✅ PortfolioRiskCheck___check_portfolio_risk (always permitted)
                    ✅ ExecuteTrade___execute_trade (quantity < 1000)
                    ❌ ExecuteTrade___execute_trade (quantity >= 1000) → DENIED
:::

Overall architecture now looks like the following:

![Overall architecture with AgentCore Policies](/static/80-lab7/lab7_architecture_diagram.png)

## What Just Happened?

You added governance to your agent without changing a single line of agent code:

1. **Added a trade execution tool** — Exposed a new Lambda function through the existing Gateway
2. **Created a Policy Engine** — A container for your authorization rules
3. **Wrote Cedar policies** — Declarative rules that permit or deny tool access based on input parameters (trade quantity, restricted tickers)
4. **Attached to Gateway in ENFORCE mode** — Every tool call is now evaluated against your policies
5. **Tested via the UI** — Small trades succeed, oversized trades and restricted securities are blocked

### Why This Matters

| Without Policy | With Policy |
|---------------|-------------|
| Any authenticated user can call any tool | Fine-grained control over what each tool can do |
| Agent decides whether to execute a 10,000-share trade | Gateway blocks it before it reaches the Lambda |
| Business rules live in prompt engineering (fragile) | Business rules are deterministic Cedar policies (reliable) |
| No audit trail of authorization decisions | Every decision logged to CloudWatch |
| Changing rules means changing agent code | Changing rules means updating a policy — no redeploy needed |

### Cedar Policy Patterns to Explore

| Pattern | Example |
|---------|---------|
| Quantity limits | `context.input.quantity < 1000` |
| Role-based access | `principal.getTag("role") == "senior_advisor"` |
| Required fields | `forbid ... unless { context.input has reason }` |
| Regional restrictions | `["US", "CA"].contains(context.input.region)` |
| Emergency shutdown | `forbid(principal, action, resource)` |

## Congratulations!

Your agent now has deterministic governance:

- ✅ **Policy Engine** — Cedar-based authorization for all Gateway tools
- ✅ **Fine-grained control** — Trade quantities capped at 1000 shares per request
- ✅ **Restricted securities** — Trades on restricted tickers blocked at the Gateway
- ✅ **No code changes** — Policies enforce at the Gateway boundary, outside agent code
- ✅ **Natural language authoring** — Generate Cedar policies from plain English

### What's Next

In Lab 9, you'll deploy your agent into a VPC for private network isolation — a critical requirement for financial services workloads.

→ Next: [Lab 9: VPC Integration for FSI](../85-lab8-vpc-integration/)
