# 🚀 Agentic Backend - Complete Startup Guide

This guide will walk you through starting up the Agentic Backend system step by step.

## 📋 Prerequisites

Before starting, ensure you have:

- **Docker** and **Docker Compose** installed
- **Git** for cloning the repository
- **Ollama** running and accessible (our example uses `http://whyland-ai.nakedsun.xyz:11434`)
- **Python dependencies**: `psutil` and `pynvml` (automatically installed via requirements.txt)
- At least **4GB RAM** available for containers
- **Ports available**: 8000 (API), 5432 (PostgreSQL), 6379 (Redis), 5555 (Flower), 8080 (Adminer)
- **NVIDIA GPU** (optional): For GPU monitoring with Tesla P40 support

## 🔧 Quick Start (Recommended)

### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd Agentic-Backend

# Copy environment template
cp .env.example .env

# Edit environment variables (see detailed configuration below)
nano .env  # or use your preferred editor
```

### Step 2: Configure Environment Variables

Edit your `.env` file with the following **minimum required** changes:

```bash
# 🔐 SECURITY - Change these immediately!
SECRET_KEY=your-super-secret-key-here-min-32-characters
API_KEY=your-api-key-for-authentication  # Optional but recommended

# 🤖 OLLAMA - Update if your Ollama is running elsewhere
OLLAMA_BASE_URL=http://your-ollama-host:11434
OLLAMA_DEFAULT_MODEL=llama2  # or your preferred model
```

### Step 3: Start the System

```bash
# Start all services (this will take a few minutes on first run)
docker-compose up -d

# Watch the logs to see startup progress
docker-compose logs -f
```

### Step 4: Initialize Database

```bash
# Wait for database to be ready, then initialize
docker-compose exec api python scripts/init_db.py
```

### Step 5: Verify Everything is Running

Check service health:
```bash
# Check all containers are running
docker-compose ps

# Test API health
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "app_name": "Agentic Backend",
  "version": "0.1.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🌐 Access Points

Once started, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| **🔗 API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| **📖 ReDoc Documentation** | http://localhost:8000/redoc | Alternative API docs |
| **🌸 Flower (Celery Monitor)** | http://localhost:5555 | Monitor background tasks |
| **🗄️ Adminer (Database UI)** | http://localhost:8080 | Database browser |
| **📊 Prometheus Metrics** | http://localhost:8000/api/v1/metrics | Application metrics |
| **🖥️ System Metrics** | http://localhost:8000/api/v1/system/metrics | CPU, Memory, GPU, Disk, Network |

### Database Connection via Adminer
- **Server**: `db`
- **Username**: `postgres`
- **Password**: `secret`
- **Database**: `ai_db`

## 🧪 Test the API

### Method 1: Swagger UI (Recommended)
1. Go to http://localhost:8000/docs
2. Click "Authorize" and enter your API key (if set)
3. Try the endpoints interactively

### Method 2: cURL Examples

**Create an Agent:**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/create" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "name": "Test Summarizer",
    "description": "Agent for testing text summarization",
    "model_name": "llama2",
    "config": {
      "temperature": 0.7,
      "max_tokens": 500,
      "system_prompt": "You are a helpful summarization assistant."
    }
  }'
```

**Run a Task:**
```bash
# Use the agent_id returned from the previous request
curl -X POST "http://localhost:8000/api/v1/tasks/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "agent_id": "YOUR_AGENT_ID_HERE",
    "input": {
      "type": "summarize",
      "text": "This is a long text that needs to be summarized. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
      "length": "short"
    }
  }'
```

**Check Task Status:**
```bash
curl "http://localhost:8000/api/v1/tasks/YOUR_TASK_ID_HERE/status"
```

**Monitor System Metrics:**
```bash
# Get all system metrics (CPU, Memory, GPU, Disk, Network)
curl "http://localhost:8000/api/v1/system/metrics"

# Get specific metrics
curl "http://localhost:8000/api/v1/system/metrics/cpu"
curl "http://localhost:8000/api/v1/system/metrics/memory"
curl "http://localhost:8000/api/v1/system/metrics/gpu"
curl "http://localhost:8000/api/v1/system/metrics/disk"
curl "http://localhost:8000/api/v1/system/metrics/network"
```

### Method 3: WebSocket Testing

Use a WebSocket client to connect to:
```
ws://localhost:8000/ws/logs?agent_id=YOUR_AGENT_ID
```

Example JavaScript:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs');
ws.onmessage = function(event) {
  console.log('Real-time log:', JSON.parse(event.data));
};
```

