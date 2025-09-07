# Agent Workflow Examples

This directory contains complete examples of how to create and integrate custom agent workflows with the Agentic Backend system.

## 📧 Email Processing Workflow Example

A comprehensive example that demonstrates creating an email analyzer workflow that:
- Connects to IMAP email servers
- Analyzes emails for importance and follow-up needs
- Creates actionable tasks
- Provides a full frontend dashboard for management

### Files

- **`email_analyzer_agent.json`** - Complete agent type schema definition
- **`email_workflow_api_example.py`** - Python API client with full workflow automation
- **`EmailWorkflowDashboard.jsx`** - React component for workflow management
- **`EmailWorkflowDashboard.css`** - Complete styling for the dashboard

### Quick Start

1. **Create the Agent Type:**
   ```bash
   # Use the AI-assisted builder
   curl -X POST http://localhost:8000/api/v1/agent-builder/start \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"description": "Create an agent that analyzes my email inbox and creates follow-up tasks for important emails"}'
   ```

2. **Create an Agent Instance:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/agents/create \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "My Email Analyzer",
       "agent_type": "email_analyzer",
       "config": {"importance_threshold": 0.7}
     }'
   ```

3. **Run the Workflow:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/tasks/run \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "your-agent-id",
       "input": {
         "email_credentials": {
           "username": "your-email@gmail.com",
           "password": "your-app-password"
         }
       }
     }'
   ```

4. **Monitor Progress:**
   ```bash
   curl http://localhost:8000/api/v1/tasks/your-task-id/status
   ```

## 🏗️ Architecture Overview

### Agent Type Schema Structure

```json
{
  "agent_type": "unique_identifier",
  "metadata": {
    "name": "Display Name",
    "description": "What the agent does",
    "category": "productivity|data|automation"
  },
  "data_models": {
    "table_name": {
      "fields": {
        "field_name": {
          "type": "string|integer|float|boolean|datetime|json|uuid",
          "required": true,
          "max_length": 255,
          "default": "value"
        }
      }
    }
  },
  "processing_pipeline": {
    "steps": [
      {
        "name": "step_name",
        "tool": "tool_name",
        "order": 1,
        "config": {}
      }
    ]
  },
  "tools": {
    "tool_name": {
      "type": "email|llm|database|custom",
      "config": {}
    }
  },
  "input_schema": {},
  "output_schema": {}
}
```

### Available Tool Types

| Tool Type | Purpose | Configuration |
|-----------|---------|---------------|
| `email` | Connect to email servers | `host`, `port`, `credentials` |
| `llm` | AI text processing | `model`, `temperature`, `prompts` |
| `database` | Data storage/retrieval | `table_name`, `operations` |
| `custom` | Your own tools | Custom configuration |

## 🔧 API Integration Examples

### Python Client

```python
from email_workflow_api_example import EmailWorkflowClient

async def main():
    async with EmailWorkflowClient(api_key="your-key") as client:
        # Create agent
        agent = await client.create_email_analyzer_agent("My Agent")

        # Run analysis
        task = await client.run_email_analysis({
            "username": "email@example.com",
            "password": "password"
        })

        # Monitor progress
        result = await client.wait_for_completion()
        print(f"Processed {result['output']['processed_emails']} emails")
```

### JavaScript/React Integration

```javascript
// Use the EmailWorkflowDashboard component
import EmailWorkflowDashboard from './EmailWorkflowDashboard';

function App() {
  return (
    <div>
      <EmailWorkflowDashboard />
    </div>
  );
}
```

### Real-time Updates

```javascript
// WebSocket connection for live updates
const ws = new WebSocket('ws://localhost:8000/ws/workflow-updates');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  if (update.type === 'task_completed') {
    // Update UI with new task status
    updateTaskStatus(update.task);
  }
};
```

## 🎨 Frontend Integration Patterns

### Component Architecture

```
EmailWorkflowDashboard
├── Header (stats, connection status)
├── Emails Section
│   ├── Email List
│   ├── Email Detail Modal
│   └── Real-time Updates
└── Tasks Section
    ├── Task Filters
    ├── Task List
    └── Task Actions
```

### State Management

