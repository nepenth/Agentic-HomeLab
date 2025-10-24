"""
Agentic Reasoning Service

Provides multi-step chain-of-thought reasoning with tool calling for the email assistant.
"""

from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import json
from enum import Enum

from app.services.ollama_client import ollama_client
from app.services.email_tools import email_tool_registry
from app.utils.logging import get_logger
from app.utils.datetime_utils import utc_now, timedelta_seconds

logger = get_logger("agentic_reasoning_service")


class ReasoningStepType(str, Enum):
    """Types of reasoning steps"""
    PLANNING = "planning"
    TOOL_CALL = "tool_call"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"


class ReasoningStep:
    """A single step in the reasoning chain"""

    def __init__(
        self,
        step_number: int,
        step_type: ReasoningStepType,
        description: str,
        content: str = "",
        tool_call: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ):
        self.step_number = step_number
        self.step_type = step_type
        self.description = description
        self.content = content
        self.tool_call = tool_call
        self.tool_result = tool_result
        self.duration_ms = duration_ms
        self.timestamp = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for streaming"""
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "description": self.description,
            "content": self.content,
            "tool_call": self.tool_call,
            "tool_result": self.tool_result,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


class AgenticReasoningService:
    """Service for multi-step agentic reasoning with tool calling"""

    def __init__(self):
        self.logger = get_logger("agentic_reasoning_service")
        self.max_steps = 10  # Maximum reasoning steps before forcing conclusion
        self.max_tool_calls = 7  # Maximum tool calls per query

    async def reason_and_respond(
        self,
        db: AsyncSession,
        user_id: int,
        user_query: str,
        model_name: str = "qwen3:30b-a3b-thinking-2507-q8_0",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        timeout_ms: Optional[int] = None
    ) -> AsyncIterator[ReasoningStep]:
        """
        Perform multi-step reasoning with tool calling and yield each step.

        This is a generator that yields ReasoningStep objects as the AI progresses
        through its reasoning chain.

        Args:
            db: Database session
            user_id: User ID for permission checking
            user_query: The user's question/query
            model_name: LLM model to use for reasoning
            conversation_history: Previous conversation context
            timeout_ms: Optional timeout for LLM calls

        Yields:
            ReasoningStep: Individual reasoning steps as they occur
        """

        reasoning_history = []
        tool_call_count = 0
        step_number = 0

        # Get available tools
        available_tools = email_tool_registry.get_all_definitions()
        tools_description = self._format_tools_for_prompt(available_tools)

        # Build system prompt
        system_prompt = f"""You are an advanced AI assistant that helps users understand and manage their emails.

You have access to the following tools that you can use to gather information:

{tools_description}

When answering a user's question, you should:
1. Think step-by-step about what information you need
2. Use tools to gather relevant information
3. Analyze the results from your tool calls
4. Continue exploring if you need more information
5. Synthesize a comprehensive final answer

To use a tool, respond with a JSON object in this format:
{{
    "reasoning": "Brief explanation of why you're using this tool",
    "tool": "tool_name",
    "parameters": {{"param1": "value1", "param2": "value2"}}
}}

When you have enough information to answer the user's question, respond with:
{{
    "reasoning": "Summary of findings",
    "final_answer": "Your comprehensive answer in markdown format"
}}

