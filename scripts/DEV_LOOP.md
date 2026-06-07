# Dev iteration loop (no new Workshop Studio events)

Edit locally, push to GitHub, pull on the live VS Code server. No republish, no new event.

## Remotes

- `origin` → Workshop Studio content (`workshopstudio://...`) — used for publishing the workshop.
- `github` → `https://github.com/aniloncloud/best-practices-for-agentic-ai-with-agentcore-in-financial-services` (public) — used for the dev loop. Local push remote uses the SSH form; the instance pulls over HTTPS (no credentials needed).

## One-time: attach the live instance to GitHub

The VS Code workspace is seeded from the S3 assets bucket, not Git. Run this **once** on the instance to make it a clone of the GitHub repo:

```bash
# copy scripts/instance-git-setup.sh onto the instance (or paste it), then:
bash instance-git-setup.sh
```

It backs up the workspace first and preserves instance-specific state. The repo is public, so the instance pulls over HTTPS with no credentials needed.

## The loop

Laptop:
```bash
git add -A && git commit -m "iterate"
git push github mainline
```

Live VS Code server:
```bash
cd ~/PortfolioAdvisor
git pull
agentcore deploy && agentcore invoke "ping"
```

`git pull` merges and flags conflicts instead of blind-overwriting, so in-progress instance edits aren't silently lost.

## Not tracked in git (instance-specific / secrets)

- `agentcore/.cli/deployed-state.json` — created by `agentcore deploy`
- `agentcore/aws-targets.json` — written by `devbox.yaml` per account/region
- `**/.env.local` — secrets
- `venv/`, `node_modules/`, `cdk.out/`, `__pycache__/`

## Publishing to participants (separate from the dev loop)

`git push github` does **not** reach participants. To update what participants receive, publish through Workshop Studio (`origin`) so `static/` is republished to the assets bucket.
