"""
Registry Module

This module provides agent registration and discovery functionality
for the A2A system using DynamoDB as the backend storage.
"""

import boto3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
from protocol import AgentCard, CapabilityType, validate_agent_card


class AgentRegistry:
    """Manages agent registration and discovery using DynamoDB."""
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize the agent registry.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.table = self.dynamodb.Table(table_name)
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure AWS CLI.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise Exception(f"DynamoDB table '{table_name}' not found.")
            else:
                raise Exception(f"Error accessing DynamoDB: {str(e)}")
    
    def register_agent(self, agent_card: AgentCard) -> Dict[str, Any]:
        """
        Register an agent in the registry.
        
        Args:
            agent_card: The agent card containing agent metadata
            
        Returns:
            Dictionary with registration result
        """
        # Validate agent card
        validation_errors = validate_agent_card(agent_card)
        if validation_errors:
            return {
                'success': False,
                'errors': validation_errors
            }
        
        try:
            # Prepare item for DynamoDB
            item = {
                'agent_id': agent_card.agent_id,
                'name': agent_card.name,
                'description': agent_card.description,
                'version': agent_card.version,
                'capabilities': [cap.dict() for cap in agent_card.capabilities],
                'contact_info': agent_card.contact_info or {},
                'location': agent_card.location,
                'tags': agent_card.tags,
                'created_at': agent_card.created_at.isoformat(),
                'last_seen': datetime.utcnow().isoformat(),
                'status': 'active',
                'response_time_ms': agent_card.response_time_ms,
                'success_rate': agent_card.success_rate,
                'total_tasks_completed': agent_card.total_tasks_completed,
                'max_concurrent_tasks': agent_card.max_concurrent_tasks,
                'supported_protocols': agent_card.supported_protocols
            }
            
            # Add capability type indexes for efficient querying
            capability_types = [cap.type.value for cap in agent_card.capabilities]
            item['capability_types'] = capability_types
            
            # Add location index if available
            if agent_card.location:
                item['location_index'] = agent_card.location.lower()
            
            # Add tag indexes for efficient querying
            for tag in agent_card.tags:
                item[f'tag_{tag.lower()}'] = True
            
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            return {
                'success': True,
                'agent_id': agent_card.agent_id,
                'message': 'Agent registered successfully'
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'DynamoDB error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing agent's information.
        
        Args:
            agent_id: The agent ID to update
            updates: Dictionary of fields to update
            
        Returns:
            Dictionary with update result
        """
        try:
            # Build update expression
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                if key == 'capabilities':
                    # Handle capabilities specially
                    update_expression += f"{key} = :{key}, "
                    expression_values[f':{key}'] = [cap.dict() if hasattr(cap, 'dict') else cap for cap in value]
                elif key == 'capability_types':
                    update_expression += f"{key} = :{key}, "
                    expression_values[f':{key}'] = value
                elif key == 'last_seen':
                    update_expression += f"{key} = :{key}, "
                    expression_values[f':{key}'] = datetime.utcnow().isoformat()
                else:
                    update_expression += f"{key} = :{key}, "
                    expression_values[f':{key}'] = value
            
            # Remove trailing comma and space
            update_expression = update_expression.rstrip(', ')
            
            # Add condition to ensure agent exists
            condition_expression = "attribute_exists(agent_id)"
            
            self.table.update_item(
                Key={'agent_id': agent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression=condition_expression
            )
            
            return {
                'success': True,
                'message': 'Agent updated successfully'
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return {
                    'success': False,
                    'error': 'Agent not found'
                }
            else:
                return {
                    'success': False,
                    'error': f'Update failed: {str(e)}'
                }
    
    def deregister_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Deregister an agent from the registry.
        
        Args:
            agent_id: The agent ID to deregister
            
        Returns:
            Dictionary with deregistration result
        """
        try:
            self.table.delete_item(
                Key={'agent_id': agent_id}
            )
            
            return {
                'success': True,
                'message': 'Agent deregistered successfully'
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'Deregistration failed: {str(e)}'
            }
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: The agent ID to retrieve
            
        Returns:
            Agent data dictionary or None if not found
        """
        try:
            response = self.table.get_item(Key={'agent_id': agent_id})
            return response.get('Item')
        except ClientError:
            return None
    
    def discover_agents(
        self,
        required_capabilities: List[CapabilityType],
        optional_capabilities: Optional[List[CapabilityType]] = None,
        location: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_results: int = 10,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Discover agents based on criteria.
        
        Args:
            required_capabilities: List of required capabilities
            optional_capabilities: List of optional capabilities
            location: Preferred location
            tags: Required tags
            max_results: Maximum number of results
            active_only: Only return active agents
            
        Returns:
            Dictionary with discovery results
        """
        try:
            # Build filter expressions
            filter_expressions = []
            expression_values = {}
            
            # Filter by required capabilities
            if required_capabilities:
                capability_conditions = []
                for i, cap_type in enumerate(required_capabilities):
                    condition = f"contains(capability_types, :cap{i})"
                    capability_conditions.append(condition)
                    expression_values[f':cap{i}'] = cap_type.value
                
                if capability_conditions:
                    filter_expressions.append(f"({' AND '.join(capability_conditions)})")
            
            # Filter by location
            if location:
                filter_expressions.append("location_index = :location")
                expression_values[':location'] = location.lower()
            
            # Filter by tags
            if tags:
                tag_conditions = []
                for i, tag in enumerate(tags):
                    condition = f"tag_{tag.lower()} = :tag{i}"
                    tag_conditions.append(condition)
                    expression_values[f':tag{i}'] = True
                
                if tag_conditions:
                    filter_expressions.append(f"({' AND '.join(tag_conditions)})")
            
            # Filter by active status
            if active_only:
                filter_expressions.append("status = :status")
                expression_values[':status'] = 'active'
            
            # Build scan parameters
            scan_kwargs = {
                'Limit': max_results
            }
            
            if filter_expressions:
                scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
                scan_kwargs['ExpressionAttributeValues'] = expression_values
            
            # Perform scan
            response = self.table.scan(**scan_kwargs)
            agents = response.get('Items', [])
            
            # Sort by relevance (could be enhanced with scoring)
            agents.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
            
            return {
                'success': True,
                'agents': agents,
                'total_found': len(agents),
                'scanned_count': response.get('ScannedCount', 0)
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'Discovery failed: {str(e)}'
            }
    
    def list_all_agents(self, active_only: bool = True) -> Dict[str, Any]:
        """
        List all agents in the registry.
        
        Args:
            active_only: Only return active agents
            
        Returns:
            Dictionary with all agents
        """
        try:
            scan_kwargs = {}
            
            if active_only:
                scan_kwargs['FilterExpression'] = 'status = :status'
                scan_kwargs['ExpressionAttributeValues'] = {':status': 'active'}
            
            response = self.table.scan(**scan_kwargs)
            agents = response.get('Items', [])
            
            return {
                'success': True,
                'agents': agents,
                'total_count': len(agents)
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'Failed to list agents: {str(e)}'
            }
    
    def update_agent_heartbeat(self, agent_id: str) -> Dict[str, Any]:
        """
        Update an agent's last seen timestamp (heartbeat).
        
        Args:
            agent_id: The agent ID to update
            
        Returns:
            Dictionary with update result
        """
        return self.update_agent(agent_id, {
            'last_seen': datetime.utcnow().isoformat()
        })
    
    def cleanup_inactive_agents(self, timeout_minutes: int = 30) -> Dict[str, Any]:
        """
        Remove agents that haven't been seen for a while.
        
        Args:
            timeout_minutes: Minutes after which an agent is considered inactive
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            cutoff_iso = cutoff_time.isoformat()
            
            # Find inactive agents
            response = self.table.scan(
                FilterExpression='last_seen < :cutoff',
                ExpressionAttributeValues={':cutoff': cutoff_iso}
            )
            
            inactive_agents = response.get('Items', [])
            deleted_count = 0
            
            # Delete inactive agents
            for agent in inactive_agents:
                try:
                    self.table.delete_item(Key={'agent_id': agent['agent_id']})
                    deleted_count += 1
                except ClientError:
                    pass  # Continue with other agents
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'total_inactive': len(inactive_agents)
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'Cleanup failed: {str(e)}'
            }
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about registered agents.
        
        Returns:
            Dictionary with agent statistics
        """
        try:
            # Get all agents
            response = self.table.scan()
            agents = response.get('Items', [])
            
            # Calculate statistics
            total_agents = len(agents)
            active_agents = len([a for a in agents if a.get('status') == 'active'])
            
            # Count by capability type
            capability_counts = {}
            for agent in agents:
                for cap_type in agent.get('capability_types', []):
                    capability_counts[cap_type] = capability_counts.get(cap_type, 0) + 1
            
            # Count by location
            location_counts = {}
            for agent in agents:
                location = agent.get('location', 'Unknown')
                location_counts[location] = location_counts.get(location, 0) + 1
            
            return {
                'success': True,
                'statistics': {
                    'total_agents': total_agents,
                    'active_agents': active_agents,
                    'inactive_agents': total_agents - active_agents,
                    'capability_distribution': capability_counts,
                    'location_distribution': location_counts
                }
            }
            
        except ClientError as e:
            return {
                'success': False,
                'error': f'Failed to get statistics: {str(e)}'
            } 