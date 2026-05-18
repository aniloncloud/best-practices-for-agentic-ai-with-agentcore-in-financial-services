---
title: "Lab 5: Secure with JWT Authentication"
weight: 55
---

**⏱️ Estimated time: ~20 minutes**

## Scale securely with personalization

Moving from a prototype that works for one developer to a production system serving thousands of users introduces new requirements around isolation and security. Security and access control must be enforced before tools execute. Users should only access data they have permission to see.

So far, your agent runtime accepts unauthenticated requests — anyone with the endpoint URL can invoke it. For a production financial services application, this is not acceptable. In this lab, you'll configure JWT-based authentication using Amazon Cognito to secure both your runtime endpoint and your Gateway.

### What You'll Learn

- Configure JWT-based authentication on AgentCore Runtime
- Create a Cognito test user and obtain tokens
- Update agent code to extract user identity from JWT claims
- Secure the AgentCore Gateway with the same JWT authorizer
- Propagate authentication tokens from Runtime to Gateway

:::alert{header="Bedrock Guardrails Note" type="info"}
Bedrock Guardrails cannot currently be attached directly to AgentCore Runtime or Gateway as infrastructure configuration. To apply guardrails, use the `guardrailConfig` parameter in the Bedrock Converse API within your agent code.
:::

## Step 1: Secure Your Runtime with Cognito Authentication

So far, your agent runtime accepts unauthenticated requests — anyone with the endpoint URL can invoke it. For a production application, this is not acceptable. You need to ensure that only authorized clients can call your agent.

AgentCore Runtime supports JWT-based authentication using a custom JWT authorizer. In this step, you'll configure your runtime to require a valid Cognito JWT token on every request, using the Cognito User Pool that was created as part of the workshop prerequisites.

### Retrieve Cognito configuration from Parameter Store

The prerequisites CloudFormation stack stored the Cognito configuration in SSM Parameter Store. Retrieve the values you need:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
COGNITO_DISCOVERY_URL=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/cognito_discovery_url \
  --query 'Parameter.Value' --output text)

COGNITO_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/client_id \
  --query 'Parameter.Value' --output text)

COGNITO_POOL_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/pool_id \
  --query 'Parameter.Value' --output text)

COGNITO_WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)

echo "Discovery URL: $COGNITO_DISCOVERY_URL"
echo "Client ID:     $COGNITO_CLIENT_ID"
echo "Pool ID:       $COGNITO_POOL_ID"
echo "Web Client ID: $COGNITO_WEB_CLIENT_ID"
```
:::
:::tab{label="Windows"}
```powershell
$COGNITO_DISCOVERY_URL = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/cognito_discovery_url `
  --query 'Parameter.Value' --output text

$COGNITO_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/client_id `
  --query 'Parameter.Value' --output text

$COGNITO_POOL_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/pool_id `
  --query 'Parameter.Value' --output text

$COGNITO_WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/web_client_id `
  --query 'Parameter.Value' --output text

Write-Host "Discovery URL: $COGNITO_DISCOVERY_URL"
Write-Host "Client ID:     $COGNITO_CLIENT_ID"
Write-Host "Pool ID:       $COGNITO_POOL_ID"
Write-Host "Web Client ID: $COGNITO_WEB_CLIENT_ID"

