"""
Documentation serving API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app.api.dependencies import get_db_session, verify_api_key
from app.services.documentation_generator import DocumentationGenerator
from app.services.schema_manager import SchemaManager
from app.services.agent_builder_service import AgentBuilderService
from app.utils.logging import get_logger

logger = get_logger("docs_api")
router = APIRouter()


@router.get("/agent-creation", response_model=Dict[str, Any])
async def get_agent_creation_guide():
    """Get comprehensive agent creation guide."""
    try:
        guide = {
            "title": "Dynamic Agent Creation Guide",
            "version": "1.0.0",
            "last_updated": "2024-01-01T00:00:00Z",
            "sections": {
                "overview": {
                    "title": "Overview",
                    "content": """
# Dynamic Agent Creation Guide

This guide covers the complete process of creating, configuring, and deploying dynamic agents in the Agentic Backend system.

## What are Dynamic Agents?

Dynamic agents are schema-driven AI agents that can be created and configured through API calls without requiring backend code changes. They support:

- Custom data models and storage schemas
- Flexible processing pipelines
- Tool integrations and external API connections
- Type-safe input/output validation
- Real-time execution monitoring

## Key Benefits

- **Rapid Development**: Create new agent types in minutes
- **Type Safety**: Schema validation ensures data consistency
- **Scalability**: Handle diverse workflows with consistent architecture
- **Maintainability**: Declarative configuration reduces code complexity
- **Integration**: Seamless integration with existing systems
                    """
                },
                "quick_start": {
                    "title": "Quick Start",
                    "content": """
# Quick Start Guide

## 1. Choose an Agent Type

Browse available agent types or create a custom one:

```bash
# List available agent types
curl http://localhost:8000/api/v1/agent-types

# Get specific agent type details
curl http://localhost:8000/api/v1/agent-types/email_analyzer
```

## 2. Create an Agent Instance

```bash
curl -X POST http://localhost:8000/api/v1/agents/dynamic \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_type": "email_analyzer",
    "name": "My Email Assistant",
    "config": {
      "model": "llama2",
      "batch_size": 10
    }
  }'
```

## 3. Execute Tasks

```bash
curl -X POST http://localhost:8000/api/v1/agents/dynamic/$AGENT_ID/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "input_data": {
      "folder": "INBOX",
      "date_range": "7d",
      "criteria": "importance"
    }
  }'
```

## 4. Monitor Results

```bash
# Get task results
curl http://localhost:8000/api/v1/agents/dynamic/$AGENT_ID/results

# Get agent status
curl http://localhost:8000/api/v1/agents/dynamic/$AGENT_ID/status
```
                    """
                },
                "ai_assisted_creation": {
                    "title": "AI-Assisted Creation",
                    "content": """
# AI-Assisted Agent Creation

Use our conversational AI to create agents through natural language:

## Start a Creation Session

```bash
curl -X POST http://localhost:8000/api/v1/agent-builder/start \\
  -H "Content-Type: application/json" \\
  -d '{
    "description": "Create an agent that analyzes customer feedback emails and categorizes them by sentiment and urgency"
  }'
```

## Continue the Conversation

```bash
curl -X POST http://localhost:8000/api/v1/agent-builder/$SESSION_ID/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "I want to use Gmail API and store results in a custom database table"
  }'
```

## Get Schema Preview

```bash
curl http://localhost:8000/api/v1/agent-builder/$SESSION_ID/schema
```

## Finalize Agent Creation

```bash
curl -X POST http://localhost:8000/api/v1/agent-builder/$SESSION_ID/finalize \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_name": "Customer Feedback Analyzer"
  }'
```

## Benefits of AI-Assisted Creation

- **Natural Language**: Describe what you want in plain English
- **Intelligent Guidance**: AI asks clarifying questions
- **Automatic Schema Generation**: Creates complete schemas from conversation
- **Validation**: Ensures generated schemas are valid and complete
- **Best Practices**: Incorporates proven patterns and configurations
                    """
                },
                "manual_creation": {
                    "title": "Manual Schema Creation",
                    "content": """
# Manual Agent Schema Creation

For advanced users who want full control over agent configuration:

## Schema Structure

