# Facilitator Guide: Best Practices for Agentic AI with AgentCore in Financial Services (IND306)

---

## Workshop Overview

**Best Practices for Agentic AI with AgentCore in Financial Services** teaches participants how to take a fully assembled AI agent and incrementally harden it for financial services production — adding tools, authentication, governance, observability, evaluations, and network isolation across six focused labs.

The workshop follows a single use case from start to finish: a **capital markets portfolio advisor agent** that handles stock analysis, compliance rule lookups, portfolio risk assessment, and trade execution. All financial data is simulated.

**What Participants Will Learn:** Participants arrive to a pre-provisioned environment — the agent workspace, infrastructure, and credentials are all ready. There is no scaffolding phase. Participants deploy the agent in Lab 1 and spend the remaining time adding production-grade capabilities through configuration and agentcore CLI commands.

**Learning Objectives:**
- Deploy a pre-built AgentCore agent and verify it produces CloudWatch traces (`agentcore deploy`)
- Centralize tools by connecting Lambda functions through AgentCore Gateway (JWT passthrough and IAM credential patterns)
- Secure the agent and gateway with JWT-based Cognito authentication
- Govern agent actions with deterministic Cedar policies (trade quantity limits, restricted securities) and surface reasoning with Agentic Explainability
- Monitor agent quality continuously using AgentCore Evaluations and CloudWatch GenAI Observability dashboards
- Deploy the agent in a VPC with private subnet isolation and VPC endpoints

**Target Audience:** Solutions Architects, Developers, and Technical Decision Makers in financial services. Participants should have basic AWS console navigation and Python experience. Familiarity with financial markets concepts is helpful but not required — all financial data is simulated.

---

## Prerequisites / Facilitator Preparation

### What Is Pre-Provisioned

The following resources are provisioned before participants arrive. Participants do not create any of these — they consume them through SSM Parameter Store references and the pre-built agent workspace.

| Resource | Details |
|----------|---------|
| VS Code Server | Browser-based IDE available immediately; no local install required |
| Agent workspace | `~/PortfolioAdvisor/` — complete project with agent code, tools, and dependencies installed |
| Cognito User Pool | M2M client (client_credentials flow), web client (auth code flow), test user `workshopuser@example.com` / `WorkshopPass1!` |
| Lambda functions | `workshop-check-portfolio-risk`, `workshop-execute-trade` |
| VPC | Private subnets, NAT Gateway, VPC endpoints for AgentCore, Bedrock, SSM, CloudWatch, S3, DynamoDB |
| SSM Parameter Store | Parameters under `/app/portfolioadvisor/agentcore/` (Lambda ARNs, Cognito config, VPC resource IDs) |
| CloudWatch | GenAI Observability enabled and dashboard pre-configured |

### Facilitator Preparation

- Walk through the entire workshop yourself before delivering it. Budget approximately 3 hours for your first run-through. Because the agent code is pre-written, your time goes toward understanding the agentcore CLI commands and configuration changes in each lab — not debugging code.
- Test by launching a test event in Workshop Studio, not just by running code locally. Workshop Studio accounts are pre-configured differently from personal accounts.
- Review `static/prereqs.yaml` to understand what the pre-provisioning stack creates. This helps you answer participant questions about why certain resources already exist.
- Read the Troubleshooting section of this guide before your first delivery.
- Ensure VS Code Server is accessible in the Workshop Studio environment. All labs use the browser-based VS Code terminal — participants do not need a local IDE.

### Service Requirements and Quotas

**Services used:** Amazon Bedrock (Claude Sonnet), Amazon Cognito, AWS Lambda, Amazon VPC, Amazon EC2 (ENIs), AWS Systems Manager Parameter Store, Amazon CloudWatch, Amazon Bedrock AgentCore (Runtime, Gateway, Evaluations, Policy)

**Model access:** Bedrock model access for **Claude Sonnet** must be enabled in **us-west-2** before participants start. This is typically pre-enabled in Workshop Studio accounts, but verify it before the event. In the Bedrock console: Model access → Request model access → Claude Sonnet. Activation takes approximately 1 minute.

