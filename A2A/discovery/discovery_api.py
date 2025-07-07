"""
Discovery API Lambda Handler

Handles agent discovery and registration requests through API Gateway.
"""

import json
import os
import boto3
from typing import Dict, Any, List, Optional
from protocol import AgentCard, Capability, CapabilityType
from registry import AgentRegistry


class DiscoveryService:
    """Service class for discovery operations with dependency injection support."""
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        sqs_client=None,
        bedrock_client=None,
        bedrock_enabled: bool = True,
        bedrock_model: str = 'anthropic.claude-3-sonnet-20240229-v1:0'
    ):
        """
        Initialize the discovery service.
        
        Args:
            registry: AgentRegistry instance (injected for testing)
            sqs_client: SQS client (injected for testing)
            bedrock_client: Bedrock client (injected for testing)
            bedrock_enabled: Whether Bedrock is enabled
            bedrock_model: Bedrock model to use
        """
        self.registry = registry
        self.sqs_client = sqs_client
        self.bedrock_client = bedrock_client
        self.bedrock_enabled = bedrock_enabled
        self.bedrock_model = bedrock_model
    
    def get_agents(self, capabilities: List[str], location: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Get agents with optional filters."""
        if not self.registry:
            return {
                'success': False,
                'error': "Registry not available",
                'status_code': 503
            }
        
        try:
            # Convert string capabilities to CapabilityType enum
            required_capabilities = []
            for cap in capabilities:
                if cap.strip():
                    try:
                        required_capabilities.append(CapabilityType(cap.strip()))
                    except ValueError:
                        return {
                            'success': False,
                            'error': f"Invalid capability type: {cap}",
                            'status_code': 400
                        }
            
            # Query the registry
            result = self.registry.discover_agents(
                required_capabilities=required_capabilities,
                location=location,
                max_results=limit
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'agents': result.get('agents', []),
                        'total_found': result.get('total_found', 0),
                        'query_params': {
                            'capabilities': capabilities,
                            'location': location,
                            'limit': limit
                        }
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"Registry error: {result.get('error')}",
                    'status_code': 500
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Discovery error: {str(e)}",
                'status_code': 500
            }
    
    def register_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent."""
        try:
            # Validate required fields
            if not agent_data.get('name'):
                return {
                    'success': False,
                    'error': "Agent name is required",
                    'status_code': 400
                }
            
            if not agent_data.get('capabilities'):
                return {
                    'success': False,
                    'error': "At least one capability is required",
                    'status_code': 400
                }
            
            # Convert capabilities to proper format
            capabilities = []
            for cap_data in agent_data.get('capabilities', []):
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
                success_rate=1.0  # Default success rate for new agents
            )
            
            # Register the agent
            if not self.registry:
                return {
                    'success': False,
                    'error': "Registry not available",
                    'status_code': 503
                }
            
            result = self.registry.register_agent(agent_card)
            
            if result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'agent_id': agent_card.agent_id,
                        'message': 'Agent registered successfully',
                        'agent_card': agent_card.dict()
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"Registration failed: {result.get('error')}",
                    'status_code': 500
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Registration error: {str(e)}",
                'status_code': 500
            }
    
    def ai_discovery(self, task_description: str, max_agents: int = 5, 
                    required_capabilities: List[str] = None, location: Optional[str] = None,
                    priority: str = 'medium', min_confidence: Optional[float] = None) -> Dict[str, Any]:
        """AI-powered agent discovery."""
        if not self.bedrock_enabled:
            return {
                'success': False,
                'error': "AI-powered discovery is not available",
                'status_code': 503
            }
        
        # Input validation
        if not task_description:
            return {
                'success': False,
                'error': "Missing required field: task_description",
                'status_code': 400
            }
        if not isinstance(max_agents, int) or max_agents < 1:
            return {
                'success': False,
                'error': "max_agents must be a positive integer",
                'status_code': 400
            }
        
        try:
            # Use Bedrock to analyze the task if description provided
            task_analysis = None
            if task_description:
                task_analysis = self._analyze_task_with_bedrock(task_description)
                # Merge with user-provided capabilities
                if required_capabilities:
                    task_analysis['required_capabilities'] = list(set(
                        task_analysis.get('required_capabilities', []) + required_capabilities
                    ))
            else:
                # Use provided capabilities directly
                task_analysis = {
                    'required_capabilities': required_capabilities or [],
                    'priority': priority,
                    'complexity': 'medium'
                }
        except Exception as e:
            # Fallback to traditional selection if Bedrock fails
            if not self.registry:
                return {
                    'success': False,
                    'error': "Registry not available",
                    'status_code': 503
                }
            
            all_agents_result = self.registry.discover_agents(
                required_capabilities=required_capabilities or [],
                location=location
            )
            if not all_agents_result.get('success'):
                return {
                    'success': False,
                    'error': f"{all_agents_result.get('error')}",
                    'status_code': 500
                }
            available_agents = all_agents_result.get('agents', [])
            available_agents = [a.dict() if hasattr(a, 'dict') else a for a in available_agents]
            
            return {
                'success': True,
                'data': {
                    'selected_agents': available_agents[:max_agents],
                    'total_available': len(available_agents),
                    'selection_method': 'fallback_traditional',
                    'task_analysis': None,
                    'bedrock_error': str(e)
                }
            }
        
        # Get all available agents
        all_agents_result = self.registry.discover_agents(
            required_capabilities=task_analysis.get('required_capabilities', []),
            location=location
        )
        
        if not all_agents_result.get('success'):
            return {
                'success': False,
                'error': f"{all_agents_result.get('error')}",
                'status_code': 500
            }
        
        available_agents = all_agents_result.get('agents', [])
        available_agents = [a.dict() if hasattr(a, 'dict') else a for a in available_agents]
        
        if not available_agents:
            return {
                'success': True,
                'data': {
                    'selected_agents': [],
                    'total_available': 0,
                    'selection_method': 'ai_powered',
                    'task_analysis': task_analysis,
                    'message': 'No agents found matching requirements'
                }
            }
        
        # Use Bedrock to select the best agents
        try:
            selection_result = self._select_multiple_agents_with_bedrock(
                task_analysis, available_agents, max_agents
            )
            
            if selection_result.get('success'):
                selected_agents = selection_result.get('selected_agents', [])
                
                # Filter by confidence if specified
                if min_confidence is not None:
                    selected_agents = [
                        agent for agent in selected_agents
                        if agent.get('selection_metadata', {}).get('confidence_score', 0) >= min_confidence
                    ]
                
                return {
                    'success': True,
                    'data': {
                        'selected_agents': selected_agents,
                        'total_available': len(available_agents),
                        'selection_method': 'ai_powered',
                        'task_analysis': task_analysis
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"Agent selection failed: {selection_result.get('error')}",
                    'status_code': 500
                }
                
        except Exception as e:
            # Fallback to simple selection
            return {
                'success': True,
                'data': {
                    'selected_agents': available_agents[:max_agents],
                    'total_available': len(available_agents),
                    'selection_method': 'fallback_simple',
                    'task_analysis': task_analysis,
                    'selection_error': str(e)
                }
            }
    
    def get_recommendations(self, task_description: str, max_agents: int = 3) -> Dict[str, Any]:
        """Get AI-powered agent recommendations."""
        if not self.bedrock_enabled:
            return {
                'success': False,
                'error': "AI-powered recommendations are not available",
                'status_code': 503
            }
        
        if not task_description:
            return {
                'success': False,
                'error': "Missing required field: task_description",
                'status_code': 400
            }
        
        try:
            # Analyze task with Bedrock
            task_analysis = self._analyze_task_with_bedrock(task_description)
            
            # Get all available agents
            all_agents_result = self.registry.discover_agents()
            
            if not all_agents_result.get('success'):
                return {
                    'success': False,
                    'error': f"{all_agents_result.get('error')}",
                    'status_code': 500
                }
            
            available_agents = all_agents_result.get('agents', [])
            available_agents = [a.dict() if hasattr(a, 'dict') else a for a in available_agents]
            
            if not available_agents:
                return {
                    'success': True,
                    'data': {
                        'recommendations': [],
                        'task_analysis': task_analysis,
                        'message': 'No agents available for recommendations'
                    }
                }
            
            # Get recommendations using Bedrock
            recommendations_result = self._select_multiple_agents_with_bedrock(
                task_analysis, available_agents, max_agents
            )
            
            if recommendations_result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'recommendations': recommendations_result.get('selected_agents', []),
                        'task_analysis': task_analysis
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"Recommendations failed: {recommendations_result.get('error')}",
                    'status_code': 500
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Recommendations error: {str(e)}",
                'status_code': 500
            }
    
    def _analyze_task_with_bedrock(self, task_description: str) -> Dict[str, Any]:
        """Analyze task using Bedrock to extract capabilities and requirements."""
        prompt = f"""
        Analyze the following task description and extract the required capabilities and characteristics:
        
        Task: {task_description}
        
        Please provide a JSON response with the following structure:
        {{
            "required_capabilities": ["capability1", "capability2"],
            "priority": "low|medium|high",
            "complexity": "simple|medium|complex",
            "estimated_duration": "short|medium|long",
            "resource_requirements": ["requirement1", "requirement2"]
        }}
        
        Available capability types: text_processing, data_analysis, image_processing, audio_processing, 
        machine_learning, natural_language_processing, computer_vision, data_visualization, 
        web_scraping, api_integration, file_processing, database_operations, security_analysis, 
        network_monitoring, automation, reporting, optimization, translation, sentiment_analysis, 
        recommendation_engine
        
        Respond with only the JSON object, no additional text.
        """
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_model,
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.1
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['completion']
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise Exception("Could not parse JSON from Bedrock response")
                
        except Exception as e:
            raise Exception(f"Bedrock analysis failed: {str(e)}")
    
    def _select_multiple_agents_with_bedrock(self, task: Dict, available_agents: List[Dict], max_agents: int) -> Dict:
        """Use Bedrock to select the best agents for a task."""
        # Prepare agent information for Bedrock
        agents_info = []
        for agent in available_agents:
            agent_info = {
                'agent_id': agent.get('agent_id'),
                'name': agent.get('name'),
                'description': agent.get('description'),
                'capabilities': [cap.get('type') for cap in agent.get('capabilities', [])],
                'success_rate': agent.get('success_rate', 0.0),
                'response_time_ms': agent.get('response_time_ms'),
                'tags': agent.get('tags', [])
            }
            agents_info.append(agent_info)
        
        prompt = f"""
        Given the following task and available agents, select the best {max_agents} agents:
        
        Task Analysis:
        - Required Capabilities: {task.get('required_capabilities', [])}
        - Priority: {task.get('priority', 'medium')}
        - Complexity: {task.get('complexity', 'medium')}
        
        Available Agents ({len(agents_info)}):
        {json.dumps(agents_info, indent=2)}
        
        Please select the best {max_agents} agents and provide a JSON response with:
        {{
            "selected_agents": [
                {{
                    "agent_id": "agent_id",
                    "confidence_score": 0.95,
                    "reasoning": "Brief explanation of why this agent was selected",
                    "role": "primary|secondary|backup"
                }}
            ]
        }}
        
        Consider:
        1. Capability match with required capabilities
        2. Success rate and performance metrics
        3. Response time and availability
        4. Task complexity and agent expertise
        
        Respond with only the JSON object, no additional text.
        """
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_model,
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.2
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['completion']
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                selection_data = json.loads(json_match.group())
                selected_agent_ids = [agent['agent_id'] for agent in selection_data.get('selected_agents', [])]
                
                # Filter and enhance selected agents
                selected_agents = []
                for agent in available_agents:
                    if agent.get('agent_id') in selected_agent_ids:
                        # Find selection metadata
                        for selection in selection_data.get('selected_agents', []):
                            if selection['agent_id'] == agent.get('agent_id'):
                                agent['selection_metadata'] = {
                                    'confidence_score': selection.get('confidence_score', 0.8),
                                    'reasoning': selection.get('reasoning', 'Selected by AI'),
                                    'role': selection.get('role', 'primary')
                                }
                                break
                        selected_agents.append(agent)
                
                return {
                    'success': True,
                    'selected_agents': selected_agents
                }
            else:
                raise Exception("Could not parse JSON from Bedrock response")
                
        except Exception as e:
            raise Exception(f"Agent selection failed: {str(e)}")


