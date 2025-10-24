# Chain-of-Thought Agentic Email Assistant - Implementation Plan

## Executive Summary

This document outlines the implementation plan for transforming the Email Assistant into a **generic chain-of-thought agentic system** that can autonomously perform multi-step reasoning, dynamic data exploration, and tool-calling to answer complex user queries.

**Key Principles:**
- **Generic & Extensible**: The system must work for ANY type of query, not just email/delivery tracking
- **Visible Reasoning**: Users see each step of the AI's thought process
- **Tool-Driven**: LLM can dynamically call tools to gather information
- **Progressive Disclosure**: UI progressively reveals reasoning steps as they happen
- **Streaming**: Each reasoning step streams to the frontend in real-time

---

## Architecture Overview

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER QUERY                                                      │
│ "Am I expecting any deliveries today? What's in the orders?"   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Initial Analysis & Planning                            │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ LLM Reasoning:                                              │ │
│ │ "I need to find delivery-related emails from today.        │ │
│ │  Let me search for emails with keywords like 'delivery',   │ │
│ │  'shipped', 'tracking' from the last 24 hours."            │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Tool Call Decision: search_emails()                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Execute Tool - Search for Delivery Emails              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Tool: search_emails(                                        │ │
│ │   query="delivery OR shipped OR tracking",                 │ │
│ │   days_back=1,                                              │ │
│ │   max_results=10                                            │ │
│ │ )                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Results: 2 emails found                                        │
│   - UPS Update: Package Scheduled for Delivery Today          │
│   - Amazon: Your package is arriving today                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Extract Tracking Numbers                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ LLM Reasoning:                                              │ │
│ │ "I found 2 delivery emails. Now I need to extract the      │ │
│ │  tracking numbers from these emails to find more details." │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Tool Call: extract_entities(email_ids=[...], entity_type="tracking") │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Find Order Details via Tracking Numbers                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Tool: search_emails(                                        │ │
│ │   query="1Z999AA10123456784",  # Tracking number           │ │
│ │   days_back=30                                              │ │
│ │ )                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Results: Found Amazon shipment confirmation email              │
│   - Order #123-4567890-1234567                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Get Order Contents                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Tool: search_emails(                                        │ │
│ │   query="123-4567890-1234567",  # Order number             │ │
│ │   days_back=30                                              │ │
│ │ )                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Results: Found order confirmation email with item list        │
│   - USB-C Cable ($12.99)                                       │
│   - Laptop Stand ($29.99)                                      │
│   - Wireless Mouse ($24.99)                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Synthesize Final Answer                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ LLM generates comprehensive formatted response:             │ │
│ │                                                             │ │
│ │ "Yes, you have 2 deliveries expected today:                │ │
│ │                                                             │ │
│ │ 📦 Package 1 - Amazon                                       │ │
│ │ • Tracking: 1Z999AA10123456784                             │ │
│ │ • Order: #123-4567890-1234567                              │ │
│ │ • Items:                                                   │ │
│ │   - USB-C Cable ($12.99)                                   │ │
│ │   - Laptop Stand ($29.99)                                  │ │
│ │   - Wireless Mouse ($24.99)                                │ │
│ │ • Total: $67.97                                            │ │
│ │                                                             │ │
│ │ 📦 Package 2 - Best Buy                                     │ │
│ │ • Tracking: 1Z888BB20987654321                             │ │
│ │ • Order: #BB987654321                                      │ │
│ │ • Items: Gaming Headset                                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Generic Tool System Design

### Tool Registry Architecture

The system uses a **generic tool registry** where tools are defined declaratively with JSON schemas. This allows the LLM to discover and use tools dynamically.

