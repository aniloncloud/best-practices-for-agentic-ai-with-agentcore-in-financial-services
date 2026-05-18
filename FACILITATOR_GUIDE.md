# Facilitator Guide: Best Practices for Agentic AI with AgentCore in Financial Services (IND306)

---

## Workshop Overview

**Best Practices for Agentic AI with AgentCore in Financial Services** teaches participants how to build a production-ready AI agent using Amazon Bedrock AgentCore — from a local prototype all the way to a VPC-isolated, policy-governed, cost-optimized deployment.

The workshop follows a single use case from start to finish: a **capital markets portfolio advisor agent** that handles stock analysis, compliance rule lookups, portfolio risk assessment, and trade execution. All financial data is simulated.

**What Participants Will Learn:** Participants scaffold a portfolio advisor agent using the AgentCore CLI, then incrementally add production-grade features across 10 labs — persistent memory, centralized tool management via Gateway, JWT authentication, continuous quality evaluation, a client-facing web UI, Cedar governance policies, VPC isolation, and cost optimization.

**Learning Objectives:**
- Scaffold and customize an AI agent using the AgentCore CLI (`agentcore create`, `agentcore dev`, `agentcore deploy`)
- Add persistent client memory using AgentCore Memory with SEMANTIC and SUMMARIZATION strategies
- Centralize tools by MCPifying existing Lambda functions through AgentCore Gateway
- Secure the agent and gateway with JWT-based Cognito authentication
- Monitor agent quality continuously using AgentCore Evaluations and CloudWatch GenAI dashboards
- Build a client-facing web interface that authenticates users via Cognito's hosted UI
- Govern agent actions with deterministic Cedar policies (trade quantity limits, restricted securities)
- Deploy the agent in a VPC with private subnet isolation and VPC endpoints
- Optimize session lifecycle, evaluation sampling rate, and memory retention for FSI workloads at scale

**Target Audience:** Solutions Architects, Developers, and Technical Decision Makers in financial services. Participants should have basic AWS console navigation and Python experience. Familiarity with financial markets concepts is helpful but not required — all financial data is simulated.

---

## Prerequisites

### Facilitator Preparation

- Walk through the entire workshop yourself before delivering it. Budget approximately 3.5 hours for your first run-through, including time to understand the agent code changes in each lab.
- Test by launching a test event in Workshop Studio, not just by running the code locally in your own account. Workshop Studio accounts are pre-configured differently from personal accounts and the experience should match what participants will have.
- The **prerequisites CloudFormation stack** (`prereqs.yaml` in the `static/` directory) provisions the following shared resources that participants depend on throughout the workshop:
  - **Amazon Cognito User Pool** with two app clients: an M2M client (for `client_credentials` flow) and a web client (for authorization code flow)
  - **Two Lambda functions**: `workshop-check-portfolio-risk` (used in Lab 3) and `workshop-execute-trade` (used in Lab 8)
  - **VPC** with two public subnets, two private subnets, a NAT Gateway, and an Internet Gateway
  - **Seven VPC endpoints**: Interface endpoints for `bedrock-agentcore`, `bedrock-agentcore-gateway`, `bedrock-runtime`, `ssm`, and `logs`; Gateway endpoints for S3 and DynamoDB
  - **Security group** allowing HTTPS (port 443) outbound from agent ENIs
  - **SSM Parameter Store parameters** under `/app/portfolioadvisor/agentcore/` that participants retrieve throughout the workshop (Lambda ARNs, Cognito config, VPC resource IDs)
- Read the Troubleshooting section of this guide before your first delivery.
- Ensure Kiro IDE is available in the Workshop Studio environment. Kiro is the recommended IDE throughout the workshop — lab instructions reference its terminal, split-terminal, and AI chat panel features.

### Service Requirements & Quotas

**Services used:** Amazon Bedrock (Claude Sonnet model), Amazon Cognito, AWS Lambda, Amazon VPC, Amazon EC2 (ENIs), AWS Systems Manager Parameter Store, Amazon CloudWatch, Amazon Bedrock AgentCore (Runtime, Memory, Gateway, Evaluations, Policy)

**Model access:** Bedrock model access for **Claude Sonnet** must be enabled in **us-west-2** before participants start. This is typically pre-enabled in Workshop Studio accounts, but verify it before the event. In the Bedrock console: Model access → Request model access → Claude Sonnet. Activation takes approximately 1 minute.

**Quota considerations:**

