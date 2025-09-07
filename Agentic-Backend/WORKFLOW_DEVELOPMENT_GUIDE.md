# 🚀 Agent Workflow Development Guide

This comprehensive guide walks you through creating custom agent workflows in the Agentic Backend system. We'll use a concrete example of building an email processing workflow that analyzes emails and creates actionable tasks.

## 📋 Table of Contents

1. [Understanding the Agent Architecture](#understanding-the-agent-architecture)
2. [Quick Start: Email Processing Workflow](#quick-start-email-processing-workflow)
3. [API Integration Patterns](#api-integration-patterns)
4. [Frontend Integration Examples](#frontend-integration-examples)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## 🏗️ Understanding the Agent Architecture

### Core Components

The Agentic Backend uses a **dynamic agent architecture** with these key components:

#### 1. **Agent Types** (Dynamic Agents)
- **Definition**: Reusable agent templates with predefined schemas
- **Purpose**: Define what an agent does, its data models, and processing pipeline
- **Storage**: Stored in `agent_types` table with JSON schemas

#### 2. **Agent Instances**
- **Definition**: Running instances of agent types
- **Purpose**: Execute specific tasks using the agent type's configuration
- **Storage**: Stored in `agents` table

#### 3. **Tasks**
- **Definition**: Individual execution requests
- **Purpose**: Process input data through an agent's pipeline
- **Storage**: Stored in `tasks` table with status tracking

#### 4. **Tools**
- **Definition**: Reusable components for data processing
- **Purpose**: Handle specific operations (email fetching, LLM processing, etc.)
- **Examples**: `EmailConnector`, `LLMProcessor`, `DatabaseWriter`

### Data Flow

```
User Request → API → Agent Instance → Processing Pipeline → Tools → Results
```

## 📧 Quick Start: Email Processing Workflow

Let's build a complete email processing workflow that:
1. Connects to an IMAP mailbox
2. Retrieves the last 30 days of emails
3. Uses LLM to analyze emails for importance/follow-up needs
4. Creates actionable tasks for the user

### Step 1: Define the Agent Type Schema

First, create the agent type using the AI-assisted builder or manual schema creation:

```json
{
  "agent_type": "email_analyzer",
  "version": "1.0.0",
  "metadata": {
    "name": "Email Priority Analyzer",
    "description": "Analyzes emails and creates follow-up tasks",
    "category": "productivity",
    "author": "Your Name"
  },
  "data_models": {
    "emails": {
      "table_name": "email_analyzer_emails",
      "fields": {
        "id": {"type": "uuid", "required": true},
        "subject": {"type": "string", "required": true, "max_length": 500},
        "sender": {"type": "string", "required": true},
        "body": {"type": "text", "required": true},
        "received_date": {"type": "datetime", "required": true},
        "priority_score": {"type": "float", "required": true},
        "requires_followup": {"type": "boolean", "required": true},
        "followup_reason": {"type": "string"},
        "created_at": {"type": "datetime", "required": true}
      }
    },
    "tasks": {
      "table_name": "email_analyzer_tasks",
      "fields": {
        "id": {"type": "uuid", "required": true},
        "email_id": {"type": "uuid", "required": true},
        "task_description": {"type": "text", "required": true},
        "priority": {"type": "string", "required": true},
        "status": {"type": "string", "required": true, "default": "pending"},
        "due_date": {"type": "datetime"},
        "created_at": {"type": "datetime", "required": true}
      }
    }
  },
  "processing_pipeline": {
    "steps": [
      {
        "name": "fetch_emails",
        "tool": "email_connector",
        "order": 1,
        "config": {
          "max_emails": 100,
          "date_range": "30d"
        }
      },
      {
        "name": "analyze_emails",
        "tool": "llm_processor",
        "order": 2,
        "config": {
          "model": "llama2",
          "temperature": 0.3,
          "system_prompt": "You are an email analysis assistant. Analyze emails for importance and follow-up needs."
        }
      },
      {
        "name": "create_tasks",
        "tool": "database_writer",
        "order": 3,
        "config": {
          "table_name": "email_analyzer_tasks"
        }
      }
    ]
  },
  "tools": {
    "email_connector": {
      "type": "email",
      "config": {
        "service_type": "imap",
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": true
      }
    },
    "llm_processor": {
      "type": "llm",
      "config": {
        "model": "llama2",
        "temperature": 0.3
      }
    },
    "database_writer": {
      "type": "database",
      "config": {
        "table_name": "email_analyzer_tasks"
      }
    }
  },
  "input_schema": {
    "email_credentials": {
      "type": "object",
      "properties": {
        "username": {"type": "string"},
        "password": {"type": "string"}
      },
      "required": ["username", "password"]
    },
    "analysis_criteria": {
      "type": "object",
      "properties": {
        "importance_threshold": {"type": "number", "default": 0.7},
        "categories": {
          "type": "array",
          "items": {"type": "string"},
          "default": ["urgent", "important", "normal"]
        }
      }
    }
  },
  "output_schema": {
    "processed_emails": {
      "type": "integer",
      "description": "Number of emails processed"
    },
    "tasks_created": {
      "type": "integer",
      "description": "Number of follow-up tasks created"
    },
    "summary": {
      "type": "string",
      "description": "Processing summary"
    }
  }
}
```

### Step 2: Create the Agent Type via API

```bash
# 1. Start an AI-assisted builder session
curl -X POST http://localhost:8000/api/v1/agent-builder/start \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create an agent that analyzes my email inbox and creates follow-up tasks for important emails",
    "user_id": "user123"
  }'

# Response includes session_id
{
  "session_id": "session-uuid",
  "initial_description": "Create an agent that analyzes my email inbox...",
  "status": "active",
  "conversation_history": [...],
  "requirements": {...}
}

# 2. Continue the conversation to refine requirements
curl -X POST http://localhost:8000/api/v1/agent-builder/session-uuid/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want it to check my Gmail inbox, analyze emails from the last 30 days, and create tasks for emails that need follow-up"
  }'

# 3. Generate the final schema
curl -X POST http://localhost:8000/api/v1/agent-builder/session-uuid/finalize \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "Email Priority Analyzer"
  }'

# Response includes the created agent type
{
  "agent_type": "email_analyzer",
  "agent_id": "session-uuid",
  "message": "Successfully created agent type: email_analyzer",
  "schema": {...}
}
```

### Step 3: Create an Agent Instance

```bash
# Create an instance of the email analyzer agent
curl -X POST http://localhost:8000/api/v1/agents/create \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Email Analyzer",
    "description": "Analyzes my work emails and creates tasks",
    "agent_type": "email_analyzer",
    "config": {
      "importance_threshold": 0.8,
      "categories": ["urgent", "important", "follow-up"]
    }
  }'

# Response
{
  "id": "agent-uuid",
  "name": "My Email Analyzer",
  "description": "Analyzes my work emails and creates tasks",
  "model_name": "llama2",
  "config": {...},
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Step 4: Run the Email Analysis Task

```bash
# Execute the email analysis
curl -X POST http://localhost:8000/api/v1/tasks/run \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-uuid",
    "input": {
      "email_credentials": {
        "username": "your-email@gmail.com",
        "password": "your-app-password"
      },
      "analysis_criteria": {
        "importance_threshold": 0.8,
        "categories": ["urgent", "important", "follow-up"]
      }
    }
  }'

# Response
{
  "id": "task-uuid",
  "agent_id": "agent-uuid",
  "status": "pending",
  "input": {...},
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Step 5: Monitor Task Progress

```bash
# Check task status
curl http://localhost:8000/api/v1/tasks/task-uuid/status

# Response when completed
{
  "id": "task-uuid",
  "agent_id": "agent-uuid",
  "status": "completed",
  "input": {...},
  "output": {
    "processed_emails": 45,
    "tasks_created": 12,
    "summary": "Processed 45 emails, created 12 follow-up tasks"
  },
  "completed_at": "2024-01-01T12:05:00Z"
}
```

## 🔌 API Integration Patterns

### Authentication

All API endpoints require authentication via API key:

```bash
# Include in all requests
-H "Authorization: Bearer your-api-key"
```

### Error Handling

```javascript
async function apiCall(endpoint, data) {
  try {
    const response = await fetch(`/api/v1/${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API call failed');
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

### Pagination

```javascript
// List agents with pagination
const agents = await apiCall('agents?limit=20&offset=0&active_only=true');

// List tasks with filtering
const tasks = await apiCall('tasks?agent_id=uuid&status=completed&limit=50');
```

### Real-time Updates

```javascript
// WebSocket connection for real-time task updates
const ws = new WebSocket(`ws://localhost:8000/ws/tasks/${taskId}`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Task update:', update);
  // Update UI with new status
  updateTaskStatus(update);
};
```

## 🎨 Frontend Integration Examples

### React Hook for Agent Management

```javascript
// hooks/useAgent.js
import { useState, useEffect } from 'react';

export function useAgent(agentId) {
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAgent();
  }, [agentId]);

  const fetchAgent = async () => {
    try {
      const response = await fetch(`/api/v1/agents/${agentId}`);
      if (!response.ok) throw new Error('Failed to fetch agent');
      const data = await response.json();
      setAgent(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const updateAgent = async (updates) => {
    try {
      const response = await fetch(`/api/v1/agents/${agentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (!response.ok) throw new Error('Failed to update agent');
      const updated = await response.json();
      setAgent(updated);
      return updated;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  return { agent, loading, error, updateAgent };
}
```

### Task Management Component

```javascript
// components/TaskManager.jsx
import React, { useState, useEffect } from 'react';
import { useAgent } from '../hooks/useAgent';

export function TaskManager({ agentId }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const { agent } = useAgent(agentId);

  useEffect(() => {
    if (agentId) {
      fetchTasks();
    }
  }, [agentId]);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`/api/v1/tasks?agent_id=${agentId}&limit=50`);
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const runTask = async (input) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/tasks/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, input })
      });
      const newTask = await response.json();
      setTasks(prev => [newTask, ...prev]);
    } catch (error) {
      console.error('Failed to run task:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await fetch(`/api/v1/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      setTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, status } : task
      ));
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  return (
    <div className="task-manager">
      <h2>{agent?.name} - Task Manager</h2>

      <button
        onClick={() => runTask({ type: 'analyze_emails' })}
        disabled={loading}
      >
        {loading ? 'Running...' : 'Run Email Analysis'}
      </button>

      <div className="tasks-list">
        {tasks.map(task => (
          <div key={task.id} className="task-item">
            <div className="task-info">
              <h3>Task {task.id.slice(0, 8)}</h3>
              <p>Status: {task.status}</p>
              <p>Created: {new Date(task.created_at).toLocaleString()}</p>
            </div>

            <div className="task-actions">
              <select
                value={task.status}
                onChange={(e) => updateTaskStatus(task.id, e.target.value)}
              >
                <option value="pending">Pending</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Email Workflow Dashboard

```javascript
// components/EmailWorkflowDashboard.jsx
import React, { useState, useEffect } from 'react';

export function EmailWorkflowDashboard() {
  const [emails, setEmails] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({});

  useEffect(() => {
    fetchWorkflowData();
    setupWebSocket();
  }, []);

  const fetchWorkflowData = async () => {
    try {
      const [emailsRes, tasksRes, statsRes] = await Promise.all([
        fetch('/api/v1/workflow/emails'),
        fetch('/api/v1/workflow/tasks'),
        fetch('/api/v1/workflow/stats')
      ]);

      setEmails(await emailsRes.json());
      setTasks(await tasksRes.json());
      setStats(await statsRes.json());
    } catch (error) {
      console.error('Failed to fetch workflow data:', error);
    }
  };

  const setupWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws/workflow-updates');

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === 'email_processed') {
        setEmails(prev => [update.email, ...prev]);
      } else if (update.type === 'task_created') {
        setTasks(prev => [update.task, ...prev]);
      }
    };

    return () => ws.close();
  };

  const markTaskComplete = async (taskId) => {
    try {
      await fetch(`/api/v1/workflow/tasks/${taskId}/complete`, {
        method: 'POST'
      });
      setTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, status: 'completed' } : task
      ));
    } catch (error) {
      console.error('Failed to complete task:', error);
    }
  };

  return (
    <div className="email-workflow-dashboard">
      <div className="dashboard-header">
        <h1>Email Priority Workflow</h1>
        <div className="stats">
          <div className="stat-item">
            <span className="stat-label">Emails Processed</span>
            <span className="stat-value">{stats.emailsProcessed || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Tasks Created</span>
            <span className="stat-value">{stats.tasksCreated || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Pending Tasks</span>
            <span className="stat-value">{stats.pendingTasks || 0}</span>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="emails-section">
          <h2>Recent Emails</h2>
          <div className="emails-list">
            {emails.slice(0, 10).map(email => (
              <div key={email.id} className="email-item">
                <div className="email-header">
                  <span className="email-sender">{email.sender}</span>
                  <span className="email-priority" data-priority={email.priority}>
                    {email.priority}
                  </span>
                </div>
                <h3 className="email-subject">{email.subject}</h3>
                <p className="email-preview">{email.body?.slice(0, 100)}...</p>
                <div className="email-meta">
                  <span>{new Date(email.date).toLocaleDateString()}</span>
                  {email.requires_followup && (
                    <span className="followup-badge">Needs Follow-up</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="tasks-section">
          <h2>Follow-up Tasks</h2>
          <div className="tasks-list">
            {tasks.map(task => (
              <div key={task.id} className="task-item" data-status={task.status}>
                <div className="task-content">
                  <h3>{task.task_description}</h3>
                  <div className="task-meta">
                    <span className="task-priority" data-priority={task.priority}>
                      {task.priority}
                    </span>
                    <span className="task-due">
                      {task.due_date ? `Due: ${new Date(task.due_date).toLocaleDateString()}` : 'No due date'}
                    </span>
                  </div>
                </div>

                <div className="task-actions">
                  {task.status === 'pending' && (
                    <button
                      onClick={() => markTaskComplete(task.id)}
                      className="complete-btn"
                    >
                      Mark Complete
                    </button>
                  )}
                  <span className="task-status">{task.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## ⚙️ Advanced Features

### Custom Tool Development

```python
# app/agents/tools/custom_email_analyzer.py
from typing import Dict, Any
from app.agents.tools.base import Tool, ExecutionContext, ToolExecutionError

class CustomEmailAnalyzer(Tool):
    """Custom tool for advanced email analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_model = config.get("llm_model", "llama2")
        self.analysis_depth = config.get("analysis_depth", "standard")
    
    async def execute(self, input_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Analyze emails with custom logic."""
        emails = input_data.get("emails", [])
        
        analyzed_emails = []
        for email in emails:
            # Custom analysis logic
            analysis = await self._analyze_email_content(email)
            analyzed_emails.append({
                **email,
                "analysis": analysis,
                "priority_score": analysis.get("priority_score", 0.5),
                "action_items": analysis.get("action_items", [])
            })
        
        context.add_metadata("emails_analyzed", len(analyzed_emails))
        return {"analyzed_emails": analyzed_emails}
    
    async def _analyze_email_content(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Custom email analysis using LLM."""
        prompt = f"""
        Analyze this email and determine:
        1. Priority score (0.0-1.0)
        2. Whether it requires follow-up
        3. Specific action items needed
        
        Email Subject: {email.get('subject', '')}
        Email Body: {email.get('body', '')}
        
        Respond in JSON format.
        """
        
        # Use LLM for analysis
        response = await self._call_llm(prompt)
        return json.loads(response)
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "CustomEmailAnalyzer",
            "description": "Advanced email analysis with custom logic",
            "input_schema": {
                "emails": {
                    "type": "array",
                    "description": "List of emails to analyze"
                },
                "analysis_criteria": {
                    "type": "object",
                    "properties": {
                        "depth": {"type": "string", "default": "standard"},
                        "include_sentiment": {"type": "boolean", "default": true}
                    }
                }
            },
            "output_schema": {
                "analyzed_emails": {
                    "type": "array",
                    "description": "Emails with analysis results"
                }
            }
        }
```

### Workflow Orchestration

```python
# Complex multi-step workflow
{
  "agent_type": "advanced_email_workflow",
  "processing_pipeline": {
    "steps": [
      {
        "name": "fetch_emails",
        "tool": "email_connector",
        "order": 1
      },
      {
        "name": "categorize_emails",
        "tool": "email_categorizer",
        "order": 2,
        "dependencies": ["fetch_emails"]
      },
      {
        "name": "analyze_important",
        "tool": "custom_email_analyzer",
        "order": 3,
        "dependencies": ["categorize_emails"],
        "condition": "step.categorize_emails.output.important_count > 0"
      },
      {
        "name": "create_tasks",
        "tool": "task_creator",
        "order": 4,
        "dependencies": ["analyze_important"]
      },
      {
        "name": "send_notifications",
        "tool": "notification_sender",
        "order": 5,
        "dependencies": ["create_tasks"]
      }
    ]
  }
}
```

## 🏆 Best Practices

### Agent Design

1. **Single Responsibility**: Each agent should have one clear purpose
2. **Modular Tools**: Break complex operations into reusable tools
3. **Error Handling**: Implement comprehensive error handling and recovery
4. **Resource Awareness**: Monitor memory and CPU usage
5. **Security First**: Validate all inputs and use secure configurations

### API Usage

1. **Rate Limiting**: Respect API rate limits and implement backoff
2. **Error Handling**: Handle network errors and API failures gracefully
3. **Caching**: Cache frequently accessed data when appropriate
4. **Authentication**: Securely store and use API keys
5. **Monitoring**: Log API usage and monitor for issues

### Frontend Integration

1. **Loading States**: Always show loading indicators for async operations
2. **Error Boundaries**: Implement error boundaries for robust UIs
3. **Real-time Updates**: Use WebSockets for live data updates
4. **Optimistic Updates**: Update UI immediately, then sync with server
5. **Accessibility**: Ensure all interactions are keyboard accessible

## 🔧 Troubleshooting

### Common Issues

#### 1. Agent Creation Fails
```bash
# Check agent type exists
curl http://localhost:8000/api/v1/agent-types

# Validate schema
curl -X POST http://localhost:8000/api/v1/schema/validate \
  -H "Content-Type: application/json" \
  -d '{"schema": your_schema_here}'
```

#### 2. Task Execution Fails
```bash
# Check task logs
curl http://localhost:8000/api/v1/logs/task-uuid

# Check agent status
curl http://localhost:8000/api/v1/agents/agent-uuid

# Check system resources
curl http://localhost:8000/api/v1/system/metrics
```

#### 3. Tool Execution Errors
```bash
# Check security incidents
curl http://localhost:8000/api/v1/security/incidents?agent_id=agent-uuid

# Validate tool configuration
curl -X POST http://localhost:8000/api/v1/security/validate-tool-execution \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-uuid",
    "tool_name": "email_connector",
    "input_data": {...}
  }'
```

#### 4. Database Connection Issues
```bash
# Check database health
curl http://localhost:8000/api/v1/health

# Check database metrics
curl http://localhost:8000/api/v1/system/metrics
```

### Performance Optimization

1. **Batch Processing**: Process multiple items together when possible
2. **Caching**: Cache expensive operations and frequently accessed data
3. **Async Processing**: Use async/await for I/O operations
4. **Resource Limits**: Set appropriate limits for memory and CPU usage
5. **Monitoring**: Regularly monitor performance metrics

### Security Considerations

1. **Input Validation**: Always validate and sanitize user inputs
2. **Authentication**: Use strong authentication for all API calls
3. **Authorization**: Implement proper access controls
4. **Data Encryption**: Encrypt sensitive data at rest and in transit
5. **Audit Logging**: Log all security-relevant events

## 📚 Additional Resources

- [API Documentation](API_DOCUMENTATION.md)
- [Security Guide](API_DOCUMENTATION.md#security-features-overview)
- [System Monitoring](API_DOCUMENTATION.md#monitoring-and-metrics)
- [Swagger UI](http://localhost:8000/docs)
- [ReDoc Documentation](http://localhost:8000/redoc)

---

This guide provides a comprehensive foundation for building custom agent workflows. Start with the email processing example, then adapt the patterns for your specific use cases. Remember to test thoroughly and follow security best practices!