```python
# File: app/services/email_tools.py

from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
import inspect

class ToolParameter(BaseModel):
    """Schema for a tool parameter"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = False
    enum: Optional[List[str]] = None
    default: Optional[Any] = None

class ToolDefinition(BaseModel):
    """Schema for a tool definition compatible with Ollama function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format

class EmailTool:
    """Base class for email assistant tools"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """Return the tool definition for LLM consumption"""
        raise NotImplementedError

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        raise NotImplementedError


class ToolRegistry:
    """Registry for managing email assistant tools"""

    def __init__(self):
        self.tools: Dict[str, EmailTool] = {}

    def register(self, tool_class: EmailTool):
        """Register a new tool"""
        definition = tool_class.get_definition()
        self.tools[definition.name] = tool_class

    def get_all_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions for LLM"""
        return [tool.get_definition() for tool in self.tools.values()]

    async def execute_tool(
        self,
        db,
        user_id: int,
        tool_name: str,
        **parameters
    ) -> Dict[str, Any]:
        """Execute a tool by name"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        return await self.tools[tool_name].execute(db, user_id, **parameters)


# Global tool registry
email_tool_registry = ToolRegistry()
```

### Core Email Tools

#### 1. search_emails - Generic Email Search

```python
class SearchEmailsTool(EmailTool):
    """Search emails with semantic or keyword query"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="search_emails",
            description="Search through user's emails using semantic search or keywords. Returns relevant emails matching the query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - can be natural language or keywords (e.g., 'tracking number', 'invoice from Amazon', 'meetings this week')"
                    },
                    "days_back": {
                        "type": "number",
                        "description": "How many days back to search (default: 30)",
                        "default": 30
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    },
                    "folder": {
                        "type": "string",
                        "description": "Specific folder to search (e.g., 'INBOX', 'Sent', 'Trash'). If not specified, searches all folders.",
                        "enum": ["INBOX", "Sent", "Drafts", "Trash", "all"]
                    },
                    "sender": {
                        "type": "string",
                        "description": "Filter by sender email address"
                    }
                },
                "required": ["query"]
            }
        )

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        from app.services.email_embedding_service import email_embedding_service

        query = kwargs.get("query")
        days_back = kwargs.get("days_back", 30)
        max_results = kwargs.get("max_results", 10)
        folder = kwargs.get("folder")
        sender = kwargs.get("sender")

        # Use semantic search
        similar_emails = await email_embedding_service.search_similar_emails(
            db=db,
            query_text=query,
            user_id=user_id,
            limit=max_results,
            similarity_threshold=0.3,
            temporal_boost=0.2
        )

        # Filter by folder if specified
        if folder and folder != "all":
            similar_emails = [
                (email, score) for email, score in similar_emails
                if email.folder_path.startswith(folder)
            ]

        # Filter by sender if specified
        if sender:
            similar_emails = [
                (email, score) for email, score in similar_emails
                if sender.lower() in (email.sender_email or "").lower()
            ]

        # Format results
        results = []
        for email, score in similar_emails:
            results.append({
                "email_id": str(email.id),
                "subject": email.subject,
                "sender": email.sender_email,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "folder": email.folder_path,
                "preview": (email.body_text or "")[:200],
                "similarity_score": round(score, 3)
            })

        return {
            "success": True,
            "count": len(results),
            "emails": results
        }


# Register the tool
email_tool_registry.register(SearchEmailsTool)
```

#### 2. extract_entities - Extract Structured Data

