---
title: "Best Practices for Agentic AI with AgentCore in Financial Services"
weight: 2
---

Welcome to the Best Practices for Agentic AI with AgentCore in Financial Services workshop. 

Building production-ready AI agents requires careful planning and execution across the entire development lifecycle. The difference between a prototype that impresses in a demo and an agent that delivers value in production is achieved through disciplined engineering practices, robust architecture, and continuous improvement.

This workshop explores  essential best practices for building enterprise AI agents using Amazon Bedrock AgentCore. [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) is an agentic platform that provides the services you need to create, deploy, and manage AI agents at scale. We cover everything from initial scoping to organizational scaling, with practical guidance that you can apply immediately.

![Best Practices](/static/images/BestPractices-InANutshell.png)

Amazon Bedrock AgentCore supports various interfaces for developing and deploying your agent code. At the lowest level, you can interact with the AgentCore APIs directly or through the [AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/overview.html) (such as [boto3](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore.html)). For a simpler development experience, the [AgentCore Python SDK](https://github.com/aws/bedrock-agentcore-sdk-python) and [AgentCore Typescript SDK](https://github.com/aws/bedrock-agentcore-sdk-typescript) provide higher-level abstractions for integrating with AgentCore services like runtime, memory, and tools. The [AgentCore CLI](https://github.com/aws/agentcore-cli) builds on top of these, offering the best developer experience that lets you quickly scaffold, configure, and deploy agents. The AgentCore CLI is the easiest way to get started, and continues to be the best developer experience as you iterate on your agents. This workshop focuses on it.

In this workshop, we will use AgentCore CLI.

## What is the AgentCore CLI?

AgentCore CLI is a Node.js command-line tool for creating, configuring, deploying, and managing agents on Amazon Bedrock AgentCore.

The AgentCore CLI is an end-to-end developer tool that abstracts away infrastructure complexity, letting developers focus on agent logic while automating AWS resource provisioning, packaging, and deployment to a serverless runtime. It gives you the flexibility to build your agent using your preferred framework (whether that's [Strands Agents](https://strandsagents.com/), [LangGraph](https://www.langchain.com/langgraph), [CrewAI](https://crewai.com/), [Microsoft Autogen](https://microsoft.github.io/autogen/stable//index.html), [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents-sdk) or [Google ADK](https://google.github.io/adk-docs/)) and pair it with the AI model of your choice, including [Amazon Bedrock](https://aws.amazon.com/bedrock/), Anthropic Claude, Google Gemini, or OpenAI.

Once your agent is ready, the CLI makes deployment seamless by integrating with Infrastructure as Code (IaC) tools like [AWS CDK](https://aws.amazon.com/cdk/), automatically handling everything from IAM roles and CloudWatch logging to packaging your code and provisioning a dedicated serverless endpoint — all without leaving your terminal. You can either run a simple `agentcore deploy` for a quick deployment, or follow a production-ready path that bootstraps your full AWS environment and synthesizes your infrastructure before pushing it live.

Invoking your agent is as straightforward as running `agentcore invoke` with a JSON payload, which sends your prompt directly to the deployed serverless endpoint and returns the agent's response in real time, making the entire journey from development to production a smooth and unified experience.

![AgentCore CLI Overview](/static/images/agentcore-cli-overview.png)

### AgentCore Services Used in This Workshop

| Service | Description |
|---------|-------------|
| **AgentCore Runtime** | Serverless execution environment for deployed agents |
| **AgentCore Memory** | Persistent memory with semantic, summarization, and user preference strategies |
| **AgentCore Gateway** | MCP-compatible proxy to centralize and secure tool access across agents |
| **AgentCore Identity** | Secure credential management for API keys and OAuth providers |
| **AgentCore Observability** | Tracing and monitoring via CloudWatch GenAI Observability |
| **AgentCore Policy** | Cedar-based fine-grained authorization for tool access at the Gateway boundary |
| **AgentCore Evaluations** | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |

## What You'll Build

In this hands-on workshop, you'll build a **Portfolio Advisor Agent** for a capital markets firm — from prototype to production — using the AgentCore CLI and [Kiro IDE](https://kiro.dev). This workshop demonstrates the full spectrum of AgentCore capabilities applied to portfolio advisory use cases.

This workshop focuses on capital markets use cases — stock analysis, portfolio risk assessment, trade execution, and compliance rules.

> **Note:** The financial data, compliance rules, and trading scenarios in this workshop are simulated for educational purposes only and do not constitute actual regulatory guidance.

| Lab | Title | Time | What You'll Learn |
|-----|-------|------|-------------------|
| 1 | Build Your Portfolio Advisor Prototype | ~20 min | Scaffold a project, add stock analysis and compliance tools, test locally |
| 2 | Add Memory for Client Personalization | ~20 min | Persistent memory across sessions with SEMANTIC and SUMMARIZATION strategies |
| 3 | Scale with Gateway & Identity | ~30 min | Centralize tools via Lambda + AgentCore Gateway |
| 4 | Production Observability & Session Management | ~15 min | Session continuity, traces, and logs via CLI and CloudWatch |
| 5 | Secure with JWT Authentication | ~20 min | Cognito JWT auth for runtime and gateway, end-to-end token propagation |
| 6 | Evaluate Agent Performance | ~15 min | Continuous quality monitoring with built-in evaluators |
| 7 | Build Client Portal Interface | ~20 min | Flask chat frontend with Cognito login connected to your deployed agent |
| 8 | Govern Agent Actions with Policies | ~20 min | Fine-grained Cedar policies to control trade execution at the Gateway |
| 9 | VPC Integration for FSI | ~15 min | Deploy your agent into a VPC for private network isolation |
| 10 | Cost Optimization & Session Lifecycle | ~15 min | Tune session timeouts, evaluation sampling, and token monitoring |

### Architecture Overview

At the end of this workshop you will have deployed the following infrastructure:

![Workshop Architecture](/static/70-lab6-frontend/lab6_architecture_diagram.png)

## Prerequisites

Before starting, complete the setup instructions:

- **At an AWS event?** → [At an AWS Event](./10-intro/11-at-aws/)
- **Using your own account?** → [Self-Paced Setup](./10-intro/12-self-paced/)
