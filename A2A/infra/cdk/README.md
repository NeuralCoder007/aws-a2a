# Agent Discovery CDK Infrastructure

This directory contains the AWS CDK stack for deploying the agent discovery system, including:
- DynamoDB table for agent registry
- SQS queues for discovery and agent messaging
- Lambda functions for API, discovery processing, and agent registration
- API Gateway for agent discovery endpoints

## Usage

```bash
cd infra/cdk
pip install -r requirements.txt
cdk bootstrap
cdk deploy --require-approval never
```

## Files
- `agent_stack.py`: Main CDK stack definition
- `app.py`: CDK app entry point
- `cdk.json`: CDK configuration
- `deploy.sh`: Deployment script
- `requirements.txt`: Python dependencies for CDK 