---
title: "Lab 9: VPC Integration for FSI"
weight: 85
---

**⏱️ Estimated time: ~15 minutes**

## Overview

Your portfolio advisor agent is fully functional — but it's running with public network connectivity. For FSI workloads, regulatory requirements often mandate private network isolation. In this lab, you'll deploy your agent into a VPC so it communicates with AWS services (Bedrock, S3, CloudWatch) through VPC endpoints rather than the public internet.

You'll retrieve pre-provisioned VPC resources from SSM Parameter Store, add a two-line configuration change to `agentcore.json`, and redeploy. AgentCore handles all the ENI provisioning, endpoint routing, and DNS resolution — your agent code doesn't change at all.

### What You'll Learn

- Retrieve pre-provisioned VPC resources from SSM Parameter Store
- Configure your agent for VPC network mode
- Deploy and test the agent within a VPC
- Verify private connectivity through VPC endpoints
- Roll back to public mode if needed

### Why VPC for Financial Services

:::alert{header="FSI Network Isolation Requirements" type="info"}
Private network isolation is a first-class requirement for most financial services production workloads:

- **Regulatory compliance** — SEC, FINRA, and SOX frameworks often require that sensitive financial data and agent interactions remain within private networks and never traverse the public internet
- **Zero-trust network architecture** — Minimize public internet exposure by ensuring agents only communicate over private channels, reducing the attack surface
- **Private connectivity to on-premises systems** — Connect to on-premises trading platforms, risk engines, and data warehouses via AWS Direct Connect or Transit Gateway without public routing
- **Network-level audit trail** — VPC Flow Logs capture metadata for all network traffic, providing a complete audit trail for regulatory examinations and incident response
:::

## Step 1: Retrieve VPC Resources

The prerequisites CloudFormation stack created a VPC with private subnets, security groups, and VPC endpoints. Retrieve these values from SSM Parameter Store:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
VPC_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/vpc_id \
  --query 'Parameter.Value' --output text)

PRIVATE_SUBNET_1=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/private_subnet_1 \
  --query 'Parameter.Value' --output text)

PRIVATE_SUBNET_2=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/private_subnet_2 \
  --query 'Parameter.Value' --output text)

SECURITY_GROUP_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/security_group_id \
  --query 'Parameter.Value' --output text)

echo "VPC ID:         $VPC_ID"
echo "Subnet 1:       $PRIVATE_SUBNET_1"
echo "Subnet 2:       $PRIVATE_SUBNET_2"
echo "Security Group: $SECURITY_GROUP_ID"
```
:::
:::tab{label="Windows"}
```powershell
$VPC_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/vpc_id `
  --query 'Parameter.Value' --output text

$PRIVATE_SUBNET_1 = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/private_subnet_1 `
  --query 'Parameter.Value' --output text

$PRIVATE_SUBNET_2 = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/private_subnet_2 `
  --query 'Parameter.Value' --output text

$SECURITY_GROUP_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/security_group_id `
  --query 'Parameter.Value' --output text

Write-Host "VPC ID:         $VPC_ID"
Write-Host "Subnet 1:       $PRIVATE_SUBNET_1"
Write-Host "Subnet 2:       $PRIVATE_SUBNET_2"
Write-Host "Security Group: $SECURITY_GROUP_ID"

