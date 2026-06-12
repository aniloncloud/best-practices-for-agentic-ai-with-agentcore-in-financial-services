# Facilitator Guide: Best Practices for Agentic AI with AgentCore in Financial Services (IND306)

---

## Workshop Overview

**Best Practices for Agentic AI with AgentCore in Financial Services** (IND306) teaches participants how to take a fully assembled AI agent and incrementally harden it for financial services production — adding tools, authentication, and governance across three live labs in a **60-minute builder session** at AWS NY Summit. The event account stays available for a limited time after the Summit so participants can continue with the self-paced labs at their own pace.

The workshop follows a single use case from start to finish: a **capital markets portfolio advisor agent** that handles stock analysis, compliance rule lookups, portfolio risk assessment, and trade execution. All financial data is simulated.

**Session format:** 8 minutes of facilitator talk (front-loaded: CISO five questions, target architecture, before/after Cedar arc, logistics), then 52 contiguous minutes of self-paced hands-on work. There is no facilitator speaking after labs begin — facilitators float for 1:1 help. The lab pages self-narrate. Each live lab contains exactly one `agentcore deploy` paired with an on-page "While this deploys" reading box.

**What Participants Will Learn:** Participants arrive to a pre-provisioned environment — the agent workspace, infrastructure, and credentials are all ready. There is no scaffolding phase. Participants deploy the agent in Lab 1 and spend the remaining time adding production-grade capabilities through configuration and agentcore CLI commands.

**Learning Objectives:**
- Deploy a pre-built AgentCore agent and verify it produces CloudWatch traces (`agentcore deploy`)
- Centralize tools by connecting Lambda functions through an authenticated AgentCore Gateway (JWT passthrough and IAM credential patterns)
- Secure the agent and gateway with JWT-based Cognito authentication; make the same large trade fail with a 401, then succeed with a valid token
- Govern agent actions with deterministic Cedar policies (trade quantity limits, restricted securities) — same 5,000-share trade denied without any code change
- (Self-paced) Monitor agent quality with AgentCore Evaluations and CloudWatch GenAI Observability
- (Self-paced) Deploy the agent in a VPC with private subnet isolation and VPC endpoints

**Target Audience:** Solutions Architects, Developers, and Technical Decision Makers in financial services. Participants should have basic AWS console navigation and Python experience. Familiarity with financial markets concepts is helpful but not required — all financial data is simulated.

---

## Prerequisites / Facilitator Preparation

### What Is Pre-Provisioned

The following resources are provisioned before participants arrive. Participants do not create any of these — they consume them through SSM Parameter Store references and the pre-built agent workspace.

| Resource | Details |
|----------|---------|
| VS Code Server | Browser-based IDE available immediately; no local install required |
| Agent workspace | `~/PortfolioAdvisor/` — declarative harness project (`harness.json` + tool schemas), CLI installed |
| Cognito User Pool | M2M client (client_credentials flow), web client (auth code flow), test user `workshopuser@example.com` / `WorkshopPass1!` |
| Lambda functions | `workshop-check-portfolio-risk`, `workshop-execute-trade` |
| AgentCore harness IAM | `workshop-harness-execution-role`, `workshop-gateway-service-role` (Lambda invoke + policy-engine attach perms) — ARNs in SSM under `/app/portfolioadvisor/agentcore/`. The OAuth2 M2M credential provider `my-gateway-m2m` is **not** pre-provisioned; participants create it in Lab 2 Step 4 with one `agentcore add credential` command (no native CloudFormation type exists for it). |
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

**Model access:** Bedrock model access for **Claude Sonnet 4.5** is pre-enabled in Workshop Studio accounts for **us-west-2**. No manual action is required. As a sanity check, verify in the Bedrock console (Model access) that Claude Sonnet 4.5 shows as "Access granted" before the session begins.

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

**The new model pre-provisions everything.** The agent workspace at `~/PortfolioAdvisor/` is fully populated when participants open their browser. Lab 1 is now a deploy-and-verify step, not a code-writing step.

