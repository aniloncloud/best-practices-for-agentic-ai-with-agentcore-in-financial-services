---
title: "Summary"
weight: 90
---

## What You Built

Over the course of this workshop, you deployed a production-ready portfolio advisor agent using the AgentCore CLI:

### Live Session Labs (60 minutes)

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| Foundations | Learned agent planning, observability strategy, "no code changes" philosophy | (reading — no services) |
| Lab 1: Deploy to the AgentCore Harness | Deployed declarative harness; right-sized the model live | AgentCore Harness (Runtime) |
| Lab 2: Connect Tools with Gateway + JWT Auth | Centralized tools via Gateway with JWT authentication and IAM credential patterns | AgentCore Gateway + Identity |
| Lab 3: Govern Agent Actions with Cedar Policies | Added Cedar policies for trade limits and restricted tickers, explored agentic explainability | AgentCore Policy |

### Self-Paced Labs (continue after the session)

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| Observability Deep Dive | Explored traces, session isolation, token metrics, CloudWatch dashboards | CloudWatch GenAI Observability |
| OAuth Token Flows | Deep dive into M2M token flows and token lifecycle management | AgentCore Identity |
| Enterprise Tool Registry | Published and governed a Market Data MCP server org-wide via the publish → review → approve → search workflow, with a handoff to the Gateway (Lab 2) for agent use | AWS Agent Registry (+ AgentCore Gateway) |
| Evaluations | Configured continuous quality monitoring with built-in evaluators | AgentCore Evaluations |
| VPC Networking | Deployed agent into VPC with private subnet isolation and VPC endpoints | AgentCore Runtime (VPC mode) |
| Memory | Added persistent memory with SEMANTIC and SUMMARIZATION strategies | AgentCore Memory |
| Frontend | Built a web chat interface with Cognito login connected to the deployed agent | All services combined |
| Cost Optimization | Optimized session lifecycle, evaluation sampling rate, and built a cost monitoring dashboard | Cost optimization |

## Key Takeaways

**The AgentCore CLI abstracts infrastructure complexity.** You never wrote a Dockerfile, an agent orchestration loop, an ECR repository, or manually created IAM roles. You declared the agent in `harness.json`, and a single `agentcore deploy` handled provisioning, wiring, and observability.

**Gateway centralizes tool access.** Organizations already have valuable business logic in Lambda functions and APIs. Gateway lets you MCPify them — exposing them as discoverable, authenticated tools — without changing the original code.

**Security is a configuration change, not a rewrite.** Adding Cognito JWT authentication required a few config fields — and zero agent code: inbound JWT controls who can call the agent, and the harness fetches an M2M token to call the Gateway for you. The same pattern works with any OAuth 2.0 compliant identity provider.

**Governance belongs outside the agent.** AgentCore Policy enforces business rules at the Gateway boundary using Cedar policies — deterministically, outside agent code. The agent can't bypass them, and every decision is logged for audit.

**Explainability is built from traces.** By combining agent reasoning traces with Cedar policy decision logs, you get a complete per-transaction audit record — satisfying regulatory requirements without additional code.

**Observability and evaluation come for free.** Every invocation is automatically instrumented with OpenTelemetry. Adding continuous quality evaluation was two commands. The hard part of production monitoring is already done.

**VPC isolation is a configuration change.** Moving from public to VPC mode required two fields in `agentcore.json`. For financial services workloads where regulatory compliance mandates private network connectivity, AgentCore makes this trivial.

## Clean Up

To avoid ongoing charges, tear down all resources created during this workshop.

### AgentCore resources

:::code{language=bash}
agentcore remove all
agentcore deploy
:::

This removes the AgentCore Runtime, Gateway, Policy, and Evaluation resources.

### Prerequisites CloudFormation stack

:::code{language=bash}
aws cloudformation delete-stack --stack-name agentcore-workshop-prereqs
:::

This removes the Cognito User Pool, VPC resources, Lambda functions, IAM roles, and SSM parameters.

Verify the stack deletion is complete:

:::code{language=bash}
aws cloudformation wait stack-delete-complete --stack-name agentcore-workshop-prereqs
:::

## What's Next?

- Browse the [AgentCore Samples repository](https://github.com/awslabs/agentcore-samples) for ready-to-deploy examples
- Explore the [AgentCore CLI documentation](https://github.com/aws/agentcore-cli) for advanced features
- Explore the [AgentCore documentation](https://docs.aws.amazon.com/bedrock-agentcore/) for deeper service understanding

## Thank You!

We hope this workshop gave you a clear path from prototype to production with Amazon Bedrock AgentCore. If you have feedback, please share it with your workshop facilitator or open an issue on the [AgentCore CLI GitHub repository](https://github.com/aws/agentcore-cli).
