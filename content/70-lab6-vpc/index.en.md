---
title: "Optional Lab: VPC Networking"
weight: 70
---

**⏱️ Estimated time: ~15 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Lab 1 (a deployed agent). The VPC switch is independent of the Gateway and Cedar policies.
:::

## Overview

Your portfolio advisor agent is fully functional — but it's running with public network connectivity. For FSI workloads, regulatory requirements often mandate that agent traffic never traverse the public internet. In this lab, you'll move your harness into a VPC so all AWS service calls (Bedrock, AgentCore Gateway, CloudWatch) flow through VPC endpoints rather than the public internet.

A small harness config change, one redeploy, and your agent is network-isolated.

### What Changes

| Aspect | PUBLIC mode | VPC mode |
|--------|-------------|----------|
| Network path | Public internet | Private subnets only |
| AWS service calls | Via public endpoints | Via VPC endpoints (PrivateLink) |
| Agent ENIs | None | Attached to private subnets |
| Security groups | N/A | Control outbound traffic |
| Deployment time | ~1–2 min | ~3–5 min (ENI provisioning) |
| Agent code changes | — | None required |

### What You'll Learn

- Retrieve pre-provisioned VPC resources from SSM Parameter Store
- Configure VPC network mode with a harness config edit
- Deploy and verify the agent within a VPC
- Understand which VPC endpoints provide connectivity for each AWS service
- Roll back to public mode if needed

### What You're Building

:::code{language=bash showCopyAction=false}
┌─────────────────────────────────────────────────────────┐
│  VPC (private subnets)  ← THIS LAB                      │
│                                                         │
│  AgentCore Harness (PortfolioAdvisor)                   │
│      │                                                  │
│      ├──▶ bedrock-runtime VPC endpoint ──▶ Bedrock      │
│      ├──▶ bedrock-agentcore-gateway endpoint ──▶ Gateway│
│      ├──▶ logs VPC endpoint ──▶ CloudWatch              │
│      └──▶ s3 gateway endpoint ──▶ S3                    │
│                                                         │
│  All traffic stays on AWS backbone (never public internet)│
└─────────────────────────────────────────────────────────┘
:::

## Step 1: Retrieve VPC Resources

The prerequisites CloudFormation stack created a VPC with private subnets, a security group, and VPC endpoints for all required AWS services. Retrieve the resource IDs from SSM Parameter Store:

:::code{language=bash}
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
:::

You should see four resource identifiers. Keep them — you'll add them to your harness config in the next step.

## Step 2: Configure VPC Mode

VPC networking is harness configuration. Edit `app/PortfolioAdvisor/harness.json` and add a network configuration block with your private subnets and security group:

:::code{language=json showCopyAction=false}
"networkConfiguration": {
  "networkMode": "VPC",
  "subnets": ["<PRIVATE_SUBNET_1>", "<PRIVATE_SUBNET_2>"],
  "securityGroups": ["<SECURITY_GROUP_ID>"]
}
:::

Replace the placeholders with the values printed in Step 1. Leave all other fields — model, system prompt, tools, inbound authorizer — unchanged.

:::alert{header="Harness VPC flags" type="info"}
The harness also accepts `--network-mode VPC --subnets ... --security-groups ...` on `agentcore add harness` at creation time. Either way it's configuration — no agent code changes.
:::

:::alert{header="VPC mode pulls the harness image over NAT" type="warning"}
In VPC mode the harness pulls its managed container image from Amazon ECR Public, which has no VPC endpoint — so your private subnets need a NAT gateway with internet egress (the workshop VPC already has one). Your agent's traffic to Bedrock, the Gateway, and CloudWatch still flows privately through VPC endpoints; only the one-time image pull uses the NAT path.
:::

## Step 3: Deploy

Validate the configuration, then deploy:

:::code{language=bash}
agentcore validate
agentcore deploy -y -v
:::

:::alert{header="ENI Provisioning" type="info"}
VPC deployments take 3–5 minutes because AgentCore provisions Elastic Network Interfaces (ENIs) in your private subnets. The runtime will show as `CREATING` until the ENIs are attached and healthy. Do not interrupt the deploy.
:::

Check the status after deployment completes:

:::code{language=bash}
agentcore status
:::

You should see `PortfolioAdvisor` in `READY` state.

## Step 4: Test Connectivity

Invoke the agent with your bearer token from Lab 2. The session management and JWT auth work identically — only the network path has changed:

:::code{language=bash}
source ~/portfolio-env.sh

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

SESSION_VPC=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Answered from the harness system prompt — no Gateway call
agentcore invoke "What's the current analysis for AAPL?" \
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream

# Gateway tool — routes through bedrock-agentcore-gateway VPC endpoint
agentcore invoke "Check the portfolio risk for PORT-003" \
  --session-id $SESSION_VPC --bearer-token "$TOKEN" --stream
:::

Both queries should return the same results as in public mode. The VPC configuration is transparent to your agent code.

