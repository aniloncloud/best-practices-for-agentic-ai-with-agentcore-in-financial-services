# AgentCore Harness — Command Verification Sheet

**Purpose:** A single, runnable source of truth for every `agentcore` / harness command the
workshop relies on. We verify each command **against the live CLI + a real deploy** here
*before* porting it into the lab content. Nothing gets written into a lab until its row is ✅.

**Workflow:** run a command → record actual output/behavior → set status → only then update the lab.

---

## Status legend

| Mark | Meaning |
|------|---------|
| ⬜ | Not yet run |
| 🟡 | Run, but needs follow-up / partial / version-dependent |
| ✅ | Verified against live CLI/AWS — safe to use in labs |
| ❌ | Verified WRONG — do not use; see correction note |

---

## Environment under test (record what we actually ran on)

**CANONICAL CLI = `@aws/agentcore@preview`.** The workshop devbox provisions with
`npm install -g @aws/agentcore@preview` (confirmed in `static/devbox.yaml` line ~1500),
which today resolves to **`1.0.0-preview.13`** (npm dist-tags: `preview: 1.0.0-preview.13`,
`latest: 0.19.0`). All command verification MUST be done on the **preview** build — the
stable line (`0.13.x`/`0.19.0`) does **not** expose the harness workflow and is irrelevant
to the workshop.

| Item | Workshop devbox | My local box | Notes |
|------|------|------|-------|
| agentcore CLI | `@aws/agentcore@preview` → `1.0.0-preview.13` | was `0.13.1` (stable) → installing preview to match | Validate on preview only. |
| node | 22 (nvm default) | `v22.22.0` | CLI.md requires Node 20.x+ ✅ |
| AWS account | participant account (Workshop Studio) | `839898192353` (IAM user `agentcore`, dev/sandbox) | Re-verify timings in a real WS event. |
| Region | us-west-2 (workshop target) | `us-east-1` | Both are harness preview regions (us-west-2, us-east-1, ap-southeast-2, eu-central-1). |

> ⚠️ **Earlier note retracted:** the "missing `--harness` / `add harness`" finding was made
> against the **stable `0.13.1`** CLI — the wrong build. The harness surface lives in the
> **preview** CLI the devbox installs. Re-checking all harness flags against `1.0.0-preview.13`.
> Still to settle: canonical create path on preview — `agentcore create --name ... --model-provider bedrock`
> (CLI.md) vs `agentcore add harness ...` (devguide). Make every lab consistent with whichever the preview CLI uses.

---

## 🔴 CRITICAL FINDING — the `harness.json` "shape trap" (BLOCKING, verified preview.13)

Validated by **generating a real `harness.json` with the preview CLI** (`agentcore create --no-agent`
→ `agentcore add harness ...`) and by reading the CLI's own zod schema
(`dist/schema/schemas/primitives/harness.js` → `HarnessSpecSchema`).

**The CLI-consumed `harness.json` is FLAT and uses different field shapes than the boto3 API.**
The workshop bundle's `harness.json` is in the **API/SDK** shape — which the CLI will **reject**
(`model` is required at top level; `agentcore validate`/`deploy` would fail).