| Service | Default Limit | Notes |
|---------|--------------|-------|
| VPCs per region | 5 (default) | Workshop Studio accounts typically have this raised. Verify before large events. Each participant needs 1 VPC from the CFN stack — the AgentCore CLI does not create additional VPCs. |
| Cognito User Pools | 60 per account | Default sufficient for up to 50 participants (1 pool per participant) |
| Lambda functions | 75 concurrent by default | The 2 workshop Lambda functions are low-traffic and synchronous; no quota issues expected |
| AgentCore Runtimes | Varies | Check current service quotas in the Bedrock AgentCore console before large events |

**For large events (20+ participants):** Verify VPC and Bedrock model quota headroom at least one week in advance.

**Region:** This workshop runs in **us-west-2 only**. All AgentCore features used in the workshop are generally available in us-west-2. Do not attempt to run it in other regions — SSM parameter names, Lambda function names, and VPC endpoint service names are all hardcoded to us-west-2.

### Participant Prerequisites

- Basic AWS console navigation (can find Lambda functions, CloudWatch, SSM Parameter Store)
- Python experience — participants don't write Python from scratch but need to read, copy, and paste multi-function Python files
- Command-line familiarity — all labs run in a terminal; participants run `agentcore`, `aws`, and `uv` commands
- Familiarity with financial markets concepts (stocks, portfolios, trade types) is helpful but not required
- Modern web browser — participants will access the Cognito hosted login page and a local Flask app in Lab 7

---

## Recommended Agenda

### Standard 3.5-Hour Format

| Time | Duration | Activity | Key Focus & Tips |
|------|----------|----------|------------------|
| 0:00–0:10 | 10 min | Welcome & Setup | Introduce objectives, confirm Workshop Studio access, open Kiro IDE, confirm region is us-west-2. Show the final architecture diagram so participants understand where they're headed. |
| 0:10–0:30 | 20 min | Lab 1: Build Prototype | **Focus:** `agentcore create`, project structure, local tools (`get_stock_analysis`, `get_compliance_rules`), `agentcore dev` interactive TUI, `agentcore deploy`. **Tip:** Make sure `uv` and Python 3.13 work before moving on. Lab 1 ends with the first cloud deploy — if CDK bootstrap hasn't run, it will happen silently and takes ~2 minutes. |
| 0:30–0:50 | 20 min | Lab 2: Add Memory | **Focus:** `agentcore add memory`, SEMANTIC vs SUMMARIZATION strategies, wiring `AgentCoreMemorySessionManager` into the agent, first redeploy with memory. **Tip:** Memory requires cloud deployment — local dev does not use memory. Remind participants to wait 1-2 minutes between sessions when testing memory recall. |
| 0:50–1:20 | 30 min | Lab 3: Gateway & Tools | **Focus:** MCPifying an existing Lambda via `agentcore add gateway` and `agentcore add gateway-target`, tool schema JSON, connecting the Gateway MCP client. **Tip:** This is the longest lab. Keep participants moving — the concept of "MCPifying an existing Lambda without changing its code" is the key insight to land. The Gateway deploy takes ~2 minutes. |
| 1:20–1:35 | 15 min | Lab 4: Observability | **Focus:** Session continuity, CloudWatch GenAI traces, logs, and metrics. **Tip:** This is a lighter lab — use it to reinforce what's been deployed so far. Encourage participants to explore the CloudWatch GenAI Observability dashboard. |
| 1:35–1:55 | 20 min | Lab 5: JWT Authentication | **Focus:** JWT auth with Cognito, `authorizerConfiguration` in `agentcore.json`, JWT extraction in agent code for user_id, securing both Runtime and Gateway. **Tip:** Token retrieval can trip participants up. Demo the Cognito user creation and token fetch steps live before participants try it. Emphasize that tokens expire after 60 minutes — this will matter in later labs. |
| 1:55–2:05 | 10 min | Break | Encourage participants to stay nearby for the second half. |
| 2:05–2:20 | 15 min | Lab 6: Evaluations | **Focus:** `agentcore add online-eval`, built-in evaluators (GoalSuccessRate, Correctness, ToolSelectionAccuracy), 100% sampling for testing, CloudWatch GenAI Observability dashboards. **Tip:** Evaluation results take a few minutes to appear in CloudWatch. Generate test traffic early in the lab so results are visible by the time participants look at the dashboard. |
| 2:20–2:40 | 20 min | Lab 7: Client Portal | **Focus:** Flask frontend, Cognito authorization code flow, AgentCore REST API invocation via Bearer token, `allowedClients` update for web client. **Tip:** Participants enjoy seeing the UI — this is a great energy boost after the security-heavy labs. Make sure the Cognito callback URL `http://localhost:8501/` is configured before participants try to log in. |
| 2:40–3:00 | 20 min | Lab 8: Policies | **Focus:** Cedar policy language, Policy Engine creation, `forbid`/`permit` statements, triple-underscore action naming (`ExecuteTrade___execute_trade`), ENFORCE mode, natural language policy generation. **Tip:** The "denied trade" demo is the most impactful moment in the workshop. Make sure everyone tries the large trade (5000 shares of MSFT) and sees the Gateway block it. |
| 3:00–3:15 | 15 min | Lab 9: VPC Integration | **Focus:** `networkMode: VPC`, `vpcConfig` in `agentcore.json`, retrieving pre-provisioned VPC resources from SSM, ENI provisioning. **Tip:** VPC deploy takes 3-5 minutes for ENI provisioning. Use this pause for discussion about FSI network isolation requirements. Rollback to PUBLIC mode if there are connectivity issues. |
| 3:15–3:30 | 15 min | Lab 10: Cost Optimization | **Focus:** `sessionConfig` (idleRuntimeSessionTimeout, maxLifetime), evaluation sampling rate tuning (100% → 20%), memory retention alignment with FSI compliance, CloudWatch cost dashboard. **Tip:** This lab can be shortened or made an optional stretch goal if the group is running behind. The key concepts (session lifecycle and sampling rate) can be covered in 5 minutes as a discussion even if participants don't run the commands. |
| 3:30–3:40 | 10 min | Wrap-up & Summary | Review key takeaways, discuss the path from prototype to production, share resources. Collect feedback via Workshop Studio survey. |

