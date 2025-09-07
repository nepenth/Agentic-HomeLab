"""
Documentation generator service for dynamic agents.
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.schemas.agent_schema import AgentSchema, FieldDefinition, FieldType, ProcessingStep, ToolDefinition
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentationGenerator:
    """Service for generating comprehensive documentation from agent schemas."""

    def __init__(self):
        self.templates = {
            "overview": self._get_overview_template(),
            "data_models": self._get_data_models_template(),
            "processing_pipeline": self._get_processing_pipeline_template(),
            "tools": self._get_tools_template(),
            "api_reference": self._get_api_reference_template(),
            "usage_examples": self._get_usage_examples_template(),
            "typescript_types": self._get_typescript_types_template(),
            "frontend_integration": self._get_frontend_integration_template()
        }

    def generate_agent_documentation(self, agent_schema: AgentSchema) -> Dict[str, Any]:
        """
        Generate comprehensive documentation for an agent.

        Args:
            agent_schema: The agent schema to document

        Returns:
            Dictionary containing all documentation sections
        """
        try:
            logger.info(f"Generating documentation for agent: {agent_schema.agent_type}")

            documentation = {
                "agent_type": agent_schema.agent_type,
                "generated_at": datetime.utcnow().isoformat(),
                "version": agent_schema.metadata.version,
                "sections": {}
            }

            # Generate each documentation section
            documentation["sections"]["overview"] = self.generate_overview_section(agent_schema)
            documentation["sections"]["data_models"] = self.generate_data_models_section(agent_schema)
            documentation["sections"]["processing_pipeline"] = self.generate_processing_pipeline_section(agent_schema)
            documentation["sections"]["tools"] = self.generate_tools_section(agent_schema)
            documentation["sections"]["api_reference"] = self.generate_api_reference_section(agent_schema)
            documentation["sections"]["usage_examples"] = self.generate_usage_examples_section(agent_schema)
            documentation["sections"]["typescript_types"] = self.generate_typescript_types_section(agent_schema)
            documentation["sections"]["frontend_integration"] = self.generate_frontend_integration_section(agent_schema)

            logger.info(f"Successfully generated documentation for agent: {agent_schema.agent_type}")
            return documentation

        except Exception as e:
            logger.error(f"Failed to generate documentation for agent {agent_schema.agent_type}: {e}")
            raise

    def generate_overview_section(self, agent_schema: AgentSchema) -> str:
        """Generate the overview section."""
        template = self.templates["overview"]

        return template.format(
            agent_type=agent_schema.agent_type,
            name=agent_schema.metadata.name,
            description=agent_schema.metadata.description,
            category=agent_schema.metadata.category,
            version=agent_schema.metadata.version,
            author=agent_schema.metadata.author or "System Generated",
            input_fields=len(agent_schema.input_schema),
            output_fields=len(agent_schema.output_schema),
            data_models=len(agent_schema.data_models),
            tools=len(agent_schema.tools),
            processing_steps=len(agent_schema.processing_pipeline.steps)
        )

    def generate_data_models_section(self, agent_schema: AgentSchema) -> str:
        """Generate the data models section."""
        template = self.templates["data_models"]

        data_models_docs = []
        for model_name, model_def in agent_schema.data_models.items():
            fields_table = self._generate_fields_table(model_def.fields)

            indexes_info = ""
            if model_def.indexes:
                index_names = [idx.name for idx in model_def.indexes]
                indexes_info = f"\n**Indexes:** {', '.join(index_names)}"

            relationships_info = ""
            if model_def.relationships:
                relationships_info = f"\n**Relationships:** {', '.join(model_def.relationships.keys())}"

            data_models_docs.append(f"""
### {model_name}

**Table:** `{model_def.table_name}`

{model_def.description or "No description provided."}

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
{fields_table}

