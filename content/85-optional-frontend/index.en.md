---
title: "Optional Lab 8: Build Client Portal"
weight: 85
---

**Optional** — This lab builds a web chat interface using Flask with Cognito login that connects to your deployed agent. Skip it if you're short on time and continue to the Summary.

**Prerequisites:** Labs 1–3 completed (deployed agent with JWT auth)
**Estimated time: ~20 minutes**

## Overview

Your agent is deployed and secured — but clients need a browser-based way to interact with it. In this lab you'll build a Flask web app that:

- Redirects unauthenticated users to Cognito's hosted login page
- Exchanges the authorization code for a JWT access token (OAuth 2.0 code flow)
- Proxies chat messages to your AgentCore Runtime using the client's Bearer token
- Streams responses back to the browser

:::alert{header="Why not boto3?" type="info"}
The `invoke_agent_runtime` boto3 API does not support JWT bearer token invocation. Instead, the Flask backend calls the AgentCore REST API directly using the `requests` library with an `Authorization: Bearer` header, as documented in the [AgentCore Runtime OAuth guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html).
:::

### What You're Building

:::code{language=bash showCopyAction=false}
Browser (localhost:5000)  ← THIS LAB
    │
    ├── /login ──▶ Cognito Hosted UI (OAuth 2.0 code flow)
    │                    │
    │                    ▼
    │              JWT access token
    │
    ├── /chat ──▶ Flask backend
    │                │
    │                ▼ (Bearer token in header)
    │          AgentCore Runtime REST API
    │                │
    │                ▼
    │          Agent response (streamed)
    │
    └── Browser renders response in real-time
:::

## Step 1: Install Dependencies

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd ~/PortfolioAdvisor/app/PortfolioAdvisor
uv add flask boto3 requests
cd ../..
```
:::
:::tab{label="Windows"}
```powershell
cd ~/PortfolioAdvisor\app\PortfolioAdvisor
uv add flask boto3 requests
cd ..\..

