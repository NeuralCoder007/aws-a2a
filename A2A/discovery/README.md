# Discovery System

This directory contains the Lambda handlers and logic for agent discovery, registration, and processing in the A2A system.

## Components

- `discovery_api.py`: Handles API Gateway requests for agent registration, discovery, and listing agents.
- `discovery_processor.py`: Processes discovery requests from SQS, matches agents, and sends responses.
- `agent_registration.py`: Handles agent registration events from SQS and updates the registry.
- `test_discovery.py`: Test script for the discovery system.

## Usage

These handlers are deployed as AWS Lambda functions and connected to API Gateway and SQS queues by the CDK infrastructure.

## Environment Variables
- `DISCOVERY_TABLE`: Name of the DynamoDB table for agent registry
- `AWS_REGION`: AWS region

## Testing

Run the test script:
```bash
python test_discovery.py
``` 