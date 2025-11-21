# Deployment & Operations Guide

## Deployment Options

### 1. Docker Compose (Recommended for small-medium)

```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  api:
    image: comment-extractor:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - API_SECRET_KEY=${API_SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    image: comment-extractor:latest
    command: celery -A src.worker worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    depends_on:
      - db
      - redis
    restart: always
    deploy:
      replicas: 2

  scheduler:
    image: comment-extractor:latest
    command: celery -A src.worker beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - worker
    restart: always

  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    restart: always

  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: always

volumes:
  postgres_data:
  redis_data:
```

### 2. Kubernetes (For scale)

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: comment-extractor-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: comment-extractor-api
  template:
    metadata:
      labels:
        app: comment-extractor-api
    spec:
      containers:
      - name: api
        image: comment-extractor:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comment-extractor-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: comment-extractor-worker
  template:
    spec:
      containers:
      - name: worker
        image: comment-extractor:latest
        command: ["celery", "-A", "src.worker", "worker", "--loglevel=info"]
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## Dockerfile

```dockerfile
# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Default command
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/ci.yml

name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: docker build -t comment-extractor:${{ github.sha }} .

    - name: Push to registry
      run: |
        echo ${{ secrets.REGISTRY_PASSWORD }} | docker login -u ${{ secrets.REGISTRY_USERNAME }} --password-stdin
        docker push comment-extractor:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to production
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.PROD_HOST }}
        username: ${{ secrets.PROD_USER }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /app/comment-extractor
          docker-compose pull
          docker-compose up -d
```

## Monitoring

### Prometheus Metrics

```python
# src/monitoring/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Extraction metrics
extraction_requests = Counter(
    'extraction_requests_total',
    'Total extraction requests',
    ['platform']
)

extraction_duration = Histogram(
    'extraction_duration_seconds',
    'Extraction duration',
    ['platform'],
    buckets=[60, 120, 300, 600, 1800, 3600]
)

comments_extracted = Counter(
    'comments_extracted_total',
    'Total comments extracted',
    ['platform']
)

# Queue metrics
queue_size = Gauge(
    'queue_size',
    'Current queue size'
)

# Error metrics
extraction_errors = Counter(
    'extraction_errors_total',
    'Total extraction errors',
    ['platform', 'error_type']
)

# API metrics
api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_latency = Histogram(
    'api_latency_seconds',
    'API request latency',
    ['method', 'endpoint']
)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Comment Extractor",
    "panels": [
      {
        "title": "Extraction Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(extraction_requests_total[5m])",
            "legendFormat": "{{platform}}"
          }
        ]
      },
      {
        "title": "Comments Extracted",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(comments_extracted_total)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(extraction_errors_total[5m])",
            "legendFormat": "{{platform}} - {{error_type}}"
          }
        ]
      },
      {
        "title": "Queue Size",
        "type": "gauge",
        "targets": [
          {
            "expr": "queue_size"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

```yaml
# logging config for production

version: 1
disable_existing_loggers: false

formatters:
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(timestamp)s %(level)s %(name)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    formatter: json
    filename: /var/log/comment-extractor/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  src:
    level: INFO
    handlers: [console, file]

root:
  level: WARNING
  handlers: [console]
```

## Backup Strategy

### Database Backup

```bash
#!/bin/bash
# scripts/backup.sh

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="comment_extractor"

# Create backup directory
mkdir -p $BACKUP_DIR

# Full backup
pg_dump -Fc $DB_NAME > $BACKUP_DIR/full_$DATE.dump

# Upload to S3
aws s3 cp $BACKUP_DIR/full_$DATE.dump s3://backups/postgres/

# Keep last 7 local backups
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete

echo "Backup completed: full_$DATE.dump"
```

### Cron Schedule

```cron
# Daily backup at 2 AM
0 2 * * * /app/scripts/backup.sh

# Weekly full backup on Sunday
0 3 * * 0 /app/scripts/backup.sh --full
```

## Scaling Guidelines

### Horizontal Scaling

| Load | API Replicas | Worker Replicas | Database |
|------|-------------|-----------------|----------|
| Low (<100 jobs/day) | 1 | 2 | 1 (4GB) |
| Medium (100-1000/day) | 2 | 5 | 1 (8GB) |
| High (1000+/day) | 3+ | 10+ | Cluster |

### Auto-scaling Rules

```yaml
# Kubernetes HPA

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: comment-extractor-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: External
    external:
      metric:
        name: celery_queue_length
      target:
        type: AverageValue
        averageValue: 10
```

## Security Checklist

- [ ] API keys stored in secrets manager
- [ ] Database encrypted at rest
- [ ] TLS enabled for all connections
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] Audit logging enabled
- [ ] Regular security updates
- [ ] Firewall rules configured
- [ ] Non-root container user
- [ ] Secrets rotation policy

## Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check worker memory
docker stats comment-extractor-worker

# Reduce concurrency if needed
celery -A src.worker worker --concurrency=2
```

#### Slow Extractions

```bash
# Check queue backlog
redis-cli llen celery

# Scale up workers
docker-compose up -d --scale worker=5
```

#### Database Connection Issues

```bash
# Check connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Increase pool size in config
DATABASE_POOL_SIZE=20
```

## Runbooks

### Restart Services

```bash
# API
docker-compose restart api

# Workers
docker-compose restart worker

# All services
docker-compose down && docker-compose up -d
```

### Clear Queue

```bash
# Clear all pending tasks
redis-cli FLUSHDB

# Clear specific queue
celery -A src.worker purge
```

### Database Maintenance

```bash
# Vacuum tables
psql -c "VACUUM ANALYZE;"

# Reindex
psql -c "REINDEX DATABASE comment_extractor;"
```