**Pacing tips:**
- Labs 3 and 8 consistently run the longest. Build in buffer around both.
- Labs 9 and 10 can be combined into a single 20-minute stretch or made optional if time is short. The core message (two config lines enable VPC isolation; session timeout and eval sampling tune cost) can be delivered as a demo.
- Every `agentcore deploy` takes 2-3 minutes. Use these pauses for Q&A on the concepts just covered rather than letting participants sit idle.
- With 20+ participants, pair faster participants with slower ones during hands-on sections. The agent code in `main.py` is intentionally similar across labs — copy-paste errors are a common source of delays.
- If a participant falls two or more labs behind, give them the final state of `main.py` and `agentcore.json` so they can catch up rather than stay stuck.

---

## Delivery Tips

### Setup & Environment

- Start provisioning Workshop Studio accounts at least 15 minutes before the session begins. The prerequisites CloudFormation stack takes 3-5 minutes to deploy.
- Region: **us-west-2 only.** Check that participants are in the correct region at the start — a wrong region is the single most common setup error and causes cascading failures across every lab.
- Cost per participant: approximately $2-5 USD for a full workshop run. Cleanup is automatic via `agentcore remove all` followed by CloudFormation stack deletion. Workshop Studio handles this automatically on event termination.
- Keep one fully-deployed environment around for live demos. If you've run the workshop yourself in advance, don't tear it down until after the event.
- Ensure Kiro is installed and available in the Workshop Studio environment. Labs reference Kiro's integrated terminal, AI chat panel, and split-terminal feature by name. Participants can use any code editor + terminal if Kiro is unavailable, but the step-by-step instructions will diverge slightly.

### FSI-Specific Facilitation Notes

**Compliance disclaimer:** Remind participants at the beginning of the workshop — and again before Lab 8 — that all financial data, compliance rules, and trade policies in this workshop are **simulated for educational purposes only**. The Cedar policies in Lab 8 illustrate how governance works; they do not constitute actual regulatory guidance. Real-world implementations require review by legal and compliance teams.

**Audience expectations:** FSI audiences typically arrive with strong opinions about security architecture. Lean into this — acknowledge the concerns and use Labs 5, 8, and 9 as direct responses:
- "You're worried about unauthorized API calls" → Lab 5 (JWT auth)
- "You need deterministic trade controls that can't be prompt-injected away" → Lab 8 (Cedar policies)
- "Your data cannot leave the private network" → Lab 9 (VPC isolation)

**Regulatory context:** When discussing VPC isolation (Lab 9) and policy governance (Lab 8), you can reference SEC Rule 17a-4, FINRA Rule 3110, SOX, and MiFID II as motivating frameworks. Be explicit that this workshop provides architectural patterns — it does not constitute compliance guidance and every firm's requirements differ.

