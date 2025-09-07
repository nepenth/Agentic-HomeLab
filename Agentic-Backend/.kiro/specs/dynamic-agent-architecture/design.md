# Design Document

## Overview

This design introduces a dynamic agent architecture that transforms the current static agent system into a flexible, schema-driven platform. The architecture enables frontend applications to define and deploy specialized agents through declarative configurations, eliminating the need for backend code changes when adding new agent types.

The system uses a plugin-based approach where agents are defined through JSON schemas that specify their data models, processing workflows, tool integrations, and storage requirements. This allows for rapid development of diverse workflows while maintaining type safety and operational consistency.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Agent Registry │    │   Schema Store  │
│   Applications  │◄──►│   & Factory      │◄──►│   & Validator   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌──────────────────┐               │
         │              │  Dynamic Agent   │               │
         │              │   Orchestrator   │               │
         │              └──────────────────┘               │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Task Queue    │    │   Tool Registry  │    │  Dynamic Schema │
│   (Celery)      │    │   & Executor     │    │   Manager       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   External APIs  │    │   File Storage  │
│   (Dynamic      │    │   & Services     │    │   & Cache       │
│   Tables)       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Components

#### 1. Agent Schema System

**Agent Definition Schema:**
```json
{
  "agent_type": "email_analyzer",
  "version": "1.0.0",
  "metadata": {
    "name": "Email Analysis Agent",
    "description": "Analyzes emails for importance and follow-ups",
    "category": "productivity"
  },
  "data_models": {
    "email_analysis_result": {
      "table_name": "email_analysis_results",
      "fields": {
        "email_id": {"type": "string", "required": true},
        "importance_score": {"type": "float", "range": [0, 1]},
        "follow_up_required": {"type": "boolean"},
        "categories": {"type": "array", "items": "string"},
        "summary": {"type": "text"},
        "extracted_entities": {"type": "json"}
      },
      "indexes": ["email_id", "importance_score"]
    }
  },
  "processing_pipeline": {
    "steps": [
      {"name": "email_extraction", "tool": "email_connector"},
      {"name": "content_analysis", "tool": "llm_processor"},
      {"name": "importance_scoring", "tool": "importance_classifier"},
      {"name": "result_storage", "tool": "database_writer"}
    ]
  },
  "tools": {
    "email_connector": {
      "type": "external_api",
      "config": {
        "auth_type": "oauth2",
        "rate_limit": "100/hour"
      }
    },
    "importance_classifier": {
      "type": "ml_model",
      "config": {
        "model_path": "models/email_importance.pkl"
      }
    }
  },
  "input_schema": {
    "email_source": {"type": "string", "required": true},
    "date_range": {"type": "string", "pattern": "\\d+[dwmy]"},
    "filters": {"type": "array", "items": "string"}
  },
  "output_schema": {
    "processed_count": {"type": "integer"},
    "results": {"type": "array", "items": "$ref:email_analysis_result"}
  }
}
```

#### 2. Dynamic Schema Manager

**Responsibilities:**
- Validate agent schemas against meta-schema
- Generate database migrations for custom data models
- Manage schema versioning and compatibility
- Provide schema introspection APIs

**Key Classes:**
```python
class SchemaManager:
    async def validate_schema(self, schema: dict) -> ValidationResult
    async def register_agent_type(self, schema: dict) -> AgentType
    async def create_data_models(self, models: dict) -> List[Table]
    async def migrate_schema(self, old_version: str, new_version: str) -> MigrationPlan

class DynamicModel:
    @classmethod
    def from_schema(cls, schema: dict) -> Type[SQLAlchemyModel]
    
class SchemaValidator:
    def validate_against_meta_schema(self, schema: dict) -> ValidationResult
    def check_compatibility(self, old_schema: dict, new_schema: dict) -> CompatibilityReport
```

#### 3. Agent Factory & Registry

**Agent Factory:**
```python
class AgentFactory:
    def __init__(self, schema_manager: SchemaManager, tool_registry: ToolRegistry):
        self.schema_manager = schema_manager
        self.tool_registry = tool_registry
    
    async def create_agent(self, agent_type: str, config: dict) -> DynamicAgent:
        schema = await self.schema_manager.get_schema(agent_type)
        tools = await self.tool_registry.get_tools(schema.tools)
        return DynamicAgent(schema, tools, config)

class AgentRegistry:
    async def register_agent_type(self, schema: dict) -> str
    async def list_agent_types(self) -> List[AgentTypeInfo]
    async def get_agent_capabilities(self, agent_type: str) -> AgentCapabilities
    async def deprecate_agent_type(self, agent_type: str, sunset_date: datetime) -> None
```