**Pacing implications:**

- **Lab 1 is shorter by design.** Participants run `agentcore deploy` within the first few minutes. The "While this deploys" reading box covers the CISO questions and code tour.
- **There is no `agentcore create` or `agentcore dev` step in the core labs.** The agent already exists. Participants deploy it, then modify configuration (agentcore.json) and redeploy to add capabilities.
- **Labs focus on configuration, not construction.** Lab 2 (Gateway + JWT) and Lab 3 (Cedar governance) involve agentcore.json edits plus CLI commands. Emphasize that in production, governance is an infrastructure concern, not an application code concern.
- **The "no code changes" message lands harder.** The agent is a declarative harness — there is no orchestration code at all. Demonstrating in Lab 3 that only configuration changed across the entire session is the whole point.

### 2026-06-11: 60-Minute Builder Session Restructure (AWS NY Summit)

The workshop was restructured from a ~3-hour format to a **60-minute builder session** for AWS NY Summit (IND306). Key changes:

- **Three live deploys, not six.** The session contains exactly three `agentcore deploy` calls (Lab 1, Lab 2, Lab 3). Each is paired with a "While this deploys" on-page reading box.
- **Gateway born with JWT.** `my-gateway` is now created with `--authorizer-type CUSTOM_JWT` on first creation and never recreated. Previously the gateway was created without auth and then replaced with `my-gateway-secure`.
- **Env-file replaces SSM copy-paste.** Lab 2 opens with `source ~/portfolio-env.sh`, a single command that loads all SSM parameter values into shell variables. Previously, participants ran multiple `aws ssm get-parameter` commands and manually copied ARNs.
- **Zero code edits.** The agent is a declarative harness (`harness.json`). Lab 2 attaches the Gateway by reference and configures inbound JWT; AgentCore Identity threads the caller's identity to tools, so no auth-forwarding code is written. No Python edits occur anywhere in the session.
- **Before/after trade demo.** Lab 2 ends with a 5,000-share MSFT trade succeeding (Gateway has no policy). Live Lab 3 ends with the identical trade denied by Cedar policy — without any code change. This is the session's narrative arc.
- **Old Lab 3 (Security) became self-paced OAuth deep-dive.** The Cognito auth-code flow, M2M client_credentials flow, and token lifecycle content that was the former Lab 3 is now the self-paced "OAuth Token Flows" page (`40-lab3-security`). The live JWT wiring happens in Lab 2.
- **Old Lab 4 (Governance) is now live Lab 3.** Cedar policies moved from the third hour into the live session. The content directory is still named `50-lab4-governance/` to preserve build history.
- **Evaluations and VPC Networking are self-paced.** Former Labs 5 and 6 are now self-paced labs participants continue after the 60-minute session.
- **All Windows/PowerShell tabs removed.** Browser VS Code on Amazon Linux is the only supported environment. The workspace-bundle in `static/workspace-bundle/` delivers the pre-built project to instances.

### 2026-06-11 (later): AgentCore Harness Migration

The workshop was migrated from a hand-written Strands agent (`main.py` + MCP client) to the **AgentCore harness** — a declarative, managed agent runtime (powered by Strands). Impact:

- **The agent is now `app/PortfolioAdvisor/harness.json`** — model, system prompt, tools, and execution limits as config. `main.py`, `mcp_client/`, `model/`, `pyproject.toml`, and `uv.lock` were removed.
- **Local tools became system-prompt reference data.** The simulated stock and compliance data now lives in the harness system prompt (a documented best practice: bake static content into the prompt instead of a per-call tool round trip). The risk and trade tools remain Gateway Lambda targets.
- **Lab 1 adds a live model right-sizing beat** (`--model-id` override; Haiku vs Sonnet) — a one-line demo enabled by the harness.
- **Lab 2 has no code edit.** The Gateway attaches to the harness by reference, and AgentCore Identity threads the caller's identity to tools — replacing the former `extract_user_id()` / auth-forwarding edit.
- **Model:** the harness defaults to `global.anthropic.claude-sonnet-4-6`. Verify model access for Sonnet 4.6 **and** the Haiku model used in Lab 1's right-sizing beat is enabled in the account template (previously only Sonnet 4.5 was noted — update `prereqs.yaml`/account template accordingly).

