# Agentic Backend

A robust, modern backend system for local AI agents with real-time logging, pub/sub capabilities, and Ollama integration.

## Features

- **FastAPI** - Modern, async web framework with automatic OpenAPI documentation
- **Celery** - Distributed task queue for scalable background processing
- **PostgreSQL + pgvector** - Robust database with vector search capabilities
- **Redis Streams** - Real-time log streaming and pub/sub messaging
- **WebSocket + SSE** - Real-time communication with frontends
- **Ollama Integration** - Local LLM inference without external dependencies
- **Docker Compose** - Easy deployment and development setup
- **Structured Logging** - Comprehensive logging with real-time streaming
- **Prometheus Metrics** - Built-in monitoring and observability
- **Type Safety** - Full type hints with Pydantic validation

## Architecture

```
[Client] --> [FastAPI API] --> [Celery Task Queue (Redis)]
                |                      |
                |                      v
                |              [Celery Workers] <--> [Ollama LLM]
                |                      |
                v                      v
    [WebSocket/SSE] <-- [Redis Streams] --> [PostgreSQL DB]
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Ollama running at `http://whyland-ai.nakedsun.xyz:11434`

### Development Setup

1. **Clone and setup**:
```bash
git clone <repository>
cd Agentic-Backend
cp .env.example .env
# Edit .env with your configuration
```

2. **Start services**:
```bash
# Development mode with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production mode
docker-compose up -d
```

3. **Initialize database**:
```bash
docker-compose exec api python scripts/init_db.py
```

4. **Access services**:
- API Documentation: http://localhost:8000/docs
- Flower (Celery monitoring): http://localhost:5555
- Adminer (Database browser): http://localhost:8080

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

2. **Setup environment**:
```bash
export DATABASE_URL="postgresql+asyncpg://postgres:secret@localhost:5432/ai_db"
export REDIS_URL="redis://localhost:6379/0"
# ... other environment variables
```

3. **Run services**:
```bash
# Start database and redis
docker-compose up -d db redis

# Initialize database
python scripts/init_db.py

# Run API
uvicorn app.main:app --reload

# Run worker (in separate terminal)
python scripts/run_worker.py

# Or use Celery directly
celery -A app.celery_app worker --loglevel=info
```

## API Usage

### Create an Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agents/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Text Summarizer",
    "description": "Agent for text summarization tasks",
    "model_name": "llama2",
    "config": {
      "temperature": 0.3,
      "max_tokens": 500
    }
  }'
```

### Run a Task

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/run" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "your-agent-id-here",
    "input": {
      "type": "summarize",
      "text": "Your long text to summarize here...",
      "length": "medium"
    }
  }'
```

### Real-time Logs via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs?agent_id=your-agent-id');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Log:', data);
};

// Subscribe to specific task
const taskWs = new WebSocket('ws://localhost:8000/ws/tasks/your-task-id');
```

### Server-Sent Events

```javascript
const eventSource = new EventSource('http://localhost:8000/api/v1/logs/stream/your-task-id');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Log event:', data);
};
```

## Task Types

The system supports various task types:

### 1. Text Generation
```json
{
  "type": "generate",
  "prompt": "Write a story about...",
  "system": "You are a creative writer."
}
```

### 2. Chat Completion
```json
{
  "type": "chat",
  "messages": [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "How are you?"}
  ]
}
```

### 3. Text Summarization
```json
{
  "type": "summarize",
  "text": "Long text to summarize...",
  "length": "short|medium|long"
}
```

### 4. Text Analysis
```json
{
  "type": "analyze",
  "text": "Text to analyze...",
  "analysis_type": "sentiment|topics|entities|general"
}
```

## Real-time Logging

The system provides comprehensive real-time logging through multiple channels:

- **Database Storage**: All logs are persisted in PostgreSQL
- **Redis Streams**: Real-time log streaming for live updates
- **WebSocket**: Direct browser connections for live log feeds
- **Server-Sent Events**: HTTP-based streaming for web applications

### Log Structure

```json
{
  "id": "log-uuid",
  "task_id": "task-uuid",
  "agent_id": "agent-uuid", 
  "level": "info|debug|warning|error|critical",
  "message": "Log message",
  "context": {"key": "value"},
  "timestamp": "2024-01-01T12:00:00Z",
  "stream_id": "redis-stream-id"
}
```

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Redis
REDIS_URL=redis://host:port/db
CELERY_BROKER_URL=redis://host:port/db

# Ollama
OLLAMA_BASE_URL=http://host:port
OLLAMA_DEFAULT_MODEL=llama2

# Security
SECRET_KEY=your-secret-key
API_KEY=your-api-key  # Optional

# Logging
LOG_LEVEL=INFO
LOG_STREAM_NAME=agent_logs
```

## Monitoring

- **Health Checks**: `/api/v1/health`, `/api/v1/ready`
- **Metrics**: `/api/v1/metrics` (Prometheus format)
- **Flower UI**: http://localhost:5555 (Celery monitoring)
- **Database UI**: http://localhost:8080 (Adminer)

## Development

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/

# Run tests
pytest tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Scaling

Scale workers:
```bash
docker-compose up --scale worker=5
```

## Future Enhancements

- Multi-agent workflows with LangGraph
- RAG capabilities with vector search
- Additional agent tools (web search, file ops, etc.)
- Kubernetes deployment manifests
- Advanced monitoring with Grafana dashboards
- Authentication and authorization system

## License

MIT License - see LICENSE file for details.