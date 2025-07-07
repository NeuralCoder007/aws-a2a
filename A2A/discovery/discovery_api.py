"""
Discovery API Lambda Handler

Handles API Gateway requests for agent registration, discovery, and listing.
"""

import json
import os
import uuid
from typing import Any, Dict
from protocol import AgentCard, CapabilityType
from registry import AgentRegistry

REGISTRY_TABLE = os.environ.get("DISCOVERY_TABLE", "agent_registry")
REGION = os.environ.get("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("DISCOVERY_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/discovery-queue")

registry = AgentRegistry(REGISTRY_TABLE, REGION)

def lambda_handler(event, context):
    """Main Lambda handler for API Gateway events."""
    path = event.get("path", "")
    http_method = event.get("httpMethod", "GET")
    body = event.get("body")
    query = event.get("queryStringParameters") or {}
    
    # Handle CORS preflight requests
    if http_method == "OPTIONS":
        return _cors_response(200, {})
    
    # Handle GET /agents - list all agents
    if path.endswith("/agents") and http_method == "GET":
        return _handle_get_agents(query)
    
    # Handle POST /agents - register new agent
    if path.endswith("/agents") and http_method == "POST":
        return _handle_post_agents(body)
    
    # Handle other endpoints
    if path.endswith("/register") and http_method == "POST":
        data = json.loads(body)
        card = AgentCard(**data)
        result = registry.register_agent(card)
        return _cors_response(200 if result['success'] else 400, result)
    
    if path.endswith("/request") and http_method == "POST":
        data = json.loads(body)
        required = [CapabilityType(x) for x in data.get("required_capabilities", [])]
        location = data.get("location_preference")
        tags = data.get("tags")
        result = registry.discover_agents(required_capabilities=required, location=location, tags=tags)
        return _cors_response(200, result)
    
    # Method not allowed
    if path.endswith("/agents"):
        return _cors_response(405, {
            "success": False,
            "error": "Method not allowed"
        })
    
    return _cors_response(404, {"error": "Not found"})

def _handle_get_agents(query: Dict[str, str]) -> Dict[str, Any]:
    """Handle GET /agents requests."""
    capabilities = query.get('capabilities', '')
    location = query.get('location')
    limit = int(query.get('limit', '10'))
    
    # Validate capabilities parameter
    if not capabilities:
        return _cors_response(400, {
            "success": False,
            "error": "Capabilities parameter is required"
        })
    
    # Parse capabilities
    try:
        capability_list = [cap.strip() for cap in capabilities.split(',')]
        # Validate capability types
        for cap in capability_list:
            if cap not in [ct.value for ct in CapabilityType]:
                return _cors_response(400, {
                    "success": False,
                    "error": f"Invalid capability: {cap}"
                })
    except Exception:
        return _cors_response(400, {
            "success": False,
            "error": "Invalid capabilities format"
        })
    
    # Send message to SQS for processing
    try:
        import boto3
        sqs = boto3.client('sqs')
        
        message_body = {
            "request_id": str(uuid.uuid4()),
            "capabilities": capability_list,
            "location": location,
            "limit": limit,
            "timestamp": str(uuid.uuid4())
        }
        
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        
        return _cors_response(200, {
            "success": True,
            "request_id": message_body["request_id"],
            "message": "Discovery request submitted successfully"
        })
        
    except Exception as e:
        return _cors_response(500, {
            "success": False,
            "error": f"Failed to submit discovery request: {str(e)}"
        })

def _handle_post_agents(body: str) -> Dict[str, Any]:
    """Handle POST /agents requests."""
    if not body:
        return _cors_response(400, {
            "success": False,
            "error": "Request body is required"
        })
    
    try:
        agent_data = json.loads(body)
        
        # Validate required fields
        if not agent_data.get('name'):
            return _cors_response(400, {
                "success": False,
                "errors": ["Agent name is required"]
            })
        
        if not agent_data.get('capabilities'):
            return _cors_response(400, {
                "success": False,
                "errors": ["At least one capability is required"]
            })
        
        # Create agent card
        card = AgentCard(**agent_data)
        
        # Send to SQS for processing
        import boto3
        sqs = boto3.client('sqs')
        
        message_body = {
            "agent_id": str(uuid.uuid4()),
            "agent_data": agent_data,
            "timestamp": str(uuid.uuid4())
        }
        
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        
        return _cors_response(200, {
            "success": True,
            "agent_id": message_body["agent_id"],
            "message": "Agent registration request submitted successfully"
        })
        
    except json.JSONDecodeError:
        return _cors_response(400, {
            "success": False,
            "errors": ["Invalid JSON in request body"]
        })
    except Exception as e:
        return _cors_response(500, {
            "success": False,
            "error": f"Failed to process registration: {str(e)}"
        })

def _cors_response(status: int, body: Any) -> Dict[str, Any]:
    """Create a response with CORS headers."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body)
    } 