> **PREVIEW/GA WARNING:** This migration was authored against the AgentCore harness documentation. Before delivery, every `agentcore` harness command, the `harness.json` schema, and the inbound-auth config block MUST be verified against the GA CLI in a Workshop Studio dry-run. See `HARNESS_MIGRATION.md` at the repo root for the full verification checklist.

---

## Recommended Agenda

### 60-Minute Run-of-Show (AWS NY Summit)

| Clock | Duration | Activity | Key Focus and Tips |
|-------|----------|----------|--------------------|
| 0:00–0:08 | 8 min | **Facilitator talk** | Front-load: CISO five questions, target architecture diagram, the before/after Cedar arc (5,000-share trade succeeds in Lab 2, denied in Lab 3 without a code change), logistics ("your first command starts a deploy — the page tells you what to read while it runs"). No speaking after this point — facilitators float. |
| 0:08–0:21 | 13 min | **Lab 1: Deploy to the AgentCore Harness** | Participants run `agentcore deploy` immediately. "While this deploys" box: CISO five questions + harness.json tour. Then: invoke the agent, right-size the model live (Haiku vs Sonnet), session-isolation A/B test, one CloudWatch trace. **Tip:** The harness image pull on first deploy adds ~2 min to Lab 1's wait — this is absorbed by the reading box. Point participants to the reading box the moment they start the deploy. |
| 0:21–0:39 | 18 min | **Lab 2: Connect Tools with Gateway + JWT Auth** | `source ~/portfolio-env.sh` (one paste loads all SSM values), create `my-gateway` with `--authorizer-type CUSTOM_JWT` (never recreated), both Lambda targets, attach the gateway to the harness by reference, configure harness inbound JWT (no code edit — Identity threads identity), deploy #2. "While this deploys" box: credential patterns + tool schemas. Then: obtain token, bearer invoke, 401 proof, 5,000-share MSFT trade SUCCEEDS (no policy yet). **Tip:** The 401 proof and the succeeding large trade together set up Lab 3's payoff — make sure participants get there. |
| 0:39–0:55 | 16 min | **Lab 3 (live): Govern Agent Actions with Cedar Policies** | Policy engine attached to `my-gateway` in ENFORCE mode, 2 Cedar policies (trade_quantity_limit < 1000, portfolio_risk_check permit), deploy #3. "While this deploys" box: Cedar-vs-prompt-rules + policy walkthrough. Then: ✅ 500-share trade passes, ❌ the SAME 5,000-share trade DENIED, ✅ risk check passes, audit record. **Tip:** The denied trade is the workshop's single most impactful moment. Circulate during Lab 3 to make sure participants reach the denial test before time is up. |
| 0:55–1:00 | 5 min | **Buffer / fast-finisher ladder** | Fast-finisher ladder on the Lab 3 page: (1) add a restricted-ticker Cedar policy → (2) Observability Deep Dive → (3) OAuth Token Flows. Facilitators prompt fast finishers to the ladder rather than letting them sit idle. |

**Talk-track guidance:** The 8-minute talk should answer the CISO's five questions before participants touch a keyboard. End with the before/after arc: "In Lab 2 you will make a 5,000-share trade succeed. In Lab 3 you will make the exact same trade fail — without touching the agent code." That one sentence motivates the entire session.

### Self-Paced Labs (continue after the session)

Participants continue these at their own pace after the 60-minute session ends. The event account remains accessible for a limited time after the Summit.