```
:::
::::

You should see four resource identifiers printed to the terminal. Keep these values — you'll need them in the next step.

> **Note:** The VPC includes Interface endpoints for AgentCore Runtime (`com.amazonaws.us-west-2.bedrock-agentcore`), AgentCore Gateway (`com.amazonaws.us-west-2.bedrock-agentcore-gateway`), and Bedrock Runtime (`com.amazonaws.us-west-2.bedrock-runtime`), plus Gateway endpoints for S3 and CloudWatch Logs. These allow your agent to communicate with AWS services without traversing the public internet.

## Step 2: Configure VPC Network Mode

Open `agentcore/agentcore.json` in Kiro's editor. In the `runtimes` array, find the `"PortfolioAdvisor"` entry and make two changes:

1. Change `"networkMode": "PUBLIC"` to `"networkMode": "VPC"`
2. Add the `vpcConfig` block with your subnet IDs and security group ID

The updated runtime entry should look like this:

:::code{language=json showCopyAction=false}
"runtimes": [
  {
    "name": "PortfolioAdvisor",
    "build": "CodeZip",
    "entrypoint": "main.py",
    "codeLocation": "app/PortfolioAdvisor/",
    "runtimeVersion": "PYTHON_3_13",
    "networkMode": "VPC",
    "vpcConfig": {
      "subnetIds": ["<PRIVATE_SUBNET_1>", "<PRIVATE_SUBNET_2>"],
      "securityGroupIds": ["<SECURITY_GROUP_ID>"]
    },
    "protocol": "HTTP",
    "requestHeaderAllowlist": [
      "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
      "Authorization"
    ],
    "authorizerType": "CUSTOM_JWT",
    "authorizerConfiguration": {
      "customJwtAuthorizer": {
        "discoveryUrl": "<your-cognito-discovery-url>",
        "allowedClients": ["<client-id>", "<web-client-id>"]
      }
    }
  }
]
:::

Replace `<PRIVATE_SUBNET_1>`, `<PRIVATE_SUBNET_2>`, and `<SECURITY_GROUP_ID>` with the actual values printed in Step 1. Leave the `authorizerConfiguration` values unchanged — those came from Lab 4 and still apply.

:::alert{header="CLI Exception: networkMode and vpcConfig" type="warning"}
The `agentcore` CLI does not currently expose a `--network-mode` flag or `--vpc-config` option. This is one of the few cases where a direct `agentcore.json` edit is required — the same pattern used for `authorizerConfiguration` in Lab 4. All other configuration (gateways, policies, memory) uses the CLI; only these two fields require a manual JSON edit.
:::

> **If `networkMode` is missing:** The field defaults to `"PUBLIC"`. Simply add `"networkMode": "VPC"` as a new field in the runtime object alongside the existing fields.

## Step 3: Validate and Deploy

Before deploying, validate the configuration to catch any JSON syntax errors or missing fields:

:::code{language=bash}
agentcore validate
:::

If validation passes, deploy:

:::code{language=bash}
agentcore deploy -y -v
:::

> **Note:** VPC deployment takes slightly longer than public mode (~3–5 minutes) because AgentCore provisions Elastic Network Interfaces (ENIs) in your private subnets and attaches them to the runtime. The agent will be unreachable until the ENIs are fully attached and healthy.

After deployment completes, verify the runtime status:

:::code{language=bash}
agentcore status
:::

The output should show your runtime as `READY`. To confirm the VPC configuration was applied, inspect the deployed state:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cat agentcore/.cli/deployed-state.json | python3 -c \
  "import sys,json; s=json.load(sys.stdin); \
   rt=s.get('runtimes',{}).get('PortfolioAdvisor',{}); \
   print('networkMode:', rt.get('networkMode')); \
   print('vpcConfig:', json.dumps(rt.get('vpcConfig'), indent=2))"
```
:::
:::tab{label="Windows"}
```powershell
$state = Get-Content agentcore\.cli\deployed-state.json | ConvertFrom-Json
$rt = $state.runtimes.PortfolioAdvisor
Write-Host "networkMode: $($rt.networkMode)"
Write-Host "vpcConfig: $($rt.vpcConfig | ConvertTo-Json)"

```
:::
::::

The output should show `networkMode: VPC` and list your subnet and security group IDs.

## Step 4: Test the Agent in VPC Mode

Since the agent is now in a VPC, it uses private endpoints for all AWS service calls. Test it the same way as before — the bearer token and session management work identically; only the network path has changed.

### Obtain a fresh token

If your Cognito token from Lab 4 has expired (tokens are valid for 60 minutes), obtain a new one:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
COGNITO_POOL_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/pool_id \
  --query 'Parameter.Value' --output text)

COGNITO_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/m2m_client_id \
  --query 'Parameter.Value' --output text)

COGNITO_CLIENT_SECRET=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/m2m_client_secret \
  --with-decryption \
  --query 'Parameter.Value' --output text)

COGNITO_TOKEN_URL=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/cognito_token_url \
  --query 'Parameter.Value' --output text)

AUTH_SCOPE=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/cognito_auth_scope \
  --query 'Parameter.Value' --output text)