```
:::
::::

### Update agentcore.json

Open `agentcore/agentcore.json` in Kiro's editor. 

In the `runtimes` array, find the `"PortfolioAdvisor"` entry and add `Authorization` to the list of `requestHeaderAllowlist`, `authorizerType` and `authorizerConfiguration` fields:

:::code{language=json showCopyAction=false}
"runtimes": [
  {
    "name": "PortfolioAdvisor",
    "build": "CodeZip",
    "entrypoint": "main.py",
    "codeLocation": "app/PortfolioAdvisor/",
    "runtimeVersion": "PYTHON_3_13",
    "networkMode": "PUBLIC",
    "protocol": "HTTP",
    "requestHeaderAllowlist": [
      "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
      "Authorization"
    ],
    "authorizerType": "CUSTOM_JWT",
    "authorizerConfiguration": {
      "customJwtAuthorizer": {
        "discoveryUrl": "<COGNITO_DISCOVERY_URL value>",
        "allowedClients": ["<COGNITO_CLIENT_ID value>", "<COGNITO_WEB_CLIENT_ID value>"]
      }
    }
  }
]
:::

Replace `<COGNITO_DISCOVERY_URL value>`, `<COGNITO_CLIENT_ID value>` and `<COGNITO_WEB_CLIENT_ID value>` with the values you retrieved above. The result should look something like (but with your own values for discoveryUrl and allowedClients):

:::code{language=json showCopyAction=false}
"requestHeaderAllowlist": [
  "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id",
  "Authorization"
],
"authorizerType": "CUSTOM_JWT",
"authorizerConfiguration": {
  "customJwtAuthorizer": {
    "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_aBcDeFgHi/.well-known/openid-configuration",
    "allowedClients": ["1abc2def3ghi4jkl5mno6pqr", "1ej35ccfkb716pc1iiv3421luj"]
  }
}
:::

> **What this does:** The `discoveryUrl` points to the Cognito OIDC discovery endpoint, which tells AgentCore Runtime how to validate incoming JWT tokens (where to fetch the signing keys, the issuer, etc.). The `allowedClients` list restricts access to tokens issued for that specific Cognito app client — any token from a different client will be rejected. The `requestHeaderAllowlist` will be important for the next session, once we add the Cognito authentication to AgentCore Gateway. It is the header that will allow your agent to propagate the authentication token to your MCP client.

### Update agent to take authentication into account
Now that the inbound auth for the agent is set, the agent code needs to get the user_id information, for memory access, from the bearer token upon successful authentication. 

Update `app/PortfolioAdvisor/main.py` to add the `extract_user_id()` method that extracts the username from the claims information. The method is also backward compatible with respect to the previous labs. It falls back to `user-id` in custom header if `Authorization` is not present in header. In production scenarios, this is unlikely to happen:

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import jwt

app = BedrockAgentCoreApp()
log = app.logger

# MCP clients: Exa AI (web search) + AgentCore Gateway (Lambda tools)
mcp_clients = [get_streamable_http_mcp_client(), get_gateway_mcp_client()]

SYSTEM_PROMPT="""You are a knowledgeable and professional portfolio advisor assistant for a capital markets firm.
Your role is to:
- Provide accurate stock analysis and market data using the tools available to you
- Explain compliance rules clearly when asked about trading requirements
- Be professional, precise, and thorough in your analysis
- Always caveat that this is informational only and not personalized investment advice
- If you can't help with something, direct the user to the appropriate compliance or research team

You have access to the following tools:
1. get_stock_analysis() - For stock fundamentals, risk profiles, and analyst ratings
2. get_compliance_rules() - For trading compliance rules, restrictions, and approval requirements
3. Web search - To search the web for market news and research

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Portfolio Advisor Tools ---

STOCKS = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "price": 198.50, "pe_ratio": 32.1, "dividend_yield": 0.55, "analyst_rating": "Buy", "risk_level": "moderate", "market_cap": "3.0T", "description": "Consumer electronics, software, and services company"},
    "MSFT": {"name": "Microsoft Corp.", "sector": "Technology", "price": 425.20, "pe_ratio": 36.8, "dividend_yield": 0.72, "analyst_rating": "Strong Buy", "risk_level": "low", "market_cap": "3.1T", "description": "Cloud computing, productivity software, and AI services"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Financials", "price": 215.30, "pe_ratio": 12.4, "dividend_yield": 2.15, "analyst_rating": "Buy", "risk_level": "moderate", "market_cap": "620B", "description": "Global financial services and investment banking"},
    "GS": {"name": "Goldman Sachs Group Inc.", "sector": "Financials", "price": 485.60, "pe_ratio": 15.2, "dividend_yield": 2.35, "analyst_rating": "Hold", "risk_level": "moderate", "market_cap": "170B", "description": "Investment banking, securities, and asset management"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Technology", "price": 186.40, "pe_ratio": 58.3, "dividend_yield": 0.0, "analyst_rating": "Strong Buy", "risk_level": "moderate", "market_cap": "1.9T", "description": "E-commerce, cloud computing (AWS), and digital streaming"},
    "V": {"name": "Visa Inc.", "sector": "Financials", "price": 289.70, "pe_ratio": 30.5, "dividend_yield": 0.75, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "580B", "description": "Global payments technology and digital transactions"},
    "UNH": {"name": "UnitedHealth Group Inc.", "sector": "Healthcare", "price": 520.80, "pe_ratio": 20.1, "dividend_yield": 1.45, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "480B", "description": "Health insurance and healthcare services"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Discretionary", "price": 248.90, "pe_ratio": 68.5, "dividend_yield": 0.0, "analyst_rating": "Hold", "risk_level": "high", "market_cap": "790B", "description": "Electric vehicles, energy storage, and solar products"},
    "BRK-B": {"name": "Berkshire Hathaway Inc.", "sector": "Financials", "price": 432.10, "pe_ratio": 9.8, "dividend_yield": 0.0, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "950B", "description": "Diversified holding company — insurance, rail, utilities, manufacturing"},
    "GOOG": {"name": "Alphabet Inc.", "sector": "Technology", "price": 172.30, "pe_ratio": 25.6, "dividend_yield": 0.45, "analyst_rating": "Strong Buy", "risk_level": "moderate", "market_cap": "2.1T", "description": "Search, advertising, cloud computing, and AI research"},
}

COMPLIANCE_RULES = {
    "equity": {"description": "Standard equity (stock) trading", "min_order": 1, "max_order": 10000, "settlement": "T+1", "restrictions": "No trading during blackout periods. Insider trading rules apply.", "required_approvals": "None for orders under $100,000. Manager approval for orders $100,000+.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "options": {"description": "Options contracts trading (calls and puts)", "min_order": 1, "max_order": 500, "settlement": "T+1", "restrictions": "Level 2+ options approval required. No naked calls without Level 4 approval.", "required_approvals": "Compliance review for positions exceeding $50,000 notional value.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "margin": {"description": "Margin trading — borrowing funds to purchase securities", "min_order": 1, "max_order": 5000, "settlement": "T+1", "restrictions": "Maintenance margin of 25% required. Margin calls must be met within 3 business days.", "required_approvals": "Margin agreement on file. Compliance review for margin utilization above 70%.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "short-selling": {"description": "Short selling — selling borrowed securities to buy back later", "min_order": 1, "max_order": 2000, "settlement": "T+1", "restrictions": "Locate requirement — shares must be available to borrow before shorting. Uptick rule applies.", "required_approvals": "Short-selling agreement required. Compliance pre-approval for positions above $200,000.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
}

@tool
def get_stock_analysis(ticker: str) -> str:
    """Get stock analysis data including price, fundamentals, and risk profile.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'JPM')

    Returns:
        Formatted stock analysis with price, PE ratio, dividend yield, analyst rating, and risk level
    """
    ticker = ticker.upper()
    if ticker in STOCKS:
        s = STOCKS[ticker]
        return (
            f"{s['name']} ({ticker})\n"
            f"  Sector: {s['sector']} | Market Cap: {s['market_cap']}\n"
            f"  Price: ${s['price']} | P/E Ratio: {s['pe_ratio']}\n"
            f"  Dividend Yield: {s['dividend_yield']}% | Analyst Rating: {s['analyst_rating']}\n"
            f"  Risk Level: {s['risk_level']}\n"
            f"  Description: {s['description']}"
        )
    return f"Unknown ticker symbol '{ticker}'. Available tickers: {', '.join(STOCKS.keys())}"

@tool
def get_compliance_rules(trade_type: str) -> str:
    """Get compliance rules for a specific trade type.

    Args:
        trade_type: Type of trade (e.g., 'equity', 'options', 'margin', 'short-selling')

    Returns:
        Compliance rules including order limits, settlement, restrictions, and required approvals
    """
    trade_type = trade_type.lower()
    if trade_type in COMPLIANCE_RULES:
        r = COMPLIANCE_RULES[trade_type]
        return (
            f"Compliance Rules — {r['description']}\n"
            f"  Order Range: {r['min_order']} - {r['max_order']} shares\n"
            f"  Settlement: {r['settlement']}\n"
            f"  Trading Hours: {r['hours']}\n"
            f"  Restrictions: {r['restrictions']}\n"
            f"  Required Approvals: {r['required_approvals']}"
        )
    return f"Unknown trade type '{trade_type}'. Available types: {', '.join(COMPLIANCE_RULES.keys())}"

tools = [get_stock_analysis, get_compliance_rules]

# Add MCP client (Exa AI web search) to tools
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)

# --- Agent Setup ---

_agent = None

def get_or_create_agent(session_id, user_id):
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            session_manager=get_memory_session_manager(session_id, user_id),
            system_prompt=SYSTEM_PROMPT,
            tools=tools
        )
    return _agent

def extract_user_id(context) -> str | None:
    """Extract user_id from JWT bearer token (username claim) or fall back to custom header."""
    headers = context.request_headers or {}

    # Try Authorization header first (Bearer JWT)
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT for user_id: {e}")
    else:
        log.info(f"No Bearer token found. Auth header present: {auth_header is not None}")

    # Fall back to custom header
    return headers.get("x-amzn-bedrock-agentcore-runtime-custom-user-id")

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    user_id = extract_user_id(context)

    if not session_id or not user_id:
        raise ValueError("session_id and user_id are required. Pass --session-id and --user-id when invoking.")

    agent = get_or_create_agent(session_id, user_id)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()
:::

### Validate and deploy the updated configuration

Before deploying, validate that your `agentcore.json` changes are correct:

:::code{language=bash}
agentcore validate
:::

If validation passes, you'll see a success message. If there are issues (e.g., a missing comma, invalid JSON, or a malformed discovery URL), the CLI will tell you exactly what's wrong so you can fix it before deploying.

:::code{language=bash}
agentcore deploy -y -v
:::

### Test with authentication

After deployment, unauthenticated requests will be rejected. You need to create a Cognito user and obtain a token first.

The prerequisites stack created two Cognito app clients: a machine client (for `client_credentials`) and a web client (for user-based flows). You'll use the web client here to authenticate as a real user.

**Create a test user in the Cognito User Pool:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws cognito-idp admin-create-user \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --temporary-password 'TempPass1!' \
  --user-attributes Name=email,Value=workshopuser@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

# Set a permanent password so the user is confirmed and ready to use
aws cognito-idp admin-set-user-password \
  --user-pool-id $COGNITO_POOL_ID \
  --username workshopuser@example.com \
  --password 'WorkshopPass1!' \
  --permanent

echo "User 'workshopuser@example.com' created and confirmed"
```
:::
:::tab{label="Windows"}
```powershell
aws cognito-idp admin-create-user `
  --user-pool-id $COGNITO_POOL_ID `
  --username workshopuser@example.com `
  --temporary-password "TempPass1!" `
  --user-attributes "Name=email,Value=workshopuser@example.com" "Name=email_verified,Value=true" `
  --message-action SUPPRESS

