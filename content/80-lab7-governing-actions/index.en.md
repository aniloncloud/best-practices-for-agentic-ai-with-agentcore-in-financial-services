---
title: "Lab 7: Governing Agent Actions with Policies"
weight: 82
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Your customer support agent is deployed, secured with JWT authentication, and monitored with evaluations. But authentication only answers *"who is calling?"* — it doesn't answer *"what are they allowed to do?"*

Consider this scenario: you add a refund processing tool to your agent. Should every authenticated user be able to issue refunds of any amount? What if a customer asks the agent to refund $10,000? Without governance, the agent will happily comply — it has no concept of business rules or spending limits.

**AgentCore Policy** solves this by adding fine-grained authorization at the Gateway boundary using [Cedar](https://www.cedarpolicy.com/) policies. Policies are evaluated deterministically *outside* the agent's code, so the agent can't accidentally bypass them — even if it's tricked by a clever prompt.

### What You'll Learn

- Add a new refund tool to your existing Gateway
- Create a Policy Engine to store authorization rules
- Write Cedar policies that restrict tool usage based on input parameters
- Attach the Policy Engine to your Gateway in ENFORCE mode
- Test that allowed actions succeed and denied actions are blocked — all from the chat UI

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Policy Engine** | A container for Cedar policies that evaluates authorization requests |
| **Cedar Policy** | A declarative rule that permits or forbids access to a tool based on conditions |
| **ENFORCE mode** | Policy decisions are enforced — denied requests are blocked at the Gateway |
| **LOG_ONLY mode** | Policy decisions are logged but not enforced (useful for testing) |
| **Default Deny** | All actions are denied unless explicitly permitted by a Cedar policy |

## Step 0: Set Up Your Terminals

Lab 7 uses both the chat UI (to test policy enforcement) and the CLI (to create policies). You'll need two terminals running side by side.

**Split your terminal** in Kiro — click the split terminal icon (⊞) in the terminal panel, or use `` Cmd+\ `` (macOS) / `` Ctrl+\ `` (Windows/Linux).

**Terminal 1 — Frontend server:**

Start the frontend from Lab 6:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd app/CustomerSupport/frontend
uv run python frontend.py
```
:::
:::tab{label="Windows"}
```powershell
cd app\CustomerSupport\frontend
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

## Step 1: Add the Refund Tool to Your Gateway

The prerequisites stack includes a Lambda function (`workshop-process-refund`) that simulates processing customer refunds. Let's expose it through your secured Gateway so the agent can call it.

### Retrieve the Lambda ARN

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
REFUND_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/customersupport/agentcore/refund_lambda_arn \
  --query 'Parameter.Value' --output text)

echo "Refund Lambda ARN: $REFUND_LAMBDA_ARN"
```
:::
:::tab{label="Windows"}
```powershell
$REFUND_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/customersupport/agentcore/refund_lambda_arn `
  --query 'Parameter.Value' --output text

Write-Host "Refund Lambda ARN: $REFUND_LAMBDA_ARN"

```
:::
::::

### Create the tool schema

Create the schema file that describes the refund tool to the agent:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
touch app/CustomerSupport/tool/refund_schema.json
```
:::
:::tab{label="Windows"}
```powershell
New-Item app\CustomerSupport\tool\refund_schema.json -Force

```
:::
::::

Open `app/CustomerSupport/tool/refund_schema.json` in Kiro's editor and add:

:::code{language=json}
[
  {
    "name": "process_refund",
    "description": "Process a customer refund for a given order. Requires the order ID, refund amount in dollars, and a reason for the refund.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "order_id": {
          "type": "string",
          "description": "The order ID to refund (e.g., ORD-12345)"
        },
        "amount": {
          "type": "integer",
          "description": "Refund amount in whole dollars"
        },
        "reason": {
          "type": "string",
          "description": "Reason for the refund (e.g., defective item, wrong product, customer dissatisfied)"
        }
      },
      "required": ["order_id", "amount", "reason"]
    }
  }
]
:::

> **Why `"type": "integer"`?** Cedar uses Long type for whole numbers, which maps directly from JSON Schema `integer`. This lets us write simple comparisons like `context.input.amount < 100` in our policies. If we used `"type": "number"` (which maps to Cedar Decimal), we'd need the more verbose `.lessThan(decimal("100.00"))` syntax.

### Add the refund target to the Gateway

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name ProcessRefund \
  --lambda-arn $REFUND_LAMBDA_ARN \
  --tool-schema-file app/CustomerSupport/tool/refund_schema.json \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway-target `
  --type lambda-function-arn `
  --name ProcessRefund `
  --lambda-arn $REFUND_LAMBDA_ARN `
  --tool-schema-file app/CustomerSupport/tool/refund_schema.json `
  --gateway my-gateway-secure

