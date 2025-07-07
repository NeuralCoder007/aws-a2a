"""
Pytest configuration and fixtures for A2A tests.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test-access-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }):
        yield


@pytest.fixture
def mock_boto3_clients():
    """Mock all boto3 clients used in the application."""
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource:
        
        # Mock SQS client
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'https://sqs.test.com/queue'}
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        mock_sqs.receive_message.return_value = {'Messages': []}
        
        # Mock DynamoDB resource
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        
        # Configure mock_client to return different clients based on service name
        def get_client(service_name, **kwargs):
            if service_name == 'sqs':
                return mock_sqs
            elif service_name == 'dynamodb':
                return Mock()
            elif service_name == 'lambda':
                return Mock()
            else:
                return Mock()
        
        mock_client.side_effect = get_client
        
        yield {
            'sqs': mock_sqs,
            'table': mock_table,
            'client': mock_client,
            'resource': mock_resource
        }


@pytest.fixture
def sample_agent_card():
    """Sample agent card for testing."""
    from ..protocol import AgentCard, Capability, CapabilityType
    
    capabilities = [
        Capability(
            type=CapabilityType.TEXT_PROCESSING,
            name="Text Processing",
            description="Processes text content",
            parameters={"max_length": 1000},
            version="1.0.0",
            confidence=0.95
        ),
        Capability(
            type=CapabilityType.DATA_ANALYSIS,
            name="Data Analysis",
            description="Analyzes data sets",
            parameters={"max_rows": 10000},
            version="1.0.0",
            confidence=0.9
        )
    ]
    
    return AgentCard(
        agent_id="test-agent-001",
        name="Test Agent",
        description="A test agent for unit testing",
        version="1.0.0",
        capabilities=capabilities,
        contact_info={"email": "test@example.com"},
        location="us-east-1",
        tags=["test", "unit-test"]
    )


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    from ..protocol import Task, CapabilityType, TaskPriority
    
    return Task(
        task_id="task-001",
        title="Test Task",
        description="A test task for unit testing",
        required_capabilities=[CapabilityType.TEXT_PROCESSING],
        parameters={"text": "Hello world", "operation": "analyze"},
        priority=TaskPriority.NORMAL,
        created_by="test-agent",
        assigned_to="worker-agent"
    )


@pytest.fixture
def sample_message():
    """Sample message for testing."""
    from ..protocol import Message, MessageType
    
    return Message(
        message_id="msg-001",
        message_type=MessageType.TASK_REQUEST,
        sender_id="sender-agent",
        recipient_id="recipient-agent",
        payload={"task": "data"},
        correlation_id="corr-001",
        reply_to="reply-queue"
    )


@pytest.fixture
def sample_discovery_request():
    """Sample discovery request for testing."""
    from ..protocol import DiscoveryRequest, CapabilityType
    
    return DiscoveryRequest(
        request_id="req-001",
        required_capabilities=[CapabilityType.TEXT_PROCESSING],
        optional_capabilities=[CapabilityType.DATA_ANALYSIS],
        location_preference="us-east-1",
        max_results=5,
        timeout_seconds=60
    )


@pytest.fixture
def mock_registry():
    """Mock agent registry for testing."""
    with patch('..registry.AgentRegistry') as mock_registry_class:
        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry
        
        # Configure default successful responses
        mock_registry.register_agent.return_value = {
            'success': True,
            'agent_id': 'test-agent-001',
            'message': 'Agent registered successfully'
        }
        
        mock_registry.discover_agents.return_value = {
            'success': True,
            'agents': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'capability_types': ['text_processing'],
                    'status': 'active'
                }
            ],
            'total_found': 1,
            'scanned_count': 1
        }
        
        mock_registry.get_agent.return_value = {
            'agent_id': 'test-agent-001',
            'name': 'Test Agent',
            'description': 'A test agent'
        }
        
        mock_registry.update_agent.return_value = {
            'success': True,
            'message': 'Agent updated successfully'
        }
        
        mock_registry.deregister_agent.return_value = {
            'success': True,
            'message': 'Agent deregistered successfully'
        }
        
        yield mock_registry


@pytest.fixture
def mock_sqs_queue():
    """Mock SQS queue for testing."""
    with patch('boto3.client') as mock_boto3:
        mock_sqs = Mock()
        mock_boto3.return_value = mock_sqs
        
        # Configure queue URL
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        }
        
        # Configure message sending
        mock_sqs.send_message.return_value = {
            'MessageId': 'test-message-id',
            'MD5OfMessageBody': 'test-md5'
        }
        
        # Configure message receiving
        mock_sqs.receive_message.return_value = {
            'Messages': [
                {
                    'MessageId': 'msg-001',
                    'ReceiptHandle': 'test-receipt',
                    'Body': '{"test": "message"}'
                }
            ]
        }
        
        yield mock_sqs


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table for testing."""
    with patch('boto3.resource') as mock_boto3:
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        # Configure table operations
        mock_table.put_item.return_value = {
            'ConsumedCapacity': {
                'TableName': 'test-table',
                'CapacityUnits': 1.0
            }
        }
        
        mock_table.get_item.return_value = {
            'Item': {
                'agent_id': 'test-agent-001',
                'name': 'Test Agent',
                'description': 'A test agent'
            }
        }
        
        mock_table.update_item.return_value = {
            'Attributes': {
                'agent_id': 'test-agent-001',
                'name': 'Updated Agent'
            }
        }
        
        mock_table.delete_item.return_value = {
            'ConsumedCapacity': {
                'TableName': 'test-table',
                'CapacityUnits': 1.0
            }
        }
        
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'capability_types': ['text_processing'],
                    'status': 'active'
                }
            ],
            'ScannedCount': 1,
            'Count': 1
        }
        
        yield mock_table


@pytest.fixture
def test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        'AWS_DEFAULT_REGION': 'us-east-1',
        'DISCOVERY_TABLE_NAME': 'test-discovery-table',
        'AGENT_REGISTRY_TABLE': 'test-registry-table',
        'DISCOVERY_QUEUE_URL': 'https://sqs.test.com/discovery-queue',
        'AGENT_MESSAGE_QUEUE_URL': 'https://sqs.test.com/agent-queue',
        'LOG_LEVEL': 'DEBUG'
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "aws: mark test as requiring AWS services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Add AWS marker to tests that use AWS services
        if any(marker in item.name.lower() for marker in ['aws', 'boto', 'dynamo', 'sqs', 'lambda']):
            item.add_marker(pytest.mark.aws)
        
        # Add slow marker to tests that might be slow
        if any(marker in item.name.lower() for marker in ['integration', 'flow', 'full']):
            item.add_marker(pytest.mark.slow) 