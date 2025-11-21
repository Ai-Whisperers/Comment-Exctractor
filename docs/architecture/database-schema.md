# Database Schema

## Overview

PostgreSQL database for storing extracted social media data.

## Entity Relationship Diagram

```
┌─────────────┐     ┌──────────────────┐     ┌────────────┐
│  companies  │────<│  social_accounts │     │   jobs     │
└─────────────┘     └──────────────────┘     └─────┬──────┘
                                                   │
                           ┌───────────────────────┤
                           │                       │
                    ┌──────▼──────┐         ┌──────▼──────┐
                    │    posts    │         │   exports   │
                    └──────┬──────┘         └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  comments   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   authors   │
                    └─────────────┘
```

## Tables

### companies

Registered companies for extraction.

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    country VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_country ON companies(country);
```

### social_accounts

Social media accounts linked to companies.

```sql
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255),
    identifier VARCHAR(255) NOT NULL,
    url VARCHAR(500),
    display_name VARCHAR(255),
    followers INTEGER,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(platform, identifier)
);

CREATE INDEX idx_social_accounts_company ON social_accounts(company_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform);
```

### extraction_jobs

Extraction job tracking.

```sql
CREATE TYPE job_status AS ENUM (
    'queued', 'running', 'completed', 'failed', 'cancelled'
);

CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    status job_status DEFAULT 'queued',
    platforms TEXT[] NOT NULL,
    options JSONB DEFAULT '{}',
    progress JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_jobs_company ON extraction_jobs(company_id);
CREATE INDEX idx_jobs_status ON extraction_jobs(status);
CREATE INDEX idx_jobs_created ON extraction_jobs(created_at DESC);
```

### posts

Extracted posts from social media.

```sql
CREATE TYPE media_type AS ENUM (
    'text', 'image', 'video', 'carousel', 'reel', 'story', 'link'
);

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255) NOT NULL,
    social_account_id UUID REFERENCES social_accounts(id),

    -- Content
    text TEXT,
    media_type media_type DEFAULT 'text',
    media_urls TEXT[],

    -- Metadata
    published_at TIMESTAMP WITH TIME ZONE,
    url VARCHAR(500),

    -- Engagement
    likes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    views INTEGER,
    reactions JSONB DEFAULT '{}',

    -- Raw data
    raw_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(job_id, platform, platform_id)
);

CREATE INDEX idx_posts_job ON posts(job_id);
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_account ON posts(social_account_id);
```

### authors

Comment authors (deduplicated by platform).

```sql
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    display_name VARCHAR(255),
    profile_url VARCHAR(500),
    is_verified BOOLEAN DEFAULT FALSE,
    profile_picture_url VARCHAR(500),
    followers INTEGER,
    metadata JSONB DEFAULT '{}',
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(platform, platform_id)
);

CREATE INDEX idx_authors_platform ON authors(platform);
CREATE INDEX idx_authors_username ON authors(username);
```

### comments

Extracted comments.

```sql
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id UUID REFERENCES authors(id),

    -- Identity
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255) NOT NULL,

    -- Content
    text TEXT NOT NULL,
    media_url VARCHAR(500),

    -- Threading
    parent_id UUID REFERENCES comments(id),
    is_reply BOOLEAN DEFAULT FALSE,

    -- Metadata
    published_at TIMESTAMP WITH TIME ZONE,

    -- Engagement
    likes INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,

    -- Raw data
    raw_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(job_id, platform, platform_id)
);

CREATE INDEX idx_comments_job ON comments(job_id);
CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_author ON comments(author_id);
CREATE INDEX idx_comments_parent ON comments(parent_id);
CREATE INDEX idx_comments_published ON comments(published_at DESC);
CREATE INDEX idx_comments_platform ON comments(platform);

-- Full text search on comment text
CREATE INDEX idx_comments_text_search ON comments USING gin(to_tsvector('spanish', text));
```

### exports

Export job tracking.

```sql
CREATE TYPE export_format AS ENUM ('json', 'csv', 'jsonl', 'parquet');
CREATE TYPE export_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES extraction_jobs(id),
    format export_format NOT NULL,
    status export_status DEFAULT 'pending',
    options JSONB DEFAULT '{}',
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    download_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_exports_job ON exports(job_id);
CREATE INDEX idx_exports_status ON exports(status);
```

### api_keys

API authentication.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    permissions TEXT[] DEFAULT ARRAY['read', 'write'],
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

## Views

### extraction_summary

Summary view for extraction jobs.

```sql
CREATE VIEW extraction_summary AS
SELECT
    j.id AS job_id,
    j.company_id,
    c.name AS company_name,
    j.status,
    j.platforms,
    COUNT(DISTINCT p.id) AS total_posts,
    COUNT(DISTINCT cm.id) AS total_comments,
    COUNT(DISTINCT cm.author_id) AS unique_authors,
    j.created_at,
    j.completed_at
FROM extraction_jobs j
JOIN companies c ON j.company_id = c.id
LEFT JOIN posts p ON j.id = p.job_id
LEFT JOIN comments cm ON j.id = cm.job_id
GROUP BY j.id, c.name;
```

### platform_stats

Statistics by platform.

```sql
CREATE VIEW platform_stats AS
SELECT
    j.id AS job_id,
    p.platform,
    COUNT(DISTINCT p.id) AS posts,
    COUNT(DISTINCT c.id) AS comments,
    COUNT(DISTINCT c.author_id) AS unique_authors,
    AVG(p.likes) AS avg_post_likes,
    AVG(p.comments_count) AS avg_comments_per_post
FROM extraction_jobs j
LEFT JOIN posts p ON j.id = p.job_id
LEFT JOIN comments c ON p.id = c.post_id
GROUP BY j.id, p.platform;
```

## Migrations

### Migration 001: Initial Schema

```sql
-- migrations/001_initial_schema.sql

BEGIN;

-- Create all tables and indexes as defined above

COMMIT;
```

### Migration 002: Add Full Text Search

```sql
-- migrations/002_add_fulltext_search.sql

BEGIN;

-- Add Spanish text search configuration
CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish);
ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;

-- Update index
DROP INDEX IF EXISTS idx_comments_text_search;
CREATE INDEX idx_comments_text_search ON comments
    USING gin(to_tsvector('spanish_unaccent', text));

COMMIT;
```

## Partitioning (for large scale)

### Partition comments by month

```sql
CREATE TABLE comments (
    -- ... same columns ...
) PARTITION BY RANGE (published_at);

-- Create partitions
CREATE TABLE comments_2024_01 PARTITION OF comments
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE comments_2024_02 PARTITION OF comments
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Automated partition creation function
CREATE OR REPLACE FUNCTION create_comments_partition()
RETURNS TRIGGER AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', NEW.published_at);
    partition_name := 'comments_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 month';

    IF NOT EXISTS (
        SELECT 1 FROM pg_tables WHERE tablename = partition_name
    ) THEN
        EXECUTE FORMAT(
            'CREATE TABLE %I PARTITION OF comments FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Backup Strategy

### Daily Backup Script

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/postgres"
DB_NAME="comment_extractor"

# Full backup
pg_dump -Fc $DB_NAME > $BACKUP_DIR/full_$DATE.dump

# Keep last 7 daily backups
find $BACKUP_DIR -name "full_*.dump" -mtime +7 -delete
```

## Performance Tuning

### Recommended PostgreSQL Settings

```ini
# postgresql.conf

# Memory
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 16MB
maintenance_work_mem = 128MB

# Connections
max_connections = 100

# Write performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Query planning
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200  # For SSD
```

### Useful Queries

#### Check table sizes

```sql
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

#### Check index usage

```sql
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```