```python
class ExtractEntitiesTool(EmailTool):
    """Extract structured entities from emails (tracking numbers, order IDs, dates, etc.)"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="extract_entities",
            description="Extract specific types of entities from emails (tracking numbers, order numbers, phone numbers, dates, amounts, etc.)",
            parameters={
                "type": "object",
                "properties": {
                    "email_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email IDs to extract entities from"
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["tracking_number", "order_number", "phone_number", "email_address", "date", "amount", "url", "address"]
                        },
                        "description": "Types of entities to extract"
                    }
                },
                "required": ["email_ids", "entity_types"]
            }
        )

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        import re
        from sqlalchemy import select
        from app.db.models.email import Email

        email_ids = kwargs.get("email_ids", [])
        entity_types = kwargs.get("entity_types", [])

        # Fetch emails
        query = select(Email).where(
            Email.id.in_(email_ids),
            Email.user_id == user_id
        )
        result = await db.execute(query)
        emails = result.scalars().all()

        # Entity extraction patterns
        patterns = {
            "tracking_number": r'\b(?:1Z[0-9A-Z]{16}|[0-9]{12,22})\b',
            "order_number": r'(?:#|Order\s*Number:?\s*)([0-9A-Z-]{8,30})',
            "phone_number": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "email_address": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "amount": r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?',
            "url": r'https?://[^\s<>"{}|\\^`\[\]]+',
            "date": r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        }

        extracted = {}
        for email in emails:
            email_id = str(email.id)
            extracted[email_id] = {}

            content = f"{email.subject or ''} {email.body_text or ''}"

            for entity_type in entity_types:
                if entity_type in patterns:
                    matches = re.findall(patterns[entity_type], content, re.IGNORECASE)
                    extracted[email_id][entity_type] = list(set(matches))

        return {
            "success": True,
            "entities": extracted
        }


email_tool_registry.register(ExtractEntitiesTool)
```

#### 3. get_email_thread - Get Conversation Context

```python
class GetEmailThreadTool(EmailTool):
    """Get full email thread/conversation"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_email_thread",
            description="Get the complete email thread/conversation for a given email. Useful for understanding context and previous exchanges.",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The email ID to get the thread for"
                    },
                    "include_sent": {
                        "type": "boolean",
                        "description": "Include sent emails in the thread (default: true)",
                        "default": True
                    }
                },
                "required": ["email_id"]
            }
        )

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        from sqlalchemy import select, and_, or_
        from app.db.models.email import Email

        email_id = kwargs.get("email_id")
        include_sent = kwargs.get("include_sent", True)

        # Get the original email
        query = select(Email).where(
            Email.id == email_id,
            Email.user_id == user_id
        )
        result = await db.execute(query)
        email = result.scalar_one_or_none()

        if not email:
            return {"success": False, "error": "Email not found"}

        # Get thread emails
        thread_query = select(Email).where(
            and_(
                Email.user_id == user_id,
                Email.thread_id == email.thread_id
            )
        ).order_by(Email.received_at)

        result = await db.execute(thread_query)
        thread_emails = result.scalars().all()

        # Format thread
        thread = []
        for e in thread_emails:
            thread.append({
                "email_id": str(e.id),
                "subject": e.subject,
                "sender": e.sender_email,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "body": e.body_text[:500] if e.body_text else ""
            })

        return {
            "success": True,
            "thread_count": len(thread),
            "thread": thread
        }


email_tool_registry.register(GetEmailThreadTool)
```

#### 4. analyze_email_content - Deep Content Analysis

```python
class AnalyzeEmailContentTool(EmailTool):
    """Perform deep analysis on email content using LLM"""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_email_content",
            description="Perform deep analysis on email content. Can extract specific information, summarize, identify action items, detect sentiment, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Email ID to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "action_items", "entities", "sentiment", "key_points", "questions"],
                        "description": "Type of analysis to perform"
                    },
                    "custom_prompt": {
                        "type": "string",
                        "description": "Custom analysis prompt if analysis_type is not sufficient"
                    }
                },
                "required": ["email_id", "analysis_type"]
            }
        )

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        from sqlalchemy import select
        from app.db.models.email import Email
        from app.services.ollama_client import ollama_client

        email_id = kwargs.get("email_id")
        analysis_type = kwargs.get("analysis_type")
        custom_prompt = kwargs.get("custom_prompt")

        # Fetch email
        query = select(Email).where(
            Email.id == email_id,
            Email.user_id == user_id
        )
        result = await db.execute(query)
        email = result.scalar_one_or_none()

        if not email:
            return {"success": False, "error": "Email not found"}

        # Build analysis prompt
        prompts = {
            "summary": "Provide a concise 2-3 sentence summary of this email.",
            "action_items": "Extract all action items, tasks, or requests from this email as a bulleted list.",
            "entities": "Extract all important entities: names, companies, products, amounts, dates, etc.",
            "sentiment": "Analyze the sentiment and tone of this email (positive/negative/neutral) and explain why.",
            "key_points": "List the 3-5 most important points or takeaways from this email.",
            "questions": "Extract all questions asked in this email."
        }

        prompt = custom_prompt or prompts.get(analysis_type, "Analyze this email.")

        full_prompt = f"""
{prompt}