| Aspect | ❌ Workshop bundle (current) | ✅ Preview CLI `harness.json` (correct) | boto3 `invoke_harness`/`create_harness` (different layer) |
|---|---|---|---|
| envelope | `{"type":"harness","name":...,"config":{...}}` | **flat** (no `type`/`config` wrapper) | n/a (API params) |
| model | `{"bedrockModelConfig":{"modelId":...}}` | `{"provider":"bedrock","modelId":...}` | `{"bedrockModelConfig":{"modelId":...}}` |
| systemPrompt | `[{"text":"..."}]` (array) | `"..."` (**plain string**) | `[{"text":"..."}]` (array) |
| inbound auth key | `customJWTAuthorizer` (migration's fix) | `authorizerConfiguration.customJwtAuthorizer` (**camelCase**) | `customJWTAuthorizer` (uppercase) |
| exec limits | removed (claimed invoke-only) | `maxIterations`/`maxTokens`/`timeoutSeconds` **are valid top-level defaults** (also invoke-overridable) | same names |

**Canonical `harness.json` the CLI actually generates (ground truth):**
```json
{
  "name": "PortfolioAdvisor",
  "model": { "provider": "bedrock", "modelId": "global.anthropic.claude-sonnet-4-6" },
  "systemPrompt": "You are a portfolio advisor.",
  "tools": [],
  "skills": [],
  "memory": { "name": "PortfolioAdvisorMemory" }
}
```
- `agentcore.json` references it as `"harnesses": [ { "name": "PortfolioAdvisor", "path": "app/PortfolioAdvisor" } ]`.
- `add harness` adds a default memory ref + a memory in `agentcore.json`. Use **`--no-harness-memory`** to suppress (workshop wants Lab 1 standalone).
- Tool shape when populated (verified in schema): `{ "type": "agentcore_gateway", "name": "...", "config": { "agentCoreGateway": { "gatewayArn": "...", "outboundAuth": { "oauth": { "providerArn": "...", "scopes": [...], "grantType": "CLIENT_CREDENTIALS" } } } } }`. NOTE: `credentialProviderName` is **no longer supported** — use `outboundAuth`.

> **Action (BLOCKING):** ✅ **FIXED 2026-06-13.** `static/workspace-bundle/app/PortfolioAdvisor/harness.json`
> rewritten to the flat CLI shape (`name` / `model:{provider,modelId}` / `systemPrompt:"string"` / `tools` / `skills`).
> `agentcore validate` now returns `Valid` on the bundle file (verified). The migration tracker's
> `systemPrompt`-as-array and `bedrockModelConfig` "corrections" were boto3-API-shaped — superseded by this fix.

---

## Sources of truth

- Official devguide: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html
  - Config & models: `.../harness-config-and-models.html`
  - Tools: `.../harness-tools.html` · Security: `.../harness-security.html`
- Control-plane API: `CreateHarness`, `Harness`, `InvokeHarness` (bedrock-agentcore-control / data plane)
- Code samples: `amazon-bedrock-agentcore-samples-1/06-workshops/11-AgentCore-harness`
  - `00-getting-started/CLI.md`, `00-getting-started/01_getting_started_bedrock.ipynb`
  - `01-advanced-examples/02-gateway-integration`, `03-execution-limits`, `07-oauth`
- NOTE: the **AgentCore *toolkit* MCP** (`search_agentcore_docs`) has **no harness docs** —
  use the **AWS documentation MCP** (`read_documentation` on the devguide URLs) instead.

---

## 0. Prerequisites

| # | Command | Status | Source / Note |
|---|---------|--------|---------------|
| 0.1 | `npm i -g @aws/agentcore@preview` | ⬜ | CLI.md. Confirm resulting version. |
| 0.2 | `agentcore --version` | ✅ | Canonical = preview `1.0.0-preview.13` (validated via extracted package). Local stable was 0.13.1/0.14.1 — not used for harness. |
| 0.3 | `aws sts get-caller-identity` | ✅ | Account 839898192353. |

---

## 1. Lab 1 — Launch & deploy a harness (getting-started CLI flow)

> **Verified create path (preview.13):** `agentcore create` scaffolds a **project** (agent-oriented);
> the harness is added with **`agentcore add harness`** (matches the devguide). CLI.md's
> "`create --name X --model-provider bedrock` = a harness" is misleading on preview.13.

### Lab 1 — workshop-page command inventory (ALL executed live, us-west-2, 2026-06-13)
Maps every command block in `content/20-lab1-runtime/index.en.md` to its live result.

| Step | Workshop command | Status | Result / note |
|---|---|---|---|
| 1 | `agentcore validate` | ✅ | `Valid` (on corrected flat harness.json) |
| 1 | `agentcore deploy -y -v` | ✅ | Stack `AgentCore-portfoliochk-default` CREATE_COMPLETE; harness deployed |
| 3 | `agentcore status` | ✅ | `PortfolioAdvisor: Deployed` |
| 3 | invoke — "current analysis for AAPL…" | ✅ | Correct (price/PE/Buy from system-prompt data) |
| 3 | invoke — "compliance rules for options trading?" | ✅ | Correct (Senior Advisor / 365d / $50k). Use `--json` for scripted capture. |
| 4 | invoke `--model-id …claude-haiku-4-5-20251001-v1:0` "Which sector is JPM in? One word." | ✅ | `Financials` — invoke-time model override works |
| 4 | invoke — "Compare AAPL and MSFT … flag any compliance concerns." | ✅ | Correct side-by-side |
| 5 | invoke (same `$SESSION_ID`) — "I'm interested in tech stocks" | ✅ | OK |
| 5 | invoke (same `$SESSION_ID`) — "Compare the two biggest ones" | ✅ | **Remembered context** → compared AAPL/MSFT. Confirms harness sessions are stateful (no Memory resource needed). |
| 5 | invoke (NEW session) — "What's its PE ratio and risk level?" | ✅ **FIXED** | Was: "Compare the two biggest ones" (derivable from system prompt → false isolation). Now uses a pronoun referent: same session establishes "Goldman Sachs", new session asks "its PE/risk" and the agent **asks which stock** (true context loss). Live-verified. |
| 6 | ~~`agentcore logs --harness …`~~ → CloudWatch GenAI Observability console | ✅ **FIXED** | `agentcore logs` has no `--harness` flag (runtime-only) on preview.13. Removed the CLI logs block; Step 6 now uses the CloudWatch console route only. |

**Narrative note (line ~124):** "`agentcore create … (which generates harness.json)`" is misleading — `create` scaffolds an agent project; `harness.json` comes from `agentcore add harness`.

### CLI scaffolding commands (preview.13)

| # | Command | Status | Source / Note |
|---|---------|--------|---------------|
| 1.1 | `agentcore create --no-agent --project-name <proj>` (or with an agent) | ✅ | Scaffolds `agentcore/` + `agentcore.json`. Verified locally on preview.13. |
| 1.2 | `agentcore add harness --name PortfolioAdvisor --model-id global.anthropic.claude-sonnet-4-6 --system-prompt "..." --no-harness-memory` | ✅ | Generates flat `app/<name>/harness.json` (see CRITICAL FINDING). `--no-harness-memory` keeps Lab 1 standalone. |
| 1.3 | `agentcore deploy` (`-y -v` valid) | ✅ | **Live-deployed to us-west-2** (acct 839898192353). CDK stack `AgentCore-portfoliochk-default` created exec role + harness in ~90s. No CDK bootstrap issue. |
| 1.4 | `agentcore status` | ✅ | Reports `PortfolioAdvisor: Deployed` (`arn:aws:bedrock-agentcore:us-west-2:...:harness/portfoliochk_PortfolioAdvisor-...`). |
| 1.5 | `agentcore invoke --harness PortfolioAdvisor --session-id <id> "..."` | ✅ | **Live invoke succeeded** — returned AAPL analysis from system-prompt reference data. Model `global.anthropic.claude-sonnet-4-6` access OK in us-west-2. |
| 1.6 | `agentcore validate` | ✅ | Passes on the **flat** harness.json; would FAIL on the workshop bundle's wrapper shape (the proof). |

**Resolved open questions for Lab 1**
- ✅ `harness.json` shape = **flat** (see CRITICAL FINDING), not the `{type,name,config}` wrapper.
- ✅ `global.anthropic.claude-sonnet-4-6` is the documented deploy-time default model.

---

## 2. Lab 1 — Right-size the model live (per-invocation override)

| # | Command | Status | Source / Note |
|---|---------|--------|---------------|
| 2.1 | `agentcore invoke --harness HarnessBedrock --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 --session-id $(uuidgen) "Which sector is JPM in? One word."` | ✅ | **Live-verified in us-west-2** — Haiku override returned `Financials`. `--model-id` override works at invoke time. |
| 2.2 | `agentcore invoke --harness HarnessBedrock --session-id $(uuidgen) "Compare AAPL and MSFT on valuation and risk."` | ✅ | Default-model path live-verified (AAPL analysis returned). |

**Overridable at invoke time (✅ confirmed in preview.13 `invoke --help`, "Model & Runtime Overrides (harness only)"):**
`--model-id`, `--model-provider`, `--api-key-arn`, `--tools`, `--allowed-tools`, `--skills`,
`--system-prompt`, `--actor-id`, `--max-iterations`, `--max-tokens`, `--harness-timeout`;
plus `--harness`, `--harness-arn`, `--region`, `--bearer-token`, `--session-id`, `--verbose`.

---

## 3. Lab 2 — Gateway integration  (ALL executed live as workshop user, acct 740610485731, us-west-2)

> Maps every command in `content/30-lab2-gateway/index.en.md`. Run as `WSParticipantRole/Participant`.
> **Structural finding:** `add tool --gateway <name>` resolves the ARN **from deployed state**, so the
> Gateway must be **deployed before** Step 5. The lab's "one deploy" framing is wrong → **two deploys**
> (Gateway after Step 3, harness at Step 7). Lab content updated.

| Step | Command | Status | Result / fix |
|---|---------|--------|---------------|
| 1 | Load SSM env (`portfolio-env.sh`) | ✅ | All params resolve (Cognito, Lambda ARNs, roles). |
| 2 | `agentcore add gateway --name my-gateway --authorizer-type CUSTOM_JWT --discovery-url … --allowed-clients … --allowed-scopes …` | ✅ **FIXED** | Lab passed `--role-arn $GATEWAY_ROLE_ARN` → **invalid flag** (`unknown option '--role-arn'`). Removed; deploy auto-provisions the gateway role. |
| 3 | `agentcore add gateway-target --type lambda-function-arn --name … --lambda-arn … --tool-schema-file … --gateway my-gateway` (×2) | ✅ | Flags correct. Needs the bundle's `tool/*.json` schemas present. |
| 3.5 | `agentcore deploy -y -v` (deploy Gateway) | ✅ **ADDED** | New step — Gateway must be deployed so Step 5 can resolve its ARN. |
| 4 | `agentcore add credential --name my-gateway-m2m --type oauth --discovery-url … --client-id … --client-secret … --scopes …` | ✅ | Flags correct. Secret read via `describe-user-pool-client`. |
| 5 | `agentcore add tool --harness PortfolioAdvisor --type agentcore_gateway --name my-gateway --gateway my-gateway --outbound-auth oauth --provider-arn $GATEWAY_M2M_CRED_ARN --scopes … --grant-type CLIENT_CREDENTIALS` | ✅ **FIXED** | Lab used `--credential-arn` → **does not exist**; correct flag is **`--provider-arn`**. Added `--grant-type CLIENT_CREDENTIALS`. harness.json `outboundAuth.oauth` block confirmed. |
| 6 | Patch `harness.json`: `authorizerType=CUSTOM_JWT` + `authorizerConfiguration.customJwtAuthorizer{discoveryUrl,allowedClients}` | ✅ **FIXED** | Lab wrote `customJWTAuthorizer` (wrong casing) and **omitted `authorizerType`** → would fail `validate`. Fixed to camelCase + `authorizerType`. |
| 7 | `agentcore validate` + `agentcore deploy -y -v` | ✅ | `Valid`; harness redeployed with inbound JWT + gateway tool. |
| 9 | Get token (`initiate-auth USER_PASSWORD_AUTH`) | ✅ | `workshopuser@example.com` token (1107 chars). |
| 9 | Authed invoke "Check the portfolio risk for PORT-001" `--bearer-token` | ✅ | `check_portfolio_risk` via Gateway → PORT-001 risk report (score 2.1/10). Outbound M2M worked. |
| 9 | Unauthed invoke (no token) | ✅ **wording fix** | Rejected: "configured for CUSTOM_JWT but no bearer token is available." NOT a literal `401` — lab reworded. |
| 10 | Trade "Buy 5000 shares of MSFT…" `--bearer-token` | ✅ | `execute_trade` via Gateway → ORD-LMT-MSFT-5000 (succeeds pre-Cedar). |

**Confirmed `harness.json` gateway tool shape (CLI):**
```json
{ "type": "agentcore_gateway", "name": "my-gateway",
  "config": { "agentCoreGateway": { "gatewayArn": "<arn>",
    "outboundAuth": { "oauth": { "providerArn": "<arn>", "scopes": ["…"], "grantType": "CLIENT_CREDENTIALS" } } } } }
```

---

## 4. Lab 2 — auth facts (verified)

| # | Item | Status | Note |
|---|------|--------|------|
| 4.1 | Inbound: `authorizerType: CUSTOM_JWT` + `authorizerConfiguration.customJwtAuthorizer` (**camelCase**) | ✅ | Differs from boto3/Gateway `customJWTAuthorizer`. Both `authorizerType` AND the config block required. |
| 4.2 | Outbound = M2M client-credentials (`outboundAuth.oauth`, `grantType CLIENT_CREDENTIALS`); end-user identity does NOT reach Gateway/Cedar | ✅ | `--provider-arn` on `add tool` (not `--credential-arn`). `USER_FEDERATION` grant exists for OBO. |
| 4.3 | `add credential --type oauth` flags: `--discovery-url --client-id --client-secret --scopes` | ✅ | Verified live. |
| 4.4 | `add tool` outbound flags: `--outbound-auth oauth --provider-arn --scopes --grant-type` | ✅ | Verified live (NOT `--gateway-provider-arn`; that's a different command's flag). |

---

## 5. Lab 3 — Governance (Cedar policy engine)  (ALL executed live as workshop user, acct 740610485731, us-west-2)

> Maps every command in `content/50-lab4-governance/index.en.md`. Builds on the Lab 2 gateway/harness.

| Step | Command | Status | Result / note |
|---|---------|--------|---------------|
| 1 | `agentcore add policy-engine --name PortfolioAdvisorPolicyEngine --description … --attach-to-gateways my-gateway --attach-mode ENFORCE` | ✅ | Flags correct. |
| 2 | Get Gateway ARN via `aws bedrock-agentcore-control list-gateways`/`get-gateway` | ✅ | Works. |
| 2 | `agentcore add policy --name trade_quantity_limit --engine … --statement "permit(... ExecuteTrade___execute_trade ...) when { context.input.quantity < 1000 };"` | ✅ | Triple-underscore action name correct. |
| 2 | `agentcore add policy --name portfolio_risk_check_policy --engine … --statement "permit(... PortfolioRiskCheck___check_portfolio_risk ...);" --validation-mode IGNORE_ALL_FINDINGS` | ✅ | Flags correct. |
| 3 | `agentcore deploy -y -v` | ✅ | Policy engine **auto-attached** to gateway — the troubleshooting workaround was NOT needed. |
| 5 | invoke "buy 500 shares of AAPL" (Test 1) | ✅ | Executed (ORD-MKT-AAPL-500) — 500 < 1000 permit. |
| 5 | invoke "Buy 5000 shares of MSFT" (Test 2) | ✅ | **DENIED** — "Trade Execution Blocked — Policy Enforcement". Same trade that succeeded in Lab 2. |
| 5 | invoke "Check the portfolio risk for PORT-002" (Test 3) | ✅ | Succeeded — permit keeps risk check alive under default-deny. |
| 6 | ~~`agentcore logs --harness PortfolioAdvisor --since 5m`~~ → CloudWatch console | ✅ **FIXED** | Same bug as Lab 1: `logs` has no `--harness`. Removed CLI block; Step 6 uses the GenAI Observability console. |
| Rung 1 | `agentcore add policy --name restricted_ticker_policy … forbid(... ) when { ["GS"].contains(context.input.ticker) };` + deploy + test "buy 100 GS" | ✅ **FIXED** | Was `["RESTRICTED-001","RESTRICTED-002"]` + "buy 100 RESTRICTED-001" → the model **self-refused** the unknown ticker and never called `execute_trade`, so Cedar `forbid` never fired (false-positive "denial"). Now forbids **GS** (a known ticker the agent will trade, system-prompt rates it "Buy"): live-verified the agent calls `execute_trade` and the Gateway returns a genuine **restricted_ticker_policy** denial — `forbid` overrides the qty<1000 `permit`. Control "buy 100 AAPL" still executes. |

| 5.3 | Policy-engine attach modes `LOG_ONLY \| ENFORCE` | ✅ | Confirmed (gateway guide + live ENFORCE). |
| 5.4 | Re-confirm Cedar evaluation when gateway is attached to a **harness** (vs runtime). | ⬜ | The harness backs a `::Runtime`-type resource — confirm the policy attaches the same way. |

---

## 6. Operations — logs, status, limits, cleanup

| # | Command | Status | Source / Note |
|---|---------|--------|---------------|
| 6.1 | `agentcore logs --harness PortfolioAdvisor --since 10m` | ⬜ | Workshop Lab 1 Step 6. Confirm `logs --harness` + `--since`. |
| 6.2 | Execution limits are **invoke-time** params: `maxIterations`, `maxTokens`, `timeoutSeconds`. | ✅ | Confirmed in `CreateHarness` (also settable as defaults) + 03-execution-limits. **Not** `harnessTimeoutSeconds`. |
| 6.3 | `aws bedrock-agentcore-control list-harnesses --region <r>` | ⬜ | Harness README cleanup. |
| 6.4 | `aws bedrock-agentcore-control delete-harness --region <r> --harness-id <id>` | ⬜ | Cleanup. |
| 6.5 | `agentcore status` / teardown for the project-level resources | ⬜ | Confirm CLI teardown path. |

---

## Run log (append actual results here)

| Date | Cmd # | Command run | Result | New status |
|------|-------|-------------|--------|-----------|
| 2026-06-13 | env | `npm view @aws/agentcore dist-tags` | `preview: 1.0.0-preview.13`, `latest: 0.19.0` | ✅ |
| 2026-06-13 | env | `npm i -g @aws/agentcore@preview` (local box) | FAILED — npm 10.9.4 arborist bug `#pruneBundledMetadeps … reading 'resolve'` on bundled deps. Worked around via `npm pack` + local `npm install`. **Test whether the devbox's npm hits this too.** | 🟡 |
| 2026-06-13 | 1.1 | `agentcore create --no-agent --project-name portfoliochk` (preview.13) | Project + `agentcore.json` scaffolded | ✅ |
| 2026-06-13 | 1.2 | `agentcore add harness --name PortfolioAdvisor --model-id global.anthropic.claude-sonnet-4-6 --system-prompt "..."` | Generated **flat** `app/PortfolioAdvisor/harness.json` (+ default memory) | ✅ |
| 2026-06-13 | — | Read `HarnessSpecSchema` + generated file | Confirmed flat shape; `model:{provider,modelId}`; `systemPrompt:string`; `customJwtAuthorizer` camelCase → **workshop bundle harness.json is wrong** | ✅ (finding) |
| 2026-06-13 | inv | `agentcore invoke --help` (preview.13) | `--harness`, `--harness-arn`, `--bearer-token`, all harness overrides present | ✅ |
| 2026-06-13 | 1.6 | `agentcore validate` on corrected flat harness.json (us-west-2) | `Valid` | ✅ |
| 2026-06-13 | 1.3 | `agentcore deploy -y -v` → us-west-2 (acct 839898192353) | Stack `AgentCore-portfoliochk-default` CREATE_COMPLETE in ~90s; exec role `portfoliochk_PortfolioAdvisor`; harness deployed | ✅ |
| 2026-06-13 | 1.4 | `agentcore status` | `PortfolioAdvisor: Deployed` (harness ARN in us-west-2) | ✅ |
| 2026-06-13 | 1.5 | `agentcore invoke --harness PortfolioAdvisor --session-id <id> "...AAPL..."` | Returned full AAPL analysis from system-prompt data; Sonnet 4.6 access OK | ✅ |
| 2026-06-13 | 2.1 | `agentcore invoke ... --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 "Which sector is JPM in?"` | `Financials` — invoke-time model override works | ✅ |
| 2026-06-13 | L1-S3b | invoke "compliance rules for options trading?" (`--json`) | Senior Advisor / 365d / $50k | ✅ |
| 2026-06-13 | L1-S4b | invoke "Compare AAPL and MSFT … compliance concerns" | Correct side-by-side | ✅ |
| 2026-06-13 | L1-S5a | invoke same session "I'm interested in tech stocks" → "Compare the two biggest ones" | Remembered AAPL/MSFT context | ✅ |
| 2026-06-13 | L1-S5b | invoke NEW session "Compare the two biggest ones" | Still answered AAPL/MSFT → **isolation claim is FALSE** (answer derivable from system prompt) | ❌ bug |
| 2026-06-13 | L1-S6 | `agentcore logs --harness PortfolioAdvisor --since 10m` | `error: unknown option '--harness'`; `logs` is runtime-only → **no harness logs via CLI** | ❌ bug |
| 2026-06-13 | FIX | harness.json → flat shape; `validate` on bundle file | `Valid` | ✅ fixed |
| 2026-06-13 | FIX | Step 5 corrected demo: same session "Let's analyze Goldman Sachs" → "What's its PE/risk?" (answers GS); NEW session "What's its PE/risk?" → agent asks **which stock** | True context loss demonstrated | ✅ fixed |
| 2026-06-13 | FIX | Step 6: removed `agentcore logs --harness` block; CloudWatch console route only | n/a | ✅ fixed |
| 2026-06-13 | **WS** | **Re-ran ALL Lab 1 as workshop user** — `WSParticipantRole/Participant`, event `385b1f4d…`, account **740610485731**, us-west-2 | See below | ✅ |
| 2026-06-13 | WS | `agentcore deploy` (participant creds) | Stack `AgentCore-portfoliochk-default` deployed; harness `portfoliochk_PortfolioAdvisor-YlOHZGKbLi` | ✅ |
| 2026-06-13 | WS | `agentcore status` | `PortfolioAdvisor: Deployed` (us-west-2, acct 740610485731) | ✅ |
| 2026-06-13 | WS | invokes: AAPL / compliance / Haiku-JPM / compare | All correct (`Financials` for Haiku) | ✅ |
| 2026-06-13 | WS | Step 5 same session (GS → "its PE/risk?") | Remembered GS (14.2 / Medium) | ✅ |
| 2026-06-13 | WS | Step 5 NEW session ("its PE/risk?") | "I don't have enough context to identify which stock" → **true isolation** | ✅ |
| 2026-06-13 | WS | Step 6 logs | No CLI path; CloudWatch console only (per fix) | ✅ n/a |
| 2026-06-13 | **L2** | **Lab 2 run live as workshop participant** (acct 740610485731) | gateway+targets+credential+tool+inbound JWT deployed; authed risk-check + 5000-share trade via Gateway succeeded; unauthed rejected | ✅ |
| 2026-06-13 | L2-FIX | Step 2 `--role-arn` removed (invalid); Step 5 `--credential-arn`→`--provider-arn`; Step 6 `customJWTAuthorizer`→`customJwtAuthorizer`+`authorizerType`; added Gateway deploy after Step 3; 401 wording softened | Lab content updated | ✅ fixed |
| 2026-06-13 | **L3** | **Lab 3 run live as workshop participant** | policy engine + 2 policies deployed (auto-attached); 500 AAPL ✅, 5000 MSFT **DENIED**, PORT-002 risk ✅; Rung 1 restricted-ticker forbid blocks 100 RESTRICTED-001 | ✅ |
| 2026-06-13 | L3-FIX | Step 6 `agentcore logs --harness` removed (no `--harness` on `logs`); CloudWatch console only | Lab content updated | ✅ fixed |
| 2026-06-14 | **BUNDLE BUG** | Participant hit `agentcore invoke --harness PortfolioAdvisor` → **"No harnesses defined in configuration"** | Root cause below | ❌→✅ |
| 2026-06-14 | RC1 | Bundle `agentcore/agentcore.json` harness entry used `configLocation`/`networkMode` | CLI `HarnessRegistryEntrySchema` requires `{name, path}` (path = harness dir). Wrong keys → entry dropped → "No harnesses defined". Fixed to `path`. | ✅ fixed |
| 2026-06-14 | RC2 | Bundle `agentcore/cdk/` was a **pre-harness** scaffold | `bin/cdk.ts` never read `harnesses[]`; `cdk-stack.ts` created no harness role → deploy failed: "Could not find role ARN in CDK outputs". Replaced with CLI-generated harness-aware cdk (bin/cdk.ts, cdk-stack.ts, package.json, package-lock pinning `@aws/agentcore-cdk` alpha.36). | ✅ fixed |
| 2026-06-14 | VALIDATION GAP | My earlier Lab 1 "✅" used a **CLI-generated** project, NOT the shipped bundle's `agentcore.json`/`cdk` | Re-validated from the literal `static/workspace-bundle/`: `validate` + `deploy` + `invoke --harness` all succeed (sandbox us-west-2). | ✅ |
| 2026-06-14 | PUSH | Committed `ab6b8ec` (bundle agentcore.json + cdk), pushed `mainline` | live | ✅ |
| 2026-06-14 | CLEANUP | Removed unrelated payments constructs from bundle CDK (`9f0af2d`); re-validated deploy+invoke; pushed `mainline` | live | ✅ |
| 2026-06-14 | **PROVISION-LAYOUT** | Re-validated the **no-committed-CDK** layout (ship `app/` only; CLI generates `agentcore/` at provision time) end-to-end on the **workshop account** (740610485731, us-west-2, project `Ind306Demo`) | See below | ✅ |
| 2026-06-14 | L1 | validate→deploy→status→invokes (AAPL, compliance, Haiku JPM=Financials, compare, GS same-session remembers 14.2/Medium, new-session asks which stock) | All pass | ✅ |
| 2026-06-14 | L2 | add gateway + 2 targets + deploy; M2M credential; add tool (outboundAuth.oauth); inbound JWT; validate+deploy (harness role output `ApplicationHarnessPortfolioAdvisorRoleRoleArn...` present); token; authed risk PORT-001=2.1/10; unauthed rejected; 5000 MSFT trade ORD-LMT-MSFT-5000 succeeds | All pass | ✅ |
| 2026-06-14 | L3 | add policy-engine (ENFORCE) + 2 policies; deploy → gateway `policyEngineConfiguration{mode:ENFORCE}` confirmed; 500 AAPL permitted; **5000 MSFT genuinely DENIED** — agent surfaced *"blocked by the Gateway's policy enforcement layer … No policy applies (denied by default)"*; PORT-002 risk permitted | Core before/after pass | ✅ |
| 2026-06-14 | **L3-RUNG1 BUG→FIX** | Rung 1 `forbid` test "Buy 100 RESTRICTED-001" did **NOT** exercise Cedar — the model **self-refused** ("not a recognized ticker") and never called `execute_trade`. **Fixed**: forbid **GS** (known ticker) + test "buy 100 GS". Live-verified: agent calls the tool, Gateway returns genuine `restricted_ticker_policy` denial (`forbid` beats qty `permit`); control "buy 100 AAPL" executes. Lab content + this sheet updated. | content fixed | ✅ |
| 2026-06-14 | NOTE(local) | This box's npm copies `.bin/*` instead of symlinking → breaks `tsc` (`Cannot find module '../lib/tsc.js'`). Added symlink-repair to `build_wsproj.sh`. Devbox npm symlinks fine — NOT a workshop bug. | local-only | 🟡 |
| 2026-06-14 | NOTE(state) | Cancelling a `deploy` mid-run can orphan Cedar policies (created, then stack update interrupted) → next deploy fails `ConflictException: Policy with same name already exists`. Cleared via `delete-policy`/`delete-policy-engine`. Artifact of interrupting, not content. | caution | 🟡 |
| 2026-06-14 | **L2 step-by-step** | Re-ran Lab 2 **command-by-command** on a freshly torn-down+rebuilt `wsproj` (workshop acct, deleted stack `AgentCore-Ind306Demo-default` + orphan harnesses via `delete-harness` + credential). Every `add ...` returns in seconds; **gateway first-create deploy took ~6–8 min** (CFN custom resource), harness redeploy ~3–4 min. Authed risk PORT-001 ✅, unauth rejected ✅, 5000 MSFT `ORD-LMT-MSFT-5000` ✅. Nothing stuck — slow deploys only emit a spinner. | ✅ |
| 2026-06-14 | **TIMING FIX** | Lab time estimates were optimistic vs live runs. Updated content: **Lab 2** header→"two deploys — first Gateway create 5–8 min", Step 3.5→"5–8 min (+ spinner-not-stuck note)", Step 7→"~3–4 min"; **Lab 1** "2–3"→"2–4 min" (3 spots). Commands themselves unchanged (already validated correct). | content updated | ✅ |
| 2026-06-14 | **LAB1 CDK SYNTH FAIL → ROOT CAUSE + GUARD** | Participant box (event acct 436706435406) hit `agentcore deploy` → "CDK synth failed: pyproject.toml not found". Root cause via `node dist/bin/cdk.js`: `agentcore/agentcore.json` was a **code-agent** scaffold (`"runtimes":[{entrypoint:main.py, build:CodeZip}]`, **no `"harnesses"`**) — old/divergent provisioning, NOT the harness path. `agentcore validate` returns **Valid** anyway (doesn't catch runtime-vs-harness), so it only fails at deploy. Re-syncing assets does NOT fix it (the `agentcore/` dir is generated at instance boot, not part of the synced bundle). Fix on a live box: regenerate via `create --no-agent` + `add harness` (+ restore real account/region in aws-targets.json) → agentcore.json then shows `"harnesses":[{name,path}]` → deploy CREATE_COMPLETE. `add harness --no-memory` confirmed valid on preview CLI. | root-caused | ✅ |
| 2026-06-14 | **GUARD ADDED** | `static/devbox.yaml`: added fail-fast guard after scaffold — asserts `app/PortfolioAdvisor/harness.json` exists, `agentcore.json` has a `harnesses` entry and NO `runtimes`, and `agentcore validate` passes; hard-exits provisioning otherwise. FACILITATOR_GUIDE: added Lab 1 recovery recipe + the "relaunch event" note. Current `static/` devbox already uses the correct harness path; the broken box was an older build. | content updated | ✅ |
| 2026-06-14 | **GUARD BRICKED DEVBOX → NON-FATAL** | First real event from new mainline: `ec2codeserver CREATE_FAILED` ("Failed to receive 1 resource signal(s)"). Cause: the guard's `exit 1` ran BEFORE the `cfn-signal` line (end of userdata), so a tripped check aborted boot with no signal → 15-min timeout. Fix (`ee18fe9`): guard now logs WARN + writes `~/HARNESS_SETUP_WARNING.txt` and continues; never exits. A bricked devbox (no code-server) is worse than a fixable Lab 1 deploy. | fixed | ✅ |
| 2026-06-14 | **REAL ROOT CAUSE: `assets/` is the seed, not `static/workspace-bundle/`** | Fresh event (build ee18fe9, CLI confirmed preview.13 — NOT drift) still produced a **code-agent**: `agentcore.json` with `runtimes`/`main.py`/`PYTHON_3_14`, no `harnesses`, no `harness.json`. cloud-init log showed `download: s3://ws-event/.../assets/agentcore/agentcore.json` then `Added harness` then `cd .../agentcore/cdk: No such file or directory`. Two bugs: (1) the committed **`assets/`** dir (maps 1:1 onto `my-workspace/`) was the OLD pre-harness code agent (`assets/app/PortfolioAdvisor/main.py` + `assets/agentcore/agentcore.json` runtimes) — all my `static/workspace-bundle/` edits were dead because the build/devbox seeds from `assets/`, not `workspace-bundle/`. (2) devbox `cp -r .../agentcore my-workspace/agentcore` **nested** into the pre-seeded `agentcore/` (→ wrong agentcore.json, missing cdk/). Fix: mirrored `assets/` ← `static/workspace-bundle/` (harness.json + tool schemas incl. market_data_record.json; removed code-agent + stale agentcore/); devbox now `rm -rf my-workspace/agentcore` before the copy so the generated harness scaffold wins. NOTE: `assets/` and `static/workspace-bundle/` are now duplicate seeds — consolidate to one source later. | fixed | ✅ |

**Workshop-user validation note:** Pulled participant creds via Workshop Studio MCP for the running IND event; deployed the **fixed** flat `harness.json` into the participant account. All Lab 1 commands pass end-to-end as `WSParticipantRole`. Caveat: the running event's content build (`e496e4e2`) still carries the OLD bundle — the fix must be committed + rebuilt so a fresh event ships the corrected `harness.json`.

---

## Next actions
1. **(BLOCKING)** Fix `static/workspace-bundle/app/PortfolioAdvisor/harness.json` to the flat CLI shape (owner must unfreeze the bundle). Then `agentcore validate` should pass.
2. Live `agentcore deploy` of the corrected harness in a test account/us-west-2 → fill 1.3/1.4 and Sections 3–6.
3. Reconcile lab pages + `HARNESS_MIGRATION.md` (its `bedrockModelConfig`/`systemPrompt`-array "corrections" apply to the boto3 API, not the CLI file).
4. Confirm the devbox npm version installs `@aws/agentcore@preview` cleanly (local npm 10.9.4 hit a bundled-deps bug).