**FSI architects and technical leads** will frequently ask about Guardrails integration. The answer is documented in the Additional Notes section of this guide: Guardrails cannot be attached to AgentCore Runtime or Gateway as infrastructure configuration. To apply Guardrails, use the `guardrailConfig` parameter in the Bedrock Converse API within the agent code itself.

### Common Facilitation Strategies

- **Show the final architecture at the start.** The `static/images/workshop-architecture.png` diagram shows the completed system. Participants retain more when they know where they're heading.
- **Explain "why" before "how."** Each lab opens with a business problem (e.g., "clients have to repeat their preferences every session"). Spend 30 seconds on the problem before walking through the solution.
- **Use the Cedar denial as a live demo.** In Lab 8, walk through the large trade denial (5000 shares of MSFT) in your own browser before participants try it. The visual of the agent explaining it cannot execute the trade — without any code change — is the workshop's single most effective demo moment.
- **Use the `agentcore deploy` pauses.** Each deploy takes 2-3 minutes. Rather than silence, use this time to ask participants what they'd connect to the Gateway next, or what Cedar policies would apply to their workload.
- **Point FSI skeptics to the "no code changes" message.** In Labs 8 and 9, emphasize that the agent code didn't change. Governance and network isolation were added entirely through configuration. This is meaningful for organizations that manage production code change processes carefully.

---

## Troubleshooting

### Top Issues

#### 1. "CDK Bootstrap Failed" on first `agentcore deploy`

:::alert{type="warning"}
This blocks Lab 1 deployment and affects every participant who hasn't bootstrapped CDK in the account/region.
:::

**Cause:** The AgentCore CLI uses AWS CDK internally. The first `agentcore deploy` in a given account and region requires CDK to be bootstrapped. Workshop Studio accounts typically have this pre-configured, but it can fail in some edge cases.

**Fix:**
1. Run `npx cdk bootstrap aws://ACCOUNT_ID/us-west-2` manually in the `PortfolioAdvisor/agentcore/cdk/` directory.
2. Once bootstrap completes (about 2 minutes), retry `agentcore deploy`.

#### 2. "Token expired" errors in Labs 6–10

**Cause:** Cognito access tokens expire after 60 minutes. Participants who spend more time on earlier labs — or who pause for breaks — hit this when they return to Labs 6+.

**Fix:** Re-run the token retrieval commands from Lab 5 Step 1 ("Authenticate as the user and obtain a token"). The token retrieval is a single `aws cognito-idp initiate-auth` command. Point participants to this command first whenever they see an authentication error after Lab 5.

**Prevention:** Remind participants at the break (between Labs 5 and 6) that tokens expire after 60 minutes. Encourage them to re-fetch the token if they pause.

#### 3. `agentcore` command not found

**Cause:** The AgentCore CLI is not installed or not on the `PATH`.

