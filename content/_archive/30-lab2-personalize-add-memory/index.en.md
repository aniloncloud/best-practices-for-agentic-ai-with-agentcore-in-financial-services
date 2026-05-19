---
title: "Lab 2: Personalize and add Memory to Your Agent"
weight: 32
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Personalization requires memory that persists across sessions. Users have preferences about how they like information presented. They work on specific projects that provide context for their questions. They use terminology and abbreviations specific to their role. AgentCore Memory provides both short-term memory for conversation history and long-term memory for facts, preferences, and past interactions. Memory is namespaced by user so each person's context remains private. 

Picture this: A valued client contacts your advisory team about their portfolio strategy. They explain their risk tolerance, share their investment preferences, and work with your agent to analyze potential trades. Three weeks later, they contact the firm again with a follow-up question. But now they have to repeat everything — their risk tolerance, their portfolio goals, their preferences — because your agent has no memory of previous interactions.

This is the reality for most AI agents today. Every conversation starts from zero, creating:
- Frustrated clients who must repeat their investment preferences repeatedly
- Inefficient advisory that cannot build on previous interactions
- Lost opportunities to provide personalized, proactive recommendations
- Poor client satisfaction due to impersonal, generic responses

[Amazon Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html) addresses this limitation by providing a managed service that enables AI agents to maintain context over time, remember important facts, and deliver consistent, personalized experiences.

## What We Are Building

### Transform Your Prototype into a Client-Aware Advisor

In this lab, you'll upgrade your Lab 1 prototype to deliver exceptional client experiences through intelligent memory. Your agent will evolve from a forgetful prototype to a client-aware assistant that:

- **"Welcome back, Mr. Chen!"** — Instantly recognizes returning clients
- **"I remember you prefer conservative investments"** — Recalls individual preferences automatically
- **"Following up on your TSLA analysis from last month"** — Connects related conversations seamlessly
- **"Based on your risk tolerance, here's what I recommend"** — Provides personalized suggestions

### How AgentCore Memory Works

AgentCore Memory operates on two levels:

| Strategy | Purpose | What It Does |
|----------|---------|-------------|
| **SEMANTIC** | Facts and context | Captures factual information from conversations (names, preferences, portfolio details) and makes them retrievable across sessions |
| **SUMMARIZATION** | Conversation history | Compressed conversation summaries that provide continuity across sessions |

## Step 1: Add Memory to Your Project

If you still have the dev server running from Lab 1, stop it first by pressing `Esc` in the interactive TUI, or `Ctrl+C` if running in `--logs` mode.

Use the AgentCore CLI to add a memory resource:

:::::tabs{variant="container"}
::::tab{label="AgentCore CLI"}
::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore add memory \
  --name SharedMemory \
  --strategies SEMANTIC,SUMMARIZATION \
  --expiry 30
```
:::
:::tab{label="Windows"}
```powershell
agentcore add memory --name SharedMemory --strategies "SEMANTIC,SUMMARIZATION" --expiry 30

```
:::
::::
::::tab{label="Interactive"}
Run `agentcore` to open the TUI, then select **add** and choose **Memory**:

1. Enter the memory name:

![Enter the memory name in the interactive wizard](/static/30-lab2/lab2_interactive_add_memory.png)

2. Select the event expiry duration:

![Select the event expiry duration](/static/30-lab2/lab2_interactive_memory_name.png)

3. Choose memory strategies for long-term memory extraction:

![Choose memory strategies for long-term memory extraction](/static/30-lab2/lab2_interactive_memory_strategies.png)

4. Review the configuration and press Enter to confirm:

![Review the memory configuration and confirm](/static/30-lab2/lab2_interactive_memory_confirm.png)
::::
:::::

You should see this output message:
:::code{language=bash showCopyAction=false}
Added memory 'SharedMemory'
:::

This updates your `agentcore/agentcore.json` with the memory configuration. You can verify:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cat agentcore/agentcore.json
```
:::
:::tab{label="Windows"}
```powershell
Get-Content agentcore\agentcore.json

```
:::
::::

The `memories` array now contains your memory resource with SEMANTIC and SUMMARIZATION strategies, each with their own namespace patterns.

