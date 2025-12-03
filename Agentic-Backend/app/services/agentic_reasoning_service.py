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
        system_prompt = f"""You are an advanced AI assistant that helps users understand and manage their emails through multi-step reasoning and tool usage.

        You have access to the following tools that you can use to gather information:

        {tools_description}

        ## Core Reasoning Framework

        When answering a user's question, follow this systematic approach:

        ### 1. **Problem Analysis**
           - Understand what the user is asking for
           - Identify the key entities, time ranges, and specific requirements
           - Determine what information sources are needed

        ### 2. **Information Gathering Strategy**
           - Choose the most appropriate tools for the task
           - Use semantic search (embeddings) when looking for content by meaning
           - Apply entity extraction to identify specific data points (order numbers, dates, etc.)
           - Retrieve full content when detailed analysis is needed

        ### 3. **Multi-Step Tool Usage**
           - **Search First**: Use `search_emails` to find relevant emails by semantic meaning
           - **Extract Entities**: Use `extract_entities` to pull out specific data like order numbers, tracking numbers, dates
           - **Get Full Content**: Use `get_email_thread` to retrieve complete email content for detailed analysis
           - **Iterate**: Based on results, decide if more information is needed

        ### 4. **Synthesis and Analysis**
           - Correlate information from multiple sources
           - Deduplicate and organize findings
           - Provide comprehensive answers with all relevant details

        ## Tool Usage Guidelines

        ### search_emails
        - Use semantic queries that capture the meaning (e.g., "Amazon order confirmations" not just "Amazon")
        - Set appropriate time ranges to focus results
        - Use reasonable max_results (10-20 for initial searches)

        ### extract_entities
        - Specify relevant entity types: ["order_number", "tracking_number", "date", "amount"]
        - Apply to specific email IDs from search results
        - Use when you need structured data extraction

        ### get_email_thread
        - Use when you need full email content for detailed analysis
        - Include_sent=false for most cases (focus on received emails)
        - Apply to specific emails identified through search/extraction

        ## Response Format

        To use a tool, respond with a JSON object:
        {{
            "reasoning": "Brief explanation of why you're using this tool and what you expect to find",
            "tool": "tool_name",
            "parameters": {{"param1": "value1", "param2": "value2"}}
        }}

        When you have enough information to answer, respond with:
        {{
            "reasoning": "Summary of findings and analysis approach",
            "final_answer": "Your comprehensive answer in markdown format"
        }}

        If you need to provide intermediate reasoning without using tools, respond with:
        {{
            "reasoning": "Your analysis and reasoning so far",
            "continue": true
        }}

        ## Best Practices

        - **Be Methodical**: Follow a clear search → extract → analyze → synthesize pattern
        - **Use Semantics**: Leverage embedding-based search for better relevance
        - **Be Specific**: Use targeted entity extraction rather than parsing everything manually
        - **Iterate Intelligently**: Use results from one tool to inform the next tool call
        - **Provide Context**: Explain your reasoning and approach at each step
        - **Handle Edge Cases**: If searches don't yield expected results, try alternative queries or approaches

        ## MANDATORY REQUIREMENTS FOR COMPLETE REASONING

        ### Complete Reasoning Process
        - You MUST use at least one tool call for every user query
        - You MUST provide a comprehensive final answer with specific insights
        - You MUST NOT stop reasoning until you have completed the full analysis
        - You MUST use semantic search (embeddings) for email analysis

        ### Tool Usage Requirements
        - You MUST use search_emails for finding relevant emails
        - You MUST use extract_entities for structured data extraction
        - You MUST use get_email_thread for detailed content analysis
        - You MUST use all three tools in sequence for comprehensive analysis

        ### Final Answer Requirements
        - You MUST provide a minimum of 500 words in your final answer
        - You MUST include specific patterns, trends, and insights
        - You MUST provide concrete examples from the email data
        - You MUST use markdown formatting with clear sections
        - You MUST include a summary, detailed analysis, and actionable insights
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
                    timeout_ms=timeout_ms,
                    options={"temperature": 0.7, "top_p": 0.9, "num_predict": 8192, "repetition_penalty": 1.2}
                )

                response_content = response.get("message", {}).get("content", "")

                # Parse LLM response
                try:
                    parsed_response = json.loads(response_content)
                except json.JSONDecodeError as je:
                    self.logger.warning(f"Failed to parse JSON response: {je}")
                    # If not valid JSON, treat as final answer
                    parsed_response = {"final_answer": response_content}

                # Debug: Log the parsed response to understand what's happening
                self.logger.info(f"Parsed LLM response: {parsed_response}")

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

                    # Validate final answer meets requirements
                    final_answer = parsed_response["final_answer"]
                    if len(final_answer) < 500:
                        # Force model to provide more comprehensive answer
                        messages.append({
                            "role": "user",
                            "content": f"Your answer is too brief. Please provide a comprehensive analysis with specific insights, patterns, and concrete examples. Minimum 500 words required. Include clear sections with markdown formatting."
                        })
                        continue

                    # Validate answer has required structure
                    required_sections = ["Summary", "Detailed Analysis", "Actionable Insights"]
                    missing_sections = [section for section in required_sections if section not in final_answer]

                    if missing_sections:
                        messages.append({
                            "role": "user",
                            "content": f"Your answer is missing required sections: {', '.join(missing_sections)}. Please provide a complete analysis with all required sections."
                        })
                        continue

                    # Yield the actual answer as a separate step
                    answer_step = ReasoningStep(
                        step_number=step_number + 1,
                        step_type=ReasoningStepType.FINAL_ANSWER,
                        description="Final Answer",
                        content=final_answer,
                        duration_ms=0
                    )
                    yield answer_step

                    # Add completion signal
                    completion_step = ReasoningStep(
                        step_number=step_number + 2,
                        step_type=ReasoningStepType.FINAL_ANSWER,
                        description="Reasoning Complete",
                        content="Chain-of-thought reasoning completed successfully.",
                        duration_ms=0
                    )
                    yield completion_step
                    break

                # Check if this is just a reasoning step without final answer
                elif "reasoning" in parsed_response and not "tool" in parsed_response:
                    step_duration = int(timedelta_seconds(step_start) * 1000)

                    reasoning_step = ReasoningStep(
                        step_number=step_number,
                        step_type=ReasoningStepType.ANALYSIS,
                        description="Analysis and reasoning",
                        content=parsed_response.get("reasoning", ""),
                        duration_ms=step_duration
                    )
                    yield reasoning_step

                    # Add the reasoning to conversation history
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(parsed_response)
                    })
                    messages.append({
                        "role": "user",
                        "content": "Continue with your analysis. What's your next step? Remember: You MUST use tools for comprehensive analysis."
                    })
                    continue

                # This is a tool call
                if "tool" in parsed_response and tool_call_count < self.max_tool_calls:
                    tool_call_count += 1

                # Handle continue response (intermediate reasoning without tools)
                elif "continue" in parsed_response and parsed_response.get("continue") is True:
                    step_duration = int(timedelta_seconds(step_start) * 1000)

                    continue_step = ReasoningStep(
                        step_number=step_number,
                        step_type=ReasoningStepType.ANALYSIS,
                        description="Continuing analysis",
                        content=parsed_response.get("reasoning", ""),
                        duration_ms=step_duration
                    )
                    yield continue_step

                    # Add the reasoning to conversation history
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(parsed_response)
                    })
                    messages.append({
                        "role": "user",
                        "content": "Continue with your analysis. What's your next step? Remember: You MUST use tools for comprehensive analysis."
                    })
                    continue

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
                        "content": "You've used the maximum number of tool calls. Please provide your final answer based on the information you've gathered. Your answer must be comprehensive with specific insights and patterns, minimum 500 words with concrete examples."
                    })

                # Handle case where model doesn't provide expected JSON structure
                else:
                    self.logger.warning(f"Unexpected LLM response structure: {parsed_response}")
                    # Treat as final answer to prevent infinite loop
                    parsed_response = {"final_answer": "I'm sorry, I encountered an issue processing your request. Please try again with a more specific question and ensure you use the available tools for comprehensive analysis."}
                    continue

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