#### 4. AI-Assisted Agent Builder

**Agent Builder Service:**
```python
class AgentBuilderService:
    def __init__(self, ollama_client: OllamaClient, schema_manager: SchemaManager):
        self.ollama_client = ollama_client
        self.schema_manager = schema_manager
        self.sessions: Dict[str, BuilderSession] = {}
    
    async def start_session(self, user_description: str) -> BuilderSession:
        session = BuilderSession(user_description)
        # Use LLM to analyze initial requirements
        analysis = await self.analyze_requirements(user_description)
        session.add_analysis(analysis)
        return session
    
    async def continue_conversation(self, session_id: str, user_input: str) -> ConversationResponse:
        session = self.sessions[session_id]
        # Use LLM to understand user input and refine requirements
        response = await self.process_user_input(session, user_input)
        return response
    
    async def generate_schema(self, session_id: str) -> AgentSchema:
        session = self.sessions[session_id]
        # Use LLM to generate complete agent schema from conversation
        schema = await self.create_schema_from_conversation(session)
        return schema

class BuilderSession:
    def __init__(self, initial_description: str):
        self.id = str(uuid.uuid4())
        self.initial_description = initial_description
        self.conversation_history: List[Dict] = []
        self.requirements: Dict[str, Any] = {}
        self.generated_schema: Optional[AgentSchema] = None
```

#### 5. Dynamic Agent Implementation

**Base Dynamic Agent:**
```python
class DynamicAgent(BaseAgent):
    def __init__(self, schema: AgentSchema, tools: Dict[str, Tool], config: dict):
        super().__init__(...)
        self.schema = schema
        self.tools = tools
        self.pipeline = ProcessingPipeline.from_schema(schema.processing_pipeline)
        self.documentation = AgentDocumentation.from_schema(schema)
    
    async def process_task(self, input_data: dict) -> dict:
        # Validate input against schema
        validated_input = self.schema.validate_input(input_data)
        
        # Execute processing pipeline
        result = await self.pipeline.execute(validated_input, self.tools)
        
        # Validate and store output
        validated_output = self.schema.validate_output(result)
        await self.store_results(validated_output)
        
        return validated_output
    
    async def store_results(self, results: dict) -> None:
        for model_name, data in results.items():
            model_class = self.schema.get_model_class(model_name)
            await self.save_to_database(model_class, data)
    
    async def cleanup_data(self, confirm_deletion: bool = False) -> DataCleanupReport:
        """Remove all data associated with this agent instance."""
        if not confirm_deletion:
            return await self.preview_data_cleanup()
        
        cleanup_report = DataCleanupReport()
        for model_name in self.schema.data_models:
            model_class = self.schema.get_model_class(model_name)
            deleted_count = await self.delete_model_data(model_class)
            cleanup_report.add_deletion(model_name, deleted_count)
        
        return cleanup_report
```

#### 6. Documentation Generation System

**Auto-Documentation Generator:**
```python
class DocumentationGenerator:
    def __init__(self, schema_manager: SchemaManager):
        self.schema_manager = schema_manager
    
    async def generate_agent_docs(self, agent_schema: AgentSchema) -> AgentDocumentation:
        """Generate comprehensive documentation for an agent type."""
        return AgentDocumentation(
            overview=self.generate_overview(agent_schema),
            usage_examples=self.generate_usage_examples(agent_schema),
            api_reference=self.generate_api_reference(agent_schema),
            data_models=self.generate_data_model_docs(agent_schema),
            integration_guide=self.generate_integration_guide(agent_schema)
        )
    
    async def generate_frontend_integration_docs(self) -> FrontendIntegrationGuide:
        """Generate documentation for frontend developers."""
        return FrontendIntegrationGuide(
            quick_start=self.generate_quick_start_guide(),
            api_examples=self.generate_api_examples(),
            typescript_types=self.generate_typescript_definitions(),
            react_components=self.generate_react_examples()
        )

class AgentDocumentation:
    def __init__(self, overview: str, usage_examples: List[dict], 
                 api_reference: dict, data_models: dict, integration_guide: dict):
        self.overview = overview
        self.usage_examples = usage_examples
        self.api_reference = api_reference
        self.data_models = data_models
        self.integration_guide = integration_guide
    
    def to_markdown(self) -> str:
        """Convert documentation to markdown format."""
        pass
    
    def to_openapi(self) -> dict:
        """Convert to OpenAPI specification."""
        pass
```

