# SNOWFLAKE Deployment Guide

## Prerequisites

- Docker and Docker Compose
- 16GB+ RAM recommended
- GPU with CUDA support (for AlphaFold)
- 100GB+ free disk space (for AlphaFold databases)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/snowflake.git
cd snowflake
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./snowflake.db

# AlphaFold
ALPHAFOLD_DATA_DIR=/data/alphafold
ALPHAFOLD_USE_CLOUD_API=false

# AI APIs (at least one required for reports)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Blockchain
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PRIVATE_KEY=your_private_key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Download AlphaFold Databases (Optional)

If using local AlphaFold:

```bash
./scripts/download_alphafold_data.sh
```

This will download ~2.2TB of data. Alternatively, set `ALPHAFOLD_USE_CLOUD_API=true`.

### 4. Start Services

```bash
docker-compose up -d
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 5. Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "SNOWFLAKE API", "version": "1.0.0"}
```

## Production Deployment

### Using Vercel (Frontend) + Render/Railway (Backend)

1. **Deploy Frontend to Vercel:**
```bash
vercel deploy
```

2. **Deploy Backend to Render:**
- Create new Web Service
- Connect GitHub repository
- Set environment variables
- Deploy

### Using Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: snowflake-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: snowflake-backend
  template:
    metadata:
      labels:
        app: snowflake-backend
    spec:
      containers:
      - name: backend
        image: snowflake-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: snowflake-secrets
              key: database-url
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/jobs
```

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View AlphaFold logs
docker-compose logs -f alphafold
```

## Scaling

### Horizontal Scaling

Add more backend workers:

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 5
```

### Vertical Scaling

Increase resources per container:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
```

## Troubleshooting

### AlphaFold Out of Memory

Increase Docker memory limit or use cloud API.

### Slow Docking

- Enable GPU acceleration
- Reduce exhaustiveness parameter
- Scale horizontally

### Database Locks

Switch from SQLite to PostgreSQL:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/snowflake
```

## Security

### Production Checklist

- [ ] Set strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set up API rate limiting
- [ ] Enable authentication
- [ ] Rotate secrets regularly
- [ ] Set up monitoring alerts

## Backup

```bash
# Backup database
docker-compose exec backend \
  sqlite3 /app/snowflake.db ".backup /backups/snowflake_backup.db"

# Backup predictions
tar -czf predictions_backup.tar.gz /workspace/predictions/
```

## Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build

# Restart services
docker-compose up -d
