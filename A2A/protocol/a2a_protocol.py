"""
A2A Protocol Definitions

This module defines the communication protocols and message formats
used for agent-to-agent communication in the A2A system.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class MessageType(str, Enum):
    """Types of messages that can be sent between agents."""
    DISCOVERY_REQUEST = "discovery_request"
    DISCOVERY_RESPONSE = "discovery_response"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_UPDATE = "task_update"
    HEARTBEAT = "heartbeat"
    REGISTRATION = "registration"
    DEREGISTRATION = "deregistration"


class TaskStatus(str, Enum):
    """Status of a task in the system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CapabilityType(str, Enum):
    """Types of capabilities that agents can have."""
    TEXT_PROCESSING = "text_processing"
    IMAGE_PROCESSING = "image_processing"
    DATA_ANALYSIS = "data_analysis"
    WEB_SCRAPING = "web_scraping"
    API_INTEGRATION = "api_integration"
    MACHINE_LEARNING = "machine_learning"
    FILE_PROCESSING = "file_processing"
    DATABASE_OPERATIONS = "database_operations"
    CUSTOM = "custom"


class Capability(BaseModel):
    """Represents a capability that an agent can provide."""
    type: CapabilityType
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class AgentMetadata(BaseModel):
    """Metadata about an agent."""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[Capability]
    contact_info: Optional[Dict[str, str]] = None
    location: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"


class Task(BaseModel):
    """Represents a task to be executed by an agent."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    required_capabilities: List[CapabilityType]
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[datetime] = None
    created_by: str
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    success_rate: Optional[float] = Field(1.0, ge=0.0, le=1.0)


class Message(BaseModel):
    """Base message structure for agent communication."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


class DiscoveryRequest(BaseModel):
    """Request for discovering agents with specific capabilities."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    required_capabilities: List[CapabilityType]
    optional_capabilities: List[CapabilityType] = Field(default_factory=list)
    location_preference: Optional[str] = None
    max_results: int = Field(ge=1, le=100, default=10)
    timeout_seconds: int = Field(ge=1, le=3600, default=30)
    filters: Optional[Dict[str, Any]] = None


class DiscoveryResponse(BaseModel):
    """Response to a discovery request."""
    request_id: str
    agents: List[AgentMetadata]
    total_found: int
    search_duration_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskRequest(BaseModel):
    """Request to execute a task."""
    task: Task
    expected_duration_minutes: Optional[int] = None
    retry_count: int = Field(ge=0, default=0)
    max_retries: int = Field(ge=0, default=3)


class TaskResponse(BaseModel):
    """Response to a task request."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Heartbeat(BaseModel):
    """Heartbeat message to indicate agent is alive."""
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"
    current_load: Optional[float] = None
    available_capabilities: List[CapabilityType] = Field(default_factory=list)


# Protocol version for compatibility
PROTOCOL_VERSION = "1.0.0"


def create_message(
    message_type: MessageType,
    sender_id: str,
    recipient_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    reply_to: Optional[str] = None
) -> Message:
    """Create a new message with the given parameters."""
    return Message(
        message_type=message_type,
        sender_id=sender_id,
        recipient_id=recipient_id,
        payload=payload or {},
        correlation_id=correlation_id,
        reply_to=reply_to
    )


def validate_message(message: Message) -> bool:
    """Validate a message according to the protocol."""
    if not message.message_id or not message.sender_id:
        return False
    
    if message.message_type not in MessageType:
        return False
    
    if message.timestamp > datetime.utcnow():
        return False
    
    return True


def get_message_size(message: Message) -> int:
    """Get the approximate size of a message in bytes."""
    import json
    return len(json.dumps(message.dict(), default=str)) 