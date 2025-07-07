"""
Discovery Processor Lambda Handler

Processes discovery requests from SQS, matches agents, and sends responses.
"""

import json
import os
from typing import Dict, Any
from protocol import CapabilityType, DiscoveryResponse, AgentMetadata
from registry import AgentRegistry

REGISTRY_TABLE = os.environ.get("DISCOVERY_TABLE", "agent_registry")
REGION = os.environ.get("AWS_REGION", "us-east-1")
registry = AgentRegistry(REGISTRY_TABLE, REGION)

def lambda_handler(event, context):
    """Process SQS messages for discovery requests."""
    if not event.get("Records"):
        return {
            "statusCode": 400,
            "body": json.dumps({"results": [{"success": False, "error": "No records found"}]})
        }
    results = []
    status_code = 200
    
    for record in event.get("Records", []):
        try:
            # Parse the message body
            if isinstance(record["body"], str):
                body = json.loads(record["body"])
            else:
                body = record["body"]
            
            # Handle different message types
            if "capabilities" in body:
                # Discovery request
                result = _process_discovery_request(body)
                # If error, set status code to 500
                if result.get("success") is False and result.get("error"):
                    status_code = 500
            elif "agent_data" in body:
                # Agent registration request
                result = _process_agent_registration(body)
            else:
                result = {
                    "success": False,
                    "error": "Unknown message type"
                }
            
            results.append(result)
            
        except json.JSONDecodeError as e:
            results.append({
                "success": False,
                "error": f"Invalid JSON in message: {str(e)}"
            })
            status_code = 400
        except Exception as e:
            results.append({
                "success": False,
                "error": f"Processing error: {str(e)}"
            })
            status_code = 500
    
    return {
        "statusCode": status_code,
        "body": json.dumps({"results": results}, default=str)
    }

def _process_discovery_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process a discovery request."""
    try:
        capabilities = body.get("capabilities", [])
        location = body.get("location")
        limit = body.get("limit", 10)
        request_id = body.get("request_id", "unknown")
        
        # Convert string capabilities to CapabilityType enum
        required_capabilities = []
        for cap in capabilities:
            try:
                required_capabilities.append(CapabilityType(cap))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid capability type: {cap}"
                }
        
        # Query the registry
        result = registry.discover_agents(
            required_capabilities=required_capabilities,
            location=location,
            max_results=limit
        )
        
        if result.get("success"):
            # Create discovery response
            agents = []
            for agent_data in result.get("agents", []):
                # Convert agent data to AgentMetadata
                agent = AgentMetadata(
                    agent_id=agent_data["agent_id"],
                    name=agent_data["name"],
                    description=agent_data["description"],
                    version=agent_data.get("version", "1.0.0"),
                    capabilities=agent_data.get("capabilities", []),
                    contact_info=agent_data.get("contact_info"),
                    location=agent_data.get("location"),
                    tags=agent_data.get("tags", []),
                    created_at=agent_data.get("created_at"),
                    last_seen=agent_data.get("last_seen"),
                    status=agent_data.get("status", "active")
                )
                agents.append(agent)
            
            discovery_response = DiscoveryResponse(
                request_id=request_id,
                agents=agents,
                total_found=len(agents),
                search_duration_ms=100  # Mock duration
            )
            
            return {
                "success": True,
                "discovery_response": discovery_response.dict(),
                "request_id": request_id
            }
        else:
            return result
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Discovery processing error: {str(e)}"
        }

def _process_agent_registration(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process an agent registration request."""
    try:
        agent_data = body.get("agent_data", {})
        agent_id = body.get("agent_id")
        
        if not agent_data:
            return {
                "success": False,
                "error": "No agent data provided"
            }
        
        # Import here to avoid circular imports
        from protocol import AgentCard, Capability
        
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
            "agent_id": agent_id,
            "message": result.get("message", "Registration processed"),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Registration processing error: {str(e)}"
        } 