# Set a permanent password so the user is confirmed and ready to use
aws cognito-idp admin-set-user-password `
  --user-pool-id $COGNITO_POOL_ID `
  --username workshopuser@example.com `
  --password "WorkshopPass1!" `
  --permanent

Write-Host "User 'workshopuser@example.com' created and confirmed"

```
:::
::::

> **Note:** The User Pool is configured with email as the username attribute, so the username must be a valid email address.

**Authenticate as the user and obtain a token:**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

echo "Token obtained successfully"
```
:::
:::tab{label="Windows"}
```powershell
$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

Write-Host "Token obtained successfully"

```
:::
::::

Now invoke the agent with the bearer token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_3=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "What's the analysis for JPM?" \
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_3 = [guid]::NewGuid().ToString()
agentcore invoke "What's the analysis for JPM?" `
  --session-id $SESSION_3 --bearer-token "$TOKEN" --stream

```
:::
::::

Try without the token to confirm it's rejected:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "What's the analysis for JPM?" \
  --session-id $SESSION_3 --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "What's the analysis for JPM?" `
  --session-id $SESSION_3 --stream

```
:::
::::

You should see an authentication error — your runtime is now secured.

## Step 2: Secure Your Gateway with Cognito Authentication

You've secured the runtime endpoint, but the AgentCore Gateway also accepts requests independently. To fully lock down your application, you should apply the same JWT authentication to the Gateway so that only authorized agents (or clients) can invoke the tools behind it.

> **Why secure the Gateway too?** The runtime and the Gateway are separate endpoints. Securing only the runtime means someone with the Gateway URL could still call your tools directly. By applying the same Cognito authorizer to both, you ensure end-to-end authentication — the client authenticates to the runtime, and the runtime's MCP client authenticates to the Gateway using the same token flow.

Gateway authorizer configuration can't be updated in-place, so we need to remove the existing gateway, deploy the removal, and then recreate it with authentication enabled.

### Remove the existing gateway

:::code{language=bash}
agentcore remove gateway --name my-gateway -y
:::


### Recreate the gateway with JWT authentication

Now create a new gateway with the Cognito JWT authorizer configured from the start. We'll use the same SSM parameter values retrieved in Step 1:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway --name my-gateway-secure --runtimes PortfolioAdvisor \
  --authorizer-type CUSTOM_JWT \
  --discovery-url $COGNITO_DISCOVERY_URL \
  --allowed-clients $COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway --name my-gateway-secure --runtimes PortfolioAdvisor `
  --authorizer-type CUSTOM_JWT `
  --discovery-url $COGNITO_DISCOVERY_URL `
  --allowed-clients "$COGNITO_CLIENT_ID,$COGNITO_WEB_CLIENT_ID"

