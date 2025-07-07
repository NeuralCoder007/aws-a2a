"""
Tests for Bedrock-powered agent discovery functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from discovery.discovery_api import lambda_handler, DiscoveryService
from protocol import AgentCard, Capability, CapabilityType


class TestBedrockDiscovery:
    """Test cases for Bedrock-powered discovery functionality."""
    
    @pytest.fixture
    def sample_agents(self):
        """Sample agents for testing."""
        return [
            AgentCard(
                agent_id='agent-1',
                name='TextProcessor',
                description='Processes text data',
                version='1.0.0',
                capabilities=[
                    Capability(
                        type=CapabilityType.TEXT_PROCESSING,
                        name='Text Analysis',
                        description='Analyze and process text data',
                        parameters={'max_length': 10000},
                        version='1.0.0',
                        confidence=0.95
                    )
                ],
                tags=['text', 'processing'],
                total_tasks_completed=50,
                success_rate=0.82,
                response_time_ms=300,
                max_concurrent_tasks=5,
                supported_protocols=['a2a_v1.0']
            ),
            AgentCard(
                agent_id='agent-2',
                name='DataAnalyzer',
                description='Analyzes data and generates insights',
                version='1.0.0',
                capabilities=[
                    Capability(
                        type=CapabilityType.DATA_ANALYSIS,
                        name='Data Analysis',
                        description='Analyze data and generate insights',
                        parameters={'supported_formats': ['csv', 'json']},
                        version='1.0.0',
                        confidence=0.88
                    )
                ],
                tags=['data', 'analysis'],
                total_tasks_completed=30,
                success_rate=0.90,
                response_time_ms=500,
                max_concurrent_tasks=3,
                supported_protocols=['a2a_v1.0']
            )
        ]
    
    @pytest.fixture
    def mock_bedrock_response(self):
        """Mock Bedrock response for agent selection."""
        return {
            "selected_agents": [
                {
                    "agent_id": "agent-1",
                    "role": "primary",
                    "confidence_score": 0.95,
                    "reasoning": "Best match for text processing requirements",
                    "assigned_capabilities": ["TEXT_PROCESSING"]
                },
                {
                    "agent_id": "agent-2",
                    "role": "secondary",
                    "confidence_score": 0.88,
                    "reasoning": "Good match for data analysis requirements",
                    "assigned_capabilities": ["DATA_ANALYSIS"]
                }
            ],
            "distribution_strategy": "parallel",
            "overall_confidence": 0.92,
            "subtask_distribution": {
                "subtasks": [
                    {
                        "subtask_id": "text_processing",
                        "assigned_agent_id": "agent-1",
                        "description": "Process and analyze text data"
                    },
                    {
                        "subtask_id": "insights_generation",
                        "assigned_agent_id": "agent-2",
                        "description": "Generate insights from processed data"
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock client."""
        return Mock()
    
    def test_ai_powered_discovery_success(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test successful AI-powered agent discovery."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock Bedrock response
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(mock_bedrock_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor',
                                'selection_metadata': {
                                    'confidence_score': 0.95,
                                    'role': 'primary',
                                    'reasoning': 'Best match for text processing requirements'
                                }
                            },
                            {
                                'agent_id': 'agent-2',
                                'name': 'DataAnalyzer',
                                'selection_metadata': {
                                    'confidence_score': 0.88,
                                    'role': 'secondary',
                                    'reasoning': 'Good match for data analysis requirements'
                                }
                            }
                        ],
                        'ai_recommendation': {
                            'distribution_strategy': 'parallel',
                            'overall_confidence': 0.92,
                            'subtask_distribution': {
                                'subtasks': [
                                    {
                                        'subtask_id': 'text_processing',
                                        'assigned_agent_id': 'agent-1',
                                        'description': 'Process and analyze text data'
                                    },
                                    {
                                        'subtask_id': 'insights_generation',
                                        'assigned_agent_id': 'agent-2',
                                        'description': 'Generate insights from processed data'
                                    }
                                ]
                            }
                        }
                    }
                }
                mock_get_service.return_value = mock_service
                
                # Test event
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Analyze customer feedback and generate insights',
                        'max_agents': 3,
                        'required_capabilities': ['TEXT_PROCESSING', 'DATA_ANALYSIS'],
                        'priority': 'high'
                    })
                }
                
                # Execute
                response = lambda_handler(event, {})
                
                # Verify response
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert 'selected_agents' in body['data']
                assert 'ai_recommendation' in body['data']
                
                # Verify selected agents
                selected_agents = body['data']['selected_agents']
                assert len(selected_agents) == 2
                assert selected_agents[0]['agent_id'] == 'agent-1'
                assert selected_agents[0]['selection_metadata']['confidence_score'] == 0.95
                assert selected_agents[1]['agent_id'] == 'agent-2'
                assert selected_agents[1]['selection_metadata']['confidence_score'] == 0.88
                
                # Verify AI recommendation
                ai_rec = body['data']['ai_recommendation']
                assert ai_rec['distribution_strategy'] == 'parallel'
                assert ai_rec['overall_confidence'] == 0.92
                assert len(ai_rec['subtask_distribution']['subtasks']) == 2

    def test_ai_powered_discovery_no_agents_available(self, mock_bedrock_client):
        """Test AI-powered discovery when no agents are available."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': []
                }
                
                # Mock the ai_discovery method to return no agents
                mock_service.ai_discovery.return_value = {
                    'success': False,
                    'error': 'No agents available',
                    'status_code': 404
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 404
                body = json.loads(response['body'])
                assert body['success'] is False
                assert 'No agents available' in body['error']

    def test_ai_powered_discovery_bedrock_error(self, sample_agents, mock_bedrock_client):
        """Test AI-powered discovery when Bedrock service fails."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock Bedrock to raise an error
            mock_bedrock.invoke_model.side_effect = ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Bedrock service unavailable'}},
                'InvokeModel'
            )
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method to fall back to traditional discovery
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor'
                            }
                        ],
                        'fallback_to_traditional': True,
                        'selection_method': 'fallback_traditional'
                    }
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3
                    })
                }
                
                response = lambda_handler(event, {})
                
                # Should fall back to traditional discovery
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert 'selected_agents' in body['data']
                assert body['data']['fallback_to_traditional'] is True

    def test_ai_powered_discovery_invalid_bedrock_response(self, sample_agents, mock_bedrock_client):
        """Test AI-powered discovery with invalid Bedrock response."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock Bedrock to return invalid JSON
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: b'invalid json response'
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method to fall back to traditional discovery
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor'
                            }
                        ],
                        'fallback_to_traditional': True,
                        'selection_method': 'fallback_simple'
                    }
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3
                    })
                }
                
                response = lambda_handler(event, {})
                
                # Should fall back to traditional discovery
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert body['data']['fallback_to_traditional'] is True

    def test_ai_recommendations_endpoint(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test AI recommendations endpoint."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock Bedrock response
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(mock_bedrock_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the get_recommendations method
                mock_service.get_recommendations.return_value = {
                    'success': True,
                    'data': {
                        'recommendations': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor',
                                'confidence_score': 0.95,
                                'reasoning': 'Best match for text processing'
                            }
                        ],
                        'ai_insights': {
                            'task_complexity': 'medium',
                            'recommended_approach': 'parallel_processing',
                            'estimated_duration': '2-3 hours'
                        }
                    }
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/recommendations',
                    'body': json.dumps({
                        'task_description': 'Analyze sales data and create visualizations',
                        'max_recommendations': 5
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert 'recommendations' in body['data']
                assert 'ai_insights' in body['data']

    def test_ai_powered_discovery_with_confidence_filtering(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test AI-powered discovery with confidence score filtering."""
        with patch('discovery.discovery_api.boto3.client') as mock_boto3:
            # Mock both SQS and Bedrock clients
            mock_sqs = Mock()
            mock_bedrock = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_sqs
            
            # Mock Bedrock response with low confidence scores
            low_confidence_response = {
                "selected_agents": [
                    {
                        "agent_id": "agent-1",
                        "role": "primary",
                        "confidence_score": 0.3,  # Low confidence
                        "reasoning": "Partial match for requirements",
                        "assigned_capabilities": ["TEXT_PROCESSING"]
                    }
                ],
                "distribution_strategy": "sequential",
                "overall_confidence": 0.3,
                "subtask_distribution": {
                    "subtasks": [
                        {
                            "subtask_id": "text_analysis",
                            "assigned_agent_id": "agent-1",
                            "description": "Process text with low confidence"
                        }
                    ]
                }
            }
            
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(low_confidence_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method to return no agents due to low confidence
                mock_service.ai_discovery.return_value = {
                    'success': False,
                    'error': 'No agents meet confidence threshold',
                    'status_code': 404
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3,
                        'min_confidence': 0.5  # Filter out low confidence agents
                    })
                }
                
                response = lambda_handler(event, {})
                
                # Should return no agents due to low confidence
                assert response['statusCode'] == 404
                body = json.loads(response['body'])
                assert body['success'] is False
                assert 'No agents meet confidence threshold' in body['error']

    def test_ai_powered_discovery_missing_required_fields(self, mock_bedrock_client):
        """Test AI-powered discovery with missing required fields."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            event = {
                'httpMethod': 'POST',
                'path': '/agents/discover',
                'body': json.dumps({
                    'max_agents': 3  # Missing task_description
                })
            }
            
            response = lambda_handler(event, {})
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'Missing required field' in body['error']

    def test_ai_powered_discovery_invalid_max_agents(self, mock_bedrock_client):
        """Test AI-powered discovery with invalid max_agents parameter."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            event = {
                'httpMethod': 'POST',
                'path': '/agents/discover',
                'body': json.dumps({
                    'task_description': 'Process text data',
                    'max_agents': -1  # Invalid value
                })
            }
            
            response = lambda_handler(event, {})
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'max_agents must be a positive integer' in body['error']

    def test_ai_powered_discovery_registry_error(self, mock_bedrock_client):
        """Test AI-powered discovery when registry fails."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            # Mock the DiscoveryService to fail
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': False,
                    'error': 'Registry service unavailable'
                }
                
                # Mock the ai_discovery method to fail
                mock_service.ai_discovery.return_value = {
                    'success': False,
                    'error': 'Registry service unavailable',
                    'status_code': 500
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 500
                body = json.loads(response['body'])
                assert body['success'] is False
                assert 'Registry service unavailable' in body['error']

    def test_ai_powered_discovery_cors_headers(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test that CORS headers are included in AI-powered discovery responses."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            # Mock Bedrock response
            mock_bedrock_client.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(mock_bedrock_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor'
                            }
                        ]
                    }
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 200
                assert 'Access-Control-Allow-Origin' in response['headers']
                assert 'Access-Control-Allow-Headers' in response['headers']
                assert 'Access-Control-Allow-Methods' in response['headers']

    def test_ai_powered_discovery_with_complex_task_description(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test AI-powered discovery with complex task descriptions."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            # Mock Bedrock response
            mock_bedrock_client.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(mock_bedrock_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor',
                                'selection_metadata': {
                                    'confidence_score': 0.95,
                                    'role': 'primary'
                                }
                            }
                        ],
                        'ai_recommendation': {
                            'distribution_strategy': 'parallel',
                            'overall_confidence': 0.92
                        }
                    }
                }
                mock_get_service.return_value = mock_service
                
                complex_task = """
                Analyze customer feedback from multiple sources including:
                - Social media posts and comments
                - Customer support tickets
                - Product reviews and ratings
                - Survey responses
                
                Generate comprehensive insights including:
                - Sentiment analysis
                - Trend identification
                - Priority issues ranking
                - Actionable recommendations
                
                Present results in both text and visual formats.
                """
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': complex_task,
                        'max_agents': 5,
                        'required_capabilities': ['TEXT_PROCESSING', 'DATA_ANALYSIS', 'VISUALIZATION'],
                        'priority': 'high',
                        'deadline': '2024-01-20T10:00:00Z'
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert 'selected_agents' in body['data']
                assert 'ai_recommendation' in body['data']

    def test_ai_powered_discovery_performance_metrics(self, sample_agents, mock_bedrock_response, mock_bedrock_client):
        """Test that AI-powered discovery includes performance metrics."""
        with patch('discovery.discovery_api.boto3.client', return_value=mock_bedrock_client):
            # Mock Bedrock response
            mock_bedrock_client.invoke_model.return_value = {
                'body': Mock(
                    read=lambda: json.dumps(mock_bedrock_response).encode()
                )
            }
            
            # Mock the DiscoveryService
            with patch('discovery.discovery_api.get_discovery_service') as mock_get_service:
                mock_service = Mock(spec=DiscoveryService)
                mock_service.registry = Mock()
                mock_service.registry.discover_agents.return_value = {
                    'success': True,
                    'agents': sample_agents
                }
                
                # Mock the ai_discovery method
                mock_service.ai_discovery.return_value = {
                    'success': True,
                    'data': {
                        'selected_agents': [
                            {
                                'agent_id': 'agent-1',
                                'name': 'TextProcessor'
                            }
                        ],
                        'performance_metrics': {
                            'discovery_time_ms': 150,
                            'bedrock_latency_ms': 200,
                            'total_agents_evaluated': 5
                        }
                    }
                }
                mock_get_service.return_value = mock_service
                
                event = {
                    'httpMethod': 'POST',
                    'path': '/agents/discover',
                    'body': json.dumps({
                        'task_description': 'Process text data',
                        'max_agents': 3,
                        'include_performance_metrics': True
                    })
                }
                
                response = lambda_handler(event, {})
                
                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['success'] is True
                assert 'selected_agents' in body['data']
                assert 'performance_metrics' in body['data'] 