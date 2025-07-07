"""
Unit tests for the discovery system Lambda handlers.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import datetime

from discovery.discovery_api import DiscoveryService, lambda_handler as discovery_api_handler
from discovery.discovery_processor import lambda_handler as discovery_processor_handler
from discovery.agent_registration import lambda_handler as registration_handler
from protocol import (
    CapabilityType, DiscoveryRequest, DiscoveryResponse,
    AgentCard, Capability, Message, MessageType, AgentMetadata
)


class TestDiscoveryAPI:
    """Test discovery API Lambda handler."""
    
    def test_discovery_api_get_agents_success(self):
        """Test successful GET /agents endpoint."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing,data_analysis',
                'location': 'us-east-1',
                'limit': '5'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': True,
            'data': {
                'agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Test Agent',
                        'capabilities': [{'type': 'text_processing'}]
                    }
                ],
                'total_found': 1,
                'query_params': {
                    'capabilities': ['text_processing', 'data_analysis'],
                    'location': 'us-east-1',
                    'limit': 5
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'data' in body
            assert 'agents' in body['data']
    
    def test_discovery_api_get_agents_no_capabilities(self):
        """Test GET /agents endpoint without capabilities."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'location': 'us-east-1'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': True,
            'data': {
                'agents': [],
                'total_found': 0,
                'query_params': {
                    'capabilities': [],
                    'location': 'us-east-1',
                    'limit': 10
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
    
    def test_discovery_api_get_agents_invalid_capabilities(self):
        """Test GET /agents endpoint with invalid capabilities."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'invalid_capability',
                'location': 'us-east-1'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': False,
            'error': 'Invalid capability type: invalid_capability',
            'status_code': 400
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'invalid capability' in body['error'].lower()
    
    def test_discovery_api_get_agents_registry_error(self):
        """Test GET /agents endpoint with registry error."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing',
                'location': 'us-east-1'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': False,
            'error': 'Registry error: DynamoDB connection failed',
            'status_code': 500
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'error' in body
    
    def test_discovery_api_post_agents_success(self):
        """Test successful POST /agents endpoint."""
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ],
            'contact_info': {'email': 'test@example.com'},
            'location': 'us-east-1'
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(agent_data)
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.register_agent.return_value = {
            'success': True,
            'data': {
                'agent_id': 'agent-001',
                'message': 'Agent registered successfully',
                'agent_card': {
                    'agent_id': 'agent-001',
                    'name': 'Test Agent',
                    'capabilities': agent_data['capabilities']
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'data' in body
            assert 'agent_id' in body['data']
    
    def test_discovery_api_post_agents_invalid_data(self):
        """Test POST /agents endpoint with invalid data."""
        agent_data = {
            'name': '',  # Empty name should fail validation
            'description': 'A test agent',
            'capabilities': []  # Empty capabilities should fail validation
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(agent_data)
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.register_agent.return_value = {
            'success': False,
            'error': 'Agent name is required',
            'status_code': 400
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'error' in body
    
    def test_discovery_api_method_not_allowed(self):
        """Test unsupported HTTP method."""
        event = {
            'httpMethod': 'PUT',
            'path': '/agents'
        }
        
        response = discovery_api_handler(event, None)
        
        assert response['statusCode'] == 405
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'method not allowed' in body['error'].lower()
    
    def test_discovery_api_cors_headers(self):
        """Test CORS headers are included in response."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': True,
            'data': {
                'agents': [],
                'total_found': 0,
                'query_params': {
                    'capabilities': ['text_processing'],
                    'location': None,
                    'limit': 10
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert 'Access-Control-Allow-Headers' in response['headers']
            assert 'Access-Control-Allow-Methods' in response['headers']


class TestDiscoveryService:
    """Test DiscoveryService class directly."""
    
    def test_discovery_service_get_agents_success(self):
        """Test successful agent discovery."""
        mock_registry = Mock()
        mock_registry.discover_agents.return_value = {
            'success': True,
            'agents': [
                {
                    'agent_id': 'agent-001',
                    'name': 'Test Agent',
                    'capabilities': [{'type': 'text_processing'}]
                }
            ],
            'total_found': 1
        }
        
        service = DiscoveryService(registry=mock_registry)
        result = service.get_agents(['text_processing'], 'us-east-1', 5)
        
        assert result['success'] is True
        assert 'data' in result
        assert len(result['data']['agents']) == 1
        mock_registry.discover_agents.assert_called_once()
    
    def test_discovery_service_get_agents_no_registry(self):
        """Test agent discovery when registry is not available."""
        service = DiscoveryService(registry=None)
        result = service.get_agents(['text_processing'], 'us-east-1', 5)
        
        assert result['success'] is False
        assert result['status_code'] == 503
        assert 'Registry not available' in result['error']
    
    def test_discovery_service_get_agents_invalid_capability(self):
        """Test agent discovery with invalid capability."""
        mock_registry = Mock()
        service = DiscoveryService(registry=mock_registry)
        result = service.get_agents(['invalid_capability'], 'us-east-1', 5)
        
        assert result['success'] is False
        assert result['status_code'] == 400
        assert 'Invalid capability type' in result['error']
    
    def test_discovery_service_register_agent_success(self):
        """Test successful agent registration."""
        mock_registry = Mock()
        mock_registry.register_agent.return_value = {
            'success': True,
            'agent_id': 'agent-001',
            'message': 'Agent registered successfully'
        }
        
        service = DiscoveryService(registry=mock_registry)
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ]
        }
        
        result = service.register_agent(agent_data)
        
        assert result['success'] is True
        assert 'data' in result
        # The agent_id is auto-generated, so we just check that it exists
        assert 'agent_id' in result['data']
        mock_registry.register_agent.assert_called_once()
    
    def test_discovery_service_register_agent_no_registry(self):
        """Test agent registration when registry is not available."""
        service = DiscoveryService(registry=None)
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ]
        }
        
        result = service.register_agent(agent_data)
        
        assert result['success'] is False
        assert result['status_code'] == 503
        assert 'Registry not available' in result['error']
    
    def test_discovery_service_register_agent_missing_name(self):
        """Test agent registration with missing name."""
        mock_registry = Mock()
        service = DiscoveryService(registry=mock_registry)
        agent_data = {
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ]
        }
        
        result = service.register_agent(agent_data)
        
        assert result['success'] is False
        assert result['status_code'] == 400
        assert 'Agent name is required' in result['error']
    
    def test_discovery_service_register_agent_missing_capabilities(self):
        """Test agent registration with missing capabilities."""
        mock_registry = Mock()
        service = DiscoveryService(registry=mock_registry)
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': []
        }
        
        result = service.register_agent(agent_data)
        
        assert result['success'] is False
        assert result['status_code'] == 400
        assert 'At least one capability is required' in result['error']