```
:::
::::

### Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the refund tool (no policy yet)

At this point, the refund tool is available but has no policy restrictions. Open your browser at **http://localhost:8501** (the Flask frontend from Lab 6) and try:

:::code{language=bash showCopyAction=true}
I'd like a refund of $500 for order ORD-12345 because the item was defective
:::

The agent should successfully process the refund — there's nothing stopping it. Any authenticated user can request any refund amount. Let's fix that.

## Step 2: Create a Policy Engine and Attach to Gateway

A Policy Engine is a container that holds your Cedar policies and evaluates them against incoming requests. Create one for your customer support application and attach it to your gateway:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy-engine \
  --name CustomerSupportPolicyEngine \
  --description "Governs customer support agent tool access — refund limits and tool permissions" \
  --attach-to-gateways my-gateway-secure \
  --attach-mode ENFORCE
```
:::
:::tab{label="Windows"}
```powershell
agentcore add policy-engine `
  --name CustomerSupportPolicyEngine `
  --description "Governs customer support agent tool access - refund limits and tool permissions" `
  --attach-to-gateways my-gateway-secure `
  --attach-mode ENFORCE

```
:::
::::

You should see output like:

:::code{language=bash showCopyAction=false}
Added policy engine 'CustomerSupportPolicyEngine'
:::

> **ENFORCE vs LOG_ONLY:** In `ENFORCE` mode, denied requests are blocked and the tool call fails. In `LOG_ONLY` mode, all requests are allowed but policy decisions are logged to CloudWatch — useful for testing policies before enforcing them.

## Step 3: Create Cedar Policies

Now write the authorization rules. We'll create two policies:

1. **Permit refunds under $100** — allows the refund tool only for small amounts
2. **Permit warranty checks** — explicitly allows the existing warranty tool for all users

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

### Policy 1: Refund limit

This policy permits the `process_refund` tool only when the amount is less than 100:

:::code{language=cedar showCopyAction=false}
permit(
  principal,
  action == AgentCore::Action::"ProcessRefund___process_refund",
  resource == AgentCore::Gateway::"<YOUR_GATEWAY_ARN>"
)
when {
  ((context.input).amount) < 100
};
:::

> **Understanding the Cedar syntax:**
> - `permit` — allows the action (Cedar also supports `forbid` to deny)
> - `principal` — any authenticated user (from the JWT token)
> - `action == AgentCore::Action::"ProcessRefund___process_refund"` — the specific tool (format: `TargetName___tool_name` with triple underscores)
> - `resource == AgentCore::Gateway::"<arn>"` — scoped to your Gateway ARN
> - `when { context.input.amount < 100 }` — only when the refund amount is under $100

Now create this policy using the CLI:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name refund_limit_policy \
  --engine CustomerSupportPolicyEngine \
  --description "Allow refunds under 100 dollars only" \
  --statement "permit(principal, action == AgentCore::Action::\"ProcessRefund___process_refund\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { context.input.amount < 100 };"
```
:::
:::tab{label="Windows"}
```powershell
$statement = 'permit(principal, action == AgentCore::Action::"ProcessRefund___process_refund", resource == AgentCore::Gateway::"' + $GATEWAY_ARN + '") when { context.input.amount < 100 };'

agentcore add policy `
  --name refund_limit_policy `
  --engine CustomerSupportPolicyEngine `
  --description "Allow refunds under 100 dollars only" `
  --statement $statement

