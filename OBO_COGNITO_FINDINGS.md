# OBO (on-behalf-of) with Cognito — feasibility findings

**Date:** 2026-06-11 · **For:** team review · **TL;DR: OBO cannot be demonstrated with Amazon Cognito. The blocker is Cognito, not AgentCore or the harness.**

## Why

AgentCore on-behalf-of token exchange requires the downstream IdP's authorization
server to support one of two grants ([OBO doc](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html)):

- `TOKEN_EXCHANGE` → RFC 8693, `urn:ietf:params:oauth:grant-type:token-exchange`
- `JWT_AUTHORIZATION_GRANT` → RFC 7523 §2.1, jwt-bearer

AgentCore Identity brokers that token-exchange request to the credential provider's
token endpoint. **Amazon Cognito's token endpoint supports only `authorization_code`,
`client_credentials`, and `refresh_token`** ([Cognito token endpoint doc](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html)) —
neither token-exchange nor jwt-bearer. So an OBO provider pointed at Cognito would get
`unsupported_grant_type`. This is why every OBO example in the AWS doc uses a generic
custom IdP (`my.idp.com`) or **Microsoft Entra** — never Cognito.

## What DOES work

The harness/AgentCore mechanics are fully capable and are NOT the problem:
- The harness delivers the inbound user token to the agent.
- `GetWorkloadAccessTokenForJWT` binds the inbound user token + agent identity.
- `GetResourceOauth2Token(oauth2Flow=ON_BEHALF_OF_TOKEN_EXCHANGE)` performs the exchange.

The only missing piece for our workshop is an **OBO-capable IdP**.

## Options

| Option | OBO demoable? | Cost | Note |
|---|---|---|---|
| **A. Keep M2M live, document OBO** (recommended for Summit) | conceptual only | none | Validated; what the labs ship today |
| **B. OBO track on Microsoft Entra** | ✅ yes | adds a 2nd IdP | Built-in `MicrosoftOauth2` OBO support — least config |
| **C. OBO track on custom IdP** (Auth0/Okta/Keycloak/PingOne) | ✅ yes | adds a 2nd IdP + setup | `CustomOauth2` + `onBehalfOfTokenExchangeConfig` |
| **D. Header/metadata propagation of user identity** | ❌ not OBO | low | Per-user *audit* only — no scoped downstream token, no IdP-enforced delegation |

## Recommendation

- **Summit live path:** Option A (M2M live, OBO documented).
- **Parallel track for review:** Option B (Entra) — see `OBO_PARALLEL_TRACK_ENTRA.md`.
  Cognito is out for OBO; Entra is the lowest-config way to actually show it.

## Open seam to verify in a dry-run

On the **declarative harness**, the only outbound auth shown in official samples is
`grantType: CLIENT_CREDENTIALS` on a gateway tool. Whether a harness gateway tool's
`outboundAuth.oauth` can reference an OBO-configured provider (and auto-run the
ON_BEHALF_OF exchange using the inbound user token), vs. requiring the runtime
`GetResourceOauth2Token` API path (a code call, not declarative), is **not yet shown in
samples**. The Entra draft flags this explicitly.