# Global service instance for production use
_discovery_service = None

def get_discovery_service() -> DiscoveryService:
    """Get the global discovery service instance, creating it if necessary."""
    global _discovery_service
    
    if _discovery_service is None:
        # Initialize AWS services
        registry_table = os.environ.get("DISCOVERY_TABLE", "agent_registry")
        region = os.environ.get("AWS_REGION", "us-east-1")
        
        registry = AgentRegistry(registry_table, region)
        sqs_client = boto3.client('sqs', region_name=region)
        
        # Initialize Bedrock
        try:
            bedrock_client = boto3.client('bedrock-runtime', region_name=region)
            bedrock_enabled = True
            bedrock_model = 'anthropic.claude-3-sonnet-20240229-v1:0'
        except Exception as e:
            print(f"Bedrock initialization failed: {e}")
            bedrock_client = None
            bedrock_enabled = False
            bedrock_model = None
        
        _discovery_service = DiscoveryService(
            registry=registry,
            sqs_client=sqs_client,
            bedrock_client=bedrock_client,
            bedrock_enabled=bedrock_enabled,
            bedrock_model=bedrock_model
        )
    
    return _discovery_service


def lambda_handler(event, context):
    """Handle API Gateway requests for agent discovery and registration."""
    
    try:
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        
        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return _create_cors_response(200)
        
        # Get the discovery service
        service = get_discovery_service()
        
        if http_method == 'GET' and path == '/agents':
            return _handle_get_agents(event, service)
        elif http_method == 'POST' and path == '/agents':
            return _handle_post_agents(event, service)
        elif http_method == 'POST' and path == '/agents/discover':
            return _handle_ai_discovery(event, service)
        elif http_method == 'POST' and path == '/agents/recommendations':
            return _handle_get_recommendations(event, service)
        else:
            return _create_error_response(405, "Method not allowed")
            
    except Exception as e:
        return _create_error_response(500, f"Internal server error: {str(e)}")


