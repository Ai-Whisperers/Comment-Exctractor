# Social Media Comment Extractor - Documentation

## Overview

Complete documentation for the Social Media Comment Extractor project. This system extracts data from multiple social media platforms using **Playwright browser automation** and exports it in formats suitable for external AI analysis.

**Scope**: Data extraction only. Sentiment analysis, clustering, and visualization are handled by a separate AI analyzer project.

**Technology Stack**:
- **Playwright** - Browser automation for all scraping (more reliable than APIs)
- **Pydantic** - Data validation and settings management
- **SQLite** - Local storage for incremental extraction
- **Python 3.10+** - Core language

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd comment-extractor

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Create a `.env` file with your credentials:

```env
# Instagram
EXTRACTOR_INSTAGRAM__USERNAME=your_username
EXTRACTOR_INSTAGRAM__PASSWORD=your_password

# Facebook
EXTRACTOR_FACEBOOK__EMAIL=your_email@example.com
EXTRACTOR_FACEBOOK__PASSWORD=your_password

# General settings
EXTRACTOR_LOG_LEVEL=INFO
EXTRACTOR_DEFAULT_MAX_POSTS=100
```

### Basic Usage

```python
from src.config.settings import get_settings
from src.scrapers.registry import ScraperRegistry

# Get settings
settings = get_settings()

# Get scraper for Instagram
config = settings.get_platform_config('instagram')
scraper = ScraperRegistry.get('instagram', config)

# Extract posts and comments
for result in scraper.get_posts_with_comments('personalpy', max_posts=10):
    print(f"Post: {result.post.platform_id}")
    print(f"Comments: {len(result.comments)}")

# Cleanup
scraper.close()
```

## Architecture

### Playwright-Based Scraping

All scrapers use Playwright browser automation instead of APIs:

**Advantages**:
- Uses real browser - harder to detect as bot
- No API rate limits or authentication issues
- Works with any public content
- Human-like interaction patterns built-in

**Anti-Detection Features**:
- User-Agent rotation (11 browser signatures)
- Randomized delays (5-15 seconds)
- Periodic breaks (30-60 seconds)
- Extended pauses (2-5 minutes)
- Session cookie persistence
- Stealth browser settings

### Supported Platforms

| Platform | Status | Scraper |
|----------|--------|---------|
| Instagram | Active | `InstagramPlaywrightScraper` |
| Facebook | Active | `FacebookPlaywrightScraper` |
| Twitter/X | Planned | Not yet implemented |

### Data Flow

```
Browser (Playwright)
    ↓
Scraper (platform-specific)
    ↓
Models (Pydantic validation)
    ↓
Storage (SQLite)
    ↓
Export (JSON/CSV/JSONL)
```

## Documentation Index

### Architecture

System design and technical specifications.

| Document | Description |
|----------|-------------|
| [Project Architecture](architecture/project-architecture.md) | System overview, tech stack |
| [Data Models](architecture/data-models.md) | Pydantic schemas, transformations |
| [Database Schema](architecture/database-schema.md) | SQLite tables, indexes |
| [Extraction Workflow](architecture/extraction-workflow.md) | Detailed extraction pipeline |

### Development

Implementation guides for developers.

| Document | Description |
|----------|-------------|
| [Configuration](development/configuration.md) | Environment variables, settings |
| [Error Handling](development/error-handling.md) | Retry strategies, circuit breakers |
| [Rate Limiting](development/rate-limiting.md) | Human-like delays, anti-detection |
| [Data Validation](development/data-validation.md) | Quality checks, cleansing |
| [Testing Strategy](development/testing-strategy.md) | Unit, integration, E2E tests |

### Test Case

| Document | Description |
|----------|-------------|
| [Personal Paraguay](test-case/personal-paraguay.md) | Complete test case with telecom company |

## Project Structure

```
comment-extractor/
├── src/
│   ├── core/
│   │   ├── models.py          # Pydantic data models
│   │   ├── protocols.py       # Abstract interfaces
│   │   └── exceptions.py      # Custom exceptions
│   ├── scrapers/
│   │   ├── base.py            # Base scraper with anti-detection
│   │   ├── instagram_playwright.py  # Instagram browser scraper
│   │   ├── facebook_playwright.py   # Facebook browser scraper
│   │   └── registry.py        # Scraper registry
│   ├── storage/
│   │   └── sqlite.py          # SQLite storage
│   ├── exporters/
│   │   ├── json_exporter.py
│   │   ├── csv_exporter.py
│   │   └── jsonl_exporter.py
│   ├── services/
│   │   └── extraction.py      # Extraction orchestration
│   └── config/
│       └── settings.py        # Pydantic settings
├── scripts/
│   └── extract.py             # CLI entry point
├── data/                      # SQLite DB and exports
├── docs/                      # Documentation
├── tests/                     # Test suite
├── requirements.txt
└── .env                       # Credentials (not in git)
```

## Anti-Detection System

The scraper includes comprehensive anti-detection measures:

### Timing Patterns

```python
# Normal requests: 5-15 second random delay
# Every 5 requests: 30-60 second break
# Every 20 requests: 2-5 minute break
# Every hour: 5-15 minute extended break
```

### Browser Stealth

- Randomized User-Agent from 11 modern browsers
- Realistic viewport and locale settings
- Disabled webdriver detection
- Session cookie persistence
- Proxy support (optional)

### Best Practices

1. **Don't scrape too fast** - Human-like delays are enforced
2. **Use authenticated sessions** - Better access to content
3. **Rotate proxies if needed** - For heavy usage
4. **Limit daily volume** - 2-3 hours max per session
5. **Vary scraping times** - Don't always run at same time

## Export Formats

### JSON (Default)

```json
{
  "profile": {...},
  "posts": [...],
  "comments": [...],
  "metadata": {
    "extracted_at": "2024-01-15T10:30:00Z",
    "platform": "instagram"
  }
}
```

### CSV

Flat format for spreadsheet analysis.

### JSONL

One JSON object per line, ideal for streaming/ML pipelines.

## Contributing

1. Follow existing code patterns
2. Include type hints
3. Write tests for new features
4. Update documentation

## License

MIT License
