"""
Processing pipeline execution engine for dynamic agents.
"""
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import asyncio

from app.schemas.agent_schema import ProcessingPipeline as PipelineSchema, ProcessingStep
from app.services.ollama_client import OllamaClient
from app.services.log_service import LogService
from app.services.security_service import SecurityService
from app.utils.logging import get_logger
from app.agents.tools.base import ExecutionContext as ToolExecutionContext

logger = get_logger(__name__)


class PipelineExecutionError(Exception):
    """Raised when pipeline execution fails."""
    pass


class PipelineExecutionContext(ToolExecutionContext):
    """Extended execution context for pipeline operations."""

    def __init__(self, initial_data: Dict[str, Any]):
        # Initialize parent class
        super().__init__({"data": initial_data})

        # Pipeline-specific attributes
        self.step_results: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []

        # Override data to be the initial_data directly
        self.data = initial_data.copy()

    def add_step_result(self, step_name: str, result: Any, execution_time: float):
        """Add result from a pipeline step."""
        self.step_results[step_name] = result
        self.execution_log.append({
            "step": step_name,
            "timestamp": datetime.utcnow().isoformat(),
            "execution_time": execution_time,
            "success": True
        })

        # Merge result into context data if it's a dict
        if isinstance(result, dict):
            self.data.update(result)

    def add_step_error(self, step_name: str, error: str, execution_time: float):
        """Add error from a pipeline step."""
        self.execution_log.append({
            "step": step_name,
            "timestamp": datetime.utcnow().isoformat(),
            "execution_time": execution_time,
            "success": False,
            "error": error
        })

    def get_total_execution_time(self) -> float:
        """Get total execution time in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()


class ProcessingPipeline:
    """Executes processing pipelines defined in agent schemas."""
    
    def __init__(
        self,
        steps: List[ProcessingStep],
        tools: Dict[str, Any],
        parallel_execution: bool = False,
        max_retries: int = 3,
        timeout: Optional[int] = None,
        ollama_client: Optional[OllamaClient] = None,
        log_service: Optional[LogService] = None,
        security_service: Optional[SecurityService] = None
    ):
        self.steps = steps
        self.tools = tools
        self.parallel_execution = parallel_execution
        self.max_retries = max_retries
        self.timeout = timeout
        self.ollama_client = ollama_client
        self.log_service = log_service
        self.security_service = security_service or SecurityService()

        # Build dependency graph
        self.dependency_graph = self._build_dependency_graph()
        self.execution_order = self._calculate_execution_order()
    
    @classmethod
    def from_schema(
        cls,
        pipeline_schema: PipelineSchema,
        tools: Dict[str, Any],
        ollama_client: Optional[OllamaClient] = None,
        log_service: Optional[LogService] = None
    ) -> "ProcessingPipeline":
        """Create pipeline from schema definition."""
        return cls(
            steps=pipeline_schema.steps,
            tools=tools,
            parallel_execution=pipeline_schema.parallel_execution,
            max_retries=pipeline_schema.max_retries,
            timeout=pipeline_schema.timeout,
            ollama_client=ollama_client,
            log_service=log_service
        )
    
    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph from step definitions."""
        graph = {}
        
        for step in self.steps:
            dependencies = set(step.depends_on) if step.depends_on else set()
            graph[step.name] = dependencies
        
        return graph
    
    def _calculate_execution_order(self) -> List[List[str]]:
        """Calculate execution order respecting dependencies."""
        # Topological sort to determine execution order
        in_degree = {}
        for step_name in self.dependency_graph:
            in_degree[step_name] = 0
        
        for step_name, dependencies in self.dependency_graph.items():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[step_name] += 1
        
        # Group steps by execution level (steps that can run in parallel)
        execution_levels = []
        remaining_steps = set(self.dependency_graph.keys())
        
        while remaining_steps:
            # Find steps with no remaining dependencies
            ready_steps = [
                step for step in remaining_steps 
                if in_degree[step] == 0
            ]
            
            if not ready_steps:
                # Circular dependency detected
                raise PipelineExecutionError(f"Circular dependency detected in steps: {remaining_steps}")
            
            execution_levels.append(ready_steps)
            
            # Remove ready steps and update in-degrees
            for step in ready_steps:
                remaining_steps.remove(step)
                for other_step in remaining_steps:
                    if step in self.dependency_graph[other_step]:
                        in_degree[other_step] -= 1
        
        return execution_levels
    
    async def execute(self, input_data: Dict[str, Any], agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the processing pipeline.
        
        Args:
            input_data: Input data for the pipeline
            agent_context: Agent execution context
            
        Returns:
            Final pipeline results
            
        Raises:
            PipelineExecutionError: If pipeline execution fails
        """
        context = PipelineExecutionContext(input_data)
        context.data.update(agent_context)
        
        try:
            logger.info(f"Starting pipeline execution with {len(self.steps)} steps")
            
            # Execute steps level by level
            for level_index, step_names in enumerate(self.execution_order):
                logger.info(f"Executing level {level_index + 1} with steps: {step_names}")
                
                if self.parallel_execution and len(step_names) > 1:
                    # Execute steps in parallel
                    tasks = [
                        self._execute_step(step_name, context)
                        for step_name in step_names
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Check for exceptions
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            step_name = step_names[i]
                            raise PipelineExecutionError(f"Step '{step_name}' failed: {str(result)}")
                else:
                    # Execute steps sequentially
                    for step_name in step_names:
                        await self._execute_step(step_name, context)
            
            logger.info(f"Pipeline execution completed in {context.get_total_execution_time():.2f}s")
            
            # Return final results
            return {
                "results": context.step_results,
                "execution_log": context.execution_log,
                "total_execution_time": context.get_total_execution_time(),
                "final_data": context.data
            }
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise PipelineExecutionError(f"Pipeline execution failed: {str(e)}")
    
    async def _execute_step(self, step_name: str, context: PipelineExecutionContext) -> None:
        """
        Execute a single pipeline step.
        
        Args:
            step_name: Name of the step to execute
            context: Execution context
            
        Raises:
            PipelineExecutionError: If step execution fails
        """
        step = next((s for s in self.steps if s.name == step_name), None)
        if not step:
            raise PipelineExecutionError(f"Step '{step_name}' not found")
        
        tool = self.tools.get(step.tool)
        if not tool:
            raise PipelineExecutionError(f"Tool '{step.tool}' not found for step '{step_name}'")
        
        step_start_time = datetime.utcnow()

        try:
            logger.info(f"Executing step '{step_name}' with tool '{step.tool}'")

            # Prepare step input
            step_input = context.data.copy()
            if step.config:
                step_input.update(step.config)

            # Security validation before execution
            agent_id = context.get_agent_id()
            if agent_id:
                is_allowed, denial_reason = await self.security_service.validate_execution_request(
                    agent_id, step.tool, step_input
                )

                if not is_allowed:
                    raise PipelineExecutionError(f"Security validation failed for step '{step_name}': {denial_reason}")

            # Execute with retries
            result = await self._execute_with_retries(
                tool, step_input, step, context
            )
            
            execution_time = (datetime.utcnow() - step_start_time).total_seconds()
            context.add_step_result(step_name, result, execution_time)
            
            logger.info(f"Step '{step_name}' completed in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = (datetime.utcnow() - step_start_time).total_seconds()
            context.add_step_error(step_name, str(e), execution_time)
            
            logger.error(f"Step '{step_name}' failed after {execution_time:.2f}s: {e}")
            raise PipelineExecutionError(f"Step '{step_name}' failed: {str(e)}")
    
    async def _execute_with_retries(
        self,
        tool: Any,
        step_input: Dict[str, Any],
        step: ProcessingStep,
        context: PipelineExecutionContext
    ) -> Any:
        """
        Execute a tool with retry logic.
        
        Args:
            tool: Tool instance to execute
            step_input: Input data for the step
            step: Step configuration
            context: Execution context
            
        Returns:
            Tool execution result
            
        Raises:
            Exception: If all retries fail
        """
        max_retries = step.retry_config.get("max_retries", self.max_retries) if step.retry_config else self.max_retries
        timeout = step.timeout or self.timeout
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if timeout:
                    result = await asyncio.wait_for(
                        tool.execute(step_input, context),
                        timeout=timeout
                    )
                else:
                    result = await tool.execute(step_input, context)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    # Calculate retry delay
                    delay = step.retry_config.get("delay", 1.0) if step.retry_config else 1.0
                    if step.retry_config and step.retry_config.get("exponential_backoff", False):
                        delay *= (2 ** attempt)
                    
                    logger.warning(f"Step execution attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Step execution failed after {max_retries + 1} attempts: {e}")
        
        if last_exception:
            raise last_exception
        else:
            raise PipelineExecutionError("Tool execution failed with unknown error")
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the pipeline structure."""
        return {
            "total_steps": len(self.steps),
            "execution_levels": len(self.execution_order),
            "parallel_execution": self.parallel_execution,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "steps": [
                {
                    "name": step.name,
                    "tool": step.tool,
                    "dependencies": step.depends_on or [],
                    "has_config": bool(step.config),
                    "has_retry_config": bool(step.retry_config),
                    "timeout": step.timeout
                }
                for step in self.steps
            ],
            "execution_order": self.execution_order,
            "dependency_graph": {
                name: list(deps) for name, deps in self.dependency_graph.items()
            }
        }