def _handle_get_agents(event, service: DiscoveryService):
    """Handle GET /agents - Discover agents with optional filters."""
    query_params = event.get('queryStringParameters', {}) or {}
    capabilities = query_params.get('capabilities', '').split(',') if query_params.get('capabilities') else []
    location = query_params.get('location')
    limit = int(query_params.get('limit', 10))
    
    result = service.get_agents(capabilities, location, limit)
    
    if result.get('success'):
        return _create_success_response(result['data'])
    else:
        return _create_error_response(result.get('status_code', 500), result['error'])


def _handle_post_agents(event, service: DiscoveryService):
    """Handle POST /agents - Register a new agent."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        if not body:
            return _create_error_response(400, "Request body is required")
        
        result = service.register_agent(body)
        
        if result.get('success'):
            return _create_success_response(result['data'])
        else:
            return _create_error_response(result.get('status_code', 500), result['error'])
            
    except json.JSONDecodeError:
        return _create_error_response(400, "Invalid JSON in request body")


def _handle_ai_discovery(event, service: DiscoveryService):
    """Handle POST /agents/discover - AI-powered agent discovery."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        task_description = body.get('task_description', '')
        max_agents = body.get('max_agents', 5)
        required_capabilities = body.get('required_capabilities', [])
        location = body.get('location')
        priority = body.get('priority', 'medium')
        min_confidence = body.get('min_confidence')
        
        result = service.ai_discovery(
            task_description, max_agents, required_capabilities, 
            location, priority, min_confidence
        )
        
        if result.get('success'):
            return _create_success_response(result['data'])
        else:
            return _create_error_response(result.get('status_code', 500), result['error'])
            
    except json.JSONDecodeError:
        return _create_error_response(400, "Invalid JSON in request body")


def _handle_get_recommendations(event, service: DiscoveryService):
    """Handle POST /agents/recommendations - Get AI-powered recommendations."""
    try:
        body = json.loads(event.get('body', '{}'))
        
        task_description = body.get('task_description', '')
        max_agents = body.get('max_agents', 3)
        
        result = service.get_recommendations(task_description, max_agents)
        
        if result.get('success'):
            return _create_success_response(result['data'])
        else:
            return _create_error_response(result.get('status_code', 500), result['error'])
            
    except json.JSONDecodeError:
        return _create_error_response(400, "Invalid JSON in request body")


def _create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a successful API response."""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'success': True,
            'data': data
        })
    }


def _create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create an error API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }


def _create_cors_response(status_code: int) -> Dict[str, Any]:
    """Create a CORS preflight response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': ''
    } 