```
:::
::::

### Re-add the portfolio risk check target

The Lambda ARN should still be in your shell from Lab 3. If not, retrieve it again:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
PORTFOLIO_RISK_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn \
  --query 'Parameter.Value' --output text)
```
:::
:::tab{label="Windows"}
```powershell
$PORTFOLIO_RISK_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn `
  --query 'Parameter.Value' --output text

```
:::
::::

Add the target to the new gateway:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name PortfolioRiskCheck \
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json \
  --gateway my-gateway-secure
```
:::
:::tab{label="Windows"}
```powershell
agentcore add gateway-target `
  --type lambda-function-arn `
  --name PortfolioRiskCheck `
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json `
  --gateway my-gateway-secure

```
:::
::::



> **Note:** The new gateway name is `my-gateway-secure`, so the injected environment variable will be `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL`. You also need to configure the Authorization header of your MCPClient. You need to update `app/PortfolioAdvisor/mcp_client/client.py` to read the new variable name and pass the authorization header:

Open `app/PortfolioAdvisor/mcp_client/client.py` and change the environment variable name:

:::alert{header="What changed from Lab 3" type="info"}
Two changes: (1) The gateway URL environment variable changed from `AGENTCORE_GATEWAY_MY_GATEWAY_URL` to `AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL` to match the new secured gateway name. (2) The `get_gateway_mcp_client` function now accepts an `auth_header` parameter and passes it as an `Authorization` header to the gateway, so the JWT token from the runtime is forwarded to authenticate gateway requests.
:::

