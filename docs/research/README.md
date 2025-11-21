# Social Media Comment Extractor - Research Documentation

## Overview

This documentation contains comprehensive research for building a social media comment extraction and analysis system. The project will extract data from multiple social media platforms for a given company, analyze comments for sentiment and patterns, condense similar comments, and generate actionable insights.

## Test Case: Personal Paraguay

The telecom company **Personal Paraguay** is used as the primary test case:
- **Facebook**: 495,428 followers
- **Instagram**: 110,000 followers
- **LinkedIn**: 60,674 followers
- **Expected monthly comments**: 8,000 - 45,000

## Documentation Structure

```
docs/
├── research/
│   ├── platforms/              # Platform-specific API research
│   │   ├── facebook.md         # Facebook Graph API
│   │   ├── instagram.md        # Instagram Graph API
│   │   ├── twitter-x.md        # Twitter/X API v2
│   │   ├── linkedin.md         # LinkedIn Marketing API
│   │   ├── tiktok.md           # TikTok extraction methods
│   │   └── platform-comparison.md
│   │
│   ├── algorithms/             # Analysis algorithms
│   │   ├── comment-deduplication.md   # Clustering & dedup
│   │   ├── sentiment-analysis.md      # NLP sentiment
│   │   └── commenter-analysis.md      # User profiling
│   │
│   └── outputs/                # Output formats
│       └── output-formats.md   # CSV, JSON, PDF, dashboards
│
├── architecture/               # System design
│   ├── project-architecture.md # Full architecture
│   └── data-models.md          # Data schemas
│
└── test-case/                  # Test implementation
    └── personal-paraguay.md    # Test case details
```

## Key Findings

### Data Extraction

| Platform | Best Method | Cost | Difficulty |
|----------|-------------|------|------------|
| Facebook | Graph API + Apify | $1.50/1K | Medium |
| Instagram | Apify (API limited) | $2.30/1K | High |
| Twitter/X | Apify (API expensive) | $0.20/1K | Medium |
| LinkedIn | Apify (API restricted) | $1.20/1K | High |
| TikTok | Apify only | $0.20/1K | Medium |

**Estimated monthly cost**: $3-75 depending on volume

### Analysis Capabilities

1. **Sentiment Analysis**
   - Spanish-optimized models (pysentimiento)
   - Emotion detection (joy, anger, sadness)
   - Aspect-based sentiment

2. **Comment Deduplication**
   - Jaccard similarity
   - Sentence embeddings + cosine similarity
   - MinHash LSH for scalability

3. **Commenter Profiling**
   - Classification (super_fan, frequent_negative, etc.)
   - Influence scoring
   - Cross-platform tracking

### Output Formats

- **Raw Data**: JSON, CSV, Parquet
- **Reports**: PDF, HTML
- **Visualizations**: Charts, word clouds, heatmaps
- **Interactive**: Streamlit dashboard
- **API**: RESTful endpoints

## Technology Stack

### Core
- Python 3.10+
- PostgreSQL / MongoDB
- Redis (caching)
- Celery (async tasks)

### NLP
- pysentimiento (Spanish sentiment)
- sentence-transformers (embeddings)
- scikit-learn (clustering)
- BERTopic (topic modeling)

### Visualization
- Plotly
- Streamlit
- ReportLab (PDFs)

### APIs
- FastAPI
- Apify client

## Development Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Setup | 1 week | Project structure, DB |
| Extractors | 2 weeks | All platforms |
| Analysis | 2 weeks | Sentiment, clustering |
| Reports | 1 week | All output formats |
| Dashboard | 1 week | Interactive UI |
| Testing | 1 week | Full test suite |
| **Total** | **8 weeks** | Production-ready |

## Quick Start (Planned)

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with API keys

# Run extraction
python -m src.main extract --company "Personal Paraguay"

# Run analysis
python -m src.main analyze --job-id <job_id>

# Generate report
python -m src.main report --job-id <job_id> --format pdf

# Launch dashboard
streamlit run src/reporters/dashboard.py
```

## Expected Results for Personal Paraguay

Based on telecom industry patterns:

### Sentiment Distribution
- **Positive**: 25-30% (promotions, improvements)
- **Negative**: 50-55% (complaints dominate)
- **Neutral**: 20-25% (inquiries)

### Top Issue Clusters
1. Internet speed problems (15-20%)
2. Coverage issues (10-15%)
3. Billing complaints (8-12%)
4. Customer service (5-8%)
5. App issues (3-5%)

### Commenter Types
- Super fans: 1-2%
- Frequent positive: 5-8%
- Frequent negative: 4-6%
- Occasional: 20-25%
- One-time: 60-70%

## Legal Considerations

1. **Terms of Service**: Review each platform's ToS
2. **Data Privacy**: GDPR/CCPA compliance
3. **Personal Data**: Anonymize when possible
4. **Retention**: Implement data retention policies
5. **Usage**: Document data usage purposes

## Next Steps

1. Review platform documentation in `research/platforms/`
2. Understand data models in `architecture/data-models.md`
3. Study algorithms in `research/algorithms/`
4. Check test case details in `test-case/personal-paraguay.md`
5. Begin implementation based on `architecture/project-architecture.md`

## Contact

For questions about this research, contact the development team.

---

*Last updated: 2024*
