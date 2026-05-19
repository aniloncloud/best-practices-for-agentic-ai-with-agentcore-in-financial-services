---
title: "Summary"
weight: 90
---

## What You Built

Over the course of this workshop, you deployed a production-ready portfolio advisor agent using the AgentCore CLI:

### Core Labs

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| Foundations | Learned agent planning, observability strategy, "no code changes" philosophy | (reading — no services) |
| 1 | Deployed pre-built agent to cloud | AgentCore Runtime |
| 1B | Explored traces, session isolation, token metrics, CloudWatch dashboards | CloudWatch GenAI Observability |
| 2 | Centralized tools via Gateway, learned JWT passthrough and IAM credential patterns | AgentCore Gateway |
| 3 | Secured Runtime and Gateway with Cognito JWT authentication | AgentCore Identity |
| 4 | Added Cedar policies for trade limits and restricted tickers, explored agentic explainability | AgentCore Policy |
| 5 | Configured continuous quality monitoring with built-in evaluators | AgentCore Evaluations |
| 6 | Deployed agent into VPC with private subnet isolation and VPC endpoints | AgentCore Runtime (VPC mode) |

### Optional Labs

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| 2B | Reviewed and approved a Market Data MCP server through enterprise tool governance workflow | AgentCore Gateway (Registry) |
| 7 | Added persistent memory with SEMANTIC and SUMMARIZATION strategies | AgentCore Memory |
| 8 | Built a web chat interface with Cognito login connected to the deployed agent | All services combined |
| 9 | Optimized session lifecycle, evaluation sampling rate, and built a cost monitoring dashboard | Cost optimization |

## Key Takeaways

**The AgentCore CLI abstracts infrastructure complexity.** You never wrote a Dockerfile, configured an ECR repository, or manually created IAM roles. A single `agentcore deploy` handled packaging, uploading, provisioning, and wiring everything together.

**Gateway centralizes tool access.** Organizations already have valuable business logic in Lambda functions and APIs. Gateway lets you MCPify them — exposing them as discoverable, authenticated tools — without changing the original code.

**Security is a configuration change, not a rewrite.** Adding Cognito JWT authentication to both Runtime and Gateway required a few fields in `agentcore.json` and one helper function in agent code. The same pattern works with any OAuth 2.0 compliant identity provider.

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
