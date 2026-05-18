---
title: "Summary"
weight: 90
---

## What You Built

Over the course of this workshop, you went from zero to a production-ready portfolio advisor agent using the AgentCore CLI and Kiro IDE:

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| 1 | Scaffolded a project, added stock analysis and compliance tools, tested locally with `agentcore dev` | AgentCore CLI, AgentCore Runtime (local) |
| 2 | Added persistent memory so the agent remembers client preferences and conversation summaries across sessions, first deploy to cloud | AgentCore Memory, AgentCore Runtime |
| 3 | MCPified an existing Lambda function (portfolio risk check) through AgentCore Gateway so any agent can discover and call it | AgentCore Gateway |
| 4 | Explored session management and observability — traces, logs, and metrics in CloudWatch | AgentCore Observability |
| 5 | Secured the runtime and gateway with Cognito JWT authentication, end-to-end token propagation | AgentCore Identity |
| 6 | Configured continuous quality monitoring with built-in evaluators (goal success, correctness, tool selection) | AgentCore Evaluations |
| 7 | Built a web chat interface with Cognito login that connects to the deployed agent | Combining all |
| 8 | Added fine-grained governance with Cedar policies to control trade execution based on quantity, ticker restrictions, and order type | AgentCore Policy |
| 9 | Deployed the agent into a VPC for private network isolation with VPC endpoints for AWS service connectivity | AgentCore Runtime (VPC mode) |
| 10 | Optimized session lifecycle, evaluation sampling rate, and built a CloudWatch cost monitoring dashboard | Cost optimization |

## Key Takeaways

**The AgentCore CLI abstracts infrastructure complexity.** You never wrote a Dockerfile, configured an ECR repository, or manually created IAM roles. A single `agentcore deploy` handled packaging, uploading, provisioning, and wiring everything together.

**AgentCore is framework and model agnostic.** This workshop used Strands Agents with Claude on Bedrock, but the same CLI and runtime work with LangGraph, CrewAI, OpenAI Agents SDK, Google ADK, and any foundation model.

**Memory is what separates a demo from a product.** Without memory, every conversation starts from zero. AgentCore Memory gives your agent the ability to recall facts, summarize past interactions, and build on previous context — turning a stateless prototype into something customers actually want to use.

**AgentCore Gateway turns existing APIs into agent tools.** Organizations already have valuable business logic in Lambda functions, REST APIs, and internal services. Gateway lets you MCPify them — exposing them as discoverable, authenticated MCP tools — without changing a single line of the original code. The portfolio risk check Lambda is just one example of six supported target types.

**Security is a configuration change, not a rewrite.** Adding Cognito JWT authentication to both the runtime and the gateway required few code changes to the agent itself — just a few fields in `agentcore.json`, token propagation from Runtime to Gateway and authorization configuration on your MCP Client. The same pattern works with any OAuth 2.0 compliant identity provider.

**Governance belongs outside the agent.** AgentCore Policy enforces business rules at the Gateway boundary using Cedar policies — deterministically, outside agent code. The agent doesn't need to know about spending limits or access controls. You can add, update, or remove policies without redeploying your agent, and every decision is logged for audit.

**Observability and evaluation come for free.** Every invocation is automatically instrumented with OpenTelemetry — you don't have to opt in, but you can opt out. Adding continuous quality evaluation on top was two commands. The hard part of production monitoring is already done for you.

**VPC isolation is a configuration change.** Moving from public to VPC mode required changing one field in `agentcore.json` and providing subnet/security group IDs. For financial services workloads where regulatory compliance mandates private network connectivity, this is a critical capability that AgentCore makes trivial.

**Cost optimization is ongoing, not one-time.** Right-sizing session timeouts, evaluation sampling rates, and monitoring token usage are essential for production financial services workloads. AgentCore's CloudWatch integration gives you the metrics to make data-driven decisions about cost vs. quality tradeoffs.

## Clean Up

To avoid ongoing charges, tear down all resources created during this workshop.

### AgentCore resources

:::code{language=bash}
agentcore remove all
agentcore deploy
:::

This removes the AgentCore Runtime, Memory, Gateway, Identity, and Evaluation resources.

### Prerequisites CloudFormation stack

:::code{language=bash}
aws cloudformation delete-stack --stack-name agentcore-workshop-prereqs
:::

This removes the Cognito User Pool, VPC resources, the portfolio risk check and trade execution Lambda functions, IAM roles, and all SSM parameters.

Verify the stack deletion is complete:

:::code{language=bash}
aws cloudformation wait stack-delete-complete --stack-name agentcore-workshop-prereqs
:::

## What's Next?

- Browse the [AgentCore Samples repository](https://github.com/awslabs/agentcore-samples) for ready-to-deploy examples covering different frameworks, use cases, and AgentCore features
- Explore the [AgentCore CLI documentation](https://github.com/aws/agentcore-cli) for advanced features like VPC networking, container deployments, and policy engines

- Explore the [AgentCore documentation](https://docs.aws.amazon.com/bedrock-agentcore/) to understand more about AgentCore and its services

## Thank You!

We hope this workshop gave you a clear path from prototype to production with Amazon Bedrock AgentCore. If you have feedback, please share it with your workshop facilitator or open an issue on the [AgentCore CLI GitHub repository](https://github.com/aws/agentcore-cli).
