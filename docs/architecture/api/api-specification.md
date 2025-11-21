# API Specification

## Overview

RESTful API for managing extraction jobs and exporting data. Built with FastAPI.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

### API Key Authentication

```http
Authorization: Bearer <api_key>
```

All endpoints require authentication except health checks.

## Endpoints

### Health & Status

#### GET /health

Check API health status.

**Response 200**:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Companies

#### POST /companies

Register a new company for extraction.

**Request**:

```json
{
  "name": "Personal Paraguay",
  "industry": "Telecommunications",
  "country": "Paraguay",
  "social_accounts": [
    {
      "platform": "facebook",
      "identifier": "personalpy",
      "url": "https://www.facebook.com/personalpy"
    },
    {
      "platform": "instagram",
      "identifier": "personalpy",
      "url": "https://www.instagram.com/personalpy"
    },
    {
      "platform": "twitter",
      "identifier": "personalpy",
      "url": "https://twitter.com/personalpy"
    }
  ]
}
```

**Response 201**:

```json
{
  "id": "comp_abc123",
  "name": "Personal Paraguay",
  "social_accounts": [...],
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /companies

List all registered companies.

**Query Parameters**:

- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)

**Response 200**:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### GET /companies/{company_id}

Get company details.

**Response 200**:

```json
{
  "id": "comp_abc123",
  "name": "Personal Paraguay",
  "industry": "Telecommunications",
  "country": "Paraguay",
  "social_accounts": [...],
  "stats": {
    "total_extractions": 10,
    "last_extraction": "2024-01-14T08:00:00Z",
    "total_comments": 45000
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Extraction Jobs

#### POST /extractions

Start a new extraction job.

**Request**:

```json
{
  "company_id": "comp_abc123",
  "platforms": ["facebook", "instagram", "twitter"],
  "options": {
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "max_posts_per_platform": 100,
    "max_comments_per_post": 500,
    "include_replies": true,
    "include_author_details": true
  }
}
```

**Response 202** (Accepted):

```json
{
  "job_id": "job_xyz789",
  "company_id": "comp_abc123",
  "status": "queued",
  "platforms": ["facebook", "instagram", "twitter"],
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T11:00:00Z"
}
```

#### GET /extractions

List extraction jobs.

**Query Parameters**:

- `company_id` (string): Filter by company
- `status` (string): Filter by status (queued, running, completed, failed)
- `page`, `per_page`: Pagination

**Response 200**:

```json
{
  "data": [
    {
      "job_id": "job_xyz789",
      "company_id": "comp_abc123",
      "status": "completed",
      "progress": {
        "facebook": {"posts": 60, "comments": 8000},
        "instagram": {"posts": 80, "comments": 4000},
        "twitter": {"posts": 50, "comments": 2500}
      },
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T11:15:00Z"
    }
  ],
  "pagination": {...}
}
```

#### GET /extractions/{job_id}

Get extraction job details.

**Response 200**:

```json
{
  "job_id": "job_xyz789",
  "company_id": "comp_abc123",
  "status": "running",
  "progress": {
    "overall_percent": 65,
    "platforms": {
      "facebook": {
        "status": "completed",
        "posts_extracted": 60,
        "comments_extracted": 8000
      },
      "instagram": {
        "status": "running",
        "posts_extracted": 45,
        "comments_extracted": 2200
      },
      "twitter": {
        "status": "pending",
        "posts_extracted": 0,
        "comments_extracted": 0
      }
    }
  },
  "options": {...},
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "estimated_completion": "2024-01-15T11:00:00Z"
}
```

#### DELETE /extractions/{job_id}

Cancel a running extraction job.

**Response 200**:

```json
{
  "job_id": "job_xyz789",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T10:45:00Z"
}
```

---

### Data Export

#### POST /exports

Create a data export from completed extraction.

**Request**:

```json
{
  "job_id": "job_xyz789",
  "format": "json",
  "options": {
    "include_posts": true,
    "include_comments": true,
    "include_authors": true,
    "split_by_platform": false,
    "compression": "gzip"
  }
}
```

**Response 202**:

```json
{
  "export_id": "exp_def456",
  "job_id": "job_xyz789",
  "format": "json",
  "status": "processing",
  "created_at": "2024-01-15T11:30:00Z"
}
```

#### GET /exports/{export_id}

Get export status and download URL.

**Response 200**:

```json
{
  "export_id": "exp_def456",
  "job_id": "job_xyz789",
  "format": "json",
  "status": "completed",
  "file_size_bytes": 15234567,
  "download_url": "/api/v1/exports/exp_def456/download",
  "expires_at": "2024-01-22T11:30:00Z",
  "created_at": "2024-01-15T11:30:00Z",
  "completed_at": "2024-01-15T11:32:00Z"
}
```

#### GET /exports/{export_id}/download

Download the exported file.

**Response 200**: File stream with appropriate content-type.

---

### Data Query (Optional)

#### GET /extractions/{job_id}/comments

Query comments from an extraction (paginated).

**Query Parameters**:

- `platform` (string): Filter by platform
- `date_from`, `date_to` (string): Date range
- `author_id` (string): Filter by author
- `search` (string): Text search
- `page`, `per_page`: Pagination

**Response 200**:

```json
{
  "data": [
    {
      "id": "fb_123456789_987654321",
      "platform": "facebook",
      "post_id": "fb_123456789",
      "text": "El internet está muy lento",
      "author": {
        "id": "user_444555666",
        "username": "juan_perez"
      },
      "timestamp": "2024-01-15T11:45:00Z",
      "likes": 5,
      "replies_count": 2
    }
  ],
  "pagination": {...}
}
```

#### GET /extractions/{job_id}/stats

Get extraction statistics.

**Response 200**:

```json
{
  "job_id": "job_xyz789",
  "totals": {
    "posts": 190,
    "comments": 14500,
    "unique_authors": 8200
  },
  "by_platform": {
    "facebook": {
      "posts": 60,
      "comments": 8000,
      "unique_authors": 5000
    },
    "instagram": {
      "posts": 80,
      "comments": 4000,
      "unique_authors": 2500
    },
    "twitter": {
      "posts": 50,
      "comments": 2500,
      "unique_authors": 1800
    }
  },
  "date_range": {
    "earliest_post": "2024-01-01T08:00:00Z",
    "latest_post": "2024-01-31T22:30:00Z"
  }
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "date_from",
        "message": "Date must be in YYYY-MM-DD format"
      }
    ]
  },
  "request_id": "req_abc123"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Rate Limiting

### Limits

- **Standard**: 100 requests/minute
- **Export downloads**: 10 requests/minute
- **Extraction creation**: 5 requests/minute

### Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705316400
```

---

## Webhooks (Optional)

### Configuration

Register webhook URLs to receive notifications.

#### POST /webhooks

```json
{
  "url": "https://your-app.com/webhooks/extractor",
  "events": ["extraction.completed", "extraction.failed", "export.ready"],
  "secret": "your_webhook_secret"
}
```

### Event Payloads

#### extraction.completed

```json
{
  "event": "extraction.completed",
  "timestamp": "2024-01-15T11:15:00Z",
  "data": {
    "job_id": "job_xyz789",
    "company_id": "comp_abc123",
    "totals": {
      "posts": 190,
      "comments": 14500
    }
  }
}
```

#### export.ready

```json
{
  "event": "export.ready",
  "timestamp": "2024-01-15T11:32:00Z",
  "data": {
    "export_id": "exp_def456",
    "job_id": "job_xyz789",
    "download_url": "https://..."
  }
}
```

---

## SDK Examples

### Python

```python
from comment_extractor import Client

client = Client(api_key="your_api_key")

# Create extraction
job = client.extractions.create(
    company_id="comp_abc123",
    platforms=["facebook", "instagram"],
    date_from="2024-01-01",
    date_to="2024-01-31"
)

# Wait for completion
job.wait()

# Export data
export = client.exports.create(
    job_id=job.id,
    format="json"
)

# Download
export.download_to("./data/output.json")
```

### cURL

```bash
# Create extraction
curl -X POST https://api.example.com/api/v1/extractions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "comp_abc123",
    "platforms": ["facebook", "instagram"]
  }'

# Check status
curl https://api.example.com/api/v1/extractions/job_xyz789 \
  -H "Authorization: Bearer $API_KEY"

# Download export
curl -O https://api.example.com/api/v1/exports/exp_def456/download \
  -H "Authorization: Bearer $API_KEY"
```