```json
{
  "agent_type": "custom_agent",
  "metadata": {
    "name": "Custom Agent",
    "description": "Description of what this agent does",
    "category": "productivity",
    "version": "1.0.0"
  },
  "data_models": {
    "results": {
      "table_name": "custom_results",
      "fields": {
        "id": {"type": "uuid", "required": true},
        "result": {"type": "string", "required": true},
        "created_at": {"type": "datetime", "required": true}
      },
      "indexes": ["created_at"]
    }
  },
  "processing_pipeline": {
    "steps": [
      {
        "name": "process_input",
        "tool": "llm_processor",
        "config": {"task": "analyze"}
      }
    ]
  },
  "tools": {
    "llm_processor": {
      "type": "llm",
      "config": {"model": "llama2"}
    }
  },
  "input_schema": {
    "input_text": {"type": "string", "required": true}
  },
  "output_schema": {
    "result": {"type": "string", "required": true}
  }
}
```

## Register Agent Type

```bash
curl -X POST http://localhost:8000/api/v1/agent-types \\
  -H "Content-Type: application/json" \\
  -d @agent_schema.json
```

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text string | `"hello world"` |
| `integer` | Whole number | `42` |
| `float` | Decimal number | `3.14` |
| `boolean` | True/false | `true` |
| `text` | Long text | `"Long text content..."` |
| `json` | JSON object | `{{"key": "value"}}` |
| `array` | List of items | `["item1", "item2"]` |
| `enum` | Fixed options | `"option1"` |
| `uuid` | Unique identifier | `"123e4567-e89b-12d3-a456-426614174000"` |
| `datetime` | Date and time | `"2024-01-01T12:00:00Z"` |
| `date` | Date only | `"2024-01-01"` |

## Validation Rules

- `required`: Field must be provided
- `default`: Default value if not provided
- `range`: Min/max values for numbers
- `pattern`: Regex pattern for strings
- `max_length`: Maximum string length
- `items`: Type of items in arrays
- `values`: Allowed values for enums
                    """
                },
                "best_practices": {
                    "title": "Best Practices",
                    "content": """
# Best Practices for Dynamic Agents

## Schema Design

### 1. Start Simple
Begin with minimal schemas and expand as needed:

```json
{
  "input_schema": {
    "text": {"type": "string", "required": true}
  },
  "output_schema": {
    "result": {"type": "string", "required": true}
  }
}
```

### 2. Use Descriptive Names
Choose clear, descriptive names for fields and models:

```json
// Good
{
  "customer_name": {"type": "string", "required": true},
  "order_total": {"type": "float", "required": true}
}

// Avoid
{
  "cn": {"type": "string", "required": true},
  "ot": {"type": "float", "required": true}
}
```

### 3. Add Validation
Use validation rules to ensure data quality:

```json
{
  "email": {
    "type": "string",
    "required": true,
    "pattern": "^[^@]+@[^@]+\\.[^@]+$"
  },
  "age": {
    "type": "integer",
    "required": true,
    "range": [0, 150]
  }
}
```

## Processing Pipeline

### 1. Keep Pipelines Simple
Start with linear pipelines and add complexity gradually:

```json
{
  "processing_pipeline": {
    "steps": [
      {"name": "validate", "tool": "validator"},
      {"name": "process", "tool": "llm_processor"},
      {"name": "store", "tool": "database_writer"}
    ]
  }
}
```

### 2. Handle Errors Gracefully
Configure retry logic and error handling:

```json
{
  "steps": [
    {
      "name": "api_call",
      "tool": "external_api",
      "retry_config": {
        "max_retries": 3,
        "delay": 1.0,
        "exponential_backoff": true
      }
    }
  ]
}
```

### 3. Use Appropriate Timeouts
Set reasonable timeouts for each step:

```json
{
  "processing_pipeline": {
    "timeout": 300,
    "steps": [
      {
        "name": "quick_task",
        "tool": "llm_processor",
        "timeout": 60
      },
      {
        "name": "slow_api",
        "tool": "external_api",
        "timeout": 120
      }
    ]
  }
}
```

## Tool Configuration

### 1. Secure Credentials
Never hardcode credentials in schemas:

```json
// Good - Use environment variables or secure storage
{
  "tools": {
    "api_client": {
      "type": "external_api",
      "config": {
        "base_url": "https://api.example.com"
      },
      "auth_config": {
        "type": "oauth2",
        "config": {
          "client_id": "$CLIENT_ID",
          "client_secret": "$CLIENT_SECRET"
        }
      }
    }
  }
}
```

### 2. Configure Rate Limits
Protect against API rate limits:

```json
{
  "tools": {
    "api_client": {
      "type": "external_api",
      "rate_limit": "100/hour",
      "timeout": 30
    }
  }
}
```

## Performance Optimization

### 1. Use Appropriate Data Types
Choose the right data type for your use case:

```json
{
  "data_models": {
    "events": {
      "table_name": "user_events",
      "fields": {
        "user_id": {"type": "uuid", "required": true},
        "event_type": {"type": "enum", "values": ["click", "view", "purchase"]},
        "timestamp": {"type": "datetime", "required": true},
        "metadata": {"type": "json"}
      },
      "indexes": ["user_id", "timestamp", "event_type"]
    }
  }
}
```

### 2. Optimize Database Queries
Use indexes for frequently queried fields:

```json
{
  "data_models": {
    "orders": {
      "table_name": "customer_orders",
      "fields": {
        "customer_id": {"type": "uuid", "required": true},
        "order_date": {"type": "datetime",", "required": true},
        "status": {"type": "enum", "values": ["pending", "processing", "shipped", "delivered"]}
      },
      "indexes": ["customer_id", "order_date", "status"]
    }
  }
}
```

## Security Considerations

### 1. Input Validation
Always validate input data:

```json
{
  "input_schema": {
    "user_input": {
      "type": "string",
      "required": true,
      "max_length": 1000,
      "pattern": "^[a-zA-Z0-9\\s.,!?-]*$"
    }
  }
}
```

### 2. Resource Limits
Set appropriate resource limits:

```json
{
  "max_execution_time": 3600,
  "max_memory_usage": 512,
  "allowed_domains": ["api.example.com", "data.example.com"]
}
```

### 3. Data Privacy
Consider data privacy requirements:

```json
{
  "data_models": {
    "user_data": {
      "table_name": "user_profiles",
      "fields": {
        "email": {"type": "string", "required": true},
        "preferences": {"type": "json"}
      }
    }
  }
}
```
                    """
                },
                "troubleshooting": {
                    "title": "Troubleshooting",
                    "content": """
# Troubleshooting Guide

## Common Issues

### Schema Validation Errors

**Problem:** Schema validation fails during agent creation

**Solutions:**
1. Check required fields are present
2. Verify field types match allowed values
3. Ensure array items specify correct type
4. Validate regex patterns in string fields

**Example Error:**
```json
{
  "detail": "Validation error: field 'email' pattern is invalid",
  "field": "input_schema.email.pattern",
  "suggestion": "Use valid regex pattern: ^[^@]+@[^@]+\\.[^@]+$"
}
```

### Tool Execution Failures

**Problem:** Agent tasks fail during execution

**Solutions:**
1. Check tool configurations are correct
2. Verify authentication credentials
3. Ensure external services are accessible
4. Check rate limits and timeouts

**Debugging:**
```bash
# Check agent status
curl http://localhost:8000/api/v1/agents/dynamic/$AGENT_ID/status

# Get recent logs
curl http://localhost:8000/api/v1/logs/history?agent_id=$AGENT_ID&level=error
```

### Database Connection Issues

**Problem:** Dynamic tables cannot be created

**Solutions:**
1. Verify database connectivity
2. Check user permissions for table creation
3. Ensure schema compatibility with database version
4. Validate table names follow database naming conventions

### Performance Problems

**Problem:** Agent execution is slow

**Solutions:**
1. Add appropriate database indexes
2. Configure parallel execution for independent steps
3. Set reasonable timeouts for external calls
4. Optimize data models for query patterns

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `400` | Bad Request | Check request format and required fields |
| `401` | Unauthorized | Verify API key authentication |
| `403` | Forbidden | Check user permissions |
| `404` | Not Found | Verify resource IDs and agent types |
| `422` | Validation Error | Fix schema validation issues |
| `429` | Rate Limited | Wait before retrying |
| `500` | Server Error | Check server logs and contact support |
| `503` | Service Unavailable | External service dependency issue |

## Getting Help

### 1. Check Documentation
```bash
# Get agent-specific documentation
curl http://localhost:8000/api/v1/agent-types/$AGENT_TYPE/documentation

# Get general creation guide
curl http://localhost:8000/api/v1/docs/agent-creation
```

### 2. Enable Debug Logging
```bash
# Enable debug mode
export LOG_LEVEL=DEBUG

# Check application logs
docker-compose logs api
```

### 3. Use Interactive Tools
- **Swagger UI**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/api/v1/health
- **Metrics Dashboard**: http://localhost:8000/api/v1/metrics

### 4. Community Support
- Check GitHub issues for similar problems
- Review existing documentation and examples
- Contact development team for complex issues
                    """
                }
            }
        }

        logger.info("Generated agent creation guide")
        return guide

    except Exception as e:
        logger.error(f"Failed to generate agent creation guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate agent creation guide"
        )


@router.get("/frontend-integration", response_model=Dict[str, Any])
async def get_frontend_integration_guide():
    """Get comprehensive frontend integration guide."""
    try:
        guide = {
            "title": "Frontend Integration Guide",
            "version": "1.0.0",
            "last_updated": "2024-01-01T00:00:00Z",
            "sections": {
                "overview": {
                    "title": "Overview",
                    "content": """