| Lab | Duration | Topic |
|-----|----------|-------|
| **Observability Deep Dive** (`25-lab1b-observability`) | ~15 min | CloudWatch GenAI traces, session isolation deep dive, token metrics, multi-tool trace inspection |
| **Enterprise Tool Registry** (`35-lab2b-tool-registry`) | ~20 min | Enterprise tool approval workflow: review security posture of a Market Data MCP server, add to Gateway |
| **OAuth Token Flows: M2M & Token Lifecycle** (`40-lab3-security`) | ~20 min | Cognito M2M client_credentials flow, token lifecycle, auth code flow, web client setup |
| **Evaluations** (`60-lab5-evaluations`) | ~20 min | Online eval with GoalSuccessRate, Correctness, ToolSelectionAccuracy; CloudWatch GenAI Observability dashboard |
| **VPC Networking** (`70-lab6-vpc`) | ~20 min | Private subnets, VPC endpoints for AgentCore/Bedrock/SSM, network isolation patterns |
| **Memory** (`80-optional-memory`) | ~20 min | Persistent client memory with SEMANTIC and SUMMARIZATION strategies |
| **Frontend** (`85-optional-frontend`) | ~20 min | Flask chat portal with Cognito login and AgentCore REST invocation |
| **Cost Optimization** (`88-optional-cost`) | ~15 min | Session lifecycle (`sessionConfig`), eval sampling rate tuning (100% → 20%) |

---

## Pacing Tips

- **No facilitator speaking after the 8-minute mark.** The lab pages self-narrate. Facilitators circulate for 1:1 help only. Resist the urge to address the room — it breaks participants' reading flow.
- **Lab 2 is the longest live lab (18 min).** It has the most steps: env block, gateway creation, two targets, runtime authorizer patch, one code edit, deploy, token, three invocation tests. If a participant is stuck at the env block or gateway creation, help immediately — falling behind here means missing the Cedar denial payoff in Lab 3.
- **Lab 3's denied trade is the payoff — protect it.** At the ~0:48 mark, check that participants are at or past the deploy step in Lab 3. Anyone still in Lab 2 should skip to the core steps (the 5,000-share trade test can be done quickly from the reference commands).
- **Every `agentcore deploy` takes 2–3 minutes.** Each deploy has a "While this deploys" reading box on the page. Point participants to it the moment they start the deploy. This is designed — the reading is load-bearing context for the next steps, not filler.
- **CDK bootstrap on Lab 1's first deploy adds ~2 min.** The Lab 1 page accounts for this in its reading box. Do not intervene unless the deploy fails outright (see Troubleshooting).
- **Token expiration: 60 minutes.** In the 60-minute session format there is no break, so token expiration is less likely during the live labs. However, participants continuing into self-paced labs after the session may hit it. The fix is `source ~/portfolio-env.sh` followed by the one-liner re-auth command shown on the Lab 2 and Lab 3 pages. Point participants there first when they see authentication errors.
- **Fast-finisher ladder.** The Lab 3 page ends with a fast-finisher ladder: (1) restricted-ticker Cedar policy, (2) Observability Deep Dive, (3) OAuth Token Flows. Direct fast finishers there rather than letting them sit idle or distract neighbors.
- **With 20+ participants:** prioritize 1:1 help for participants stuck on the env block (Lab 2 step 1) or the Cedar policy creation (Lab 3). If a participant falls more than one full lab behind, provide the reference `agentcore.json` for the completed lab so they can catch up.

---

## Delivery Tips

### Setup

- Start provisioning Workshop Studio accounts at least 15 minutes before the session begins. The pre-provisioning stack takes 3–5 minutes to deploy.
- Verify VS Code Server is reachable and the `~/PortfolioAdvisor/` directory is populated before participants start.
- Keep one fully-deployed environment for live demos. If you ran the workshop yourself in advance, do not tear it down until after the event.
- Verify Claude Sonnet 4.5 model access shows as "Access granted" in Bedrock for us-west-2 (pre-enabled by the account template).

