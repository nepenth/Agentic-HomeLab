# Email Workflow Getting Started Guide

This guide focuses specifically on configuring and running the Email Workflow System, assuming the Agentic Backend infrastructure is already set up and running.

## 📧 Email Workflow Prerequisites

### Required Backend Services
- ✅ PostgreSQL database with pgvector extension
- ✅ Redis for caching and task queuing
- ✅ Ollama server with AI models
- ✅ Agentic Backend API running

### Required AI Models
```bash
# Ensure these models are available in Ollama
ollama pull qwen3:30b-a3b-thinking-2507-q8_0  # Primary model for email analysis
ollama pull llama2:13b                        # Alternative for categorization
ollama pull aembeddinggemma                   # For embeddings and semantic search
```

## 🔧 Environment Variables for Email Workflow

### Core Email Processing Variables

```bash
# Email Analysis Configuration
EMAIL_ANALYSIS_MODEL=qwen3:30b-a3b-thinking-2507-q8_0
EMAIL_IMPORTANCE_THRESHOLD=0.7
EMAIL_SPAM_THRESHOLD=0.8
EMAIL_MAX_BATCH_SIZE=50

# IMAP Configuration (for Gmail/Outlook/etc.)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_CONNECTION_TIMEOUT=30

# Email Processing Limits
MAX_EMAILS_PER_WORKFLOW=100
EMAIL_PROCESSING_TIMEOUT=300
EMAIL_ATTACHMENT_MAX_SIZE=10485760  # 10MB

# Task Creation Settings
AUTO_CREATE_TASKS=true
TASK_PRIORITY_MAPPING='{"high": 0.8, "medium": 0.6, "low": 0.4}'
TASK_DUE_DATE_DEFAULT_HOURS=24

# Follow-up Configuration
AUTO_SCHEDULE_FOLLOWUPS=true
FOLLOWUP_REMINDER_HOURS=24
FOLLOWUP_ESCALATION_HOURS=72
```

### Semantic Search & AI Configuration

```bash
# Vector Search Settings
VECTOR_DIMENSION=384
SEMANTIC_SEARCH_MODEL=all-minilm
SEARCH_SIMILARITY_THRESHOLD=0.7
SEARCH_MAX_RESULTS=50

# Chat & Conversation Settings
CHAT_MODEL=qwen3:30b-a3b-thinking-2507-q8_0
CHAT_MAX_TOKENS=1000
CHAT_TEMPERATURE=0.3
CHAT_SESSION_TIMEOUT_HOURS=24

# Thread Detection
THREAD_DETECTION_ENABLED=true
THREAD_TIME_WINDOW_HOURS=168  # 7 days
THREAD_SIMILARITY_THRESHOLD=0.8
```

### Performance & Caching

```bash
# Redis Caching
EMAIL_CACHE_TTL=3600  # 1 hour
ANALYSIS_CACHE_TTL=1800  # 30 minutes
SEARCH_CACHE_TTL=900  # 15 minutes

# Performance Limits
MAX_CONCURRENT_WORKFLOWS=5
WORKFLOW_QUEUE_SIZE=100
BATCH_PROCESSING_SIZE=25
```

### Security & Monitoring

```bash
# Email Security
EMAIL_SANITIZE_CONTENT=true
ATTACHMENT_VIRUS_SCAN=true
SENDER_REPUTATION_CHECK=true

# Audit & Logging
EMAIL_AUDIT_LOGGING=true
WORKFLOW_METRICS_ENABLED=true
PERFORMANCE_MONITORING=true
```

## 🚀 Running the Email Workflow

### 1. Verify Backend Services

```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify Ollama models
curl http://localhost:8000/api/v1/ollama/models

# Check database connectivity
curl http://localhost:8000/api/v1/health
```

### 2. Configure Email Credentials

```bash
# For Gmail: Use App Passwords
# 1. Enable 2FA on your Google account
# 2. Generate App Password: https://myaccount.google.com/apppasswords
# 3. Use the 16-character password (not your regular password)

# For Outlook/Exchange
# Use your regular password or create an App Password
```

### 3. Start Email Processing Workflow

```bash
curl -X POST http://localhost:8000/api/v1/email/workflows/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "mailbox_config": {
      "server": "imap.gmail.com",
      "port": 993,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "use_ssl": true
    },
    "processing_options": {
      "max_emails": 50,
      "unread_only": true,
      "since_date": "2024-01-01T00:00:00Z",
      "importance_threshold": 0.7,
      "create_tasks": true,
      "schedule_followups": true
    },
    "user_id": "your-user-id"
  }'
```

### 4. Monitor Workflow Progress