# Frontend Integration Guide

This guide covers integrating the Dynamic Agent Backend with modern frontend applications.

## Supported Frameworks

- **React** (with hooks and TypeScript)
- **Vue.js** (with composition API)
- **Angular** (with services and observables)
- **Vanilla JavaScript** (with fetch/XHR)
- **Svelte** (with stores and reactive statements)

## Key Integration Points

### 1. Agent Management
- Create and configure dynamic agents
- Execute tasks and monitor progress
- Retrieve and display results
- Handle errors and retries

### 2. Real-time Updates
- WebSocket connections for live updates
- Server-sent events for notifications
- Polling strategies for status updates

### 3. Type Safety
- TypeScript interfaces for all API responses
- Runtime validation with generated schemas
- IntelliSense support in IDEs
                    """
                },
                "authentication": {
                    "title": "Authentication",
                    "content": """
# Authentication

## API Key Setup

Configure your API key for authenticated requests:

```javascript
// Environment variable
const API_KEY = process.env.REACT_APP_API_KEY;

// Request headers
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${API_KEY}`
};
```

## Secure Storage

Never expose API keys in client-side code:

```javascript
// ❌ Don't do this
const config = {
  apiKey: 'your-secret-key'
};

// ✅ Do this instead
const config = {
  apiUrl: '/api/v1'
};
```

## Token Management

For user-specific operations:

```javascript
class ApiClient {
  constructor() {
    this.baseUrl = '/api/v1';
    this.token = localStorage.getItem('auth_token');
  }

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers
    });

    if (response.status === 401) {
      // Handle token refresh or redirect to login
      this.handleUnauthorized();
    }

    return response;
  }
}
```
                    """
                },
                "react_integration": {
                    "title": "React Integration",
                    "content": """
# React Integration

## Custom Hooks

Create reusable hooks for agent operations:

```javascript
import { useState, useEffect, useCallback } from 'react';