**Region:** This workshop runs in **us-west-2 only.** All AgentCore features used are generally available in us-west-2. SSM parameter names, Lambda function names, and VPC endpoint service names are hardcoded to us-west-2. Do not attempt to run the workshop in other regions.

**Cost per participant:** approximately $2–5 USD for a full workshop run.

**Quota considerations:**

| Service | Default Limit | Notes |
|---------|--------------|-------|
| VPCs per region | 5 (default) | Pre-provisioned; participants do not create additional VPCs. Verify the account limit before large events. |
| Cognito User Pools | 60 per account | Pre-provisioned; one pool per participant account. |
| Lambda functions | 75 concurrent | The 2 workshop Lambda functions are low-traffic and synchronous; no quota issues expected. |
| AgentCore Runtimes | Varies | Check current service quotas in the Bedrock AgentCore console before large events. |

For large events (20+ participants): verify AgentCore Runtime quota headroom at least one week in advance.

---

## What Changed from the Original Workshop

The original workshop had participants scaffold, write, and iteratively build the agent code across 10 labs. That model spent the first 30 minutes on project creation and code writing before any cloud deployment.

**The new model pre-provisions everything.** The agent workspace at `~/PortfolioAdvisor/` is fully populated when participants open their browser. Lab 1 is now a 15-minute deploy-and-verify step, not a 30-minute code-writing step.

**Pacing implications:**

- **Lab 1 is shorter by design.** Participants run `agentcore deploy` within the first few minutes. The saved time is for discussion — walk through the project structure, explain what the pre-built tools do, and answer questions about the deployment process before moving on.
- **There is no `agentcore create` or `agentcore dev` step in the core labs.** The agent already exists. Participants deploy it, then modify configuration (agentcore.json) and redeploy to add capabilities. The only file participants edit is `agentcore.json` — and in some labs, they run CLI commands that update it automatically.
- **Labs focus on configuration, not construction.** Labs 3 (Gateway), 4 (Security), and 6 (VPC) involve direct `agentcore.json` edits plus one or two CLI commands. Emphasize that this is intentional: in production, governance and network isolation are infrastructure concerns, not application code concerns.
- **The "no code changes" message lands harder.** Because participants spent Lab 1 looking at the pre-written agent code, demonstrating in Labs 4 and 6 that the code didn't change at all — only the config did — is more impactful.

---

## Recommended Agenda

### Core Format (~3 hours total)