Email Subject: {email.subject}
From: {email.sender_email}
Date: {email.received_at}

Email Content:
{email.body_text or email.body_html or 'No content'}
"""

        # Use LLM for analysis
        response = await ollama_client.generate(
            prompt=full_prompt,
            model="qwen3:30b-a3b-thinking-2507-q8_0",  # Use a capable model
            options={"temperature": 0.3}
        )

        return {
            "success": True,
            "analysis_type": analysis_type,
            "result": response.get("response", "")
        }


email_tool_registry.register(AnalyzeEmailContentTool)
```

---

## Chain-of-Thought Service Implementation

### Core Service: AgenticReasoningService

```python
# File: app/services/agentic_reasoning_service.py

from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import json
from enum import Enum

from app.services.ollama_client import ollama_client
from app.services.email_tools import email_tool_registry
from app.utils.logging import get_logger

logger = get_logger("agentic_reasoning_service")


class ReasoningStepType(str, Enum):
    """Types of reasoning steps"""
    PLANNING = "planning"
    TOOL_CALL = "tool_call"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    FINAL_ANSWER = "final_answer"


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
        self.timestamp = datetime.now()

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
            step_start = datetime.now()

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
                except json.JSONDecodeError:
                    # If not valid JSON, treat as final answer
                    parsed_response = {"final_answer": response_content}

                # Check if this is the final answer
                if "final_answer" in parsed_response:
                    step_duration = int((datetime.now() - step_start).total_seconds() * 1000)

                    final_step = ReasoningStep(
                        step_number=step_number,
                        step_type=ReasoningStepType.FINAL_ANSWER,
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
                        duration_ms=int((datetime.now() - step_start).total_seconds() * 1000)
                    )
                    yield planning_step

                    # Execute the tool
                    tool_start = datetime.now()
                    try:
                        tool_result = await email_tool_registry.execute_tool(
                            db=db,
                            user_id=user_id,
                            tool_name=tool_name,
                            **parameters
                        )

                        tool_duration = int((datetime.now() - tool_start).total_seconds() * 1000)

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
                        self.logger.error(f"Tool execution error: {e}")

                        error_step = ReasoningStep(
                            step_number=step_number + 1,
                            step_type=ReasoningStepType.TOOL_CALL,
                            description=f"Tool error: {tool_name}",
                            content=f"Error executing tool: {str(e)}",
                            tool_call={
                                "tool": tool_name,
                                "parameters": parameters
                            },
                            tool_result={"error": str(e)},
                            duration_ms=int((datetime.now() - tool_start).total_seconds() * 1000)
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
                self.logger.error(f"Reasoning step error: {e}")

                error_step = ReasoningStep(
                    step_number=step_number,
                    step_type=ReasoningStepType.ANALYSIS,
                    description="Error in reasoning",
                    content=f"An error occurred: {str(e)}",
                    duration_ms=int((datetime.now() - step_start).total_seconds() * 1000)
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
```

---

## Streaming API Endpoint

### Enhanced Chat Endpoint with Chain-of-Thought

```python
# File: app/api/routes/email_chat.py (additions)

from app.services.agentic_reasoning_service import agentic_reasoning_service, ReasoningStep

@router.post("/chat/stream-agentic")
async def stream_agentic_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Stream chat responses with visible chain-of-thought reasoning.

    This endpoint uses the agentic reasoning service to perform multi-step
    reasoning with tool calling, streaming each step to the client.
    """

    async def generate_reasoning_stream():
        """Generator for SSE streaming"""
        try:
            # Stream reasoning steps
            async for step in agentic_reasoning_service.reason_and_respond(
                db=db,
                user_id=current_user.id,
                user_query=request.message,
                model_name=request.model_name,
                conversation_history=request.conversation_history,
                timeout_ms=request.timeout_ms
            ):
                # Format as SSE
                step_data = step.to_dict()
                yield f"data: {json.dumps(step_data)}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_reasoning_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