export function useDynamicAgent(agentId) {
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch agent details
  const fetchAgent = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/agents/dynamic/${agentId}`);
      if (!response.ok) throw new Error('Failed to fetch agent');
      const data = await response.json();
      setAgent(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Execute task
  const executeTask = useCallback(async (inputData) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/agents/dynamic/${agentId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_data: inputData })
      });
      if (!response.ok) throw new Error('Task execution failed');
      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Get results
  const getResults = useCallback(async (query = {}) => {
    try {
      const params = new URLSearchParams(query);
      const response = await fetch(
        `/api/v1/agents/dynamic/${agentId}/results?${params}`
      );
      if (!response.ok) throw new Error('Failed to fetch results');
      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [agentId]);

  useEffect(() => {
    if (agentId) {
      fetchAgent();
    }
  }, [agentId, fetchAgent]);

  return {
    agent,
    loading,
    error,
    executeTask,
    getResults,
    refetch: fetchAgent
  };
}
```

## Component Example

```javascript
import React, { useState } from 'react';
import { useDynamicAgent } from './hooks/useDynamicAgent';

function AgentInterface({ agentId }) {
  const { agent, loading, error, executeTask, getResults } = useDynamicAgent(agentId);
  const [inputData, setInputData] = useState({});
  const [results, setResults] = useState([]);

  const handleExecute = async () => {
    try {
      const result = await executeTask(inputData);
      setResults(prev => [...prev, result]);
    } catch (err) {
      console.error('Execution failed:', err);
    }
  };

  const handleGetResults = async () => {
    try {
      const data = await getResults({ limit: 10 });
      setResults(data);
    } catch (err) {
      console.error('Failed to get results:', err);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!agent) return <div>Agent not found</div>;

  return (
    <div className="agent-interface">
      <h2>{agent.name}</h2>
      <p>{agent.description}</p>

      <div className="input-section">
        <h3>Input Configuration</h3>
        {/* Render input fields based on agent schema */}
      </div>

      <div className="actions">
        <button onClick={handleExecute} disabled={loading}>
          Execute Task
        </button>
        <button onClick={handleGetResults}>
          Get Results
        </button>
      </div>

      <div className="results">
        <h3>Results</h3>
        {results.map((result, index) => (
          <div key={index} className="result-item">
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Context Provider

Create a context for global agent management:

```javascript
import React, { createContext, useContext, useReducer } from 'react';

const AgentContext = createContext();

const agentReducer = (state, action) => {
  switch (action.type) {
    case 'SET_AGENTS':
      return { ...state, agents: action.payload };
    case 'ADD_AGENT':
      return { ...state, agents: [...state.agents, action.payload] };
    case 'UPDATE_AGENT':
      return {
        ...state,
        agents: state.agents.map(agent =>
          agent.id === action.payload.id ? action.payload : agent
        )
      };
    default:
      return state;
  }
};

export function AgentProvider({ children }) {
  const [state, dispatch] = useReducer(agentReducer, {
    agents: [],
    loading: false,
    error: null
  });

  const fetchAgents = async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await fetch('/api/v1/agents/dynamic');
      const agents = await response.json();
      dispatch({ type: 'SET_AGENTS', payload: agents });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const createAgent = async (agentData) => {
    try {
      const response = await fetch('/api/v1/agents/dynamic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      });
      const newAgent = await response.json();
      dispatch({ type: 'ADD_AGENT', payload: newAgent });
      return newAgent;
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
      throw error;
    }
  };

  return (
    <AgentContext.Provider value={{
      ...state,
      fetchAgents,
      createAgent
    }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgents() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgents must be used within AgentProvider');
  }
  return context;
}
```
                    """
                },
                "real_time_updates": {
                    "title": "Real-time Updates",
                    "content": """
# Real-time Updates

## WebSocket Integration

Connect to real-time agent updates:

```javascript
class AgentWebSocketManager {
  constructor(agentId) {
    this.agentId = agentId;
    this.ws = null;
    this.listeners = new Map();
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/tasks/${this.agentId}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
      // Implement reconnection logic
      setTimeout(() => this.connect(), 5000);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };
  }

  handleMessage(data) {
    switch (data.type) {
      case 'task_started':
        this.emit('taskStarted', data.task_id);
        break;
      case 'task_progress':
        this.emit('taskProgress', data);
        break;
      case 'task_completed':
        this.emit('taskCompleted', data);
        break;
      case 'task_failed':
        this.emit('taskFailed', data);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach(callback => callback(data));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const wsManager = new AgentWebSocketManager('agent-123');
wsManager.on('taskCompleted', (data) => {
  console.log('Task completed:', data);
  // Update UI with results
});
wsManager.connect();
```

## Server-Sent Events

Alternative to WebSockets for simple updates:

```javascript
class SSEManager {
  constructor(agentId) {
    this.agentId = agentId;
    this.eventSource = null;
  }

  connect() {
    this.eventSource = new EventSource(
      `/api/v1/logs/stream/${this.agentId}`
    );

    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleUpdate(data);
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      // Implement reconnection
    };
  }

  handleUpdate(data) {
    // Handle different types of updates
    console.log('Received update:', data);
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
}
```

## React Hook for Real-time Updates

```javascript
import { useState, useEffect, useRef } from 'react';

export function useAgentRealtime(agentId) {
  const [updates, setUpdates] = useState([]);
  const [status, setStatus] = useState('disconnected');
  const wsRef = useRef(null);

  useEffect(() => {
    if (!agentId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/tasks/${agentId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setUpdates(prev => [...prev, data]);
    };

    ws.onclose = () => {
      setStatus('disconnected');
    };

    ws.onerror = (error) => {
      setStatus('error');
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [agentId]);

  const sendMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return {
    updates,
    status,
    sendMessage
  };
}
```

## Polling Strategy

Fallback for environments without WebSocket support:

```javascript
export function useAgentPolling(agentId, interval = 5000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!agentId) return;

    const poll = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/v1/agents/dynamic/${agentId}/status`);
        const status = await response.json();
        setData(status);
      } catch (error) {
        console.error('Polling error:', error);
      } finally {
        setLoading(false);
      }
    };

    // Initial poll
    poll();

    // Set up interval
    const intervalId = setInterval(poll, interval);

    return () => clearInterval(intervalId);
  }, [agentId, interval]);

  return { data, loading };
}
```
                    """
                },
                "error_handling": {
                    "title": "Error Handling",
                    "content": """
# Error Handling

## Comprehensive Error Management

Implement robust error handling for agent operations:

```javascript
class AgentErrorHandler {
  static handleApiError(error, context = {}) {
    const baseError = {
      timestamp: new Date().toISOString(),
      context,
      userMessage: 'An unexpected error occurred',
      technicalDetails: null,
      suggestedActions: []
    };

    // Handle different error types
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      switch (status) {
        case 400:
          return this.handleValidationError(data, baseError);
        case 401:
          return this.handleAuthenticationError(data, baseError);
        case 403:
          return this.handleAuthorizationError(data, baseError);
        case 404:
          return this.handleNotFoundError(data, baseError);
        case 422:
          return this.handleSchemaError(data, baseError);
        case 429:
          return this.handleRateLimitError(data, baseError);
        case 500:
          return this.handleServerError(data, baseError);
        default:
          return this.handleUnknownError(error, baseError);
      }
    } else if (error.request) {
      return this.handleNetworkError(error, baseError);
    } else {
      return this.handleClientError(error, baseError);
    }
  }

  static handleValidationError(data, baseError) {
    return {
      ...baseError,
      type: 'VALIDATION_ERROR',
      userMessage: 'Please check your input and try again',
      technicalDetails: data.detail || 'Invalid input data',
      suggestedActions: [
        'Review the input fields',
        'Check data types and formats',
        'Ensure required fields are provided'
      ]
    };
  }

  static handleAuthenticationError(data, baseError) {
    return {
      ...baseError,
      type: 'AUTHENTICATION_ERROR',
      userMessage: 'Authentication required',
      technicalDetails: 'Invalid or missing API key',
      suggestedActions: [
        'Verify your API key',
        'Check API key configuration',
        'Contact administrator for key access'
      ]
    };
  }

  static handleNetworkError(error, baseError) {
    return {
      ...baseError,
      type: 'NETWORK_ERROR',
      userMessage: 'Connection problem',
      technicalDetails: 'Network request failed',
      suggestedActions: [
        'Check your internet connection',
        'Try again in a few moments',
        'Contact support if problem persists'
      ]
    };
  }
}

// Usage in React component
function AgentComponent() {
  const [error, setError] = useState(null);

  const handleError = (error) => {
    const processedError = AgentErrorHandler.handleApiError(error, {
      component: 'AgentComponent',
      action: 'executeTask'
    });
    setError(processedError);
  };

  // Display error to user
  if (error) {
    return (
      <div className="error-container">
        <h3>{error.userMessage}</h3>
        <ul>
          {error.suggestedActions.map((action, index) => (
            <li key={index}>{action}</li>
          ))}
        </ul>
        {process.env.NODE_ENV === 'development' && (
          <details>
            <summary>Technical Details</summary>
            <pre>{error.technicalDetails}</pre>
          </details>
        )}
      </div>
    );
  }

  return <div>Agent content...</div>;
}
```

## Retry Logic

Implement intelligent retry mechanisms:

```javascript
class RetryManager {
  constructor(maxRetries = 3, baseDelay = 1000) {
    this.maxRetries = maxRetries;
    this.baseDelay = baseDelay;
  }

  async executeWithRetry(operation, context = {}) {
    let lastError;

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;

        // Don't retry certain errors
        if (this.shouldNotRetry(error)) {
          throw error;
        }

        if (attempt < this.maxRetries) {
          const delay = this.calculateDelay(attempt);
          console.log(`Attempt ${attempt} failed, retrying in ${delay}ms...`);
          await this.delay(delay);
        }
      }
    }

    throw lastError;
  }

  shouldNotRetry(error) {
    // Don't retry authentication or validation errors
    const nonRetryableStatuses = [400, 401, 403, 422];
    return error.response && nonRetryableStatuses.includes(error.response.status);
  }

  calculateDelay(attempt) {
    // Exponential backoff with jitter
    const exponentialDelay = this.baseDelay * Math.pow(2, attempt - 1);
    const jitter = Math.random() * 0.1 * exponentialDelay;
    return exponentialDelay + jitter;
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Usage
const retryManager = new RetryManager();

const result = await retryManager.executeWithRetry(async () => {
  return await api.executeTask(agentId, inputData);
});
```

## Error Boundaries (React)

Create error boundaries for graceful error handling:

```javascript
import React from 'react';

class AgentErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to monitoring service
    console.error('Agent error boundary caught an error:', error, errorInfo);

    // Report to error tracking service
    if (window.errorTracker) {
      window.errorTracker.captureException(error, {
        extra: errorInfo
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>The agent component encountered an error.</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
          {process.env.NODE_ENV === 'development' && (
            <details>
              <summary>Error Details</summary>
              <pre>{this.state.error?.toString()}</pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <AgentErrorBoundary>
      <AgentInterface agentId="agent-123" />
    </AgentErrorBoundary>
  );
}
```
                    """
                }
            }
        }

        logger.info("Generated frontend integration guide")
        return guide

    except Exception as e:
        logger.error(f"Failed to generate frontend integration guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate frontend integration guide"
        )


@router.get("/examples", response_model=List[Dict[str, Any]])
async def get_examples():
    """Get example configurations and usage patterns."""
    try:
        examples = [
            {
                "title": "Email Analysis Agent",
                "description": "Analyzes emails for importance and generates summaries",
                "category": "productivity",
                "complexity": "intermediate",
                "schema": {
                    "agent_type": "email_analyzer",
                    "data_models": {
                        "analysis_results": {
                            "table_name": "email_analysis_results",
                            "fields": {
                                "email_id": {"type": "string", "required": True},
                                "importance_score": {"type": "float", "range": [0, 1]},
                                "category": {"type": "enum", "values": ["urgent", "important", "normal"]},
                                "summary": {"type": "text"},
                                "sentiment": {"type": "string"}
                            }
                        }
                    },
                    "processing_pipeline": {
                        "steps": [
                            {"name": "extract_content", "tool": "email_connector"},
                            {"name": "analyze_importance", "tool": "llm_processor"},
                            {"name": "store_results", "tool": "database_writer"}
                        ]
                    },
                    "tools": {
                        "email_connector": {"type": "email_service", "config": {"service": "gmail"}},
                        "llm_processor": {"type": "llm", "config": {"model": "llama2"}},
                        "database_writer": {"type": "database", "config": {"table": "analysis_results"}}
                    },
                    "input_schema": {
                        "folder": {"type": "string", "default": "INBOX"},
                        "date_range": {"type": "string", "default": "7d"},
                        "max_emails": {"type": "integer", "default": 50}
                    },
                    "output_schema": {
                        "analyzed_count": {"type": "integer"},
                        "results": {"type": "array", "items": "analysis_result"}
                    }
                },
                "usage_example": {
                    "endpoint": "POST /api/v1/agents/dynamic/{agent_id}/execute",
                    "request": {
                        "input_data": {
                            "folder": "INBOX",
                            "date_range": "24h",
                            "max_emails": 10
                        }
                    },
                    "response": {
                        "task_id": "task-123",
                        "status": "completed",
                        "results": {
                            "analyzed_count": 8,
                            "results": [
                                {
                                    "email_id": "msg_001",
                                    "importance_score": 0.9,
                                    "category": "urgent",
                                    "summary": "Urgent client request requiring immediate attention",
                                    "sentiment": "concerned"
                                }
                            ]
                        }
                    }
                }
            },
            {
                "title": "Document Summarizer",
                "description": "Creates concise summaries of long documents",
                "category": "content",
                "complexity": "beginner",
                "schema": {
                    "agent_type": "document_summarizer",
                    "data_models": {
                        "summaries": {
                            "table_name": "document_summaries",
                            "fields": {
                                "document_id": {"type": "string", "required": True},
                                "title": {"type": "string", "required": True},
                                "summary": {"type": "text", "required": True},
                                "compression_ratio": {"type": "float"},
                                "created_at": {"type": "datetime", "required": True}
                            }
                        }
                    },
                    "processing_pipeline": {
                        "steps": [
                            {"name": "extract_text", "tool": "text_extractor"},
                            {"name": "generate_summary", "tool": "llm_processor"},
                            {"name": "store_summary", "tool": "database_writer"}
                        ]
                    },
                    "tools": {
                        "text_extractor": {"type": "text_processing", "config": {}},
                        "llm_processor": {"type": "llm", "config": {"model": "llama2", "temperature": 0.3}},
                        "database_writer": {"type": "database", "config": {"table": "summaries"}}
                    },
                    "input_schema": {
                        "document_text": {"type": "text", "required": True},
                        "summary_length": {"type": "enum", "values": ["short", "medium", "long"], "default": "medium"},
                        "focus_areas": {"type": "array", "items": "string"}
                    },
                    "output_schema": {
                        "summary": {"type": "text", "required": True},
                        "key_points": {"type": "array", "items": "string"},
                        "compression_ratio": {"type": "float"}
                    }
                },
                "usage_example": {
                    "endpoint": "POST /api/v1/agents/dynamic/{agent_id}/execute",
                    "request": {
                        "input_data": {
                            "document_text": "Long document content here...",
                            "summary_length": "short",
                            "focus_areas": ["main_arguments", "conclusions"]
                        }
                    },
                    "response": {
                        "task_id": "task-456",
                        "status": "completed",
                        "results": {
                            "summary": "Concise summary of the document...",
                            "key_points": ["Point 1", "Point 2", "Point 3"],
                            "compression_ratio": 0.15
                        }
                    }
                }
            },
            {
                "title": "Data Analysis Agent",
                "description": "Analyzes datasets and generates insights",
                "category": "analytics",
                "complexity": "advanced",
                "schema": {
                    "agent_type": "data_analyzer",
                    "data_models": {
                        "analysis_reports": {
                            "table_name": "data_analysis_reports",
                            "fields": {
                                "dataset_id": {"type": "string", "required": True},
                                "analysis_type": {"type": "string", "required": True},
                                "insights": {"type": "json", "required": True},
                                "visualizations": {"type": "json"},
                                "confidence_score": {"type": "float", "range": [0, 1]},
                                "created_at": {"type": "datetime", "required": True}
                            }
                        }
                    },
                    "processing_pipeline": {
                        "steps": [
                            {"name": "validate_data", "tool": "data_validator"},
                            {"name": "analyze_patterns", "tool": "llm_processor"},
                            {"name": "generate_insights", "tool": "analytics_engine"},
                            {"name": "create_visualizations", "tool": "chart_generator"},
                            {"name": "store_report", "tool": "database_writer"}
                        ]
                    },
                    "tools": {
                        "data_validator": {"type": "data_processing", "config": {}},
                        "llm_processor": {"type": "llm", "config": {"model": "llama2", "temperature": 0.1}},
                        "analytics_engine": {"type": "analytics", "config": {"algorithms": ["clustering", "correlation"]}},
                        "chart_generator": {"type": "visualization", "config": {"formats": ["png", "svg"]}},
                        "database_writer": {"type": "database", "config": {"table": "analysis_reports"}}
                    },
                    "input_schema": {
                        "dataset": {"type": "json", "required": True},
                        "analysis_type": {"type": "enum", "values": ["exploratory", "predictive", "diagnostic"], "default": "exploratory"},
                        "focus_metrics": {"type": "array", "items": "string"},
                        "include_visualizations": {"type": "boolean", "default": True}
                    },
                    "output_schema": {
                        "insights": {"type": "json", "required": True},
                        "visualizations": {"type": "json"},
                        "confidence_score": {"type": "float", "range": [0, 1]},
                        "recommendations": {"type": "array", "items": "string"}
                    }
                },
                "usage_example": {
                    "endpoint": "POST /api/v1/agents/dynamic/{agent_id}/execute",
                    "request": {
                        "input_data": {
                            "dataset": "sample_data.json",
                            "analysis_type": "exploratory",
                            "focus_metrics": ["revenue", "users"],
                            "include_visualizations": True
                        }
                    },
                    "response": {
                        "task_id": "task-789",
                        "status": "completed",
                        "results": {
                            "insights": {
                                "correlations": {"revenue_users": 0.85},
                                "clusters": 3,
                                "outliers": 5
                            },
                            "visualizations": {
                                "charts": ["correlation_matrix.png", "cluster_plot.svg"]
                            },
                            "confidence_score": 0.92,
                            "recommendations": [
                                "Focus on high-value user segments",
                                "Investigate outlier data points"
                            ]
                        }
                    }
                }
            }
        ]

        logger.info("Generated examples collection")
        return examples

    except Exception as e:
        logger.error(f"Failed to generate examples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate examples"
        )


@router.get("/agent-types/{agent_type}/documentation", response_model=Dict[str, Any])
async def get_agent_type_documentation(
    agent_type: str,
    format: str = Query("markdown", description="Output format (markdown, html, json)"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive documentation for a specific agent type."""
    try:
        # Get agent type schema
        schema_manager = SchemaManager(db)
        agent_type_obj = await schema_manager.get_agent_type(agent_type)

        if not agent_type_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent type '{agent_type}' not found"
            )

        # Convert database model to schema
        from app.schemas.agent_schema import AgentSchema, AgentMetadata
        schema = AgentSchema(
            agent_type=agent_type_obj.type_name,
            metadata=AgentMetadata(
                name=agent_type_obj.type_name,
                description="",
                category="general",
                version=agent_type_obj.version
            ),
            data_models={},  # Would need to be populated from related tables
            processing_pipeline={},  # Would need to be populated
            tools={},  # Would need to be populated
            input_schema={},  # Would need to be populated
            output_schema={}  # Would need to be populated
        )

        # Generate documentation
        doc_generator = DocumentationGenerator()
        documentation = doc_generator.generate_agent_documentation(schema)

        # Format output
        if format == "markdown":
            result = doc_generator.to_markdown(documentation)
        elif format == "html":
            # Convert markdown to HTML (would need markdown library)
            result = f"<pre>{doc_generator.to_markdown(documentation)}</pre>"
        elif format == "json":
            result = documentation
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}"
            )

        logger.info(f"Generated documentation for agent type: {agent_type} in format: {format}")
        return {
            "agent_type": agent_type,
            "format": format,
            "documentation": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate documentation for agent type {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate agent type documentation"
        )