#### 7. Agent Lifecycle Management

**Agent Lifecycle Manager:**
```python
class AgentLifecycleManager:
    def __init__(self, db_session: AsyncSession, schema_manager: SchemaManager):
        self.db = db_session
        self.schema_manager = schema_manager
    
    async def delete_agent_type(self, agent_type: str, purge_data: bool = False) -> DeletionReport:
        """Delete agent type and optionally all associated data."""
        report = DeletionReport()
        
        if purge_data:
            # Delete all data from dynamic tables
            schema = await self.schema_manager.get_schema(agent_type)
            for model_name, model_def in schema.data_models.items():
                deleted_count = await self.purge_table_data(model_def.table_name)
                report.add_table_deletion(model_def.table_name, deleted_count)
            
            # Drop dynamic tables
            await self.drop_dynamic_tables(schema)
        
        # Remove agent type registration
        await self.remove_agent_type_registration(agent_type)
        report.agent_type_deleted = True
        
        return report
    
    async def preview_deletion_impact(self, agent_type: str) -> DeletionImpactReport:
        """Show what would be deleted without actually deleting."""
        schema = await self.schema_manager.get_schema(agent_type)
        impact = DeletionImpactReport()
        
        for model_name, model_def in schema.data_models.items():
            row_count = await self.count_table_rows(model_def.table_name)
            impact.add_table_impact(model_def.table_name, row_count)
        
        agent_instances = await self.count_agent_instances(agent_type)
        impact.agent_instances = agent_instances
        
        return impact

class DeletionReport:
    def __init__(self):
        self.table_deletions: Dict[str, int] = {}
        self.agent_type_deleted: bool = False
        self.errors: List[str] = []
    
    def add_table_deletion(self, table_name: str, deleted_count: int):
        self.table_deletions[table_name] = deleted_count
```

#### 8. Tool Registry & Plugin System

**Tool Architecture:**
```python
class Tool(ABC):
    @abstractmethod
    async def execute(self, input_data: dict, context: ExecutionContext) -> dict:
        pass
    
    @abstractmethod
    def get_schema(self) -> dict:
        pass

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Type[Tool]] = {}
    
    def register_tool(self, name: str, tool_class: Type[Tool]) -> None:
        self.tools[name] = tool_class
    
    async def get_tool(self, name: str, config: dict) -> Tool:
        tool_class = self.tools[name]
        return tool_class(config)

# Built-in tools
class LLMProcessor(Tool):
    async def execute(self, input_data: dict, context: ExecutionContext) -> dict:
        # Use Ollama client for LLM processing
        pass

class DatabaseWriter(Tool):
    async def execute(self, input_data: dict, context: ExecutionContext) -> dict:
        # Write to dynamic tables
        pass

class EmailConnector(Tool):
    async def execute(self, input_data: dict, context: ExecutionContext) -> dict:
        # Connect to email services
        pass
```

## Components and Interfaces

### API Endpoints

**AI-Assisted Agent Creation:**
```
POST   /api/v1/agent-builder/start            # Start AI-assisted agent creation session
POST   /api/v1/agent-builder/{session}/chat   # Continue conversation about agent requirements
GET    /api/v1/agent-builder/{session}/schema # Get generated schema from conversation
POST   /api/v1/agent-builder/{session}/finalize # Create agent from AI-generated schema
GET    /api/v1/agent-builder/templates        # Get pre-built agent templates
```

**Agent Type Management:**
```
POST   /api/v1/agent-types                    # Register new agent type
GET    /api/v1/agent-types                    # List available agent types
GET    /api/v1/agent-types/{type}             # Get agent type details
PUT    /api/v1/agent-types/{type}             # Update agent type
DELETE /api/v1/agent-types/{type}             # Deprecate agent type (soft delete)
DELETE /api/v1/agent-types/{type}/purge       # Permanently delete agent type and all data
GET    /api/v1/agent-types/{type}/schema      # Get agent schema
GET    /api/v1/agent-types/{type}/capabilities # Get agent capabilities
GET    /api/v1/agent-types/{type}/documentation # Get comprehensive documentation
```

