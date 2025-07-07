"""
Base Agent

This module provides a base class for creating agents in the A2A system.
All agents should extend this base class to ensure consistent behavior.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from protocol import (
    CapabilityType, AgentCard, Capability, Message, MessageType, Task,
    create_message, validate_message
)
from registry import AgentRegistry


class BaseAgent(ABC):
    """
    Base class for all agents in the A2A system.
    
    This class provides common functionality for agent registration,
    message handling, and task execution.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        capabilities: List[Capability],
        agent_id: Optional[str] = None,
        region: str = 'us-east-1',
        registry_table: Optional[str] = None,
        message_queue: Optional[str] = None
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            description: Agent description
            capabilities: List of agent capabilities
            agent_id: Optional custom agent ID
            region: AWS region
            registry_table: DynamoDB table name for registry
            message_queue: SQS queue name for messages
        """
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.agent_id = agent_id or f"{name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.region = region
        
        # Initialize AWS services
        self.sqs = boto3.client('sqs', region_name=region)
        self.registry = AgentRegistry(registry_table, region) if registry_table else None
        
        # Message queue configuration
        self.message_queue_url = None
        if message_queue:
            try:
                response = self.sqs.get_queue_url(QueueName=message_queue)
                self.message_queue_url = response['QueueUrl']
            except ClientError as e:
                logging.warning(f"Could not get queue URL for {message_queue}: {e}")
        
        # Agent state
        self.is_registered = False
        self.is_running = False
        self.current_tasks: Dict[str, Task] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.task_handlers: Dict[CapabilityType, Callable] = {}
        
        # Performance metrics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.response_times: List[float] = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"Agent_{self.name}")
        
        # Register default message handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self.register_message_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.register_message_handler(MessageType.DISCOVERY_REQUEST, self._handle_discovery_request)
        self.register_message_handler(MessageType.TASK_REQUEST, self._handle_task_request)
        self.register_message_handler(MessageType.REGISTRATION, self._handle_registration)
        self.register_message_handler(MessageType.DEREGISTRATION, self._handle_deregistration)
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler
        self.logger.info(f"Registered handler for message type: {message_type}")
    
    def register_task_handler(self, capability_type: CapabilityType, handler: Callable):
        """Register a handler for a specific capability type."""
        self.task_handlers[capability_type] = handler
        self.logger.info(f"Registered task handler for capability: {capability_type}")
    
    def create_agent_card(self) -> AgentCard:
        """Create an agent card for registration."""
        return AgentCard(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            version="1.0.0",
            tags=[cap.type.value for cap in self.capabilities],
            total_tasks_completed=self.tasks_completed,
            success_rate=self._calculate_success_rate(),
            response_time_ms=self._calculate_average_response_time()
        )
    
    def _calculate_success_rate(self) -> float:
        """Calculate the agent's success rate."""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 1.0
    
    def _calculate_average_response_time(self) -> Optional[int]:
        """Calculate average response time in milliseconds."""
        if not self.response_times:
            return None
        return int(sum(self.response_times) / len(self.response_times))
    
    async def register(self) -> bool:
        """Register the agent with the discovery system."""
        if not self.registry:
            self.logger.warning("No registry configured, skipping registration")
            return False
        
        try:
            agent_card = self.create_agent_card()
            result = self.registry.register_agent(agent_card)
            
            if result['success']:
                self.is_registered = True
                self.logger.info(f"Successfully registered agent: {self.agent_id}")
                return True
            else:
                self.logger.error(f"Registration failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    async def deregister(self) -> bool:
        """Deregister the agent from the discovery system."""
        if not self.registry or not self.is_registered:
            return True
        
        try:
            result = self.registry.deregister_agent(self.agent_id)
            
            if result['success']:
                self.is_registered = False
                self.logger.info(f"Successfully deregistered agent: {self.agent_id}")
                return True
            else:
                self.logger.error(f"Deregistration failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Deregistration error: {e}")
            return False
    
    async def send_message(self, message: Message) -> bool:
        """Send a message to another agent or system."""
        if not self.message_queue_url:
            self.logger.warning("No message queue configured")
            return False
        
        try:
            message_body = json.dumps(message.dict(), default=str)
            response = self.sqs.send_message(
                QueueUrl=self.message_queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    'message_type': {
                        'StringValue': message.message_type.value,
                        'DataType': 'String'
                    },
                    'sender_id': {
                        'StringValue': message.sender_id,
                        'DataType': 'String'
                    }
                }
            )
            
            self.logger.debug(f"Message sent: {response['MessageId']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def receive_messages(self, max_messages: int = 10) -> List[Message]:
        """Receive messages from the queue."""
        if not self.message_queue_url:
            return []
        
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.message_queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=20,
                MessageAttributeNames=['All']
            )
            
            messages = []
            for msg in response.get('Messages', []):
                try:
                    message_data = json.loads(msg['Body'])
                    message = Message(**message_data)
                    
                    if validate_message(message):
                        messages.append(message)
                    else:
                        self.logger.warning(f"Invalid message received: {message.message_id}")
                        
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.error(f"Failed to parse message: {e}")
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to receive messages: {e}")
            return []
    
    async def process_message(self, message: Message) -> bool:
        """Process a received message."""
        try:
            handler = self.message_handlers.get(message.message_type)
            if handler:
                start_time = datetime.utcnow()
                await handler(message)
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.response_times.append(response_time)
                return True
            else:
                self.logger.warning(f"No handler for message type: {message.message_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return False
    
    async def _handle_heartbeat(self, message: Message):
        """Handle heartbeat messages."""
        if self.registry and self.is_registered:
            self.registry.update_agent_heartbeat(self.agent_id)
    
    async def _handle_discovery_request(self, message: Message):
        """Handle discovery request messages."""
        # This is a basic implementation - agents can override this
        pass
    
    async def _handle_task_request(self, message: Message):
        """Handle task request messages."""
        task_data = message.payload.get('task', {})
        task = Task(**task_data)
        
        # Check if we can handle this task
        can_handle = all(
            cap_type in [cap.type for cap in self.capabilities]
            for cap_type in task.required_capabilities
        )
        
        if can_handle:
            # Execute the task
            result = await self.execute_task(task)
            
            # Send response
            response = create_message(
                message_type=MessageType.TASK_RESPONSE,
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                payload={
                    'task_id': task.task_id,
                    'status': 'completed' if result['success'] else 'failed',
                    'result': result.get('result'),
                    'error_message': result.get('error')
                },
                correlation_id=message.correlation_id
            )
            
            await self.send_message(response)
        else:
            # Send rejection
            response = create_message(
                message_type=MessageType.TASK_RESPONSE,
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                payload={
                    'task_id': task.task_id,
                    'status': 'rejected',
                    'error_message': 'Agent does not have required capabilities'
                },
                correlation_id=message.correlation_id
            )
            
            await self.send_message(response)
    
    async def _handle_registration(self, message: Message):
        """Handle registration messages."""
        # This is typically handled by the registry, not individual agents
        pass
    
    async def _handle_deregistration(self, message: Message):
        """Handle deregistration messages."""
        # This is typically handled by the registry, not individual agents
        pass
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a task using the appropriate handler."""
        try:
            # Find appropriate handler
            handler = None
            for capability in task.required_capabilities:
                if capability in self.task_handlers:
                    handler = self.task_handlers[capability]
                    break
            
            if not handler:
                return {
                    'success': False,
                    'error': 'No handler found for required capabilities'
                }
            
            # Execute the task
            start_time = datetime.utcnow()
            result = await handler(task.parameters)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update metrics
            self.tasks_completed += 1
            self.response_times.append(execution_time)
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            self.tasks_failed += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start(self):
        """Start the agent."""
        self.logger.info(f"Starting agent: {self.name}")
        
        # Register with discovery system
        await self.register()
        
        self.is_running = True
        
        # Start message processing loop
        while self.is_running:
            try:
                messages = await self.receive_messages()
                
                for message in messages:
                    await self.process_message(message)
                
                # Send heartbeat periodically
                if self.is_registered and self.registry:
                    self.registry.update_agent_heartbeat(self.agent_id)
                
                await asyncio.sleep(1)  # Small delay to prevent tight loop
                
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(5)  # Longer delay on error
    
    async def stop(self):
        """Stop the agent."""
        self.logger.info(f"Stopping agent: {self.name}")
        
        self.is_running = False
        
        # Deregister from discovery system
        await self.deregister()
    
    @abstractmethod
    async def initialize(self):
        """Initialize agent-specific functionality."""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up agent-specific resources."""
        pass 