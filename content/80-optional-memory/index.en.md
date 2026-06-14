---
title: "Optional Lab: Add Persistent Memory"
weight: 80
---

**Optional** — This lab adds persistent memory so your agent remembers client preferences across sessions. Skip it if you're short on time and continue to the Summary.

**⏱️ Estimated time: ~20 minutes**

:::alert{header="Self-paced lab" type="info"}
Do this after the live session — **your event account stays available for a limited time after the Summit**. If you're in a new terminal, run `source ~/portfolio-env.sh` to reload your environment variables.

**Prerequisites:** Lab 1 (a deployed agent). Memory is independent of the Gateway.
:::

## Overview

Without memory, every conversation starts from zero. Clients must repeat their investment preferences, risk tolerance, and portfolio goals on every call. AgentCore Memory provides both SEMANTIC extraction (facts and preferences) and SUMMARIZATION (compressed conversation history), namespaced per user so each client's context stays private.

In this lab you'll add memory to your deployed `PortfolioAdvisor` agent and verify that preferences introduced in one session are recalled automatically in a brand-new session.

### What You're Building

:::code{language=bash showCopyAction=false}
Session 1: "I prefer conservative tech stocks"
    ↓
AgentCore Runtime → AgentCore Memory  ← THIS LAB
                        │
                        ├── SEMANTIC: extracts facts & preferences
                        └── SUMMARIZATION: compresses conversation history
                        │
                        ▼ (persisted per user)
Session 2: "What should I look at today?"
    ↓
Agent recalls: "You prefer conservative tech stocks" ── no repetition needed
:::

## Step 1: Add Memory to Your Project

Use the AgentCore CLI to add a memory resource:

:::code{language=bash}
cd ~/PortfolioAdvisor

agentcore add memory \
  --name SharedMemory \
  --strategies SEMANTIC,SUMMARIZATION \
  --expiry 30
:::

You should see:

:::code{language=bash showCopyAction=false}
Added memory 'SharedMemory'
:::

Verify the updated configuration:

:::code{language=bash}
cat agentcore/agentcore.json
:::

The `memories` array now contains your memory resource with SEMANTIC and SUMMARIZATION strategies, each with their own namespace patterns.

## Step 2: Create the Memory Session Manager

Create the memory integration module:

:::code{language=bash}
mkdir -p app/PortfolioAdvisor/memory
touch app/PortfolioAdvisor/memory/__init__.py
touch app/PortfolioAdvisor/memory/session.py
:::

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

:::alert{header="Harness note" type="warning"}
This self-paced lab reflects the original code-based agent. On the AgentCore **harness**, persistent memory is enabled through configuration (a memory resource referenced by the harness) rather than by editing `main.py`. The concepts below — SEMANTIC and SUMMARIZATION strategies, actor/session scoping — are identical. A harness-native version of these steps is tracked in `HARNESS_MIGRATION.md`.
:::

## Step 3: Update main.py to Use Memory

Open `app/PortfolioAdvisor/main.py`. Make the following changes:

1. Add the import at the top (alongside the existing imports):

:::code{language=python}
from memory.session import get_memory_session_manager
:::

2. Update `get_or_create_agent` to create a `session_manager` and pass it to the Agent. Add the `session_manager` parameter — everything else stays the same:

:::code{language=python}
def get_or_create_agent(session_id=None, user_id=None, auth_header=""):
    gateway_client = get_gateway_mcp_client(auth_header)
    mcp_tools = [gateway_client] if gateway_client else []
    tools = [get_stock_analysis, get_compliance_rules] + mcp_tools
    session_manager = get_memory_session_manager(session_id, user_id) if session_id and user_id else None
    try:
        return Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            session_manager=session_manager,
        )
    except (ValueError, Exception) as e:
        log.warning(f"Agent creation failed with MCP tools, falling back: {e}")
        return Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=[get_stock_analysis, get_compliance_rules],
            session_manager=session_manager,
        )
:::

The `invoke` function already passes `session_id` and `user_id` from Lab 2 — no changes needed there. The `extract_user_id` function extracts the user from the JWT, which is what Memory uses as the `actor_id` to namespace stored facts per user.

:::alert{header="Header allowlist" type="info"}
Lab 2 already added `Authorization` and `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id` to `requestHeaderAllowlist` — no additional configuration needed here.
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

### Grant Memory Retrieval Permissions

The CDK stack grants write access to memory but you must manually add retrieval permissions to the runtime role:

:::code{language=bash}
RUNTIME_ROLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name AgentCore-PortfolioAdvisor-default \
  --query "StackResources[?ResourceType=='AWS::IAM::Role' && contains(LogicalResourceId, 'ApplicationAgentPortfolio')].PhysicalResourceId | [0]" \
  --output text)

MEMORY_ARN=$(aws cloudformation describe-stacks \
  --stack-name AgentCore-PortfolioAdvisor-default \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'MemorySharedMemoryArn')].OutputValue | [0]" \
  --output text)

aws iam put-role-policy \
  --role-name $RUNTIME_ROLE_NAME \
  --policy-name MemoryAccess \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"bedrock-agentcore:RetrieveMemoryRecords\",\"bedrock-agentcore:GetMemory\",\"bedrock-agentcore:ListMemoryRecords\",\"bedrock-agentcore:CreateMemoryEvent\",\"bedrock-agentcore:ListMemoryEvents\"],\"Resource\":\"${MEMORY_ARN}\"}]}"

echo "Added MemoryAccess policy to role: $RUNTIME_ROLE_NAME"
:::

:::alert{header="Why is this step needed?" type="info"}
The AgentCore CDK constructs grant event write permissions (`CreateMemoryEvent`) to the runtime role but do not currently grant retrieval permissions (`RetrieveMemoryRecords`). This manual IAM step is required until the CDK fix ships.
:::

## Step 5: Test Memory Recall Across Sessions

Get a token using your environment variables, then teach the agent about a client in **Session A**:

:::code{language=bash}
source ~/portfolio-env.sh

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $COGNITO_WEB_CLIENT_ID \
  --auth-parameters USERNAME=workshopuser@example.com,PASSWORD='WorkshopPass1!' \
  --query 'AuthenticationResult.AccessToken' --output text)

SESSION_A=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "My name is Alex Chen. I prefer conservative dividend stocks. My risk tolerance is moderate." \
  --session-id $SESSION_A \
  --bearer-token "$TOKEN" --stream
:::

:::alert{header="How Memory identifies users" type="info"}
The `extract_user_id` function (added in Lab 2) extracts the user identity from the JWT. Memory uses this as the `actor_id` to namespace stored facts. Since `workshopuser@example.com` always gets the same JWT `username` claim, preferences persist correctly across sessions for the same authenticated user.
:::

Wait ~2 minutes for memory extraction to process, then start a **completely new session** and ask:

:::code{language=bash}
sleep 2m

SESSION_B=$(python3 -c 'import uuid; print(uuid.uuid4())')

agentcore invoke "Do you know anything about me?" \
  --session-id $SESSION_B \
  --bearer-token "$TOKEN" --stream
:::

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

→ Next: [Summary](../90-summary/)