{indexes_info}{relationships_info}
""")

        return template.format(data_models="\n".join(data_models_docs))

    def generate_processing_pipeline_section(self, agent_schema: AgentSchema) -> str:
        """Generate the processing pipeline section."""
        template = self.templates["processing_pipeline"]

        steps_docs = []
        for i, step in enumerate(agent_schema.processing_pipeline.steps, 1):
            config_info = ""
            if step.config:
                config_info = f"\n**Configuration:** {json.dumps(step.config, indent=2)}"

            retry_info = ""
            if step.retry_config:
                retry_info = f"\n**Retry Configuration:** {json.dumps(step.retry_config, indent=2)}"

            dependencies_info = ""
            if step.depends_on:
                dependencies_info = f"\n**Dependencies:** {', '.join(step.depends_on)}"

            steps_docs.append(f"""
#### Step {i}: {step.name}

**Tool:** `{step.tool}`
**Description:** {step.description or "No description provided."}
**Timeout:** {step.timeout or "Default"} seconds{config_info}{retry_info}{dependencies_info}
""")

        execution_order = self._calculate_execution_order(agent_schema.processing_pipeline.steps)

        return template.format(
            steps="\n".join(steps_docs),
            parallel_execution="Yes" if agent_schema.processing_pipeline.parallel_execution else "No",
            max_retries=agent_schema.processing_pipeline.max_retries,
            timeout=agent_schema.processing_pipeline.timeout or "None",
            execution_levels=len(execution_order),
            execution_order="\n".join([f"- Level {i+1}: {', '.join(level)}" for i, level in enumerate(execution_order)])
        )

    def generate_tools_section(self, agent_schema: AgentSchema) -> str:
        """Generate the tools section."""
        template = self.templates["tools"]

        tools_docs = []
        for tool_name, tool_def in agent_schema.tools.items():
            auth_info = ""
            if tool_def.auth_config:
                auth_info = f"\n**Authentication:** {tool_def.auth_config.type}"

            rate_limit_info = ""
            if tool_def.rate_limit:
                rate_limit_info = f"\n**Rate Limit:** {tool_def.rate_limit}"

            timeout_info = ""
            if tool_def.timeout:
                timeout_info = f"\n**Timeout:** {tool_def.timeout} seconds"

            config_info = ""
            if tool_def.config:
                config_info = f"\n**Configuration:**\n```json\n{json.dumps(tool_def.config, indent=2)}\n```"

            tools_docs.append(f"""
### {tool_name}

**Type:** `{tool_def.type}`
**Description:** {tool_def.description or "No description provided."}{auth_info}{rate_limit_info}{timeout_info}{config_info}
""")

        return template.format(tools="\n".join(tools_docs))

    def generate_api_reference_section(self, agent_schema: AgentSchema) -> str:
        """Generate the API reference section."""
        template = self.templates["api_reference"]

        # Generate input schema documentation
        input_fields_table = self._generate_fields_table(agent_schema.input_schema)

        # Generate output schema documentation
        output_fields_table = self._generate_fields_table(agent_schema.output_schema)

        return template.format(
            agent_type=agent_schema.agent_type,
            input_fields=input_fields_table,
            output_fields=output_fields_table
        )

    def generate_usage_examples_section(self, agent_schema: AgentSchema) -> str:
        """Generate the usage examples section."""
        template = self.templates["usage_examples"]

        # Generate example input
        example_input = {}
        for field_name, field_def in agent_schema.input_schema.items():
            example_input[field_name] = self._generate_field_example(field_def)

        # Generate example configuration
        example_config = {}
        for tool_name, tool_def in agent_schema.tools.items():
            example_config[tool_name] = tool_def.config

        return template.format(
            agent_type=agent_schema.agent_type,
            example_input=json.dumps(example_input, indent=2),
            example_config=json.dumps(example_config, indent=2)
        )

    def generate_typescript_types_section(self, agent_schema: AgentSchema) -> str:
        """Generate TypeScript type definitions."""
        template = self.templates["typescript_types"]

        # Generate TypeScript interfaces
        input_interface = self._generate_typescript_interface("InputData", agent_schema.input_schema)
        output_interface = self._generate_typescript_interface("OutputData", agent_schema.output_schema)

        # Generate configuration interface
        config_interface = self._generate_typescript_config_interface(agent_schema.tools)

        # Create title case version for function names
        agent_type_title = agent_schema.agent_type.title().replace('_', '')

        return template.format(
            agent_type=agent_schema.agent_type,
            agent_type_title=agent_type_title,
            input_interface=input_interface,
            output_interface=output_interface,
            config_interface=config_interface
        )

    def generate_frontend_integration_section(self, agent_schema: AgentSchema) -> str:
        """Generate frontend integration documentation."""
        template = self.templates["frontend_integration"]

        # Generate React hook example
        react_hook = self._generate_react_hook(agent_schema)

        # Generate API client example
        api_client = self._generate_api_client(agent_schema)

        # Create title case version for function names
        agent_type_title = agent_schema.agent_type.title().replace('_', '')

        return template.format(
            agent_type=agent_schema.agent_type,
            agent_type_title=agent_type_title,
            react_hook=react_hook,
            api_client=api_client
        )

    def to_markdown(self, documentation: Dict[str, Any]) -> str:
        """Convert documentation to markdown format."""
        sections = documentation["sections"]

        markdown = f"""# {documentation['agent_type']} Agent Documentation

