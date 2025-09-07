# 🔧 Troubleshooting Guide

Common issues and solutions for the Agentic Backend system.

## 🚨 Common Startup Issues

### 1. Docker Compose Fails to Start

**Symptoms:**
- Containers exit immediately
- Port conflicts
- Permission denied errors

**Solutions:**

**Port Conflicts:**
```bash
# Check what's using ports
lsof -i :8000    # API port
lsof -i :5432    # PostgreSQL port
lsof -i :6379    # Redis port
lsof -i :5555    # Flower port

# Kill conflicting processes or change ports in docker-compose.yml
```

**Permission Issues:**
```bash
# Fix log directory permissions
mkdir -p logs
chmod 755 logs
sudo chown -R $USER:$USER logs

# Restart Docker if needed
sudo systemctl restart docker
```

**Docker daemon issues:**
```bash
# Start Docker daemon
sudo systemctl start docker

# Add user to docker group (then logout/login)
sudo usermod -aG docker $USER
```

### 2. Database Connection Failed

**Symptoms:**
- `connection refused` errors
- Database initialization fails
- API returns 500 errors

**Diagnosis:**
```bash
# Check database container status
docker-compose ps db

# Check database logs
docker-compose logs db

# Test database connectivity
docker-compose exec db psql -U postgres -d ai_db -c "SELECT 1;"
```

**Solutions:**

**Database not ready:**
```bash
# Wait for database to be fully ready (can take 30-60 seconds)
docker-compose logs -f db

# Look for: "database system is ready to accept connections"
```

**Connection string issues:**
```bash
# Verify .env file has correct DATABASE_URL
cat .env | grep DATABASE_URL

# Should be: postgresql+asyncpg://postgres:secret@db:5432/ai_db
```

**Container networking:**
```bash
# Restart all containers
docker-compose down
docker-compose up -d

# Check network connectivity
docker-compose exec api ping db
```

### 3. Ollama Connection Issues

**Symptoms:**
- Tasks fail with connection errors
- "Unable to connect to Ollama" messages
- HTTP timeout errors

**Diagnosis:**
```bash
# Test Ollama connectivity from host
curl http://whyland-ai.nakedsun.xyz:11434/api/tags

# Test from container
docker-compose exec api curl http://whyland-ai.nakedsun.xyz:11434/api/tags

# Check if model exists
curl http://whyland-ai.nakedsun.xyz:11434/api/tags | jq '.models[].name'
```

**Solutions:**

**Update Ollama URL:**
```bash
# Edit .env file
OLLAMA_BASE_URL=http://your-correct-ollama-host:11434

# Restart services
docker-compose restart api worker
```

**Model not available:**
```bash
# List available models
curl http://whyland-ai.nakedsun.xyz:11434/api/tags

# Pull required model (if you have access to Ollama server)
curl -X POST http://whyland-ai.nakedsun.xyz:11434/api/pull \
  -d '{"name": "qwen3:30b-a3b-thinking-2507-q8_0"}'

# Or change to available model in .env
OLLAMA_DEFAULT_MODEL=llama2
```

**Firewall/Network issues:**
```bash
# Check if port is accessible
telnet whyland-ai.nakedsun.xyz 11434

# Add to hosts file if DNS issues
echo "IP_ADDRESS whyland-ai.nakedsun.xyz" >> /etc/hosts
```

### 4. Redis Connection Problems

**Symptoms:**
- Celery workers can't connect
- Real-time logging not working
- Task queue failures

**Diagnosis:**
```bash
# Check Redis container
docker-compose ps redis
docker-compose logs redis

# Test Redis connectivity
docker-compose exec redis redis-cli ping
# Should return: PONG
```

**Solutions:**
```bash
# Restart Redis
docker-compose restart redis

# Clear Redis data if corrupted
docker-compose exec redis redis-cli FLUSHALL

# Check Redis configuration
docker-compose exec redis redis-cli INFO
```

## ⚡ Runtime Issues