```
:::
::::

### Policy 2: Warranty check access

This policy permits the warranty check tool unconditionally for all authenticated users:

:::alert[Cedar uses **default deny** — once you attach a Policy Engine in ENFORCE mode, every tool call through the Gateway needs an explicit `permit` policy to succeed. Without this policy, the warranty check tool (which worked fine before) would start failing with authorization errors. This policy preserves existing functionality.]{header="Why is this policy needed?"}
:::

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name warranty_check_policy \
  --engine CustomerSupportPolicyEngine \
  --description "Allow all authenticated users to check warranties" \
  --statement "permit(principal, action == AgentCore::Action::\"WarrantyCheck___check_warranty\", resource == AgentCore::Gateway::\"${GATEWAY_ARN}\") when { (principal is AgentCore::OAuthUser) };" \
  --validation-mode IGNORE_ALL_FINDINGS
```
:::
:::tab{label="Windows"}
```powershell
$statement = 'permit(principal, action == AgentCore::Action::"WarrantyCheck___check_warranty", resource == AgentCore::Gateway::"' + $GATEWAY_ARN + '") when { (principal is AgentCore::OAuthUser) };'

agentcore add policy `
  --name warranty_check_policy `
  --engine CustomerSupportPolicyEngine `
  --description "Allow all authenticated users to check warranties" `
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

Open your browser at **http://localhost:8501**. The agent now has the refund tool available, but it's governed by your Cedar policies.

Use the credentials you created in Lab 4:

- **Email:** `workshopuser@example.com`
- **Password:** `WorkshopPass1!`

### Test 1: Small refund (should succeed ✅)

Type in the chat:

:::code{language=bash showCopyAction=true}
I need a refund of $50 for order ORD-12345. The item arrived damaged.
:::

**Expected:** The agent calls `process_refund` with amount=50. The policy permits it (50 < 100), and the refund is processed successfully.

### Test 2: Large refund (should be denied ❌)

Type in the chat:

:::code{language=bash showCopyAction=true}
Actually, can you process a refund of $500 for order ORD-67890? I want a full refund.
:::

**Expected:** The agent tries to call `process_refund` with amount=500. The policy denies it (500 ≥ 100), and the Gateway returns an authorization error. The agent should inform the customer that the refund cannot be processed and suggest contacting a supervisor or support team.

### Test 3: Warranty check (should succeed ✅)

Type in the chat:

:::code{language=bash showCopyAction=true}
Check the warranty for PROD-002
:::

**Expected:** The warranty check works as before — the policy explicitly permits it for all users.

### What's happening behind the scenes

:::code{language=bash showCopyAction=false}
User: "Refund $500 for order ORD-67890"
    ↓
Agent decides to call process_refund(amount=500, order_id="ORD-67890", reason="full refund")
    ↓
MCP Client sends request to Gateway
    ↓
Gateway intercepts request → Policy Engine evaluates Cedar policies
    ↓
Cedar evaluation: amount=500, policy requires amount < 100 → DENY
    ↓
Gateway returns authorization error to agent
    ↓
Agent tells user: "I'm unable to process this refund..."
:::

The key insight: **the agent code never changed, and neither did the Lambda function code**. The refund tool was discovered automatically via the Gateway MCP client, and the policy enforcement happens entirely at the Gateway boundary — before the request ever reaches the Lambda. The agent simply receives an error when a policy denies the action.

## Step 5: (Bonus) Generate a Policy from Natural Language

AgentCore Policy can generate Cedar policies from plain English descriptions. This is useful when you want to add new rules without learning Cedar syntax:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add policy \
  --name refund_reason_policy \
  --engine CustomerSupportPolicyEngine \
  --generate "Forbid refunds when the reason does not contain the word defective" \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add policy `
  --name refund_reason_policy `
  --engine CustomerSupportPolicyEngine `
  --generate "Forbid refunds when the reason does not contain the word defective" `
  --gateway my-gateway-secure

```
:::
::::

The CLI translates your natural language into a valid Cedar policy, validates it against the tool schema, and checks for safety issues — all before you deploy it.

### Inspect the generated Cedar

Open `agentcore/agentcore.json` and look at the new policy entry under `policyEngines` and `policies`. You should see something like:

