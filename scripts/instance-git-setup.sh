#!/usr/bin/env bash
# Run ONCE on the live VS Code server to attach the S3-seeded workspace to your
# GitHub repo, so you can iterate with `git pull` instead of recreating events.
#
# After this runs, the normal loop is:
#     git pull github mainline   # on the instance
#     agentcore deploy && agentcore invoke "ping"
#
# Safe by design: backs up the workspace first; instance state (deployed-state.json,
# aws-targets.json, .env.local, venv/) is gitignored, so a hard reset won't touch it.
#
# Usage (on the instance):
#     bash instance-git-setup.sh [--branch mainline] [--repo <git-url>] [--dest ~/PortfolioAdvisor]
set -euo pipefail

# Public repo — HTTPS needs no credentials for read/pull on the instance.
REPO="https://github.com/aniloncloud/best-practices-for-agentic-ai-with-agentcore-in-financial-services.git"
BRANCH="mainline"
DEST="${HOME}/PortfolioAdvisor"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)   REPO="$2";   shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --dest)   DEST="$2";   shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Resolve the ~/PortfolioAdvisor symlink to the real workspace dir.
if [[ -L "$DEST" ]]; then DEST="$(readlink -f "$DEST")"; fi
if [[ ! -d "$DEST" ]]; then echo "ERROR: workspace not found: $DEST" >&2; exit 1; fi
cd "$DEST"

# Backup before touching anything.
TS="$(date +%Y%m%d-%H%M%S)"
BK="/tmp/portfolioadvisor-backup-${TS}.tgz"
echo "INFO: backing up workspace -> ${BK}"
tar --exclude='venv' --exclude='.venv' --exclude='node_modules' --exclude='cdk.out' \
    --exclude='__pycache__' -czf "$BK" . || echo "WARN: backup failed (continuing)"

# Initialize git if the S3-seeded workspace isn't a repo yet.
if [[ ! -d .git ]]; then
  echo "INFO: git init on ${DEST}"
  git init -q
  git checkout -q -b "$BRANCH" 2>/dev/null || git checkout -q "$BRANCH" 2>/dev/null || true
fi

# Point 'github' at your repo (add or update).
if git remote get-url github >/dev/null 2>&1; then
  git remote set-url github "$REPO"
else
  git remote add github "$REPO"
fi

echo "INFO: fetching ${REPO} (${BRANCH})"
git fetch github "$BRANCH"

echo "INFO: aligning workspace to github/${BRANCH} (tracked files only; instance state preserved)"
git reset --hard "github/${BRANCH}"
git branch --set-upstream-to "github/${BRANCH}" "$BRANCH" 2>/dev/null || true

cat <<EOF

Done. Workspace is now a clone of:
  ${REPO}  (branch ${BRANCH})

Backup of the previous state: ${BK}

From now on, iterate with:
  cd ${DEST}
  git pull
  agentcore deploy && agentcore invoke "ping"

Preserved (gitignored, not overwritten): agentcore/.cli/deployed-state.json,
agentcore/aws-targets.json, .env.local, venv/.
EOF
