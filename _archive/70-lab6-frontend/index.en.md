---
title: "Lab 7: Build Client Portal Interface"
weight: 72
---

**⏱️ Estimated time: ~20 minutes**

## Overview

Your agent is deployed, monitored, and evaluated — but clients need a way to interact with it. In this lab, you'll build a web chat interface using Flask that connects to your deployed AgentCore Runtime. Clients authenticate via Cognito's hosted login page before accessing the portfolio advisor chat.

### What You'll Build

- A login page that redirects to Cognito's hosted UI for authentication
- A chat interface with a Flask backend
- Automatic agent discovery from your deployment state
- Client authentication via Cognito authorization code flow
- Session management for persistent conversations
- Quick action buttons for common portfolio advisor queries

## Step 1: Install Dependencies

In Kiro's terminal, add Flask, boto3, and requests to your project:

:::code{language=bash}
cd app/PortfolioAdvisor
uv add flask boto3 requests
cd ../..

:::

## Step 2: Allow the Web Client in Your Runtime and Gateway

In Lab 5, you configured the runtime and gateway to accept tokens from the M2M Cognito client. The frontend uses a different Cognito client (the web client, which supports the authorization code flow for user login). You need to add its client ID to the `allowedClients` list.

Retrieve the web client ID:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
WEB_CLIENT_ID=$(aws ssm get-parameter \
  --name /app/portfolioadvisor/agentcore/web_client_id \
  --query 'Parameter.Value' --output text)
echo "Web Client ID: $WEB_CLIENT_ID"
```
:::
:::tab{label="Windows"}
```powershell
$WEB_CLIENT_ID = aws ssm get-parameter `
  --name /app/portfolioadvisor/agentcore/web_client_id `
  --query 'Parameter.Value' --output text
Write-Host "Web Client ID: $WEB_CLIENT_ID"

```
:::
::::

Open `agentcore/agentcore.json` in Kiro's editor. Find both `allowedClients` arrays (**one in the runtime, one in the gateway**) and add the web client ID alongside the existing M2M client ID:

:::code{language=json showCopyAction=false}
"allowedClients": [
  "<existing-m2m-client-id>",
  "<WEB_CLIENT_ID value>"
]
:::

> **Note:** No CLI flag exists for `allowedClients` — this minimal `agentcore.json` edit is required (same pattern as `authorizerConfiguration` in Lab 5).

Then validate and deploy:

:::code{language=bash}
agentcore validate
agentcore deploy -y -v
:::

## Step 3: Create the Backend

Create the frontend directory and files:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
mkdir -p app/PortfolioAdvisor/frontend/templates
touch app/PortfolioAdvisor/frontend/__init__.py
touch app/PortfolioAdvisor/frontend/frontend.py
```
:::
:::tab{label="Windows"}
```powershell
mkdir app\PortfolioAdvisor\frontend\templates
New-Item app\PortfolioAdvisor\frontend\__init__.py -Force
New-Item app\PortfolioAdvisor\frontend\frontend.py -Force

```
:::
::::

Create `app/PortfolioAdvisor/frontend/frontend.py` in Kiro's editor. This Flask server handles Cognito login (authorization code flow), serves the chat UI, and proxies requests to AgentCore Runtime using the user's JWT token.

> **Why not boto3?** The `invoke_agent_runtime` API with JWT bearer tokens is not supported by boto3. Instead, we use the `requests` library to call the AgentCore REST API directly with an `Authorization: Bearer` header, as recommended in the [AWS documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html).

::::::expand{header="Click to see frontend.py code"}

:::alert{header="What this code does" type="info"}
This is a Flask web server that implements the full Cognito OAuth 2.0 authorization code flow. It redirects users to Cognito for login, exchanges the authorization code for tokens, and uses the JWT access token to call the AgentCore Runtime REST API. The `/chat` endpoint proxies user messages to your deployed agent and streams responses back to the browser in real time via server-sent events.
:::
:::code{language=python}
import json
import time
import uuid
import urllib.parse
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, session
import boto3
import requests as http_requests