class TestBedrockIntegration:
    """Test Bedrock integration features."""
    
    def test_ai_powered_discovery_endpoint(self):
        """Test AI-powered discovery endpoint."""
        event = {
            'httpMethod': 'POST',
            'path': '/agents/discover',
            'body': json.dumps({
                'task_description': 'Analyze customer feedback and generate sentiment report',
                'max_agents': 3,
                'required_capabilities': ['text_processing'],
                'location': 'us-east-1',
                'priority': 'high',
                'min_confidence': 0.8
            })
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.ai_discovery.return_value = {
            'success': True,
            'data': {
                'selected_agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Sentiment Analyzer',
                        'selection_metadata': {
                            'confidence_score': 0.95,
                            'reasoning': 'Excellent for sentiment analysis',
                            'role': 'primary'
                        }
                    }
                ],
                'total_available': 5,
                'selection_method': 'ai_powered',
                'task_analysis': {
                    'required_capabilities': ['text_processing', 'sentiment_analysis'],
                    'priority': 'high',
                    'complexity': 'medium'
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'data' in body
            assert 'selected_agents' in body['data']
            assert len(body['data']['selected_agents']) == 1
            assert body['data']['selection_method'] == 'ai_powered'
    
    def test_ai_recommendations_endpoint(self):
        """Test AI recommendations endpoint."""
        event = {
            'httpMethod': 'POST',
            'path': '/agents/recommendations',
            'body': json.dumps({
                'task_description': 'Process large dataset and create visualizations',
                'max_agents': 2
            })
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_recommendations.return_value = {
            'success': True,
            'data': {
                'recommendations': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Data Processor',
                        'selection_metadata': {
                            'confidence_score': 0.92,
                            'reasoning': 'Specialized in data processing',
                            'role': 'primary'
                        }
                    }
                ],
                'task_analysis': {
                    'required_capabilities': ['data_analysis', 'data_visualization'],
                    'priority': 'medium',
                    'complexity': 'high'
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'data' in body
            assert 'recommendations' in body['data']
            assert len(body['data']['recommendations']) == 1
    
    def test_bedrock_fallback_to_traditional_discovery(self):
        """Test fallback to traditional discovery when Bedrock fails."""
        event = {
            'httpMethod': 'POST',
            'path': '/agents/discover',
            'body': json.dumps({
                'task_description': 'Simple text processing task',
                'max_agents': 2
            })
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.ai_discovery.return_value = {
            'success': True,
            'data': {
                'selected_agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Text Processor',
                        'selection_metadata': {
                            'confidence_score': 0.85,
                            'reasoning': 'Selected by fallback method',
                            'role': 'primary'
                        }
                    }
                ],
                'total_available': 3,
                'selection_method': 'fallback_simple',
                'task_analysis': None,
                'selection_error': 'Bedrock service unavailable'
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['data']['selection_method'] == 'fallback_simple'
    
    def test_ai_powered_discovery_confidence_filtering(self):
        """Test confidence-based filtering in AI discovery."""
        event = {
            'httpMethod': 'POST',
            'path': '/agents/discover',
            'body': json.dumps({
                'task_description': 'Complex data analysis task',
                'max_agents': 5,
                'min_confidence': 0.9
            })
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.ai_discovery.return_value = {
            'success': True,
            'data': {
                'selected_agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'High Confidence Agent',
                        'selection_metadata': {
                            'confidence_score': 0.95,
                            'reasoning': 'High confidence match',
                            'role': 'primary'
                        }
                    }
                ],
                'total_available': 10,
                'selection_method': 'ai_powered',
                'task_analysis': {
                    'required_capabilities': ['data_analysis'],
                    'priority': 'high',
                    'complexity': 'complex'
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert len(body['data']['selected_agents']) == 1
            assert body['data']['selected_agents'][0]['selection_metadata']['confidence_score'] >= 0.9


class TestDiscoveryProcessor:
    """Test discovery processor Lambda handler."""
    
    def test_discovery_processor_success(self):
        """Test successful discovery processing."""
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'request_id': 'req-001',
                        'capabilities': ['text_processing'],
                        'location': 'us-east-1',
                        'max_results': 5
                    })
                }
            ]
        }
        
        # Mock the registry at the module level
        with patch('discovery.discovery_processor.registry') as mock_registry:
            mock_registry.discover_agents.return_value = {
                'success': True,
                'agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Test Agent',
                        'description': 'A test agent',
                        'version': '1.0.0',
                        'capabilities': [
                            {
                                'type': 'text_processing',
                                'name': 'Text Processing',
                                'description': 'Processes text',
                                'parameters': None,
                                'version': '1.0.0',
                                'confidence': 1.0
                            }
                        ],
                        'contact_info': None,
                        'location': 'us-east-1',
                        'tags': [],
                        'created_at': '2024-01-01T00:00:00Z',
                        'last_seen': '2024-01-01T00:00:00Z',
                        'status': 'active'
                    }
                ],
                'total_found': 1
            }
            
            # Import and call the handler
            from discovery.discovery_processor import lambda_handler
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['results']) == 1
            assert body['results'][0]['success'] is True
    
    def test_discovery_processor_registry_error(self):
        """Test discovery processing with registry error."""
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'request_id': 'req-001',
                        'capabilities': ['text_processing'],
                        'location': 'us-east-1',
                        'limit': 5
                    })
                }
            ]
        }
        
        # Mock the registry at the module level
        with patch('discovery.discovery_processor.registry') as mock_registry:
            mock_registry.discover_agents.return_value = {
                'success': False,
                'error': 'Registry error: DynamoDB connection failed'
            }
            
            # Import and call the handler
            from discovery.discovery_processor import lambda_handler
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert len(body['results']) == 1
            assert body['results'][0]['success'] is False
    
    def test_discovery_processor_invalid_message(self):
        """Test discovery processing with invalid message."""
        event = {
            'Records': [
                {
                    'body': 'invalid json'
                }
            ]
        }
        
        response = discovery_processor_handler(event, None)
        
        assert response['statusCode'] == 400
        assert 'error' in response['body']
    
    def test_discovery_processor_no_records(self):
        """Test discovery processing with no records."""
        event = {'Records': []}
        
        response = discovery_processor_handler(event, None)
        
        assert response['statusCode'] == 400
        assert 'No records found' in response['body']


