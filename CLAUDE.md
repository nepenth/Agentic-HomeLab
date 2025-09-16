# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a full-stack AI/ML application with two main components:

### Agentic-Backend (FastAPI + Celery)
- **FastAPI** application with async database operations
- **Celery** distributed task queue with Redis broker
- **PostgreSQL + pgvector** for database with vector search
- **WebSocket/SSE** for real-time communication
- **Ollama** integration for local LLM inference
- **Docker Compose** for containerized deployment

### Agentic-Frontend (React + TypeScript)
- **React 18** with TypeScript and Vite
- **Material-UI (MUI)** with Apple-inspired design system
- **Redux Toolkit + React Query** for state management
- **Docker** containerization with Nginx

## Key Development Commands

### Backend Development
```bash
# Local development setup
cd Agentic-Backend
pip install -r requirements.txt

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
python scripts/run_worker.py
# or
celery -A app.celery_app worker --loglevel=info --concurrency=4 -Q agent_tasks

# Code quality checks
black app/ tests/
isort app/ tests/
mypy app/
pytest tests/

# Docker deployment
docker compose up -d
```

### Frontend Development
```bash
# Local development
cd Agentic-Frontend/frontend
npm install
npm run dev

# Testing
npm run test
npm run test:watch
npm run test:coverage

# Building
npm run build
npm run preview

# Code quality
npm run lint

# Docker deployment
docker compose up -d --build
```

## Core Architecture Patterns

### Backend Service Layer
The backend follows a layered architecture:
- **API Routes** (`app/api/routes/`) - HTTP endpoints organized by domain
- **Services** (`app/services/`) - Business logic layer with specialized services
- **Models** (`app/db/models/`) - SQLAlchemy database models
- **Tasks** (`app/tasks/`) - Celery async task definitions
- **Agents** (`app/agents/`) - AI agent implementations with tools

### Key Backend Services
- **AgenticHttpClient** (`app/services/agentic_http_client.py`) - HTTP client with retry/circuit breaker
- **EmailAnalysisService** (`app/services/email_analysis_service.py`) - Email processing workflows
- **ChatService** (`app/services/chat_service.py`) - Chat session management
- **SecurityService** (`app/services/security_service.py`) - Authentication and security
- **OllamaClient** (`app/services/ollama_client.py`) - LLM integration

### Frontend Module System
- **Pages** (`src/pages/`) - Main application screens
- **Components** (`src/components/`) - Reusable UI components
- **Modules** (`src/modules/`) - Workflow-specific functionality
- **Services** (`src/services/`) - API clients and business logic
- **Store** (`src/store/`) - Redux state management

## Database Schema

The application uses PostgreSQL with pgvector extension for:
- **Users and Authentication** - JWT-based auth system
- **Agent Management** - Dynamic agent creation and configuration
- **Chat Sessions** - Conversation history and resumable sessions
- **Email Workflows** - Email processing and task management
- **Content Processing** - Document analysis and knowledge base
- **Vector Storage** - Embeddings for semantic search

Migration files are in `Agentic-Backend/alembic/versions/` with descriptive naming.

## Configuration Management

### Backend Configuration
Environment variables defined in `app/config.py`:
- Database: `DATABASE_URL`, `REDIS_URL`
- External services: `OLLAMA_BASE_URL`
- Security: `SECRET_KEY`, `JWT_ALGORITHM`
- Feature toggles for various service components

### Frontend Configuration
Environment variables in frontend package:
- API endpoints: `VITE_API_BASE_URL`, `VITE_WS_URL`
- Application metadata: `VITE_APP_NAME`, `VITE_APP_VERSION`

## Real-time Communication

The system implements multiple real-time channels:
- **WebSocket** endpoints for live updates
- **Server-Sent Events (SSE)** for HTTP-based streaming
- **Redis Streams** for log aggregation and pub/sub
- **Celery** for background task processing

## Agent System

### Agent Architecture
- **BaseAgent** - Core agent interface and lifecycle
- **DynamicAgent** - Runtime-configurable agents
- **AgentFactory** - Agent creation and management
- **Tools** - Pluggable capabilities (database, email, LLM, security)

### Agent Tools
Located in `app/agents/tools/`:
- **DatabaseWriter** - Database operations
- **EmailConnector** - Email processing
- **LLMProcessor** - Language model integration
- **SecurityEnhancedBase** - Security-aware tool base

## Testing Strategy

### Backend Testing
- **pytest** with async support
- Test files in `tests/` directory
- Tests for agents, API routes, services, and database operations
- Use `pytest tests/` to run all tests

### Frontend Testing
- **Jest + React Testing Library**
- Component and integration tests
- Coverage reporting available

## Deployment Architecture

### Docker Services
The `docker compose.yml` defines:
- **api** - FastAPI application server
- **worker** - Celery background workers
- **db** - PostgreSQL with pgvector extension
- **redis** - Message broker and cache
- **flower** - Celery monitoring UI
- **nginx** - Reverse proxy with SSL termination

### Service Dependencies
- API and workers depend on healthy db + redis
- Nginx routes traffic to API and Flower
- External Ollama service for LLM inference

## Security Considerations

- JWT-based authentication with configurable expiration
- API key support for service-to-service communication  
- Security middleware for request validation
- Input validation using Pydantic schemas
- SQL injection protection via SQLAlchemy ORM
- CORS handling via nginx reverse proxy

## Development Workflow

When working on this codebase:

1. **Backend changes**: Always run migrations after model changes
2. **Frontend changes**: Ensure TypeScript compilation passes
3. **API changes**: Update both backend routes and frontend API client
4. **Database changes**: Create and test migrations thoroughly
5. **Agent development**: Follow the established tool pattern
6. **Configuration**: Add new settings to config.py with environment variable support

## External Dependencies

- **Ollama Server**: Expected at configured URL for LLM operations
- **PostgreSQL**: Requires pgvector extension for vector operations
- **Redis**: Used for Celery broker and caching
- **SSL Certificates**: Located in nginx/ssl/ directories