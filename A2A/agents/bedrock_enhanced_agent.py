"""
Bedrock Enhanced Base Agent

Extends BaseAgent with AI-powered task processing using AWS Bedrock.
"""

import asyncio
import json
import boto3
from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent
from protocol import Task, Message, MessageType, CapabilityType

class BedrockEnhancedBaseAgent(BaseAgent):
    """
    Enhanced base agent with AI-powered task processing using Bedrock.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_history = []
        self.performance_metrics = {
            'ai_enhanced_tasks': 0,
            'ai_suggestions_used': 0,
            'task_optimization_count': 0
        }
        
        # Initialize Bedrock
        try:
            self.bedrock = boto3.client('bedrock-runtime', region_name=self.region)
            self.bedrock_model = 'anthropic.claude-3-sonnet-20240229-v1:0'
            self.bedrock_enabled = True
        except Exception as e:
            self.logger.warning(f"Bedrock initialization failed: {e}")
            self.bedrock_enabled = False
            self.bedrock_model = None
    
    async def process_task_with_ai(self, task_description: str, task_parameters: Dict = None) -> Dict:
        """Process task using Bedrock for intelligent decision making"""
        
        if not self.bedrock_enabled:
            return await self.execute_task_fallback(task_description, task_parameters)
        
        try:
            # Use Bedrock to analyze the task
            task_analysis = await self._analyze_task_with_bedrock(task_description)
            
            # Check if we can handle this task
            can_handle = all(
                cap in [c.type.value for c in self.capabilities]
                for cap in task_analysis.get('required_capabilities', [])
            )
            
            if can_handle:
                # Execute with AI-enhanced parameters
                result = await self.execute_task_with_ai_guidance(task_analysis, task_parameters)
                self.performance_metrics['ai_enhanced_tasks'] += 1
                return result
            else:
                # Recommend alternative agents
                return await self.recommend_alternative_agents(task_analysis)
                
        except Exception as e:
            self.logger.error(f"AI-enhanced task processing failed: {e}")
            # Fallback to regular task execution
            return await self.execute_task_fallback(task_description, task_parameters)
    
    async def _analyze_task_with_bedrock(self, task_description: str) -> Dict[str, Any]:
        """Use Bedrock to analyze task and identify requirements."""
        
        prompt = f"""
        Analyze this task and identify the required capabilities and task type.
        
        Task: {task_description}
        
        Available capability types:
        - TEXT_PROCESSING: Text analysis, summarization, translation
        - DATA_ANALYSIS: Statistical analysis, data processing
        - IMAGE_PROCESSING: Image recognition, analysis, generation
        - AUDIO_PROCESSING: Speech recognition, audio analysis
        - CODE_GENERATION: Code writing, debugging, optimization
        
        Return a JSON response with:
        {{
            "task_type": "string",
            "required_capabilities": ["capability1", "capability2"],
            "complexity": "low|medium|high",
            "estimated_duration_minutes": number,
            "priority": "low|medium|high",
            "parallel_execution": boolean,
            "max_agents_needed": number
        }}
        """
        
        response = self.bedrock.invoke_model(
            modelId=self.bedrock_model,
            body=json.dumps({
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.1
            })
        )
        
        result = json.loads(response['body'].read())
        return json.loads(result['completion'])
    
    async def execute_task_with_ai_guidance(self, task_analysis: Dict, task_parameters: Dict = None) -> Dict:
        """Execute task with AI-provided guidance"""
        
        try:
            # Use Bedrock to optimize execution parameters
            optimization_prompt = f"""
            Given this task analysis, provide execution guidance:
            {json.dumps(task_analysis)}
            
            Current agent capabilities: {[cap.type.value for cap in self.capabilities]}
            
            Return JSON with execution parameters:
            {{
                "timeout_seconds": number,
                "retry_count": number,
                "resource_requirements": "string",
                "execution_strategy": "string",
                "optimization_suggestions": ["suggestion1", "suggestion2"]
            }}
            """
            
            # For now, create a mock optimization result
            # In real implementation, call Bedrock here
            optimization_guidance = {
                "timeout_seconds": task_analysis.get('estimated_duration_minutes', 5) * 60,
                "retry_count": 2 if task_analysis.get('complexity') == 'high' else 1,
                "resource_requirements": "standard",
                "execution_strategy": "optimized",
                "optimization_suggestions": ["Use parallel processing", "Cache intermediate results"]
            }
            
            # Execute with AI guidance
            return await self.execute_task_with_parameters(task_analysis, optimization_guidance, task_parameters)
            
        except Exception as e:
            self.logger.error(f"AI guidance failed: {e}")
            return await self.execute_task_fallback(task_analysis.get('description', ''), task_parameters)
    
    async def execute_task_with_parameters(self, task_analysis: Dict, guidance: Dict, 
                                         task_parameters: Dict = None) -> Dict:
        """Execute task with specific parameters and guidance"""
        
        try:
            # Find appropriate handler
            handler = None
            for capability in task_analysis.get('required_capabilities', []):
                if capability in self.task_handlers:
                    handler = self.task_handlers[capability]
                    break
            
            if not handler:
                return {
                    'success': False,
                    'error': 'No handler found for required capabilities',
                    'ai_analysis': task_analysis
                }
            
            # Execute the task with guidance
            start_time = asyncio.get_event_loop().time()
            
            # Apply optimization suggestions
            if guidance.get('optimization_suggestions'):
                self.logger.info(f"Applying AI suggestions: {guidance['optimization_suggestions']}")
                self.performance_metrics['ai_suggestions_used'] += 1
            
            # Execute with timeout
            if guidance.get('timeout_seconds'):
                result = await asyncio.wait_for(
                    handler(task_parameters or {}),
                    timeout=guidance['timeout_seconds']
                )
            else:
                result = await handler(task_parameters or {})
            
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Update metrics
            self.tasks_completed += 1
            self.response_times.append(execution_time)
            
            # Record task history
            self.task_history.append({
                'task_analysis': task_analysis,
                'guidance_used': guidance,
                'execution_time': execution_time,
                'success': True,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time,
                'ai_analysis': task_analysis,
                'guidance_applied': guidance,
                'performance_metrics': self.performance_metrics
            }
            
        except asyncio.TimeoutError:
            self.tasks_failed += 1
            return {
                'success': False,
                'error': f'Task timed out after {guidance.get("timeout_seconds", 0)} seconds',
                'ai_analysis': task_analysis
            }
        except Exception as e:
            self.tasks_failed += 1
            return {
                'success': False,
                'error': str(e),
                'ai_analysis': task_analysis
            }
    
    async def execute_task_fallback(self, task_description: str, task_parameters: Dict = None) -> Dict:
        """Fallback task execution without AI enhancement"""
        
        try:
            # Create a basic task
            task = Task(
                task_id=f"fallback_{asyncio.get_event_loop().time()}",
                description=task_description,
                parameters=task_parameters or {},
                required_capabilities=[cap.type for cap in self.capabilities[:1]],  # Use first capability
                priority="medium"
            )
            
            return await self.execute_task(task)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Fallback execution failed: {str(e)}'
            }
    
    async def recommend_alternative_agents(self, task_analysis: Dict) -> Dict:
        """Recommend alternative agents when current agent can't handle the task"""
        
        try:
            # This would typically query the discovery system
            # For now, return a structured recommendation
            return {
                'success': False,
                'error': 'Agent cannot handle this task',
                'ai_analysis': task_analysis,
                'recommendations': {
                    'required_capabilities': task_analysis.get('required_capabilities', []),
                    'suggested_agent_types': self._suggest_agent_types(task_analysis),
                    'task_complexity': task_analysis.get('complexity', 'medium'),
                    'estimated_duration': task_analysis.get('estimated_duration_minutes', 0)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate recommendations: {str(e)}'
            }
    
    def _suggest_agent_types(self, task_analysis: Dict) -> List[str]:
        """Suggest agent types based on task analysis"""
        
        capability_mapping = {
            'TEXT_PROCESSING': ['TextProcessor', 'NLPProcessor', 'Summarizer'],
            'DATA_ANALYSIS': ['DataAnalyst', 'Statistician', 'MLProcessor'],
            'IMAGE_PROCESSING': ['ImageProcessor', 'ComputerVision', 'ImageAnalyzer'],
            'AUDIO_PROCESSING': ['AudioProcessor', 'SpeechRecognizer', 'AudioAnalyzer'],
            'CODE_GENERATION': ['CodeGenerator', 'CodeReviewer', 'Debugger']
        }
        
        suggested_types = []
        for capability in task_analysis.get('required_capabilities', []):
            if capability in capability_mapping:
                suggested_types.extend(capability_mapping[capability])
        
        return list(set(suggested_types))  # Remove duplicates
    
    async def get_ai_insights(self) -> Dict:
        """Get AI-powered insights about agent performance"""
        
        try:
            if not self.task_history:
                return {
                    'success': False,
                    'error': 'No task history available for analysis'
                }
            
            # Analyze recent performance
            recent_tasks = self.task_history[-10:]  # Last 10 tasks
            
            avg_execution_time = sum(task['execution_time'] for task in recent_tasks) / len(recent_tasks)
            success_rate = sum(1 for task in recent_tasks if task['success']) / len(recent_tasks)
            
            # Generate insights
            insights = {
                'performance_summary': {
                    'avg_execution_time_ms': avg_execution_time,
                    'recent_success_rate': success_rate,
                    'ai_enhanced_tasks': self.performance_metrics['ai_enhanced_tasks'],
                    'ai_suggestions_used': self.performance_metrics['ai_suggestions_used']
                },
                'recommendations': self._generate_performance_recommendations(recent_tasks),
                'capability_analysis': self._analyze_capability_usage(recent_tasks)
            }
            
            return {
                'success': True,
                'insights': insights,
                'task_history_count': len(self.task_history)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate insights: {str(e)}'
            }
    
    def _generate_performance_recommendations(self, recent_tasks: List[Dict]) -> List[str]:
        """Generate performance recommendations based on task history"""
        
        recommendations = []
        
        # Analyze execution times
        slow_tasks = [task for task in recent_tasks if task['execution_time'] > 5000]  # > 5 seconds
        if slow_tasks:
            recommendations.append("Consider optimizing slow tasks with parallel processing")
        
        # Analyze success rate
        failed_tasks = [task for task in recent_tasks if not task['success']]
        if failed_tasks:
            recommendations.append("Review failed tasks to improve error handling")
        
        # Analyze AI usage
        if self.performance_metrics['ai_enhanced_tasks'] < len(recent_tasks) * 0.5:
            recommendations.append("Consider using AI enhancement for more tasks")
        
        return recommendations
    
    def _analyze_capability_usage(self, recent_tasks: List[Dict]) -> Dict:
        """Analyze which capabilities are used most frequently"""
        
        capability_usage = {}
        for task in recent_tasks:
            capabilities = task.get('task_analysis', {}).get('required_capabilities', [])
            for capability in capabilities:
                capability_usage[capability] = capability_usage.get(capability, 0) + 1
        
        return {
            'most_used_capabilities': sorted(capability_usage.items(), key=lambda x: x[1], reverse=True)[:3],
            'underutilized_capabilities': [cap.type.value for cap in self.capabilities 
                                         if cap.type.value not in capability_usage]
        } 