**Fix:**
- Install: `npm install -g @anthropic-ai/agentcore-cli` (or check the Workshop Studio environment's pre-installed CLI version)
- Verify: `agentcore --version`
- If Kiro's terminal doesn't pick up the PATH change, close and reopen the terminal.

#### 4. Gateway timeout after VPC deployment (Lab 9)

**Cause:** ENIs are still provisioning in the private subnets, or the security group is missing HTTPS outbound (port 443) egress rules.

**Fix:**
1. Wait 3-5 minutes after `agentcore deploy` completes. VPC ENI attachment takes longer than a standard deploy.
2. Run `agentcore status` to confirm the runtime reports `READY`.
3. If still failing after 5 minutes, verify the security group allows outbound HTTPS: `aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID`.
4. If VPC issues can't be resolved quickly, roll back to PUBLIC mode (Lab 9 Step 6) and continue — the conceptual point of Lab 9 can be made without the participant's agent remaining in VPC mode.

#### 5. "Model access denied" on first agent invocation

**Cause:** Claude Sonnet model access is not enabled in the Bedrock console for us-west-2.

**Fix:** In the Bedrock console → Model access → Enable Claude Sonnet. Takes approximately 1 minute. This should be pre-configured in Workshop Studio accounts.

#### 6. "VPC limit exceeded" (Lab 9)

**Cause:** The account has hit the VPC-per-region limit. This is unlikely in Workshop Studio accounts (which have raised limits) but can occur in self-paced scenarios.

**Fix:** Delete unused VPCs in us-west-2, or request a limit increase via Service Quotas. For large events, verify the account's VPC limit before provisioning participant accounts.

#### 7. "Attribute type null is not yet supported" during Gateway deploy

**Cause:** The tool schema JSON has a nested `"json"` wrapper inside `inputSchema`, or uses an unsupported type.

**Fix:** The `inputSchema` must have `"type": "object"` directly inside the `inputSchema` key, not wrapped in a `"json"` object. Check `portfolio_risk_schema.json` and `trade_schema.json` against the examples in Lab 3 and Lab 8 respectively.

### Module-Specific Issues

**Lab 1:**
- If `agentcore dev` shows "no tools found" or the agent doesn't call tools, check that `main.py` is saved and that the `@tool` decorator is present on both `get_stock_analysis` and `get_compliance_rules`.
- If the `agentcore create` command generates a project but doesn't open it in Kiro automatically, use **File → Open Folder** to navigate to the `PortfolioAdvisor/` directory.

**Lab 2:**
- If memory doesn't persist across sessions, confirm the agent was redeployed after adding memory (not just running locally). `agentcore dev` does not use AgentCore Memory.
- If the memory recall test returns "I don't know anything about you", the memory extraction job may not have finished. Wait 1-2 minutes and retry with a new session ID.
- If deployment fails with a header-related error, check that `requestHeaderAllowlist` was added to the runtime entry in `agentcore.json` (Lab 2 Step 3).

**Lab 3:**
- If the Lambda ARN retrieval fails, verify the prerequisites CloudFormation stack completed successfully: `aws ssm get-parameter --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn`.
- If the gateway target fails to add, confirm the Lambda ARN is valid and that the IAM role has permission to invoke it. The CDK-generated role should have this, but check if the Lambda was created in a different account.
- If the agent doesn't discover the Gateway tool, confirm `AGENTCORE_GATEWAY_MY_GATEWAY_URL` is in the agent's environment: this variable is only injected after deployment with `--runtimes PortfolioAdvisor` specified when creating the gateway.

**Lab 4:**
- If traces don't appear in CloudWatch, confirm the agent was deployed (not just running locally with `agentcore dev`). Observability is only active for cloud-deployed runtimes.
- If session continuity doesn't work (agent forgets context between messages in the same session), verify the `--session-id` flag is the same across invocations.

**Lab 5:**
- If JWT auth is configured but invocations are still accepted without a token, check that `agentcore deploy` ran after editing `agentcore.json`. The `authorizerType` field is only applied on deploy.
- If `agentcore validate` fails after adding `authorizerConfiguration`, check for JSON syntax errors — missing commas between the `requestHeaderAllowlist` array and the `authorizerType` field are common.
- When securing the Gateway in Step 2, the original `my-gateway` must be removed and redeployed before creating `my-gateway-secure`. If the remove fails, check that no deployment is in progress.
- The `mcp_client/client.py` environment variable must match the new gateway name exactly: `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL` (not `MY_GATEWAY_URL`).

**Lab 7:**
- If the login redirect loops back to the login page without signing in, confirm the web client ID was added to BOTH `allowedClients` arrays in `agentcore.json` — one in the runtime's `authorizerConfiguration`, and one in the gateway's `authorizerConfiguration`.
- If the Flask app starts but the Runtime ARN shows "NOT FOUND", the `deployed-state.json` file is either missing or doesn't contain the PortfolioAdvisor runtime entry. Run `agentcore status` to verify the runtime is deployed, then check `agentcore/.cli/deployed-state.json`.
- If the chat sends a message but gets a 401 response, the session-stored token has expired. Log out and log back in via the Cognito hosted UI.

**Lab 8:**
- Cedar policy action names use **triple underscores**: `ExecuteTrade___execute_trade` and `PortfolioRiskCheck___check_portfolio_risk`. A double-underscore or single-underscore will silently create a policy that never matches.
- After attaching the Policy Engine in ENFORCE mode, every tool behind the Gateway is subject to default-deny. If the portfolio risk check starts failing in Lab 8, it means `portfolio_risk_check_policy` was not created or not deployed.
- When creating the `restricted_ticker_policy` and `portfolio_risk_check_policy`, the `--validation-mode IGNORE_ALL_FINDINGS` flag is required because the Cedar validator doesn't know these principals exist at creation time.
- The natural language policy generation in Step 5 (bonus) requires `--gateway my-gateway-secure` so the CLI can resolve the gateway ARN and tool schema. Without it, the generated Cedar will have a placeholder ARN.

**Lab 9:**
- The `agentcore` CLI does not expose a `--network-mode` flag. The `networkMode` and `vpcConfig` fields must be edited directly in `agentcore.json`. This is explicitly documented in Lab 9 Step 2.
- If VPC deploy fails with "invalid subnet", verify the subnet IDs retrieved from SSM are for the private subnets (not public). Private subnets have no direct route to the Internet Gateway.

**Lab 10:**
- The `sessionConfig` block is also a direct `agentcore.json` edit — no CLI flag exists for session lifecycle parameters.
- When re-adding `QualityMonitor` with 20% sampling, the old configuration must be paused first (`agentcore pause online-eval QualityMonitor`). Adding a duplicate name may fail.

### Service Limits & Quotas During Delivery

:::expand{header="Service quota issues during delivery"}
- **AgentCore Runtime quota exceeded**: If participants hit runtime creation limits, check the current quota in the Bedrock console under Service Quotas. For large events, request increases at least one week in advance.
- **Slow deploys**: AgentCore deploy times can increase during peak hours. If deploys are taking more than 5 minutes consistently, use the time for discussion and flag it in post-event notes.
- **Cognito token endpoint throttled**: Unlikely, but possible if many participants are refreshing tokens simultaneously. If this happens, stagger the token refresh commands across the room.
:::

### When Nothing Works

If you hit something not listed here:
1. Check Workshop Studio event logs for detailed error messages.
2. Run `agentcore status` — it gives a clean summary of what's deployed and what's not.
3. Ask the Workshop Studio Atlas Agent from the UI.
4. Ask in #workshop-studio-interest on Slack.
5. **Add it to this guide after you fix it.** The next facilitator will appreciate it.

---

## Resources

### For Facilitators

- **Source code and workshop content:** This repository
- **Prerequisites CloudFormation template:** `static/prereqs.yaml` — review this before the event to understand what's pre-provisioned for participants
- **Support:** Workshop Studio Atlas Agent (from the Workshop Studio UI), or #workshop-studio-interest on Slack

### For Participants (share after the event)

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore CLI GitHub](https://github.com/aws/agentcore-cli)
- [AgentCore Samples (GitHub)](https://github.com/awslabs/agentcore-samples)
- [Cedar Policy Language](https://www.cedarpolicy.com/) — the open-source authorization language used in Lab 8
- [Strands Agents SDK](https://strandsagents.com/) — the Python agent framework used throughout the workshop
- [CloudWatch GenAI Observability for Bedrock AgentCore](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-GenAI-Observability-AgentCore.html)

---

## Post-Event Actions

- Terminate the event in Workshop Studio — cleanup is automatic.
- Remind participants who ran the workshop in their own AWS account to: run `agentcore remove all` from the `PortfolioAdvisor/` directory, then delete the prerequisites CloudFormation stack.
- Share the Resources links above with participants after the event.
- Collect feedback via the Workshop Studio survey.
- Update this guide if you found new issues or better approaches during delivery.

---

## Additional Notes

- **All financial data is simulated.** The stock prices, PE ratios, portfolio holdings, compliance rules, and trade limits in this workshop are fictional and exist solely to provide realistic-looking data for the portfolio advisor scenario. They do not reflect real market data.
- **All AgentCore features used are generally available in us-west-2** as of the workshop's publication date.
- **Framework-agnostic design, Python-specific code.** The workshop uses the Strands Agents SDK and Python 3.13 throughout. The AgentCore CLI supports other frameworks (LangChain, CrewAI, Google ADK, OpenAI Agents SDK), but all code samples are Python.
- **Guardrails and AgentCore infrastructure:** A common question from FSI participants is whether Bedrock Guardrails can be attached to AgentCore Runtime or Gateway at the infrastructure level (similar to how VPC endpoints are configured). The answer is **no** — Guardrails integration with AgentCore Runtime and Gateway is not available as an infrastructure attachment. To use Guardrails, configure the `guardrailConfig` parameter in the Bedrock Converse API calls within the agent code itself (in `model/load.py` or wherever the Bedrock client is configured).
- **Session ID minimum length:** AgentCore Runtime requires session IDs to be at least 33 characters. The workshop uses `uuid.uuid4()` (36 characters) throughout to satisfy this requirement. Shorter custom session IDs will be rejected with a validation error.
- **`agentcore.json` direct edits:** Three configuration areas require direct JSON file edits rather than CLI flags: `authorizerConfiguration` (Lab 5), `networkMode` and `vpcConfig` (Lab 9), and `sessionConfig` (Lab 10). All other configuration is managed through CLI commands. This is a known limitation of the CLI at the time of writing; point participants to the inline alert in each lab that flags these as exceptions.