TOKEN=$(curl -s -X POST "$COGNITO_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_CLIENT_ID&client_secret=$COGNITO_CLIENT_SECRET&scope=$AUTH_SCOPE" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtained successfully"
```
:::
:::tab{label="Windows"}
```powershell
$COGNITO_POOL_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/pool_id `
  --query 'Parameter.Value' --output text

$COGNITO_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/m2m_client_id `
  --query 'Parameter.Value' --output text

$COGNITO_CLIENT_SECRET = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/m2m_client_secret `
  --with-decryption `
  --query 'Parameter.Value' --output text

$COGNITO_TOKEN_URL = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/cognito_token_url `
  --query 'Parameter.Value' --output text

$AUTH_SCOPE = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/cognito_auth_scope `
  --query 'Parameter.Value' --output text

$body = "grant_type=client_credentials&client_id=$COGNITO_CLIENT_ID&client_secret=$COGNITO_CLIENT_SECRET&scope=$AUTH_SCOPE"
$response = Invoke-RestMethod -Method Post -Uri $COGNITO_TOKEN_URL `
  -ContentType "application/x-www-form-urlencoded" -Body $body
$TOKEN = $response.access_token

Write-Host "Token obtained successfully"

```
:::
::::

### Run three test queries

Create a new session and run queries that exercise all three code paths — local tools, Gateway tools, and memory:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_VPC=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Test 1: Local tool (stock analysis — no AWS service call required)
agentcore invoke "What's the current analysis for AAPL?" \
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

# Test 2: Gateway tool (portfolio risk check via Lambda — crosses VPC endpoint)
agentcore invoke "Check the portfolio risk for PORT-003" \
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

# Test 3: Memory recall (reads from AgentCore Memory — crosses VPC endpoint)
agentcore invoke "Do you remember my investment preferences?" \
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_VPC = [guid]::NewGuid().ToString()

# Test 1: Local tool (stock analysis — no AWS service call required)
agentcore invoke "What's the current analysis for AAPL?" `
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

# Test 2: Gateway tool (portfolio risk check via Lambda — crosses VPC endpoint)
agentcore invoke "Check the portfolio risk for PORT-003" `
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

# Test 3: Memory recall (reads from AgentCore Memory — crosses VPC endpoint)
agentcore invoke "Do you remember my investment preferences?" `
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

```
:::
::::

> **Expected:** All three queries should work identically to public mode. The VPC configuration is transparent to the agent code — it only changes the network path. Local tool calls (Test 1) are handled entirely within the runtime. Gateway and memory calls (Tests 2 and 3) are routed through the VPC Interface endpoints rather than the public internet.

## Step 5: Verify Private Connectivity (Optional)

To confirm that traffic is flowing through VPC endpoints rather than the public internet, inspect the Elastic Network Interfaces that AgentCore created for your agent:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=$SECURITY_GROUP_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,SubnetId:SubnetId,Status:Status,Description:Description}' \
  --output table
```
:::
:::tab{label="Windows"}
```powershell
aws ec2 describe-network-interfaces `
  --filters "Name=group-id,Values=$SECURITY_GROUP_ID" `
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,SubnetId:SubnetId,Status:Status,Description:Description}' `
  --output table

```
:::
::::

You should see ENIs in both private subnets with `Status: in-use` — these are the network interfaces your agent runtime uses to communicate within the VPC.

To confirm that VPC Flow Logs are capturing traffic (for audit compliance), check whether flow logging is enabled on your VPC:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws ec2 describe-flow-logs \
  --filter "Name=resource-id,Values=$VPC_ID" \
  --query 'FlowLogs[].{FlowLogId:FlowLogId,Status:FlowLogStatus,Destination:LogDestination}' \
  --output table
```
:::
:::tab{label="Windows"}
```powershell
aws ec2 describe-flow-logs `
  --filter "Name=resource-id,Values=$VPC_ID" `
  --query 'FlowLogs[].{FlowLogId:FlowLogId,Status:FlowLogStatus,Destination:LogDestination}' `
  --output table