```bash
# Get workflow status
curl http://localhost:8000/api/v1/email/workflows/WORKFLOW_ID/status

# Real-time monitoring via WebSocket
# Connect to: ws://localhost:8000/ws/email/progress
```

### 5. Test Email Search

```bash
curl -X POST http://localhost:8000/api/v1/email/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "query": "urgent project deadlines",
    "search_type": "semantic",
    "limit": 20,
    "include_threads": true
  }'
```

### 6. Test Conversational AI

```bash
curl -X POST http://localhost:8000/api/v1/email/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "Show me urgent emails from this week",
    "session_id": "optional-session-id"
  }'
```

## 📊 Email Workflow Features

### Core Processing Pipeline

1. **Email Discovery**: Connect to IMAP server and fetch emails
2. **Content Analysis**: AI-powered importance scoring and categorization
3. **Task Creation**: Automatic task generation from important emails
4. **Follow-up Scheduling**: Smart reminder and escalation system
5. **Thread Detection**: Conversation grouping and relationship mapping
6. **Semantic Indexing**: Vector embeddings for advanced search

### Available Endpoints

| Feature | Endpoint | Description |
|---------|----------|-------------|
| **Workflow Management** | `/api/v1/email/workflows/*` | Start, monitor, cancel workflows |
| **Task Management** | `/api/v1/email/tasks/*` | View, complete, follow-up on tasks |
| **Semantic Search** | `/api/v1/email/search` | AI-powered email search |
| **Conversational AI** | `/api/v1/email/chat` | Natural language email interaction |
| **Analytics** | `/api/v1/email/analytics/*` | Usage statistics and insights |
| **Configuration** | `/api/v1/email/settings/*` | Customize processing rules |

### Real-time Features

- **WebSocket Progress**: `ws://localhost:8000/ws/email/progress`
- **Live Task Updates**: Real-time task status changes
- **Workflow Monitoring**: Live processing statistics
- **Chat Sessions**: Interactive conversation support

## 🔍 Troubleshooting Email Workflow

### Common Issues

#### IMAP Connection Failed
```bash
# Check IMAP settings
curl -X POST http://localhost:8000/api/v1/email/workflows/start \
  -d '{"test_connection": true, "mailbox_config": {...}}'
```

#### AI Model Not Available
```bash
# Check available models
curl http://localhost:8000/api/v1/ollama/models

# Pull missing model
ollama pull qwen3:30b-a3b-thinking-2507-q8_0
```

#### Processing Timeout
```bash
# Check workflow status
curl http://localhost:8000/api/v1/email/workflows/WORKFLOW_ID/status

# Adjust timeout settings in environment
EMAIL_PROCESSING_TIMEOUT=600  # 10 minutes
```

#### Search Not Working
```bash
# Rebuild search index
curl -X POST http://localhost:8000/api/v1/email/search/rebuild-index

# Check vector database
curl http://localhost:8000/api/v1/email/search/stats
```

### Performance Optimization

```bash
# Adjust batch sizes
EMAIL_MAX_BATCH_SIZE=25
MAX_CONCURRENT_WORKFLOWS=3

# Enable caching
EMAIL_CACHE_TTL=3600
ANALYSIS_CACHE_TTL=1800

# Monitor performance
curl http://localhost:8000/api/v1/email/monitoring/performance
```

## 📈 Monitoring & Analytics

### Key Metrics to Monitor

```bash
# Workflow statistics
curl http://localhost:8000/api/v1/email/analytics/overview

# Processing performance
curl http://localhost:8000/api/v1/email/monitoring/performance

# System health
curl http://localhost:8000/api/v1/email/monitoring/system-health
```

### Dashboard Endpoints

- **Statistics**: `/api/v1/email/dashboard/stats`
- **Recent Activity**: `/api/v1/email/dashboard/recent-activity`
- **Task Overview**: `/api/v1/email/tasks/stats`
- **Search Analytics**: `/api/v1/email/analytics/search`

## 🎯 Next Steps

1. **Configure Email Credentials**: Set up IMAP access for your email provider
2. **Test Basic Workflow**: Run a small email processing job
3. **Customize Settings**: Adjust thresholds and rules for your needs
4. **Set up Monitoring**: Configure alerts and dashboards
5. **Frontend Integration**: Use the API documentation to build your interface

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Email Workflow APIs**: See `/api/v1/email/*` endpoints
- **Configuration Guide**: Check `.env.example.detailed` for all options
- **Examples**: Review `examples/email_workflow_api_example.py`

The Email Workflow System is now ready to process your emails with AI-powered analysis, task creation, and intelligent search capabilities!