app = Flask(__name__)
app.secret_key = uuid.uuid4().hex

REGION = boto3.session.Session().region_name or "us-west-2"
ssm_client = boto3.client("ssm", region_name=REGION)
AGENTCORE_ENDPOINT = f"https://bedrock-agentcore.{REGION}.amazonaws.com"
CALLBACK_URL = "http://localhost:8501/"


def get_runtime_arn():
    state_file = Path(__file__).parent.parent.parent.parent / "agentcore" / ".cli" / "deployed-state.json"
    try:
        state = json.loads(state_file.read_text())
        runtimes = state.get("targets", {}).get("default", {}).get("resources", {}).get("runtimes", {})
        return runtimes.get("PortfolioAdvisor", {}).get("runtimeArn", None)
    except Exception:
        pass
    return None

RUNTIME_ARN = get_runtime_arn()

def get_ssm_param(name):
    return ssm_client.get_parameter(Name=name)["Parameter"]["Value"]

def load_cognito_config():
    return {
        "domain": get_ssm_param("/app/portfolioadvisor/agentcore/cognito_domain"),
        "web_client_id": get_ssm_param("/app/portfolioadvisor/agentcore/web_client_id"),
        "token_url": get_ssm_param("/app/portfolioadvisor/agentcore/cognito_token_url"),
        "auth_scope": get_ssm_param("/app/portfolioadvisor/agentcore/cognito_auth_scope"),
    }

_cognito = None
def get_cognito():
    global _cognito
    if not _cognito:
        _cognito = load_cognito_config()
    return _cognito