| Time | Duration | Activity | Key Focus and Tips |
|------|----------|----------|--------------------|
| 0:00–0:10 | 10 min | Welcome and Setup | Introduce objectives, confirm VS Code Server access, verify region is us-west-2. Show the final architecture diagram so participants understand where they're headed. Direct participants to read the **Foundations** page (~5 min read) during this time. |
| 0:10–0:25 | 15 min | **Lab 1: Runtime** | Run `agentcore deploy`, confirm runtime reaches READY state, invoke the agent. **Tip:** Walk through the project structure while the 2–3 minute deploy runs. Use this time to explain the pre-built tools (`get_stock_analysis`, `get_compliance_rules`). |
| 0:25–0:40 | 15 min | **Lab 1B: Observability** | Inspect traces in CloudWatch, test session isolation (Session A vs Session B), examine multi-tool traces, review token metrics. **Tip:** If traces haven't appeared yet (1-2 min delay), discuss the three-layer observability model from the Foundations page while waiting. This lab lands the "instrument from day one" message. |
| 0:40–1:05 | 25 min | **Lab 2: Gateway** | Add Lambda tools via `agentcore add gateway` and `agentcore add gateway-target`. Cover JWT passthrough vs IAM credential patterns. Connect the Gateway MCP client. **Tip:** This is one of the two longest labs. The concept of "MCPifying an existing Lambda without changing its code" is the key insight to land. The Gateway deploy takes 2–3 minutes — use it for Q&A on credential patterns. |
| 1:05–1:25 | 20 min | **Lab 3: Security** | Add JWT auth via `authorizerConfiguration` in agentcore.json for both Runtime and Gateway. Obtain a Cognito token and invoke with it. **Tip:** Token retrieval can trip participants up. Demo the token fetch live before participants try it. Emphasize that tokens expire after 60 minutes — this matters in Labs 4 through 6. |
| 1:25–1:35 | 10 min | Break | Remind participants that tokens expire 60 minutes after issuance. Encourage re-fetching the token after the break if they're close to the limit. |
| 1:35–2:00 | 25 min | **Lab 4: Governance** | Create a Cedar Policy Engine, write `forbid` and `permit` statements, attach in ENFORCE mode. Demo the large trade denial (5000 shares of MSFT). Cover Agentic Explainability (reasoning traces). **Tip:** The denied trade demo is the most impactful moment in the workshop — run it in your own browser first, then let participants try. Emphasize that the agent code didn't change at all. Read the compliance disclaimer note below before this lab. |
| 2:00–2:15 | 15 min | **Lab 5: Evaluations** | Add `online-eval` with built-in evaluators (GoalSuccessRate, Correctness, ToolSelectionAccuracy) at 100% sampling. Generate test traffic. Check the CloudWatch GenAI Observability dashboard. **Tip:** Kick off test traffic early — evaluation results take a few minutes to appear. |
| 2:15–2:30 | 15 min | **Lab 6: VPC** | Edit `networkMode` and `vpcConfig` in agentcore.json with pre-provisioned subnet and security group IDs from SSM. Redeploy. Verify agent still responds. **Tip:** VPC deploy takes 3–5 minutes for ENI provisioning. Use the pause for discussion about FSI network isolation requirements. Rollback instructions are in the lab if there are connectivity issues. |
| 2:30–2:40 | 10 min | Wrap-up and Summary | Review the three FSI security answers (Labs 3, 4, 6). Discuss the path from prototype to production. Share resources. Collect feedback via Workshop Studio survey. |

**Total core time:** ~2 hours 40 minutes (per agenda above). Foundations reading happens concurrently with setup.

### Optional Stretch Labs (~1 additional hour)

| Lab | Duration | Topic | When to Use |
|-----|----------|--------|-------------|
| **Lab 2B: Tool Registry** | ~20 min | Enterprise tool approval workflow: review security posture of a Market Data MCP server, add to Gateway, verify agent discovers new tools | Run for audiences focused on enterprise tooling governance and platform engineering. Best fit right after Lab 2 but can be done anytime after. |
| **Lab 7: Memory** | ~20 min | Persistent client memory with SEMANTIC and SUMMARIZATION strategies | Run if group finishes core early or requests memory capabilities |
| **Lab 8: Frontend** | ~20 min | Flask chat portal with Cognito login and AgentCore REST invocation | Run for audiences who want a complete end-to-end client demo |
| **Lab 9: Cost Optimization** | ~15 min | Session lifecycle (`sessionConfig`), eval sampling rate tuning (100% → 20%), memory retention | Run for FSI audiences focused on production cost controls |

---

## Pacing Tips

- **Labs 2 and 4 run longest.** Lab 2 (Gateway) involves the most CLI commands; Lab 4 (Governance) involves the most new concepts (Cedar syntax, ENFORCE mode, Agentic Explainability). Build in buffer around both. If a lab is running over, skip the bonus steps rather than rushing the core.
- **Lab 1B can be shortened if needed.** If time is tight, the session isolation test (Step 2) and token metrics (Step 4) are the most impactful. The trace inspection (Step 1) and checklist (Step 5) can be compressed to a facilitator demo.
- **Labs 5 and 6 can be combined if short on time.** Both are 15-minute labs. If the group is running 10–15 minutes behind after Lab 4, present Labs 5 and 6 as a combined "observability and network" block. The key commands in each lab are independent and can run in parallel.
- **Every `agentcore deploy` takes 2–3 minutes.** Use these pauses for Q&A on the concepts just covered rather than letting participants sit idle. Good prompts: "What other tools would you connect to the Gateway in your workload?" or "What Cedar policies would you write for your compliance requirements?"
- **VPC deploy (Lab 6) takes 3–5 minutes** for ENI provisioning. This is the longest single pause in the workshop. Use it to walk through the architecture diagram one more time and explain what the VPC endpoints eliminate (public internet paths for Bedrock, SSM, and CloudWatch).
- **Token expiration: 60 minutes.** Remind the group at the break (between Labs 3 and 4). Participants who took longer on Labs 1–3 or who paused during the break may hit token expiration during Labs 4–6. The fix is one `aws cognito-idp initiate-auth` command — point participants there first when they see authentication errors.
- **With 20+ participants:** pair faster participants with slower ones during Labs 2 and 4. If a participant falls two or more labs behind, provide the reference `agentcore.json` for the completed lab so they can catch up rather than stay stuck.

