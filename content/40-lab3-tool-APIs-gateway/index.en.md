---
title: "Lab 3: Plan for tooling and API integration with Gateway"
weight: 42
---

**⏱️ Estimated time: ~30 minutes**

## Build a deliberate tooling strategy
Tools are how your agent accesses the real world. They fetch data from databases, call external APIs, search documentation, and execute business logic. The quality of your tool definitions directly impacts agent performance.

When you define a tool, clarity matters more than brevity. Consider these two descriptions for the same function:

Bad: "Gets revenue data"
Good: "Retrieves quarterly revenue data for a specified region and time period.
Returns values in millions of USD. Requires region code (EMEA, APAC, AMER)
and quarter in YYYY-QN format (e.g., 2024-Q3)."

The first description forces the agent to guess what inputs are valid and how to interpret outputs. The second helps remove ambiguity. When you multiply this across twenty tools, the difference becomes dramatic. Your tooling strategy should address four areas:

1) Error handling and resilience. Tools fail. APIs return errors. Timeouts happen. Define the expected behavior for each failure mode, if the agent should retry, fallback to cached data, or tell the user the service is unavailable. Document this alongside the tool definition.
2) Reuse through Model Context Protocol (MCP). Many service providers already provide MCP servers for tools such as Slack, Google Drive, Salesforce, and GitHub. Use them instead of building custom integrations. For internal APIs, wrap them as MCP tools through AgentCore Gateway. This gives you one protocol across the tools and makes them discoverable by different agents.
3) Centralized tool catalog. Teams shouldn't build the same database connector five times. Maintain an approved catalog of tools that have been reviewed by security and tested in production. When a new team needs a capability, they start by checking the catalog.
4) Code examples with every tool. Documentation alone isn't enough. Show developers how to integrate each tool with working code samples that they can copy and adapt.
The following table shows what effective tool documentation includes:

![tool documenation](/static/40-lab3/lab3_tool-documenation.png)

In Lab 2, we deployed our agent to AgentCore Runtime and personalized it using AgentCore Memory. Now we turn our attention to scaling tool access by exposing our tools through AgentCore Gateway, a managed MCP-compatible proxy that enables multiple agents to discover, authenticate, and invoke tools through a unified endpoint.

We'll migrate from tools defined directly in our agent code to centralized, enterprise-ready tools managed through the Gateway.

:::alert{header="Compliance Disclaimer" type="warning"}
The compliance rules and financial data in this workshop are **simulated for educational purposes only** and do not constitute actual regulatory guidance. Consult your compliance team for real-world implementations.
:::

## Why Use AgentCore Gateway?

Great agents need tools that take full advantage of proprietary and third-party APIs and data. However, building, securing, and scaling agent tools is difficult, becoming a significant blocker for customers moving from prototypes to production.

In most organizations, valuable business logic already exists — as Lambda functions, REST APIs, or internal services — but it wasn't built with AI agents in mind. AgentCore Gateway lets you "MCPify" those existing resources, turning them into tools that any agent can discover and use through the standard MCP protocol, without modifying the original code.

AgentCore Gateway supports a wide range of target types:
- **AWS Lambda functions** — Wrap existing serverless functions as MCP tools
- **Amazon API Gateway REST API stages** — Expose managed REST APIs directly
- **OpenAPI schema targets** — Point at any OpenAPI-described HTTP service
- **Smithy model targets** — Use Smithy service models as tool definitions
- **MCP server targets** — Proxy and secure existing MCP-compatible endpoints
- **Built-in templates from integration providers** — Pre-built connectors for popular third-party services

In this lab, we'll focus on the Lambda target type, but the same Gateway can mix and match all of these behind a single MCP endpoint.

AgentCore Gateway provides:

- **Simplify tool development and integration** — Turn existing Lambda functions, APIs, and services into agent-ready MCP tools without rewriting code
- **Accelerate agent development through unified access** — A single MCP endpoint gives every agent access to all registered tools
- **Scale with confidence through intelligent tool discovery** — Agents automatically discover available tools and their capabilities via the MCP protocol
- **Comprehensive authentication** — JWT-based inbound auth, plus outbound credentials (API keys, OAuth) for upstream services
- **Framework compatibility** — Works with any MCP-compatible agent framework (Strands, LangChain, CrewAI, etc.)
- **Serverless infrastructure** — Fully managed, no servers to provision or scale

## What You'll Build

### Tool Centralization & Reusability
- Take an existing Lambda function (portfolio risk check) — imagine it's owned by the risk management team in your organization — and MCPify it through AgentCore Gateway
- Expose it as an MCP-compatible tool so any agent can discover and call it
- Update the existing agent to access tools via Gateway alongside local tools

