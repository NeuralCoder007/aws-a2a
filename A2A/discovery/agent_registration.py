"""
Agent Registration Lambda Handler

Handles agent registration events from SQS and updates the registry.
"""

import json
import os
from typing import Dict, Any
from protocol import AgentCard, Capability, CapabilityType
from registry import AgentRegistry

REGISTRY_TABLE = os.environ.get("DISCOVERY_TABLE", "agent_registry")
REGION = os.environ.get("AWS_REGION", "us-east-1")
registry = AgentRegistry(REGISTRY_TABLE, REGION)

def lambda_handler(event, context):
    """Process SQS messages for agent registration."""
    results = []
    
    for record in event.get("Records", []):
        try:
            # Parse the message body
            if isinstance(record["body"], str):
                body = json.loads(record["body"])
            else:
                body = record["body"]
            
            # Handle different message formats
            if "agent_data" in body:
                # New format from discovery API
                result = _process_agent_data(body)
            else:
                # Direct agent card format
                result = _process_direct_registration(body)
            
            results.append(result)
            
        except json.JSONDecodeError as e:
            results.append({
                "success": False,
                "error": f"Invalid JSON in message: {str(e)}"
            })
        except Exception as e:
            results.append({
                "success": False,
                "error": f"Registration error: {str(e)}"
            })
    
    return {
        "statusCode": 200,
        "body": json.dumps({"results": results})
    }

def _process_agent_data(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process agent registration with agent_data format."""
    try:
        agent_data = body.get("agent_data", {})
        agent_id = body.get("agent_id")
        
        if not agent_data:
            return {
                "success": False,
                "error": "No agent data provided"
            }
        
        # Validate required fields
        if not agent_data.get("name"):
            return {
                "success": False,
                "error": "Agent name is required"
            }
        
        if not agent_data.get("capabilities"):
            return {
                "success": False,
                "error": "At least one capability is required"
            }
        
        # Convert capabilities to proper format
        capabilities = []
        for cap_data in agent_data.get("capabilities", []):
            if isinstance(cap_data, dict):
                capability = Capability(
                    type=CapabilityType(cap_data["type"]),
                    name=cap_data["name"],
                    description=cap_data["description"],
                    parameters=cap_data.get("parameters"),
                    version=cap_data.get("version", "1.0.0"),
                    confidence=cap_data.get("confidence", 1.0)
                )
                capabilities.append(capability)
        
        # Create agent card
        agent_card = AgentCard(
            name=agent_data["name"],
            description=agent_data["description"],
            capabilities=capabilities,
            contact_info=agent_data.get("contact_info"),
            location=agent_data.get("location"),
            tags=agent_data.get("tags", []),
            success_rate=agent_data.get("success_rate")
        )
        
        # Register the agent
        result = registry.register_agent(agent_card)
        
        return {
            "success": result.get("success", False),
            "agent_id": agent_card.agent_id,
            "message": result.get("message", "Registration processed"),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Registration processing error: {str(e)}"
        }

def _process_direct_registration(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process direct agent card registration."""
    try:
        # Create agent card directly from body
        agent_card = AgentCard(**body)
        
        # Register the agent
        result = registry.register_agent(agent_card)
        
        return {
            "success": result.get("success", False),
            "agent_id": agent_card.agent_id,
            "message": result.get("message", "Registration processed"),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Direct registration error: {str(e)}"
        } 