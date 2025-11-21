# Social Media Comment Extractor - Project Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              Social Media Comment Extractor                      │
│              (Data Extraction Only)                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Facebook │  │Instagram │  │Twitter/X │  │ LinkedIn │  ...    │
│  │ Extractor│  │ Extractor│  │ Extractor│  │ Extractor│         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │             │             │             │                │
│       └─────────────┴──────┬──────┴─────────────┘                │
│                            │                                     │
│                   ┌────────▼────────┐                            │
│                   │  Data Normalizer │                            │
│                   │  (Unified Schema)│                            │
│                   └────────┬────────┘                            │
│                            │                                     │
│                   ┌────────▼────────┐                            │
│                   │   Data Storage   │                            │
│                   │  (PostgreSQL/    │                            │
│                   │   MongoDB)       │                            │
│                   └────────┬────────┘                            │
│                            │                                     │
│                   ┌────────▼────────┐                            │
│                   │  Data Exporter   │                            │
│                   └────────┬────────┘                            │
│                            │                                     │
│       ┌──────────┬─────────┼─────────┐                           │
│       │          │         │         │                           │
│  ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌──▼───┐                      │
│  │  CSV   │ │  JSON  │ │ JSONL  │ │ API  │                      │
│  │ Export │ │ Export │ │ Export │ │ Resp │                      │
│  └────────┘ └────────┘ └────────┘ └──────┘                      │
│                            │                                     │
│                            ▼                                     │
│              ┌─────────────────────────┐                         │
│              │  External AI Analyzer   │                         │
│              │  (Separate Project)     │                         │
│              └─────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core
- **Language**: Python 3.10+
- **Package Manager**: pip/poetry
- **Task Queue**: Celery (for async jobs)
- **Scheduler**: APScheduler (for periodic extraction)

### Data Extraction
- **Official APIs**: requests, httpx
- **Third-Party**: apify-client
- **Rate Limiting**: ratelimit, tenacity

### Data Storage
- **Primary**: PostgreSQL 14+
- **Cache**: Redis
- **Object Storage**: S3/MinIO (for media)

### Data Export
- **Formats**: JSON, CSV, JSONL, Parquet
- **Serialization**: orjson (fast JSON)

### Web Interface
- **API**: FastAPI

**Note**: Sentiment analysis, clustering, and visualization are handled by the external AI analyzer project.

## Project Structure

```
comment-extractor/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Configuration management
│   │   └── credentials.py         # API keys management
│   │
│   ├── extractors/                # Platform-specific extractors
│   │   ├── __init__.py
│   │   ├── base.py                # Base extractor class
│   │   ├── facebook.py
│   │   ├── instagram.py
│   │   ├── twitter.py
│   │   ├── linkedin.py
│   │   └── tiktok.py
│   │
│   ├── models/                    # Data models
│   │   ├── __init__.py
│   │   ├── post.py
│   │   ├── comment.py
│   │   ├── commenter.py
│   │   └── analysis.py
│   │
│   ├── storage/                   # Data persistence
│   │   ├── __init__.py
│   │   ├── database.py            # PostgreSQL/MongoDB
│   │   ├── cache.py               # Redis
│   │   └── file_storage.py        # File exports
│   │
│   ├── analyzers/                 # Analysis modules
│   │   ├── __init__.py
│   │   ├── preprocessor.py        # Text cleaning
│   │   ├── deduplicator.py        # Duplicate detection
│   │   ├── clusterer.py           # Comment clustering
│   │   ├── sentiment.py           # Sentiment analysis
│   │   └── commenter.py           # Commenter profiling
│   │
│   ├── reporters/                 # Output generation
│   │   ├── __init__.py
│   │   ├── exporter.py            # CSV/JSON export
│   │   ├── visualizer.py          # Charts
│   │   ├── pdf_generator.py       # PDF reports
│   │   └── dashboard.py           # Streamlit dashboard
│   │
│   ├── api/                       # API endpoints
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI app
│   │   ├── routes/
│   │   │   ├── extraction.py
│   │   │   ├── analysis.py
│   │   │   └── reports.py
│   │   └── schemas.py             # API schemas
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── logging.py
│       ├── rate_limiter.py
│       └── validators.py
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── test_extractors/
│   ├── test_analyzers/
│   └── test_reporters/
│
├── data/                          # Data directory
│   ├── raw/                       # Raw extracted data
│   ├── processed/                 # Processed data
│   └── output/                    # Generated reports
│
├── docs/                          # Documentation
│   ├── research/
│   ├── architecture/
│   └── api/
│
├── scripts/                       # Utility scripts
│   ├── setup_db.py
│   ├── run_extraction.py
│   └── generate_report.py
│
├── docker/                        # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## Data Flow

### 1. Extraction Pipeline

```python
# src/extractors/base.py
from abc import ABC, abstractmethod
from typing import List
from models import Post, Comment