### Architecture Change

:::code{language=json showCopyAction=false}
Lab 1-2 (Local tools):
  Agent → [get_stock_analysis(), get_compliance_rules()] (in code)
  Agent → [Exa AI MCP] (direct connection)

Lab 3 (Gateway + Local):
  Agent → Gateway → [Lambda: check_portfolio_risk]
  Agent → [get_stock_analysis(), get_compliance_rules()] (kept local)
  Agent → [Exa AI MCP] (kept as direct MCP client)
:::

![architecture](/static/40-lab3/lab3_architecture_diagram.png)


## Step 1: Verify the AWS Lambda Function

If you still have the dev server running from Lab 2, stop it first.

This lab uses a Lambda function (`workshop-check-portfolio-risk`) that simulates an enterprise portfolio risk assessment API maintained by the risk management team in your organization. This is a common real-world scenario: useful business logic already exists as Lambda functions, but it wasn't designed for AI agents. AgentCore Gateway lets you MCPify these existing functions — making them discoverable and callable by any agent — without touching the original Lambda code.

:::alert{type="info" header="Workshop Studio (AWS event)"}
If you are running this workshop from a **Workshop Studio** account, the Lambda function has already been created for you. Go check it out in the AWS Console:

👉 [Open the workshop-check-portfolio-risk Lambda function](https://console.aws.amazon.com/lambda/home#/functions/workshop-check-portfolio-risk)
:::

:::alert{type="info" header="Self-paced"}
If you are running this workshop **self-paced**, the Lambda function was created when you deployed the CloudFormation stack in the [Prerequisites / Self-paced](../10-intro/12-self-paced/) step.
:::

Take a moment to review the function code in the console. It's a lookup against a portfolio database that returns risk scores, holdings breakdowns, and rebalancing recommendations:

:::code{language=python showCopyAction=false}
import json

PORTFOLIOS = {
    "PORT-001": {
        "name": "Conservative Income", "strategy": "conservative",
        "total_value": 500000, "risk_score": 2.1,
        "holdings": {"UNH": 21, "V": 20, "JPM": 17, "BRK-B": 22, "MSFT": 9, "CASH": 11},
        "diversification_rating": "Excellent",
        "recommendation": "Well-diversified with strong income focus...",
    },
    "PORT-002": { ... },  # Growth Technology — risk_score: 7.8
    "PORT-003": { ... },  # Balanced Moderate — risk_score: 4.5
    "PORT-004": { ... },  # High-Yield Dividend — risk_score: 3.2
    "PORT-005": { ... },  # Speculative Growth — risk_score: 9.1
}

def handler(event, context):
    portfolio_id = event.get("portfolio_id", "").upper()
    if portfolio_id in PORTFOLIOS:
        portfolio = PORTFOLIOS[portfolio_id]
        return {"statusCode": 200, "body": json.dumps({...})}
    return {"statusCode": 404, "body": json.dumps({"error": f"No portfolio found for {portfolio_id}"})}
:::

> **How the Gateway invokes Lambda:** AgentCore Gateway passes tool parameters directly in the Lambda `event` (not inside `event["body"]`). The tool name is available in `context.client_context.custom["bedrockAgentCoreToolName"]` with the format `<TargetName>___<tool_name>`. Since we have a single tool per Lambda, we only need to read the parameters from `event`.

Now retrieve the Lambda ARN from Parameter Store (it was saved there by the prerequisites stack):

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
PORTFOLIO_RISK_LAMBDA_ARN=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn \
  --query 'Parameter.Value' --output text)

echo "Lambda ARN: $PORTFOLIO_RISK_LAMBDA_ARN"
```
:::
:::tab{label="Windows"}
```powershell
$PORTFOLIO_RISK_LAMBDA_ARN = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/portfolio_risk_lambda_arn `
  --query 'Parameter.Value' --output text

Write-Host "Lambda ARN: $PORTFOLIO_RISK_LAMBDA_ARN"

```
:::
::::

## Step 2: Create Tool Schema

For an AI agent to use a tool, it needs to understand what the tool does, what parameters it expects, and what it returns — all described in natural language. This is exactly what the MCP protocol provides: a standard way for tools to advertise their capabilities so agents can reason about when and how to call them.

Lambda functions, however, don't carry that metadata. A Lambda is just code with an input event and an output — there's no built-in way for an agent to know what `workshop-check-portfolio-risk` does or what arguments to pass it.

