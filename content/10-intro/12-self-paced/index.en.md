---
title: "Self paced"
weight: 12
---

# Prerequisites — Self-Paced

Instructions for running the AgentCore CLI Workshop in your own AWS account.

## Cost of the workshop

⚠️ **Important:** Running this workshop in your own environment will incur costs. Examples include Amazon Bedrock inference costs, AgentCore Runtime, Memory, and Gateway resources, and CloudFormation/CDK deployments. We recommend checking the official pricing pages, monitoring costs, and tearing down all resources when finished.

## Requirements

### Local machine

| Requirement | Minimum version | Check command |
|-------------|----------------|---------------|
| **Node.js** | 20.x | `node --version` |
| **uv** | 0.4+ | `uv --version` |
| **AWS CLI** | 2.x | `aws --version` |
| **Git** | 2.x | `git --version` |

### AWS account

- An AWS account with permissions to create IAM roles, Lambda functions, CloudFormation stacks, and AgentCore resources
- Amazon Bedrock model access enabled for your chosen model (default: Claude Sonnet 4.5 via Bedrock)

## Setup

### 1. Install Node.js 20.x or later

Download from https://nodejs.org/ or use a version manager:

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

### 2. Install uv (Python package manager)

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

### 3. Install AgentCore CLI

:::code{language=bash}
npm install -g @aws/agentcore

# Verify
agentcore --version
:::

**Note:** If you previously installed the `bedrock-agentcore-starter-toolkit`, uninstall it first to avoid conflicts:

:::code{language=bash}
uv tool uninstall bedrock-agentcore-starter-toolkit

# or
pip uninstall bedrock-agentcore-starter-toolkit -y
:::

Then refresh your shell's command cache:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
hash -r
```
:::
:::tab{label="Windows"}
```powershell
# PowerShell doesn't cache commands — no action needed

```
:::
::::


### 4. Install Kiro IDE

Download and install Kiro from https://kiro.dev/downloads/

After installing, open Kiro and launch the integrated terminal where you'll run all workshop commands:

- **macOS:** Press `` Cmd+` `` (backtick)
- **Windows/Linux:** Press `` Ctrl+` `` (backtick)
- **Or:** Go to the menu **View → Terminal**

**Tip:** You can also describe what you want to do in natural language in Kiro's chat, and it will suggest the terminal command for you. See [Terminal integration](https://kiro.dev/docs/chat/terminal) for details.

All commands from this point forward should be run in Kiro's integrated terminal.

### 5. Configure AWS credentials

Configure your AWS CLI with credentials that have the required permissions:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws configure
# Or use environment variables:
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=us-east-1
```
:::
:::tab{label="Windows"}
```powershell
aws configure
# Or use environment variables:
$env:AWS_ACCESS_KEY_ID = "<your-access-key>"
$env:AWS_SECRET_ACCESS_KEY = "<your-secret-key>"
$env:AWS_DEFAULT_REGION = "us-east-1"

```
:::
::::

### 6. Verify setup

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

## IAM Policy

Your IAM user or role needs the following permissions. You can create a custom policy with these statements:

:::code{language=json}
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CoreAWSServices",
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "cloudwatch:*",
                "lambda:*",
                "logs:*",
                "s3:*",
                "ecr:*",
                "sts:*",
                "tag:*",
                "codebuild:*",
                "ssm:*",
                "secretsmanager:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockAgentCorePermission",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:Get*",
                "bedrock-agentcore:List*",
                "bedrock-agentcore:Delete*",
                "bedrock-agentcore:Create*",
                "bedrock-agentcore:Retrieve*",
                "bedrock-agentcore:Invoke*",
                "bedrock-agentcore:UpdateAgentRuntime"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockAgentCoreWorkloadAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockAgentCoreObservability",
            "Effect": "Allow",
            "Action": [
                "application-signals:StartDiscovery"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockModelAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:Get*",
                "bedrock:List*",
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:CountTokens",
                "bedrock:TagResource",
                "bedrock:UntagResource"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECRAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer",
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:*"
            ],
            "Resource": [
                "arn:aws:iam::*:role/*",
                "arn:aws:iam::*:policy/*"
            ]
        },
        {
            "Sid": "PassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::*:role/*"
        }
    ]
}
:::

### Trust Policy (for the execution role)

:::code{language=json}
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudformation.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
:::

## Deploy the Prerequisites CloudFormation Stack

This stack creates the resources needed for later labs (Cognito for identity, a Lambda function for the Gateway lab, and SSM parameters used throughout the workshop).

Click the button below to open the AWS CloudFormation console with the stack ready to create:

:button[Launch Stack]{href="https://console.aws.amazon.com/cloudformation/home#/stacks/create/review?stackName=agentcore-workshop-prereqs&templateURL=https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/c770f35f-90a9-4e02-8985-4ef912bddb77/prereqs.yaml" variant="primary" iconName="external" iconAlign="right"}

1. Review the pre-filled parameters (the defaults are fine for this workshop)
2. Scroll to the bottom, check the **I acknowledge that AWS CloudFormation might create IAM resources with custom names** checkbox
3. Click **Create stack**
4. Wait for the stack status to reach **CREATE_COMPLETE** (this takes ~2 minutes)

You can verify the stack created successfully:

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws cloudformation describe-stacks \
  --stack-name agentcore-workshop-prereqs \
  --query 'Stacks[0].StackStatus' --output text
```
:::
:::tab{label="Windows"}
```powershell
aws cloudformation describe-stacks `
  --stack-name agentcore-workshop-prereqs `
  --query 'Stacks[0].StackStatus' --output text

```
:::
::::

## Enable Transaction Search (for Observability)

This is a one-time prerequisite to view observability metrics in CloudWatch:

**Option A: Via Console**

1. Navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. In the left panel, find **GenAI Observability** → **Bedrock AgentCore**
3. Click **Configure** which navigates to the X-Ray Transaction Search page
4. Enable Transaction Search

![CloudWatch GenAI Observability console showing the Configure button for Transaction Search](/static/images/cloudwatch-transaction-search-configure.png)

Toggle **Enable Transaction Search** and click **Save**:

![X-Ray Transaction Search enable toggle](/static/images/xray-enable-transaction-search.png)

**Option B: Via AWS CLI**

::::tabs{variant="container" groupId="os"}
:::tab{label="macOS/Linux"}
```bash
aws xray update-indexing-rule \
  --region us-east-1 \
  --name Default \
  --rule '{"Probabilistic": {"DesiredSamplingPercentage": 100}}'
```
:::
:::tab{label="Windows"}
```powershell
aws xray update-indexing-rule `
  --region us-east-1 `
  --name Default `
  --rule '{"Probabilistic": {"DesiredSamplingPercentage": 100}}'

```
:::
::::

To verify it was enabled:

:::code{language=bash}
aws xray get-indexing-rules --region us-east-1
:::

The `DesiredSamplingPercentage` should be `100.0`.

**Congrats! You are now ready to start Lab 1!**
