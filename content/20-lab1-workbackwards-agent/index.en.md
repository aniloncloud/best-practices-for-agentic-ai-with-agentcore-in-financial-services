---
title: "Lab 1: Work backwards from the problem and build your first Prototype"
weight: 22
---

**⏱️ Estimated time: ~20 minutes**

## Start small and define success clearly
The first question you need to answer isn’t “what can this agent do?” but rather “what problem are we solving?” Too many teams start by building an agent that tries to handle every possible scenario. This leads to complexity, slow iteration cycles, and agents that don’t excel at anything.

Instead, work backwards from a specific use case. If you’re building a financial assistant, start with the three most common analyst tasks. If you’re building an HR helper, focus on the top five employee questions. Get those working reliably before expanding scope.

Your initial planning should produce four concrete deliverables:

 Clear definition of what the agent should and should not do. Write this down. Share it with stakeholders. Use it to say no to feature creep.
The agent’s tone and personality. Decide if it will be formal or conversation, how it will greet users, and what will happen when it encounters questions outside its scope.
Unambiguous definitions for every tool, parameter, and knowledge source. Vague descriptions cause the agent to make incorrect choices.
A ground truth dataset of expected interactions covering both common queries and edge cases.

![Agent Definition](/static/20-lab1/lab1_agentdefinition.png)

### EDITOR's NOTE MODIFY The section below with new Capital Market use case agent

In this lab, you'll build a customer support agent prototype for an e-commerce company. The agent will be able to handle common customer inquiries using three specialized tools:

1. **`get_return_policy()`** — Look up return policies for different product categories
2. **`get_product_info()`** — Search product information and specifications
3. **`Exa MCP Tools`** — Search the web for troubleshooting help

The architecture will look as following:
![architecture diagram](/static/20-lab1/lab1_architecture_diagram.png)

You'll use the AgentCore CLI to scaffold the project, then customize the agent with these tools. By the end, you'll have a working agent that can:
- Answer questions about return policies
- Look up product details
- Search the web for troubleshooting information
- Combine tool results with its knowledge to provide helpful responses

### What happens when you ask the agent a question?

When a customer asks something like *"What's the return policy for my headphones?"*, the agent:

1. **Query analysis** — Analyzes the customer's question
2. **Tool selection** — Determines which tool(s) to use (`get_return_policy`)
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
  --name CustomerSupport \
  --framework Strands \
  --model-provider Bedrock \
  --defaults
```
:::
:::tab{label="Windows"}
```powershell
agentcore create `
  --name CustomerSupport `
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

1. Enter `CustomerSupport` as your project name:

![Enter your project name in the interactive wizard](/static/20-lab1/lab1_interactive_project_name.png)

:::alert{header="Make sure to use `CustomerSupport` as your project name" type="info"}
Future parts of this workshop depend on having the correct project name. Make sure to use `CustomerSupport` to avoid discrepancies throughout the workshop.

2. Choose your agent framework and model provider:

![Choose your agent framework from the available options](/static/20-lab1/lab1_interactive_framework.png)

3. Review your configuration and confirm:

![Review the configuration summary and confirm to create the project](/static/20-lab1/lab1_interactive_confirm.png)
::::
:::::

You should see:

:::code{language=bash showCopyAction=false}
[done]  Create CustomerSupport/ project directory
[done]  Prepare agentcore/ directory
[done]  Initialize git repository
[done]  Add agent to project
[done]  Set up Python environment

Created:
  CustomerSupport/
    app/CustomerSupport/  Python agent (Strands)
    agentcore/            Config and CDK project

Project created successfully!
:::

### Open the project in Kiro

If the project didn't open automatically, you can open it manually:

1. Click **Open a project** on the Kiro Getting Started page:

![Click Open a project on the Getting Started page](/static/20-lab1/lab1_open_project.png)

2. Navigate to the `CustomerSupport` folder you just created and click **Open**.

3. You should now see the full project structure in Kiro's sidebar:

![Project opened in Kiro with file explorer showing the agent structure](/static/20-lab1/lab1_project_opened.png)

Navigate into the project in the terminal:

:::code{language=bash}
cd CustomerSupport
:::

## Step 2: Explore the Project Structure

Take a moment to understand what was generated:

:::code{language=bash showCopyAction=false}
CustomerSupport/
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
    └── CustomerSupport/
        ├── main.py                    # Agent entry point
        ├── model/load.py              # Model configuration
        ├── mcp_client/client.py       # MCP client (Exa AI web search)
        └── pyproject.toml             # Python dependencies
:::

Key files to look at:

**`app/CustomerSupport/main.py`** — The agent entry point. It creates a Strands Agent with:
- A system prompt ("You are a helpful assistant")
- A sample `add_numbers` tool
- An MCP client connected to Exa AI for web search

**`app/CustomerSupport/model/load.py`** — Model configuration. By default, it uses Claude Sonnet 4.5 via Amazon Bedrock.

**`agentcore/agentcore.json`** — The project configuration that defines agents, memories, credentials, and other resources.

