---
title: "Optional Lab: OAuth Token Flows — M2M & Token Lifecycle"
weight: 55
---

**⏱️ ~20 minutes (self-paced)**

:::alert{header="Self-paced lab" type="info"}
Do this **after the live session** — your event account stays live. Prerequisites: Labs 1–3. If you're in a new terminal, run `source ~/portfolio-env.sh` first.
:::

## Overview

In Lab 2 you secured both the AgentCore Runtime and the Gateway with a Cognito JWT authorizer using the **resource-owner-password** flow — a human user authenticates with a username and password and the resulting token identifies that person in every request.

This deep dive covers the **other** half of the OAuth 2.0 picture:

- The **client_credentials** (machine-to-machine) grant — no username, no password, no human in the loop.
- How to inspect the token claims to understand the difference.
- Token **lifecycle management** patterns for production systems — proactive refresh, never-embed rules, and key rotation.

### OAuth 2.0 Grant Types

AgentCore Runtime validates standard JWT tokens — it doesn't care which OAuth flow produced them. Your Cognito setup supports two:

| Grant Type | Use Case | Who Has It |
|---|---|---|
| **Resource Owner Password** (`USER_PASSWORD_AUTH`) | Human users — interactive login with username/password | Test user: `workshopuser@example.com` |
| **Client Credentials** (`client_credentials`) | Machine-to-machine — CI pipelines, other agents, batch jobs | M2M client: pre-provisioned |

Both produce a JWT access token. Both work with the same `authorizerConfiguration`. The difference is **who** the token represents — a human user or a service identity.

### What You're Exploring

:::code{language=bash showCopyAction=false}
┌──────────────────────────────────────────────────────────────────┐
│  OAuth 2.0 Flows                                                 │
│                                                                  │
│  User (password grant)        Service (client_credentials)       │
│       │                               │                          │
│       ▼                               ▼                          │
│  Cognito User Pool ─────────── Cognito User Pool                 │
│       │                               │                          │
│       └──── JWT access token ─────────┘                          │
└──────────────────────────────────────────────────────────────────┘
                        │
                        ▼
        AgentCore Runtime (my-gateway)  [requires JWT]
                        │
                        │ forwards token
                        ▼
        AgentCore Gateway (my-gateway)  [requires JWT]
                        ├── PortfolioRiskCheck → Lambda
                        └── ExecuteTrade → Lambda
:::

No deploys happen on this page. You only mint tokens, invoke the agent, and inspect claims.

---

## Step 1: Confirm Your Environment

The `~/portfolio-env.sh` file created in Lab 2 already exports everything you need. Verify it is loaded:

:::code{language=bash}
echo "Domain:     $COGNITO_DOMAIN"
echo "Scope:      $COGNITO_SCOPE"
echo "Pool ID:    $COGNITO_POOL_ID"
echo "Client ID:  $COGNITO_CLIENT_ID"
echo "Web Client: $COGNITO_WEB_CLIENT_ID"
:::

If any variable is blank, reload the file:

:::code{language=bash}
source ~/portfolio-env.sh
:::

---

## Step 2: Refresh Your User Token (Optional)

Lab 2 produced a `$TOKEN` for the resource-owner-password flow. If more than 60 minutes have passed, or if you are in a fresh terminal, re-mint it with one line:

:::code{language=bash}
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "User token refreshed"
:::

---

## Step 3: Obtain a Machine-to-Machine Token

For service-to-service calls (CI pipelines, batch jobs, other agents) use the `client_credentials` grant — no username or password required. The caller authenticates as an application, not a person.

Retrieve the M2M client secret from Cognito and exchange it for a token:

:::code{language=bash}
# Retrieve the M2M client secret
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $COGNITO_POOL_ID \
  --client-id $COGNITO_CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' --output text)