**Version:** {documentation['version']} | **Generated:** {documentation['generated_at']}

## Table of Contents

- [Overview](#overview)
- [Data Models](#data-models)
- [Processing Pipeline](#processing-pipeline)
- [Tools](#tools)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [TypeScript Types](#typescript-types)
- [Frontend Integration](#frontend-integration)

"""

        for section_name, section_content in sections.items():
            markdown += section_content + "\n\n"

        return markdown

    def to_openapi(self, documentation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert documentation to OpenAPI specification."""
        agent_type = documentation["agent_type"]
        sections = documentation["sections"]

        # Generate OpenAPI spec for this agent
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{agent_type} Agent API",
                "version": documentation["version"],
                "description": sections["overview"]
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }

        # Add schemas
        if "InputData" in sections["typescript_types"]:
            openapi_spec["components"]["schemas"]["InputData"] = {
                "type": "object",
                "description": "Input data schema"
            }

        if "OutputData" in sections["typescript_types"]:
            openapi_spec["components"]["schemas"]["OutputData"] = {
                "type": "object",
                "description": "Output data schema"
            }

        return openapi_spec

    def _generate_fields_table(self, fields: Dict[str, FieldDefinition]) -> str:
        """Generate a markdown table for fields."""
        rows = []
        for field_name, field_def in fields.items():
            field_type = self._format_field_type(field_def)
            required = "✅" if field_def.required else "❌"
            description = field_def.description or ""

            rows.append(f"| {field_name} | {field_type} | {required} | {description} |")

        return "\n".join(rows)

    def _format_field_type(self, field_def: FieldDefinition) -> str:
        """Format field type for display."""
        base_type = field_def.type.value

        if field_def.type == FieldType.ARRAY:
            if field_def.items:
                base_type = f"array[{field_def.items}]"
            else:
                base_type = "array"

        if field_def.range:
            base_type += f" ({field_def.range[0]}-{field_def.range[1]})"

        if field_def.pattern:
            base_type += f" (pattern: {field_def.pattern})"

        return base_type

    def _generate_field_example(self, field_def: FieldDefinition) -> Any:
        """Generate an example value for a field."""
        if field_def.type == FieldType.STRING:
            return "example_string"
        elif field_def.type == FieldType.INTEGER:
            return 42
        elif field_def.type == FieldType.FLOAT:
            return 3.14
        elif field_def.type == FieldType.BOOLEAN:
            return True
        elif field_def.type == FieldType.TEXT:
            return "This is a longer text example..."
        elif field_def.type == FieldType.JSON:
            return {"key": "value"}
        elif field_def.type == FieldType.ARRAY:
            return ["item1", "item2"]
        elif field_def.type == FieldType.ENUM:
            return field_def.values[0] if field_def.values else "example"
        elif field_def.type == FieldType.UUID:
            return "123e4567-e89b-12d3-a456-426614174000"
        elif field_def.type == FieldType.DATETIME:
            return "2024-01-01T12:00:00Z"
        elif field_def.type == FieldType.DATE:
            return "2024-01-01"
        else:
            return "example_value"

    def _generate_typescript_interface(self, interface_name: str, fields: Dict[str, FieldDefinition]) -> str:
        """Generate TypeScript interface."""
        lines = [f"interface {interface_name} {{"]
        for field_name, field_def in fields.items():
            ts_type = self._field_type_to_typescript(field_def)
            optional = "" if field_def.required else "?"
            lines.append(f"  {field_name}{optional}: {ts_type};")
        lines.append("}")
        return "\n".join(lines)

    def _generate_typescript_config_interface(self, tools: Dict[str, ToolDefinition]) -> str:
        """Generate TypeScript configuration interface."""
        lines = ["interface AgentConfig {"]
        for tool_name, tool_def in tools.items():
            lines.append(f"  {tool_name}: {{")

            for key, value in tool_def.config.items():
                ts_type = type(value).__name__
                if ts_type == "str":
                    ts_type = "string"
                elif ts_type == "bool":
                    ts_type = "boolean"
                lines.append(f"    {key}: {ts_type};")

            lines.append("  };")
        lines.append("}")
        return "\n".join(lines)

    def _field_type_to_typescript(self, field_def: FieldDefinition) -> str:
        """Convert field type to TypeScript type."""
        type_mapping = {
            FieldType.STRING: "string",
            FieldType.INTEGER: "number",
            FieldType.FLOAT: "number",
            FieldType.BOOLEAN: "boolean",
            FieldType.TEXT: "string",
            FieldType.JSON: "any",
            FieldType.ARRAY: "any[]",
            FieldType.ENUM: "string",
            FieldType.UUID: "string",
            FieldType.DATETIME: "string",
            FieldType.DATE: "string"
        }

        return type_mapping.get(field_def.type, "any")

    def _generate_react_hook(self, agent_schema: AgentSchema) -> str:
        """Generate React hook example."""
        agent_type = agent_schema.agent_type

        return f'''import {{ useState, useEffect }} from 'react';

interface Use{agent_type.title().replace('_', '')}AgentOptions {{
  agentId?: string;
  autoExecute?: boolean;
}}

export function use{agent_type.title().replace('_', '')}Agent(options: Use{agent_type.title().replace('_', '')}AgentOptions = {{}}) {{
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const executeTask = async (inputData: any) => {{
    setLoading(true);
    setError(null);

    try {{
      const response = await fetch(`/api/v1/agents/dynamic/${{options.agentId}}/execute`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ input_data: inputData }})
      }});

      if (!response.ok) {{
        throw new Error(`HTTP error! status: ${{response.status}}`);
      }}

      const result = await response.json();
      setResults(prev => [...prev, result]);
      return result;
    }} catch (err) {{
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    }} finally {{
      setLoading(false);
    }}
  }};

  return {{
    results,
    loading,
    error,
    executeTask
  }};
}}'''

    def _generate_api_client(self, agent_schema: AgentSchema) -> str:
        """Generate API client example."""
        agent_type = agent_schema.agent_type

        return f'''class {agent_type.title().replace('_', '')}ApiClient {{
  constructor(private baseUrl: string, private apiKey?: string) {{}}

  async createAgent(config: any): Promise<any> {{
    const response = await fetch(`${{this.baseUrl}}/api/v1/agents/dynamic`, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        ...(this.apiKey && {{ 'Authorization': `Bearer ${{this.apiKey}}` }})
      }},
      body: JSON.stringify({{
        agent_type: '{agent_schema.agent_type}',
        name: config.name,
        config: config
      }})
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}

  async executeTask(agentId: string, inputData: any): Promise<any> {{
    const response = await fetch(`${{this.baseUrl}}/api/v1/agents/dynamic/${{agentId}}/execute`, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        ...(this.apiKey && {{ 'Authorization': `Bearer ${{this.apiKey}}` }})
      }},
      body: JSON.stringify({{ input_data: inputData }})
    }});

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}

  async getResults(agentId: string, query: any = {{}}): Promise<any[]> {{
    const params = new URLSearchParams(query);
    const response = await fetch(
      `${{this.baseUrl}}/api/v1/agents/dynamic/${{agentId}}/results?${{params}}`,
      {{
        headers: {{
          ...(this.apiKey && {{ 'Authorization': `Bearer ${{this.apiKey}}` }})
        }}
      }}
    );

    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}

    return response.json();
  }}
}}'''

    def _calculate_execution_order(self, steps: List[ProcessingStep]) -> List[List[str]]:
        """Calculate execution order from processing steps."""
        # Simple topological sort for demonstration
        # In a real implementation, this would be more sophisticated
        return [[step.name for step in steps]]

    def _get_overview_template(self) -> str:
        """Get the overview template."""
        return """# Overview

## {name}

**Agent Type:** `{agent_type}`
**Version:** {version}
**Category:** {category}
**Author:** {author}

### Description

{description}

### Key Features

- **Input Fields:** {input_fields} configurable parameters
- **Output Fields:** {output_fields} result types
- **Data Models:** {data_models} custom data structures
- **Tools:** {tools} integrated processing tools
- **Processing Steps:** {processing_steps} step pipeline

### Quick Start

1. Create an agent instance using the agent type `{agent_type}`
2. Configure input parameters according to your needs
3. Execute tasks and retrieve results
4. Monitor execution through logs and status endpoints

### Requirements

- Dynamic Agent Backend v0.1.0+
- Appropriate tool configurations
- Valid input data matching the schema requirements"""

    def _get_data_models_template(self) -> str:
        """Get the data models template."""
        return """# Data Models

This agent uses the following custom data models for storing and managing information:

{data_models}

### Database Integration

All data models are automatically created as PostgreSQL tables with:
- UUID primary keys
- JSONB fields for flexible data storage
- Configured indexes for optimal performance
- Foreign key relationships where applicable"""

    def _get_processing_pipeline_template(self) -> str:
        """Get the processing pipeline template."""
        return """# Processing Pipeline

## Overview

This agent processes tasks through a series of configurable steps:

**Parallel Execution:** {parallel_execution}
**Max Retries:** {max_retries}
**Global Timeout:** {timeout} seconds
**Execution Levels:** {execution_levels}

## Pipeline Steps

{steps}

## Execution Order

{execution_order}

### Error Handling

- Automatic retry logic with exponential backoff
- Step-level timeout configuration
- Comprehensive error logging and reporting
- Graceful failure handling with rollback capabilities"""

    def _get_tools_template(self) -> str:
        """Get the tools template."""
        return """# Tools

This agent integrates with the following tools for processing tasks:

{tools}

### Tool Configuration

Each tool can be configured with:
- Authentication parameters
- Rate limiting settings
- Timeout configurations
- Custom parameters specific to the tool type

### Built-in Tools

The system provides several built-in tools:
- **LLMProcessor**: Large language model processing
- **DatabaseWriter**: Data persistence and retrieval
- **EmailConnector**: Email service integration"""

    def _get_api_reference_template(self) -> str:
        """Get the API reference template."""
        return """# API Reference

## Endpoints

### Create Agent Instance
```
POST /api/v1/agents/dynamic
```

**Request Body:**
```json
{{
  "agent_type": "{agent_type}",
  "name": "My Agent Instance",
  "config": {{
    "custom_parameter": "value"
  }}
}}
```

### Execute Task
```
POST /api/v1/agents/dynamic/{{agent_id}}/execute
```

**Request Body:**
```json
{{
  "input_data": {{
    // Input fields according to schema
  }},
  "task_config": {{
    "timeout": 300,
    "priority": "high"
  }}
}}
```

### Get Results
```
GET /api/v1/agents/dynamic/{{agent_id}}/results
```

## Input Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
{input_fields}

## Output Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
{output_fields}"""

    def _get_usage_examples_template(self) -> str:
        """Get the usage examples template."""
        return """# Usage Examples

## Python Example

```python
import asyncio
from app.services.dynamic_agent_service import DynamicAgentService

async def main():
    # Create agent service
    agent_service = DynamicAgentService()

    # Create agent instance
    agent = await agent_service.create_agent(
        agent_type="{agent_type}",
        name="Example Agent",
        config={example_config}
    )

    # Execute task
    result = await agent_service.execute_task(
        agent_id=agent.id,
        input_data={example_input}
    )

    print("Task completed:", result)

asyncio.run(main())
```

## cURL Example

```bash
# Create agent instance
curl -X POST http://localhost:8000/api/v1/agents/dynamic \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_type": "{agent_type}",
    "name": "Example Agent",
    "config": {example_config}
  }}'

# Execute task
curl -X POST http://localhost:8000/api/v1/agents/dynamic/$AGENT_ID/execute \\
  -H "Content-Type: application/json" \\
  -d '{{
    "input_data": {example_input}
  }}'
```

## JavaScript Example

```javascript
// Create agent instance
const agentResponse = await fetch('/api/v1/agents/dynamic', {{
  method: 'POST',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify({{
    agent_type: '{agent_type}',
    name: 'Example Agent',
    config: {example_config}
  }})
}});

const agent = await agentResponse.json();

// Execute task
const taskResponse = await fetch(`/api/v1/agents/dynamic/${{agent.id}}/execute`, {{
  method: 'POST',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify({{
    input_data: {example_input}
  }})
}});

const result = await taskResponse.json();
console.log('Task result:', result);
```"""

    def _get_typescript_types_template(self) -> str:
        """Get the TypeScript types template."""
        return """# TypeScript Types

## Type Definitions

{input_interface}

{output_interface}

{config_interface}

## Usage Example

```typescript
import type {{ InputData, OutputData, AgentConfig }} from './types';

async function execute{agent_type_title}Task(
  agentId: string,
  input: InputData
): Promise<OutputData> {{
  const response = await fetch(`/api/v1/agents/dynamic/${{agentId}}/execute`, {{
    method: 'POST',
    headers: {{
      'Content-Type': 'application/json'
    }},
    body: JSON.stringify({{ input_data: input }})
  }});

  if (!response.ok) {{
    throw new Error(`HTTP error! status: ${{response.status}}`);
  }}

  const result = await response.json();
  return result.results as OutputData;
}}
```"""

    def _get_frontend_integration_template(self) -> str:
        """Get the frontend integration template."""
        return """# Frontend Integration

## React Hook

{react_hook}

## API Client

{api_client}

## Integration Example

```typescript
import React from 'react';
import {{ use{agent_type_title}Agent }} from './hooks/use{agent_type_title}Agent';
import type {{ InputData }} from './types';

function {agent_type_title}Component() {{
  const {{ results, loading, error, executeTask }} = use{agent_type_title}Agent({{
    agentId: 'your-agent-id'
  }});

  const handleExecute = async () => {{
    const input: InputData = {{
      // Configure input data according to schema
    }};

    try {{
      await executeTask(input);
    }} catch (err) {{
      console.error('Task execution failed:', err);
    }}
  }};

  return (
    <div>
      <button onClick={{handleExecute}} disabled={{loading}}>
        {{loading ? 'Executing...' : 'Execute Task'}}
      </button>

      {{error && <div className="error">{{error}}</div>}}

      <div className="results">
        {{results.map((result, index) => (
          <div key={{index}} className="result">
            <pre>{{JSON.stringify(result, null, 2)}}</pre>
          </div>
        ))}}
      </div>
    </div>
  );
}}
```"""