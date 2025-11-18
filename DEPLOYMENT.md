# 🚀 Production Deployment Guide

Complete guide for deploying the AI Library & Knowledge Engine to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Security](#security)
- [Monitoring](#monitoring)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- 4 CPU cores
- 8GB RAM
- 50GB disk space
- Ubuntu 20.04 LTS or newer

**Recommended:**
- 8+ CPU cores
- 16GB+ RAM
- 100GB+ SSD storage
- Ubuntu 22.04 LTS

### Software Dependencies

- Docker 24.0+
- Docker Compose 2.0+
- Git
- (Optional) Nginx for reverse proxy
- (Optional) Certbot for SSL certificates

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ai-library.git
cd ai-library
```

### 2. Configure Environment

```bash
# Copy production environment template
cp .env.production .env

# Edit configuration
nano .env
```

**Required variables:**
```bash
SECRET_KEY=<generate-random-key>
API_PORT=5000
ENABLE_AUTH=true
ALLOWED_API_KEYS=<comma-separated-keys>
```

### 3. Deploy with Docker

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f ai-library
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:5000/health

# Metrics
curl http://localhost:9090/metrics
```

---

## Configuration

### Environment Variables

#### Application Settings

```bash
# Environment
ENVIRONMENT=production
APP_NAME=ai-library
APP_VERSION=1.0.0
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here
ENABLE_AUTH=true
JWT_SECRET=your-jwt-secret
JWT_EXPIRY=3600

# API Keys (comma-separated)
ALLOWED_API_KEYS=key1,key2,key3
```

#### Database Configuration

```bash
# Paths
DATABASE_PATH=./data/books_metadata.db
VECTOR_DB_PATH=./data/books_index

# Backups
BACKUP_ENABLED=true
BACKUP_INTERVAL=86400  # 24 hours
MAX_BACKUPS=7
```

#### API Server

```bash
API_HOST=0.0.0.0
API_PORT=5000
API_WORKERS=4
API_TIMEOUT=300
CORS_ORIGINS=https://yourdomain.com
```

#### Rate Limiting

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

#### Caching

```bash
CACHE_ENABLED=true
CACHE_TYPE=redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### Generate Secret Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API keys
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## Docker Deployment

### Production Stack

The Docker Compose stack includes:
- **ai-library**: Main API server
- **redis**: Caching layer
- **prometheus**: Metrics collection
- **grafana**: Metrics visualization
- **nginx**: Reverse proxy (optional)

### Build Custom Image

```bash
# Build image
docker build -t ai-library:latest .

# Tag for registry
docker tag ai-library:latest your-registry.com/ai-library:latest

# Push to registry
docker push your-registry.com/ai-library:latest
```

### Deploy Services

```bash
# Start all services
docker-compose up -d

# Scale API servers
docker-compose up -d --scale ai-library=3

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down
```

### Update Deployment

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d

# Clean up old images
docker system prune -f
```

---

## Manual Deployment

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install system dependencies
sudo apt install build-essential git curl -y
```

### 2. Create Application User

```bash
sudo useradd -m -s /bin/bash ailib
sudo usermod -aG sudo ailib
```

### 3. Install Application

```bash
# Switch to application user
sudo su - ailib

# Clone repository
git clone https://github.com/your-org/ai-library.git
cd ai-library

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure systemd Service

Create `/etc/systemd/system/ai-library.service`:

```ini
[Unit]
Description=AI Library API Server
After=network.target

[Service]
Type=notify
User=ailib
Group=ailib
WorkingDirectory=/home/ailib/ai-library
Environment="PATH=/home/ailib/ai-library/venv/bin"
EnvironmentFile=/home/ailib/ai-library/.env
ExecStart=/home/ailib/ai-library/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 300 \
    --access-logfile /var/log/ai-library/access.log \
    --error-logfile /var/log/ai-library/error.log \
    src.wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-library
sudo systemctl start ai-library
sudo systemctl status ai-library
```

---

## Security

### SSL/TLS Configuration

#### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal (automatic with Certbot)
sudo certbot renew --dry-run
```

#### Self-Signed Certificate (Development)

```bash
# Generate certificate
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem
```

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if direct access needed)
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable
```

### API Authentication

#### Using API Keys

```bash
# Request with API key
curl -H "X-API-Key: your-api-key" \
    https://yourdomain.com/api/search \
    -d '{"query": "test"}'
```

#### Using JWT Tokens

```bash
# Get token (implement /auth/login endpoint)
TOKEN=$(curl -X POST https://yourdomain.com/auth/login \
    -d '{"username": "user", "password": "pass"}' \
    | jq -r '.token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
    https://yourdomain.com/api/query \
    -d '{"question": "What is AI?"}'
```

---

## Monitoring

### Prometheus Setup

Access Prometheus at: `http://localhost:9091`

**Key Metrics:**
- `ai_library_requests_total` - Total API requests
- `ai_library_requests_success` - Successful requests
- `ai_library_requests_error` - Failed requests
- `ai_library_avg_response_time` - Average response time
- `ai_library_active_requests` - Current active requests

### Grafana Dashboards

1. Access Grafana: `http://localhost:3000`
2. Login: `admin` / `admin` (change on first login)
3. Add Prometheus data source: `http://prometheus:9090`
4. Import dashboard from `monitoring/grafana/dashboards/`

### Health Checks

```bash
# Check service health
curl http://localhost:5000/health

# Expected response:
{
  "status": "healthy",
  "components": {
    "vector_db": {"status": "healthy", "size": 12345},
    "metadata_db": {"status": "healthy", "total_books": 100}
  }
}
```

### Log Management

```bash
# View application logs
docker-compose logs -f ai-library

# View specific service logs
docker-compose logs -f redis

# View last 100 lines
docker-compose logs --tail=100 ai-library

# Export logs
docker-compose logs ai-library > /tmp/ai-library.log
```

---

## Backup & Recovery

### Automated Backups

```bash
# Run manual backup
./scripts/backup.sh

# Schedule automatic backups (cron)
crontab -e

# Add line (daily backup at 2 AM):
0 2 * * * /path/to/ai-library/scripts/backup.sh
```

### Manual Backup

```bash
# Stop services
docker-compose stop ai-library

# Backup data
tar -czf backup_$(date +%Y%m%d).tar.gz \
    data/ \
    config.yaml \
    .env

# Restart services
docker-compose start ai-library
```

### Restore from Backup

```bash
# Stop services
docker-compose stop ai-library

# Restore using script
./scripts/restore.sh backups/ai_library_backup_20240101_120000.tar.gz

# Or manual restore
tar -xzf backup.tar.gz
cp -r data/* ./data/

# Restart services
docker-compose start ai-library
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs ai-library

# Check configuration
docker-compose config

# Verify environment variables
docker-compose exec ai-library env
```

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Reduce workers
# Edit .env: API_WORKERS=2
docker-compose restart ai-library
```

#### Slow Responses

```bash
# Check metrics
curl http://localhost:9090/metrics | grep response_time

# Enable caching
# Edit .env: CACHE_ENABLED=true
docker-compose restart ai-library
```

#### Database Errors

```bash
# Check database integrity
sqlite3 data/books_metadata.db "PRAGMA integrity_check;"

# Rebuild if corrupted
python build_vector_base.py --force
```

### Performance Tuning

#### Optimize Gunicorn Workers

```python
# Rule of thumb: (2 x CPU cores) + 1
workers = (2 * cpu_count) + 1
```

#### Redis Configuration

```bash
# Increase max memory
# docker-compose.yml
redis:
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

#### Vector Database Optimization

```python
# Use GPU if available
EMBEDDING_DEVICE=cuda

# Increase batch size
EMBEDDING_BATCH_SIZE=64
CHUNK_BATCH_SIZE=100
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run in foreground
docker-compose up ai-library

# Attach to running container
docker exec -it ai-library-api /bin/bash
```

---

## Production Checklist

Before going to production:

- [ ] Changed all default passwords and secrets
- [ ] Configured SSL/TLS certificates
- [ ] Enabled authentication
- [ ] Set up rate limiting
- [ ] Configured firewall rules
- [ ] Set up automated backups
- [ ] Configured monitoring and alerts
- [ ] Tested backup and restore procedures
- [ ] Load tested the API
- [ ] Reviewed and optimized configuration
- [ ] Set up log rotation
- [ ] Documented deployment procedures
- [ ] Created disaster recovery plan

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/ai-library/issues
- Documentation: See README.md and ENHANCEMENTS.md
- Monitoring: Check Grafana dashboards

---

**Production deployment complete! Your AI Library is ready for the world.** 🚀
