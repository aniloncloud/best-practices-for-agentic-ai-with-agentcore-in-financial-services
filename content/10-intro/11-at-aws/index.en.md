---
title: "At an AWS Event"
weight: 11
---

If you are attending an AWS Immersion Day, AWS Workshop, or similar AWS led event, you will be provided with access to a temporary AWS account pre-configured with all the necessary resources — including a browser-based VS Code development environment.

## Before you start

- Sign out of all AWS accounts in all browser windows
- Review the event terms and conditions. Do not upload personal or confidential information to the account
- The AWS account will only be available during the workshop — back up any materials you want to keep
- No local software installation is required — everything runs in your browser

## Workshop Studio AWS Account access

1. Follow the link provided by the instructor or use the 12-digit access code
2. Sign in via Workshop Studio, choose "Email one-time password (OTP)"
3. Enter your email, receive the passcode by email, and sign in
4. Review the terms and conditions and click "Join event"
5. On the event page, choose "Open AWS console"
6. Verify you are in the **us-west-2** region

## Access Your VS Code Development Environment

Your workshop environment includes a browser-based VS Code server (code-server) with all tools pre-installed. No local setup is needed.

### 1. Find the VS Code Server URL

In the AWS Console, navigate to **CloudFormation** → **Stacks** → select the **DevBox** stack → **Outputs** tab.

Find the output labeled **01LandingPageUrl** — this is your VS Code Server URL. Click the link to open it in a new browser tab.

:::alert{header="First Load" type="info"}
The first time you open the URL, it may take 30-60 seconds for the page to load while CloudFront establishes the connection.
:::

### 2. Retrieve Your Password

In the same CloudFormation **Outputs** tab, find the output labeled **02CodeServerPassword**. Click the Secrets Manager link to open the secret in the AWS Console.

1. In Secrets Manager, click **Retrieve secret value**
2. Copy the password value
3. Paste it into the code-server login page in your browser

:::alert{header="Tip" type="info"}
You can also retrieve the password from the terminal (once logged in) or via the AWS CLI:
```bash
aws secretsmanager get-secret-value \
  --secret-id devbox-codeserver-password \
  --query SecretString --output text
```
:::

### 3. Verify Your Environment

Once logged into VS Code Server, open a terminal (**Terminal → New Terminal** or `` Ctrl+` ``):

:::code{language=bash}
# Verify Python 3.11 virtual environment is active
python --version

# Verify workshop dependencies
pip show strands-agents bedrock-agentcore

# Verify AWS credentials (pre-configured via instance profile)
aws sts get-caller-identity

# Verify Docker
docker --version

# Verify region
aws configure get region
:::

Expected:
- Python 3.11.x
- `strands-agents` and `bedrock-agentcore` packages installed
- Valid AWS identity (EC2 instance role)
- Docker available
- Region: `us-west-2`

### 4. Explore the Workshop Files

Your workspace is pre-loaded with the workshop project:

:::code{language=bash}
cd ~/PortfolioAdvisor
ls app/PortfolioAdvisor/
:::

You should see: `main.py`, `mcp_client/`, `model/`, `tool/`, `pyproject.toml`

## What's Pre-Installed

Your DevBox development environment includes:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11 | Agent runtime |
| **strands-agents** | Latest | Agent framework |
| **bedrock-agentcore** | Latest | AgentCore SDK |
| **mcp** | Latest | Model Context Protocol client |
| **Docker** | Latest | Container builds for AgentCore Runtime |
| **AWS CLI** | v2 | AWS resource management |
| **Node.js** | 20.x | AgentCore CLI |
| **AgentCore CLI** | Latest | `agentcore` commands |

## Enable Transaction Search (for Observability)

:::alert{header="Region Availability" type="info"}
If you are running this at an AWS-led event, this will already be enabled, but you can double-check with the following steps:
:::

This is a one-time prerequisite to view observability metrics in CloudWatch. You will need this for Lab 4.

1. Navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. In the left panel, find **GenAI Observability** → **Bedrock AgentCore**
3. Click **Configure** which navigates to the X-Ray Transaction Search page
4. Enable Transaction Search

![CloudWatch GenAI Observability console showing the Configure button for Transaction Search](/static/images/cloudwatch-transaction-search-configure.png)

Toggle **Enable Transaction Search** and click **Save**:

![X-Ray Transaction Search enable toggle](/static/images/xray-enable-transaction-search.png)

**You are now ready to start the workshop!**
