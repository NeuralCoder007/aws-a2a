"""
Unit tests for the A2A registry module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from registry import AgentRegistry
from protocol import AgentCard, Capability, CapabilityType


class TestAgentRegistry:
    """Test AgentRegistry class."""
    
    @patch('boto3.resource')
    def test_registry_initialization(self, mock_boto3):
        """Test registry initialization."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        assert registry.table_name == "test-table"
        assert registry.region == "us-east-1"
        assert registry.table == mock_table
    
    @patch('boto3.resource')
    def test_registry_initialization_no_credentials(self, mock_boto3):
        """Test registry initialization without AWS credentials."""
        from botocore.exceptions import NoCredentialsError
        mock_boto3.side_effect = NoCredentialsError()
        
        with pytest.raises(Exception, match="AWS credentials not found"):
            AgentRegistry("test-table", "us-east-1")
    
    @patch('boto3.resource')
    def test_registry_initialization_table_not_found(self, mock_boto3):
        """Test registry initialization with non-existent table."""
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_boto3.side_effect = ClientError(error_response, 'DescribeTable')
        
        with pytest.raises(Exception, match="DynamoDB table 'test-table' not found"):
            AgentRegistry("test-table", "us-east-1")
    
    @patch('boto3.resource')
    def test_register_agent_success(self, mock_boto3):
        """Test successful agent registration."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent_card = AgentCard(
            agent_id="test-agent-001",
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            success_rate=1.0
        )
        
        result = registry.register_agent(agent_card)
        
        assert result['success'] is True
        assert result['agent_id'] == "test-agent-001"
        assert "successfully" in result['message']
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert call_args['agent_id'] == "test-agent-001"
        assert call_args['name'] == "Test Agent"
        assert call_args['capability_types'] == ["text_processing"]
    
    @patch('boto3.resource')
    def test_register_agent_validation_error(self, mock_boto3):
        """Test agent registration with validation errors."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        # Create invalid agent card (missing required fields)
        agent_card = AgentCard(
            agent_id="test-agent-001",
            name="",  # Empty name should fail validation
            description="A test agent",
            capabilities=[],  # Empty capabilities should fail validation
            success_rate=1.0
        )
        
        result = registry.register_agent(agent_card)
        
        assert result['success'] is False
        assert 'errors' in result
        assert len(result['errors']) > 0
    
    @patch('boto3.resource')
    def test_register_agent_dynamodb_error(self, mock_boto3):
        """Test agent registration with DynamoDB error."""
        from botocore.exceptions import ClientError
        
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}}, 
            'PutItem'
        )
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        capabilities = [
            Capability(
                type=CapabilityType.TEXT_PROCESSING,
                name="Text Processing",
                description="Processes text"
            )
        ]
        
        agent_card = AgentCard(
            agent_id="test-agent-001",
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities,
            success_rate=1.0
        )
        
        result = registry.register_agent(agent_card)
        
        assert result['success'] is False
        assert "DynamoDB error" in result['error']
    
    @patch('boto3.resource')
    def test_get_agent_success(self, mock_boto3):
        """Test successful agent retrieval."""
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'agent_id': 'test-agent-001',
                'name': 'Test Agent',
                'description': 'A test agent'
            }
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        agent = registry.get_agent("test-agent-001")
        
        assert agent is not None
        assert agent['agent_id'] == "test-agent-001"
        assert agent['name'] == "Test Agent"
        
        mock_table.get_item.assert_called_once_with(Key={'agent_id': 'test-agent-001'})
    
    @patch('boto3.resource')
    def test_get_agent_not_found(self, mock_boto3):
        """Test agent retrieval when agent doesn't exist."""
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        agent = registry.get_agent("non-existent-agent")
        
        assert agent is None
    
    @patch('boto3.resource')
    def test_discover_agents_success(self, mock_boto3):
        """Test successful agent discovery."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'capability_types': ['text_processing'],
                    'status': 'active'
                },
                {
                    'agent_id': 'agent-2',
                    'name': 'Agent 2',
                    'capability_types': ['data_analysis'],
                    'status': 'active'
                }
            ],
            'ScannedCount': 2
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.discover_agents([CapabilityType.TEXT_PROCESSING])
        
        assert result['success'] is True
        assert result['total_found'] == 2
        assert result['scanned_count'] == 2
        assert len(result['agents']) == 2
    
    @patch('boto3.resource')
    def test_discover_agents_with_filters(self, mock_boto3):
        """Test agent discovery with filters."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'capability_types': ['text_processing'],
                    'status': 'active',
                    'location_index': 'us-east-1'
                }
            ],
            'ScannedCount': 1
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.discover_agents(
            required_capabilities=[CapabilityType.TEXT_PROCESSING],
            location="us-east-1",
            tags=["test"]
        )
        
        assert result['success'] is True
        assert result['total_found'] == 1
    
    @patch('boto3.resource')
    def test_discover_agents_dynamodb_error(self, mock_boto3):
        """Test agent discovery with DynamoDB error."""
        from botocore.exceptions import ClientError
        
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException'}}, 
            'Scan'
        )
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.discover_agents([CapabilityType.TEXT_PROCESSING])
        
        assert result['success'] is False
        assert "Discovery failed" in result['error']
    
    @patch('boto3.resource')
    def test_list_all_agents_success(self, mock_boto3):
        """Test successful listing of all agents."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'status': 'active'
                },
                {
                    'agent_id': 'agent-2',
                    'name': 'Agent 2',
                    'status': 'inactive'
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.list_all_agents(active_only=False)
        
        assert result['success'] is True
        assert result['total_count'] == 2
        assert len(result['agents']) == 2
    
    @patch('boto3.resource')
    def test_list_all_agents_active_only(self, mock_boto3):
        """Test listing only active agents."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'status': 'active'
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.list_all_agents(active_only=True)
        
        assert result['success'] is True
        assert result['total_count'] == 1
        assert len(result['agents']) == 1
    
    @patch('boto3.resource')
    def test_update_agent_success(self, mock_boto3):
        """Test successful agent update."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        updates = {
            'name': 'Updated Agent',
            'description': 'Updated description'
        }
        
        result = registry.update_agent("test-agent-001", updates)
        
        assert result['success'] is True
        assert "successfully" in result['message']
        
        # Verify DynamoDB update_item was called
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args['Key'] == {'agent_id': 'test-agent-001'}
        assert 'UpdateExpression' in call_args
    
    @patch('boto3.resource')
    def test_update_agent_not_found(self, mock_boto3):
        """Test agent update when agent doesn't exist."""
        from botocore.exceptions import ClientError
        
        mock_table = Mock()
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}}, 
            'UpdateItem'
        )
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.update_agent("non-existent-agent", {'name': 'New Name'})
        
        assert result['success'] is False
        assert result['error'] == 'Agent not found'
    
    @patch('boto3.resource')
    def test_deregister_agent_success(self, mock_boto3):
        """Test successful agent deregistration."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.deregister_agent("test-agent-001")
        
        assert result['success'] is True
        assert "successfully" in result['message']
        
        # Verify DynamoDB delete_item was called
        mock_table.delete_item.assert_called_once_with(Key={'agent_id': 'test-agent-001'})
    
    @patch('boto3.resource')
    def test_update_agent_heartbeat(self, mock_boto3):
        """Test agent heartbeat update."""
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.update_agent_heartbeat("test-agent-001")
        
        assert result['success'] is True
        assert "successfully" in result['message']
        
        # Verify DynamoDB update_item was called with last_seen update
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]
        assert call_args['Key'] == {'agent_id': 'test-agent-001'}
        assert ':last_seen' in call_args['ExpressionAttributeValues']
    
    @patch('boto3.resource')
    def test_cleanup_inactive_agents(self, mock_boto3):
        """Test cleanup of inactive agents."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'inactive-agent-1',
                    'last_seen': (datetime.utcnow() - timedelta(hours=2)).isoformat()
                },
                {
                    'agent_id': 'inactive-agent-2',
                    'last_seen': (datetime.utcnow() - timedelta(hours=3)).isoformat()
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.cleanup_inactive_agents(timeout_minutes=30)
        
        assert result['success'] is True
        assert result['total_inactive'] == 2
        assert result['deleted_count'] == 2
        
        # Verify delete_item was called for each inactive agent
        assert mock_table.delete_item.call_count == 2
    
    @patch('boto3.resource')
    def test_get_agent_statistics(self, mock_boto3):
        """Test getting agent statistics."""
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'agent_id': 'agent-1',
                    'name': 'Agent 1',
                    'status': 'active',
                    'capability_types': ['text_processing'],
                    'location': 'us-east-1'
                },
                {
                    'agent_id': 'agent-2',
                    'name': 'Agent 2',
                    'status': 'inactive',
                    'capability_types': ['data_analysis'],
                    'location': 'us-west-2'
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table
        
        registry = AgentRegistry("test-table", "us-east-1")
        
        result = registry.get_agent_statistics()
        
        assert result['success'] is True
        stats = result['statistics']
        assert stats['total_agents'] == 2
        assert stats['active_agents'] == 1
        assert stats['inactive_agents'] == 1
        assert 'text_processing' in stats['capability_distribution']
        assert 'data_analysis' in stats['capability_distribution']
        assert 'us-east-1' in stats['location_distribution']
        assert 'us-west-2' in stats['location_distribution'] 