## Frontend Implementation

### ReasoningChain Component

```typescript
// File: src/components/EmailAssistant/ReasoningChain.tsx

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  CircularProgress,
  LinearProgress
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Psychology as ThinkingIcon,
  Build as ToolIcon,
  Analytics as AnalysisIcon,
  CheckCircle as CompleteIcon
} from '@mui/icons-material';

interface ReasoningStep {
  step_number: number;
  step_type: 'planning' | 'tool_call' | 'analysis' | 'synthesis' | 'final_answer';
  description: string;
  content: string;
  tool_call?: {
    tool: string;
    parameters: Record<string, any>;
  };
  tool_result?: any;
  duration_ms?: number;
  timestamp: string;
}

interface ReasoningChainProps {
  steps: ReasoningStep[];
  isActive: boolean;
}

export const ReasoningChain: React.FC<ReasoningChainProps> = ({ steps, isActive }) => {
  const [expanded, setExpanded] = useState(true);

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'planning':
        return <ThinkingIcon sx={{ color: '#007AFF' }} />;
      case 'tool_call':
        return <ToolIcon sx={{ color: '#34C759' }} />;
      case 'analysis':
        return <AnalysisIcon sx={{ color: '#FF9500' }} />;
      case 'final_answer':
        return <CompleteIcon sx={{ color: '#34C759' }} />;
      default:
        return <ThinkingIcon sx={{ color: '#8E8E93' }} />;
    }
  };

  const getStepColor = (type: string) => {
    switch (type) {
      case 'planning':
        return 'rgba(0, 122, 255, 0.1)';
      case 'tool_call':
        return 'rgba(52, 199, 89, 0.1)';
      case 'analysis':
        return 'rgba(255, 149, 0, 0.1)';
      case 'final_answer':
        return 'rgba(52, 199, 89, 0.15)';
      default:
        return 'rgba(142, 142, 147, 0.1)';
    }
  };

  if (steps.length === 0) return null;

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid rgba(0, 0, 0, 0.08)',
        borderRadius: 3,
        overflow: 'hidden',
        mb: 2
      }}
    >
      {/* Header */}
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1.5,
          cursor: 'pointer',
          backgroundColor: 'rgba(0, 122, 255, 0.05)',
          '&:hover': {
            backgroundColor: 'rgba(0, 122, 255, 0.08)'
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ThinkingIcon sx={{ color: '#007AFF', fontSize: '1.2rem' }} />
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#007AFF' }}>
            Reasoning Steps
          </Typography>
          <Chip
            label={steps.length}
            size="small"
            sx={{
              backgroundColor: '#007AFF',
              color: 'white',
              height: 20,
              fontSize: '0.7rem'
            }}
          />
          {isActive && (
            <CircularProgress size={14} sx={{ color: '#007AFF' }} />
          )}
        </Box>
        <IconButton
          size="small"
          sx={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s'
          }}
        >
          <ExpandMoreIcon />
        </IconButton>
      </Box>

      {/* Steps */}
      <Collapse in={expanded}>
        <Box sx={{ p: 2 }}>
          {steps.map((step, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                gap: 2,
                mb: index < steps.length - 1 ? 2 : 0,
                position: 'relative'
              }}
            >
              {/* Connector line */}
              {index < steps.length - 1 && (
                <Box
                  sx={{
                    position: 'absolute',
                    left: 20,
                    top: 40,
                    bottom: -16,
                    width: 2,
                    backgroundColor: 'rgba(0, 0, 0, 0.08)'
                  }}
                />
              )}

              {/* Step icon */}
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  backgroundColor: getStepColor(step.step_type),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  zIndex: 1
                }}
              >
                {getStepIcon(step.step_type)}
              </Box>

              {/* Step content */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  {step.description}
                </Typography>

                {step.content && (
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#6e6e73',
                      fontSize: '0.85rem',
                      mb: 1,
                      fontStyle: 'italic'
                    }}
                  >
                    {step.content}
                  </Typography>
                )}

                {/* Tool call details */}
                {step.tool_call && (
                  <Paper
                    elevation={0}
                    sx={{
                      backgroundColor: 'rgba(0, 0, 0, 0.02)',
                      p: 1,
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      Tool: {step.tool_call.tool}
                    </Typography>
                    <pre
                      style={{
                        fontSize: '0.7rem',
                        margin: '4px 0 0 0',
                        fontFamily: 'monospace',
                        color: '#6e6e73'
                      }}
                    >
                      {JSON.stringify(step.tool_call.parameters, null, 2)}
                    </pre>
                  </Paper>
                )}

                {/* Tool result */}
                {step.tool_result && (
                  <Paper
                    elevation={0}
                    sx={{
                      backgroundColor: 'rgba(52, 199, 89, 0.05)',
                      p: 1,
                      borderRadius: 1,
                      mb: 1,
                      border: '1px solid rgba(52, 199, 89, 0.2)'
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#34C759' }}>
                      Result: {step.tool_result.success ? '✓ Success' : '✗ Failed'}
                    </Typography>
                    {step.tool_result.count !== undefined && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                        Found: {step.tool_result.count} items
                      </Typography>
                    )}
                  </Paper>
                )}

                {/* Duration */}
                {step.duration_ms && (
                  <Chip
                    label={`${step.duration_ms}ms`}
                    size="small"
                    sx={{
                      height: 16,
                      fontSize: '0.65rem',
                      backgroundColor: 'rgba(0, 0, 0, 0.05)'
                    }}
                  />
                )}
              </Box>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Paper>
  );
};
```

