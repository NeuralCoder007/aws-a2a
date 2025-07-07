"""
Unit tests for the A2A protocol module.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from protocol import (
    MessageType, TaskStatus, TaskPriority, CapabilityType,
    Capability, AgentCard, Task, Message, DiscoveryRequest,
    DiscoveryResponse, TaskRequest, TaskResponse, Heartbeat,
    AgentMetadata, create_message, validate_message, get_message_size,
    PROTOCOL_VERSION
)


class TestProtocolEnums:
    """Test protocol enums and constants."""
    
    def test_message_types(self):
        """Test MessageType enum values."""
        assert MessageType.DISCOVERY_REQUEST == "discovery_request"
        assert MessageType.DISCOVERY_RESPONSE == "discovery_response"
        assert MessageType.TASK_REQUEST == "task_request"
        assert MessageType.TASK_RESPONSE == "task_response"
        assert MessageType.HEARTBEAT == "heartbeat"
        assert MessageType.REGISTRATION == "registration"
        assert MessageType.DEREGISTRATION == "deregistration"
    
    def test_task_status(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
    
    def test_task_priority(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.NORMAL == "normal"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.URGENT == "urgent"
    
    def test_capability_types(self):
        """Test CapabilityType enum values."""
        assert CapabilityType.TEXT_PROCESSING == "text_processing"
        assert CapabilityType.IMAGE_PROCESSING == "image_processing"
        assert CapabilityType.DATA_ANALYSIS == "data_analysis"
        assert CapabilityType.WEB_SCRAPING == "web_scraping"
        assert CapabilityType.API_INTEGRATION == "api_integration"
        assert CapabilityType.MACHINE_LEARNING == "machine_learning"
        assert CapabilityType.FILE_PROCESSING == "file_processing"
        assert CapabilityType.DATABASE_OPERATIONS == "database_operations"
        assert CapabilityType.CUSTOM == "custom"
    
    def test_protocol_version(self):
        """Test protocol version constant."""
        assert PROTOCOL_VERSION == "1.0.0"


class TestCapability:
    """Test Capability class."""
    
    def test_capability_creation(self):
        """Test creating a capability."""
        cap = Capability(
            type=CapabilityType.TEXT_PROCESSING,
            name="Text Analysis",
            description="Analyzes text content",
            parameters={"max_length": 1000},
            version="1.0.0",
            confidence=0.95
        )
        
        assert cap.type == CapabilityType.TEXT_PROCESSING
        assert cap.name == "Text Analysis"
        assert cap.description == "Analyzes text content"
        assert cap.parameters == {"max_length": 1000}
        assert cap.version == "1.0.0"
        assert cap.confidence == 0.95
    
    def test_capability_defaults(self):
        """Test capability with default values."""
        cap = Capability(
            type=CapabilityType.DATA_ANALYSIS,
            name="Data Analysis",
            description="Analyzes data"
        )
        
        assert cap.parameters is None
        assert cap.version == "1.0.0"
        assert cap.confidence == 1.0
    
    def test_capability_validation(self):
        """Test capability validation."""
        # Test confidence bounds
        with pytest.raises(ValueError):
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Test",
                description="Test",
                confidence=1.5  # Should be <= 1.0
            )
        
        with pytest.raises(ValueError):
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Test",
                description="Test",
                confidence=-0.1  # Should be >= 0.0
            )


class TestAgentCard:
    """Test AgentCard class."""
    
    def test_agent_card_creation(self):
        """Test creating an agent card."""
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        card = AgentCard(
            agent_id="test-agent-001",
            name="Test Agent",
            description="A test agent",
            version="1.0.0",
            capabilities=capabilities,
            contact_info={"email": "test@example.com"},
            location="us-east-1",
            tags=["test", "demo"],
            success_rate=0.98
        )
        
        assert card.agent_id == "test-agent-001"
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.version == "1.0.0"
        assert len(card.capabilities) == 1
        assert card.contact_info == {"email": "test@example.com"}
        assert card.location == "us-east-1"
        assert card.tags == ["test", "demo"]
        assert card.status == "active"
        assert card.success_rate == 0.98
    
    def test_agent_card_defaults(self):
        """Test agent card with default values."""
        capabilities = [
            Capability(
                type=CapabilityType.DATA_ANALYSIS,
                name="Data Analysis",
                description="Analyzes data"
            )
        ]
        
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        assert card.agent_id is not None
        assert card.version == "1.0.0"
        assert card.contact_info is None
        assert card.location is None
        assert card.tags == []
        assert card.status == "active"
        assert card.max_concurrent_tasks == 5
        assert card.success_rate == 1.0
    
    def test_agent_card_methods(self):
        """Test agent card methods."""
        capabilities = [
            Capability(type=CapabilityType.TEXT_PROCESSING, name="Text", description="Text"),
            Capability(type=CapabilityType.DATA_ANALYSIS, name="Data", description="Data")
        ]
        
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )
        
        # Test capability checking
        assert card.has_capability(CapabilityType.TEXT_PROCESSING) is True
        assert card.has_capability(CapabilityType.IMAGE_PROCESSING) is False
        
        # Test getting capability
        text_cap = card.get_capability(CapabilityType.TEXT_PROCESSING)
        assert text_cap is not None
        assert text_cap.type == CapabilityType.TEXT_PROCESSING
        
        # Test adding capability
        new_cap = Capability(type=CapabilityType.API_INTEGRATION, name="API", description="API")
        card.add_capability(new_cap)
        assert card.has_capability(CapabilityType.API_INTEGRATION) is True
        
        # Test removing capability
        assert card.remove_capability(CapabilityType.TEXT_PROCESSING) is True
        assert card.has_capability(CapabilityType.TEXT_PROCESSING) is False
        
        # Test updating last seen
        old_last_seen = card.last_seen
        card.update_last_seen()
        assert card.last_seen > old_last_seen
        
        # Test active status
        assert card.is_active() is True
        
        # Test summary
        summary = card.get_summary()
        assert "agent_id" in summary
        assert "name" in summary
        assert "capability_types" in summary


class TestTask:
    """Test Task class."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            task_id="task-001",
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            parameters={"text": "Hello world"},
            priority=TaskPriority.HIGH,
            created_by="test-agent",
            assigned_to="worker-agent",
            success_rate=0.95
        )
        
        assert task.task_id == "task-001"
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.required_capabilities == [CapabilityType.TEXT_PROCESSING]
        assert task.parameters == {"text": "Hello world"}
        assert task.priority == TaskPriority.HIGH
        assert task.created_by == "test-agent"
        assert task.assigned_to == "worker-agent"
        assert task.status == TaskStatus.PENDING
        assert task.success_rate == 0.95
    
    def test_task_defaults(self):
        """Test task with default values."""
        task = Task(
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.DATA_ANALYSIS],
            created_by="test-agent"
        )
        
        assert task.task_id is not None
        assert task.parameters == {}
        assert task.priority == TaskPriority.NORMAL
        assert task.assigned_to is None
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error_message is None
        assert task.success_rate == 1.0


