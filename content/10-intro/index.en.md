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
| **Agent workspace** | Complete `PortfolioAdvisor/` harness project (`harness.json` + tool schemas), AgentCore CLI pre-installed |
| **Amazon Cognito** | User Pool with M2M client, web client, and test user (`workshopuser@example.com` / `WorkshopPass1!`) |
| **Lambda functions** | `workshop-check-portfolio-risk` and `workshop-execute-trade` — ready to be wired through Gateway |
| **AgentCore harness IAM** | Harness execution role, gateway service role (Lambda invoke + policy-engine attach), and an OAuth2 M2M credential provider — all pre-created so deploys and governance "just work" |
| **VPC** | Two private subnets, NAT Gateway, VPC endpoints for AgentCore, Bedrock Runtime, S3, CloudWatch Logs |
| **SSM Parameters** | All resource IDs stored under `/app/portfolioadvisor/agentcore/` for easy retrieval |
| **CloudWatch** | GenAI Observability dashboards pre-configured |

:::alert{header="Your first priority" type="info"}
**Get to Lab 1 and kick off the deploy.** The deploy takes 2–3 minutes and the lab is written so you read while it runs. Don't spend time here — orientation below takes under 3 minutes.
:::

## Orientation (~3 minutes)

### 1. Open VS Code Server

In Workshop Studio, click the **VS Code Server** link in the left sidebar. This opens a browser-based IDE connected to your workshop environment.

### 2. Open a Terminal

In VS Code, open a terminal: **Terminal → New Terminal** (or `` Ctrl+` ``).

### 3. Verify Your Workspace and AgentCore CLI

```bash
cd ~/PortfolioAdvisor
agentcore --version
```

### 4. Confirm Your Region

```bash
aws configure get region
```

Expected output: `us-west-2`

:::alert{header="Region Check" type="warning"}
This workshop runs exclusively in **us-west-2**. If your region is different, run: `export AWS_DEFAULT_REGION=us-west-2`
:::

That's all the orientation you need. The agent code tour happens inside Lab 1's deploy-wait panel — head there now.

:::alert{header="About the agent" type="info"}
The agent is defined declaratively in `app/PortfolioAdvisor/harness.json` — model, system prompt, and tools. There is no orchestration code. Once Lab 2 creates a Gateway, you attach it to the harness by reference and its tools appear automatically. There are no agent code edits anywhere in this workshop.
:::

## Workshop Schedule

### Live Session (60 minutes)

| Segment | Title | Time | What You'll Do |
|---------|-------|------|----------------|
| Talk | Intro: AgentCore for Financial Services | ~8 min | Facilitator presents; read [Foundations](../15-foundations/) |
| [Lab 1](../20-lab1-runtime/) | Deploy to the AgentCore Harness | ~10 min | Deploy declarative harness, invoke, right-size the model live; read while it deploys |
| [Lab 2](../30-lab2-gateway/) | Connect Tools with Gateway + JWT Auth | ~18 min | Gateway creation, Lambda tool registration, JWT auth end-to-end |
| [Lab 3](../50-lab4-governance/) | Govern Agent Actions with Cedar Policies | ~16 min | Cedar policies deny a 5,000-share trade that succeeded in Lab 2 |
| Buffer | Finish up / questions | ~8 min | Fast finishers: try the restricted-ticker Cedar policy extension |

### Self-Paced (continue after the session)

| Lab | Title | Time | What You'll Do |
|-----|-------|------|----------------|
| [Observability Deep Dive](../25-lab1b-observability/) | Observability Deep Dive | ~15 min | Traces, session isolation, token metrics, CloudWatch GenAI dashboards |
| [OAuth Token Flows](../40-lab3-security/) | OAuth Token Flows: M2M & Token Lifecycle | ~20 min | M2M client credentials, token introspection, full lifecycle |
| [Enterprise Tool Registry](../35-lab2b-tool-registry/) | Enterprise Tool Registry | ~20 min | Tool approval workflow, security review, MCP server registration |
| [Evaluations](../60-lab5-evaluations/) | Evaluations | ~15 min | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |
| [VPC Networking](../70-lab6-vpc/) | VPC Networking | ~15 min | Private subnet isolation, VPC endpoints, PrivateLink |
| [Memory](../80-optional-memory/) | Add Persistent Memory | ~20 min | SEMANTIC and SUMMARIZATION memory strategies |
| [Frontend](../85-optional-frontend/) | Build Client Portal | ~20 min | Flask chat frontend with Cognito login |
| [Cost Optimization](../88-optional-cost/) | Cost Optimization | ~15 min | Session lifecycle, eval sampling, token monitoring |

:::alert{header="Continue after the session" type="info"}
Everything in the Self-Paced section can be completed after the live session — **your event account stays available for a limited time after the Summit**. You don't need to rush through any of those labs during the 60-minute live session.
:::

→ Next: [Lab 1: Deploy to AgentCore Runtime](../20-lab1-runtime/)
