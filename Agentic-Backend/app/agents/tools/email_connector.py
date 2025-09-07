"""
Email connector tool for dynamic agents.
"""
from typing import Dict, Any
from app.agents.tools.base import Tool, ExecutionContext, ToolExecutionError


class EmailConnector(Tool):
    """Tool for connecting to email services and retrieving emails."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_type = config.get("service_type", "imap")
        self.host = config.get("host")
        self.port = config.get("port", 993)
        self.use_ssl = config.get("use_ssl", True)
        self.max_emails = config.get("max_emails", 100)
    
    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Connect to email service and retrieve emails.
        
        Args:
            input_data: Must contain connection parameters and query criteria
            context: Execution context
            
        Returns:
            Dictionary with retrieved emails
        """
        try:
            # Extract query parameters
            folder = input_data.get("folder", "INBOX")
            date_range = input_data.get("date_range", "30d")
            unread_only = input_data.get("unread_only", False)
            
            # For now, simulate email retrieval
            # TODO: Integrate with actual email service when available
            mock_emails = [
                {
                    "id": f"email_{i}",
                    "subject": f"Test Email {i}",
                    "sender": f"sender{i}@example.com",
                    "date": "2024-01-01T10:00:00Z",
                    "body": f"This is test email content {i}",
                    "unread": i % 2 == 0
                }
                for i in range(min(10, self.max_emails))
            ]
            
            # Filter by unread if requested
            if unread_only:
                mock_emails = [email for email in mock_emails if email["unread"]]
            
            context.add_metadata("emails_retrieved", len(mock_emails))
            context.add_metadata("folder", folder)
            context.add_metadata("service_type", self.service_type)
            
            return {
                "emails": mock_emails,
                "count": len(mock_emails),
                "folder": folder,
                "service_type": self.service_type,
                "date_range": date_range
            }
            
        except Exception as e:
            raise ToolExecutionError(f"Email connection failed: {str(e)}", self.tool_type)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's input/output schema."""
        return {
            "name": "EmailConnector",
            "description": "Connect to email services and retrieve emails",
            "input_schema": {
                "folder": {
                    "type": "string",
                    "default": "INBOX",
                    "description": "Email folder to query"
                },
                "date_range": {
                    "type": "string",
                    "default": "30d",
                    "description": "Date range for email query (e.g., '30d', '1w')"
                },
                "unread_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to retrieve only unread emails"
                }
            },
            "output_schema": {
                "emails": {
                    "type": "array",
                    "description": "List of retrieved emails"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of emails retrieved"
                },
                "folder": {
                    "type": "string",
                    "description": "Folder that was queried"
                },
                "service_type": {
                    "type": "string",
                    "description": "Email service type used"
                },
                "date_range": {
                    "type": "string",
                    "description": "Date range that was queried"
                }
            },
            "config_schema": {
                "service_type": {
                    "type": "string",
                    "default": "imap",
                    "description": "Email service type (imap, pop3, exchange)"
                },
                "host": {
                    "type": "string",
                    "required": True,
                    "description": "Email server hostname"
                },
                "port": {
                    "type": "integer",
                    "default": 993,
                    "description": "Email server port"
                },
                "use_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to use SSL/TLS"
                },
                "max_emails": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of emails to retrieve"
                }
            }
        }