@app.route("/")
def index():
    code = request.args.get("code")
    if code and "access_token" not in session:
        cognito = get_cognito()
        resp = http_requests.post(cognito["token_url"], data={
            "grant_type": "authorization_code", "client_id": cognito["web_client_id"],
            "code": code, "redirect_uri": CALLBACK_URL,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if resp.status_code == 200:
            tokens = resp.json()
            session["access_token"] = tokens["access_token"]
            try:
                import base64
                payload = tokens.get("id_token", "").split(".")[1]
                payload += "=" * (4 - len(payload) % 4)
                claims = json.loads(base64.b64decode(payload))
                session["username"] = claims.get("email", claims.get("cognito:username", "Client"))
            except Exception:
                session["username"] = "Client"
        return redirect("/")
    if "access_token" not in session:
        cognito = get_cognito()
        login_url = (f"{cognito['domain']}/oauth2/authorize?response_type=code"
            f"&client_id={cognito['web_client_id']}&redirect_uri={urllib.parse.quote(CALLBACK_URL)}"
            f"&scope=openid+email+profile+{urllib.parse.quote(cognito['auth_scope'])}")
        return render_template("login.html", login_url=login_url)
    return render_template("index.html", runtime_arn=RUNTIME_ARN or "Not deployed",
                           username=session.get("username", "Client"))

@app.route("/logout")
def logout():
    session.clear()
    cognito = get_cognito()
    return redirect(f"{cognito['domain']}/logout?client_id={cognito['web_client_id']}"
                    f"&logout_uri={urllib.parse.quote('http://localhost:8501/')}")

@app.route("/chat", methods=["POST"])
def chat():
    if not RUNTIME_ARN:
        return jsonify({"error": "Agent not deployed."}), 500
    token = session.get("access_token")
    if not token:
        return jsonify({"error": "Not authenticated. Please log in."}), 401
    data = request.json
    prompt = data.get("prompt", "")
    session_id = data.get("session_id", str(uuid.uuid4()))
    try:
        escaped_arn = urllib.parse.quote(RUNTIME_ARN, safe='')
        url = f"{AGENTCORE_ENDPOINT}/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id}
        resp = http_requests.post(url, headers=headers, data=json.dumps({"prompt": prompt}))
        resp.raise_for_status()
        full_response = ""
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                chunk = line[6:].strip()
                if chunk:
                    if chunk.startswith('"') and chunk.endswith('"'):
                        chunk = json.loads(chunk)
                    full_response += chunk
        if not full_response:
            full_response = resp.text
        return jsonify({"response": full_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"Runtime ARN: {RUNTIME_ARN or 'NOT FOUND'}")
    app.run(host="0.0.0.0", port=8501)
:::
::::::


> **How it works:**
> - `get_runtime_arn()` reads `agentcore/.cli/deployed-state.json` to discover your agent ARN automatically.
> - When a client opens the app, they're redirected to Cognito's hosted login page. After login, Cognito redirects back with an authorization code that the backend exchanges for an access token.
> - The `/chat` endpoint uses the client's access token to call the AgentCore REST API with an `Authorization: Bearer` header.
> - boto3 doesn't support JWT bearer token invocation, so we use the `requests` library to call the API directly.

## Step 4: Create the Login Page

Create `app/PortfolioAdvisor/frontend/templates/login.html` in Kiro's editor:

:::code{language=html}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Advisor - Sign In</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(180deg, #d6eaf8 0%, #ebf0f5 40%, #f5f7fa 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card { background: white; border-radius: 16px; padding: 48px 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; max-width: 400px; width: 100%; }
.login-card h1 { font-size: 24px; font-weight: 600; color: #1a1a2e; margin-bottom: 8px; }
.login-card p { color: #666; font-size: 14px; margin-bottom: 32px; line-height: 1.5; }
.login-card .avatar { width: 64px; height: 64px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 28px; margin: 0 auto 24px; }
.login-btn { display: inline-block; padding: 14px 32px; background: #1a1a2e; color: white; text-decoration: none; border-radius: 28px; font-size: 15px; font-weight: 500; transition: background 0.2s; }
.login-btn:hover { background: #2d2d4e; }
.footer { margin-top: 24px; font-size: 11px; color: #aaa; }
</style>
</head>
<body>
<div class="login-card">
  <div class="avatar">🤖</div>
  <h1>Portfolio Advisor</h1>
  <p>Sign in to chat with your AI-powered portfolio advisor.</p>
  <a href="{{ login_url }}" class="login-btn">Sign in with Cognito</a>
  <div class="footer">Powered by Amazon Bedrock AgentCore</div>
</div>
</body>
</html>
:::

## Step 5: Create the Chat UI

Create `app/PortfolioAdvisor/frontend/templates/index.html` in Kiro's editor:

:::code{language=html}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Advisor</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(180deg, #d6eaf8 0%, #ebf0f5 40%, #f5f7fa 100%);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.container {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.header {
  text-align: center;
  padding: 60px 0 30px;
}
.header h1 { font-size: 28px; font-weight: 600; color: #1a1a2e; }
.status {
  text-align: center;
  font-size: 12px;
  color: #888;
  padding: 8px 0;
}
.status .connected { color: #27ae60; }
.status .btn-new {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid #ddd;
  background: white;
  font-size: 11px;
  cursor: pointer;
  color: #555;
  margin-left: 8px;
}
.status .btn-new:hover { border-color: #1a1a2e; }
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}
.message {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.message.user { justify-content: flex-end; }
.message .bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.message.user .bubble {
  background: #1a1a2e;
  color: white;
  border-bottom-right-radius: 4px;
}
.message.assistant .bubble {
  background: white;
  color: #1a1a2e;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.message.assistant .avatar {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 14px; flex-shrink: 0;
}
.thinking { display: flex; gap: 4px; padding: 4px 0; }
.thinking span {
  width: 8px; height: 8px; background: #aaa; border-radius: 50%;
  animation: bounce 1.4s infinite;
}
.thinking span:nth-child(2) { animation-delay: 0.2s; }
.thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0.6); } 40% { transform: scale(1); } }
.input-area { padding: 20px 0; position: sticky; bottom: 0; }
.input-bar {
  display: flex; align-items: center;
  background: white; border-radius: 28px;
  padding: 6px 6px 6px 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border: 1px solid #e8e8e8;
}
.input-bar input {
  flex: 1; border: none; outline: none;
  font-size: 15px; background: transparent; color: #1a1a2e;
}
.input-bar input::placeholder { color: #aaa; }
.input-bar button {
  width: 40px; height: 40px; border-radius: 50%; border: none;
  background: #1a1a2e; color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.2s;
}
.input-bar button:hover { background: #2d2d4e; }
.input-bar button:disabled { background: #ccc; cursor: default; }
.quick-actions {
  display: flex; gap: 8px; justify-content: center;
  margin-top: 12px; flex-wrap: wrap;
}
.quick-actions button {
  padding: 8px 16px; border-radius: 20px;
  border: 1px solid #ddd; background: white;
  color: #555; font-size: 13px; cursor: pointer;
  transition: all 0.2s;
}
.quick-actions button:hover { border-color: #1a1a2e; color: #1a1a2e; }
</style>
</head>
<body>
<div class="container">
  <div class="status">
    <span class="connected">● Connected</span> — {{ runtime_arn }}
    <button class="btn-new" onclick="newSession()">🔄 New Session</button>
    <a href="/logout" class="btn-new">🚪 Logout ({{ username }})</a>
    <span id="sessionLabel"></span>
  </div>
  <div class="header" id="header">
    <h1>👋 How can I help you today?</h1>
  </div>
  <div class="chat-area" id="chatArea"></div>
  <div class="input-area">
    <div class="input-bar">
      <input id="msgInput" type="text" placeholder="Ask your portfolio advisor..." onkeydown="if(event.key==='Enter')sendMsg()" autofocus />
      <button onclick="sendMsg()" id="sendBtn">↑</button>
    </div>
    <div class="quick-actions" id="quickActions">
      <button onclick="quickSend('Analyze AAPL stock')">📊 Analyze Stock</button>
      <button onclick="quickSend('Check portfolio risk for PORT-001')">📈 Portfolio Risk</button>
      <button onclick="quickSend('Execute a trade: buy 100 MSFT market')">💹 Execute Trade</button>
      <button onclick="quickSend('Do you remember my preferences?')">🧠 Memory</button>
    </div>
  </div>
</div>
<script>
let sessionId = crypto.randomUUID();
document.getElementById('sessionLabel').textContent = '  Session: ' + sessionId;

function newSession() {
  sessionId = crypto.randomUUID();
  document.getElementById('sessionLabel').textContent = '  Session: ' + sessionId;
  document.getElementById('chatArea').innerHTML = '';
  document.getElementById('quickActions').style.display = 'flex';
  document.getElementById('header').style.display = 'block';
}

function addMessage(role, text) {
  const chat = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'message ' + role;
  if (role === 'assistant') {
    div.innerHTML = '<div class="avatar">🤖</div><div class="bubble">' + text.replace(/\n/g, '<br>') + '</div>';
  } else {
    div.innerHTML = '<div class="bubble">' + text + '</div>';
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function showThinking() {
  const chat = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'message assistant'; div.id = 'thinking';
  div.innerHTML = '<div class="avatar">🤖</div><div class="bubble"><div class="thinking"><span></span><span></span><span></span></div></div>';
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function removeThinking() { const el = document.getElementById('thinking'); if (el) el.remove(); }

async function sendMsg() {
  const input = document.getElementById('msgInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  document.getElementById('quickActions').style.display = 'none';
  document.getElementById('header').style.display = 'none';
  addMessage('user', msg);
  showThinking();
  document.getElementById('sendBtn').disabled = true;
  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: msg, session_id: sessionId})
    });
    const data = await resp.json();
    removeThinking();
    addMessage('assistant', data.response || data.error || 'No response');
  } catch(e) {
    removeThinking();
    addMessage('assistant', 'Error: ' + e.message);
  }
  document.getElementById('sendBtn').disabled = false;
  input.focus();
}

function quickSend(text) { document.getElementById('msgInput').value = text; sendMsg(); }
</script>
</body>
</html>
:::

## Step 6: Run the Frontend

In Kiro's terminal, start the Flask app:

:::code{language=bash}
cd app/PortfolioAdvisor/frontend
uv run python frontend.py
:::

You should see:
:::code{language=bash showCopyAction=false}
Runtime ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/PortfolioAdvisor_PortfolioAdvisor-xxxxx
 * Running on http://127.0.0.1:8501
:::

Open your browser at **http://localhost:8501**. You'll see a login page — click "Sign in with Cognito" to authenticate via the Cognito hosted UI.

![Login page with Sign in with Cognito button](/static/70-lab6-frontend/lab6_login_page.png)

Use the credentials you created in Lab 5:

- **Email:** `workshopuser@example.com`
- **Password:** `WorkshopPass1!`

After login, you'll be redirected to the chat interface.

![Chat interface running in the browser](/static/images/lab6_chat_interface.png)

## Alternative: Quick Test with AgentCore Dev TUI

If you want a quick way to interact with your agent without building a frontend, the AgentCore CLI provides a built-in interactive chat TUI:

:::code{language=bash}
agentcore dev
:::

This opens an interactive chat interface directly in your terminal where you can type messages and see responses in real time. Note that memory is not available in local dev mode — to test with memory, use `agentcore invoke` against the deployed agent.

## Step 7: Test the Interface

Try the quick action buttons or type your own questions:

**Stock analysis:**
> "What's the analysis for MSFT?"

**Compliance inquiry:**
> "What are the compliance rules for margin trading?"

**Portfolio risk check (via Gateway):**
> "Check the portfolio risk for PORT-002"

**Memory recall:**
> "Do you remember my investment preferences?"

**Session continuity — send multiple messages in the same session:**
> "My name is Alex Chen, I prefer conservative dividend stocks"
> "What are my preferences?"

Click **🔄 New Session** to start a fresh conversation — the agent won't remember the previous session context (but long-term memory facts will persist).

## Architecture

![Lab 7 Architecture](/static/70-lab6-frontend/lab6_architecture_diagram.png)

:::code{language=bash showCopyAction=false}
User (browser at localhost:8501)
    ↓
Flask backend (frontend.py)
    ├── Reads deployed-state.json for agent ARN
    ├── Obtains Cognito M2M token from SSM + Cognito token endpoint
    ↓
invoke_agent_runtime(bearerToken=token)
    ↓
Cognito validates JWT
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Session management (isolated per session-id)
    ├── Memory (SEMANTIC + SUMMARIZATION)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    ├── MCP Client → Exa AI (web search)
    └── MCP Client → AgentCore Gateway (secured) → Lambda: check_portfolio_risk
                          ↓
                    CloudWatch + AgentCore Evaluations
:::

## What Just Happened?

The Flask app authenticates users via Cognito's hosted UI and uses their access token to call AgentCore Runtime. The flow is:

:::code{language=bash showCopyAction=false}
User opens http://localhost:8501
    ↓
Flask redirects to Cognito hosted login page
    ↓
User signs in (or signs up)
    ↓
Cognito redirects back with authorization code
    ↓
Flask exchanges code for access token
    ↓
User types message in chat
    ↓
Flask calls AgentCore REST API with Authorization: Bearer header
    ↓
AgentCore Runtime (PortfolioAdvisor) validates JWT and processes the request
    ↓
Agent uses tools (local + Gateway) and memory
    ↓
Response returned as JSON to browser
:::

Key features:
- **Cognito login** — Clients authenticate via Cognito's hosted UI (authorization code flow)
- **Auto-discovery** — The backend reads `deployed-state.json` to find your agent ARN automatically
- **Session management** — Each conversation gets a unique UUID session ID
- **Persistent history** — Chat history is maintained in the browser
- **Logout** — The logout button clears the session and redirects to Cognito's logout endpoint

### What's Next

In Lab 8, you'll add governance to your agent with AgentCore Policies — controlling what tools the agent can use and under what conditions, all without changing agent code.

→ Next: [Lab 8: Governing Agent Actions with Policies](../80-lab7-governing-actions/)
