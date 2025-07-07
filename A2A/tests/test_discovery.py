"""
Unit tests for the discovery system Lambda handlers.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from discovery.discovery_api import lambda_handler as discovery_api_handler
from discovery.discovery_processor import lambda_handler as discovery_processor_handler
from discovery.agent_registration import lambda_handler as registration_handler
from protocol import (
    CapabilityType, DiscoveryRequest, DiscoveryResponse,
    AgentCard, Capability, Message, MessageType
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
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
            
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'request_id' in body
            assert body['message'] == 'Discovery request submitted successfully'
    
    def test_discovery_api_get_agents_no_capabilities(self):
        """Test GET /agents endpoint without capabilities."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'location': 'us-east-1'
            }
        }
        
        response = discovery_api_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'capabilities' in body['error'].lower()
    
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
        
        response = discovery_api_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'invalid capability' in body['error'].lower()
    
    def test_discovery_api_get_agents_sqs_error(self):
        """Test GET /agents endpoint with SQS error."""
        event = {
            'httpMethod': 'GET',
            'path': '/agents',
            'queryStringParameters': {
                'capabilities': 'text_processing',
                'location': 'us-east-1'
            }
        }
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.side_effect = Exception("SQS error")
            
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
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
            
            response = discovery_api_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'agent_id' in body
            assert body['message'] == 'Agent registration request submitted successfully'
    
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
        
        response = discovery_api_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'errors' in body
    
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
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
            
            response = discovery_api_handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert 'Access-Control-Allow-Headers' in response['headers']
            assert 'Access-Control-Allow-Methods' in response['headers']


class TestDiscoveryProcessor:
    """Test discovery processor Lambda handler."""
    
    def test_discovery_processor_success(self):
        """Test successful discovery processing."""
        discovery_request = DiscoveryRequest(
            request_id="req-001",
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            location_preference="us-east-1",
            max_results=5
        )
        
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'request_id': discovery_request.request_id,
                        'capabilities': [cap.value for cap in discovery_request.required_capabilities],
                        'location': discovery_request.location_preference,
                        'limit': discovery_request.max_results
                    })
                }
            ]
        }
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs

            with patch('discovery.discovery_processor.registry') as mock_registry:
                mock_registry.discover_agents.return_value = {
                    'success': True,
                    'agents': [
                        {
                            'agent_id': 'agent-1',
                            'name': 'Agent 1',
                            'description': 'Test agent',
                            'version': '1.0.0',
                            'capabilities': [],
                            'contact_info': None,
                            'location': 'us-east-1',
                            'tags': [],
                            'created_at': datetime(2024, 1, 1, 0, 0, 0),
                            'last_seen': datetime(2024, 1, 1, 0, 0, 0),
                            'status': 'active'
                        }
                    ],
                    'total_found': 1
                }

                response = discovery_processor_handler(event, None)

                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert len(body['results']) == 1
                assert body['results'][0]['success'] is True

                # Verify registry was called
                mock_registry.discover_agents.assert_called_once()
    
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
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            
            with patch('discovery.discovery_processor.registry') as mock_registry:
                mock_registry.discover_agents.return_value = {
                    'success': False,
                    'error': 'Registry error'
                }
                
                response = discovery_processor_handler(event, None)
                
                assert response['statusCode'] == 500
                assert 'error' in response['body']
    
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
        agent_data = {
            'agent_id': 'test-agent-001',
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
            'Records': [
                {
                    'body': json.dumps(agent_data)
                }
            ]
        }
        with patch('discovery.agent_registration.registry') as mock_registry:
            mock_registry.register_agent.return_value = {
                'success': True,
                'agent_id': 'test-agent-001',
                'message': 'Agent registered successfully'
            }
            response = registration_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['results'][0]['success'] is True
            assert 'agent_id' in body['results'][0]

    def test_agent_registration_validation_error(self):
        """Test agent registration with validation error."""
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'agent_data': {
                            'name': '',  # Invalid empty name
                            'description': 'A test agent',
                            'capabilities': []
                        }
                    })
                }
            ]
        }
        response = registration_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['success'] is False
        assert 'error' in body['results'][0]

    def test_agent_registration_registry_error(self):
        """Test agent registration with registry error."""
        agent_data = {
            'agent_id': 'test-agent-001',
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
                'error': 'Registry error'
            }
            response = registration_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['results'][0]['success'] is False
            assert 'errors' in body['results'][0]

    def test_agent_registration_invalid_message(self):
        """Test agent registration with invalid message format."""
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
        assert body['results'][0]['success'] is False
        assert 'error' in body['results'][0]

    def test_agent_registration_no_records(self):
        """Test agent registration with no records."""
        event = {}
        response = registration_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'] == []


class TestDiscoveryIntegration:
    """Test discovery system integration scenarios."""
    
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
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
            
            api_response = discovery_api_handler(api_event, None)
            assert api_response['statusCode'] == 200
            
            # Extract the message that would be sent to SQS
            call_args = mock_sqs.send_message.call_args[1]
            message_body = json.loads(call_args['MessageBody'])
            
            # Test processor with the same message
            processor_event = {
                'Records': [
                    {
                        'body': call_args['MessageBody']
                    }
                ]
            }
            
            with patch('discovery.discovery_processor.registry') as mock_registry:
                mock_registry.discover_agents.return_value = {
                    'success': True,
                    'agents': [
                        {
                            'agent_id': 'agent-1',
                            'name': 'Text Processor',
                            'description': 'A text processing agent',
                            'capabilities': [],
                            'location': 'us-east-1',
                            'created_at': '2024-01-01T00:00:00Z',
                            'last_seen': '2024-01-02T00:00:00Z'
                        }
                    ],
                    'total_found': 1
                }
                
                processor_response = discovery_processor_handler(processor_event, None)
                print(f"Processor response: {processor_response}")
                assert processor_response['statusCode'] == 200
    
    def test_agent_registration_flow(self):
        """Test complete agent registration flow."""
        # Test API endpoint
        agent_data = {
            'name': 'New Agent',
            'description': 'A new agent',
            'capabilities': [
                {
                    'type': 'data_analysis',
                    'name': 'Data Analysis',
                    'description': 'Analyzes data'
                }
            ],
            'contact_info': {'email': 'new@example.com'},
            'location': 'us-west-2'
        }
        
        api_event = {
            'httpMethod': 'POST',
            'path': '/agents',
            'body': json.dumps(agent_data)
        }
        
        with patch('boto3.client') as mock_boto3:
            mock_sqs = Mock()
            mock_boto3.return_value = mock_sqs
            mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
            
            api_response = discovery_api_handler(api_event, None)
            assert api_response['statusCode'] == 200
            
            # Extract the message that would be sent to SQS
            call_args = mock_sqs.send_message.call_args[1]
            message_body = json.loads(call_args['MessageBody'])
            
            # Test registration handler with the same message
            registration_event = {
                'Records': [
                    {
                        'body': call_args['MessageBody']
                    }
                ]
            }
            
            with patch('registry.AgentRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry.register_agent.return_value = {
                    'success': True,
                    'agent_id': message_body.get('agent_id'),
                    'message': 'Agent registered successfully'
                }
                mock_registry_class.return_value = mock_registry
                
                registration_response = registration_handler(registration_event, None)
                assert registration_response['statusCode'] == 200 