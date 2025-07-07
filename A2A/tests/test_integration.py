"""
Integration tests for the A2A Agent Discovery System.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock

from protocol import (
    AgentCard, Capability, CapabilityType, Task, TaskStatus,
    Message, MessageType, DiscoveryRequest
)
from registry import AgentRegistry
from agents.base_agent import BaseAgent


# Minimal concrete subclass for integration tests
class TestAgent(BaseAgent):
    async def initialize(self):
        pass
    async def cleanup(self):
        pass


class TestSystemIntegration:
    """Test the complete system integration."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_agent_registration_and_discovery_flow(self, mock_boto3_clients, test_environment):
        """Test complete flow: agent registration -> discovery -> task execution."""
        
        # Step 1: Create and register an agent
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text content"
            )
        ]
        
        agent = TestAgent(
            name="Integration Test Agent",
            description="An agent for integration testing",
            capabilities=capabilities,
            registry_table="test-registry",
            message_queue="test-queue",
            success_rate=1.0
        )
        
        # Mock registry for registration
        with patch('registry.AgentRegistry') as mock_registry_class:
            mock_registry = Mock()
            mock_registry.register_agent.return_value = {
                'success': True,
                'agent_id': agent.agent_id,
                'message': 'Agent registered successfully'
            }
            mock_registry_class.return_value = mock_registry
            
            # Register the agent
            registration_result = await agent.register()
            assert registration_result is True
            assert agent.is_registered is True
            
            # Verify registry was called
            mock_registry.register_agent.assert_called_once()
        
        # Step 2: Test agent discovery
        with patch('registry.AgentRegistry') as mock_registry_class:
            mock_registry = Mock()
            mock_registry.discover_agents.return_value = {
                'success': True,
                'agents': [
                    {
                        'agent_id': agent.agent_id,
                        'name': agent.name,
                        'description': agent.description,
                        'capability_types': ['text_processing'],
                        'status': 'active'
                    }
                ],
                'total_found': 1,
                'scanned_count': 1
            }
            mock_registry_class.return_value = mock_registry
            
            # Create discovery request
            discovery_request = DiscoveryRequest(
                required_capabilities=[CapabilityType.TEXT_PROCESSING],
                location_preference="us-east-1",
                max_results=5
            )
            
            # Discover agents
            discovery_result = mock_registry.discover_agents(
                required_capabilities=discovery_request.required_capabilities,
                location=discovery_request.location_preference,
                max_results=discovery_request.max_results
            )
            
            assert discovery_result['success'] is True
            assert discovery_result['total_found'] == 1
            assert len(discovery_result['agents']) == 1
            assert discovery_result['agents'][0]['agent_id'] == agent.agent_id
        
        # Step 3: Test task execution
        task = Task(
            title="Integration Test Task",
            description="A task for integration testing",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            parameters={"text": "Hello integration test!"},
            created_by="test-client",
            success_rate=1.0
        )
        
        # Register a task handler
        async def text_processing_handler(params):
            return {
                "processed_text": params.get("text", "").upper(),
                "word_count": len(params.get("text", "").split()),
                "status": "completed"
            }
        
        agent.register_task_handler(CapabilityType.TEXT_PROCESSING, text_processing_handler)
        
        # Execute the task
        task_result = await agent.execute_task(task)
        
        assert task_result['success'] is True
        assert task_result['result']['processed_text'] == "HELLO INTEGRATION TEST!"
        assert task_result['result']['word_count'] == 3
        assert agent.tasks_completed == 1
        assert agent.tasks_failed == 0
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_message_passing_between_agents(self, mock_boto3_clients, test_environment):
        """Test message passing between agents."""
        
        # Create two agents
        agent1 = TestAgent(
            name="Agent 1",
            description="First test agent",
            capabilities=[
                Capability(type=CapabilityType.TEXT_PROCESSING, name="Text", description="Text")
            ],
            message_queue="test-queue",
            success_rate=1.0
        )
        
        agent2 = TestAgent(
            name="Agent 2",
            description="Second test agent",
            capabilities=[
                Capability(type=CapabilityType.DATA_ANALYSIS, name="Data", description="Data")
            ],
            message_queue="test-queue",
            success_rate=1.0
        )
        
        # Register message handlers
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
            return True
        
        agent2.register_message_handler(MessageType.TASK_REQUEST, message_handler)
        
        # Send a message from agent1 to agent2
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id=agent1.agent_id,
            recipient_id=agent2.agent_id,
            payload={"task": "process_data", "data": "test_data"}
        )
        
        # Mock SQS for message sending
        mock_sqs = mock_boto3_clients['sqs']
        mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
        
        # Send message
        send_result = await agent1.send_message(message)
        assert send_result is True
        
        # Mock SQS for message receiving
        mock_sqs.receive_message.return_value = {
            'Messages': [
                {
                    'MessageId': 'msg-001',
                    'ReceiptHandle': 'receipt-001',
                    'Body': json.dumps({
                        'message_id': message.message_id,
                        'message_type': message.message_type,
                        'sender_id': message.sender_id,
                        'recipient_id': message.recipient_id,
                        'payload': message.payload
                    })
                }
            ]
        }
        
        # Receive and process message
        received = await agent2.receive_messages()
        assert len(received) == 1
        
        # Process the message
        process_result = await agent2.process_message(received[0])
        assert process_result is True
        assert len(received_messages) == 1
        assert received_messages[0].sender_id == agent1.agent_id
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_discovery_api_integration(self, mock_boto3_clients, test_environment):
        """Test discovery API integration."""
        
        from discovery.discovery_api import lambda_handler as discovery_api_handler
        
        # Test GET /agents endpoint
        get_event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing,data_analysis',
                'location': 'us-east-1',
                'limit': '3'
            }
        }
        
        mock_sqs = mock_boto3_clients['sqs']
        mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
        
        response = discovery_api_handler(get_event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'request_id' in body
        
        # Test POST /agents endpoint
        agent_data = {
            'name': 'API Test Agent',
            'description': 'Agent created via API',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ],
            'contact_info': {'email': 'api@test.com'},
            'location': 'us-east-1'
        }
        
        post_event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(agent_data)
        }
        
        response = discovery_api_handler(post_event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'agent_id' in body
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_registry_operations_integration(self, mock_boto3_clients, test_environment):
        """Test registry operations integration."""
        
        # Create registry
        registry = AgentRegistry("test-registry", "us-east-1")
        
        # Create agent card
        agent_card = AgentCard(
            name="Registry Test Agent",
            description="Agent for registry testing",
            capabilities=[
                Capability(
                    type=CapabilityType.TEXT_PROCESSING,
                    name="Text Processing",
                    description="Processes text"
                )
            ],
            success_rate=1.0
        )
        
        # Mock DynamoDB table
        mock_table = mock_boto3_clients['table']
        mock_table.put_item.return_value = {'ConsumedCapacity': {'CapacityUnits': 1.0}}
        mock_table.get_item.return_value = {
            'Item': {
                'agent_id': agent_card.agent_id,
                'name': agent_card.name,
                'description': agent_card.description,
                'capability_types': ['text_processing'],
                'status': 'active'
            }
        }
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': agent_card.agent_id,
                    'name': agent_card.name,
                    'capability_types': ['text_processing'],
                    'status': 'active'
                }
            ],
            'ScannedCount': 1,
            'Count': 1
        }
        
        # Test registration
        registration_result = registry.register_agent(agent_card)
        assert registration_result['success'] is True
        assert registration_result['agent_id'] == agent_card.agent_id
        
        # Test retrieval
        retrieved_agent = registry.get_agent(agent_card.agent_id)
        assert retrieved_agent is not None
        assert retrieved_agent['agent_id'] == agent_card.agent_id
        assert retrieved_agent['name'] == agent_card.name
        
        # Test discovery
        discovery_result = registry.discover_agents([CapabilityType.TEXT_PROCESSING])
        assert discovery_result['success'] is True
        assert discovery_result['total_found'] == 1
        assert len(discovery_result['agents']) == 1
        assert discovery_result['agents'][0]['agent_id'] == agent_card.agent_id
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_error_handling_integration(self, mock_boto3_clients, test_environment):
        """Test error handling across the system."""
        
        # Test agent with invalid capabilities
        agent = TestAgent(
            name="Error Test Agent",
            description="Agent for error testing",
            capabilities=[]  # Empty capabilities should cause issues
        )
        
        # Test task execution without handler
        task = Task(
            title="Error Test Task",
            description="A task that should fail",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            created_by="test-client",
            success_rate=1.0
        )
        
        task_result = await agent.execute_task(task)
        assert task_result['success'] is False
        assert "No handler found" in task_result['error']
        assert agent.tasks_failed == 1
        
        # Test message processing without handler
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id="test-sender"
        )
        
        process_result = await agent.process_message(message)
        assert process_result is False
        
        # Test registry with invalid data
        registry = AgentRegistry("test-registry", "us-east-1")
        
        invalid_agent_card = AgentCard(
            name="",  # Empty name should fail validation
            description="Invalid agent",
            capabilities=[]  # Empty capabilities should fail validation
        )
        
        registration_result = registry.register_agent(invalid_agent_card)
        assert registration_result['success'] is False
        assert 'errors' in registration_result
        assert len(registration_result['errors']) > 0


