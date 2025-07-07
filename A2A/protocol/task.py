"""
Task Module

This module provides task management functionality for the A2A system,
including task creation, validation, and execution tracking.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid
from .a2a_protocol import Task, TaskStatus, TaskPriority, CapabilityType


class TaskManager:
    """Manages task lifecycle and execution."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_task(
        self,
        title: str,
        description: str,
        required_capabilities: List[CapabilityType],
        created_by: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[datetime] = None,
        task_id: Optional[str] = None
    ) -> Task:
        """Create a new task."""
        task = Task(
            task_id=task_id or str(uuid.uuid4()),
            title=title,
            description=description,
            required_capabilities=required_capabilities,
            created_by=created_by,
            parameters=parameters or {},
            priority=priority,
            deadline=deadline
        )
        
        self.tasks[task.task_id] = task
        self.execution_history[task.task_id] = []
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs) -> bool:
        """Update the status of a task."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = status
        task.updated_at = datetime.utcnow()
        
        # Update additional fields if provided
        if 'result' in kwargs:
            task.result = kwargs['result']
        if 'error_message' in kwargs:
            task.error_message = kwargs['error_message']
        if 'assigned_to' in kwargs:
            task.assigned_to = kwargs['assigned_to']
        
        # Record in execution history
        self.execution_history[task_id].append({
            'timestamp': datetime.utcnow(),
            'status': status,
            'updated_by': kwargs.get('updated_by', 'system'),
            'notes': kwargs.get('notes', '')
        })
        
        return True
    
    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        return self.update_task_status(
            task_id, 
            TaskStatus.IN_PROGRESS, 
            assigned_to=agent_id,
            updated_by='system'
        )
    
    def complete_task(self, task_id: str, result: Dict[str, Any], agent_id: str) -> bool:
        """Mark a task as completed with results."""
        return self.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result,
            updated_by=agent_id
        )
    
    def fail_task(self, task_id: str, error_message: str, agent_id: str) -> bool:
        """Mark a task as failed with error message."""
        return self.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=error_message,
            updated_by=agent_id
        )
    
    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a task."""
        return self.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            error_message=reason,
            updated_by='system'
        )
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        """Get all tasks assigned to a specific agent."""
        return [task for task in self.tasks.values() if task.assigned_to == agent_id]
    
    def get_tasks_by_creator(self, creator_id: str) -> List[Task]:
        """Get all tasks created by a specific agent."""
        return [task for task in self.tasks.values() if task.created_by == creator_id]
    
    def get_overdue_tasks(self) -> List[Task]:
        """Get all tasks that have passed their deadline."""
        now = datetime.utcnow()
        return [
            task for task in self.tasks.values()
            if task.deadline and task.deadline < now and task.status not in [
                TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
            ]
        ]
    
    def get_task_execution_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get the execution history of a task."""
        return self.execution_history.get(task_id, [])
    
    def register_task_handler(self, capability_type: CapabilityType, handler: Callable) -> None:
        """Register a handler for a specific capability type."""
        self.task_handlers[capability_type.value] = handler
    
    def execute_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """Execute a task using the appropriate handler."""
        task = self.get_task(task_id)
        if not task:
            return {'success': False, 'error': 'Task not found'}
        
        if task.status != TaskStatus.IN_PROGRESS:
            return {'success': False, 'error': f'Task is not in progress (status: {task.status})'}
        
        if task.assigned_to != agent_id:
            return {'success': False, 'error': 'Task not assigned to this agent'}
        
        # Find appropriate handler
        handler = None
        for capability in task.required_capabilities:
            if capability.value in self.task_handlers:
                handler = self.task_handlers[capability.value]
                break
        
        if not handler:
            return {'success': False, 'error': 'No handler found for required capabilities'}
        
        try:
            # Execute the task
            start_time = datetime.utcnow()
            result = handler(task.parameters)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update task with results
            self.complete_task(task_id, result, agent_id)
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            error_msg = str(e)
            self.fail_task(task_id, error_msg, agent_id)
            return {
                'success': False,
                'error': error_msg
            }
    
    def cleanup_completed_tasks(self, days_old: int = 30) -> int:
        """Remove completed tasks older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED] and
                task.updated_at < cutoff_date):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            if task_id in self.execution_history:
                del self.execution_history[task_id]
        
        return len(tasks_to_remove)


class TaskValidator:
    """Validates task definitions and parameters."""
    
    @staticmethod
    def validate_task_creation(
        title: str,
        description: str,
        required_capabilities: List[CapabilityType],
        created_by: str
    ) -> List[str]:
        """Validate task creation parameters."""
        errors = []
        
        if not title or len(title.strip()) == 0:
            errors.append("Task title is required")
        
        if not description or len(description.strip()) == 0:
            errors.append("Task description is required")
        
        if not required_capabilities:
            errors.append("At least one required capability is needed")
        
        if not created_by or len(created_by.strip()) == 0:
            errors.append("Task creator ID is required")
        
        return errors
    
    @staticmethod
    def validate_task_parameters(
        parameters: Dict[str, Any],
        required_params: List[str],
        optional_params: Optional[Dict[str, type]] = None
    ) -> List[str]:
        """Validate task parameters against required and optional specifications."""
        errors = []
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                errors.append(f"Required parameter '{param}' is missing")
        
        # Check optional parameter types
        if optional_params:
            for param, expected_type in optional_params.items():
                if param in parameters:
                    if not isinstance(parameters[param], expected_type):
                        errors.append(f"Parameter '{param}' must be of type {expected_type.__name__}")
        
        return errors
    
    @staticmethod
    def validate_task_assignment(task: Task, agent_capabilities: List[CapabilityType]) -> List[str]:
        """Validate if an agent can handle a task based on capabilities."""
        errors = []
        
        for required_cap in task.required_capabilities:
            if required_cap not in agent_capabilities:
                errors.append(f"Agent missing required capability: {required_cap.value}")
        
        return errors


class TaskScheduler:
    """Schedules and prioritizes tasks."""
    
    def __init__(self):
        self.priority_weights = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.URGENT: 4
        }
    
    def prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by priority and other factors."""
        def task_score(task: Task) -> float:
            # Base priority score
            score = self.priority_weights.get(task.priority, 1)
            
            # Boost score for overdue tasks
            if task.deadline and task.deadline < datetime.utcnow():
                score += 10
            
            # Boost score for older tasks (FIFO within same priority)
            age_hours = (datetime.utcnow() - task.created_at).total_seconds() / 3600
            score += age_hours * 0.1
            
            return score
        
        return sorted(tasks, key=task_score, reverse=True)
    
    def get_optimal_agent_for_task(
        self,
        task: Task,
        available_agents: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find the best agent for a task based on capabilities and load."""
        suitable_agents = []
        
        for agent in available_agents:
            agent_capabilities = agent.get('capabilities', [])
            
            # Check if agent has all required capabilities
            has_all_capabilities = all(
                cap.value in agent_capabilities
                for cap in task.required_capabilities
            )
            
            if has_all_capabilities:
                # Calculate agent score based on load and performance
                current_load = agent.get('current_load', 0.0)
                success_rate = agent.get('success_rate', 0.5)
                
                # Lower load and higher success rate = better score
                agent_score = (1 - current_load) * success_rate
                
                suitable_agents.append({
                    'agent_id': agent['agent_id'],
                    'score': agent_score
                })
        
        if not suitable_agents:
            return None
        
        # Return the agent with the highest score
        best_agent = max(suitable_agents, key=lambda x: x['score'])
        return best_agent['agent_id'] 