### Updated AssistantTab Integration

```typescript
// File: src/components/EmailAssistant/tabs/AssistantTab.tsx (additions)

import { ReasoningChain } from '../ReasoningChain';

// Add to component state
const [reasoningSteps, setReasoningSteps] = useState<Map<string, ReasoningStep[]>>(new Map());
const [activeReasoningMessageId, setActiveReasoningMessageId] = useState<string | null>(null);

// Enhanced sendMessage with chain-of-thought support
const handleSendMessage = async () => {
  if (!messageInput.trim() || isStreaming) return;

  const messageId = `msg-${Date.now()}`;
  setActiveReasoningMessageId(messageId);
  setReasoningSteps(new Map(reasoningSteps).set(messageId, []));

  try {
    // Create EventSource for SSE streaming
    const eventSource = new EventSource(
      `/api/v1/email-chat/stream-agentic?message=${encodeURIComponent(messageInput)}&session_id=${currentSession}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'complete') {
        eventSource.close();
        setActiveReasoningMessageId(null);
        return;
      }

      if (data.type === 'error') {
        console.error('Streaming error:', data.error);
        eventSource.close();
        setActiveReasoningMessageId(null);
        return;
      }

      // Add reasoning step
      setReasoningSteps(prev => {
        const steps = prev.get(messageId) || [];
        return new Map(prev).set(messageId, [...steps, data]);
      });
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
      setActiveReasoningMessageId(null);
    };

  } catch (error) {
    console.error('Send message error:', error);
    setActiveReasoningMessageId(null);
  }
};