class TestMessage:
    """Test Message class."""
    
    def test_message_creation(self):
        """Test creating a message."""
        message = Message(
            message_id="msg-001",
            message_type=MessageType.TASK_REQUEST,
            sender_id="sender-agent",
            recipient_id="recipient-agent",
            payload={"task": "data"},
            correlation_id="corr-001",
            reply_to="reply-queue"
        )
        
        assert message.message_id == "msg-001"
        assert message.message_type == MessageType.TASK_REQUEST
        assert message.sender_id == "sender-agent"
        assert message.recipient_id == "recipient-agent"
        assert message.payload == {"task": "data"}
        assert message.correlation_id == "corr-001"
        assert message.reply_to == "reply-queue"
    
    def test_message_defaults(self):
        """Test message with default values."""
        message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        
        assert message.message_id is not None
        assert message.recipient_id is None
        assert message.payload == {}
        assert message.correlation_id is None
        assert message.reply_to is None


class TestProtocolFunctions:
    """Test protocol utility functions."""
    
    def test_create_message(self):
        """Test create_message function."""
        message = create_message(
            message_type=MessageType.DISCOVERY_REQUEST,
            sender_id="test-agent",
            recipient_id="discovery-service",
            payload={"capabilities": ["text_processing"]},
            correlation_id="corr-001"
        )
        
        assert message.message_type == MessageType.DISCOVERY_REQUEST
        assert message.sender_id == "test-agent"
        assert message.recipient_id == "discovery-service"
        assert message.payload == {"capabilities": ["text_processing"]}
        assert message.correlation_id == "corr-001"
    
    def test_validate_message(self):
        """Test validate_message function."""
        # Valid message
        valid_message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        assert validate_message(valid_message) is True
        
        # Invalid message - missing sender_id
        invalid_message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id=""
        )
        assert validate_message(invalid_message) is False
        
        # Invalid message - future timestamp
        future_message = Message(
            message_type=MessageType.HEARTBEAT,
            sender_id="test-agent"
        )
        future_message.timestamp = datetime(2030, 1, 1)
        assert validate_message(future_message) is False
    
    def test_get_message_size(self):
        """Test get_message_size function."""
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id="test-agent",
            payload={"data": "test"}
        )
        
        size = get_message_size(message)
        assert isinstance(size, int)
        assert size > 0


