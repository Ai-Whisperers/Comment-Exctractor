# Configuration & Environment Setup

## Environment Variables

### Required Variables

```env
# .env

# ===================
# Database
# ===================
DATABASE_URL=postgresql://user:password@localhost:5432/comment_extractor
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# ===================
# Redis
# ===================
REDIS_URL=redis://localhost:6379/0

# ===================
# API Configuration
# ===================
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-min-32-characters
API_CORS_ORIGINS=["http://localhost:3000"]

# ===================
# Third-Party APIs
# ===================

# Apify (recommended for extraction)
APIFY_API_KEY=apify_api_xxx

# Facebook (if using official API)
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_PAGE_ACCESS_TOKEN=

# Instagram (via Facebook)
INSTAGRAM_BUSINESS_ACCOUNT_ID=

# Twitter/X
TWITTER_BEARER_TOKEN=

# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=

# ===================
# Storage
# ===================
STORAGE_TYPE=local  # local, s3, gcs
STORAGE_PATH=./data/exports

# S3 (if STORAGE_TYPE=s3)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=comment-extractor-exports
AWS_S3_REGION=us-east-1

# ===================
# Celery
# ===================
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ===================
# Logging
# ===================
LOG_LEVEL=INFO
LOG_FORMAT=json  # json or text
LOG_FILE=./logs/app.log

# ===================
# Rate Limiting
# ===================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute

# ===================
# Feature Flags
# ===================
ENABLE_WEBHOOKS=true
ENABLE_METRICS=true
```

### Environment-Specific Overrides

```env
# .env.development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/comment_extractor_dev
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# .env.production
DATABASE_URL=postgresql://user:pass@prod-db:5432/comment_extractor
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_ENABLED=true
```

## Settings Management

### Settings Class

```python
# src/config/settings.py

from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, RedisDsn
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: PostgresDsn
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: RedisDsn

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str
    api_cors_origins: List[str] = ["http://localhost:3000"]

    # Third-party APIs
    apify_api_key: Optional[str] = None
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_page_access_token: Optional[str] = None
    instagram_business_account_id: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None

    # Storage
    storage_type: str = "local"
    storage_path: str = "./data/exports"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_s3_region: str = "us-east-1"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"

    # Features
    enable_webhooks: bool = True
    enable_metrics: bool = True

    # Extraction defaults
    default_max_posts: int = 100
    default_max_comments: int = 500
    extraction_timeout: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Usage
settings = get_settings()
```

### Platform Credentials

```python
# src/config/credentials.py

from dataclasses import dataclass
from typing import Optional
from config.settings import get_settings

@dataclass
class PlatformCredentials:
    platform: str
    api_key: Optional[str] = None
    access_token: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None

def get_platform_credentials(platform: str) -> PlatformCredentials:
    settings = get_settings()

    if platform == "facebook":
        return PlatformCredentials(
            platform="facebook",
            app_id=settings.facebook_app_id,
            app_secret=settings.facebook_app_secret,
            access_token=settings.facebook_page_access_token
        )

    elif platform == "instagram":
        return PlatformCredentials(
            platform="instagram",
            access_token=settings.facebook_page_access_token,
            app_id=settings.instagram_business_account_id
        )

    elif platform == "twitter":
        return PlatformCredentials(
            platform="twitter",
            access_token=settings.twitter_bearer_token
        )

    elif platform == "linkedin":
        return PlatformCredentials(
            platform="linkedin",
            app_id=settings.linkedin_client_id,
            app_secret=settings.linkedin_client_secret,
            access_token=settings.linkedin_access_token
        )

    # Default: use Apify
    return PlatformCredentials(
        platform=platform,
        api_key=settings.apify_api_key
    )
```

## Logging Configuration

```python
# src/config/logging.py

import logging
import sys
from pythonjsonlogger import jsonlogger
from config.settings import get_settings

def setup_logging():
    settings = get_settings()

    # Create formatter
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler (optional)
    handlers = [console_handler]
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        handlers=handlers
    )

    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

## Database Configuration

```python
# src/config/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings

def get_database_url():
    settings = get_settings()
    # Convert postgresql:// to postgresql+asyncpg://
    url = str(settings.database_url)
    return url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    get_database_url(),
    pool_size=get_settings().database_pool_size,
    max_overflow=get_settings().database_max_overflow,
    echo=get_settings().log_level == "DEBUG"
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Development Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# PostgreSQL 14+
psql --version

# Redis 7+
redis-server --version
```

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd comment-extractor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
cp .env.example .env
# Edit .env with your values

# 5. Create database
createdb comment_extractor

# 6. Run migrations
alembic upgrade head

# 7. Start Redis
redis-server

# 8. Start Celery worker
celery -A src.worker worker --loglevel=info

# 9. Start API
uvicorn src.api.app:app --reload
```

### Docker Development

```yaml
# docker-compose.dev.yml

version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - ./data:/app/data
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/comment_extractor
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    command: uvicorn src.api.app:app --host 0.0.0.0 --reload

  worker:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/comment_extractor
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    command: celery -A src.worker worker --loglevel=info

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=comment_extractor
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_dev:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_dev:
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/test_extractors/

# Watch mode
pytest-watch
```

## Production Configuration

### Recommended Settings

```env
# .env.production

# Security
API_SECRET_KEY=<generate-strong-key>
RATE_LIMIT_ENABLED=true

# Performance
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
ENABLE_METRICS=true
```

### Health Checks

```python
# src/api/health.py

from fastapi import APIRouter
from config.database import engine
from config.settings import get_settings
import redis

router = APIRouter()

@router.get("/health")
async def health_check():
    settings = get_settings()
    checks = {
        "status": "healthy",
        "database": await check_database(),
        "redis": check_redis(),
        "version": "1.0.0"
    }

    if any(v == "unhealthy" for v in checks.values() if isinstance(v, str)):
        checks["status"] = "unhealthy"

    return checks

async def check_database():
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return "connected"
    except Exception:
        return "unhealthy"

def check_redis():
    try:
        settings = get_settings()
        r = redis.from_url(str(settings.redis_url))
        r.ping()
        return "connected"
    except Exception:
        return "unhealthy"
```
