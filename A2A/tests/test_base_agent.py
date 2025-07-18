"""
Unit tests for the BaseAgent class.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from agents.base_agent import BaseAgent
from protocol import Capability, CapabilityType, Message, MessageType, Task, TaskStatus

class IncompleteAgent(BaseAgent):
    """A test agent that does not implement abstract methods."""
    pass

class TestAgent(BaseAgent):
    """A test agent that implements abstract methods."""
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass

class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    @patch('boto3.client')
    def test_base_agent_initialization(self, mock_boto3_client):
        """Test basic agent initialization."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert len(agent.capabilities) == 1
        assert agent.capabilities[0].type == CapabilityType.TEXT_PROCESSING
        assert agent.agent_id is not None
        assert agent.is_running is False
        assert agent.is_registered is False
    
    @patch('boto3.client')
    def test_base_agent_initialization_no_queue(self, mock_boto3_client):
        """Test agent initialization without message queue."""
        capabilities = [
            Capability(
                type=CapabilityType.DATA_ANALYSIS,
                name="Data Analysis",
                description="Analyzes data"
            )
        ]
        
        agent = TestAgent(
            name="Data Agent",
            description="A data analysis agent",
            capabilities=capabilities
        )
        
        assert agent.message_queue_url is None
    
    @patch('boto3.client')
    def test_create_agent_card(self, mock_boto3_client):
        """Test agent card creation."""
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        card = agent.create_agent_card()
        
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert len(card.capabilities) == 1
        assert card.capabilities[0].type == CapabilityType.TEXT_PROCESSING
        assert card.agent_id == agent.agent_id
    
    @patch('boto3.client')
    def test_calculate_success_rate(self, mock_boto3_client):
        """Test success rate calculation."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Test with no tasks
        assert agent._calculate_success_rate() == 1.0
        
        # Test with completed tasks
        agent.tasks_completed = 8
        agent.tasks_failed = 2
        assert agent._calculate_success_rate() == 0.8
        
        # Test with only failed tasks
        agent.tasks_completed = 0
        agent.tasks_failed = 5
        assert agent._calculate_success_rate() == 0.0
    
    @patch('boto3.client')
    def test_calculate_average_response_time(self, mock_boto3_client):
        """Test average response time calculation."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Test with no response times
        assert agent._calculate_average_response_time() is None
        
        # Test with response times
        agent.response_times = [100, 200, 300]
        avg_time = agent._calculate_average_response_time()
        assert avg_time == 200
    
    @patch('boto3.client')
    @patch('..registry.AgentRegistry')
    async def test_register_success(self, mock_registry_class, mock_boto3_client):
        """Test successful agent registration."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        mock_registry = Mock()
        mock_registry.register_agent.return_value = {'success': True, 'agent_id': 'test-agent-001'}
        mock_registry_class.return_value = mock_registry
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            registry_table="test-registry"
        )
        
        result = await agent.register()
        
        assert result is True
        assert agent.is_registered is True
        mock_registry.register_agent.assert_called_once()
    
    @patch('boto3.client')
    @patch('..registry.AgentRegistry')
    async def test_register_failure(self, mock_registry_class, mock_boto3_client):
        """Test failed agent registration."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        mock_registry = Mock()
        mock_registry.register_agent.return_value = {'success': False, 'error': 'Registration failed'}
        mock_registry_class.return_value = mock_registry
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            registry_table="test-registry"
        )
        
        result = await agent.register()
        
        assert result is False
        assert agent.is_registered is False
    
    @patch('boto3.client')
    @patch('..registry.AgentRegistry')
    async def test_register_no_registry(self, mock_registry_class, mock_boto3_client):
        """Test registration without registry configured."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        result = await agent.register()
        
        assert result is False
        assert agent.is_registered is False
    
    @patch('boto3.client')
    @patch('..registry.AgentRegistry')
    async def test_deregister_success(self, mock_registry_class, mock_boto3_client):
        """Test successful agent deregistration."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        mock_registry = Mock()
        mock_registry.deregister_agent.return_value = {'success': True}
        mock_registry_class.return_value = mock_registry
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            registry_table="test-registry"
        )
        agent.is_registered = True
        
        result = await agent.deregister()
        
        assert result is True
        assert agent.is_registered is False
        mock_registry.deregister_agent.assert_called_once()
    
    @patch('boto3.client')
    async def test_send_message_success(self, mock_boto3_client):
        """Test successful message sending."""
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            message_queue="test-queue"
        )
        agent.message_queue_url = "https://sqs.test.com/queue"
        
        message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        
        result = await agent.send_message(message)
        
        assert result is True
        mock_sqs.send_message.assert_called_once()
    
    @patch('boto3.client')
    async def test_send_message_no_queue(self, mock_boto3_client):
        """Test message sending without queue configured."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        
        result = await agent.send_message(message)
        
        assert result is False
    
    @patch('boto3.client')
    async def test_receive_messages_success(self, mock_boto3_client):
        """Test successful message receiving."""
        mock_sqs = Mock()
        mock_sqs.receive_message.return_value = {
            'Messages': [
                {
                    'Body': '{"message_type": "heartbeat", "sender_id": "test-agent"}',
                    'MessageId': 'msg-001'
                }
            ]
        }
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            message_queue="test-queue"
        )
        agent.message_queue_url = "https://sqs.test.com/queue"
        
        messages = await agent.receive_messages()
        
        assert len(messages) == 1
        assert messages[0].message_type == MessageType.HEARTBEAT
        assert messages[0].sender_id == "test-agent"
    
    @patch('boto3.client')
    async def test_receive_messages_no_queue(self, mock_boto3_client):
        """Test message receiving without queue configured."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        messages = await agent.receive_messages()
        
        assert messages == []
    
    @patch('boto3.client')
    async def test_process_message_success(self, mock_boto3_client):
        """Test successful message processing."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Register a test handler
        test_handler = AsyncMock()
        agent.message_handlers[MessageType.HEARTBEAT] = test_handler
        
        message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        
        result = await agent.process_message(message)
        
        assert result is True
        test_handler.assert_called_once_with(message)
        assert len(agent.response_times) == 1
    
    @patch('boto3.client')
    async def test_process_message_no_handler(self, mock_boto3_client):
        """Test message processing without handler."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id="test-agent"
        )
        
        result = await agent.process_message(message)
        
        assert result is False
    
    @patch('boto3.client')
    async def test_execute_task_success(self, mock_boto3_client):
        """Test successful task execution."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Register a test task handler
        test_handler = AsyncMock(return_value={"result": "success"})
        agent.task_handlers[CapabilityType.TEXT_PROCESSING] = test_handler
        
        task = Task(
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            created_by="test-agent"
        )
        
        result = await agent.execute_task(task)
        
        assert result['success'] is True
        assert result['result'] == {"result": "success"}
        assert agent.tasks_completed == 1
        assert len(agent.response_times) == 1
    
    @patch('boto3.client')
    async def test_execute_task_no_handler(self, mock_boto3_client):
        """Test task execution without handler."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        task = Task(
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.DATA_ANALYSIS],
            created_by="test-agent"
        )
        
        result = await agent.execute_task(task)
        
        assert result['success'] is False
        assert "No handler found" in result['error']
    
    @patch('boto3.client')
    async def test_execute_task_exception(self, mock_boto3_client):
        """Test task execution with exception."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Register a test task handler that raises an exception
        test_handler = AsyncMock(side_effect=Exception("Task failed"))
        agent.task_handlers[CapabilityType.TEXT_PROCESSING] = test_handler
        
        task = Task(
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            created_by="test-agent"
        )
        
        result = await agent.execute_task(task)
        
        assert result['success'] is False
        assert result['error'] == "Task failed"
        assert agent.tasks_failed == 1
    
    @patch('boto3.client')
    def test_register_message_handler(self, mock_boto3_client):
        """Test registering message handlers."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        test_handler = lambda msg: None
        
        agent.register_message_handler(MessageType.TASK_REQUEST, test_handler)
        
        assert MessageType.TASK_REQUEST in agent.message_handlers
        assert agent.message_handlers[MessageType.TASK_REQUEST] == test_handler
    
    @patch('boto3.client')
    def test_register_task_handler(self, mock_boto3_client):
        """Test registering task handlers."""
        mock_sqs = Mock()
        mock_boto3_client.return_value = mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent = TestAgent(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        test_handler = lambda params: {"result": "success"}
        
        agent.register_task_handler(CapabilityType.TEXT_PROCESSING, test_handler)
        
        assert CapabilityType.TEXT_PROCESSING in agent.task_handlers
        assert agent.task_handlers[CapabilityType.TEXT_PROCESSING] == test_handler


class TestBaseAgentAbstractMethods:
    def test_base_agent_is_abstract(self):
        """Test that BaseAgent abstract methods raise NotImplementedError."""
        capabilities = [Capability(type=CapabilityType.TEXT_PROCESSING, name="Text Processing", description="Processes text")]
        agent = TestAgent(name="Test Agent", description="A test agent", capabilities=capabilities)
        
        # Test that abstract methods are implemented in TestAgent (should not raise)
        try:
            asyncio.run(agent.initialize())
            asyncio.run(agent.cleanup())
        except NotImplementedError:
            pytest.fail("TestAgent should implement abstract methods")
        
        # Test that we can't instantiate a class without implementing abstract methods
        # Note: This should raise TypeError, but some Python versions may allow it
        try:
            IncompleteAgent(name="Test Agent", description="A test agent", capabilities=capabilities)
            # If we get here, the test should fail because we expect an error
            pytest.fail("Expected TypeError when instantiating IncompleteAgent")
        except TypeError:
            # This is the expected behavior
            pass


class TestBedrockEnhancedAgent:
    """Test Bedrock-enhanced agent functionality."""
    
    @patch('boto3.client')
    def test_bedrock_enhanced_agent_initialization(self, mock_boto3_client):
        """Test Bedrock-enhanced agent initialization."""
        mock_sqs = Mock()
        mock_bedrock = Mock()
        mock_boto3_client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text with AI"
            )
        ]
        
        # Create a Bedrock-enhanced agent
        class BedrockTestAgent(TestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.bedrock_client = mock_bedrock
                self.ai_enhanced = True
        
        agent = BedrockTestAgent(
            name="AI Agent",
            description="An AI-enhanced agent",
            capabilities=capabilities
        )
        
        assert agent.name == "AI Agent"
        assert agent.ai_enhanced is True
        assert agent.bedrock_client == mock_bedrock
    
    @patch('boto3.client')
    async def test_ai_powered_task_processing(self, mock_boto3_client):
        """Test AI-powered task processing."""
        mock_sqs = Mock()
        mock_bedrock = Mock()
        mock_boto3_client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
        
        # Mock Bedrock response
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(
                read=lambda: b'{"task_analysis": "This is a text processing task", "recommended_approach": "Use NLP techniques", "confidence": 0.95}'
            )
        }
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text with AI"
            )
        ]
        
        class BedrockTestAgent(TestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.bedrock_client = mock_bedrock
                self.ai_enhanced = True
            
            async def process_task_with_ai(self, task_description, parameters):
                """Process task with AI guidance."""
                try:
                    response = self.bedrock_client.invoke_model(
                        ModelId='anthropic.claude-3-sonnet-20240229-v1:0',
                        Body=json.dumps({
                            'prompt': f"Analyze this task: {task_description}",
                            'max_tokens': 1000
                        })
                    )
                    return json.loads(response['body'].read())
                except Exception as e:
                    return {'error': str(e)}
        
        agent = BedrockTestAgent(
            name="AI Agent",
            description="An AI-enhanced agent",
            capabilities=capabilities
        )
        
        # Test AI-powered task processing
        result = await agent.process_task_with_ai(
            "Analyze sentiment in customer reviews",
            {"reviews": ["Great product!", "Terrible service"]}
        )
        
        assert 'task_analysis' in result
        assert 'recommended_approach' in result
        assert 'confidence' in result
        assert result['confidence'] == 0.95
    
    @patch('boto3.client')
    async def test_ai_insights_generation(self, mock_boto3_client):
        """Test AI insights generation."""
        mock_sqs = Mock()
        mock_bedrock = Mock()
        mock_boto3_client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
        
        # Mock Bedrock response for insights
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(
                read=lambda: b'{"performance_insights": "Agent is performing well", "optimization_suggestions": ["Reduce response time", "Improve error handling"], "trends": "Increasing success rate"}'
            )
        }
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text with AI"
            )
        ]
        
        class BedrockTestAgent(TestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.bedrock_client = mock_bedrock
                self.ai_enhanced = True
            
            async def get_ai_insights(self):
                """Get AI-generated insights about agent performance."""
                try:
                    response = self.bedrock_client.invoke_model(
                        ModelId='anthropic.claude-3-sonnet-20240229-v1:0',
                        Body=json.dumps({
                            'prompt': f"Analyze agent performance: {self.tasks_completed} tasks completed, {self.tasks_failed} failed, avg response time: {self._calculate_average_response_time()}ms",
                            'max_tokens': 500
                        })
                    )
                    return json.loads(response['body'].read())
                except Exception as e:
                    return {'error': str(e)}
        
        agent = BedrockTestAgent(
            name="AI Agent",
            description="An AI-enhanced agent",
            capabilities=capabilities
        )
        
        # Set some performance data
        agent.tasks_completed = 50
        agent.tasks_failed = 5
        agent.response_times = [100, 150, 200]
        
        # Test AI insights generation
        insights = await agent.get_ai_insights()
        
        assert 'performance_insights' in insights
        assert 'optimization_suggestions' in insights
        assert 'trends' in insights
    
    @patch('boto3.client')
    async def test_ai_enhanced_task_execution(self, mock_boto3_client):
        """Test AI-enhanced task execution with confidence scoring."""
        mock_sqs = Mock()
        mock_bedrock = Mock()
        mock_boto3_client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
        
        # Mock Bedrock response for task analysis
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(
                read=lambda: b'{"task_complexity": "medium", "estimated_duration": "2-3 minutes", "confidence_score": 0.88, "recommended_resources": ["NLP library", "Sentiment analysis model"]}'
            )
        }
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text with AI"
            )
        ]
        
        class BedrockTestAgent(TestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.bedrock_client = mock_bedrock
                self.ai_enhanced = True
            
            async def execute_task_with_ai_analysis(self, task):
                """Execute task with AI analysis and confidence scoring."""
                try:
                    # Get AI analysis of the task
                    response = self.bedrock_client.invoke_model(
                        ModelId='anthropic.claude-3-sonnet-20240229-v1:0',
                        Body=json.dumps({
                            'prompt': f"Analyze task complexity and requirements: {task.description}",
                            'max_tokens': 500
                        })
                    )
                    ai_analysis = json.loads(response['body'].read())
                    
                    # Execute the task
                    result = await self.execute_task(task)
                    
                    # Add AI analysis to result
                    result['ai_analysis'] = ai_analysis
                    result['confidence_score'] = ai_analysis.get('confidence_score', 0.5)
                    
                    return result
                except Exception as e:
                    return {'success': False, 'error': str(e)}
        
        agent = BedrockTestAgent(
            name="AI Agent",
            description="An AI-enhanced agent",
            capabilities=capabilities
        )
        
        # Register a task handler
        async def process_text_task(parameters):
            return {"processed_text": "AI-enhanced processing result"}
        
        agent.register_task_handler(CapabilityType.TEXT_PROCESSING, process_text_task)
        
        # Create a task
        task = Task(
            title="Test Task",
            description="Analyze sentiment in customer feedback",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            created_by="test-agent"
        )
        
        # Test AI-enhanced task execution
        result = await agent.execute_task_with_ai_analysis(task)
        
        assert result['success'] is True
        assert 'ai_analysis' in result
        assert 'confidence_score' in result
        assert result['confidence_score'] == 0.88
        assert 'task_complexity' in result['ai_analysis']
        assert 'estimated_duration' in result['ai_analysis']
    
    @patch('boto3.client')
    async def test_bedrock_error_handling(self, mock_boto3_client):
        """Test error handling when Bedrock service fails."""
        mock_sqs = Mock()
        mock_bedrock = Mock()
        mock_boto3_client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
        
        # Mock Bedrock to fail
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock service unavailable")
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text with AI"
            )
        ]
        
        class BedrockTestAgent(TestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.bedrock_client = mock_bedrock
                self.ai_enhanced = True
            
            async def process_task_with_ai(self, task_description, parameters):
                """Process task with AI guidance."""
                try:
                    response = self.bedrock_client.invoke_model(
                        ModelId='anthropic.claude-3-sonnet-20240229-v1:0',
                        Body=json.dumps({
                            'prompt': f"Analyze this task: {task_description}",
                            'max_tokens': 1000
                        })
                    )
                    return json.loads(response['body'].read())
                except Exception as e:
                    return {'error': str(e), 'fallback_mode': True}
        
        agent = BedrockTestAgent(
            name="AI Agent",
            description="An AI-enhanced agent",
            capabilities=capabilities
        )
        
        # Test error handling
        result = await agent.process_task_with_ai(
            "Analyze sentiment in customer reviews",
            {"reviews": ["Great product!", "Terrible service"]}
        )
        
        assert 'error' in result
        assert 'fallback_mode' in result
        assert result['fallback_mode'] is True 