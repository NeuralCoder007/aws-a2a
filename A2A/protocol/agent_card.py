"""
Agent Card Module

This module defines the AgentCard class which represents the metadata
and capabilities of an agent in the A2A system.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from .a2a_protocol import Capability, CapabilityType


class AgentCard(BaseModel):
    """
    Represents an agent's identity and capabilities in the A2A system.
    
    This is the primary way agents describe themselves to the discovery system
    and other agents.
    """
    
    # Core identity
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    version: str = "1.0.0"
    
    # Capabilities and skills
    capabilities: List[Capability] = Field(default_factory=list)
    
    # Contact and location
    contact_info: Optional[Dict[str, str]] = None
    location: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"
    
    # Performance metrics
    response_time_ms: Optional[int] = None
    success_rate: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    total_tasks_completed: int = 0
    
    # Configuration
    max_concurrent_tasks: int = Field(default=5, ge=1)
    supported_protocols: List[str] = Field(default_factory=lambda: ["a2a_v1.0"])
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def has_capability(self, capability_type: CapabilityType) -> bool:
        """Check if the agent has a specific capability."""
        return any(cap.type == capability_type for cap in self.capabilities)
    
    def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type."""
        for cap in self.capabilities:
            if cap.type == capability_type:
                return cap
        return None
    
    def add_capability(self, capability: Capability) -> None:
        """Add a new capability to the agent."""
        # Remove existing capability of the same type
        self.capabilities = [cap for cap in self.capabilities if cap.type != capability.type]
        self.capabilities.append(capability)
    
    def remove_capability(self, capability_type: CapabilityType) -> bool:
        """Remove a capability from the agent."""
        original_count = len(self.capabilities)
        self.capabilities = [cap for cap in self.capabilities if cap.type != capability_type]
        return len(self.capabilities) < original_count
    
    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = datetime.utcnow()
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if the agent is considered active based on last seen time."""
        if self.status != "active":
            return False
        
        time_diff = datetime.utcnow() - self.last_seen
        return time_diff.total_seconds() < (timeout_minutes * 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the agent card to a dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCard':
        """Create an agent card from a dictionary."""
        return cls(**data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the agent card for discovery purposes."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capability_types": [cap.type.value for cap in self.capabilities],
            "location": self.location,
            "tags": self.tags,
            "status": self.status,
            "last_seen": self.last_seen.isoformat(),
            "success_rate": self.success_rate,
            "total_tasks_completed": self.total_tasks_completed
        }


def create_agent_card(
    name: str,
    description: str,
    capabilities: List[Capability],
    agent_id: Optional[str] = None,
    version: str = "1.0.0",
    location: Optional[str] = None,
    tags: Optional[List[str]] = None,
    contact_info: Optional[Dict[str, str]] = None,
    success_rate: Optional[float] = 1.0
) -> AgentCard:
    """
    Create a new agent card with the specified parameters.
    
    Args:
        name: The name of the agent
        description: Description of what the agent does
        capabilities: List of capabilities the agent provides
        agent_id: Optional custom agent ID
        version: Version of the agent
        location: Optional location information
        tags: Optional tags for categorization
        contact_info: Optional contact information
        
    Returns:
        A new AgentCard instance
    """
    return AgentCard(
        agent_id=agent_id or str(uuid.uuid4()),
        name=name,
        description=description,
        version=version,
        capabilities=capabilities,
        location=location,
        tags=tags or [],
        contact_info=contact_info,
        success_rate=success_rate
    )


def validate_agent_card(card: AgentCard) -> List[str]:
    """
    Validate an agent card and return any validation errors.
    
    Args:
        card: The agent card to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not card.name or len(card.name.strip()) == 0:
        errors.append("Agent name is required")
    
    if not card.description or len(card.description.strip()) == 0:
        errors.append("Agent description is required")
    
    if not card.capabilities:
        errors.append("At least one capability is required")
    
    for i, cap in enumerate(card.capabilities):
        if not cap.name or len(cap.name.strip()) == 0:
            errors.append(f"Capability {i+1} must have a name")
        
        if not cap.description or len(cap.description.strip()) == 0:
            errors.append(f"Capability {i+1} must have a description")
    
    if card.success_rate is not None and (card.success_rate < 0 or card.success_rate > 1):
        errors.append("Success rate must be between 0 and 1")
    
    if card.max_concurrent_tasks < 1:
        errors.append("Max concurrent tasks must be at least 1")
    
    return errors 