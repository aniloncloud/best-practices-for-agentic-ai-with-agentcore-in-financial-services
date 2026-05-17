---
title: "At an AWS Event"
weight: 11
---

If you are attending an AWS Immersion Day, AWS Workshop, or similar AWS led event, you will be provided with access to a temporary AWS account pre-configured with all the necessary resources.

## Before you start

- Sign out of all AWS accounts in all browser windows
- Review the event terms and conditions. Do not upload personal or confidential information to the account
- The AWS account will only be available during the workshop — back up any materials you want to keep
- All workshop content is available in the public [AgentCore CLI](https://github.com/aws/agentcore-cli) repository on GitHub

## Workshop Studio AWS Account access

1. Follow the link provided by the instructor or use the 12-digit access code
2. Sign in via Workshop Studio, choose "Email one-time password (OTP)"
3. Enter your email, receive the passcode by email, and sign in
4. Review the terms and conditions and click "Join event"
5. On the event page, choose "Open AWS console"
6. Verify you are in the correct region (check with your instructor)

## Local environment setup

Once you have access to the AWS account, set up your local environment:

### 1. Install latest AWS CLI
If you haven't installed AWS CLI yet, follow the [instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions) to install AWS CLI on your local machine.

### 2. Install Node.js 20.x or later

:::code{language=bash}
node --version  # Should be v20.x or later
:::

If you have an older version or Node.js is not installed, download from https://nodejs.org/ or use a version manager:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
# Using nvm
nvm install 20
nvm use 20

# Verify
node --version
```
:::
:::tab{label="Windows"}
```powershell
# Using nvm-windows (https://github.com/coreybutler/nvm-windows)
nvm install 20
nvm use 20

# Verify
node --version

```
:::
::::

### 3. Install uv (Python package manager)

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```
:::
:::tab{label="Windows"}
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version

```
:::
::::

### 4. Install AgentCore CLI

:::code{language=bash}
npm install -g @aws/agentcore

# Verify
agentcore --version
:::

> **Note:** If you previously installed the `bedrock-agentcore-starter-toolkit`, uninstall it first to avoid conflicts:
:::code{language=bash}

uv tool uninstall bedrock-agentcore-starter-toolkit

# or
pip uninstall bedrock-agentcore-starter-toolkit -y
:::

### 5. Install Kiro IDE

Download and install Kiro from https://kiro.dev/downloads/

After installing, open Kiro and launch the integrated terminal where you'll run all workshop commands:

- **macOS:** Press `` Cmd+` `` (backtick)
- **Windows/Linux:** Press `` Ctrl+` `` (backtick)
- **Or:** Go to the menu **View → Terminal**

> **Tip:** You can also describe what you want to do in natural language in Kiro's chat, and it will suggest the terminal command for you. See [Terminal integration](https://kiro.dev/docs/chat/terminal) for details.

All commands from this point forward should be run in Kiro's integrated terminal.

### 6. Configure AWS credentials
Click on the `Get AWS CLI credentials` option in your workshop left-hand side menu:
![Step 1](/static/10-intro/GetAWSCLICredentials.png)

Copy the temporary credentials from Workshop Studio:
![Step 2](/static/10-intro/CopyCredentials.png)

And past them in your terminal:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_SESSION_TOKEN=<your-session-token>
export AWS_DEFAULT_REGION=<your-region>
```
:::
:::tab{label="Windows"}
```powershell
$env:AWS_ACCESS_KEY_ID = "<your-access-key>"
$env:AWS_SECRET_ACCESS_KEY = "<your-secret-key>"
$env:AWS_SESSION_TOKEN = "<your-session-token>"
$env:AWS_DEFAULT_REGION = "<your-region>"

```
:::
::::

### 7. Verify setup

:::code{language=bash}
# Check AWS credentials
aws sts get-caller-identity

# Check AgentCore CLI
agentcore --help

# Check Node.js
node --version

# Check uv
uv --version
:::

You are now ready to start Lab 1!

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
