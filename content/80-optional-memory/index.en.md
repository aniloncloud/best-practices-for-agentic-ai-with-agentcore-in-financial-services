---
title: "Optional Lab 7: Add Persistent Memory"
weight: 80
---

**Optional** — This lab adds persistent memory so your agent remembers client preferences across sessions. Skip it if you're short on time and continue to the Summary.

**Prerequisites:** Labs 1–3 completed (deployed agent with JWT auth)
**Estimated time: ~20 minutes**

## Overview

Without memory, every conversation starts from zero. Clients must repeat their investment preferences, risk tolerance, and portfolio goals on every call. AgentCore Memory provides both SEMANTIC extraction (facts and preferences) and SUMMARIZATION (compressed conversation history), namespaced per user so each client's context stays private.

In this lab you'll add memory to your deployed `PortfolioAdvisor` agent and verify that preferences introduced in one session are recalled automatically in a brand-new session.

## Step 1: Add Memory to Your Project

Use the AgentCore CLI to add a memory resource:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd ~/PortfolioAdvisor

agentcore add memory \
  --name SharedMemory \
  --strategies SEMANTIC,SUMMARIZATION \
  --expiry 30
```
:::
:::tab{label="Windows"}
```powershell
cd ~/PortfolioAdvisor

agentcore add memory --name SharedMemory --strategies "SEMANTIC,SUMMARIZATION" --expiry 30

```
:::
::::

You should see:

:::code{language=bash showCopyAction=false}
Added memory 'SharedMemory'
:::

Verify the updated configuration:

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

## Step 2: Create the Memory Session Manager

Create the memory integration module:

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

Open `app/PortfolioAdvisor/memory/session.py` and add the following code:

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

## Step 3: Update main.py to Use Memory

Open `app/PortfolioAdvisor/main.py`. Make the following changes:

1. Add the import at the top (alongside the existing imports):

:::code{language=python}
from memory.session import get_memory_session_manager
:::

2. Replace the single global `_agent` setup with an agent factory that accepts `session_id` and `user_id`:

:::code{language=python}
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
:::

3. Update the `invoke` function to extract `user_id` from the request context and pass it to the factory:

:::code{language=python}
@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    session_id = context.session_id
    user_id = context.request_headers['x-amzn-bedrock-agentcore-runtime-custom-user-id']

    if not session_id or not user_id:
        raise ValueError("session_id and user_id are required.")

    agent = get_or_create_agent(session_id, user_id)
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
:::

4. Add the custom header to the allowlist in `agentcore/agentcore.json` (inside your runtime block):

:::code{language=json}
"requestHeaderAllowlist": [
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"
]
:::

## Step 4: Deploy

:::alert{header="Memory requires a cloud deployment" type="info"}
Memory is a managed cloud service — it is not available in local `agentcore dev` mode. The redeployment updates your existing stack with the new memory resource.
:::

:::code{language=bash}
agentcore validate
agentcore deploy -y -v
:::

You should see the memory resource added to your existing deployment:

:::code{language=bash showCopyAction=false}
✓ Load deployment target
✓ Validate project
✓ Build CDK project
✓ Synthesize CloudFormation
✓ Deploy to AWS
  - AWS::BedrockAgentCore::Memory (SharedMemory)
  - AWS::BedrockAgentCore::Runtime (PortfolioAdvisor) [updated]
✓ Deployed to 'default'
:::

## Step 5: Test Memory Recall Across Sessions

Get a token, then teach the agent about a client in **Session A**:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $(aws ssm get-parameter --name /app/portfolioadvisor/agentcore/m2m_client_id --query 'Parameter.Value' --output text) \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1! \
  --query 'AuthenticationResult.AccessToken' --output text)

SESSION_A=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "My name is Alex Chen. I prefer conservative dividend stocks. My risk tolerance is moderate." \
  --session-id $SESSION_A \
  --bearer-token "$TOKEN" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
$TOKEN = aws cognito-idp initiate-auth `
  --auth-flow USER_PASSWORD_AUTH `
  --client-id (aws ssm get-parameter --name /app/portfolioadvisor/agentcore/m2m_client_id --query 'Parameter.Value' --output text) `
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD=WorkshopPass1! `
  --query 'AuthenticationResult.AccessToken' --output text

$SESSION_A = [guid]::NewGuid().ToString()

agentcore invoke "My name is Alex Chen. I prefer conservative dividend stocks. My risk tolerance is moderate." `
  --session-id $SESSION_A `
  --bearer-token "$TOKEN" `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream

```
:::
::::

Wait ~2 minutes for memory extraction to process, then start a **completely new session** and ask:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
sleep 2m

SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "Do you know anything about me?" \
  --session-id $SESSION_B \
  --bearer-token "$TOKEN" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id: AlexChen" --stream
```
:::
:::tab{label="Windows"}
```powershell
Start-Sleep -Seconds 120

$SESSION_B = [guid]::NewGuid().ToString()

agentcore invoke "Do you know anything about me?" `
  --session-id $SESSION_B `
  --bearer-token "$TOKEN" `
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

:::alert{header="Memory extraction is asynchronous" type="info"}
Facts are extracted after each session ends, not in real time. If the recall test returns nothing, wait another minute and try again.
:::

## How It Works

| What happened | Strategy | Result |
|--------------|----------|--------|
| "My name is Alex Chen" | SEMANTIC | Stored as fact: user's name is Alex Chen |
| "I prefer conservative dividend stocks" | SEMANTIC | Stored as fact: investment preference |
| "My risk tolerance is moderate" | SEMANTIC | Stored as fact: risk tolerance |
| Full conversation | SUMMARIZATION | Compressed summary for session continuity |

## Architecture

:::code{language=bash showCopyAction=false}
agentcore invoke (Session B, user=AlexChen)
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── AgentCoreMemorySessionManager
    │   ├── Retrieve: /users/AlexChen/facts (top 3)
    │   └── Retrieve: /summaries/AlexChen/{sessionB} (top 3)
    ├── Facts injected into agent context
    └── Agent responds with recalled preferences
:::

---

→ Next: [Optional Lab 8: Build Client Portal](../85-optional-frontend/) or [Summary](../90-summary/)