class BaseExtractor(ABC):
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.rate_limiter = RateLimiter()

    @abstractmethod
    async def get_company_profile(self, company_id: str) -> dict:
        pass

    @abstractmethod
    async def get_posts(self, company_id: str, limit: int = 100) -> List[Post]:
        pass

    @abstractmethod
    async def get_comments(self, post_id: str) -> List[Comment]:
        pass

    async def extract_all(self, company_id: str) -> dict:
        profile = await self.get_company_profile(company_id)
        posts = await self.get_posts(company_id)

        all_comments = []
        for post in posts:
            comments = await self.get_comments(post.id)
            all_comments.extend(comments)

        return {
            'profile': profile,
            'posts': posts,
            'comments': all_comments
        }
```

### 2. Data Normalization

```python
# src/models/comment.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UnifiedComment(BaseModel):
    id: str
    platform: str
    post_id: str
    text: str
    author_id: str
    author_username: str
    author_name: Optional[str]
    timestamp: datetime
    likes: int = 0
    replies_count: int = 0
    parent_id: Optional[str] = None
    raw_data: dict = {}

    @classmethod
    def from_facebook(cls, fb_comment: dict) -> 'UnifiedComment':
        return cls(
            id=f"fb_{fb_comment['id']}",
            platform='facebook',
            post_id=fb_comment['post_id'],
            text=fb_comment['message'],
            author_id=fb_comment['from']['id'],
            author_username=fb_comment['from']['name'],
            timestamp=fb_comment['created_time'],
            likes=fb_comment.get('like_count', 0),
            replies_count=fb_comment.get('comment_count', 0),
            raw_data=fb_comment
        )

    @classmethod
    def from_instagram(cls, ig_comment: dict) -> 'UnifiedComment':
        # Similar transformation
        pass
```

### 3. Analysis Pipeline

```python
# src/analyzers/pipeline.py
from typing import List
from models import UnifiedComment, AnalysisResult

class AnalysisPipeline:
    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.deduplicator = CommentDeduplicator()
        self.clusterer = CommentClusterer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.commenter_analyzer = CommenterAnalyzer()

    async def analyze(self, comments: List[UnifiedComment]) -> AnalysisResult:
        # Step 1: Preprocess
        preprocessed = [
            self.preprocessor.process(c.text)
            for c in comments
        ]

        # Step 2: Deduplicate and cluster
        clusters = self.deduplicator.find_clusters(comments)

        # Step 3: Sentiment analysis
        sentiments = self.sentiment_analyzer.batch_analyze([c.text for c in comments])

        # Step 4: Commenter profiling
        commenter_profiles = self.commenter_analyzer.analyze(comments)

        return AnalysisResult(
            total_comments=len(comments),
            clusters=clusters,
            sentiments=sentiments,
            commenter_profiles=commenter_profiles
        )
```

## Configuration

### Environment Variables

```env
# .env.example

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/comment_extractor
REDIS_URL=redis://localhost:6379/0

# Facebook
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_PAGE_ACCESS_TOKEN=your_token

# Instagram (via Facebook)
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id

# Twitter
TWITTER_BEARER_TOKEN=your_bearer_token

# LinkedIn
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_ACCESS_TOKEN=your_access_token

# Apify (third-party)
APIFY_API_KEY=your_apify_key

# General
LOG_LEVEL=INFO
OUTPUT_DIR=./data/output
```

### Settings Management

```python
# src/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    redis_url: str

    # Extraction
    extraction_batch_size: int = 100
    rate_limit_per_minute: int = 60

    # Analysis
    similarity_threshold: float = 0.8
    min_cluster_size: int = 3
    sentiment_model: str = "pysentimiento/robertuito-sentiment-analysis"

    # Output
    output_dir: str = "./data/output"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Database Schema

