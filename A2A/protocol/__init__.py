"""
A2A Protocol Package

This package contains all the communication protocols and data structures
used for agent-to-agent communication in the A2A system.
"""

from .a2a_protocol import (
    MessageType,
    TaskStatus,
    TaskPriority,
    CapabilityType,
    Capability,
    AgentMetadata,
    Task,
    Message,
    DiscoveryRequest,
    DiscoveryResponse,
    TaskRequest,
    TaskResponse,
    Heartbeat,
    create_message,
    validate_message,
    get_message_size,
    PROTOCOL_VERSION
)

from .agent_card import (
    AgentCard,
    create_agent_card,
    validate_agent_card
)

from .message import (
    MessageHandler,
    MessageBuilder
)

from .task import (
    TaskManager,
    TaskValidator,
    TaskScheduler
)

__all__ = [
    # Protocol definitions
    'MessageType',
    'TaskStatus', 
    'TaskPriority',
    'CapabilityType',
    'Capability',
    'AgentMetadata',
    'Task',
    'Message',
    'DiscoveryRequest',
    'DiscoveryResponse',
    'TaskRequest',
    'TaskResponse',
    'Heartbeat',
    'create_message',
    'validate_message',
    'get_message_size',
    'PROTOCOL_VERSION',
    
    # Agent card
    'AgentCard',
    'create_agent_card',
    'validate_agent_card',
    
    # Message handling
    'MessageHandler',
    'MessageBuilder',
    
    # Task management
    'TaskManager',
    'TaskValidator',
    'TaskScheduler'
] 