### FSI-Specific Facilitation Notes

**Compliance disclaimer:** Remind participants during the 8-minute talk — and note it again on the Lab 3 (live) page — that all financial data, compliance rules, and trade policies in this workshop are **simulated for educational purposes only.** The Cedar policies in Lab 3 illustrate how governance works; they do not constitute actual regulatory guidance. Real-world implementations require review by legal and compliance teams.

**Audience expectations:** FSI audiences typically arrive with strong opinions about security architecture. Lean into this — acknowledge the concerns and use the live labs as direct answers:
- "You're worried about unauthorized API calls" → **Lab 2** (JWT authentication on Runtime and Gateway)
- "You need deterministic trade controls that can't be prompt-injected away" → **Lab 3 (live)** (Cedar policies in ENFORCE mode)
- "Your data cannot leave the private network" → **VPC Networking** (self-paced; private subnets and VPC endpoints)

**Regulatory context:** When discussing VPC isolation (self-paced VPC lab) and policy governance (live Lab 3), you can reference SEC Rule 17a-4, FINRA Rule 3110, SOX, and MiFID II as motivating frameworks. Be explicit that this workshop provides architectural patterns — it does not constitute compliance guidance and every firm's requirements differ.

**FSI architects and technical leads** will frequently ask about Guardrails integration. The answer: Guardrails cannot be attached to AgentCore Runtime or Gateway as infrastructure configuration. To apply Guardrails, use the `guardrailConfig` parameter in the Bedrock Converse API within the agent code itself. See Additional Notes for detail.

### Common Facilitation Strategies

- **Show the final architecture at the start.** The `static/images/workshop-architecture.png` diagram shows the completed system. Participants retain more when they know where they're heading.
- **Explain "why" before "how."** Each lab opens with a business problem (e.g., "any caller can invoke the agent without authentication"). Spend 30 seconds on the problem before walking through the solution.
- **Use the Cedar denial as the session's payoff.** In live Lab 3, the large trade denial (5,000 shares of MSFT) is the moment the entire session builds toward. Ensure your own test environment has reached this point before the session. The visual of the agent explaining it cannot execute the trade — without any code change — is the workshop's single most effective demo moment.
- **Let the "While this deploys" boxes do the narrating.** Each of the three deploys has a reading box on the page. Do not lecture over it — participants are reading. Use the deploy time to circulate and check progress.
- **Reinforce the "no code changes" message.** In live Lab 3, emphasize that the agent code didn't change between Lab 2 and Lab 3 — Cedar governance was added entirely through configuration. This resonates strongly with organizations that manage production code change processes carefully.
- **Reference the pre-provisioned infrastructure as a model.** When participants ask how they would do this in their own environment, the pre-provisioning stack (`static/prereqs.yaml`) is a concrete starting point they can adapt.

---

## Troubleshooting

### Top Issues

#### 1. CDK Bootstrap Failed on First `agentcore deploy`

**Cause:** The AgentCore CLI uses AWS CDK internally. The first `agentcore deploy` in a given account and region requires CDK to be bootstrapped. Workshop Studio accounts typically have this pre-configured, but it can fail in edge cases.

**Note for Lab 1:** Lab 1 has participants start the deploy immediately and read the "While this deploys" box during the wait. CDK bootstrap adds ~2 minutes to the first deploy and is absorbed by the reading box. No action needed unless the deploy fails outright.

**Fix:**
1. Run `npx cdk bootstrap aws://ACCOUNT_ID/us-west-2` manually in the `~/PortfolioAdvisor/agentcore/cdk/` directory.
2. Once bootstrap completes (about 2 minutes), retry `agentcore deploy`.

#### 2. Token Expired in Lab 3 (live) or Self-Paced Labs

**Cause:** Cognito access tokens expire after 60 minutes. In the 60-minute session, this is unlikely to affect the live labs — tokens obtained in Lab 2 should last through Lab 3. Participants continuing into self-paced labs after the session ends are more likely to hit this.

