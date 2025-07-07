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

## Agent Lifecycle and Communication

### Agent Registration
1. **Initialization**: Agent creates an `AgentCard` with capabilities and metadata
2. **Registration**: Agent registers with the discovery system via API or direct registry call
3. **Heartbeat**: Agent begins sending periodic heartbeat signals to maintain "active" status

### Heartbeat Mechanism
The heartbeat system ensures agents remain discoverable and healthy:

```python
# Agents send heartbeats periodically (every few seconds)
if self.is_registered and self.registry:
    self.registry.update_agent_heartbeat(self.agent_id)
```

**Purpose:**
- **Health Check**: Signals agent is still alive and functioning
- **Registry Updates**: Keeps `last_seen` timestamp current
- **Failure Detection**: Agents without recent heartbeats are considered offline
- **Discovery Filtering**: Only active agents are returned in discovery requests

**Flow:**
1. Agent starts → registers → begins sending heartbeats
2. Registry tracks: "Agent X was last seen at 2024-01-15 10:30:45"
3. If heartbeats stop for 5+ minutes → agent considered offline
4. Discovery API filters out offline agents

### Message Handling
Agents communicate through a message-based system:

```python
# Register message handlers
agent.register_message_handler(MessageType.TASK_REQUEST, handle_task)
agent.register_message_handler(MessageType.HEARTBEAT, handle_heartbeat)

# Process incoming messages
messages = await agent.receive_messages()
for message in messages:
    await agent.process_message(message)
```

**Message Types:**
- `HEARTBEAT`: Health check signals
- `TASK_REQUEST`: Task execution requests
- `TASK_RESPONSE`: Task completion results
- `DISCOVERY_REQUEST`: Agent discovery queries
- `REGISTRATION`: Agent registration events

### Task Execution
Agents can execute tasks based on their capabilities:

```python
# Register task handlers for specific capabilities
agent.register_task_handler(CapabilityType.TEXT_PROCESSING, process_text)
agent.register_task_handler(CapabilityType.DATA_ANALYSIS, analyze_data)

# Tasks are automatically routed to appropriate handlers
result = await agent.execute_task(task)
```

**Task Flow:**
1. Task request received via message
2. Agent checks if it has required capabilities
3. If capable, executes task using registered handler
4. Sends response with results or error
5. Updates performance metrics (success rate, response time)

### Agent Discovery
The discovery system enables agents to find each other:

```python
# Find agents with specific capabilities
result = registry.discover_agents([
    CapabilityType.TEXT_PROCESSING,
    CapabilityType.DATA_ANALYSIS
], location="us-east-1", max_results=5)
```

**Discovery Process:**
1. Client sends discovery request with required capabilities
2. Request queued in SQS for processing
3. Discovery processor queries registry
4. Filters agents by capabilities, location, and active status
5. Returns matching agents with metadata

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
│   ├── base_agent.py      # Base agent class with common functionality
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
├── registry/              # Registry utilities
│   └── registry.py        # Registry operations
└── tests/                 # Comprehensive test suite
    ├── test_discovery.py  # Discovery system tests
    ├── test_protocol.py   # Protocol tests
    ├── test_registry.py   # Registry tests
    └── test_base_agent.py # Base agent tests
```

## API Endpoints

### Discovery API
- `GET /agents` - Discover agents with optional capability filters
- `POST /agents` - Register a new agent
- `GET /agents/{agent_id}` - Get specific agent details
- `DELETE /agents/{agent_id}` - Deregister an agent

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

### Creating New Agents
1. Extend the `BaseAgent` class:
```python
class MyAgent(BaseAgent):
    async def initialize(self):
        # Agent-specific initialization
        pass
    
    async def cleanup(self):
        # Agent-specific cleanup
        pass
    
    async def process_text(self, text):
        # Custom text processing logic
        return processed_text
```

2. Register capabilities and handlers:
```python
agent = MyAgent(
    name="TextProcessor",
    description="Processes text data",
    capabilities=[
        Capability(type=CapabilityType.TEXT_PROCESSING, 
                  name="TextProc", 
                  description="Text processing")
    ]
)

agent.register_task_handler(CapabilityType.TEXT_PROCESSING, agent.process_text)
```

3. Start the agent:
```python
await agent.initialize()
await agent.start()  # Runs message processing loop
```

### Customizing Discovery Logic
1. Modify `discovery_processor.py` for custom matching algorithms
2. Update capability types in `protocol/a2a_protocol.py`
3. Add new message types as needed

### Performance Monitoring
Agents automatically track:
- Tasks completed/failed
- Success rate
- Average response time
- Message processing metrics

## Testing

Run the comprehensive test suite:
```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_discovery.py
python -m pytest tests/test_protocol.py
python -m pytest tests/test_registry.py

# Run with coverage
python -m pytest --cov=.
```

**Test Coverage:**
- Discovery API functionality
- Agent registration and deregistration
- Message handling and routing
- Task execution and response
- Protocol validation
- Registry operations
- Integration scenarios

## System Benefits

### Scalability
- **Serverless**: Lambda functions scale automatically
- **Queue-based**: SQS handles message buffering and retry
- **NoSQL**: DynamoDB scales with data volume

### Reliability
- **Message Persistence**: SQS ensures no message loss
- **Heartbeat Monitoring**: Automatic failure detection
- **Error Handling**: Comprehensive error recovery

### Flexibility
- **Capability-based**: Agents can handle multiple task types
- **Protocol-driven**: Standardized communication format
- **Extensible**: Easy to add new agent types and capabilities

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 