// In message rendering
{messages.map((message, index) => (
  <Box key={message.id}>
    {/* Show reasoning chain for assistant messages */}
    {message.role === 'assistant' && reasoningSteps.has(message.id) && (
      <ReasoningChain
        steps={reasoningSteps.get(message.id) || []}
        isActive={activeReasoningMessageId === message.id}
      />
    )}

    {/* Original message content */}
    <MarkdownMessage
      content={message.content}
      role={message.role}
    />
  </Box>
))}
```

---

## Configuration & Settings

### Environment Variables

Add to `.env`:

```bash
# Chain-of-Thought Settings
REASONING_MAX_STEPS=10
REASONING_MAX_TOOL_CALLS=7
REASONING_DEFAULT_MODEL=qwen3:30b-a3b-thinking-2507-q8_0

# Tool Execution Settings
TOOL_EXECUTION_TIMEOUT=30000  # 30 seconds per tool
ENABLE_TOOL_CACHING=true
```

### User Preferences

Add to `UserChatPreferences` model:

```python
# app/db/models/chat_session.py

class UserChatPreferences(Base):
    # ... existing fields ...

    # Chain-of-thought settings
    enable_reasoning_chain = Column(Boolean, default=True)
    show_reasoning_steps = Column(Boolean, default=True)
    max_reasoning_steps = Column(Integer, default=10)
    max_tool_calls_per_query = Column(Integer, default=7)
    auto_collapse_reasoning = Column(Boolean, default=False)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/services/test_agentic_reasoning.py

import pytest
from app.services.agentic_reasoning_service import agentic_reasoning_service

@pytest.mark.asyncio
async def test_simple_query_no_tools(db_session, test_user):
    """Test simple query that doesn't require tools"""
    steps = []
    async for step in agentic_reasoning_service.reason_and_respond(
        db=db_session,
        user_id=test_user.id,
        user_query="Hello, how are you?"
    ):
        steps.append(step)

    assert len(steps) > 0
    assert steps[-1].step_type == "final_answer"


@pytest.mark.asyncio
async def test_email_search_tool(db_session, test_user):
    """Test query that triggers email search tool"""
    steps = []
    async for step in agentic_reasoning_service.reason_and_respond(
        db=db_session,
        user_id=test_user.id,
        user_query="Show me emails from Amazon in the last week"
    ):
        steps.append(step)

    # Should have planning, tool call, and final answer
    assert any(s.step_type == "planning" for s in steps)
    assert any(s.step_type == "tool_call" for s in steps)
    assert any(s.tool_call and s.tool_call["tool"] == "search_emails" for s in steps)
```

### Integration Tests

```python
# tests/api/test_agentic_chat.py

@pytest.mark.asyncio
async def test_stream_agentic_chat(client, test_user_token):
    """Test SSE streaming endpoint"""
    response = client.get(
        "/api/v1/email-chat/stream-agentic",
        params={"message": "Find my delivery tracking numbers"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Collect SSE events
    events = []
    for line in response.iter_lines():
        if line.startswith(b"data:"):
            data = json.loads(line[5:])
            events.append(data)

    # Should have multiple steps and completion
    assert len(events) > 1
    assert events[-1]["type"] == "complete"
```

---

## Rollout Plan

### Phase 1: Backend Foundation (Week 1)
- [ ] Implement `EmailTool` base class and `ToolRegistry`
- [ ] Create 4 core tools: `search_emails`, `extract_entities`, `get_email_thread`, `analyze_email_content`
- [ ] Implement `AgenticReasoningService` with reasoning loop
- [ ] Add SSE streaming endpoint `/chat/stream-agentic`
- [ ] Unit tests for tools and reasoning service

### Phase 2: Frontend Components (Week 2)
- [ ] Create `ReasoningChain` component
- [ ] Add SSE client in `AssistantTab`
- [ ] Implement state management for reasoning steps
- [ ] Add user preferences for chain-of-thought
- [ ] Integration testing

### Phase 3: UI/UX Polish (Week 3)
- [ ] Add animations for step transitions
- [ ] Implement auto-collapse after completion
- [ ] Add copy/share reasoning chain feature
- [ ] Performance optimization for large reasoning chains
- [ ] Accessibility improvements

### Phase 4: Advanced Features (Week 4)
- [ ] Add more specialized tools (calendar integration, task creation, etc.)
- [ ] Implement tool caching for performance
- [ ] Add reasoning chain export (PDF/Markdown)
- [ ] Multi-turn conversation with context retention
- [ ] Analytics dashboard for tool usage

---

## Extension Points

### Adding New Tools

To add a new tool, simply create a new class inheriting from `EmailTool`:

```python
class CustomTool(EmailTool):
    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="my_custom_tool",
            description="What this tool does",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "..."}
                },
                "required": ["param1"]
            }
        )

    @classmethod
    async def execute(cls, db, user_id: int, **kwargs) -> Dict[str, Any]:
        # Tool implementation
        return {"success": True, "data": "..."}

