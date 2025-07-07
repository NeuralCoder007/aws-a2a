"""
Message Module

This module provides utilities for creating, validating, and handling
messages in the A2A communication system.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from .a2a_protocol import Message, MessageType, validate_message, create_message


class MessageHandler:
    """Handles message creation, validation, and processing."""
    
    @staticmethod
    def create_discovery_request(
        sender_id: str,
        required_capabilities: List[str],
        optional_capabilities: Optional[List[str]] = None,
        location_preference: Optional[str] = None,
        max_results: int = 10,
        timeout_seconds: int = 30
    ) -> Message:
        """Create a discovery request message."""
        payload = {
            "required_capabilities": required_capabilities,
            "optional_capabilities": optional_capabilities or [],
            "location_preference": location_preference,
            "max_results": max_results,
            "timeout_seconds": timeout_seconds
        }
        
        return create_message(
            message_type=MessageType.DISCOVERY_REQUEST,
            sender_id=sender_id,
            payload=payload
        )
    
    @staticmethod
    def create_discovery_response(
        sender_id: str,
        recipient_id: str,
        request_id: str,
        agents: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> Message:
        """Create a discovery response message."""
        payload = {
            "request_id": request_id,
            "agents": agents,
            "total_found": len(agents),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return create_message(
            message_type=MessageType.DISCOVERY_RESPONSE,
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_task_request(
        sender_id: str,
        recipient_id: str,
        task: Dict[str, Any],
        expected_duration_minutes: Optional[int] = None
    ) -> Message:
        """Create a task request message."""
        payload = {
            "task": task,
            "expected_duration_minutes": expected_duration_minutes
        }
        
        return create_message(
            message_type=MessageType.TASK_REQUEST,
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload
        )
    
    @staticmethod
    def create_task_response(
        sender_id: str,
        recipient_id: str,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Message:
        """Create a task response message."""
        payload = {
            "task_id": task_id,
            "status": status,
            "result": result,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return create_message(
            message_type=MessageType.TASK_RESPONSE,
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_heartbeat(
        agent_id: str,
        status: str = "active",
        current_load: Optional[float] = None,
        available_capabilities: Optional[List[str]] = None
    ) -> Message:
        """Create a heartbeat message."""
        payload = {
            "status": status,
            "current_load": current_load,
            "available_capabilities": available_capabilities or [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return create_message(
            message_type=MessageType.HEARTBEAT,
            sender_id=agent_id,
            payload=payload
        )
    
    @staticmethod
    def create_registration_message(
        agent_id: str,
        agent_card: Dict[str, Any]
    ) -> Message:
        """Create an agent registration message."""
        payload = {
            "agent_card": agent_card,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return create_message(
            message_type=MessageType.REGISTRATION,
            sender_id=agent_id,
            payload=payload
        )
    
    @staticmethod
    def create_deregistration_message(agent_id: str) -> Message:
        """Create an agent deregistration message."""
        payload = {
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return create_message(
            message_type=MessageType.DEREGISTRATION,
            sender_id=agent_id,
            payload=payload
        )
    
    @staticmethod
    def serialize_message(message: Message) -> str:
        """Serialize a message to JSON string."""
        return json.dumps(message.dict(), default=str)
    
    @staticmethod
    def deserialize_message(message_str: str) -> Message:
        """Deserialize a JSON string to a Message object."""
        data = json.loads(message_str)
        return Message(**data)
    
    @staticmethod
    def validate_and_parse(message_str: str) -> Optional[Message]:
        """Validate and parse a message string."""
        try:
            message = MessageHandler.deserialize_message(message_str)
            if validate_message(message):
                return message
            return None
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    @staticmethod
    def get_message_type(message: Message) -> MessageType:
        """Get the message type from a message."""
        return message.message_type
    
    @staticmethod
    def is_discovery_message(message: Message) -> bool:
        """Check if a message is a discovery-related message."""
        return message.message_type in [
            MessageType.DISCOVERY_REQUEST,
            MessageType.DISCOVERY_RESPONSE
        ]
    
    @staticmethod
    def is_task_message(message: Message) -> bool:
        """Check if a message is a task-related message."""
        return message.message_type in [
            MessageType.TASK_REQUEST,
            MessageType.TASK_RESPONSE,
            MessageType.TASK_UPDATE
        ]
    
    @staticmethod
    def is_system_message(message: Message) -> bool:
        """Check if a message is a system message."""
        return message.message_type in [
            MessageType.HEARTBEAT,
            MessageType.REGISTRATION,
            MessageType.DEREGISTRATION
        ]
    
    @staticmethod
    def extract_correlation_id(message: Message) -> Optional[str]:
        """Extract correlation ID from a message."""
        return message.correlation_id
    
    @staticmethod
    def set_correlation_id(message: Message, correlation_id: str) -> Message:
        """Set correlation ID for a message."""
        message.correlation_id = correlation_id
        return message
    
    @staticmethod
    def get_payload_value(message: Message, key: str, default: Any = None) -> Any:
        """Get a value from the message payload."""
        return message.payload.get(key, default)
    
    @staticmethod
    def set_payload_value(message: Message, key: str, value: Any) -> Message:
        """Set a value in the message payload."""
        message.payload[key] = value
        return message


class MessageBuilder:
    """Builder pattern for creating complex messages."""
    
    def __init__(self, sender_id: str):
        self.sender_id = sender_id
        self.message_type: Optional[MessageType] = None
        self.recipient_id: Optional[str] = None
        self.payload: Dict[str, Any] = {}
        self.correlation_id: Optional[str] = None
        self.reply_to: Optional[str] = None
    
    def set_type(self, message_type: MessageType) -> 'MessageBuilder':
        """Set the message type."""
        self.message_type = message_type
        return self
    
    def set_recipient(self, recipient_id: str) -> 'MessageBuilder':
        """Set the recipient ID."""
        self.recipient_id = recipient_id
        return self
    
    def add_payload(self, key: str, value: Any) -> 'MessageBuilder':
        """Add a key-value pair to the payload."""
        self.payload[key] = value
        return self
    
    def set_payload(self, payload: Dict[str, Any]) -> 'MessageBuilder':
        """Set the entire payload."""
        self.payload = payload
        return self
    
    def set_correlation_id(self, correlation_id: str) -> 'MessageBuilder':
        """Set the correlation ID."""
        self.correlation_id = correlation_id
        return self
    
    def set_reply_to(self, reply_to: str) -> 'MessageBuilder':
        """Set the reply-to field."""
        self.reply_to = reply_to
        return self
    
    def build(self) -> Message:
        """Build the message."""
        if not self.message_type:
            raise ValueError("Message type must be set")
        
        return Message(
            message_type=self.message_type,
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            payload=self.payload,
            correlation_id=self.correlation_id,
            reply_to=self.reply_to
        ) 