# A2A - Agent-to-Agent Communication System

A comprehensive AWS-based system for agent discovery, registration, and communication.

## Overview

This system enables autonomous agents to:
- Register themselves with a central registry
- Discover other agents based on capabilities and requirements
- Communicate asynchronously through a reliable messaging system
- Execute tasks collaboratively

## Architecture

The system consists of several key components:

### Core Components
- **Agent Registry**: DynamoDB-based registry for agent metadata and capabilities
- **Discovery API**: RESTful API for agent discovery and registration
- **Message Queue**: SQS-based messaging system for agent communication
- **Task Management**: System for task distribution and execution

### Infrastructure
- **API Gateway**: REST API endpoints for discovery and registration
- **Lambda Functions**: Serverless compute for API handling and processing
- **DynamoDB**: NoSQL database for agent registry and discovery requests
- **SQS**: Message queues for agent communication and discovery requests

## Quick Start

### Prerequisites
- AWS CLI installed and configured
- Node.js 18+ and Python 3.9+
- CDK CLI installed globally

### Deployment
```bash
# Install dependencies
pip install -r requirements.txt
cd infra/cdk
npm install
pip install -r requirements.txt

# Deploy infrastructure
./deploy.sh
```

### Running Agents
```bash
# Start a discovery agent
python agents/discovery_agent.py

# Test the discovery system
python discovery/test_discovery.py
```

## Project Structure

```
A2A/
├── agents/                 # Agent implementations
│   ├── agent_template.py   # Base agent template
│   └── discovery_agent.py  # Discovery agent example
├── discovery/              # Discovery system components
│   ├── discovery_api.py    # Discovery API Lambda handler
│   ├── discovery_processor.py  # Discovery processing logic
│   ├── agent_registration.py   # Agent registration handler
│   └── test_discovery.py   # Test scripts
├── infra/                  # Infrastructure as Code
│   └── cdk/               # CDK deployment
│       ├── agent_stack.py # Main infrastructure stack
│       ├── app.py         # CDK app entry point
│       └── deploy.sh      # Deployment script
├── protocol/              # Communication protocols
│   ├── a2a_protocol.py    # Protocol definitions
│   ├── agent_card.py      # Agent metadata structure
│   ├── message.py         # Message formats
│   └── task.py           # Task definitions
└── registry/              # Registry utilities
    └── registry.py        # Registry operations
```

## API Endpoints

### Discovery API
- `POST /discovery/register` - Register an agent
- `GET /discovery/agents` - List all agents
- `POST /discovery/request` - Request agent discovery
- `GET /discovery/request/{request_id}` - Get discovery results

### Agent Communication
- `POST /agents/message` - Send message to agent
- `GET /agents/message/{agent_id}` - Get messages for agent

## Configuration

Environment variables:
- `AWS_REGION`: AWS region for deployment
- `DISCOVERY_TABLE`: DynamoDB table for agent registry
- `DISCOVERY_QUEUE`: SQS queue for discovery requests
- `AGENT_QUEUE`: SQS queue for agent messages

## Development

### Adding New Agents
1. Extend the `AgentTemplate` class
2. Implement required methods
3. Register with the discovery system
4. Handle incoming messages

### Customizing Discovery Logic
1. Modify `discovery_processor.py`
2. Update matching algorithms
3. Add new capability types

## Testing

Run the test suite:
```bash
python discovery/test_discovery.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 