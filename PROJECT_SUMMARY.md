# Social Media Comment Extractor - Project Summary

## Project Scope

**This project is DATA EXTRACTION ONLY.**

The system will:
1. **Receive** company name and social media links
2. **Extract** all available data (profile, posts, comments)
3. **Normalize** data into unified schema
4. **Export** structured data for external AI analysis

**NOT in scope** (handled by separate AI analyzer project):
- Sentiment analysis
- Topic clustering
- Commenter profiling algorithms
- Visualizations/dashboards

## Test Case: Personal Paraguay

Paraguay's major telecom company with:
- **Facebook**: 495,428 followers (@personalpy)
- **Instagram**: 110,000 followers (@personalpy)
- **LinkedIn**: 60,674 followers
- **Twitter**: @personalpy

## What Data Will Be Extracted?

### Per Platform

| Data Type | Facebook | Instagram | Twitter | LinkedIn |
|-----------|----------|-----------|---------|----------|
| Profile info | Yes | Yes | Yes | Yes |
| Posts | Yes | Yes | Yes | Yes |
| Comments | Yes | Yes | Yes | Yes |
| Replies | Yes | Yes | Yes | Yes |
| Likes/Reactions | Yes | Yes | Yes | Yes |
| Shares | Yes | No | Yes | Yes |
| Author info | Partial | Partial | Partial | Partial |

### Data Points Per Comment
- Comment ID & text
- Platform source
- Post ID (parent)
- Author (ID, username, name, verified status)
- Timestamp
- Engagement (likes, replies count)
- Parent comment ID (for threads)
- Media attachments
- Raw platform data

## Output Formats

The extractor outputs data ready for AI processing:

### Primary: JSON
```json
{
  "export_metadata": {
    "company": "Personal Paraguay",
    "extraction_date": "2024-01-31T10:30:00Z",
    "platforms": ["facebook", "instagram", "twitter"],
    "totals": {
      "posts": 150,
      "comments": 15000,
      "unique_commenters": 8500
    }
  },
  "comments": [
    {
      "id": "fb_123456789_987654321",
      "platform": "facebook",
      "post_id": "fb_123456789",
      "text": "El internet está muy lento",
      "author": {
        "id": "user_444555666",
        "username": "juan_perez",
        "display_name": "Juan Perez"
      },
      "timestamp": "2024-01-15T11:45:00Z",
      "likes": 5,
      "replies_count": 2
    }
  ]
}
```

### Also Available
- **CSV** - Flat tabular format
- **JSONL** - One comment per line (streaming)
- **Parquet** - Columnar format for big data

## Technical Approach

### Extraction Methods

**Recommended: Apify (Third-Party)**
- Works on public pages
- No authentication required
- Reliable and maintained

| Platform | Cost per 1,000 comments |
|----------|------------------------|
| Facebook | $1.50 |
| Instagram | $2.30 |
| Twitter | $0.20 |
| LinkedIn | $1.20 |
| TikTok | $0.20 |

**Alternative: Official APIs**
- Require authentication and permissions
- Limited to accounts you manage
- Free within rate limits

### Technology Stack

- **Language**: Python 3.10+
- **APIs**: requests, httpx, apify-client
- **Database**: PostgreSQL
- **Cache**: Redis
- **Export**: orjson, pandas

## Project Architecture

```
┌─────────────────────────────────────────┐
│     Social Media Comment Extractor       │
├─────────────────────────────────────────┤
│  Facebook │ Instagram │ Twitter │ etc.  │
│  Extractor│ Extractor │Extractor│       │
└─────────────┬───────────────────────────┘
              │
     ┌────────▼────────┐
     │ Data Normalizer │
     │ (Unified Schema)│
     └────────┬────────┘
              │
     ┌────────▼────────┐
     │  Data Storage   │
     │   (Database)    │
     └────────┬────────┘
              │
     ┌────────▼────────┐
     │  Data Exporter  │
     └────────┬────────┘
              │
    ┌─────┬───┴───┬─────┐
    │     │       │     │
   CSV   JSON   JSONL   API
              │
              ▼
    ┌─────────────────┐
    │ External AI     │
    │ Analyzer        │
    │ (Separate Proj) │
    └─────────────────┘
```

## Directory Structure

```
comment-extractor/
├── src/
│   ├── extractors/       # Platform extractors
│   │   ├── facebook.py
│   │   ├── instagram.py
│   │   ├── twitter.py
│   │   └── linkedin.py
│   ├── models/           # Data schemas
│   ├── storage/          # Database & cache
│   ├── exporters/        # Output generators
│   └── api/              # FastAPI endpoints
├── data/
│   ├── raw/              # Raw API responses
│   └── output/           # Exported files
└── docs/                 # Documentation
```

## Estimated Volume for Personal Paraguay

| Metric | Monthly Low | Monthly High |
|--------|-------------|--------------|
| Facebook comments | 5,000 | 30,000 |
| Instagram comments | 2,000 | 10,000 |
| Twitter replies | 1,000 | 5,000 |
| LinkedIn comments | 100 | 500 |
| **Total** | **8,100** | **45,500** |

## Estimated Costs

### Monthly Infrastructure
- Database (managed): $20-50
- Compute: $20-50
- Redis cache: $10-20
- **Subtotal**: $50-120

### Third-Party Data (Apify)
- Based on volume: $50-100/month

### Total Monthly: $100-220

## Development Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Setup | Project structure, database |
| 2-3 | Extractors | All platform integrations |
| 4 | Storage | Data pipeline, caching |
| 5 | Export | JSON, CSV, JSONL formats |
| 6 | API | FastAPI endpoints |

**Total: 6 weeks to production**

## Integration with AI Analyzer

The extractor outputs will feed into your separate AI analyzer project:

```
Extractor → JSON/CSV → AI Analyzer → Results
```

### What AI Analyzer Will Do (separate project)
- Sentiment analysis (positive/negative/neutral)
- Emotion detection
- Topic clustering
- Comment deduplication
- Commenter profiling
- Visualization & dashboards

## Documentation Structure

```
docs/
├── research/
│   ├── platforms/          # API details per platform
│   ├── algorithms/         # Deduplication methods
│   └── outputs/            # Export format specs
├── architecture/           # System design
└── test-case/              # Personal Paraguay details
```

## Next Steps

1. **Review API docs**: `docs/research/platforms/`
2. **Set up environment**: Python, database, API keys
3. **Test Facebook extraction** (highest volume)
4. **Add remaining platforms**
5. **Implement exporters**

---

**Ready to start? Check the architecture at:**
`docs/architecture/project-architecture.md`