**Dynamic Agent Management:**
```
POST   /api/v1/agents/dynamic                 # Create dynamic agent instance
GET    /api/v1/agents/dynamic/{id}/schema     # Get agent's schema
GET    /api/v1/agents/dynamic/{id}/results    # Query agent results with custom schema
DELETE /api/v1/agents/dynamic/{id}            # Delete agent instance
DELETE /api/v1/agents/dynamic/{id}/data       # Delete agent's stored data
GET    /api/v1/agents/dynamic/{id}/documentation # Get agent-specific documentation
```

**Schema Management:**
```
POST   /api/v1/schemas/validate               # Validate schema before registration
GET    /api/v1/schemas/meta                   # Get meta-schema for validation
POST   /api/v1/schemas/migrate                # Preview schema migration
GET    /api/v1/schemas/documentation          # Get schema creation documentation
```

**Documentation & Discovery:**
```
GET    /api/v1/docs/agent-creation            # Comprehensive agent creation guide
GET    /api/v1/docs/schema-reference          # Schema definition reference
GET    /api/v1/docs/tools                     # Available tools documentation
GET    /api/v1/docs/examples                  # Example agent configurations
GET    /api/v1/docs/frontend-integration      # Frontend integration guide
```

### Database Schema

**Core Tables:**
```sql
-- Agent type definitions
CREATE TABLE agent_types (
    id UUID PRIMARY KEY,
    type_name VARCHAR(255) UNIQUE NOT NULL,
    version VARCHAR(50) NOT NULL,
    schema_definition JSONB NOT NULL,
    documentation JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    deprecated_at TIMESTAMP NULL,
    created_by VARCHAR(255),
    UNIQUE(type_name, version)
);

-- AI Builder sessions
CREATE TABLE agent_builder_sessions (
    id UUID PRIMARY KEY,
    initial_description TEXT NOT NULL,
    conversation_history JSONB NOT NULL DEFAULT '[]',
    requirements JSONB NOT NULL DEFAULT '{}',
    generated_schema JSONB NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Dynamic table metadata
CREATE TABLE dynamic_tables (
    id UUID PRIMARY KEY,
    agent_type_id UUID REFERENCES agent_types(id),
    table_name VARCHAR(255) NOT NULL,
    schema_definition JSONB NOT NULL,
    row_count BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Tool registry
CREATE TABLE registered_tools (
    id UUID PRIMARY KEY,
    tool_name VARCHAR(255) UNIQUE NOT NULL,
    tool_class VARCHAR(500) NOT NULL,
    schema_definition JSONB NOT NULL,
    documentation JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent deletion audit log
CREATE TABLE agent_deletion_log (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(255) NOT NULL,
    deletion_type VARCHAR(50) NOT NULL, -- 'soft', 'hard', 'purge'
    tables_affected JSONB NOT NULL,
    rows_deleted JSONB NOT NULL,
    deleted_by VARCHAR(255),
    deleted_at TIMESTAMP DEFAULT NOW()
);

-- Agent instances with dynamic types
ALTER TABLE agents ADD COLUMN agent_type_id UUID REFERENCES agent_types(id);
ALTER TABLE agents ADD COLUMN dynamic_config JSONB;
ALTER TABLE agents ADD COLUMN documentation_url VARCHAR(500);
```

**Dynamic Table Creation:**
The system will create tables based on agent schemas:
```sql
-- Example: Email analysis results table (created dynamically)
CREATE TABLE email_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    email_id VARCHAR(255) NOT NULL,
    importance_score FLOAT CHECK (importance_score >= 0 AND importance_score <= 1),
    follow_up_required BOOLEAN,
    categories TEXT[],
    summary TEXT,
    extracted_entities JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_analysis_email_id ON email_analysis_results(email_id);
CREATE INDEX idx_email_analysis_importance ON email_analysis_results(importance_score);
```

## Data Models

### Schema Validation Models

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class FieldDefinition(BaseModel):
    type: str
    required: bool = False
    default: Optional[Any] = None
    constraints: Optional[Dict[str, Any]] = None

class DataModelDefinition(BaseModel):
    table_name: str
    fields: Dict[str, FieldDefinition]
    indexes: Optional[List[str]] = None
    relationships: Optional[Dict[str, str]] = None

class ToolDefinition(BaseModel):
    type: str
    config: Dict[str, Any]
    auth_config: Optional[Dict[str, Any]] = None