### 5. Celery Worker Problems

**Symptoms:**
- Tasks stuck in "pending" status
- Workers not processing tasks
- High memory usage

**Diagnosis:**
```bash
# Check worker status
docker-compose logs worker

# Monitor with Flower
# Go to: http://localhost:5555

# Check worker processes
docker-compose exec worker ps aux
```

**Solutions:**

**Worker not starting:**
```bash
# Restart worker
docker-compose restart worker

# Scale workers
docker-compose up -d --scale worker=3

# Check for Python errors
docker-compose logs worker | grep ERROR
```

**Memory issues:**
```bash
# Add memory limits to docker-compose.yml
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

**Task timeouts:**
```bash
# Increase timeout in .env
CELERY_TASK_TIMEOUT=600  # 10 minutes

# Restart worker
docker-compose restart worker
```

### 6. API Response Issues

**Symptoms:**
- 500 Internal Server Error
- Slow response times
- Connection timeouts

**Diagnosis:**
```bash
# Check API logs
docker-compose logs api

# Test API health
curl http://localhost:8000/api/v1/health

# Monitor API performance
curl -w "%{time_total}\n" http://localhost:8000/api/v1/health
```

**Solutions:**

**Database connection pool:**
```bash
# Add to .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Restart API
docker-compose restart api
```

**Memory issues:**
```bash
# Check container memory usage
docker stats

# Add memory limits if needed
# Edit docker-compose.yml
```

### 7. WebSocket Connection Issues

**Symptoms:**
- WebSocket connection failed
- No real-time logs
- Connection drops

**Diagnosis:**
```bash
# Test WebSocket from command line
pip install websockets
python3 -c "
import asyncio
import websockets

async def test():
    uri = 'ws://localhost:8000/ws/logs'
    async with websockets.connect(uri) as websocket:
        print('Connected!')
        await websocket.send('ping')
        response = await websocket.recv()
        print(f'Received: {response}')

asyncio.run(test())
"
```

**Solutions:**

**Proxy configuration:**
```nginx
# If using nginx proxy
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

**Firewall rules:**
```bash
# Ensure WebSocket ports are open
sudo ufw allow 8000
```

## 🐛 Debugging Tools

### Log Analysis

**View all logs:**
```bash
# All services
docker-compose logs -f

# Specific service with timestamps
docker-compose logs -f -t api
docker-compose logs -f -t worker
docker-compose logs -f -t db
docker-compose logs -f -t redis
```

**Filter logs:**
```bash
# Error logs only
docker-compose logs api | grep ERROR

# Last 100 lines
docker-compose logs --tail=100 api

# Follow logs from specific time
docker-compose logs --since="2024-01-01T12:00:00" api
```

### Container Inspection

**Container status:**
```bash
# List containers
docker-compose ps

# Detailed container info
docker inspect agentic-backend_api_1

# Resource usage
docker stats
```

**Shell access:**
```bash
# Access API container
docker-compose exec api bash

# Access worker container  
docker-compose exec worker bash

# Access database
docker-compose exec db psql -U postgres -d ai_db
```

### Database Debugging

**Check database status:**
```bash
# Connect to database
docker-compose exec db psql -U postgres -d ai_db

# List tables
\dt

# Check agent table
SELECT * FROM agents LIMIT 5;

# Check task status
SELECT id, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 10;

# Check logs
SELECT level, message, timestamp FROM task_logs ORDER BY timestamp DESC LIMIT 10;
```

**Database performance:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Redis Debugging

**Redis inspection:**
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check key patterns
KEYS *

# Check stream info
XINFO STREAM agent_logs

# Monitor commands
MONITOR

# Check memory usage
INFO memory
```

## 🔍 Performance Issues

### High CPU Usage

**Diagnosis:**
```bash
# Check process usage
docker-compose exec api top
docker-compose exec worker top