class TestAgentRegistration:
    """Test agent registration Lambda handler."""
    
    def test_agent_registration_success(self):
        """Test successful agent registration."""
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ]
        }
        
        event = {
            'Records': [
                {
                    'body': json.dumps(agent_data)
                }
            ]
        }
        
        with patch('discovery.agent_registration.registry') as mock_registry:
            mock_registry.register_agent.return_value = {
                'success': True,
                'agent_id': 'agent-001',
                'message': 'Agent registered successfully'
            }
            
            response = registration_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['results']) == 1
            assert body['results'][0]['success'] is True
    
    def test_agent_registration_validation_error(self):
        """Test agent registration with validation error."""
        agent_data = {
            'name': '',  # Invalid empty name
            'description': 'A test agent',
            'capabilities': []
        }
        
        event = {
            'Records': [
                {
                    'body': json.dumps(agent_data)
                }
            ]
        }
        
        response = registration_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['results']) == 1
        assert body['results'][0]['success'] is False
        assert 'errors' in body['results'][0]
    
    def test_agent_registration_registry_error(self):
        """Test agent registration with registry error."""
        agent_data = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'capabilities': [
                {
                    'type': 'text_processing',
                    'name': 'Text Processing',
                    'description': 'Processes text'
                }
            ]
        }
        
        event = {
            'Records': [
                {
                    'body': json.dumps(agent_data)
                }
            ]
        }
        
        with patch('discovery.agent_registration.registry') as mock_registry:
            mock_registry.register_agent.return_value = {
                'success': False,
                'error': 'Registry error: DynamoDB connection failed'
            }
            
            response = registration_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['results']) == 1
            assert body['results'][0]['success'] is False
            # The registry error gets stored in 'errors' field
            assert 'errors' in body['results'][0] or 'error' in body['results'][0]
    
    def test_agent_registration_invalid_message(self):
        """Test agent registration with invalid message."""
        event = {
            'Records': [
                {
                    'body': 'invalid json'
                }
            ]
        }
        
        response = registration_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['results']) == 1
        assert body['results'][0]['success'] is False
        assert 'error' in body['results'][0]
    
    def test_agent_registration_no_records(self):
        """Test agent registration with no records."""
        event = {'Records': []}
        
        response = registration_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'] == []