![agentcore.json showing the memory configuration with SEMANTIC and SUMMARIZATION strategies](/static/30-lab2/lab2_agentcore_memory_config.png)


## Step 2: Integrate Memory into Your Agent Code

The CLI creates the memory resource in the infrastructure, but you need to wire it into your agent code. In Kiro's terminal, create the memory session manager:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
mkdir -p app/PortfolioAdvisor/memory
touch app/PortfolioAdvisor/memory/__init__.py
touch app/PortfolioAdvisor/memory/session.py
```
:::
:::tab{label="Windows"}
```powershell
mkdir app\PortfolioAdvisor\memory
New-Item app\PortfolioAdvisor\memory\__init__.py -Force
New-Item app\PortfolioAdvisor\memory\session.py -Force

```
:::
::::

Open `app/PortfolioAdvisor/memory/session.py` (open the file in Kiro's editor and copy following code):

:::alert{header="What this code does" type="info"}
This module creates a memory session manager that connects your agent to AgentCore Memory. It configures two retrieval namespaces: one for user-specific facts (`/users/{actorId}/facts`) extracted by the SEMANTIC strategy, and one for conversation summaries (`/summaries/{actorId}/{sessionId}`) from the SUMMARIZATION strategy. The `MEMORY_SHAREDMEMORY_ID` environment variable is automatically injected by AgentCore Runtime after deployment.
:::

:::code{language=python}
import os
from typing import Optional
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

MEMORY_ID = os.getenv("MEMORY_SHAREDMEMORY_ID")
REGION = os.getenv("AWS_REGION")

def get_memory_session_manager(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    if not MEMORY_ID:
        return None

    retrieval_config = {
        f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.3),
        f"/summaries/{actor_id}/{session_id}": RetrievalConfig(top_k=3, relevance_score=0.3)
    }

    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        ),
        REGION
    )
:::

**How it works:** The memory ID is injected as an environment variable (`MEMORY_SHAREDMEMORY_ID`) by the AgentCore Runtime after deployment. The session manager handles storing and retrieving memory records automatically.

## Step 3: Update main.py to Use Memory

Open `app/PortfolioAdvisor/main.py` in Kiro's editor. The key changes are:
- Import the memory session manager
- Use a factory pattern to create agents per session/user
- Extract `session_id` and `user_id` from the runtime context

:::alert{header="What changed from Lab 1" type="info"}
The main difference is the agent factory pattern. Instead of a single global agent, we now create one agent per session/user combination, each with its own `session_manager`. This allows the agent to store and retrieve memories scoped to each user. The `invoke` function now extracts `session_id` and `user_id` from the runtime context and passes them to the factory.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client
from memory.session import get_memory_session_manager

app = BedrockAgentCoreApp()
log = app.logger

# Exa AI MCP client for web search
mcp_clients = [get_streamable_http_mcp_client()]

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

The user-id is retrieved from a custom header as shown in the above code. We need to allowlist the custom header in `agentcore.json`.
Add below entry to the runtime config:

:::code{language=json}
"requestHeaderAllowlist": [
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
]
:::

The runtime config in `agentcore.json` should look like:

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
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
        ]
    }
]
:::

This is an important step before moving to the next step to make sure that the AgentCore Runtime understands the custom header once the agent is invoked. Ideally, once security is implemented, the `user-id` or `actor-id` should be retrieved from the authorization claims. We will see that behavior in Lab 5.

## Step 4: Deploy to Enable Memory

Memory is a cloud service — it requires deployment to function.

Since you already deployed your agent in Lab 1, this redeployment will update your existing stack with the new memory resource:

:::code{language=bash}
agentcore deploy -y -v
:::

You should see the memory resource being added to your existing deployment:
:::code{language=bash showCopyAction=false}
✓ Load deployment target
✓ Validate project
✓ Build CDK project
✓ Synthesize CloudFormation
✓ Deploy to AWS
  - AWS::IAM::Role (ExecutionRole)
  - AWS::BedrockAgentCore::Memory (SharedMemory)
  - AWS::BedrockAgentCore::Runtime (PortfolioAdvisor) [updated]
✓ Persist deployment state

✓ Deployed to 'default'
:::

> **Note:** Since your agent is already deployed, this update should be fast (~40 seconds). The CLI detects the existing stack and only applies the changes.

That is it! You just deployed your AgentCore Memory and updated your agent code with the memory integration.

Here is the updated architecture:
![Architecture Diagram](/static/30-lab2/lab2_architecture_diagram.png)


## Step 5: Test Memory — Teach Your Agent About You

Now let's test that memory works across sessions. First, tell the agent something about yourself:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
SESSION_A=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "My name is Alex Chen. I prefer conservative investments with a focus on dividends. My risk tolerance is moderate." \
  --session-id $SESSION_A \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_A = [guid]::NewGuid().ToString()
agentcore invoke "My name is Alex Chen. I prefer conservative investments with a focus on dividends. My risk tolerance is moderate." `
  --session-id $SESSION_A `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream

```
:::
::::

