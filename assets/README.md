# Participant workspace seed (`assets/`) — SOURCE OF TRUTH

This directory **is** the agent workspace every participant gets at `~/PortfolioAdvisor/`.
At provision time the devbox downloads this content into `my-workspace/`, so the
layout here maps 1:1 onto the participant's project root.

## What belongs here

- `app/PortfolioAdvisor/harness.json` — the declarative agent (model, system prompt,
  tools, skills). **This is the entire agent definition.**
- `app/PortfolioAdvisor/tool/*.json` — JSON-schema tool definitions used by Lab 2
  (Gateway targets) and Lab 2b (the Agent Registry record descriptor).
- `AGENTS.md`, `README.md` — docs that ship to the workspace.

## What must NOT be here

- **No `main.py` / `model/` / `mcp_client/` / `pyproject.toml`** — those are a *code agent*.
  This workshop is harness-based. A code agent here makes Lab 1 `agentcore deploy` fail
  with `CDK synth failed: pyproject.toml not found`.
- **No `agentcore/` directory.** The devbox generates `agentcore/` (config + CDK) at boot
  with `agentcore create --no-agent` + `agentcore add harness`, so the CDK always matches
  the installed CLI. It's gitignored here (`assets/agentcore/`) to prevent accidental commits.

## How to deploy a change (the ONLY delivery path)

`assets/` is delivered to participants by syncing it to the Workshop Studio asset bucket —
NOT by the normal git build. After editing files here:

```bash
aws s3 sync ./assets s3://ws-assets-us-east-1/1bc2dbf0-7b79-4c9c-8ece-46a78c6a598f --delete
```

Then trigger a new build (push to `mainline`) and create a new event. The build must
postdate the sync so the event snapshots the corrected assets.

## Sanity check on a provisioned box

`agentcore.json` should show `"harnesses": [{...}]` and empty `"runtimes": []`, and
`~/PortfolioAdvisor/app/PortfolioAdvisor/` should contain `harness.json` (not `main.py`).
If `~/HARNESS_SETUP_WARNING.txt` exists, the scaffold check failed — see `FACILITATOR_GUIDE.md`.

> History: there used to be a second, git-tracked copy at `static/workspace-bundle/`.
> It was NOT the live seed (this `assets/` dir is) and was deleted to remove the
> drift that once shipped a stale code agent. There is now one source of truth: here.