```
:::
::::

> **If flow logs are enabled**, the `Status` column will show `ACTIVE` and the `Destination` will show the CloudWatch log group or S3 bucket receiving the data. This is the network-level audit trail required by many FSI regulatory frameworks.

## Step 6: Roll Back to Public Mode (If Needed)

If VPC mode causes connectivity issues — for example, because a required VPC endpoint is missing or the security group is too restrictive — you can revert to public mode with one configuration change:

1. Open `agentcore/agentcore.json` in Kiro's editor
2. Change `"networkMode": "VPC"` back to `"networkMode": "PUBLIC"`
3. The `vpcConfig` block can remain in place — it is ignored in `PUBLIC` mode
4. Redeploy:

:::code{language=bash}
agentcore deploy -y -v
:::

:::alert{header="Common VPC connectivity issues" type="warning"}
If you see timeout errors after switching to VPC mode, check the following:

- **Missing VPC endpoints** — Every AWS service your agent calls (Bedrock Runtime, AgentCore, S3, CloudWatch Logs) needs either a VPC Interface/Gateway endpoint or a NAT Gateway to reach it. Verify the endpoints exist with `aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=$VPC_ID`.
- **Security group egress rules** — The security group must allow outbound HTTPS (port 443) traffic. Overly restrictive egress rules will silently block all AWS API calls.
- **Subnet routing** — Private subnets must have a route table entry pointing to the VPC endpoints or NAT Gateway. Public subnets route via the Internet Gateway, which defeats the purpose of VPC mode.
:::

## Architecture

After completing this lab, your agent runs entirely within a private network:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor) — VPC Mode
    ├── Deployed in private subnets (no public IP)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION) ──────────────── via VPC endpoint
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── MCP Client → Exa AI ────────────────────────────── via NAT Gateway → internet
    └── MCP Client → AgentCore Gateway ─────────────────── via VPC endpoint
                          ↓
                    Policy Engine (Cedar policies)
                          ↓
                    Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics) ──── via VPC endpoint
:::

All AWS service traffic — Bedrock model invocations, memory reads and writes, Gateway calls, and CloudWatch telemetry — flows through VPC endpoints and never leaves the AWS network. Only the Exa AI MCP connection (a third-party service) requires a NAT Gateway for internet egress.

## FSI VPC Best Practices

:::alert{header="Production VPC Checklist for FSI Agents" type="info"}
When deploying agents in financial services production environments, apply these network isolation controls:

- **Network segmentation** — Place agents in dedicated subnets, separate from data stores and trading systems. Use separate security groups for each tier (agents, databases, trading engines) with explicit ingress/egress rules between them.
- **VPC endpoint policies** — Attach resource-based policies to each VPC Interface endpoint to restrict which IAM principals can call through it. Least-privilege endpoint policies prevent lateral movement within the VPC.
- **PrivateLink for cross-account tools** — If your Lambda tools are in a different AWS account, expose them over AWS PrivateLink rather than routing across account boundaries via the public internet.
- **VPC Flow Logs enabled** — Enable flow logs to a CloudWatch log group or S3 bucket for all agent subnets. This is the primary network-level audit mechanism for regulatory examinations.
- **No agents in public subnets** — Never place production agents in public subnets. Public subnets have routes to the Internet Gateway, which means the agent's ENI could receive an Elastic IP and be directly reachable from the internet.
:::

## What Just Happened?

Two configuration changes converted your public agent to a VPC-isolated agent:

1. Set `"networkMode": "VPC"` in `agentcore.json`
2. Added `"vpcConfig"` with your subnet IDs and security group ID
3. Ran `agentcore deploy` — AgentCore provisioned ENIs in your private subnets, updated DNS resolution to use VPC endpoints, and restarted the runtime

The agent code didn't change at all. The tools, memory, Gateway, and Cedar policies all work identically — the only difference is the network path.

### Before and After

| | Public Mode | VPC Mode |
|---|---|---|
| **Network path** | Public internet | Private subnets only |
| **Bedrock API calls** | Public endpoint | VPC Interface endpoint |
| **Agent has public IP** | Yes (managed by AgentCore) | No |
| **VPC Flow Logs** | Not applicable | Full network audit trail |
| **Direct Connect / TGW** | Not applicable | Supported |
| **Deployment time** | ~1–2 min | ~3–5 min (ENI provisioning) |
| **Agent code changes** | — | None required |

## Congratulations!

Your agent now runs in a private VPC:

- ✅ **Private network isolation** — No public internet exposure for AWS service traffic
- ✅ **VPC endpoints** — Direct AWS service connectivity without NAT for Bedrock, AgentCore, and CloudWatch
- ✅ **Same functionality** — All tools, memory, Gateway, and policies work unchanged
- ✅ **Network audit trail** — VPC Flow Logs capture all network activity for regulatory compliance
- ✅ **Rollback ready** — Switch back to public mode with a single config change and redeploy

### What's Next

In Lab 10, you'll optimize your agent's cost profile by tuning session lifecycle, evaluation sampling rates, and memory retention — critical for managing FSI workloads at scale.

→ Next: [Lab 10: Cost Optimization & Session Lifecycle](../88-lab9-cost-optimization/)
