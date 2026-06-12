# IND306 — Best Practices for Agentic AI with AgentCore in Financial Services

A hands-on AWS workshop for builders in financial services. Participants take a pre-built capital markets **portfolio advisor agent** and incrementally harden it for production: deploying it to AgentCore Runtime, connecting Lambda tools through an authenticated Gateway, and enforcing deterministic trade controls with Cedar policies. The session runs as a **60-minute builder format** (8-minute facilitator talk, then 52 contiguous minutes of self-paced labs) with three progressive deploys. The event stays live after the session ends so participants can continue with the self-paced labs on their own.

---

## Repo Structure

```
.
├── contentspec.yaml                  # Workshop Studio build manifest (lab pages, assets, IAM policy)
├── README.md                         # This file
├── FACILITATOR_GUIDE.md              # Delivery guide, run-of-show, troubleshooting
│
├── content/                          # Workshop Studio markdown (rendered as HTML for participants)
│   ├── index.en.md                   # Workshop root page
│   ├── 10-intro/                     # Introduction + orientation (at-event vs self-paced variants)
│   ├── 15-foundations/               # Foundations reading (CISO five questions, architecture)
│   │
│   │   ── LIVE LABS (60-min session) ──────────────────────────────────────────
│   ├── 20-lab1-runtime/              # Lab 1: Deploy to AgentCore Runtime (~10 min)
│   ├── 30-lab2-gateway/              # Lab 2: Connect Tools with Gateway + JWT Auth (~18 min)
│   ├── 50-lab4-governance/           # Lab 3 (live): Govern Agent Actions with Cedar Policies (~16 min)
│   │
│   │   ── SELF-PACED (post-session) ────────────────────────────────────────────
│   ├── 25-lab1b-observability/       # Observability Deep Dive (CloudWatch traces, session isolation)
│   ├── 35-lab2b-tool-registry/       # Enterprise Tool Registry
│   ├── 40-lab3-security/             # OAuth Token Flows: M2M & Token Lifecycle
│   ├── 60-lab5-evaluations/          # Evaluations (online eval, GoalSuccessRate)
│   ├── 70-lab6-vpc/                  # VPC Networking (private subnets, VPC endpoints)
│   ├── 80-optional-memory/           # Memory (semantic + summarization strategies)
│   ├── 85-optional-frontend/         # Frontend (Flask chat portal)
│   ├── 88-optional-cost/             # Cost Optimization (session lifecycle, eval sampling)
│   └── 90-summary/                   # Summary and resources
│
└── static/                           # Assets uploaded to Workshop Studio assets bucket
    ├── prereqs.yaml                  # CloudFormation: pre-provisions Cognito, Lambda, VPC, SSM params
    ├── devbox.yaml                   # Provisions the browser VS Code instance; seeds ~/PortfolioAdvisor
    ├── workshop-resources.yaml       # Supplemental CloudFormation resources
    ├── iam_policy.json               # IAM permissions granted to WSParticipantRole
    ├── images/                       # Architecture diagrams and screenshots
    └── workspace-bundle/             # Pre-built PortfolioAdvisor project delivered to each instance
```

> **Note on content/ numbering:** The live Lab 3 (Cedar governance) lives at `50-lab4-governance/` because it was originally the fourth lab. The directory name was preserved to avoid breaking Workshop Studio build history. Facilitators and participants see it labeled "Lab 3" on the page.

---

## Session Format

### 60-Minute Run-of-Show (AWS NY Summit)

| Clock | Duration | Activity |
|-------|----------|----------|
| 0:00–0:08 | 8 min | Facilitator talk: CISO five questions, target architecture, before/after Cedar arc, logistics ("your first command starts a deploy — the page tells you what to read while it runs") |
| 0:08–0:21 | 13 min | **Lab 1** — Deploy to AgentCore Runtime: deploy, read during wait, invoke, session-isolation A/B, one CloudWatch trace |
| 0:21–0:39 | 18 min | **Lab 2** — Connect Tools with Gateway + JWT Auth: env block from SSM, gateway with JWT authorizer, Lambda targets, runtime authorizer patch, one code edit, deploy, token, bearer invoke, 401 proof, 5 000-share trade succeeds |
| 0:39–0:55 | 16 min | **Lab 3 (live)** — Govern Agent Actions with Cedar Policies: policy engine, 2 Cedar policies, deploy, ✅500-share trade, ❌5 000-share trade DENIED, ✅risk check, audit record |
| 0:55–1:00 | 5 min | Buffer / fast-finisher ladder: restricted-ticker policy → Observability Deep Dive → OAuth Token Flows |

### Three-Deploy Design

Each live lab contains exactly one `agentcore deploy` (~2–3 min). Every deploy is paired with an on-page **"While this deploys"** reading box so participants stay engaged rather than idle:

| Deploy | Lab | Reading during wait |
|--------|-----|---------------------|
| 1 | Lab 1 — Runtime | CISO five questions + code tour |
| 2 | Lab 2 — Gateway | Credential patterns + tool schemas |
| 3 | Lab 3 (live) — Governance | Cedar-vs-prompt-rules + policy walkthrough |

---

## How Content Is Delivered

1. **Workshop Studio build:** A `git push` to this repository triggers an automatic Workshop Studio build. The build validates `contentspec.yaml`, the IAM policy, and the CloudFormation templates, then produces an immutable content snapshot.

2. **Static assets:** Everything in `static/` is uploaded to the Workshop Studio assets bucket and made available on participant instances at provisioning time.

3. **Participant environment:** `devbox.yaml` provisions a browser-based VS Code instance (Amazon Linux) for each participant. It installs the AgentCore CLI, seeds `~/PortfolioAdvisor/` from `workspace-bundle/`, and wires up environment defaults. Participants use only the browser VS Code terminal — no local IDE or PowerShell required.

4. **Pre-provisioned infrastructure:** `prereqs.yaml` deploys a CloudFormation stack per participant account that creates the Cognito User Pool, Lambda functions (`workshop-check-portfolio-risk`, `workshop-execute-trade`), VPC with private subnets and VPC endpoints, and SSM Parameter Store entries under `/app/portfolioadvisor/agentcore/`. Participants consume these resources; they do not create them.

---

## Key Design Choices

- **No scaffolding phase.** The agent workspace is fully populated when participants open their browser. Lab 1 starts with `agentcore deploy`, not `agentcore create`.
- **One code edit total.** Lab 2 has participants add `import jwt`, an `extract_user_id()` helper, and auth-forwarding to the invoke call. Every other change is configuration (`agentcore.json`) or CLI commands.
- **Gateway born with JWT.** The gateway (`my-gateway`) is created with `--authorizer-type CUSTOM_JWT` on first creation. It is never recreated during the session.
- **Env block replaces SSM copy-paste.** Lab 2 starts with a single `source ~/portfolio-env.sh` that loads all SSM values into shell variables, eliminating multi-step parameter lookups.
- **Before/after trade demo.** Lab 2 ends with a 5,000-share MSFT trade succeeding (no policy). Lab 3 ends with the identical trade denied by Cedar policy — without any code change.
- **All Windows/PowerShell tabs removed.** Browser VS Code on Amazon Linux is the only supported environment.
- **Region:** us-west-2 only. All resource names, SSM paths, and VPC endpoint service names are hardcoded to us-west-2.
