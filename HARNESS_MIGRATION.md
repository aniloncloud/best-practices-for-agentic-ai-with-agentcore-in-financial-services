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
- [ ] Gateway target → tool action names still resolve as `ExecuteTrade___execute_trade` /
      `PortfolioRiskCheck___check_portfolio_risk` when the gateway is attached to a harness.
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