## 🔧 Development Mode

For active development with hot reload:

```bash
# Start in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# This enables:
# - Code hot reload
# - Debug logging
# - Development database browser (Adminer)
# - Volume mounting for live code changes
```

## 🐛 Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Find what's using the port
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

**2. Database Connection Failed**
```bash
# Check if database is ready
docker-compose logs db

# Restart database
docker-compose restart db

# Wait a few seconds, then retry
```

**3. Ollama Connection Failed**
```bash
# Test Ollama connectivity
curl http://whyland-ai.nakedsun.xyz:11434/api/tags

# Update OLLAMA_BASE_URL in .env if needed
# Restart services: docker-compose restart
```

**4. Celery Worker Issues**
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Scale workers if needed
docker-compose up -d --scale worker=2
```

**5. Permission Issues**
```bash
# Fix log directory permissions
mkdir -p logs
chmod 755 logs

# Restart containers
docker-compose restart
```

### Health Checks

**System Health:**
```bash
curl http://localhost:8000/api/v1/health
```

**Detailed Health:**
```bash
curl http://localhost:8000/api/v1/ready
```

**System Metrics Health:**
```bash
# Test system metrics collection
curl http://localhost:8000/api/v1/system/metrics/cpu
curl http://localhost:8000/api/v1/system/metrics/gpu

# Should return JSON with system utilization data
```

**Service Status:**
```bash
# Check all containers
docker-compose ps

# Expected output: All services should be "Up"
```

### Logs and Monitoring

**View Real-time Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f db
```

**Monitor Tasks:**
- Go to http://localhost:5555 (Flower)
- Monitor active/completed tasks
- View task details and logs

## 🛠️ Advanced Configuration

### Custom Model Configuration

Add custom models in your agent config:
```json
{
  "name": "Custom Agent",
  "model_name": "codellama",
  "config": {
    "temperature": 0.1,
    "max_tokens": 2000,
    "options": {
      "top_p": 0.9,
      "repeat_penalty": 1.1
    }
  }
}
```

### Scaling Workers

```bash
# Scale workers horizontally
docker-compose up -d --scale worker=5

# Or edit docker-compose.yml and add:
# deploy:
#   replicas: 5
```

### System Monitoring

The Agentic Backend provides comprehensive system monitoring capabilities:

**Available Metrics:**
- **CPU**: Usage percentage, frequency, core counts, time breakdowns
- **Memory**: Total/used/free in GB, usage percentage, buffers/cached
- **GPU**: Utilization, memory usage, temperature (°F), clock frequencies, power (NVIDIA GPUs)
- **Disk**: Usage statistics and I/O metrics
- **Network**: Traffic statistics and interface information

**Monitoring Endpoints:**
```bash
# All system metrics
curl http://localhost:8000/api/v1/system/metrics

# Individual metrics
curl http://localhost:8000/api/v1/system/metrics/cpu
curl http://localhost:8000/api/v1/system/metrics/memory
curl http://localhost:8000/api/v1/system/metrics/gpu
```

**Integration with Frontend:**
The system metrics endpoints are designed for easy frontend integration, providing real-time system monitoring data in JSON format perfect for dashboards and monitoring displays.

### Production Considerations

1. **Security**: Change all default passwords and keys
2. **SSL/TLS**: Add reverse proxy (nginx) with SSL
3. **Monitoring**: Set up Grafana + Prometheus with system metrics
4. **Backup**: Configure PostgreSQL backups
5. **Resource Limits**: Set Docker memory/CPU limits

## 📚 Next Steps

1. **Read the API Documentation**: http://localhost:8000/docs
2. **Create your first agent** using the Swagger UI
3. **Monitor system performance** with `/api/v1/system/metrics`
4. **Test real-time logging** via WebSocket
5. **Monitor tasks** using Flower
6. **Explore the database** using Adminer

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs -f`
2. **Verify environment**: Ensure `.env` is configured correctly
3. **Test connectivity**: Verify Ollama is accessible
4. **Review health endpoints**: Check `/health` and `/ready`
5. **Restart services**: `docker-compose restart`

The system should now be fully operational! 🎉