This is where AgentCore Gateway bridges the gap. It wraps your Lambda (or API, or MCP server) behind an MCP-compatible endpoint, but it still needs you to provide the tool description — the name, a natural-language description, and the input schema. That's what we're creating here.

Create the schema file:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
mkdir -p app/PortfolioAdvisor/tool
touch app/PortfolioAdvisor/tool/__init__.py
touch app/PortfolioAdvisor/tool/portfolio_risk_schema.json
```
:::
:::tab{label="Windows"}
```powershell
mkdir app\PortfolioAdvisor\tool
New-Item app\PortfolioAdvisor\tool\__init__.py -Force
New-Item app\PortfolioAdvisor\tool\portfolio_risk_schema.json -Force

```
:::
::::

Open `app/PortfolioAdvisor/tool/portfolio_risk_schema.json` in Kiro's editor and add the following:

:::code{language=json}
[
  {
    "name": "check_portfolio_risk",
    "description": "Check the risk profile of a portfolio by its portfolio ID (e.g., PORT-001). Returns risk score, holdings breakdown, diversification rating, and rebalancing recommendations.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "portfolio_id": {
          "type": "string",
          "description": "The portfolio ID to check risk for (e.g., PORT-001, PORT-002)"
        }
      },
      "required": ["portfolio_id"]
    }
  }
]
:::

Notice how the `description` fields use natural language — this is what the agent reads to decide whether to call the tool and how to fill in the parameters. Without this, the Gateway would have no way to present the Lambda as a meaningful tool to the agent.

⚠️ **Important:** The `inputSchema` must NOT have a nested `"json"` wrapper. Use `"type": "object"` directly inside `inputSchema`, otherwise the deployment will fail with "Attribute type null is not yet supported".

## Step 3: Add Gateway and Target via CLI

Now we wire it all together. We'll create a Gateway (a managed MCP endpoint) and register the Lambda function as a target. Remember, Lambda is just one of many target types — you could just as easily add an API Gateway REST API stage, an OpenAPI endpoint, a Smithy model, an existing MCP server, or a built-in provider template to the same Gateway.

In Kiro's terminal:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
# Create the gateway linked to the existing PortfolioAdvisor agent
agentcore add gateway --name my-gateway --runtimes PortfolioAdvisor

# Add portfolio risk check Lambda as a target (using the ARN retrieved from Parameter Store in Step 1)
agentcore add gateway-target \
  --type lambda-function-arn \
  --name PortfolioRiskCheck \
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN \
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json \
  --gateway my-gateway
```
:::
:::tab{label="Windows"}
```powershell
# Create the gateway linked to the existing PortfolioAdvisor agent
agentcore add gateway --name my-gateway --runtimes PortfolioAdvisor

# Add portfolio risk check Lambda as a target (using the ARN retrieved from Parameter Store in Step 1)
agentcore add gateway-target `
  --type lambda-function-arn `
  --name PortfolioRiskCheck `
  --lambda-arn $PORTFOLIO_RISK_LAMBDA_ARN `
  --tool-schema-file app/PortfolioAdvisor/tool/portfolio_risk_schema.json `
  --gateway my-gateway