# System resources
htop
```

**Solutions:**
- Reduce `CELERY_WORKER_CONCURRENCY`
- Add more worker containers
- Optimize Ollama model size
- Add CPU limits to containers

### High Memory Usage

**Diagnosis:**
```bash
# Memory usage by container
docker stats

# Memory info inside container
docker-compose exec api free -h
```

**Solutions:**
- Add memory limits
- Reduce batch sizes
- Clear Redis periodically
- Use smaller models

### Slow Database Queries

**Solutions:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_task_logs_timestamp ON task_logs(timestamp);
CREATE INDEX idx_task_logs_task_id ON task_logs(task_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'pending';
```

## 🚀 Recovery Procedures

### Complete System Reset

**When everything is broken:**
```bash
# Stop and remove everything
docker-compose down -v

# Remove all images (optional)
docker-compose down --rmi all

# Clean rebuild
docker-compose build --no-cache
docker-compose up -d

# Reinitialize database
docker-compose exec api python scripts/init_db.py
```

### Data Recovery

**Database backup:**
```bash
# Create backup
docker-compose exec db pg_dump -U postgres ai_db > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres ai_db < backup.sql
```

**Redis backup:**
```bash
# Save Redis data
docker-compose exec redis redis-cli SAVE

# Copy backup file
docker cp container_name:/data/dump.rdb ./redis_backup.rdb
```

## 📞 Getting Help

### Health Check Commands

**Quick system check:**
```bash
#!/bin/bash
echo "=== System Health Check ==="
echo "Docker containers:"
docker-compose ps

echo -e "\nAPI Health:"
curl -s http://localhost:8000/api/v1/health | jq .

echo -e "\nDatabase connectivity:"
docker-compose exec db psql -U postgres -d ai_db -c "SELECT 1;" > /dev/null && echo "✅ OK" || echo "❌ FAILED"

echo -e "\nRedis connectivity:"
docker-compose exec redis redis-cli ping

echo -e "\nOllama connectivity:"
curl -s http://whyland-ai.nakedsun.xyz:11434/api/tags > /dev/null && echo "✅ OK" || echo "❌ FAILED"
```

### Log Collection

**Collect all logs for support:**
```bash
# Create log bundle
mkdir -p debug_logs
docker-compose logs > debug_logs/all_services.log
docker-compose logs api > debug_logs/api.log
docker-compose logs worker > debug_logs/worker.log
docker-compose logs db > debug_logs/database.log
docker-compose logs redis > debug_logs/redis.log

# System info
docker version > debug_logs/docker_info.txt
docker-compose version >> debug_logs/docker_info.txt
uname -a >> debug_logs/system_info.txt
free -h >> debug_logs/system_info.txt

# Create archive
tar -czf debug_logs_$(date +%Y%m%d_%H%M%S).tar.gz debug_logs/
```

### Configuration Check

**Validate configuration:**
```bash
# Check environment file
echo "=== Environment Variables ==="
cat .env | grep -v "SECRET\|PASSWORD\|KEY"

# Check Docker Compose validity  
docker-compose config

# Check file permissions
ls -la logs/
ls -la .env
```

## 🎯 Prevention

### Monitoring Setup

**Basic monitoring script:**
```bash
#!/bin/bash
# Add to crontab: */5 * * * * /path/to/monitor.sh

# Check if services are running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "$(date): API is down - restarting" >> monitor.log
    docker-compose restart api
fi

# Check disk space
if [ $(df / | tail -1 | awk '{print $5}' | sed 's/%//') -gt 90 ]; then
    echo "$(date): Disk space critical - cleaning logs" >> monitor.log
    docker system prune -f
fi
```

### Backup Strategy

**Automated backups:**
```bash
#!/bin/bash
# Daily backup script
DATE=$(date +%Y%m%d)
docker-compose exec db pg_dump -U postgres ai_db | gzip > "backup_${DATE}.sql.gz"
find . -name "backup_*.sql.gz" -mtime +7 -delete
```

Remember: Most issues can be resolved by checking logs and restarting services! 🔄