---

## Delivery Tips

### Setup

- Start provisioning Workshop Studio accounts at least 15 minutes before the session begins. The pre-provisioning stack takes 3–5 minutes to deploy.
- Verify VS Code Server is reachable and the `~/PortfolioAdvisor/` directory is populated before participants start.
- Keep one fully-deployed environment for live demos. If you ran the workshop yourself in advance, do not tear it down until after the event.
- Confirm Claude Sonnet model access is enabled in Bedrock for us-west-2.

### FSI-Specific Facilitation Notes

**Compliance disclaimer:** Remind participants at the beginning of the workshop — and again before Lab 4 — that all financial data, compliance rules, and trade policies in this workshop are **simulated for educational purposes only.** The Cedar policies in Lab 4 illustrate how governance works; they do not constitute actual regulatory guidance. Real-world implementations require review by legal and compliance teams.

**Audience expectations:** FSI audiences typically arrive with strong opinions about security architecture. Lean into this — acknowledge the concerns and use Labs 3, 4, and 6 as direct answers:
- "You're worried about unauthorized API calls" → **Lab 3** (JWT authentication on Runtime and Gateway)
- "You need deterministic trade controls that can't be prompt-injected away" → **Lab 4** (Cedar policies in ENFORCE mode)
- "Your data cannot leave the private network" → **Lab 6** (VPC isolation with private subnets and VPC endpoints)

**Regulatory context:** When discussing VPC isolation (Lab 6) and policy governance (Lab 4), you can reference SEC Rule 17a-4, FINRA Rule 3110, SOX, and MiFID II as motivating frameworks. Be explicit that this workshop provides architectural patterns — it does not constitute compliance guidance and every firm's requirements differ.

**FSI architects and technical leads** will frequently ask about Guardrails integration. The answer: Guardrails cannot be attached to AgentCore Runtime or Gateway as infrastructure configuration. To apply Guardrails, use the `guardrailConfig` parameter in the Bedrock Converse API within the agent code itself. See Additional Notes for detail.

### Common Facilitation Strategies

- **Show the final architecture at the start.** The `static/images/workshop-architecture.png` diagram shows the completed system. Participants retain more when they know where they're heading.
- **Explain "why" before "how."** Each lab opens with a business problem (e.g., "any caller can invoke the agent without authentication"). Spend 30 seconds on the problem before walking through the solution.
- **Use the Cedar denial as a live demo.** In Lab 4, walk through the large trade denial (5000 shares of MSFT) in your own browser before participants try it. The visual of the agent explaining it cannot execute the trade — without any code change — is the workshop's single most effective demo moment.
- **Use the `agentcore deploy` pauses.** Each deploy takes 2–3 minutes. Rather than silence, use this time to ask participants what they would connect to the Gateway next, or what Cedar policies would apply to their workload.
- **Reinforce the "no code changes" message.** In Labs 4 and 6, emphasize that the agent code didn't change — governance and network isolation were added entirely through configuration. This resonates strongly with organizations that manage production code change processes carefully.
- **Reference the pre-provisioned infrastructure as a model.** When participants ask how they would do this in their own environment, the pre-provisioning stack (`static/prereqs.yaml`) is a concrete starting point they can adapt.

---

## Troubleshooting

