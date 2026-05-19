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
| **AgentCore Runtime** | Serverless execution environment for deployed agents |
| **AgentCore Gateway** | MCP-compatible proxy to centralize and secure tool access across agents |
| **AgentCore Identity** | Secure credential management for API keys and OAuth providers |
| **AgentCore Observability** | Tracing and monitoring via CloudWatch GenAI Observability |
| **AgentCore Policy** | Cedar-based fine-grained authorization for tool access at the Gateway boundary |
| **AgentCore Evaluations** | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |
| **AgentCore Memory** | Persistent memory with semantic and summarization strategies (optional lab) |

## What You'll Build

In this hands-on workshop, you'll build a **Portfolio Advisor Agent** for a capital markets firm — deploying it to production and progressively adding security, governance, evaluations, and network isolation using the AgentCore CLI.

> **Note:** The financial data, compliance rules, and trading scenarios in this workshop are simulated for educational purposes only and do not constitute actual regulatory guidance.

### Core Labs

| Lab | Title | Time | What You'll Learn |
|-----|-------|------|-------------------|
| — | Foundations (reading) | ~5 min | Agent planning, observability strategy, "no code changes" philosophy |
| 1 | Deploy to AgentCore Runtime | ~15 min | Deploy pre-built agent, invoke via CLI |
| 1B | Observability Deep Dive | ~15 min | Traces, session isolation, token metrics, CloudWatch GenAI dashboards |
| 2 | Centralize Tools with Gateway | ~25 min | Gateway creation, Lambda tool registration, credential patterns (JWT vs IAM vs OBO) |
| 3 | Secure with JWT Authentication | ~20 min | Cognito JWT auth on Runtime and Gateway, end-to-end token propagation |
| 4 | Govern Agent Actions with Policies | ~25 min | Cedar policies, trade limits, restricted tickers, agentic explainability |
| 5 | Evaluate Agent Quality | ~15 min | Continuous quality monitoring with built-in evaluators |
| 6 | VPC Integration for Private Networking | ~15 min | Private subnet isolation, VPC endpoints, PrivateLink |

### Optional Labs

| Lab | Title | Time | Prerequisites | What You'll Learn |
|-----|-------|------|---------------|-------------------|
| 2B | Enterprise Tool Registry | ~20 min | Lab 2 | Tool approval workflow, security review, MCP server registration, semantic discovery |
| 7 | Add Persistent Memory | ~20 min | Labs 1–3 | SEMANTIC and SUMMARIZATION memory strategies |
| 8 | Build Client Portal | ~20 min | Labs 1–3 | Flask chat frontend with Cognito login |
| 9 | Cost Optimization | ~15 min | Labs 1–5 | Session lifecycle, eval sampling, token monitoring |

### Architecture Overview

At the end of the core labs you will have deployed the following infrastructure:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor) — in VPC private subnet
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── MCP Client → AgentCore Gateway (JWT + Cedar Policy Engine)
                          ├── PortfolioRiskCheck → Lambda
                          ├── ExecuteTrade → Lambda (governed by Cedar policies)
                          ↓
                    CloudWatch GenAI Observability
                          ↓
                    AgentCore Evaluations (QualityMonitor)
:::

## Prerequisites

Your Workshop Studio environment is **fully pre-provisioned**. No manual setup is required — proceed directly to the Getting Started page.

→ [Getting Started](./10-intro/)

→ [Foundations: Building Production Agents](./15-foundations/) *(read while setup runs)*
