"""
Database writer tool for dynamic agents.
"""
from typing import Dict, Any
from app.agents.tools.base import Tool, ExecutionContext, ToolExecutionError


class DatabaseWriter(Tool):
    """Tool for writing data to dynamic database tables."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.table_name = config.get("table_name")
        self.batch_size = config.get("batch_size", 100)
        self.upsert = config.get("upsert", False)
    
    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Write data to database table.
        
        Args:
            input_data: Must contain 'data' field with records to write
            context: Execution context
            
        Returns:
            Dictionary with write operation results
        """
        try:
            # Extract data to write
            data = input_data.get("data")
            if not data:
                raise ToolExecutionError("Input must contain 'data' field", self.tool_type)
            
            # Ensure data is a list
            if not isinstance(data, list):
                data = [data]
            
            # For now, simulate database write
            # TODO: Integrate with actual DynamicModel when available
            written_count = len(data)
            
            context.add_metadata("records_written", written_count)
            context.add_metadata("table_name", self.table_name)
            
            return {
                "records_written": written_count,
                "table_name": self.table_name,
                "success": True,
                "batch_size": self.batch_size
            }
            
        except Exception as e:
            raise ToolExecutionError(f"Database write failed: {str(e)}", self.tool_type)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's input/output schema."""
        return {
            "name": "DatabaseWriter",
            "description": "Write data to dynamic database tables",
            "input_schema": {
                "data": {
                    "type": "array",
                    "required": True,
                    "description": "Data records to write to database"
                }
            },
            "output_schema": {
                "records_written": {
                    "type": "integer",
                    "description": "Number of records written"
                },
                "table_name": {
                    "type": "string",
                    "description": "Name of table written to"
                },
                "success": {
                    "type": "boolean",
                    "description": "Whether write operation succeeded"
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Batch size used for writing"
                }
            },
            "config_schema": {
                "table_name": {
                    "type": "string",
                    "required": True,
                    "description": "Name of table to write to"
                },
                "batch_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of records to write in each batch"
                },
                "upsert": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to upsert (update or insert) records"
                }
            }
        }