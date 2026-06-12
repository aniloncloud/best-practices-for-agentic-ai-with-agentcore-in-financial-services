# AgentCore Harness Migration — Status & Verification Tracker

**Branch:** `harness`
**Date:** 2026-06-11
**Authored against:** the AgentCore harness documentation (harness was preview at authoring time; expected GA for AWS NY Summit).

> **READ THIS FIRST.** This branch migrates the workshop from a hand-written
> Strands agent (`main.py` + MCP client) to the **AgentCore harness** (declarative,
> managed, Strands-powered). The content is complete and internally consistent, but
> the harness CLI/`harness.json` schema was authored from documentation, **not**
> validated against a live GA CLI. Nothing here is dry-run-tested. Treat every
> `agentcore` harness command and config block as **needs-verification** until the
> checklist below is green.

---

## What changed

### Agent bundle (`static/workspace-bundle/`)
- **Added** `app/PortfolioAdvisor/harness.json` — the declarative agent (model, system
  prompt, tools, execution limits). This is now the entire agent definition.
- **Removed** `app/PortfolioAdvisor/main.py`, `mcp_client/`, `model/`,
  `pyproject.toml`, `uv.lock` — orchestration code the managed harness replaces.
- **Kept** `app/PortfolioAdvisor/tool/*.json` — still used as Gateway target schemas.
- **Updated** `agentcore/agentcore.json` — `runtimes: []`, added a `harnesses` array.

