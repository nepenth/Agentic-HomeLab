"""
Email Tools Package

This package contains the tool system for the chain-of-thought agentic email assistant.
"""

from app.services.email_tools.base import (
    EmailTool,
    ToolDefinition,
    ToolRegistry,
    email_tool_registry
)

# Import all tools to register them
from app.services.email_tools import search_emails
from app.services.email_tools import extract_entities
from app.services.email_tools import get_email_thread
from app.services.email_tools import analyze_email_content

__all__ = [
    "EmailTool",
    "ToolDefinition",
    "ToolRegistry",
    "email_tool_registry"
]