class ProcessingStep(BaseModel):
    name: str
    tool: str
    config: Optional[Dict[str, Any]] = None
    retry_config: Optional[Dict[str, Any]] = None

class AgentSchema(BaseModel):
    agent_type: str
    version: str
    metadata: Dict[str, Any]
    data_models: Dict[str, DataModelDefinition]
    processing_pipeline: Dict[str, List[ProcessingStep]]
    tools: Dict[str, ToolDefinition]
    input_schema: Dict[str, FieldDefinition]
    output_schema: Dict[str, FieldDefinition]
```

## Error Handling

### Schema Validation Errors
```python
class SchemaValidationError(Exception):
    def __init__(self, errors: List[str], schema_path: str):
        self.errors = errors
        self.schema_path = schema_path

class IncompatibleSchemaError(Exception):
    def __init__(self, breaking_changes: List[str]):
        self.breaking_changes = breaking_changes

class DynamicTableCreationError(Exception):
    def __init__(self, table_name: str, sql_error: str):
        self.table_name = table_name
        self.sql_error = sql_error
```

### Error Recovery Strategies
- **Schema Validation**: Provide detailed error messages with suggestions
- **Migration Failures**: Automatic rollback with state preservation
- **Tool Execution**: Retry with exponential backoff and circuit breaker
- **Dynamic Table Issues**: Graceful degradation with temporary storage

## Testing Strategy

### Unit Tests
- Schema validation logic
- Dynamic model generation
- Tool registry functionality
- Agent factory operations

### Integration Tests
- End-to-end agent creation and execution
- Database migration scenarios
- Tool integration and error handling
- API endpoint functionality

### Performance Tests
- Schema validation performance with large schemas
- Dynamic table query performance
- Concurrent agent execution
- Memory usage with multiple agent types

### Security Tests
- Schema injection attempts
- Tool permission boundaries
- Data access controls
- Resource consumption limits

This design provides a robust foundation for dynamic agent creation while maintaining the architectural principles of your existing system. The schema-driven approach ensures type safety and consistency while enabling the flexibility you need for diverse workflows.
#
# AI-Assisted Agent Creation Flow

### Conversation-Driven Schema Generation

**Step 1: Initial Analysis**
```python
# User provides initial description
user_input = "I want to create an agent that analyzes my emails and finds important ones"

# AI analyzes and asks clarifying questions
ai_response = {
    "understanding": "You want to create an email analysis agent for importance detection",
    "questions": [
        "What email service do you use? (Gmail, Outlook, IMAP)",
        "How do you define 'important'? (sender, keywords, urgency indicators)",
        "What time range should it analyze? (last 30 days, all unread, etc.)",
        "What actions should it suggest? (flag, categorize, create tasks)"
    ],
    "suggested_features": [
        "Importance scoring (0-1 scale)",
        "Category classification",
        "Follow-up task generation",
        "Sender reputation analysis"
    ]
}
```

**Step 2: Iterative Refinement**
```python
# User answers questions
user_responses = {
    "email_service": "Gmail via IMAP",
    "importance_criteria": "VIP senders, urgent keywords, meeting invites",
    "time_range": "last 30 days",
    "desired_actions": "score, categorize, suggest follow-ups"
}

# AI generates refined schema
generated_schema = {
    "agent_type": "gmail_importance_analyzer",
    "data_models": {
        "email_analysis": {
            "fields": {
                "email_id": {"type": "string", "required": True},
                "importance_score": {"type": "float", "range": [0, 1]},
                "category": {"type": "enum", "values": ["urgent", "important", "normal", "low"]},
                "follow_up_suggested": {"type": "boolean"},
                "vip_sender": {"type": "boolean"}
            }
        }
    },
    "tools": {
        "gmail_connector": {"type": "email_service", "config": {"service": "gmail"}},
        "importance_classifier": {"type": "ml_classifier"}
    }
}
```

### Frontend Integration Examples

**React Component for Agent Creation:**
```typescript
interface AgentBuilderProps {
  onAgentCreated: (agent: Agent) => void;
}