### PostgreSQL Schema

```sql
-- Companies
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Social accounts
CREATE TABLE social_accounts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    followers INTEGER,
    UNIQUE(platform, account_id)
);

-- Posts
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    platform_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    social_account_id INTEGER REFERENCES social_accounts(id),
    content TEXT,
    media_type VARCHAR(50),
    published_at TIMESTAMP,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    raw_data JSONB,
    UNIQUE(platform, platform_id)
);

-- Comments
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    platform_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    post_id INTEGER REFERENCES posts(id),
    parent_id INTEGER REFERENCES comments(id),
    author_id VARCHAR(255),
    author_username VARCHAR(255),
    author_name VARCHAR(255),
    text TEXT NOT NULL,
    published_at TIMESTAMP,
    likes INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    raw_data JSONB,
    UNIQUE(platform, platform_id)
);

-- Analysis results
CREATE TABLE sentiment_analysis (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER REFERENCES comments(id),
    sentiment VARCHAR(20),
    positive_score FLOAT,
    negative_score FLOAT,
    neutral_score FLOAT,
    emotions JSONB,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comment_clusters (
    id SERIAL PRIMARY KEY,
    analysis_run_id INTEGER,
    cluster_id INTEGER,
    theme VARCHAR(255),
    representative_text TEXT,
    comment_count INTEGER,
    sentiment VARCHAR(20),
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE commenter_profiles (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),
    platform_user_id VARCHAR(255),
    username VARCHAR(255),
    total_comments INTEGER,
    avg_likes FLOAT,
    sentiment_positive_ratio FLOAT,
    classification VARCHAR(50),
    influence_score FLOAT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    UNIQUE(platform, platform_user_id)
);

-- Indexes
CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_author ON comments(author_id);
CREATE INDEX idx_comments_published ON comments(published_at);
CREATE INDEX idx_sentiment_comment ON sentiment_analysis(comment_id);
```

## API Endpoints

### FastAPI Routes

```python
# src/api/routes/extraction.py
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/extraction", tags=["extraction"])

@router.post("/start")
async def start_extraction(
    company_name: str,
    platforms: List[str],
    background_tasks: BackgroundTasks
):
    """Start extraction job for a company"""
    job_id = create_job(company_name, platforms)
    background_tasks.add_task(run_extraction, job_id)
    return {"job_id": job_id, "status": "started"}

@router.get("/status/{job_id}")
async def get_extraction_status(job_id: str):
    """Get status of extraction job"""
    return get_job_status(job_id)

# src/api/routes/analysis.py
router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/run")
async def run_analysis(job_id: str):
    """Run analysis on extracted data"""
    pass

@router.get("/results/{job_id}")
async def get_analysis_results(job_id: str):
    """Get analysis results"""
    pass

# src/api/routes/reports.py
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/summary/{job_id}")
async def get_summary(job_id: str):
    """Get executive summary"""
    pass

@router.get("/export/{job_id}")
async def export_data(job_id: str, format: str = "json"):
    """Export data in specified format"""
    pass
```

## Deployment

### Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/comment_extractor
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data

  worker:
    build: .
    command: celery -A src.worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/comment_extractor
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  scheduler:
    build: .
    command: celery -A src.worker beat --loglevel=info
    depends_on:
      - worker

  dashboard:
    build: .
    command: streamlit run src/reporters/dashboard.py
    ports:
      - "8501:8501"
    depends_on:
      - app

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=comment_extractor
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Estimated Development Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Setup | 1 week | Project structure, DB, basic config |
| Extractors | 2 weeks | All platform extractors |
| Storage | 1 week | Database, caching, file storage |
| Analysis | 2 weeks | Dedup, clustering, sentiment |
| Reports | 1 week | CSV, JSON, PDF, charts |
| Dashboard | 1 week | Streamlit interactive |
| API | 1 week | FastAPI endpoints |
| Testing | 1 week | Unit and integration tests |
| **Total** | **10 weeks** | |

## Cost Estimates

### Monthly Infrastructure
- Database (managed): $20-50
- Redis (managed): $10-20
- Compute (small): $20-50
- **Total**: $50-120/month

### Third-Party APIs
- Apify (moderate use): $50-100/month
- Official APIs: Free (within limits)

### Total Monthly: $100-220