```javascript
const [emails, setEmails] = useState([]);
const [tasks, setTasks] = useState([]);
const [stats, setStats] = useState({});
const [loading, setLoading] = useState(false);
const [wsConnection, setWsConnection] = useState(null);
```

### API Integration Hook

```javascript
function useWorkflowAPI() {
  const apiRequest = useCallback(async (endpoint, options = {}) => {
    const response = await fetch(`/api/v1/${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }, []);

  return { apiRequest };
}
```

## 📊 Monitoring & Analytics

### Workflow Metrics

```javascript
// Get workflow statistics
const stats = await apiRequest('workflow/stats');
console.log(`Processed ${stats.emailsProcessed} emails`);
console.log(`Created ${stats.tasksCreated} tasks`);
```

### Task Analytics

```javascript
// Get task completion rates
const tasks = await apiRequest('workflow/tasks');
const completed = tasks.filter(t => t.status === 'completed').length;
const completionRate = (completed / tasks.length) * 100;
```

### Performance Monitoring

```javascript
// Monitor processing times
const task = await apiRequest(`tasks/${taskId}/status`);
console.log(`Processing time: ${task.processing_time_seconds}s`);
```

## 🔒 Security Considerations

### Credential Management

```javascript
// Secure credential handling
const credentials = {
  username: process.env.EMAIL_USERNAME,
  password: process.env.EMAIL_PASSWORD
};

// Never log credentials
console.log('Processing emails for user:', credentials.username);
```

### Input Validation

```javascript
// Validate email credentials
function validateCredentials(creds) {
  if (!creds.username || !creds.username.includes('@')) {
    throw new Error('Invalid email username');
  }
  if (!creds.password || creds.password.length < 8) {
    throw new Error('Invalid password');
  }
  return true;
}
```

### Rate Limiting

```javascript
// Implement client-side rate limiting
class RateLimiter {
  constructor(requestsPerMinute = 60) {
    this.requests = [];
    this.limit = requestsPerMinute;
  }

  canMakeRequest() {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove old requests
    this.requests = this.requests.filter(time => time > oneMinuteAgo);

    return this.requests.length < this.limit;
  }

  recordRequest() {
    this.requests.push(Date.now());
  }
}
```

## 🚀 Deployment & Scaling

### Environment Configuration

```bash
# .env file
API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
EMAIL_SERVER=imap.gmail.com
EMAIL_PORT=993
OLLAMA_BASE_URL=http://localhost:11434
```

### Docker Configuration

```yaml
# docker-compose.yml
services:
  agentic-backend:
    image: agentic-backend:latest
    environment:
      - API_KEY=your-secure-api-key
      - OLLAMA_BASE_URL=http://ollama:11434
    ports:
      - "8000:8000"

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
```

### Production Considerations

1. **SSL/TLS**: Always use HTTPS in production
2. **API Keys**: Rotate API keys regularly
3. **Rate Limiting**: Implement appropriate rate limits
4. **Monitoring**: Set up comprehensive monitoring
5. **Backups**: Regular database backups
6. **Scaling**: Consider load balancing for high traffic

## 🐛 Troubleshooting

### Common Issues

#### 502 Bad Gateway
```bash
# Check nginx status
docker logs agentic-backend-nginx-1

# Check API health
curl http://localhost:8000/api/v1/health
```

#### Task Failures
```bash
# Check task logs
curl http://localhost:8000/api/v1/logs/task-id

# Check agent status
curl http://localhost:8000/api/v1/agents/agent-id
```

#### Email Connection Issues
```bash
# Test email connectivity
python -c "
import imaplib
server = imaplib.IMAP4_SSL('imap.gmail.com')
server.login('user@gmail.com', 'password')
print('Connection successful')
"
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with verbose output
python email_workflow_api_example.py --verbose
```

## 📚 Additional Resources

- [Main Documentation](../WORKFLOW_DEVELOPMENT_GUIDE.md)
- [API Documentation](../API_DOCUMENTATION.md)
- [Security Guide](../API_DOCUMENTATION.md#security-features-overview)
- [System Monitoring](../API_DOCUMENTATION.md#monitoring-and-metrics)

---

This example provides a complete foundation for building custom agent workflows. Adapt the patterns and configurations to create workflows for your specific use cases!