**Fix:** Run `source ~/portfolio-env.sh` to reload env vars, then re-run the one-liner re-auth command shown on the Lab 2 and Lab 3 pages (the `aws cognito-idp initiate-auth` command). Point participants there first whenever they see an authentication error.

**Prevention:** The Lab 2 and Lab 3 pages include a note about token lifetime and the re-auth command. For self-paced participants, remind them to re-auth if they take a break between labs.

#### 3. `agentcore` Command Not Found

**Cause:** The AgentCore CLI is not installed or not on the PATH.

**Fix:**
- Verify: `agentcore --version`
- Install if missing: `npm i -g @aws/agentcore@preview` (the harness requires the preview AgentCore CLI; check the Workshop Studio environment's pre-installed version)
- If the VS Code Server terminal does not pick up the PATH change, close and reopen the terminal tab.

#### 4. Gateway Timeout After VPC Deployment (Lab 6)

**Cause:** ENIs are still provisioning in the private subnets, or the security group is missing HTTPS outbound (port 443) egress rules.

**Fix:**
1. Wait 3–5 minutes after `agentcore deploy` completes. VPC ENI attachment takes longer than a standard deploy.
2. Run `agentcore status` to confirm the runtime reports READY.
3. If still failing after 5 minutes, verify the security group allows outbound HTTPS: `aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID`.
4. If VPC issues cannot be resolved quickly, roll back to PUBLIC mode (remove `networkMode` and `vpcConfig` from agentcore.json and redeploy — the rollback step is documented in the self-paced VPC Networking lab). The conceptual point of the VPC lab can be made without the participant's agent remaining in VPC mode.

#### 5. Model Access Denied on First Agent Invocation

**Cause:** Claude Sonnet 4.5 model access is not active in us-west-2. This is pre-enabled by the Workshop Studio account template and should not occur under normal circumstances.

**Fix:** In the Bedrock console → Model access → verify Claude Sonnet 4.5 shows "Access granted." If not, request access — activation takes approximately 1 minute.

#### 6. VPC Limit Exceeded (Lab 6)

**Cause:** The account has hit the VPC-per-region limit. The VPC is pre-provisioned, so this should not occur unless the account already has several VPCs.

**Fix:** Delete unused VPCs in us-west-2, or request a limit increase via Service Quotas. Verify the account's VPC limit before large events.

### Module-Specific Issues

**Lab 1 — Deploy to AgentCore Runtime (live):**
- If `agentcore deploy` completes but `agentcore status` shows FAILED, check CloudWatch Logs for the Lambda deployment function for CDK errors. CDK bootstrap (issue 1 above) is the most common cause.
- If traces don't appear in CloudWatch after invocation, wait 1–2 minutes — CloudWatch GenAI Observability can have a short ingestion delay. Confirm the agent was invoked successfully (the CLI should print the agent response) before investigating traces.
- If the VS Code Server terminal opens to a different directory, navigate to `~/PortfolioAdvisor/` before running agentcore commands.

**Lab 2 — Connect Tools with Gateway + JWT Auth (live):**
- If `source ~/portfolio-env.sh` fails or env vars are empty, verify the pre-provisioning CloudFormation stack completed successfully: `aws ssm get-parameter --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn`.
- The gateway `my-gateway` is created once with `--authorizer-type CUSTOM_JWT`. It is never removed and recreated during the session. If a participant accidentally removed it, recreate it with the same flags.
- If the gateway target fails to add, confirm the Lambda ARN is valid and the IAM role has permission to invoke it. The CDK-generated role should have this automatically.
- If the agent doesn't discover the Gateway tool after redeployment, confirm `AGENTCORE_GATEWAY_MY_GATEWAY_URL` is in the agent's environment (injected automatically when the gateway is linked to the runtime).
- If the tool schema JSON fails with "Attribute type null is not yet supported", the `inputSchema` has a nested `"json"` wrapper. The `inputSchema` must have `"type": "object"` directly inside it, not wrapped in a `"json"` object.
- If JWT auth is configured but invocations are still accepted without a token, check that `agentcore deploy` ran after the agentcore.json patch. The `authorizerType` field is only applied on deploy.

**Lab 3 (live) — Govern Agent Actions with Cedar Policies:**
- Cedar policy action names use **triple underscores**: `ExecuteTrade___execute_trade` and `PortfolioRiskCheck___check_portfolio_risk`. A double-underscore or single-underscore will silently create a policy that never matches.
- After attaching the Policy Engine in ENFORCE mode, all tools behind the Gateway are subject to default-deny. If the portfolio risk check starts failing, it means `portfolio_risk_check_policy` was not created or not attached.
- When creating Cedar policies, the `--validation-mode IGNORE_ALL_FINDINGS` flag is required because the Cedar validator doesn't know the principals exist at creation time.
- **Policy engine attachment issue (if Test 2 is not denied):** A troubleshooting expander at the bottom of the Lab 3 page contains the manual attachment workaround: `put-role-policy` + `update-gateway` commands. Facilitators should pre-verify this flow in a test event before delivery — if the standard `agentcore` attach command doesn't wire the engine to the gateway, the manual commands are the fix.
- Agentic Explainability reasoning traces appear in CloudWatch under the same trace as the invocation. If they don't appear, verify the explainability configuration block was added to agentcore.json and the runtime was redeployed.

**Self-Paced: Observability Deep Dive (`25-lab1b-observability`):**
- This lab is fully self-paced. Participants who finish the live labs early are directed here via the fast-finisher ladder on Lab 3.
- If traces don't appear, see Lab 1 notes above (ingestion delay).

**Self-Paced: OAuth Token Flows — M2M & Token Lifecycle (`40-lab3-security`):**
- This is the former Lab 3 (Security) page, restructured as a self-paced deep dive. The live JWT wiring now happens in Lab 2. This page covers the M2M client_credentials flow, token lifecycle, and auth code flow in depth.
- If JWT auth is configured but invocations are accepted without a token, check that `agentcore deploy` ran after editing agentcore.json.
- If `agentcore validate` fails after adding `authorizerConfiguration`, check for JSON syntax errors — missing commas between fields are common.

**Self-Paced: Evaluations (`60-lab5-evaluations`):**
- If traces don't appear in CloudWatch, confirm the agent was deployed (not just running locally). Evaluations are only active for cloud-deployed runtimes.
- Evaluation results take a few minutes to appear after traffic is generated. Generate test traffic at the start of the lab and check the dashboard toward the end.
- If adding a second `QualityMonitor` fails with a duplicate name error, the previous configuration must be paused first: `agentcore pause online-eval QualityMonitor`.

**Self-Paced: VPC Networking (`70-lab6-vpc`):**
- The `networkMode` and `vpcConfig` fields must be edited directly in agentcore.json. There is no `--network-mode` CLI flag. This is explicitly documented in the lab.
- If VPC deploy fails with "invalid subnet", verify the subnet IDs retrieved from SSM are for the **private** subnets (not public). Private subnets have no direct route to the Internet Gateway.
- If the agent responds after VPC deployment but latency increased noticeably, this is expected — traffic now routes through VPC endpoints. It is not a failure.
- Gateway timeout after VPC deployment: ENIs may still be provisioning. Wait 3–5 minutes after `agentcore deploy` completes, run `agentcore status` to confirm READY. If still failing, verify the security group allows outbound HTTPS (port 443). Rollback: remove `networkMode` and `vpcConfig` from agentcore.json and redeploy.

**Self-Paced: Memory (`80-optional-memory`):**
- Memory requires cloud deployment — `agentcore dev` does not use AgentCore Memory.
- If the memory recall test returns "I don't know anything about you", the memory extraction job may not have finished. Wait 1–2 minutes and retry with a new session ID.
- If deployment fails with a header-related error, check that `requestHeaderAllowlist` was added to the runtime entry in agentcore.json.

**Self-Paced: Frontend (`85-optional-frontend`):**
- If the login redirect loops back to the login page without signing in, confirm the web client ID was added to BOTH `allowedClients` arrays in agentcore.json — one in the runtime's `authorizerConfiguration` and one in the gateway's `authorizerConfiguration`.
- If the Flask app starts but the Runtime ARN shows NOT FOUND, the `deployed-state.json` file is either missing or doesn't contain the PortfolioAdvisor runtime entry. Run `agentcore status` to verify the runtime is deployed.
- If the chat sends a message but gets a 401 response, the session-stored token has expired. Log out and log back in via the Cognito hosted UI.

**Self-Paced: Cost Optimization (`88-optional-cost`):**
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
- [Cedar Policy Language](https://www.cedarpolicy.com/) — the open-source authorization language used in Lab 3 (live governance lab)
- [Strands Agents SDK](https://strandsagents.com/) — the Python agent framework used throughout the workshop
- [CloudWatch GenAI Observability for Bedrock AgentCore](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-GenAI-Observability-AgentCore.html)

---

## Post-Event Actions

- Terminate the event in Workshop Studio — cleanup is automatic. The event staying live for self-paced work is intentional; terminate only when self-paced time has ended.
- Remind participants who ran the workshop in their own AWS account to: run `agentcore remove all` from the `~/PortfolioAdvisor/` directory, then delete the pre-provisioning CloudFormation stack.
- Share the Resources links above with participants after the event.
- Collect feedback via the Workshop Studio survey.
- Update this guide if you found new issues or better approaches during delivery.
- Note any participants who hit the policy-engine attachment issue (Lab 3 troubleshooting expander) — if it occurs consistently, escalate to the workshop team to investigate the standard attach command.

---

## Additional Notes

- **All financial data is simulated.** The stock prices, PE ratios, portfolio holdings, compliance rules, and trade limits in this workshop are fictional and exist solely to provide realistic-looking data for the portfolio advisor scenario. They do not reflect real market data.
- **All AgentCore features used are generally available in us-west-2** as of the workshop's publication date.
- **Framework-agnostic design, Python-specific code.** The workshop uses the Strands Agents SDK and Python 3.13 throughout. The AgentCore CLI supports other frameworks (LangChain, CrewAI, Google ADK, OpenAI Agents SDK), but all code samples are Python.
- **Guardrails and AgentCore infrastructure:** A common question from FSI participants is whether Bedrock Guardrails can be attached to AgentCore Runtime or Gateway at the infrastructure level (similar to how VPC endpoints are configured). The answer is **no** — Guardrails are not attachable to AgentCore Runtime or Gateway as infrastructure. To use Guardrails, configure the `guardrailConfig` parameter in the Bedrock Converse API calls within the agent code itself (in `model/load.py` or wherever the Bedrock client is configured).
- **Session ID minimum length:** AgentCore Runtime requires session IDs to be at least 33 characters. The workshop uses `uuid.uuid4()` (36 characters) throughout to satisfy this requirement. Shorter custom session IDs will be rejected with a validation error.
- **`agentcore.json` direct edits:** Three configuration areas require direct JSON file edits rather than CLI flags: `authorizerConfiguration` (Lab 2, applied via python3 heredoc patch), `networkMode` and `vpcConfig` (self-paced VPC Networking lab), and `sessionConfig` (self-paced Cost Optimization lab). All other configuration is managed through CLI commands. Each lab that requires a direct edit includes an inline alert flagging this as an exception to the normal CLI workflow.
- **Cedar triple-underscore naming:** Cedar policy action names use three underscores as a separator between the Gateway target name and the tool function name. For example: `ExecuteTrade___execute_trade` and `PortfolioRiskCheck___check_portfolio_risk`. Using two underscores or one underscore will silently create a policy that never matches any action.