:::code{language=json showCopyAction=false}
{
  "name": "refund_reason_policy",
  "statement": "forbid(\n  principal,\n  action == AgentCore::Action::\"ProcessRefund___process_refund\",\n  resource == AgentCore::Gateway::\"<YOUR_GATEWAY_ARN>\"\n) unless {\n  ((context.input).reason) like \"*defective*\"\n};",
  "validationMode": "FAIL_ON_ANY_FINDINGS"
}
:::

Notice how the CLI automatically:
- Identified the correct action name (`ProcessRefund___process_refund`)
- Scoped the policy to your gateway ARN
- Translated "does not contain the word defective" into Cedar's `forbid ... unless { reason like "*defective*" }` pattern
- Used `forbid` with `unless` — this means the refund is **blocked** unless the reason contains "defective". Since Cedar's `forbid` overrides `permit`, this policy takes precedence over the amount-based permit policy

### Deploy the generated policy

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the refund reason policy

Try a refund with "defective" in the reason (should succeed ✅):

:::code{language=bash showCopyAction=true}
I need a refund of $50 for order ORD-99999 because the item was defective
:::

Try a refund without "defective" in the reason (should be denied ❌):

:::code{language=bash showCopyAction=true}
I need a refund of $50 for order ORD-11111 because I changed my mind
:::

## Architecture

After completing this lab, your architecture includes policy enforcement at the Gateway:

:::code{language=bash showCopyAction=false}
User (browser at localhost:8501)
    ↓
Flask backend → AgentCore Runtime (with JWT)
    ↓
AgentCore Runtime (CustomerSupport)
    ├── Local tools: get_return_policy(), get_product_info()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway (secured + policy enforced)
                          ↓
                    Policy Engine evaluates Cedar policies
                          ↓
                    ✅ WarrantyCheck__check_warranty (always permitted)
                    ✅ RefundTarget__process_refund (amount < $100)
                    ❌ RefundTarget__process_refund (amount ≥ $100) → DENIED
:::

Overall architecture now looks like the following:

![Overall architecture with AgentCore Policies](/static/80-lab7/lab7_architecture_diagram.png)

## What Just Happened?

You added governance to your agent without changing a single line of agent code:

1. **Added a refund tool** — Exposed a new Lambda function through the existing Gateway
2. **Created a Policy Engine** — A container for your authorization rules
3. **Wrote Cedar policies** — Declarative rules that permit or deny tool access based on input parameters
4. **Attached to Gateway in ENFORCE mode** — Every tool call is now evaluated against your policies
5. **Tested via the UI** — Small refunds succeed, large refunds are blocked

### Why This Matters

| Without Policy | With Policy |
|---------------|-------------|
| Any authenticated user can call any tool | Fine-grained control over what each tool can do |
| Agent decides whether to process a $10,000 refund | Gateway blocks it before it reaches the Lambda |
| Business rules live in prompt engineering (fragile) | Business rules are deterministic Cedar policies (reliable) |
| No audit trail of authorization decisions | Every decision logged to CloudWatch |
| Changing rules means changing agent code | Changing rules means updating a policy — no redeploy needed |

### Cedar Policy Patterns to Explore

| Pattern | Example |
|---------|---------|
| Amount limits | `context.input.amount < 1000` |
| Role-based access | `principal.getTag("role") == "manager"` |
| Required fields | `forbid ... unless { context.input has description }` |
| Regional restrictions | `["US", "CA"].contains(context.input.region)` |
| Emergency shutdown | `forbid(principal, action, resource)` |

## Congratulations!

Your agent now has deterministic governance:

- ✅ **Policy Engine** — Cedar-based authorization for all Gateway tools
- ✅ **Fine-grained control** — Refund amounts capped at $100
- ✅ **No code changes** — Policies enforce at the Gateway boundary, outside agent code
- ✅ **Audit trail** — Every policy decision logged to CloudWatch
- ✅ **Natural language authoring** — Generate Cedar policies from plain English

### What's Next

You've completed the full workshop! Head to the summary to review everything you've built.

→ Next: [Summary](../90-summary/)
