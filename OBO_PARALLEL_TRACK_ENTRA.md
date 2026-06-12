# DRAFT — Parallel Track: Per-User Identity with On-Behalf-Of (Microsoft Entra)

> **STATUS: DRAFT for team review. Not wired into the workshop nav. Not dry-run-verified.**
> This is a *parallel* track to the live Lab 2 (which uses M2M outbound). It demonstrates
> the stronger FSI pattern — the agent calls downstream tools **as the end user** — using
> AgentCore on-behalf-of (OBO) token exchange. It uses **Microsoft Entra** because Amazon
> Cognito's token endpoint does not support the token-exchange/jwt-bearer grants OBO
> requires (see `OBO_COGNITO_FINDINGS.md`).

---

## Why this track exists

The live Lab 2 secures the agent with inbound JWT and reaches the Gateway with a
**machine-to-machine (M2M)** token. That means the Gateway and Cedar see the *agent's*
service identity, not the end user. Per-tool and per-argument policies (the 5,000-share
quantity limit) work great — but **per-user** authorization and audit do not.

On-behalf-of (OBO) closes that gap: the agent exchanges the inbound user token for a
**scoped downstream token that carries both the user's and the agent's identity**, so the
downstream resource can enforce per-user, zero-trust authorization at every hop.

## Architecture

```
End user → (inbound Entra JWT) → AgentCore Harness (PortfolioAdvisor)
                                      │
                                      │ 1. GetWorkloadAccessTokenForJWT
                                      │    (binds inbound user token + agent identity)
                                      ▼
                              AgentCore Identity
                                      │ 2. GetResourceOauth2Token
                                      │    (oauth2Flow = ON_BEHALF_OF_TOKEN_EXCHANGE)
                                      │    brokers RFC 7523 jwt-bearer to Entra
                                      ▼
                              Downstream scoped token  (carries user + agent identity)
                                      │
                                      ▼
                              Downstream resource (Graph API / protected API / Gateway tool)
```

Agent code never touches the inbound token or client secrets — AgentCore Identity brokers
the whole exchange.

---

## Prerequisites (one-time, would move to prereqs/account template)

- A **Microsoft Entra** tenant with two app registrations:
  - **Agent app** (confidential client) — holds the client ID/secret AgentCore uses for
    the OBO exchange; granted delegated permission to the downstream API.
  - **Downstream API** (resource server) — exposes a scope (e.g. `Portfolio.Read`) that
    the OBO token will target.