class TestPerformanceIntegration:
    """Test system performance under load."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_agent_registration(self, mock_boto3_clients, test_environment):
        """Test concurrent agent registration."""
        
        registry = AgentRegistry("test-registry", "us-east-1")
        mock_table = mock_boto3_clients['table']
        mock_table.put_item.return_value = {'ConsumedCapacity': {'CapacityUnits': 1.0}}
        
        # Create multiple agents
        agents = []
        for i in range(5):
            agent_card = AgentCard(
                name=f"Concurrent Agent {i}",
                description=f"Agent {i} for concurrent testing",
                capabilities=[
                    Capability(
                        type=CapabilityType.TEXT_PROCESSING,
                        name=f"Text Processing {i}",
                        description=f"Text processing capability {i}"
                    )
                ],
                success_rate=1.0
            )
            agents.append(agent_card)
        
        # Register agents concurrently
        async def register_agent(agent_card):
            return registry.register_agent(agent_card)
        
        tasks = [register_agent(agent_card) for agent_card in agents]
        results = await asyncio.gather(*tasks)
        
        # Verify all registrations succeeded
        for result in results:
            assert result['success'] is True
        
        # Verify all agents were registered
        assert len(results) == 5
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_bulk_discovery_operations(self, mock_boto3_clients, test_environment):
        """Test bulk discovery operations."""
        
        registry = AgentRegistry("test-registry", "us-east-1")
        mock_table = mock_boto3_clients['table']
        
        # Mock multiple agents in scan results
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': f'agent-{i}',
                    'name': f'Agent {i}',
                    'capability_types': ['text_processing', 'data_analysis'],
                    'status': 'active'
                }
                for i in range(10)
            ],
            'ScannedCount': 10,
            'Count': 10
        }
        
        # Test discovery with different capability combinations
        discovery_requests = [
            [CapabilityType.TEXT_PROCESSING],
            [CapabilityType.DATA_ANALYSIS],
            [CapabilityType.TEXT_PROCESSING, CapabilityType.DATA_ANALYSIS]
        ]
        
        for capabilities in discovery_requests:
            result = registry.discover_agents(capabilities)
            assert result['success'] is True
            assert result['total_found'] == 10
            assert len(result['agents']) == 10


class TestSecurityIntegration:
    """Test security aspects of the system."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_input_validation_integration(self, mock_boto3_clients, test_environment):
        """Test input validation across the system."""
        
        from discovery.discovery_api import lambda_handler as discovery_api_handler
        
        # Test malicious input in API
        malicious_event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing; DROP TABLE agents; --',
                'location': 'us-east-1'
            }
        }
        
        response = discovery_api_handler(malicious_event, None)
        assert response['statusCode'] == 400
        
        # Test oversized payload
        oversized_payload = {
            'name': 'A' * 10000,  # Very long name
            'description': 'A' * 50000,  # Very long description
            'capabilities': []
        }
        
        oversized_event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(oversized_payload)
        }
        
        response = discovery_api_handler(oversized_event, None)
        assert response['statusCode'] == 400
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_authentication_integration(self, mock_boto3_clients, test_environment):
        """Test authentication and authorization."""
        
        # Test agent registration with invalid credentials
        agent = TestAgent(
            name="Auth Test Agent",
            description="Agent for auth testing",
            capabilities=[
                Capability(
                    type=CapabilityType.TEXT_PROCESSING,
                    name="Text Processing",
                    description="Processes text"
                )
            ],
            registry_table="test-registry"
        )
        
        # Mock registry to simulate authentication failure
        with patch('registry.AgentRegistry') as mock_registry_class:
            from botocore.exceptions import ClientError
            error_response = {'Error': {'Code': 'UnauthorizedOperation'}}
            mock_registry = Mock()
            mock_registry.register_agent.side_effect = ClientError(error_response, 'RegisterAgent')
            mock_registry_class.return_value = mock_registry
            
            registration_result = await agent.register()
            assert registration_result is False 