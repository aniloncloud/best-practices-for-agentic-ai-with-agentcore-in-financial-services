---
title: "Optional Lab: OAuth Token Flows — M2M & Token Lifecycle"
weight: 67
---

**⏱️ ~20 minutes (self-paced)**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. Prerequisites: Labs 1–2. If you're in a new terminal, run `source ~/portfolio-env.sh` first.
:::

## Overview

In Lab 2 you secured the harness (inbound) and the Gateway with a Cognito JWT authorizer. End users log in with the **resource-owner-password** flow — a human authenticates with a username and password, and that token identifies the person on every call to the agent.

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

Both produce a JWT access token. Both work with the same `authorizerConfiguration`. The difference is **who** the token represents — a human user or a service identity. (In this workshop the harness inbound authorizer allows the web/user client; the M2M client's primary role is *outbound* auth to the Gateway, configured in Lab 2.)

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
        AgentCore Harness (PortfolioAdvisor)  [validates inbound JWT]
                        │
                        │ harness uses its own M2M token (Lab 2 outbound auth)
                        ▼
        AgentCore Gateway (my-gateway)  [validates M2M JWT]
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
Use the **user token** (`$TOKEN`) for human callers; use the **M2M token** (`$M2M_TOKEN`) for automated pipelines and other services. Both are JWTs the harness inbound authorizer can validate (if the client is allowlisted). Note the harness→Gateway hop uses a *separate* M2M credential (Lab 2), so the inbound identity is recorded at the harness — it is not what the Gateway or Cedar evaluates.
:::

---

## Step 4: Invoke the Agent with the M2M Token

An M2M token is a valid JWT, but the **harness inbound authorizer in this workshop allows the web/user client** (Lab 2). To invoke the harness directly with the M2M token, add the M2M client to the harness allowlist first:

:::alert{header="Inbound allowlist" type="warning"}
By default the harness rejects the M2M client *inbound* (it's used for *outbound* Gateway auth). To run the invoke below, add `$COGNITO_CLIENT_ID` to the harness `authorizerConfiguration.allowedClients` and `agentcore deploy`.
:::

:::code{language=bash}
SESSION_M2M=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke --harness PortfolioAdvisor "What are the compliance rules for options trading?" \
  --session-id $SESSION_M2M --bearer-token "$M2M_TOKEN"
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

Because the M2M token has no `username` claim, the caller identity is the `sub` (the M2M client ID). This inbound identity is recorded at the harness; the Gateway and Cedar (Lab 3) evaluate the harness's *outbound* M2M identity, not this inbound caller.

---

## Concept: how an agent authenticates to its tools

When an agent calls a downstream tool, it presents one of two kinds of identity:

- **As itself (machine-to-machine).** The agent uses its own service credential — what this workshop does (the harness fetches an M2M token to call the Gateway). Simple, and the right default when the tool doesn't need to know *which* user is behind the request. The downstream sees the agent.
- **As the user (on-behalf-of).** The agent exchanges the user's inbound token for a new, scoped token that carries **both** the user's and the agent's identity. Now the tool can enforce per-user authorization, and the audit trail shows the real person. This is the stronger pattern when downstream access must be scoped to the end user.

On-behalf-of is brokered by AgentCore Identity — the agent never handles the inbound token or client secrets. It does require an identity provider that supports OAuth token exchange (RFC 8693 / RFC 7523). Providers like Microsoft Entra, Okta, and Auth0 support it; Amazon Cognito (used in this workshop) does not, which is why these labs demonstrate the M2M pattern. For production systems that need per-user authorization at the tool, on-behalf-of is the pattern to reach for.

→ Reference: [On-behalf-of token exchange with AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html)

---

## Token Lifecycle in Production

:::code{language=bash showCopyAction=false}
User/service authenticates → Cognito issues access token (60-min TTL)
    ↓
Client stores token in memory only — never on disk, never in env files
    ↓
Client passes token on each invocation (Authorization: Bearer <token>)
    ↓
AgentCore Harness validates inbound (signature + expiry + audience + issuer)
    ↓
Harness calls the Gateway with its own M2M token (Lab 2 outbound auth)
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
The harness and Gateway are independent HTTPS endpoints. In Lab 2 you saw that each was created with its own JWT authorizer. Assume each endpoint will be discovered and called directly. Authenticate at all of them.
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