```
:::
::::

## Step 2: Allow the Web Client in Your Runtime and Gateway

In Lab 3, you configured `allowedClients` with the M2M Cognito client. The web login flow uses a different client (one that supports the authorization code flow). Add its client ID to both `allowedClients` arrays.

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

Open `agentcore/agentcore.json` in Kiro's editor. Find both `allowedClients` arrays — one inside the runtime block and one inside the gateway block — and add the web client ID alongside the existing M2M client ID:

:::code{language=json showCopyAction=false}
"allowedClients": [
  "<existing-m2m-client-id>",
  "<WEB_CLIENT_ID value>"
]
:::

Then validate and deploy:

:::code{language=bash}
agentcore validate
agentcore deploy -y -v
:::

## Step 3: Create the Frontend Directory

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

## Step 4: Create the Backend

Open `app/PortfolioAdvisor/frontend/frontend.py` and add the following code.

::::::expand{header="Click to see frontend.py"}

:::alert{header="What this code does" type="info"}
This Flask server implements the Cognito OAuth 2.0 authorization code flow. It redirects users to Cognito's hosted UI, exchanges the authorization code for tokens, and uses the JWT access token to call the AgentCore Runtime REST API. The `/chat` endpoint proxies user messages to your deployed agent and returns the response as JSON.
:::

:::code{language=python}
import json
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
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }
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

## Step 5: Create the Login Page

Create `app/PortfolioAdvisor/frontend/templates/login.html`:

::::::expand{header="Click to see login.html"}
:::code{language=html}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Advisor - Sign In</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(180deg, #d6eaf8 0%, #ebf0f5 40%, #f5f7fa 100%);
  min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card { background: white; border-radius: 16px; padding: 48px 40px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; max-width: 400px; width: 100%; }
.login-card h1 { font-size: 24px; font-weight: 600; color: #1a1a2e; margin-bottom: 8px; }
.login-card p { color: #666; font-size: 14px; margin-bottom: 32px; line-height: 1.5; }
.login-card .avatar { width: 64px; height: 64px;
  background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 28px; margin: 0 auto 24px; }
.login-btn { display: inline-block; padding: 14px 32px; background: #1a1a2e; color: white;
  text-decoration: none; border-radius: 28px; font-size: 15px; font-weight: 500; transition: background 0.2s; }
.login-btn:hover { background: #2d2d4e; }
.footer { margin-top: 24px; font-size: 11px; color: #aaa; }
</style>
</head>
<body>
<div class="login-card">
  <div class="avatar">&#x1F916;</div>
  <h1>Portfolio Advisor</h1>
  <p>Sign in to chat with your AI-powered portfolio advisor.</p>
  <a href="{{ login_url }}" class="login-btn">Sign in with Cognito</a>
  <div class="footer">Powered by Amazon Bedrock AgentCore</div>
</div>
</body>
</html>
:::
::::::

## Step 6: Create the Chat Interface

Create `app/PortfolioAdvisor/frontend/templates/index.html`:

::::::expand{header="Click to see index.html"}
:::code{language=html}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Advisor</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(180deg, #d6eaf8 0%, #ebf0f5 40%, #f5f7fa 100%);
  min-height: 100vh; display: flex; flex-direction: column; }
.container { max-width: 800px; width: 100%; margin: 0 auto; padding: 20px;
  flex: 1; display: flex; flex-direction: column; }
.header { text-align: center; padding: 60px 0 30px; }
.header h1 { font-size: 28px; font-weight: 600; color: #1a1a2e; }
.status { text-align: center; font-size: 12px; color: #888; padding: 8px 0; }
.status .connected { color: #27ae60; }
.status .btn-new { padding: 4px 12px; border-radius: 8px; border: 1px solid #ddd;
  background: white; font-size: 11px; cursor: pointer; color: #555; margin-left: 8px; }
.status .btn-new:hover { border-color: #1a1a2e; }
.chat-area { flex: 1; overflow-y: auto; padding: 20px 0; }
.message { margin-bottom: 16px; display: flex; gap: 10px; animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.message.user { justify-content: flex-end; }
.message .bubble { max-width: 75%; padding: 12px 16px; border-radius: 18px;
  font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
.message.user .bubble { background: #1a1a2e; color: white; border-bottom-right-radius: 4px; }
.message.assistant .bubble { background: white; color: #1a1a2e; border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.message.assistant .avatar { width: 32px; height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 14px; flex-shrink: 0; }
.thinking { display: flex; gap: 4px; padding: 4px 0; }
.thinking span { width: 8px; height: 8px; background: #aaa; border-radius: 50%;
  animation: bounce 1.4s infinite; }
.thinking span:nth-child(2) { animation-delay: 0.2s; }
.thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0.6); } 40% { transform: scale(1); } }
.input-area { padding: 20px 0; position: sticky; bottom: 0; }
.input-bar { display: flex; align-items: center; background: white; border-radius: 28px;
  padding: 6px 6px 6px 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e8e8e8; }
.input-bar input { flex: 1; border: none; outline: none; font-size: 15px;
  background: transparent; color: #1a1a2e; }
.input-bar input::placeholder { color: #aaa; }
.input-bar button { width: 40px; height: 40px; border-radius: 50%; border: none;
  background: #1a1a2e; color: white; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
.input-bar button:hover { background: #2d2d4e; }
.input-bar button:disabled { background: #ccc; cursor: default; }
.quick-actions { display: flex; gap: 8px; justify-content: center;
  margin-top: 12px; flex-wrap: wrap; }
.quick-actions button { padding: 8px 16px; border-radius: 20px; border: 1px solid #ddd;
  background: white; color: #555; font-size: 13px; cursor: pointer; transition: all 0.2s; }
.quick-actions button:hover { border-color: #1a1a2e; color: #1a1a2e; }
</style>
</head>
<body>
<div class="container">
  <div class="status">
    <span class="connected">&#x25CF; Connected</span> &mdash; {{ runtime_arn }}
    <button class="btn-new" onclick="newSession()">New Session</button>
    <a href="/logout" class="btn-new">Logout ({{ username }})</a>
    <span id="sessionLabel"></span>
  </div>
  <div class="header" id="header">
    <h1>How can I help you today?</h1>
  </div>
  <div class="chat-area" id="chatArea"></div>
  <div class="input-area">
    <div class="input-bar">
      <input id="msgInput" type="text" placeholder="Ask your portfolio advisor..."
             onkeydown="if(event.key==='Enter')sendMsg()" autofocus />
      <button onclick="sendMsg()" id="sendBtn">&#x2191;</button>
    </div>
    <div class="quick-actions" id="quickActions">
      <button onclick="quickSend('Analyze AAPL stock')">Analyze Stock</button>
      <button onclick="quickSend('What are the compliance rules for margin trading?')">Compliance Rules</button>
      <button onclick="quickSend('Check portfolio risk for PORT-001')">Portfolio Risk</button>
      <button onclick="quickSend('Do you remember my preferences?')">Memory Recall</button>
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
    div.innerHTML = '<div class="avatar">&#x1F916;</div><div class="bubble">' + text.replace(/\n/g, '<br>') + '</div>';
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
  div.innerHTML = '<div class="avatar">&#x1F916;</div><div class="bubble"><div class="thinking"><span></span><span></span><span></span></div></div>';
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
::::::

## Step 7: Run the Frontend

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
cd app/PortfolioAdvisor/frontend
uv run python frontend.py
```
:::
:::tab{label="Windows"}
```powershell
cd app\PortfolioAdvisor\frontend
uv run python frontend.py

```
:::
::::

You should see:

:::code{language=bash showCopyAction=false}
Runtime ARN: arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/PortfolioAdvisor_PortfolioAdvisor-xxxxx
 * Running on http://127.0.0.1:8501
:::

Open **http://localhost:8501** in your browser. Click **Sign in with Cognito** and use the workshop credentials:

- **Email:** `workshopuser@example.com`
- **Password:** `WorkshopPass1!`

After login you'll land on the chat interface. Try the quick action buttons or type your own questions:

- `"What's the analysis for MSFT?"` — stock fundamentals
- `"What are the compliance rules for options trading?"` — compliance query
- `"Check portfolio risk for PORT-002"` — Gateway tool call (if Lab 2 deployed)

Click **New Session** to start a fresh conversation. Long-term memory facts persist across sessions; session context does not.

## Architecture

:::code{language=bash showCopyAction=false}
User (browser at localhost:8501)
    ↓
Flask backend (frontend.py)
    ├── Cognito hosted UI → authorization code → access token
    ├── Reads deployed-state.json for runtime ARN
    ↓
POST /runtimes/{arn}/invocations
    Authorization: Bearer {access_token}
    ↓
Cognito validates JWT
    ↓
AgentCore Runtime (PortfolioAdvisor)
    ├── Local tools: get_stock_analysis(), get_compliance_rules()
    └── AgentCore Gateway (if configured)
:::

---

→ Next: [Optional Lab 9: Cost Optimization](../88-optional-cost/) or [Summary](../90-summary/)