class TestDiscoveryRequest:
    """Test DiscoveryRequest class."""
    
    def test_discovery_request_creation(self):
        """Test creating a discovery request."""
        request = DiscoveryRequest(
            request_id="req-001",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            optional_capabilities=[CapabilityType.DATA_ANALYSIS],
            location_preference="us-east-1",
            max_results=5,
            timeout_seconds=60
        )
        
        assert request.request_id == "req-001"
        assert request.required_capabilities == [CapabilityType.TEXT_PROCESSING]
        assert request.optional_capabilities == [CapabilityType.DATA_ANALYSIS]
        assert request.location_preference == "us-east-1"
        assert request.max_results == 5
        assert request.timeout_seconds == 60
    
    def test_discovery_request_defaults(self):
        """Test discovery request with default values."""
        request = DiscoveryRequest(
            required_capabilities=[CapabilityType.TEXT_PROCESSING]
        )
        
        assert request.request_id is not None
        assert request.optional_capabilities == []
        assert request.location_preference is None
        assert request.max_results == 10
        assert request.timeout_seconds == 30
        assert request.filters is None


class TestDiscoveryResponse:
    """Test DiscoveryResponse class."""
    
    def test_discovery_response_creation(self):
        """Test creating a discovery response."""
        agents = [
            AgentMetadata(
                agent_id="agent-1",
                name="Agent 1",
                description="Test agent 1",
                version="1.0.0",
                capabilities=[]
            ),
            AgentMetadata(
                agent_id="agent-2",
                name="Agent 2",
                description="Test agent 2",
                version="1.0.0",
                capabilities=[]
            )
        ]
        
        response = DiscoveryResponse(
            request_id="req-001",
            agents=agents,
            total_found=2,
            search_duration_ms=150
        )
        
        assert response.request_id == "req-001"
        assert len(response.agents) == 2
        assert response.agents[0].agent_id == "agent-1"
        assert response.agents[1].agent_id == "agent-2"
        assert response.total_found == 2
        assert response.search_duration_ms == 150


class TestTaskRequest:
    """Test TaskRequest class."""
    
    def test_task_request_creation(self):
        """Test creating a task request."""
        task = Task(
            title="Test Task",
            description="A test task",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            created_by="test-agent"
        )
        
        request = TaskRequest(
            task=task,
            expected_duration_minutes=30,
            retry_count=0,
            max_retries=3
        )
        
        assert request.task == task
        assert request.expected_duration_minutes == 30
        assert request.retry_count == 0
        assert request.max_retries == 3


class TestTaskResponse:
    """Test TaskResponse class."""
    
    def test_task_response_creation(self):
        """Test creating a task response."""
        response = TaskResponse(
            task_id="task-001",
            status=TaskStatus.COMPLETED,
            result={"processed": True},
            error_message=None,
            execution_time_ms=1500
        )
        
        assert response.task_id == "task-001"
        assert response.status == TaskStatus.COMPLETED
        assert response.result == {"processed": True}
        assert response.error_message is None
        assert response.execution_time_ms == 1500


class TestHeartbeat:
    """Test Heartbeat class."""
    
    def test_heartbeat_creation(self):
        """Test creating a heartbeat."""
        heartbeat = Heartbeat(
            agent_id="test-agent",
            status="active",
            current_load=0.5,
            available_capabilities=[CapabilityType.TEXT_PROCESSING]
        )
        
        assert heartbeat.agent_id == "test-agent"
        assert heartbeat.status == "active"
        assert heartbeat.current_load == 0.5
        assert heartbeat.available_capabilities == [CapabilityType.TEXT_PROCESSING]
    
    def test_heartbeat_defaults(self):
        """Test heartbeat with default values."""
        heartbeat = Heartbeat(agent_id="test-agent")
        
        assert heartbeat.status == "active"
        assert heartbeat.current_load is None
        assert heartbeat.available_capabilities == [] 