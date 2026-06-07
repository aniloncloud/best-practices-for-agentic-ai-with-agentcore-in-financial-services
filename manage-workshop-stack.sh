#!/bin/bash -x
# Workshop bootstrap script for AWS Workshop Studio
# Runs via CodeBuild to handle account-level setup (CDK bootstrap, etc.)

STACK_OPERATION="$1"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_DEFAULT_REGION:-us-west-2}

if [[ "$STACK_OPERATION" == "create" || "$STACK_OPERATION" == "update" ]]; then
    echo "INFO: Bootstrapping CDK in account ${AWS_ACCOUNT_ID}, region ${AWS_REGION}"

    # Install Node.js and CDK
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    yum install -y nodejs || true
    npm install -g aws-cdk

    # CDK bootstrap
    cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION}

    echo "INFO: Bootstrap complete"

elif [ "$STACK_OPERATION" == "delete" ]; then
    echo "INFO: Cleaning up workshop resources in account ${AWS_ACCOUNT_ID}, region ${AWS_REGION}"

    # Delete any AgentCore CDK stacks deployed by participants
    for stack in $(aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
        --query "StackSummaries[?contains(StackName,'AgentCore') || contains(StackName,'PortfolioAdvisor')].StackName" \
        --output text --region ${AWS_REGION} 2>/dev/null); do
        echo "Deleting stack: ${stack}"
        aws cloudformation delete-stack --stack-name "${stack}" --region ${AWS_REGION}
        aws cloudformation wait stack-delete-complete --stack-name "${stack}" --region ${AWS_REGION} || true
    done

    # Delete CDK bootstrap stack
    echo "Deleting CDKToolkit stack"
    aws cloudformation delete-stack --stack-name CDKToolkit --region ${AWS_REGION}
    aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region ${AWS_REGION} || true

    echo "INFO: Cleanup complete"
else
    echo "ERROR: Invalid stack operation: ${STACK_OPERATION}"
    exit 1
fi
