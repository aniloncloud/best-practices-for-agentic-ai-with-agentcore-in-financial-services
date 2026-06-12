---
title: "Best Practices for Agentic AI with AgentCore in Financial Services"
weight: 2
---

Welcome to the Best Practices for Agentic AI with AgentCore in Financial Services workshop. 

Building production-ready AI agents requires careful planning and execution across the entire development lifecycle. The difference between a prototype that impresses in a demo and an agent that delivers value in production is achieved through disciplined engineering practices, robust architecture, and continuous improvement.

This workshop explores essential best practices for building enterprise AI agents using Amazon Bedrock AgentCore. [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) is an agentic platform that provides the services you need to create, deploy, and manage AI agents at scale. We cover everything from initial deployment to organizational scaling, with practical guidance that you can apply immediately.

![Best Practices](/static/images/BestPractices-InANutshell.png)

Amazon Bedrock AgentCore supports various interfaces for developing and deploying your agent code. At the lowest level, you can interact with the AgentCore APIs directly or through the [AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/overview.html). For a simpler development experience, the [AgentCore Python SDK](https://github.com/aws/bedrock-agentcore-sdk-python) and [AgentCore Typescript SDK](https://github.com/aws/bedrock-agentcore-sdk-typescript) provide higher-level abstractions for integrating with AgentCore services. The [AgentCore CLI](https://github.com/aws/agentcore-cli) builds on top of these, offering the best developer experience that lets you quickly scaffold, configure, and deploy agents. This workshop focuses on the AgentCore CLI.

## What is the AgentCore CLI?

AgentCore CLI is a Node.js command-line tool for creating, configuring, deploying, and managing agents on Amazon Bedrock AgentCore.

The AgentCore CLI abstracts away infrastructure complexity, letting developers focus on agent logic while automating AWS resource provisioning, packaging, and deployment to a serverless runtime. It gives you the flexibility to build your agent using your preferred framework (whether that's [Strands Agents](https://strandsagents.com/), [LangGraph](https://www.langchain.com/langgraph), [CrewAI](https://crewai.com/), [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents-sdk) or [Google ADK](https://google.github.io/adk-docs/)) and pair it with the AI model of your choice.

![AgentCore CLI Overview](/static/images/agentcore-cli-overview.png)

### AgentCore Services Used in This Workshop

| Service | Description |
|---------|-------------|
| **AgentCore Harness** | Managed, declarative agent runtime — declare model, prompt, and tools in config (powered by Strands Agents) |
| **AgentCore Runtime** | Serverless execution environment underlying the harness |
| **AgentCore Gateway** | MCP-compatible proxy to centralize and secure tool access across agents |
| **AgentCore Identity** | Secure credential management for API keys and OAuth providers |
| **AgentCore Observability** | Tracing and monitoring via CloudWatch GenAI Observability |
| **AgentCore Policy** | Cedar-based fine-grained authorization for tool access at the Gateway boundary |
| **AgentCore Evaluations** | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |
| **AgentCore Memory** | Persistent memory with semantic and summarization strategies (optional lab) |

## What You'll Build

In this hands-on workshop, you'll deploy a **Portfolio Advisor Agent** for a capital markets firm — defined as a declarative **AgentCore harness** (no orchestration code) — and progressively add security, governance, and observability through configuration using the AgentCore CLI.

> **Note:** The financial data, compliance rules, and trading scenarios in this workshop are simulated for educational purposes only and do not constitute actual regulatory guidance.

## Workshop Schedule

### Live Session (60 minutes)

| Segment | Title | Time | What You'll Do |
|---------|-------|------|----------------|
| Talk | Intro: AgentCore for Financial Services | ~8 min | Facilitator presents; read [Foundations](./15-foundations/) |
| [Lab 1](./20-lab1-runtime/) | Deploy to the AgentCore Harness | ~10 min | Deploy declarative harness, invoke, right-size the model live; read while it deploys |
| [Lab 2](./30-lab2-gateway/) | Connect Tools with Gateway + JWT Auth | ~18 min | Gateway creation, Lambda tool registration, JWT auth end-to-end |
| [Lab 3](./50-lab4-governance/) | Govern Agent Actions with Cedar Policies | ~16 min | Cedar policies deny a 5,000-share trade that succeeded in Lab 2 |
| Buffer | Finish up / questions | ~8 min | Fast finishers: try the restricted-ticker Cedar policy extension |

### Self-Paced (continue after the session)

Your event account stays available for a limited time after the Summit, so you can continue then.

| Lab | Title | Time | What You'll Do |
|-----|-------|------|----------------|
| [Observability Deep Dive](./25-lab1b-observability/) | Observability Deep Dive | ~15 min | Traces, session isolation, token metrics, CloudWatch GenAI dashboards |
| [OAuth Token Flows](./40-lab3-security/) | OAuth Token Flows: M2M & Token Lifecycle | ~20 min | M2M client credentials, token introspection, full lifecycle |
| [Enterprise Tool Registry](./35-lab2b-tool-registry/) | Enterprise Tool Registry | ~20 min | Tool approval workflow, security review, MCP server registration |
| [Evaluations](./60-lab5-evaluations/) | Evaluations | ~15 min | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |
| [VPC Networking](./70-lab6-vpc/) | VPC Networking | ~15 min | Private subnet isolation, VPC endpoints, PrivateLink |
| [Memory](./80-optional-memory/) | Add Persistent Memory | ~20 min | SEMANTIC and SUMMARIZATION memory strategies |
| [Frontend](./85-optional-frontend/) | Build Client Portal | ~20 min | Flask chat frontend with Cognito login |
| [Cost Optimization](./88-optional-cost/) | Cost Optimization | ~15 min | Session lifecycle, eval sampling, token monitoring |

### Architecture Overview

At the end of the live session you will have deployed the following infrastructure:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Harness (PortfolioAdvisor)
    ├── Model + system prompt (stock/compliance reference data)
    └── Gateway tool (by reference) → AgentCore Gateway (JWT + Cedar Policy Engine)
                          ├── PortfolioRiskCheck → Lambda
                          └── ExecuteTrade → Lambda (governed by Cedar policies)
                                ↓
                          CloudWatch GenAI Observability
:::

For VPC private-subnet isolation and continuous Evaluations, see the self-paced labs above.

## Prerequisites

Your Workshop Studio environment is **fully pre-provisioned**. No manual setup is required — proceed directly to the Getting Started page.

→ [Getting Started](./10-intro/)