# Register it
email_tool_registry.register(CustomTool)
```

### Generic Workflow Support

The system is designed to be generic. Here are examples of non-email workflows:

**1. Calendar Analysis**
```python
class FindMeetingsTool(EmailTool):
    """Find meeting-related information"""
    # Searches emails for calendar invites, extracts meeting times, attendees
```

**2. Financial Analysis**
```python
class AnalyzeExpensesTool(EmailTool):
    """Analyze expenses from receipts in emails"""
    # Searches for receipts, extracts amounts, categorizes spending
```

**3. Project Management**
```python
class TrackTasksTool(EmailTool):
    """Track project tasks mentioned in emails"""
    # Identifies action items, deadlines, project references
```

---

## Performance Considerations

1. **Tool Execution Timeout**: Each tool has a 30-second timeout to prevent hanging
2. **Max Steps Limit**: Prevents infinite reasoning loops
3. **Caching**: Tool results can be cached for repeated queries
4. **Streaming**: Steps stream immediately, no waiting for complete response
5. **Database Connection Pooling**: Ensure sufficient connections for concurrent tool calls

---

## Security Considerations

1. **Tool Permission System**: Users can only access their own data
2. **Rate Limiting**: Limit tool calls per user per minute
3. **Input Sanitization**: All tool parameters validated before execution
4. **LLM Output Validation**: Validate JSON structure before parsing
5. **Audit Logging**: Log all tool executions for security review

---

## Metrics & Monitoring

Track these metrics:

- Average reasoning steps per query
- Tool call success rate
- Tool execution latency
- User engagement with reasoning chain (expand/collapse rates)
- Token usage per reasoning chain
- User satisfaction ratings

---

## Future Enhancements

1. **Multi-Agent Collaboration**: Multiple specialized agents working together
2. **Memory System**: Long-term memory of user preferences and past queries
3. **Proactive Suggestions**: AI suggests queries based on email patterns
4. **Voice Interface**: Speak queries and hear reasoning steps
5. **Visual Reasoning**: Show reasoning as a graph/flowchart
6. **Explainable AI**: Detailed explanations of each decision point

---

## Conclusion

This generic chain-of-thought system transforms the Email Assistant into a powerful agentic system that can:

✅ **Think step-by-step** through complex queries
✅ **Autonomously explore data** using tools
✅ **Show its work** with visible reasoning
✅ **Work for any domain** (not just email/tracking)
✅ **Stream responses** for real-time feedback
✅ **Scale gracefully** with new tools and capabilities

The key innovation is the **generic tool registry** and **reasoning loop** that allow the LLM to autonomously decide which tools to use, when to use them, and how to synthesize information from multiple sources.

This creates a truly intelligent assistant that doesn't just answer questions—it *investigates* them.
