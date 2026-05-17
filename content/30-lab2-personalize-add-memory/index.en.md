---
title: "Lab 2: Personalize and add Memory to Your Agent"
weight: 32
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Personalization requires memory that persists across sessions. Users have preferences about how they like information presented. They work on specific projects that provide context for their questions. They use terminology and abbreviations specific to their role. AgentCore Memory provides both short-term memory for conversation history and long-term memory for facts, preferences, and past interactions. Memory is namespaced by user so each person’s context remains private. 

Picture this: A valued customer contacts your support team about an issue with their recent order. They explain their preferences, share their frustration, and work with your agent to resolve the problem. Three weeks later, they contact support again with a related question. But now they have to repeat everything — their preferences, their history, their context — because your agent has no memory of previous interactions.

This is the reality for most AI agents today. Every conversation starts from zero, creating:
- Frustrated customers who must repeat their information repeatedly
- Inefficient support that cannot build on previous interactions
- Lost opportunities to provide personalized, proactive service
- Poor customer satisfaction due to impersonal, generic responses

[Amazon Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html) addresses this limitation by providing a managed service that enables AI agents to maintain context over time, remember important facts, and deliver consistent, personalized experiences.

## What We Are Building

### Transform Your Prototype into a Customer-Obsessed Agent

In this lab, you'll upgrade your Lab 1 prototype to deliver exceptional customer experiences through intelligent memory. Your agent will evolve from a forgetful prototype to a customer-aware assistant that:

- **"Welcome back, Sarah!"** — Instantly recognizes returning customers
- **"I remember you prefer email updates"** — Recalls individual preferences automatically
- **"Following up on your laptop issue from last month"** — Connects related conversations seamlessly
- **"Based on your purchase history, here's what I recommend"** — Provides personalized suggestions

### How AgentCore Memory Works

AgentCore Memory operates on two levels:

| Strategy | Purpose | What It Does |
|----------|---------|-------------|
| **SEMANTIC** | Facts and context | Captures factual information from conversations (names, preferences, order details) and makes them retrievable across sessions |
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
mkdir -p app/CustomerSupport/memory
touch app/CustomerSupport/memory/__init__.py
touch app/CustomerSupport/memory/session.py
```
:::
:::tab{label="Windows"}
```powershell
mkdir app\CustomerSupport\memory
New-Item app\CustomerSupport\memory\__init__.py -Force
New-Item app\CustomerSupport\memory\session.py -Force

```
:::
::::

Open `app/CustomerSupport/memory/session.py` (open the file in Kiro's editor and copy following code):

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

Open `app/CustomerSupport/main.py` in Kiro's editor. The key changes are:
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

SYSTEM_PROMPT="""You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To look up product information and specifications
3. Web search - To search the web for troubleshooting help

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""

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

The user-id is retrieved from a custom header as shown in the above code. We need to allowlist the customer header in `agentcore.json`.
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
        "name": "CustomerSupport",
        "build": "CodeZip",
        "entrypoint": "main.py",
        "codeLocation": "app/ClientSupport/",
        "runtimeVersion": "PYTHON_3_13",
        "networkMode": "PUBLIC",
        "protocol": "HTTP",
        "requestHeaderAllowlist": [
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
        ]
    }
]
:::

This is an important step before moving to the next step to make sure that the AgentCore Runtime understands the custom header once the agent is invoked. Ideally, once security is implemented, the `user-id` or `actor-id` should be retreived from the authorization claims. We will see that behavior in Lab 4.

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
  - AWS::BedrockAgentCore::Runtime (CustomerSupport) [updated]
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
agentcore invoke "My name is Sarah and I prefer email updates. I recently bought a Smart Watch." \
  --session-id $SESSION_A \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream
```
:::
:::tab{label="Windows"}
```powershell
$SESSION_A = [guid]::NewGuid().ToString()
agentcore invoke "My name is Sarah and I prefer email updates. I recently bought a Smart Watch." `
  --session-id $SESSION_A `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream

```
:::
::::

Note that a random `--session_id` in the format of UUID and the custom header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id` which we allowlisted in the previous step, is set to Sarah in the command. Wait about 1-2 minutes for the memory extraction to process, then start a **completely new session** and ask. Running the same command with a different prompt works as a new random UUID will be created as session_id. However, the user-id in the custom header is still Sarah:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
sleep 2m
SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')
agentcore invoke "Do you know anything about me?" \
  --session-id $SESSION_B \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream
```
:::
:::tab{label="Windows"}
```powershell
Start-Sleep -Seconds 120
$SESSION_B = [guid]::NewGuid().ToString()
agentcore invoke "Do you know anything about me?" `
  --session-id $SESSION_B `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: Sarah" --stream

```
:::
::::

Expected response:
:::code{language=bash showCopyAction=false}
Yes! I know a few things about you, Sarah:
1. Your name is Sarah
2. You prefer email updates
3. You recently purchased a Smart Watch
:::

🎉 **The agent remembered you across sessions!** The SEMANTIC strategy automatically extracted facts from the first conversation and made them available in the second.

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
| "My name is Sarah" | SEMANTIC | Extracted as fact: "The user's name is Sarah" |
| "I prefer email updates" | SEMANTIC | Extracted as fact: "Sarah prefers email updates" |
| Full conversation | SUMMARIZATION | Compressed summary stored for session continuity |

> **Important:** Memory extraction is asynchronous. If you test too quickly after the first conversation, the facts may not be available yet. Wait ~1-2 minutes between sessions for all facts to be extracted.

## Congratulations — You've Built a Customer-Obsessed AI Agent!

Your agent now:
- ✅ **Remembers every customer interaction** using AgentCore Memory
- ✅ **Extracts customer preferences** automatically via SEMANTIC strategy
- ✅ **Maintains context across sessions** — no more "goldfish agent"
- ✅ **Personalizes responses** based on historical patterns

### What's Next

In Lab 3, you'll move from local tools to enterprise-ready services using AgentCore Gateway — centralizing tool management and adding authentication.

→ Next: [Lab 3: Scaling Tools with Gateway](../40-lab3-gateway/)
