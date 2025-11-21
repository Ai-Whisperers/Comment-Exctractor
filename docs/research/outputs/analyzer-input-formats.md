# Output Formats for External AI Analyzer

## Overview

This project focuses on **data extraction only**. All extracted data will be formatted as input for an external AI-based sentiment/analysis system.

## Primary Output Format: JSON

The main output will be structured JSON files ready for AI processing.

### Comment Export Schema

```json
{
  "export_metadata": {
    "company": "Personal Paraguay",
    "extraction_date": "2024-01-31T10:30:00Z",
    "platforms": ["facebook", "instagram", "twitter", "linkedin"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    },
    "totals": {
      "posts": 150,
      "comments": 15000,
      "unique_commenters": 8500
    }
  },
  "comments": [...]
}
```

### Individual Comment Object

Each comment includes all data needed for AI analysis:

```json
{
  "id": "fb_123456789_987654321",
  "platform": "facebook",
  "post_id": "fb_123456789",
  "text": "El internet está muy lento, no puedo trabajar",
  "author": {
    "id": "user_444555666",
    "username": "juan_perez",
    "display_name": "Juan Perez",
    "is_verified": false,
    "profile_url": "https://facebook.com/juan_perez"
  },
  "timestamp": "2024-01-15T11:45:00Z",
  "engagement": {
    "likes": 5,
    "replies_count": 2
  },
  "context": {
    "is_reply": false,
    "parent_id": null,
    "post_text": "Conoce nuestros nuevos planes!",
    "post_type": "promotional"
  },
  "metadata": {
    "language_hint": "es",
    "has_media": false,
    "mentions": [],
    "hashtags": []
  }
}
```

## Output File Structures

### Option 1: Single File (Small Datasets < 50K comments)

```
output/
└── personal_paraguay_2024_01.json
```

### Option 2: Split Files (Large Datasets)

```
output/
├── metadata.json
├── posts/
│   ├── facebook_posts.json
│   ├── instagram_posts.json
│   └── twitter_posts.json
├── comments/
│   ├── facebook_comments.json
│   ├── instagram_comments.json
│   └── twitter_comments.json
└── commenters/
    └── commenter_profiles.json
```

### Option 3: JSONL (Streaming/Large Scale)

One comment per line for efficient processing:

```jsonl
{"id": "fb_1", "platform": "facebook", "text": "Excelente servicio!", ...}
{"id": "fb_2", "platform": "facebook", "text": "Internet muy lento", ...}
{"id": "ig_1", "platform": "instagram", "text": "Gran promoción!", ...}
```

## CSV Alternative

For simpler AI systems or spreadsheet pre-processing:

### comments.csv

```csv
id,platform,post_id,text,author_id,author_username,timestamp,likes,replies_count,is_reply,parent_id
fb_123456789_987654321,facebook,fb_123456789,"El internet está muy lento, no puedo trabajar",user_444555666,juan_perez,2024-01-15T11:45:00Z,5,2,false,
```

### posts.csv

```csv
id,platform,text,media_type,timestamp,likes,comments_count,shares,url
fb_123456789,facebook,"Conoce nuestros nuevos planes!",image,2024-01-15T10:00:00Z,1200,89,150,https://facebook.com/personalpy/posts/123456789
```

### commenters.csv

```csv
id,username,platforms,total_comments,first_seen,last_seen
user_444555666,juan_perez,"facebook,instagram",15,2023-06-15T00:00:00Z,2024-01-28T00:00:00Z
```

## Data Enrichment for AI

### Context Fields

The extractor adds context to help AI analysis:

```json
{
  "text": "Otra vez sin señal",
  "context": {
    "post_text": "Estamos expandiendo nuestra cobertura",
    "post_type": "announcement",
    "thread_position": 3,
    "is_reply_to_company": false,
    "previous_comment_same_author": "Cuando llega a mi zona?"
  }
}
```

### Commenter History

```json
{
  "author": {
    "id": "user_444555666",
    "username": "juan_perez",
    "history": {
      "total_comments": 15,
      "first_seen": "2023-06-15",
      "platforms": ["facebook", "instagram"],
      "comment_frequency": "weekly"
    }
  }
}
```

## Batch Processing Support

### Pagination Metadata

For large exports:

```json
{
  "pagination": {
    "total_comments": 45000,
    "batch_size": 10000,
    "current_batch": 1,
    "total_batches": 5,
    "next_batch_url": "/api/export/batch/2"
  },
  "comments": [...]
}
```

### Incremental Exports

For continuous processing:

```json
{
  "incremental": {
    "last_export": "2024-01-30T00:00:00Z",
    "this_export": "2024-01-31T00:00:00Z",
    "new_comments": 500,
    "updated_comments": 50
  },
  "comments": [...]
}
```

## Pre-processing Options

The extractor can optionally pre-process text:

### Raw (Default)
```json
{
  "text": "El internet está MUY lento!!! @personalpy 😡"
}
```

### Cleaned
```json
{
  "text": "El internet está MUY lento!!! @personalpy 😡",
  "text_cleaned": "el internet esta muy lento personalpy",
  "extracted": {
    "mentions": ["@personalpy"],
    "emojis": ["😡"],
    "urls": []
  }
}
```

## API Endpoint Response

For real-time integration:

```json
{
  "status": "success",
  "request_id": "req_abc123",
  "data": {
    "comments": [...],
    "pagination": {...}
  },
  "export_options": {
    "download_json": "/api/download/req_abc123.json",
    "download_csv": "/api/download/req_abc123.csv",
    "download_jsonl": "/api/download/req_abc123.jsonl"
  }
}
```

## Recommended Workflow

```
┌─────────────────┐
│  This Project   │
│   (Extractor)   │
└────────┬────────┘
         │
         │ JSON/CSV/JSONL
         ▼
┌─────────────────┐
│  AI Analyzer    │
│ (Separate Proj) │
└────────┬────────┘
         │
         │ Analysis Results
         ▼
┌─────────────────┐
│   Reporting /   │
│   Dashboard     │
└─────────────────┘
```

## Integration Points

### File-based
1. Extractor writes to shared storage (S3, local)
2. AI analyzer picks up files
3. Results written back

### API-based
1. Extractor exposes `/api/export` endpoint
2. AI analyzer calls API
3. Processes in batches

### Queue-based
1. Extractor publishes to message queue (Kafka, RabbitMQ)
2. AI analyzer consumes messages
3. Real-time processing

## Summary

This project outputs:
- **JSON** - Primary format with full context
- **CSV** - Simple tabular format
- **JSONL** - Streaming format for large datasets

All sentiment analysis, topic detection, and clustering will be performed by the external AI analyzer project.
