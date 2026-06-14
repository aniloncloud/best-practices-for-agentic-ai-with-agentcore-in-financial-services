---
title: "Best Practices for Agentic AI with AgentCore in Financial Services"
weight: 2
---

Welcome to the Best Practices for Agentic AI with AgentCore in Financial Services workshop. 

Building production-ready AI agents requires careful planning and execution across the entire development lifecycle. The difference between a prototype that impresses in a demo and an agent that delivers value in production is achieved through disciplined engineering practices, robust architecture, and continuous improvement.

This workshop explores essential best practices for building enterprise AI agents using [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/). We cover everything from initial deployment to organizational scaling, with practical guidance that you can apply immediately.

![Best Practices](/static/images/BestPractices-InANutshell.png)


## What is AgentCore?

Amazon Bedrock AgentCore is a modular set of capabilities to build, deploy and operate production-grade agents securely and scalably using any framework and model.

AgentCore capabilities are optimized to work together or individually, giving you the flexibility to integrate with any open-source frameworks


![AgentCore features Overview](/static/images/ac_overviewchart.png)

Amazon Bedrock AgentCore supports various interfaces for developing and deploying your agent code. At the lowest level, you can interact with the AgentCore APIs directly or through the [AWS SDKs](https://docs.aws.amazon.com/sdkref/latest/guide/overview.html). For a simpler development experience, the [AgentCore Python SDK](https://github.com/aws/bedrock-agentcore-sdk-python) and [AgentCore Typescript SDK](https://github.com/aws/bedrock-agentcore-sdk-typescript) provide higher-level abstractions for integrating with AgentCore features. The [AgentCore CLI](https://github.com/aws/agentcore-cli) builds on top of these, offering the best developer experience that lets you quickly scaffold, configure, and deploy agents. This workshop focuses on the AgentCore CLI.

### AgentCore features Used in This Workshop

| Features | Description |
|---------|-------------|
| **AgentCore harness** | Managed, declarative agent runtime — declare model, prompt, and tools in config (powered by Strands Agents) |
| **AgentCore runtime** | Serverless execution environment underlying the harness |
| **AgentCore gateway** | MCP-compatible proxy to centralize and secure tool access across agents |
| **AgentCore identity** | Secure credential management for API keys and OAuth providers |
| **AgentCore observability** | Tracing and monitoring via CloudWatch GenAI Observability |
| **AgentCore policy** | Cedar-based fine-grained authorization for tool access at the Gateway boundary |
| **AgentCore evaluations** | Continuous quality monitoring with built-in LLM-as-a-Judge evaluators |
| **AgentCore memory** | Persistent memory with semantic and summarization strategies (optional lab) |

## What You'll Build

In this hands-on workshop, you'll deploy a **Portfolio Advisor Agent** for a capital markets firm — defined as a declarative **AgentCore harness** (no orchestration code) — and progressively add security, governance, and observability through configuration using the AgentCore CLI.

> **Note:** The financial data, compliance rules, and trading scenarios in this workshop are simulated for educational purposes only and do not constitute actual regulatory guidance.


### Architecture Overview

At the end of the live session you will have deployed the following infrastructure:

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore harness (PortfolioAdvisor)
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