```
:::
::::

You should see:
:::code{language=bash showCopyAction=false}
Added gateway 'my-gateway'
Added gateway target 'PortfolioRiskCheck'
:::

> **Note:** The `--runtimes PortfolioAdvisor` flag tells the CLI to inject the gateway URL as an environment variable (`AGENTCORE_GATEWAY_MY_GATEWAY_URL`) into the PortfolioAdvisor agent runtime after deployment.

## Step 4: Update Your Agent to Use Gateway Tools

Instead of creating a new agent, we'll update the existing PortfolioAdvisor agent to use the gateway tools alongside the local tools — just like the original workshop does.

First, update `app/PortfolioAdvisor/mcp_client/client.py` in Kiro's editor to add the gateway MCP client:

:::alert{header="What this code does" type="info"}
This adds a new `get_gateway_mcp_client()` function alongside the existing Exa AI client. It reads the gateway URL from the `AGENTCORE_GATEWAY_MY_GATEWAY_URL` environment variable (injected by AgentCore Runtime after deployment) and creates an MCP client that connects to your gateway endpoint. If the URL isn't set (e.g., during local dev), it gracefully returns `None`.
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


def get_gateway_mcp_client() -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, if configured"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    return MCPClient(lambda: streamablehttp_client(url))
:::

Then update `app/PortfolioAdvisor/main.py` to import and use the gateway client. The key change is adding `get_gateway_mcp_client` to the MCP clients list:

:::alert{header="What changed from Lab 2" type="info"}
The only changes are importing `get_gateway_mcp_client` and adding it to the `mcp_clients` list. This gives your agent access to the gateway tools (like the portfolio risk check Lambda) alongside the existing Exa AI web search and local tools. The agent automatically discovers all available tools from both MCP clients.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client, get_gateway_mcp_client
from memory.session import get_memory_session_manager
import json

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

You have access to the following local tools:
1. get_stock_analysis() - For stock fundamentals, risk profiles, and analyst ratings
2. get_compliance_rules() - For trading compliance rules, restrictions, and approval requirements

You have access to tools outside of the local tools through MCP, use them as necessary.
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


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    user_id = context.request_headers['x-amzn-bedrock-agentcore-runtime-custom-user-id']

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

The local tools (`get_stock_analysis`, `get_compliance_rules`) remain in the agent code. The gateway tool (`check_portfolio_risk`) is discovered automatically via the MCP client at runtime.

**How it works:** After deployment, the AgentCore Runtime injects `AGENTCORE_GATEWAY_MY_GATEWAY_URL` as an environment variable. The `get_gateway_mcp_client()` function reads this URL and creates an MCP client that connects to the gateway. The gateway routes requests to the Lambda functions.

## Step 5: Deploy

:::code{language=bash}
agentcore deploy -y -v
:::

This deploys everything in one command:
- Gateway + Lambda target
- Updated agent runtime (PortfolioAdvisor) with gateway URL injected
- IAM roles and policies

**Note:** The first gateway deployment takes ~2 minutes.

## Step 6: Test Gateway Tools

Test the portfolio risk check tool with a high-risk portfolio:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_C=$(python3 -c "import uuid; print(uuid.uuid4())")
agentcore invoke "Check the risk profile for portfolio PORT-005" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_C = [guid]::NewGuid().ToString()
agentcore invoke "Check the risk profile for portfolio PORT-005" `
  --session-id $SESSION_C `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream

```
:::
::::

Expected response:
:::code{language=bash showCopyAction=false}
The risk profile for PORT-005 (Speculative Growth) shows:
- Risk Score: 9.1/10 (Very High)
- Strategy: Aggressive
- Total Value: $200,000
- Holdings: TSLA 62%, AMZN 28%, CASH 10%
- Diversification Rating: Very Poor
- Recommendation: CRITICAL — Extreme concentration risk with 62% in TSLA.
  Immediate rebalancing required. Max single-position should not exceed 25%.
:::

Test with a well-diversified portfolio:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore invoke "What's the risk assessment for PORT-001?" \
  --session-id $SESSION_C \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
agentcore invoke "What's the risk assessment for PORT-001?" `
  --session-id $SESSION_C `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream

```
:::
::::

Expected: The agent calls `check_portfolio_risk` via the Gateway and returns that PORT-001 (Conservative Income) has a low risk score of 2.1 with an "Excellent" diversification rating.

## What Just Happened?

### Before (Lab 1-2)
- Tools defined as Python functions in `main.py`
- Only one agent could use them
- No authentication or access control

### After (Lab 3)
- An existing Lambda function (owned by the risk management team) is now MCPified through the Gateway
- Any agent in the project can discover and call it via the Gateway's MCP endpoint
- Gateway handles routing, discovery, and authentication
- The Lambda code was never modified — only a tool schema was added
- The same Gateway could expose API Gateway stages, OpenAPI services, Smithy models, MCP servers, or built-in provider templates

### How the Gateway Works

:::code{language=bash showCopyAction=false}
agentcore invoke "Check risk for PORT-005"
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ↓
Agent reads AGENTCORE_GATEWAY_MY_GATEWAY_URL from env
    ↓
MCP Client connects to Gateway
    ↓
Gateway routes to PortfolioRiskCheck Lambda target
    ↓
Lambda executes and returns result
    ↓
Agent synthesizes response
:::

## Congratulations!

You've MCPified an existing Lambda function and moved from local tools to enterprise-ready, centralized tool management:

- **Existing Lambda** turned into an MCP-compatible tool without code changes
- **Tool schema** bridges the gap between raw Lambda functions and agent-friendly MCP tools
- **Gateway** handles routing, discovery, and authentication
- **Multiple agents** can share the same tools
- **Multiple target types** — Lambda, API Gateway stages, OpenAPI, Smithy, MCP servers, and built-in provider templates behind one endpoint


### What's Next

In Lab 4, you'll explore the production observability and session management capabilities that are already active in your deployed agent.

→ Next: [Lab 4: Production Observability & Session Management](../50-lab4-observability-security/)