const AgentBuilder: React.FC<AgentBuilderProps> = ({ onAgentCreated }) => {
  const [session, setSession] = useState<BuilderSession | null>(null);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  
  const startBuilder = async (description: string) => {
    const response = await fetch('/api/v1/agent-builder/start', {
      method: 'POST',
      body: JSON.stringify({ description }),
      headers: { 'Content-Type': 'application/json' }
    });
    const session = await response.json();
    setSession(session);
    setConversation([session.initial_response]);
  };
  
  const continueConversation = async (userInput: string) => {
    const response = await fetch(`/api/v1/agent-builder/${session.id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message: userInput }),
      headers: { 'Content-Type': 'application/json' }
    });
    const aiResponse = await response.json();
    setConversation(prev => [...prev, { role: 'user', content: userInput }, aiResponse]);
  };
  
  const finalizeAgent = async () => {
    const response = await fetch(`/api/v1/agent-builder/${session.id}/finalize`, {
      method: 'POST'
    });
    const agent = await response.json();
    onAgentCreated(agent);
  };
  
  return (
    <div className="agent-builder">
      {/* Conversation interface */}
      <ConversationView messages={conversation} onSendMessage={continueConversation} />
      
      {/* Schema preview */}
      {session?.generated_schema && (
        <SchemaPreview schema={session.generated_schema} onFinalize={finalizeAgent} />
      )}
    </div>
  );
};
```

**TypeScript Types for Frontend:**
```typescript
interface AgentSchema {
  agent_type: string;
  version: string;
  metadata: {
    name: string;
    description: string;
    category: string;
  };
  data_models: Record<string, DataModelDefinition>;
  processing_pipeline: ProcessingPipeline;
  tools: Record<string, ToolDefinition>;
  input_schema: Record<string, FieldDefinition>;
  output_schema: Record<string, FieldDefinition>;
}

interface AgentDocumentation {
  overview: string;
  usage_examples: UsageExample[];
  api_reference: ApiReference;
  data_models: DataModelDocs[];
  integration_guide: IntegrationGuide;
}

interface AgentCreationRequest {
  schema: AgentSchema;
  initial_config?: Record<string, any>;
  documentation_preferences?: DocumentationPreferences;
}

interface AgentDeletionRequest {
  agent_id: string;
  purge_data: boolean;
  confirmation_token: string;
}
```

## Documentation Generation

### Auto-Generated Agent Documentation

**Example Generated Documentation Structure:**
```markdown
# Gmail Importance Analyzer Agent

## Overview
This agent analyzes Gmail messages to identify important emails based on sender reputation, content analysis, and user-defined criteria.

## Quick Start
```javascript
// Create agent instance
const agent = await createAgent({
  type: 'gmail_importance_analyzer',
  config: {
    gmail_credentials: {...},
    importance_threshold: 0.7
  }
});

// Run analysis
const task = await runTask(agent.id, {
  date_range: '30d',
  folders: ['INBOX', 'Important']
});
```

## Data Models

### EmailAnalysis
| Field | Type | Description |
|-------|------|-------------|
| email_id | string | Unique email identifier |
| importance_score | float | Importance score (0-1) |
| category | enum | Email category classification |
| follow_up_suggested | boolean | Whether follow-up is recommended |

## API Reference

### Create Analysis Task
`POST /api/v1/tasks/run`

**Request Body:**
```json
{
  "agent_id": "uuid",
  "input": {
    "date_range": "30d",
    "folders": ["INBOX"],
    "filters": {
      "unread_only": false,
      "min_importance": 0.5
    }
  }
}
```

## Integration Examples

### React Hook
```typescript
const useEmailAnalysis = (agentId: string) => {
  const [results, setResults] = useState<EmailAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  
  const runAnalysis = async (config: AnalysisConfig) => {
    setLoading(true);
    const task = await runTask(agentId, config);
    // Subscribe to real-time updates
    const ws = new WebSocket(`/ws/tasks/${task.id}`);
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === 'result') {
        setResults(prev => [...prev, update.data]);
      }
    };
  };
  
  return { results, loading, runAnalysis };
};
```
```

### Frontend Integration Guide

**Complete Integration Workflow:**
1. **Discovery**: Use `/api/v1/agent-types` to list available agent types
2. **Documentation**: Fetch `/api/v1/agent-types/{type}/documentation` for integration details
3. **Creation**: Use AI builder or direct schema submission
4. **Execution**: Run tasks and subscribe to real-time updates
5. **Results**: Query custom result schemas via `/api/v1/agents/dynamic/{id}/results`
6. **Management**: Update, deprecate, or delete agents as needed

This comprehensive design ensures that frontend developers have all the information and tools they need to integrate with the dynamic agent system effectively.