:::alert{header="If you see a timeout" type="warning"}
Wait 2–3 minutes and retry — ENIs may still be initializing. If the error persists, check that the security group allows outbound HTTPS (port 443) and that all required VPC endpoints are present (see Step 5).
:::

## Step 5: Verify Network Isolation

The pre-provisioned VPC includes Interface endpoints for all AWS services your agent calls. Each endpoint keeps that service's traffic on the AWS backbone:

| VPC Endpoint | Service it covers |
|---|---|
| `bedrock-agentcore` | Runtime management (deploy, status, invoke) |
| `bedrock-agentcore-gateway` | Gateway tool calls (MCP connectivity) |
| `bedrock-runtime` | Model inference (Claude invocations) |
| `s3` | Package retrieval during deploy |
| `logs` | CloudWatch Logs (traces and metrics) |

To confirm ENIs were provisioned in your private subnets:

:::code{language=bash}
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=$SECURITY_GROUP_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Subnet:SubnetId,Status:Status}' \
  --output table
:::

You should see ENIs in both private subnets with `Status: in-use`.

## Step 6: Roll Back to PUBLIC Mode (Optional)

If VPC connectivity issues can't be resolved in the workshop timeframe, revert with one edit:

1. Open `app/PortfolioAdvisor/harness.json`
2. Change `"networkMode": "VPC"` back to `"networkMode": "PUBLIC"`
3. The `networkConfiguration` block can stay — it is ignored in `PUBLIC` mode
4. Redeploy:

:::code{language=bash}
agentcore deploy -y -v
:::

## Architecture

After this lab, your agent runs entirely within a private network:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
AgentCore Harness (PortfolioAdvisor) — VPC Mode
    ├── Private subnets (no public IP, ENIs attached)
    ├── Model + system prompt (stock/compliance reference data)
    └── Gateway tool (by reference) → AgentCore Gateway ──── via bedrock-agentcore-gateway VPC endpoint
                          ↓
                    Cedar Policy Engine
                          ↓
                    Lambda: check_portfolio_risk

AWS service traffic (Bedrock, Gateway, CloudWatch, S3)
    → VPC Interface/Gateway endpoints → AWS backbone (never public internet)
:::

## What Just Happened?

A small harness config change enabled full VPC isolation:

1. `"networkMode": "VPC"` — tells AgentCore to provision ENIs in your subnets
2. `"networkConfiguration"` — specifies which subnets and security group to use

AgentCore handled ENI provisioning, DNS resolution updates, and VPC endpoint routing automatically. Your agent code, tools, Gateway integration, JWT auth, and Cedar policies all work identically — the only change is the network path.

---

## Best Practices: Network Isolation

:::alert{header="Best Practice" type="info"}
**VPC isolation is a configuration change, not an architecture overhaul.** A small harness config change moves your agent from public internet to private subnets.
:::

**When to use VPC mode:**

- Your agent accesses sensitive data (PII, financial records, health data)
- Your organization requires network-level audit trails (VPC Flow Logs)
- Compliance frameworks mandate private network paths for data processing
- You want defense-in-depth beyond IAM (network restriction + IAM + auth)

**PrivateLink vs. NAT Gateway:**

PrivateLink (VPC Interface endpoints) routes traffic entirely on the AWS backbone — it never touches the public internet. A NAT Gateway routes traffic to the public internet endpoint of an AWS service, even if that endpoint resolves to an AWS-owned IP. For sensitive workloads, PrivateLink is the correct choice. NAT Gateway is a fallback for services that don't yet offer VPC endpoints.

**VPC endpoints are per-service:**

You need one endpoint for each AWS service your agent calls. Missing a single endpoint causes silent timeouts (the traffic tries to reach a public IP that is unreachable from a private subnet with no NAT). Always enumerate every AWS API your agent touches before deploying to VPC mode.

**Security group principle of least privilege:**

Allow outbound HTTPS (port 443) only. Deny all inbound. Your agent initiates connections outbound to AWS service endpoints — it never needs to accept inbound connections from within the VPC. Lock down the egress rule list to the specific CIDR ranges of your VPC endpoints if your security policy requires it.

**Multi-AZ for high availability:**

Always specify subnets in at least two Availability Zones (as this lab does). If one AZ has an ENI provisioning failure or an AZ-level event, AgentCore can use the other subnet. Single-AZ deployments create an unnecessary availability risk for production systems.

**Cost consideration:**

VPC Interface endpoints have an hourly charge per AZ plus a per-GB data processing fee. For most agent workloads this is modest. NAT Gateway is often more expensive at scale because it charges per GB processed, and model inference responses can be large. Profile your workload before choosing NAT over endpoints.

**Data residency:**

VPC isolation ensures agent traffic stays within the AWS Region — it cannot be routed through peering arrangements or transit paths that cross regional boundaries. This matters for cross-border data transfer restrictions under various regulatory frameworks.

---

→ Next: [Summary](../90-summary/)

*(Optional labs available: [Memory](../80-optional-memory/) | [Frontend](../85-optional-frontend/) | [Cost Optimization](../88-optional-cost/))*