### Top Issues

#### 1. CDK Bootstrap Failed on First `agentcore deploy`

**Cause:** The AgentCore CLI uses AWS CDK internally. The first `agentcore deploy` in a given account and region requires CDK to be bootstrapped. Workshop Studio accounts typically have this pre-configured, but it can fail in edge cases.

**Fix:**
1. Run `npx cdk bootstrap aws://ACCOUNT_ID/us-west-2` manually in the `~/PortfolioAdvisor/agentcore/cdk/` directory.
2. Once bootstrap completes (about 2 minutes), retry `agentcore deploy`.

#### 2. Token Expired in Labs 4–6

**Cause:** Cognito access tokens expire after 60 minutes. Participants who spend extra time on earlier labs — or who pause for the break — hit this when they return to Labs 4–6.

**Fix:** Re-run the token retrieval command from Lab 3 Step 1 (the `aws cognito-idp initiate-auth` command). Point participants there first whenever they see an authentication error after Lab 3.

**Prevention:** Remind participants at the break (between Labs 3 and 4) that tokens expire after 60 minutes. Encourage them to re-fetch the token if they are close to the limit.

#### 3. `agentcore` Command Not Found

**Cause:** The AgentCore CLI is not installed or not on the PATH.

**Fix:**
- Verify: `agentcore --version`
- Install if missing: `npm install -g @aws/agentcore-cli` (check the Workshop Studio environment's pre-installed CLI version)
- If the VS Code Server terminal does not pick up the PATH change, close and reopen the terminal tab.

#### 4. Gateway Timeout After VPC Deployment (Lab 6)

**Cause:** ENIs are still provisioning in the private subnets, or the security group is missing HTTPS outbound (port 443) egress rules.

**Fix:**
1. Wait 3–5 minutes after `agentcore deploy` completes. VPC ENI attachment takes longer than a standard deploy.
2. Run `agentcore status` to confirm the runtime reports READY.
3. If still failing after 5 minutes, verify the security group allows outbound HTTPS: `aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID`.
4. If VPC issues cannot be resolved quickly, roll back to PUBLIC mode (Lab 6 Step 6 — remove `networkMode` and `vpcConfig` from agentcore.json and redeploy). The conceptual point of Lab 6 can be made without the participant's agent remaining in VPC mode.

#### 5. Model Access Denied on First Agent Invocation

**Cause:** Claude Sonnet model access is not enabled in the Bedrock console for us-west-2.

**Fix:** In the Bedrock console → Model access → Enable Claude Sonnet. Takes approximately 1 minute. This should be pre-configured in Workshop Studio accounts — verify before the event.

#### 6. VPC Limit Exceeded (Lab 6)

**Cause:** The account has hit the VPC-per-region limit. The VPC is pre-provisioned, so this should not occur unless the account already has several VPCs.

**Fix:** Delete unused VPCs in us-west-2, or request a limit increase via Service Quotas. Verify the account's VPC limit before large events.

### Module-Specific Issues

**Lab 1 (Runtime):**
- If `agentcore deploy` completes but `agentcore status` shows FAILED, check CloudWatch Logs for the Lambda deployment function for CDK errors. CDK bootstrap (issue 1 above) is the most common cause.
- If traces don't appear in CloudWatch after invocation, wait 1–2 minutes — CloudWatch GenAI Observability can have a short ingestion delay. Confirm the agent was invoked successfully (the CLI should print the agent response) before investigating traces.
- If the VS Code Server terminal opens to a different directory, navigate to `~/PortfolioAdvisor/` before running agentcore commands.

**Lab 2 (Gateway):**
- If the Lambda ARN retrieval fails, verify the pre-provisioning CloudFormation stack completed successfully: `aws ssm get-parameter --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn`.
- If the gateway target fails to add, confirm the Lambda ARN is valid and the IAM role has permission to invoke it. The CDK-generated role should have this automatically.
- If the agent doesn't discover the Gateway tool after redeployment, confirm `AGENTCORE_GATEWAY_MY_GATEWAY_URL` is in the agent's environment (injected automatically when the gateway is linked to the runtime).
- If the tool schema JSON fails with "Attribute type null is not yet supported", the `inputSchema` has a nested `"json"` wrapper. The `inputSchema` must have `"type": "object"` directly inside it, not wrapped in a `"json"` object.

**Lab 3 (Security):**
- If JWT auth is configured but invocations are still accepted without a token, check that `agentcore deploy` ran after editing agentcore.json. The `authorizerType` field is only applied on deploy.
- If `agentcore validate` fails after adding `authorizerConfiguration`, check for JSON syntax errors — missing commas between fields are common.
- When securing the Gateway, the original `my-gateway` must be removed and redeployed before creating `my-gateway-secure`. If the remove fails, check that no deployment is in progress.
- The `mcp_client/client.py` environment variable must match the new gateway name exactly: `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL` (not `MY_GATEWAY_URL`).

**Lab 4 (Governance):**
- Cedar policy action names use **triple underscores**: `ExecuteTrade___execute_trade` and `PortfolioRiskCheck___check_portfolio_risk`. A double-underscore or single-underscore will silently create a policy that never matches.
- After attaching the Policy Engine in ENFORCE mode, all tools behind the Gateway are subject to default-deny. If the portfolio risk check starts failing, it means `portfolio_risk_check_policy` was not created or not deployed.
- When creating Cedar policies, the `--validation-mode IGNORE_ALL_FINDINGS` flag is required because the Cedar validator doesn't know the principals exist at creation time.
- Agentic Explainability reasoning traces appear in CloudWatch under the same trace as the invocation. If they don't appear, verify the lab's explainability configuration block was added to agentcore.json and the runtime was redeployed.

**Lab 5 (Evaluations):**
- If traces don't appear in CloudWatch, confirm the agent was deployed (not just running locally). Evaluations are only active for cloud-deployed runtimes.
- Evaluation results take a few minutes to appear after traffic is generated. Generate test traffic at the start of the lab and check the dashboard toward the end.
- If adding a second `QualityMonitor` fails with a duplicate name error, the previous configuration must be paused first: `agentcore pause online-eval QualityMonitor`.

**Lab 6 (VPC):**
- The `networkMode` and `vpcConfig` fields must be edited directly in agentcore.json. There is no `--network-mode` CLI flag. This is explicitly documented in the lab.
- If VPC deploy fails with "invalid subnet", verify the subnet IDs retrieved from SSM are for the **private** subnets (not public). Private subnets have no direct route to the Internet Gateway.
- If the agent responds after VPC deployment but latency increased noticeably, this is expected — traffic now routes through VPC endpoints. It is not a failure.

**Optional Lab 7 (Memory):**
- Memory requires cloud deployment — `agentcore dev` does not use AgentCore Memory.
- If the memory recall test returns "I don't know anything about you", the memory extraction job may not have finished. Wait 1–2 minutes and retry with a new session ID.
- If deployment fails with a header-related error, check that `requestHeaderAllowlist` was added to the runtime entry in agentcore.json.

**Optional Lab 8 (Frontend):**
- If the login redirect loops back to the login page without signing in, confirm the web client ID was added to BOTH `allowedClients` arrays in agentcore.json — one in the runtime's `authorizerConfiguration` and one in the gateway's `authorizerConfiguration`.
- If the Flask app starts but the Runtime ARN shows NOT FOUND, the `deployed-state.json` file is either missing or doesn't contain the PortfolioAdvisor runtime entry. Run `agentcore status` to verify the runtime is deployed.
- If the chat sends a message but gets a 401 response, the session-stored token has expired. Log out and log back in via the Cognito hosted UI.

**Optional Lab 9 (Cost Optimization):**
- The `sessionConfig` block is a direct agentcore.json edit — no CLI flag exists for session lifecycle parameters.
- When re-adding `QualityMonitor` with 20% sampling, the old configuration must be paused first.

### Service Limits During Delivery

- **AgentCore Runtime quota exceeded:** If participants hit runtime creation limits, check the current quota in the Bedrock console under Service Quotas. For large events, request increases at least one week in advance.
- **Slow deploys:** AgentCore deploy times can increase during peak hours. If deploys consistently take more than 5 minutes, use the time for discussion and flag it in post-event notes.
- **Cognito token endpoint throttled:** Unlikely, but possible if many participants refresh tokens simultaneously. If this happens, stagger the token refresh commands across the room.

### When Nothing Works

1. Check Workshop Studio event logs for detailed error messages.
2. Run `agentcore status` — it gives a clean summary of what's deployed and what's not.
3. Ask the Workshop Studio Atlas Agent from the UI.
4. Ask in #workshop-studio-interest on Slack.
5. Add it to this guide after you fix it — the next facilitator will appreciate it.

---

## Resources

### For Facilitators

- **Source code and workshop content:** This repository
- **Pre-provisioning CloudFormation template:** `static/prereqs.yaml` — review before the event to understand what's pre-provisioned for participants
- **Support:** Workshop Studio Atlas Agent (from the Workshop Studio UI), or #workshop-studio-interest on Slack

### For Participants (share after the event)

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore CLI GitHub](https://github.com/aws/agentcore-cli)
- [AgentCore Samples (GitHub)](https://github.com/awslabs/agentcore-samples)
- [Cedar Policy Language](https://www.cedarpolicy.com/) — the open-source authorization language used in Lab 4
- [Strands Agents SDK](https://strandsagents.com/) — the Python agent framework used throughout the workshop
- [CloudWatch GenAI Observability for Bedrock AgentCore](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-GenAI-Observability-AgentCore.html)

---

## Post-Event Actions

- Terminate the event in Workshop Studio — cleanup is automatic.
- Remind participants who ran the workshop in their own AWS account to: run `agentcore remove all` from the `~/PortfolioAdvisor/` directory, then delete the pre-provisioning CloudFormation stack.
- Share the Resources links above with participants after the event.
- Collect feedback via the Workshop Studio survey.
- Update this guide if you found new issues or better approaches during delivery.

---

## Additional Notes

- **All financial data is simulated.** The stock prices, PE ratios, portfolio holdings, compliance rules, and trade limits in this workshop are fictional and exist solely to provide realistic-looking data for the portfolio advisor scenario. They do not reflect real market data.
- **All AgentCore features used are generally available in us-west-2** as of the workshop's publication date.
- **Framework-agnostic design, Python-specific code.** The workshop uses the Strands Agents SDK and Python 3.13 throughout. The AgentCore CLI supports other frameworks (LangChain, CrewAI, Google ADK, OpenAI Agents SDK), but all code samples are Python.
- **Guardrails and AgentCore infrastructure:** A common question from FSI participants is whether Bedrock Guardrails can be attached to AgentCore Runtime or Gateway at the infrastructure level (similar to how VPC endpoints are configured). The answer is **no** — Guardrails are not attachable to AgentCore Runtime or Gateway as infrastructure. To use Guardrails, configure the `guardrailConfig` parameter in the Bedrock Converse API calls within the agent code itself (in `model/load.py` or wherever the Bedrock client is configured).
- **Session ID minimum length:** AgentCore Runtime requires session IDs to be at least 33 characters. The workshop uses `uuid.uuid4()` (36 characters) throughout to satisfy this requirement. Shorter custom session IDs will be rejected with a validation error.
- **`agentcore.json` direct edits:** Three configuration areas require direct JSON file edits rather than CLI flags: `authorizerConfiguration` (Lab 3), `networkMode` and `vpcConfig` (Lab 6), and `sessionConfig` (Optional Lab 9). All other configuration is managed through CLI commands. Each lab that requires a direct edit includes an inline alert flagging this as an exception to the normal CLI workflow.
- **Cedar triple-underscore naming:** Cedar policy action names use three underscores as a separator between the Gateway target name and the tool function name. For example: `ExecuteTrade___execute_trade` and `PortfolioRiskCheck___check_portfolio_risk`. Using two underscores or one underscore will silently create a policy that never matches any action.