class TestDiscoveryIntegration:
    """Test full discovery flow integration."""
    
    def test_full_discovery_flow(self):
        """Test complete discovery flow from API to processor."""
        # Test API endpoint
        api_event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing',
                'location': 'us-east-1',
                'limit': '3'
            }
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.get_agents.return_value = {
            'success': True,
            'data': {
                'agents': [
                    {
                        'agent_id': 'agent-001',
                        'name': 'Text Processor',
                        'capabilities': [{'type': 'text_processing'}]
                    }
                ],
                'total_found': 1,
                'query_params': {
                    'capabilities': ['text_processing'],
                    'location': 'us-east-1',
                    'limit': 3
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            api_response = discovery_api_handler(api_event, None)
            
            assert api_response['statusCode'] == 200
            body = json.loads(api_response['body'])
            assert body['success'] is True
            assert len(body['data']['agents']) == 1
    
    def test_agent_registration_flow(self):
        """Test complete agent registration flow."""
        # Test API endpoint
        agent_data = {
            'name': 'Integration Test Agent',
            'description': 'Agent for integration testing',
            'capabilities': [
                {
                    'type': 'data_analysis',
                    'name': 'Data Analysis',
                    'description': 'Analyzes data'
                }
            ],
            'contact_info': {'email': 'test@example.com'},
            'location': 'us-east-1'
        }
        
        api_event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(agent_data)
        }
        
        # Mock the discovery service
        mock_service = Mock(spec=DiscoveryService)
        mock_service.register_agent.return_value = {
            'success': True,
            'data': {
                'agent_id': 'integration-agent-001',
                'message': 'Agent registered successfully',
                'agent_card': {
                    'agent_id': 'integration-agent-001',
                    'name': 'Integration Test Agent',
                    'capabilities': agent_data['capabilities']
                }
            }
        }
        
        with patch('discovery.discovery_api.get_discovery_service', return_value=mock_service):
            api_response = discovery_api_handler(api_event, None)
            
            assert api_response['statusCode'] == 200
            body = json.loads(api_response['body'])
            assert body['success'] is True
            assert body['data']['agent_id'] == 'integration-agent-001' 