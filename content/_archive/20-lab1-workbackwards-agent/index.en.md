---
title: "Lab 1: Work backwards from the problem and build your first Prototype"
weight: 22
---

**⏱️ Estimated time: ~20 minutes**

## Start small and define success clearly
The first question you need to answer isn't "what can this agent do?" but rather "what problem are we solving?" Too many teams start by building an agent that tries to handle every possible scenario. This leads to complexity, slow iteration cycles, and agents that don't excel at anything.

Instead, work backwards from a specific use case. If you're building a financial assistant, start with the three most common analyst tasks. If you're building an HR helper, focus on the top five employee questions. Get those working reliably before expanding scope.

Your initial planning should produce four concrete deliverables:

 Clear definition of what the agent should and should not do. Write this down. Share it with stakeholders. Use it to say no to feature creep.
The agent's tone and personality. Decide if it will be formal or conversation, how it will greet users, and what will happen when it encounters questions outside its scope.
Unambiguous definitions for every tool, parameter, and knowledge source. Vague descriptions cause the agent to make incorrect choices.
A ground truth dataset of expected interactions covering both common queries and edge cases.

![Agent Definition](/static/20-lab1/lab1_agentdefinition.png)

In this lab, you'll build a **portfolio advisor agent prototype** for a capital markets firm. The agent will handle common analyst and client inquiries using three specialized tools:

1. **`get_stock_analysis()`** — Look up stock analysis data (price, PE ratio, analyst rating, risk level)
2. **`get_compliance_rules()`** — Retrieve compliance rules for different trade types
3. **`Exa MCP Tools`** — Search the web for market news and research

:::alert{header="Compliance Disclaimer" type="warning"}
The compliance rules and financial data in this workshop are **simulated for educational purposes only** and do not constitute actual regulatory guidance. Consult your compliance team for real-world implementations.
:::

The architecture will look as following:
![architecture diagram](/static/20-lab1/lab1_architecture_diagram.png)

You'll use the AgentCore CLI to scaffold the project, then customize the agent with these tools. By the end, you'll have a working agent that can:
- Analyze stock fundamentals and risk profiles
- Look up compliance rules for different trade types
- Search the web for market news and research
- Combine tool results with its knowledge to provide informed recommendations

### What happens when you ask the agent a question?

When an analyst asks something like *"What's the risk profile for TSLA?"*, the agent:

1. **Query analysis** — Analyzes the analyst's question
2. **Tool selection** — Determines which tool(s) to use (`get_stock_analysis`)
3. **Tool execution** — Calls the tool with the correct parameters
4. **Response synthesis** — Combines tool results with its knowledge
5. **Quality check** — Ensures the response follows the system prompt guidelines

## Step 1: Create the Project

Open Kiro IDE and make sure you have the integrated terminal open (`` Cmd+` `` on macOS or `` Ctrl+` `` on Windows/Linux). All commands in this lab should be run in Kiro's terminal.

Run the `agentcore create` command to scaffold a new project:

:::::tabs{variant="container"}
::::tab{label="AgentCore CLI"}
Use the `--defaults` flag to generate a Python agent using the Strands Agents SDK with Amazon Bedrock as the model provider:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
agentcore create \
  --name PortfolioAdvisor \
  --framework Strands \
  --model-provider Bedrock \
  --defaults
```
:::
:::tab{label="Windows"}
```powershell
agentcore create `
  --name PortfolioAdvisor `
  --framework Strands `
  --model-provider Bedrock `
  --defaults