### Local-tools decision (important)
The two in-process tools (`get_stock_analysis`, `get_compliance_rules`) had no clean
home in a declarative harness. Resolution: **their simulated reference data was baked
into the harness system prompt** — a documented best practice ("if a tool returns the
same static content every call, put it in the prompt"). This keeps Lab 1 standalone
with zero new infrastructure. The **dynamic** tools (risk, trade) remain Gateway
Lambda targets, exactly as before.

### Content pages
- **Lab 1** (`20-lab1-runtime`) — rewritten: deploy the harness, `harness.json` tour,
  BP5 system-prompt note, **new live model right-sizing beat (BP6)**, session isolation, trace.
- **Lab 2** (`30-lab2-gateway`) — rewritten: gateway by reference, harness inbound JWT
  as config, **the former code edit deleted** (Identity threads the caller's identity).
- **Lab 3** (`50-lab4-governance`) — Cedar unchanged; harness terminology, `--harness`
  on invokes, cost note added to the deploy-wait box.
- **Framing** — `index`, `10-intro`, `15-foundations`, `90-summary` updated (harness
  architecture, "zero code edits", services table).
- **Self-paced** — `11-at-aws` file list fixed; `40-lab3-security` identity note fixed;
  `80-optional-memory` carries a harness-adaptation banner (see TODO below).

### Blog threading (companion guide)
The "While this deploys" boxes and a few alerts now carry "Deep dive" pointers to the
AgentCore optimization best-practices companion guide
(`BLOG_AGENTCORE_OPTIMIZATION_BEST_PRACTICES.md`, lives outside this repo). BP coverage:
BP1 (observability) + BP5 (Gateway/policy/identity) + BP9 (security) shown live; **BP6
(model right-sizing) added live in Lab 1**; BP2/BP3 surfaced in deploy-wait reading.

---

## VERIFICATION CHECKLIST — must be green before delivery

### 1. Harness CLI & schema (GA reconciliation) — BLOCKING
- [ ] `agentcore add harness` / `agentcore deploy` for a harness project — confirm exact flags.
- [ ] `harness.json` schema: confirm the real field names for `model` (`bedrockModelConfig.modelId`,
      `apiFormat`), `systemPrompt`, `tools`, `allowedTools`, `executionLimits`. Our file is
      doc-derived and may not match the GA schema 1:1.
- [ ] `agentcore.json` harness representation (`harnesses` array shape) vs. the GA CLI output.
- [ ] `agentcore add tool --type agentcore_gateway --gateway my-gateway` attaches gateway tools.
- [ ] Harness inbound JWT: confirm whether it's `--authorizer-type` on `add/update harness`
      or a `harness.json` `inboundAuth` block (Step 5 uses a config patch — verify the field path).
- [ ] `agentcore invoke --harness <name> [--model-id ...] [--bearer-token ...]` flags & output.
- [ ] `agentcore logs --harness <name>` and `agentcore status` for harnesses.

### 2. Identity threading (the "no code edit" claim) — BLOCKING
- [ ] Confirm that with harness inbound OAuth configured, AgentCore Identity threads the
      end-user identity to Gateway tools **with no agent code**, and that this identity is
      what the Cedar policies in Lab 3 evaluate (principal `AgentCore::OAuthUser`, `sub` claim).
- [ ] If identity does NOT auto-thread, Lab 2 Step 6 and the whole "zero code edits" narrative
      must change — this is the migration's central claim.

### 3. Models — BLOCKING
- [ ] `global.anthropic.claude-sonnet-4-6` (harness default) access enabled in the account template.
- [ ] The Haiku model ID in Lab 1's right-sizing beat (`us.anthropic.claude-haiku-4-5-...`) is a
      **placeholder** — replace with a real, access-enabled us-west-2 model ID.
- [ ] Reconcile FACILITATOR_GUIDE / prereqs references to "Claude Sonnet 4.5" with the 4.6 default.

### 4. Cedar action names — verify
- [x] **VALIDATED via AgentCore MCP `get_gateway_guide`:** tool names exposed through MCP are
      `${target_name}___${tool_name}` (three underscores) — confirms `ExecuteTrade___execute_trade`
      and `PortfolioRiskCheck___check_portfolio_risk`.
- [ ] Confirm the same naming holds when the gateway is attached to a **harness** (vs. a runtime).
- [ ] The Lab 3 "policy engine not attached" troubleshooting expander still references
      runtime CloudFormation stack `AgentCore-PortfolioAdvisor-default` — confirm the harness
      backs the same stack/resource type (docs say harness shows as `::Runtime` in CloudTrail).

### 5. Provisioning — likely OK, confirm
- [ ] `static/devbox.yaml` installs the AgentCore CLI **with harness support**. The Python venv
      pip install of `strands-agents`/`bedrock-agentcore`/`mcp` is now unnecessary (harmless) —
      optional cleanup.
- [ ] `static/prereqs.yaml` unchanged and still correct: Cognito, the two Lambdas, VPC, and all
      SSM params are reused as-is (no new infra needed). ✅ expected.
- [ ] VPC note: in VPC mode the harness pulls its image from ECR Public (needs NAT egress).
      The prereqs NAT gateway covers this — confirm in the self-paced VPC lab.

### 6. Full dry-run — BLOCKING
- [ ] Run Labs 1–3 end-to-end in a test Workshop Studio event. Time each segment vs. run-of-show.
- [ ] Confirm the before/after 5,000-share trade: SUCCEEDS in Lab 2, DENIED in Lab 3.

---

## Open TODOs (non-blocking for the live path)
- [ ] **Memory self-paced lab** (`80-optional-memory`) still shows the code-based `main.py`
      pattern under a harness banner. Rewrite as harness-native memory config (a memory
      resource referenced by the harness).
- [ ] Other self-paced labs (`25`, `35`, `60`, `70`, `85`, `88`) — scan for any remaining
      `agentcore.json` runtime / `main.py` assumptions and align to harness terms.
- [ ] Consider declaring `allowedTools` to exclude built-in `shell`/`file_operations` in the
      FSI hardening narrative (mentioned in Lab 2 best-practices; not yet enforced in harness.json).
- [ ] Reconcile the companion blog (BP2 cold-start/artifact framing is custom-code-runtime
      specific and partly N/A under the managed harness).

---

## Validation against the AgentCore MCP server (2026-06-11)

Ran the installed `aws-agentcore` power's MCP server (`search_agentcore_docs`,
`get_gateway_guide`) to validate the migration. **Important finding:** the MCP's
curated documentation and control-plane tools are the **classic Runtime/Gateway/
Memory/Identity/Policy** surface — there is **no harness tool and no harness
documentation** in this MCP. Two separate harness searches returned only VPC,
import-agent, runtime, and CloudFormation docs. So the MCP can validate the
**primitives the harness sits on (Labs 2–3 mechanics), but not the harness layer itself.**

### VALIDATED (authoritative, via MCP)
- ✅ `agentcore add gateway --name <n> --authorizer-type CUSTOM_JWT --discovery-url <u>
  --allowed-clients <ids>` — exact match to Lab 2 Step 2. Optional flags confirmed:
  `--allowed-audience`, `--allowed-scopes`, `--policy-engine`, `--policy-engine-mode (LOG_ONLY|ENFORCE)`.
- ✅ `agentcore add gateway-target --type lambda-function-arn --lambda-arn <arn>
  --tool-schema-file <f> --gateway <n>` — exact match to Lab 2 Step 3.
- ✅ **Triple-underscore tool naming** `${target_name}___${tool_name}` — confirms the
  Lab 3 Cedar action names `ExecuteTrade___execute_trade` / `PortfolioRiskCheck___check_portfolio_risk`.
- ✅ Cedar policy engine attach modes `LOG_ONLY | ENFORCE` — confirms Lab 3.
- ✅ CLI install `npm install -g @aws/agentcore-cli` — confirms facilitator guide.
- ✅ Gateway CUSTOM_JWT config key is `customJWTAuthorizer` (uppercase JWT). **Fixed** the
  Lab 2 Step 5 harness inbound-auth heredoc to match this casing (was `customJwtAuthorizer`).

### NOT VALIDATABLE via this MCP (harness layer — still BLOCKING, need GA CLI/docs)
- ❌ `harness.json` schema (model/systemPrompt/tools/allowedTools/executionLimits field names).
- ❌ `agentcore add harness`, `agentcore add tool --type agentcore_gateway`, `--harness` flags.
- ❌ Harness inbound JWT config path AND whether `customJWTAuthorizer` is the right key there too.
- ❌ **Identity auto-threading** (the "zero code edit" claim). Notably, the MCP's Gateway guide
  describes the *classic* model where "you'll need to handle OAuth tokens properly" — i.e. manual
  forwarding. The harness improvement (auto-threading) is exactly what must be confirmed against
  the harness GA docs/CLI, because the whole Lab 2 narrative depends on it.
- ❌ Model right-sizing `--model-id` override and mid-session switch.

### Net
Labs 2–3's gateway/Cedar mechanics are now **validated at the API/CLI level** — those commands
are correct regardless of harness. The harness-specific layer (Lab 1 deploy, Lab 2 attach + auth,
the zero-code claim) remains authored-from-docs and unverified; the AgentCore MCP cannot close
that gap. A GA-CLI dry-run in a Workshop Studio event is still required (checklist items 1, 2, 3, 6).