### Understanding the `agentcore/` subdirectories

**`agentcore/.llm-context/`** — Contains read-only TypeScript type definitions (`agentcore.ts`, `aws-targets.ts`) that mirror the JSON config files. These files exist so that AI coding assistants (like Kiro) can understand the schema, validation rules, and constraints of your project configuration. You should never edit these files — they are auto-generated by the CLI.

**`agentcore/.cli/`** — Internal CLI state directory:
- `deployed-state.json` — Tracks what resources have been deployed and their ARNs. The CLI uses this to map local config to deployed AWS resources (e.g., runtime IDs, memory IDs, gateway URLs). Starts empty (`{"targets": {}}`) and gets populated after `agentcore deploy`.
- `logs/` — Local dev server logs from `agentcore dev` sessions.

**`agentcore/cdk/`** — A full [AWS CDK](https://aws.amazon.com/cdk/) project (TypeScript) that the CLI uses to deploy your infrastructure. When you run `agentcore deploy`, the CLI synthesizes CloudFormation templates from this CDK code and deploys them. It uses the `@aws/agentcore-cdk` L3 constructs to create AgentCore resources (runtimes, memories, gateways). You don't need to edit this unless you want to customize the infrastructure beyond what the CLI provides.

## Step 3: Customize the Agent with Customer Support Tools

The generated project comes with a sample `add_numbers` tool and an Exa AI MCP client. Let's replace the sample tool with our customer support tools.

Open `app/CustomerSupport/main.py` in Kiro's editor. In the sidebar, expand `app` → `CustomerSupport` and click `main.py`:

![Navigate to app/CustomerSupport/main.py in the sidebar](/static/20-lab1/lab1_main_py_location.png)

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

# --- Customer Support Tools ---

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life", "warranty_months": 12},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery", "warranty_months": 24},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup", "warranty_months": 6},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet", "warranty_months": 12},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches", "warranty_months": 24},
}

@tool
def get_return_policy(product_category: str) -> str:
    """Get return policy information for a specific product category.

    Args:
        product_category: Product category (e.g., 'electronics', 'accessories', 'audio')

    Returns:
        Formatted return policy details including timeframes and conditions
    """
    category = product_category.lower()
    if category in RETURN_POLICIES:
        policy = RETURN_POLICIES[category]
        return f"Return policy for {category}: Window: {policy['window']}, Condition: {policy['condition']}, Refund: {policy['refund']}"
    return f"No specific return policy found for '{product_category}'. Please contact support for details."

@tool
def get_product_info(query: str) -> str:
    """Search for product information by name, ID, or keyword.

    Args:
        query: Product name, ID (e.g., 'PROD-001'), or search keyword

    Returns:
        Product details including name, price, category, and description
    """
    query_lower = query.lower()
    # Search by ID
    if query.upper() in PRODUCTS:
        p = PRODUCTS[query.upper()]
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}, Warranty: {p['warranty_months']} months"
    # Search by keyword
    results = [f"{pid}: {p['name']} - ${p['price']} - {p['description']}" for pid, p in PRODUCTS.items()
               if query_lower in p['name'].lower() or query_lower in p['description'].lower() or query_lower in p['category'].lower()]
    if results:
        return "Found products:\n" + "\n".join(results)
    return f"No products found matching '{query}'."

tools = [get_return_policy, get_product_info]

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
            system_prompt="""You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications
3. Web search - To search the web for troubleshooting help

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

**Test the return policy tool:**
:::code{language=bash}
What's the return policy for electronics?
:::

Expected: The agent calls `get_return_policy("electronics")` and returns the 30-day return window with conditions.

**Test the product info tool:**
:::code{language=bash}
Tell me about the Wireless Headphones
:::

Expected: The agent calls `get_product_info("headphones")` and returns product details, price, and warranty info.

**Test the web search:**
:::code{language=bash}
Search for common Bluetooth headphone troubleshooting tips
:::

Expected: The agent uses the Exa AI MCP server to search the web and return relevant troubleshooting information.

**Test a multi-tool query:**
:::code{language=bash}
I bought a Smart Watch (PROD-002) and want to return it. What's the policy?
:::

Expected: The agent calls both `get_product_info("PROD-002")` to identify the category and `get_return_policy("electronics")` to provide the return policy.

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

1. **Replaced the sample tool** with domain-specific tools (`get_return_policy`, `get_product_info`)
2. **Kept the MCP client** (Exa AI) as the web search capability
3. **Added a customer support system prompt** to guide the agent's behavior

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

You've created the foundation of a customer support agent! In the next labs, you'll add:
- **Lab 2:** Persistent memory for personalized conversations
- **Lab 3:** Gateway for centralized, secure tool management
- **Lab 4:** Production observability and session management
- **Lab 5:** Continuous quality evaluation
- **Lab 6:** Customer-facing chat interface

→ Next: [Lab 2: Add Memory to Your Agent](../30-lab2-memory/)