# Exchange credentials for a token via the Cognito token endpoint
M2M_TOKEN=$(curl -s -X POST "$COGNITO_DOMAIN/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$COGNITO_CLIENT_ID&client_secret=$CLIENT_SECRET&scope=$COGNITO_SCOPE" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "M2M token obtained successfully"
:::

Note that `$COGNITO_DOMAIN`, `$COGNITO_SCOPE`, `$COGNITO_POOL_ID`, and `$COGNITO_CLIENT_ID` are all already exported by `~/portfolio-env.sh` — no `aws ssm get-parameter` calls needed here.

:::alert{header="When to use which flow" type="info"}
Use the **user token** (`$TOKEN`) when you need per-user identity for policies and audit trails. Use the **M2M token** (`$M2M_TOKEN`) for automated pipelines and scheduled jobs that have no human user context. Both are accepted by the same `CUSTOM_JWT` authorizer — the Runtime does not distinguish between them at the token-validation layer. The distinction matters for identity propagation and Cedar policy evaluation downstream.
:::

---

## Step 4: Invoke the Agent with the M2M Token

The same `agentcore invoke` command that works with a user token also works with an M2M token — the authorizer on `my-gateway` accepts either:

:::code{language=bash}
SESSION_M2M=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What are the compliance rules for options trading?" \
  --session-id $SESSION_M2M --bearer-token "$M2M_TOKEN" --stream
:::

The agent responds normally. But notice what is different under the hood.

### Inspect the Token Claims

Decode both tokens (without verifying the signature — for inspection only) and compare the claims:

:::code{language=bash}
python3 - <<'EOF'
import base64, json, sys

def decode_jwt_payload(token):
    # JWT is header.payload.signature — decode the middle segment
    payload = token.split('.')[1]
    # Add padding so base64 doesn't complain
    padding = 4 - len(payload) % 4
    payload += '=' * (padding % 4)
    return json.loads(base64.urlsafe_b64decode(payload))

import os
user_token = os.environ.get('TOKEN', '')
m2m_token  = os.environ.get('M2M_TOKEN', '')

if user_token:
    u = decode_jwt_payload(user_token)
    print("=== User token claims ===")
    for k in ('sub', 'username', 'token_use', 'client_id', 'scope', 'exp'):
        print(f"  {k}: {u.get(k)}")

if m2m_token:
    m = decode_jwt_payload(m2m_token)
    print("\n=== M2M token claims ===")
    for k in ('sub', 'username', 'token_use', 'client_id', 'scope', 'exp'):
        print(f"  {k}: {m.get(k)}")
EOF
:::

Key observations:

| Claim | User token | M2M token |
|---|---|---|
| `username` | `workshopuser@example.com` | _(absent)_ |
| `sub` | User's UUID in the pool | App client ID |
| `token_use` | `access` | `access` |
| `scope` | Pool-level scopes | Resource server scope (e.g. `portfolioadvisor/invoke`) |
| `client_id` | Web client ID | M2M client ID |

Because the M2M token has no `username` claim, AgentCore Identity threads the `sub` claim — which is the M2M client ID — as the caller identity. This identity is what flows into Cedar policy evaluation in [Lab 3](../50-lab4-governance/).

---

## Token Lifecycle in Production

:::code{language=bash showCopyAction=false}
User/service authenticates → Cognito issues access token (60-min TTL)
    ↓
Client stores token in memory only — never on disk, never in env files
    ↓
Client passes token on each invocation (Authorization: Bearer <token>)
    ↓
AgentCore Runtime validates (signature + expiry + audience + issuer)
    ↓
Runtime forwards to Gateway (same token, re-validated at that layer)
    ↓
Token age > 55 min → Client proactively refreshes (REFRESH_TOKEN_AUTH)
    ↓
Token expires → Refresh token used → New access token (no re-login)
:::

**Proactive refresh — do not wait for a 401.** A 60-minute TTL means your agent may be mid-session when expiry hits. The recommended pattern is to refresh when fewer than 5 minutes remain, not on error:

:::code{language=bash}
# Example: refresh the user token using the refresh token
# (capture RefreshToken at login time and store it securely)
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow REFRESH_TOKEN_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters REFRESH_TOKEN="$REFRESH_TOKEN" \
  --query 'AuthenticationResult.AccessToken' --output text)
:::

**M2M tokens have no refresh token.** The `client_credentials` grant does not issue a refresh token — the client simply re-authenticates with its secret when needed. Keep the TTL short (Cognito default is 60 minutes) and re-mint on expiry.

---

## Defense in Depth: Production Best Practices

::::expand{header="Best practices reference (click to expand)"}

:::alert{header="Secure every layer independently" type="info"}
Runtime and Gateway are independent HTTPS endpoints. In Lab 2 you saw that each was created with its own JWT authorizer. Assume each endpoint will be discovered and called directly. Authenticate at all of them.
:::

**Multi-tenant isolation** — when a single agent deployment serves multiple users or teams:

| Requirement | How AgentCore Addresses It |
|---|---|
| User A cannot see User B's data | Session isolation (microVM per session) + JWT `sub` claim scoping |
| Role-based permissions | JWT custom claims (`role`, `team`) → Cedar policies evaluate them ([Lab 3](../50-lab4-governance/)) |
| Audit per user | JWT `sub` claim logged in every trace → query by user identity |
| Emergency revocation | Disable the Cognito app client → all tokens issued by that client immediately fail validation |
| Key rotation | Cognito rotates JWKS automatically; AgentCore re-fetches from `discoveryUrl` on each validation |

**Operational rules:**

- **`allowedClients` least privilege.** Issue separate Cognito app clients for different callers (users, pipelines, other agents) and list only the ones that need access. A compromised credential then affects only that one client.
- **Cognito rotates signing keys automatically.** AgentCore Runtime fetches public keys from the OIDC `discoveryUrl` on each validation — key rotation is transparent, no manual steps required.
- **Never embed tokens.** JWT tokens are credentials. Do not log them, store them in persistent environment variables, or include them in system prompts or tool descriptions. Read the token from the request context per invocation, forward it, and treat it as ephemeral.
- **M2M secrets belong in Secrets Manager** — not in environment variables or source control.

::::

---

## What's Next

- If you haven't completed [Lab 3: Govern Agent Actions with Cedar Policies](../50-lab4-governance/) yet, head there next — Cedar policies use the identity claims you inspected here.
- Other self-paced deep dives available after the live session:
  - [Observability Deep Dive](../25-lab1b-observability/)
  - [Evaluations](../60-lab5-evaluations/)
