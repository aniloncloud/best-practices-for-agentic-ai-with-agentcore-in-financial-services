---
title: "Summary"
weight: 90
---

## What You Built

Over the course of this workshop, you went from zero to a production-ready customer support agent using the AgentCore CLI and Kiro IDE:

| Lab | What You Did | AgentCore Services |
|-----|-------------|-------------------|
| 1 | Scaffolded a project, added local tools and an MCP integration (Exa AI), tested locally with `agentcore dev` | AgentCore CLI, AgentCore Runtime (local) |
| 2 | Added persistent memory so the agent remembers facts and conversation summaries across sessions, first deploy to cloud | AgentCore Memory, AgentCore Runtime |
| 3 | MCPified an existing Lambda function through AgentCore Gateway so any agent can discover and call it | AgentCore Gateway |
| 4 | Secured the runtime and gateway with Cognito JWT authentication, explored session management and observability | AgentCore Identity, AgentCore Observability |
| 5 | Configured continuous quality monitoring with built-in evaluators (goal success, correctness, tool selection) | AgentCore Evaluations |
| 6 | Built a web chat interface with Cognito login that connects to the deployed agent | Combining all |
| 7 | Added fine-grained governance with Cedar policies to control tool access based on input parameters | AgentCore Policy |

## Key Takeaways

**The AgentCore CLI abstracts infrastructure complexity.** You never wrote a Dockerfile, configured an ECR repository, or manually created IAM roles. A single `agentcore deploy` handled packaging, uploading, provisioning, and wiring everything together.

**AgentCore is framework and model agnostic.** This workshop used Strands Agents with Claude on Bedrock, but the same CLI and runtime work with LangGraph, CrewAI, OpenAI Agents SDK, Google ADK, and any foundation model.

**Memory is what separates a demo from a product.** Without memory, every conversation starts from zero. AgentCore Memory gives your agent the ability to recall facts, summarize past interactions, and build on previous context — turning a stateless prototype into something customers actually want to use.

**AgentCore Gateway turns existing APIs into agent tools.** Organizations already have valuable business logic in Lambda functions, REST APIs, and internal services. Gateway lets you MCPify them — exposing them as discoverable, authenticated MCP tools — without changing a single line of the original code. Lambda is just one of six supported target types.


**Security is a configuration change, not a rewrite.** Adding Cognito JWT authentication to both the runtime and the gateway required few code changes to the agent itself — just a few fields in `agentcore.json`, token propagation from Runtime to Gateway and authorization configuration on your MCP Client. The same pattern works with any OAuth 2.0 compliant identity provider.

**Governance belongs outside the agent.** AgentCore Policy enforces business rules at the Gateway boundary using Cedar policies — deterministically, outside agent code. The agent doesn't need to know about spending limits or access controls. You can add, update, or remove policies without redeploying your agent, and every decision is logged for audit.

**Observability and evaluation come for free.** Every invocation is automatically instrumented with OpenTelemetry — you don't have to opt in, but you can opt out. Adding continuous quality evaluation on top was two commands. The hard part of production monitoring is already done for you.

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

This removes the Cognito User Pool, the warranty check Lambda function, IAM roles, and all SSM parameters.

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
