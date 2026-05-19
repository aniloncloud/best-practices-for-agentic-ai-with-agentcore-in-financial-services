---
title: "Getting Started"
weight: 10
---

## Welcome

Welcome to **Best Practices for Agentic AI with AgentCore in Financial Services**. In this workshop, you'll deploy and progressively harden a portfolio advisor agent using Amazon Bedrock AgentCore.

## What's Already Set Up

Your Workshop Studio environment comes **fully pre-provisioned**. The following resources are already deployed and ready:

| Resource | What It Provides |
|----------|-----------------|
| **VS Code Server** | Browser-based IDE with terminal access |
| **Agent workspace** | Complete `PortfolioAdvisor/` project with agent code, tools, and dependencies pre-installed |
| **Amazon Cognito** | User Pool with M2M client, web client, and test user (`workshopuser@example.com` / `WorkshopPass1!`) |
| **Lambda functions** | `workshop-check-portfolio-risk` and `workshop-execute-trade` — ready to be wired through Gateway |
| **VPC** | Two private subnets, NAT Gateway, VPC endpoints for AgentCore, Bedrock Runtime, S3, CloudWatch Logs |
| **SSM Parameters** | All resource IDs stored under `/app/portfolioadvisor/agentcore/` for easy retrieval |
| **CloudWatch** | GenAI Observability dashboards pre-configured |

## Orientation (~5 minutes)

### 1. Open VS Code Server

In Workshop Studio, click the **VS Code Server** link in the left sidebar. This opens a browser-based IDE connected to your workshop environment.

### 2. Open a Terminal

In VS Code, open a terminal: **Terminal → New Terminal** (or `` Ctrl+` ``).

### 3. Verify Your Workspace

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd ~/PortfolioAdvisor
ls app/PortfolioAdvisor/
```
:::
:::tab{label="Windows"}
```powershell
cd $HOME\PortfolioAdvisor
dir app\PortfolioAdvisor\

```
:::
::::

You should see: `main.py`, `mcp_client/`, `tool/`, `pyproject.toml`

### 4. Verify the AgentCore CLI

:::code{language=bash}
agentcore --version
:::

### 5. Confirm Your Region

:::code{language=bash}
aws configure get region
:::

Expected output: `us-west-2`

:::alert{header="Region Check" type="warning"}
This workshop runs exclusively in **us-west-2**. If your region is different, run: `export AWS_DEFAULT_REGION=us-west-2`
:::

### 6. Review the Agent Code

Open `app/PortfolioAdvisor/main.py` in VS Code. Notice:
- Two local tools: `get_stock_analysis()` and `get_compliance_rules()`
- An MCP client stub (commented out — you'll enable this in Lab 2)
- A `handler()` function that creates a Strands Agent and invokes it with the user's prompt
- Simulated financial data (stocks, compliance rules)

### 7. Review the AgentCore Configuration

Open `agentcore/agentcore.json`. It contains a single runtime definition with the agent's name, model, and code directory. No gateway, auth, or VPC config yet — you'll add those in subsequent labs.

## Workshop Structure

### Core Labs

| Lab | Title | Time | What You'll Do |
|-----|-------|------|----------------|
| — | Foundations (reading) | ~5 min | Agent planning, observability strategy, "no code changes" philosophy |
| 1 | Runtime | ~15 min | Deploy to cloud |
| 1B | Observability | ~15 min | Traces, session isolation, token metrics |
| 2 | Gateway | ~25 min | Centralize tools, credential patterns |
| 3 | Security | ~20 min | JWT auth on Runtime and Gateway |
| 4 | Governance | ~25 min | Cedar policies, explainability |
| 5 | Evaluations | ~15 min | Continuous quality monitoring |
| 6 | VPC | ~15 min | Private network isolation |

### Optional Labs

| Lab | Title | Time | What You'll Do |
|-----|-------|------|----------------|
| 2B | Tool Registry | ~20 min | Enterprise tool approval workflow |
| 7 | Memory | ~20 min | Persistent client memory |
| 8 | Frontend | ~20 min | Flask chat portal with Cognito login |
| 9 | Cost Optimization | ~15 min | Session lifecycle, eval sampling |

## Ready?

→ Next: [Foundations: Building Production Agents](../15-foundations/)