:::code{language=python}
import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# ExaAI MCP endpoint for web search
EXAMPLE_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client for Exa AI web search"""
    return MCPClient(lambda: streamablehttp_client(EXAMPLE_MCP_ENDPOINT))


def get_gateway_mcp_client(auth_header: str) -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, if configured"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(
        url=url,
        headers={"Authorization": auth_header}
    ))
:::

Since we are using the same Cognito client for AgentCore Runtime and AgentCore Gateway, you will need to update your `app/PortfolioAdvisor/main.py` file to pass the authorization header to your gateway and let's use the Cognito username as the actor id for the agent memory:

:::alert{header="What changed from Lab 3" type="info"}
The `invoke` function now extracts the `Authorization` header from the incoming request context and passes it to `get_gateway_mcp_client`. This propagates the caller's JWT token from the Runtime to the Gateway, enabling end-to-end authentication. The gateway MCP client is now created per-request (inside `invoke`) instead of at startup, since each request may carry a different token.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import jwt

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT="""You are a knowledgeable and professional portfolio advisor assistant for a capital markets firm.
Your role is to:
- Provide accurate stock analysis and market data using the tools available to you
- Explain compliance rules clearly when asked about trading requirements
- Be professional, precise, and thorough in your analysis
- Always caveat that this is informational only and not personalized investment advice
- If you can't help with something, direct the user to the appropriate compliance or research team