- The downstream resource that validates the OBO token (for this draft: a protected API
  or Microsoft Graph; in the workshop it would be the Gateway tool's backend).
- A test user in the Entra tenant.

> Cognito is intentionally not used here — it cannot perform the OBO token exchange.

## Step 1 — Register the OBO credential provider (Entra, built-in)

Entra has built-in OBO support in AgentCore Identity (`MicrosoftOauth2`), which uses the
RFC 7523 `JWT_AUTHORIZATION_GRANT` and auto-adds `requested_token_use=on_behalf_of`:

```bash
aws bedrock-agentcore-control create-oauth2-credential-provider \
  --cli-input-json '{
    "name": "portfolio-obo-entra",
    "credentialProviderVendor": "MicrosoftOauth2",
    "oauth2ProviderConfigInput": {
      "microsoftOauth2ProviderConfig": {
        "clientId": "<ENTRA_AGENT_APP_CLIENT_ID>",
        "clientSecret": "<ENTRA_AGENT_APP_CLIENT_SECRET>"
      }
    }
  }'
```

<details>
<summary>Custom-IdP equivalent (Auth0 / Okta / Keycloak / PingOne)</summary>

```bash
aws bedrock-agentcore-control create-oauth2-credential-provider \
  --cli-input-json '{
    "name": "portfolio-obo-custom",
    "credentialProviderVendor": "CustomOauth2",
    "oauth2ProviderConfigInput": {
      "customOauth2ProviderConfig": {
        "oauthDiscovery": { "discoveryUrl": "https://<your-idp>/.well-known/openid-configuration" },
        "clientId": "<CLIENT_ID>",
        "clientSecret": "<CLIENT_SECRET>",
        "clientAuthenticationMethod": "CLIENT_SECRET_BASIC",
        "onBehalfOfTokenExchangeConfig": {
          "grantType": "TOKEN_EXCHANGE",
          "tokenExchangeGrantTypeConfig": { "actorTokenContent": "M2M", "actorTokenScopes": ["<scope>"] }
        }
      }
    }
  }'
```
</details>

## Step 2 — Secure the harness inbound with the Entra user app

Set the harness inbound authorizer to the Entra **user** app (the client end users log in
with), so the harness receives a valid Entra user JWT:

```json
"authorizerConfiguration": {
  "customJWTAuthorizer": {
    "discoveryUrl": "https://login.microsoftonline.com/<TENANT_ID>/v2.0/.well-known/openid-configuration",
    "allowedClients": ["<ENTRA_USER_APP_CLIENT_ID>"]
  }
}
```

## Step 3 — Wire OBO to the downstream call

:::alert — UNVERIFIED SEAM (the key thing to get feedback on)
There are two candidate mechanisms, and **which one the declarative harness supports is
the open question for the dry-run**:

**(3a) Declarative — gateway tool `outboundAuth.oauth` references the OBO provider.**
Mirrors the M2M sample, but pointing at the OBO-configured provider so the inbound user
token drives an on-behalf-of exchange instead of client-credentials:

```jsonc
"tools": [{
  "type": "agentcore_gateway",
  "name": "my-gateway",
  "config": { "agentCoreGateway": {
    "gatewayArn": "<GATEWAY_ARN>",
    "outboundAuth": { "oauth": {
      "providerArn": "<portfolio-obo-entra ARN>",
      "scopes": ["api://<DOWNSTREAM_API>/Portfolio.Read"],
      "grantType": "ON_BEHALF_OF"        // <-- NOT shown in samples; verify the exact value/shape
    }}
  }}
}]
```
Official samples only show `grantType: CLIENT_CREDENTIALS` here, so the `ON_BEHALF_OF`
variant on a harness gateway tool is **unconfirmed**.

**(3b) Runtime API path — code calls `GetResourceOauth2Token`.** This is the path the OBO
doc actually demonstrates, but it's a *code* call (custom-code runtime, a Lambda
interceptor, or an MCP tool), not declarative harness config:

```bash
# harness already delivered the inbound user token; bind it to the workload
aws bedrock-agentcore get-workload-access-token-for-jwt \
  --workload-name PortfolioAdvisor --user-token "<inbound-entra-user-jwt>"
# -> { "workloadAccessToken": "<wat>" }

aws bedrock-agentcore get-resource-oauth2-token \
  --resource-credential-provider-name portfolio-obo-entra \
  --oauth2-flow ON_BEHALF_OF_TOKEN_EXCHANGE \
  --scopes "api://<DOWNSTREAM_API>/Portfolio.Read" \
  --workload-identity-token "<wat>"
# -> { "accessToken": "<obo-token carrying user + agent identity>" }
```
:::

## Step 4 — Show the payoff

1. Log in as the Entra **test user**, get a user JWT.
2. Invoke the harness with that bearer token.
3. The agent (via OBO) calls the downstream resource with a token that carries the
   **user's** identity. Decode it and show the `sub`/`oid` is the real user, plus the
   agent (actor) identity.
4. Contrast with the live M2M lab, where the downstream principal is the agent's service
   client. **This is the per-user authorization + audit story** the FSI reviewer wanted.

## What to get feedback on

1. **Mechanism (Step 3):** is OBO supported via the harness gateway tool's
   `outboundAuth.oauth` (3a), or must it go through `GetResourceOauth2Token` in code (3b)?
   This determines whether OBO fits the *declarative* harness story or needs a code seam.
2. **IdP choice:** Entra (built-in, least config) vs a custom IdP the team already uses.
3. **Scope of the track:** standalone self-paced lab vs a swap-in for live Lab 2 (the
   latter only if per-user governance must be shown live AND it's dry-run-verified).
4. **Downstream target:** a simple protected API/Graph (clean OBO demo) vs the existing
   Gateway Lambda tools (closer to the workshop, but ties OBO to the gateway seam in #1).

## Verification checklist before this leaves DRAFT

- [ ] Confirm mechanism 3a vs 3b on a deployed harness.
- [ ] Confirm Entra app registrations + delegated permission/consent for the downstream scope.
- [ ] Decode the OBO token; confirm it carries both user and agent identity.
- [ ] If using the Gateway, confirm Cedar can evaluate the end-user principal from the OBO token.
- [ ] Time the added setup vs. the workshop's no-facilitator constraints.