Note that a random `--session_id` in the format of UUID and the custom header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id` which we allowlisted in the previous step, is set to AlexChen in the command. Wait about 1-2 minutes for the memory extraction to process, then start a **completely new session** and ask. Running the same command with a different prompt works as a new random UUID will be created as session_id. However, the user-id in the custom header is still AlexChen:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
sleep 2m
SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Do you know anything about me?" \
  --session-id $SESSION_B \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
Start-Sleep -Seconds 120
$SESSION_B = [guid]::NewGuid().ToString()
agentcore invoke "Do you know anything about me?" `
  --session-id $SESSION_B `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream

```
:::
::::

Expected response:
:::code{language=bash showCopyAction=false}
Yes! I know a few things about you, Mr. Chen:
1. Your name is Alex Chen
2. You prefer conservative investments with a focus on dividends
3. Your risk tolerance is moderate
:::

The agent remembered you across sessions! The SEMANTIC strategy automatically extracted facts from the first conversation and made them available in the second.

## What Just Happened?

When you ran `agentcore add memory`, the CLI:
1. **Updated `agentcore.json`** — Added the memory resource with SEMANTIC and SUMMARIZATION strategies
2. **Configured namespaces** — Set up `/users/{actorId}/facts` for semantic facts and `/summaries/{actorId}/{sessionId}` for conversation summaries

When you integrated memory into the code:
1. **Session manager** — `AgentCoreMemorySessionManager` hooks into the Strands Agent lifecycle
2. **Automatic extraction** — After each conversation, the memory service asynchronously extracts facts and stores them
3. **Automatic retrieval** — Before each response, the memory service retrieves relevant facts and injects them into the agent's context

When you ran `agentcore deploy` the AgentCore CLI updated your existing CloudFormation stack to add the AgentCore Memory resource. It also redeployed your agent code with the memory integration to AgentCore Runtime.


### Memory Strategies in Action

| What happened | Strategy | Result |
|--------------|----------|--------|
| "My name is Alex Chen" | SEMANTIC | Extracted as fact: "The user's name is Alex Chen" |
| "I prefer conservative investments" | SEMANTIC | Extracted as fact: "Alex Chen prefers conservative investments with dividend focus" |
| "My risk tolerance is moderate" | SEMANTIC | Extracted as fact: "Alex Chen has moderate risk tolerance" |
| Full conversation | SUMMARIZATION | Compressed summary stored for session continuity |

> **Important:** Memory extraction is asynchronous. If you test too quickly after the first conversation, the facts may not be available yet. Wait ~1-2 minutes between sessions for all facts to be extracted.

## Congratulations — You've Built a Client-Aware Portfolio Advisor!

Your agent now:
- **Remembers every client interaction** using AgentCore Memory
- **Extracts client preferences** automatically via SEMANTIC strategy
- **Maintains context across sessions** — no more "goldfish agent"
- **Personalizes responses** based on investment preferences and risk tolerance

### What's Next

In Lab 3, you'll move from local tools to enterprise-ready services using AgentCore Gateway — centralizing tool management and adding authentication.

→ Next: [Lab 3: Scaling Tools with Gateway](../40-lab3-tool-APIs-gateway/)