You have access to the following tools:
1. get_stock_analysis() - For stock fundamentals, risk profiles, and analyst ratings
2. get_compliance_rules() - For trading compliance rules, restrictions, and approval requirements
3. Web search - To search the web for market news and research

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

# --- Portfolio Advisor Tools ---

STOCKS = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "price": 198.50, "pe_ratio": 32.1, "dividend_yield": 0.55, "analyst_rating": "Buy", "risk_level": "moderate", "market_cap": "3.0T", "description": "Consumer electronics, software, and services company"},
    "MSFT": {"name": "Microsoft Corp.", "sector": "Technology", "price": 425.20, "pe_ratio": 36.8, "dividend_yield": 0.72, "analyst_rating": "Strong Buy", "risk_level": "low", "market_cap": "3.1T", "description": "Cloud computing, productivity software, and AI services"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Financials", "price": 215.30, "pe_ratio": 12.4, "dividend_yield": 2.15, "analyst_rating": "Buy", "risk_level": "moderate", "market_cap": "620B", "description": "Global financial services and investment banking"},
    "GS": {"name": "Goldman Sachs Group Inc.", "sector": "Financials", "price": 485.60, "pe_ratio": 15.2, "dividend_yield": 2.35, "analyst_rating": "Hold", "risk_level": "moderate", "market_cap": "170B", "description": "Investment banking, securities, and asset management"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Technology", "price": 186.40, "pe_ratio": 58.3, "dividend_yield": 0.0, "analyst_rating": "Strong Buy", "risk_level": "moderate", "market_cap": "1.9T", "description": "E-commerce, cloud computing (AWS), and digital streaming"},
    "V": {"name": "Visa Inc.", "sector": "Financials", "price": 289.70, "pe_ratio": 30.5, "dividend_yield": 0.75, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "580B", "description": "Global payments technology and digital transactions"},
    "UNH": {"name": "UnitedHealth Group Inc.", "sector": "Healthcare", "price": 520.80, "pe_ratio": 20.1, "dividend_yield": 1.45, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "480B", "description": "Health insurance and healthcare services"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Discretionary", "price": 248.90, "pe_ratio": 68.5, "dividend_yield": 0.0, "analyst_rating": "Hold", "risk_level": "high", "market_cap": "790B", "description": "Electric vehicles, energy storage, and solar products"},
    "BRK-B": {"name": "Berkshire Hathaway Inc.", "sector": "Financials", "price": 432.10, "pe_ratio": 9.8, "dividend_yield": 0.0, "analyst_rating": "Buy", "risk_level": "low", "market_cap": "950B", "description": "Diversified holding company — insurance, rail, utilities, manufacturing"},
    "GOOG": {"name": "Alphabet Inc.", "sector": "Technology", "price": 172.30, "pe_ratio": 25.6, "dividend_yield": 0.45, "analyst_rating": "Strong Buy", "risk_level": "moderate", "market_cap": "2.1T", "description": "Search, advertising, cloud computing, and AI research"},
}

COMPLIANCE_RULES = {
    "equity": {"description": "Standard equity (stock) trading", "min_order": 1, "max_order": 10000, "settlement": "T+1", "restrictions": "No trading during blackout periods. Insider trading rules apply.", "required_approvals": "None for orders under $100,000. Manager approval for orders $100,000+.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "options": {"description": "Options contracts trading (calls and puts)", "min_order": 1, "max_order": 500, "settlement": "T+1", "restrictions": "Level 2+ options approval required. No naked calls without Level 4 approval.", "required_approvals": "Compliance review for positions exceeding $50,000 notional value.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "margin": {"description": "Margin trading — borrowing funds to purchase securities", "min_order": 1, "max_order": 5000, "settlement": "T+1", "restrictions": "Maintenance margin of 25% required. Margin calls must be met within 3 business days.", "required_approvals": "Margin agreement on file. Compliance review for margin utilization above 70%.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
    "short-selling": {"description": "Short selling — selling borrowed securities to buy back later", "min_order": 1, "max_order": 2000, "settlement": "T+1", "restrictions": "Locate requirement — shares must be available to borrow before shorting. Uptick rule applies.", "required_approvals": "Short-selling agreement required. Compliance pre-approval for positions above $200,000.", "hours": "9:30 AM - 4:00 PM ET (regular session)"},
}

@tool
def get_stock_analysis(ticker: str) -> str:
    """Get stock analysis data including price, fundamentals, and risk profile.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'JPM')

    Returns:
        Formatted stock analysis with price, PE ratio, dividend yield, analyst rating, and risk level
    """
    ticker = ticker.upper()
    if ticker in STOCKS:
        s = STOCKS[ticker]
        return (
            f"{s['name']} ({ticker})\n"
            f"  Sector: {s['sector']} | Market Cap: {s['market_cap']}\n"
            f"  Price: ${s['price']} | P/E Ratio: {s['pe_ratio']}\n"
            f"  Dividend Yield: {s['dividend_yield']}% | Analyst Rating: {s['analyst_rating']}\n"
            f"  Risk Level: {s['risk_level']}\n"
            f"  Description: {s['description']}"
        )
    return f"Unknown ticker symbol '{ticker}'. Available tickers: {', '.join(STOCKS.keys())}"

@tool
def get_compliance_rules(trade_type: str) -> str:
    """Get compliance rules for a specific trade type.

    Args:
        trade_type: Type of trade (e.g., 'equity', 'options', 'margin', 'short-selling')

    Returns:
        Compliance rules including order limits, settlement, restrictions, and required approvals
    """
    trade_type = trade_type.lower()
    if trade_type in COMPLIANCE_RULES:
        r = COMPLIANCE_RULES[trade_type]
        return (
            f"Compliance Rules — {r['description']}\n"
            f"  Order Range: {r['min_order']} - {r['max_order']} shares\n"
            f"  Settlement: {r['settlement']}\n"
            f"  Trading Hours: {r['hours']}\n"
            f"  Restrictions: {r['restrictions']}\n"
            f"  Required Approvals: {r['required_approvals']}"
        )
    return f"Unknown trade type '{trade_type}'. Available types: {', '.join(COMPLIANCE_RULES.keys())}"

# --- Agent Setup ---

_agent = None

def get_or_create_agent(session_id, user_id, auth_header):
    global _agent

    session_manager = get_memory_session_manager(session_id, user_id)

    # MCP clients: Exa AI (web search) + AgentCore Gateway (Lambda tools)
    mcp_clients = [get_streamable_http_mcp_client(), get_gateway_mcp_client(auth_header)]
    tools = [get_stock_analysis, get_compliance_rules]

    # Add MCP client (Exa AI web search) to tools
    for mcp_client in mcp_clients:
        if mcp_client:
            tools.append(mcp_client)

    if _agent is None:
        _agent = Agent(
            model=load_model(),
            session_manager=session_manager,
            system_prompt=SYSTEM_PROMPT,
            tools=tools
        )
    return _agent

def extract_user_id(auth_header) -> str | None:
    """Extract user_id from JWT bearer token (username claim) or fall back to custom header."""

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            claims = jwt.decode(token, options={"verify_signature": False})
            username = claims.get("username")
            if username:
                return username
        except Exception as e:
            log.warning(f"Failed to decode JWT for user_id: {e}")
    else:
        log.info(f"No Bearer token found. Auth header present: {auth_header is not None}")
        raise Exception("No authorization header")

@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    request_headers = context.request_headers or {}

    # Get Client JWT token
    auth_header = request_headers.get('Authorization', '')

    if not auth_header:
        raise Exception("No authorization header")

    user_id = extract_user_id(auth_header)

    if not session_id or not user_id:
        raise ValueError("session_id and user_id are required. Pass --session-id and --user-id when invoking.")

    agent = get_or_create_agent(session_id, user_id, auth_header)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]

if __name__ == "__main__":
    app.run()
:::

### Validate and deploy

:::code{language=bash}
agentcore validate
:::

:::code{language=bash}
agentcore deploy -y -v
:::

### Test the secured Gateway

The portfolio risk check tool goes through the Gateway. If the Gateway auth is working, this should succeed with a valid token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_E=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Check the risk profile for PORT-001" \
  --session-id $SESSION_E --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_E = [guid]::NewGuid().ToString()
agentcore invoke "Check the risk profile for PORT-001" `
  --session-id $SESSION_E --bearer-token "$TOKEN" --stream

```
:::
::::

The agent should return the risk assessment for PORT-001 (Conservative Income, risk score 2.1, Excellent diversification). Both the runtime and the Gateway are now secured with the same Cognito identity provider.

## Step 3: Generate Test Traffic

Let's generate some varied interactions to populate the observability dashboard. Since the runtime is now secured, include the bearer token:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_D=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "What are the compliance rules for options trading?" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Give me the analysis for MSFT" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Check the risk for portfolio PORT-002" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Do you remember my name?" \
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_D = [guid]::NewGuid().ToString()

agentcore invoke "What are the compliance rules for options trading?" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Give me the analysis for MSFT" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Check the risk for portfolio PORT-002" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

agentcore invoke "Do you remember my name?" `
  --session-id $SESSION_D --bearer-token "$TOKEN" --stream

```
:::
::::

After running these, wait a few minutes and check the CloudWatch dashboard to see the traces for each interaction, including which tools were called and how long each step took.

:::alert{type="info" header="Token expired?"}
The Cognito access token is valid for 60 minutes (as configured in the prerequisites stack). If you get an authentication error after some time, just re-run the token command from Step 1:
:::

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)
```
:::
:::tab{label="Windows"}
```powershell
$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id $COGNITO_WEB_CLIENT_ID `
  --auth-parameters "USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1!" `
  --query 'AuthenticationResult.AccessToken' --output text

```
:::
::::

If you've started a new terminal session and lost the environment variables, re-run the full retrieval block from Step 1 ("Retrieve Cognito configuration" and "Test with authentication") to set them again.
:::

## Architecture

After completing this lab, your deployed architecture looks like this:

![Lab 4 Architecture](/static/50-lab4-deploy/lab4_architecture_diagram.png)

:::code{language=bash showCopyAction=false}
Client (with JWT token)
    ↓
Cognito validates token
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch (traces, logs, metrics)
:::

> **Observability still works as before.** Adding JWT authentication doesn't change how traces, logs, and metrics are collected. AgentCore Runtime continues to instrument every invocation with OpenTelemetry automatically — the only difference is that unauthenticated requests are now rejected before they reach your agent code, so you'll only see traces for legitimate, authorized calls.

## What Just Happened?

In this lab you secured your agent end-to-end:

1. **Secured the runtime** — Configured JWT-based authentication with Cognito so only authorized clients can invoke the agent
2. **Updated agent code** — Extracted user identity from JWT claims for memory personalization
3. **Secured the Gateway** — Applied the same Cognito JWT authorizer to the Gateway for end-to-end authentication
4. **Generated test traffic** — Populated the observability dashboard with authenticated interactions

### What the CLI Does Behind the Scenes

When you run `agentcore deploy`, the CLI:

1. **Packages your code** — Zips your agent code with all dependencies from `.venv`
2. **Uploads to S3** — Stores the package in an S3 bucket managed by CDK
3. **Creates/Updates Runtime** — Provisions the AgentCore Runtime with your code, including the JWT authorizer configuration
4. **Creates/Updates Gateway** — Deploys the Gateway with targets and JWT authorizer configuration
5. **Injects environment variables** — Memory IDs, Gateway URLs, and credentials are automatically injected
6. **Enables observability** — OpenTelemetry instrumentation is enabled by default

## Congratulations!

Your agent is now fully secured:

- ✅ **Runtime authentication** — Only authorized JWT tokens can invoke your agent
- ✅ **Gateway authentication** — End-to-end auth from client → runtime → gateway
- ✅ **Token propagation** — JWT flows from runtime to gateway automatically
- ✅ **User identity** — Agent extracts username from JWT for personalized memory

### What's Next

In Lab 6, you'll set up continuous quality monitoring with AgentCore Evaluations to ensure your production agent maintains high performance standards.

→ Next: [Lab 6: Evaluating Agent Quality](../60-lab5-evals/)
