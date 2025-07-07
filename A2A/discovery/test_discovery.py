"""
Test script for the discovery system.
"""

import os
import pytest
from protocol import AgentCard, Capability, CapabilityType
from registry import AgentRegistry
from unittest.mock import patch, Mock

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE = os.environ.get("DISCOVERY_TABLE", "agent_registry_test")

@pytest.fixture(scope="module")
def registry():
    return AgentRegistry(TABLE, REGION)

@patch('boto3.resource')
def test_agent_registration(mock_boto3_resource):
    mock_table = Mock()
    mock_boto3_resource.return_value.Table.return_value = mock_table
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    from registry import AgentRegistry
    registry = AgentRegistry('dummy_table')
    card = AgentCard(
        name="TestAgent",
        description="A test agent",
        capabilities=[Capability(type=CapabilityType.TEXT_PROCESSING, name="TextProc", description="Text processing")],
    )
    result = registry.register_agent(card)
    assert result["success"] is True
    assert result["agent_id"] == card.agent_id

@patch('boto3.resource')
def test_discovery(mock_boto3_resource):
    mock_table = Mock()
    mock_boto3_resource.return_value.Table.return_value = mock_table
    mock_table.scan.return_value = {"Items": [{
        "agent_id": "agent-1",
        "name": "TestAgent",
        "description": "A test agent",
        "capabilities": [
            {"type": "text_processing", "name": "TextProc", "description": "Text processing"}
        ],
        "location": "us-east-1"
    }]}
    from registry import AgentRegistry
    registry = AgentRegistry('dummy_table')
    result = registry.discover_agents([CapabilityType.TEXT_PROCESSING])
    assert result["success"] is True
    assert result["total_found"] == 1
    assert result["agents"][0]["name"] == "TestAgent" 