```
:::
::::
::::tab{label="Interactive"}
Run `agentcore create` without flags to launch the interactive wizard:

:::code{language=bash}
agentcore create
:::

The interactive mode lets you choose from the following options:

- **Framework** — Strands Agents, LangChain/LangGraph, CrewAI, Google Agent Development Kit (ADK), or OpenAI Agents SDK
- **Model provider** — Amazon Bedrock, Anthropic, OpenAI, or Gemini
- **Memory** — None, short-term only, or long-term and short-term
- **Build type** — CodeZip (default) or Container

1. Enter `PortfolioAdvisor` as your project name:

![Enter your project name in the interactive wizard](/static/20-lab1/lab1_interactive_project_name.png)

:::alert{header="Make sure to use `PortfolioAdvisor` as your project name" type="info"}
Future parts of this workshop depend on having the correct project name. Make sure to use `PortfolioAdvisor` to avoid discrepancies throughout the workshop.

2. Choose your agent framework and model provider:

![Choose your agent framework from the available options](/static/20-lab1/lab1_interactive_framework.png)

3. Review your configuration and confirm:

![Review the configuration summary and confirm to create the project](/static/20-lab1/lab1_interactive_confirm.png)
::::
:::::

You should see:

:::code{language=bash showCopyAction=false}
[done]  Create PortfolioAdvisor/ project directory
[done]  Prepare agentcore/ directory
[done]  Initialize git repository
[done]  Add agent to project
[done]  Set up Python environment

Created:
  PortfolioAdvisor/
    app/PortfolioAdvisor/  Python agent (Strands)
    agentcore/             Config and CDK project

Project created successfully!
:::

### Open the project in Kiro

If the project didn't open automatically, you can open it manually:

1. Click **Open a project** on the Kiro Getting Started page:

![Click Open a project on the Getting Started page](/static/20-lab1/lab1_open_project.png)

2. Navigate to the `PortfolioAdvisor` folder you just created and click **Open**.

3. You should now see the full project structure in Kiro's sidebar:

![Project opened in Kiro with file explorer showing the agent structure](/static/20-lab1/lab1_project_opened.png)

Navigate into the project in the terminal:

:::code{language=bash}
cd PortfolioAdvisor
:::

## Step 2: Explore the Project Structure

Take a moment to understand what was generated:

:::code{language=bash showCopyAction=false}
PortfolioAdvisor/
├── AGENTS.md                          # AI assistant context file
├── README.md
├── agentcore/
│   ├── agentcore.json                 # Main project config
│   ├── aws-targets.json               # Deployment targets
│   ├── .env.local                     # API keys (gitignored)
│   ├── .cli/deployed-state.json       # Deployment state (auto-managed)
│   ├── .llm-context/                  # TypeScript type definitions
│   └── cdk/                           # CDK infrastructure
└── app/
    └── PortfolioAdvisor/
        ├── main.py                    # Agent entry point
        ├── model/load.py              # Model configuration
        ├── mcp_client/client.py       # MCP client (Exa AI web search)
        └── pyproject.toml             # Python dependencies
:::

Key files to look at:

**`app/PortfolioAdvisor/main.py`** — The agent entry point. It creates a Strands Agent with:
- A system prompt ("You are a helpful assistant")
- A sample `add_numbers` tool
- An MCP client connected to Exa AI for web search

**`app/PortfolioAdvisor/model/load.py`** — Model configuration. By default, it uses Claude Sonnet 4.5 via Amazon Bedrock.

**`agentcore/agentcore.json`** — The project configuration that defines agents, memories, credentials, and other resources.

### Understanding the `agentcore/` subdirectories

**`agentcore/.llm-context/`** — Contains read-only TypeScript type definitions (`agentcore.ts`, `aws-targets.ts`) that mirror the JSON config files. These files exist so that AI coding assistants (like Kiro) can understand the schema, validation rules, and constraints of your project configuration. You should never edit these files — they are auto-generated by the CLI.

**`agentcore/.cli/`** — Internal CLI state directory:
- `deployed-state.json` — Tracks what resources have been deployed and their ARNs. The CLI uses this to map local config to deployed AWS resources (e.g., runtime IDs, memory IDs, gateway URLs). Starts empty (`{"targets": {}}`) and gets populated after `agentcore deploy`.
- `logs/` — Local dev server logs from `agentcore dev` sessions.

**`agentcore/cdk/`** — A full [AWS CDK](https://aws.amazon.com/cdk/) project (TypeScript) that the CLI uses to deploy your infrastructure. When you run `agentcore deploy`, the CLI synthesizes CloudFormation templates from this CDK code and deploys them. It uses the `@aws/agentcore-cdk` L3 constructs to create AgentCore resources (runtimes, memories, gateways). You don't need to edit this unless you want to customize the infrastructure beyond what the CLI provides.

## Step 3: Customize the Agent with Portfolio Advisor Tools

The generated project comes with a sample `add_numbers` tool and an Exa AI MCP client. Let's replace the sample tool with our portfolio advisor tools.

Open `app/PortfolioAdvisor/main.py` in Kiro's editor. In the sidebar, expand `app` → `PortfolioAdvisor` and click `main.py`:

![Navigate to app/PortfolioAdvisor/main.py in the sidebar](/static/20-lab1/lab1_main_py_location.png)

Replace the entire contents of `main.py` with the following:

:::alert{header="What this code does" type="info"}
Want to understand what this code does? Ask Kiro's AI chat! Open the AI chat panel by clicking the chat icon in the left sidebar or pressing `Option+Command+B` (macOS) / `Ctrl+Alt+B` (Windows/Linux). You can ask Kiro about specific files or just paste your code in the Kiro's AI chat terminal!

![AI Mode](/static/20-lab1/OpenAIMode.png)

This is a great habit to build throughout the workshop. Whenever you encounter code you'd like to understand better, Kiro's AI chat can break it down for you, explain individual functions, or clarify how pieces fit together. Think of it as a knowledgeable pair programmer sitting right next to you.
:::

:::code{language=python}
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

# Exa AI MCP client for web search
mcp_clients = [get_streamable_http_mcp_client()]

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

def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt="""You are a knowledgeable and professional portfolio advisor assistant for a capital markets firm.
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

Always use the appropriate tool to get accurate, up-to-date information rather than guessing.""",
            tools=tools
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")
    agent = get_or_create_agent()
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
:::

## Step 4: Start the Local Dev Server

Back in Kiro's terminal, launch the agent locally:

:::::tabs{variant="container"}
::::tab{label="AgentCore CLI"}
Start the local development server directly:

:::code{language=bash}
agentcore dev
:::

The CLI starts a local development server with an interactive chat interface:

![AgentCore dev server running with interactive chat](/static/20-lab1/lab1_image1.png)
::::
::::tab{label="Interactive"}
Run `agentcore` to open the TUI home screen, then select **dev** to start the local development server with an inline chat prompt:

:::code{language=bash}
agentcore
:::

![AgentCore interactive dev server with inline chat](/static/20-lab1/lab1_interactive_dev_server.png)
::::
:::::

## Step 5: Test Your Agent

In the interactive prompt, try these queries:

**Test the stock analysis tool:**
:::code{language=bash}
What's the analysis for AAPL?
:::

Expected: The agent calls `get_stock_analysis("AAPL")` and returns Apple's price, PE ratio, analyst rating, and risk level.

**Test the compliance rules tool:**
:::code{language=bash}
What are the compliance rules for options trading?
:::

Expected: The agent calls `get_compliance_rules("options")` and returns order limits, restrictions, required approvals, and settlement info.

**Test the web search:**
:::code{language=bash}
Search for recent Federal Reserve interest rate decisions
:::

Expected: The agent uses the Exa AI MCP server to search the web and return relevant market news.

**Test a multi-tool query:**
:::code{language=bash}
I want to buy 200 shares of TSLA. What's the current risk profile and what compliance rules apply for equity trades?
:::

Expected: The agent calls both `get_stock_analysis("TSLA")` to get the risk profile and `get_compliance_rules("equity")` to provide the applicable trading rules.

Press `Esc` to exit the dev server when done.

## Step 6: Test with CLI Invocations (Non-Interactive)

You can also invoke the agent from the command line without the interactive TUI. In Kiro, you can split the terminal to run both commands side by side — click the split terminal icon (⊞) in the terminal panel, or use `` Cmd+\ `` (macOS) / `` Ctrl+\ `` (Windows/Linux).

In the first terminal, start the dev server in non-interactive mode:

:::code{language=bash}
agentcore dev --logs
:::

You should see the server start up and begin watching for changes:

![Dev server running in logs mode](/static/20-lab1/lab1_dev_logs.png)

Then, in the second terminal, invoke the agent:

:::code{language=bash}
agentcore dev "What can you do?" --stream
:::

The agent responds with a summary of its capabilities, streamed directly to the terminal:

![Agent response streamed to the terminal via CLI invocation](/static/20-lab1/lab1_cli_invoke.png)

This is useful for scripting and CI/CD pipelines.


## Step 7: Deploy agent to the AWS

Local development with `agentcore dev` is great for iterating quickly — you get hot reload, instant feedback, and a tight development loop. But at some point, you want your agent running in the cloud: scalable, always-on, and ready for real users.

The good news? The AgentCore CLI makes this a one-liner. All the infrastructure setup — code packaging, IAM roles, runtime configuration — is handled for you behind the scenes.

:::code{language=bash showCopyAction=true}
agentcore deploy
:::

You can then check the status of your deployment

:::code{language=bash showCopyAction=true}
agentcore status
:::

And invoke your deployed agent

:::code{language=bash showCopyAction=true}
agentcore invoke "What can you do?"
:::

The now your architecture looks as following:
![Updated Architecture Diagram](/static/20-lab1/lab1_updated_architecture_diagram.png)


## What Just Happened?

When you ran `agentcore create`, the CLI:

1. **Scaffolded the project** — Created the directory structure with `agentcore/` (config + CDK) and `app/` (agent code)
2. **Generated agent code** — Created `main.py` with a Strands Agent, sample tools, and an MCP client
3. **Set up Python environment** — Created a virtual environment and installed dependencies via `uv`
4. **Initialized git** — Set up a git repository with appropriate `.gitignore` files

When you customized `main.py`, you:

1. **Replaced the sample tool** with domain-specific tools (`get_stock_analysis`, `get_compliance_rules`)
2. **Kept the MCP client** (Exa AI) as the web search capability
3. **Added a portfolio advisor system prompt** to guide the agent's behavior

When you ran `agentcore dev`, the CLI:

1. **Created `.venv`** if it didn't exist
2. **Ran `uv sync`** to install dependencies from `pyproject.toml`
3. **Started uvicorn** with your agent on port 8080
4. **Enabled hot reload** — any code changes are picked up automatically

When you ran `agentcore deploy`, the CLI:

1. **Packaged your agent** — Bundled your code and dependencies into a deployable artifact
2. **Provisioned infrastructure** — Created the necessary IAM roles and runtime environment via CDK
3. **Deployed to AgentCore Runtime** — Pushed your agent to a fully managed, scalable endpoint in the cloud

## Congratulations!

You've created the foundation of a portfolio advisor agent! In the next labs, you'll add:
- **Lab 2:** Persistent memory for client personalization
- **Lab 3:** Gateway for centralized, secure tool management
- **Lab 4:** Production observability and session management
- **Lab 5:** JWT authentication for runtime and gateway
- **Lab 6:** Continuous quality evaluation
- **Lab 7:** Client-facing portal interface
- **Lab 8:** Governance policies for trade execution
- **Lab 9:** VPC integration for FSI compliance
- **Lab 10:** Cost optimization and session lifecycle

→ Next: [Lab 2: Add Memory to Your Agent](../30-lab2-personalize-add-memory/)