Important:
- Be thorough but efficient - don't make unnecessary tool calls
- If a previous tool call didn't yield results, try a different approach
- Always explain your reasoning at each step
- Use markdown formatting in your final answer for clarity
- If you cannot find the information needed, explain what you tried and suggest alternatives
"""

        # Initialize conversation with system prompt and user query
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_query})

        # Reasoning loop
        while step_number < self.max_steps:
            step_number += 1
            step_start = utc_now()

            # Get LLM response
            try:
                response = await ollama_client.chat(
                    messages=messages,
                    model=model_name,
                    format="json",  # Request JSON output
                    timeout_ms=timeout_ms
                )

                response_content = response.get("message", {}).get("content", "")

                # Parse LLM response
                try:
                    parsed_response = json.loads(response_content)
                except json.JSONDecodeError as je:
                    self.logger.warning(f"Failed to parse JSON response: {je}")
                    # If not valid JSON, treat as final answer
                    parsed_response = {"final_answer": response_content}

                # Check if this is the final answer
                if "final_answer" in parsed_response:
                    step_duration = int(timedelta_seconds(step_start) * 1000)

                    final_step = ReasoningStep(
                        step_number=step_number,
                        step_type=ReasoningStepType.SYNTHESIS,
                        description="Synthesizing final answer",
                        content=parsed_response.get("reasoning", ""),
                        duration_ms=step_duration
                    )
                    yield final_step

                    # Yield the actual answer as a separate step
                    answer_step = ReasoningStep(
                        step_number=step_number + 1,
                        step_type=ReasoningStepType.FINAL_ANSWER,
                        description="Final Answer",
                        content=parsed_response["final_answer"],
                        duration_ms=0
                    )
                    yield answer_step
                    break

                # This is a tool call
                if "tool" in parsed_response and tool_call_count < self.max_tool_calls:
                    tool_call_count += 1

                    tool_name = parsed_response["tool"]
                    parameters = parsed_response.get("parameters", {})
                    reasoning = parsed_response.get("reasoning", "")

                    # Yield the planning step
                    planning_step = ReasoningStep(
                        step_number=step_number,
                        step_type=ReasoningStepType.PLANNING,
                        description=f"Calling tool: {tool_name}",
                        content=reasoning,
                        tool_call={
                            "tool": tool_name,
                            "parameters": parameters
                        },
                        duration_ms=int(timedelta_seconds(step_start) * 1000)
                    )
                    yield planning_step

                    # Execute the tool
                    tool_start = utc_now()
                    try:
                        tool_result = await email_tool_registry.execute_tool(
                            db=db,
                            user_id=user_id,
                            tool_name=tool_name,
                            **parameters
                        )

                        tool_duration = int(timedelta_seconds(tool_start) * 1000)

                        # Yield the tool execution step
                        tool_step = ReasoningStep(
                            step_number=step_number + 1,
                            step_type=ReasoningStepType.TOOL_CALL,
                            description=f"Tool result: {tool_name}",
                            content=f"Successfully executed {tool_name}",
                            tool_call={
                                "tool": tool_name,
                                "parameters": parameters
                            },
                            tool_result=tool_result,
                            duration_ms=tool_duration
                        )
                        yield tool_step

                        # Add tool result to conversation
                        messages.append({
                            "role": "assistant",
                            "content": json.dumps(parsed_response)
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Tool '{tool_name}' returned: {json.dumps(tool_result, indent=2)}\n\nWhat's your next step?"
                        })

                    except Exception as e:
                        self.logger.error(f"Tool execution error: {e}", exc_info=True)

                        error_step = ReasoningStep(
                            step_number=step_number + 1,
                            step_type=ReasoningStepType.ERROR,
                            description=f"Tool error: {tool_name}",
                            content=f"Error executing tool: {str(e)}",
                            tool_call={
                                "tool": tool_name,
                                "parameters": parameters
                            },
                            tool_result={"success": False, "error": str(e)},
                            duration_ms=int(timedelta_seconds(tool_start) * 1000)
                        )
                        yield error_step

                        # Add error to conversation
                        messages.append({
                            "role": "user",
                            "content": f"Tool '{tool_name}' failed with error: {str(e)}\n\nPlease try a different approach."
                        })

                elif tool_call_count >= self.max_tool_calls:
                    # Force conclusion
                    messages.append({
                        "role": "user",
                        "content": "You've used the maximum number of tool calls. Please provide your final answer based on the information you've gathered."
                    })

            except Exception as e:
                self.logger.error(f"Reasoning step error: {e}", exc_info=True)

                error_step = ReasoningStep(
                    step_number=step_number,
                    step_type=ReasoningStepType.ERROR,
                    description="Error in reasoning",
                    content=f"An error occurred: {str(e)}",
                    duration_ms=int(timedelta_seconds(step_start) * 1000)
                )
                yield error_step
                break

    def _format_tools_for_prompt(self, tools: List[Any]) -> str:
        """Format tool definitions for the system prompt"""
        tool_descriptions = []

        for tool in tools:
            params_str = json.dumps(tool.parameters, indent=2)
            tool_descriptions.append(
                f"**{tool.name}**\n"
                f"Description: {tool.description}\n"
                f"Parameters:\n```json\n{params_str}\n```\n"
            )

        return "\n\n".join(tool_descriptions)


# Global instance
agentic_reasoning_service = AgenticReasoningService()
