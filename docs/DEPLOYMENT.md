# Deployment Guide

This guide covers deploying the Comment Extractor system for production use.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running Extractions](#running-extractions)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)

---

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 4GB RAM (8GB recommended for large extractions)
- **Storage**: Sufficient space for SQLite database and exports

### Browser Requirements

The scraper uses Playwright for browser automation:

```bash
# Install Playwright browsers after pip install
playwright install chromium
```

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd Comment-Exctractor
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Verify Installation

```bash
python -c "from src.core import Container; print('Installation successful!')"
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Facebook credentials
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Instagram credentials (if using)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Optional: Browser settings
HEADLESS=true
BROWSER_PROFILE=./data/browser_profile

# Optional: Proxy configuration
PROXY_ENABLED=false
PROXY_URLS=http://proxy1:8080,http://proxy2:8080
```

### Client Configuration

Create client configuration files in `config/clients/`:

```yaml
# config/clients/acme.yaml
name: acme
accounts:
  - platform: facebook
    identifier: AcmeCorp
    enabled: true
  - platform: instagram
    identifier: acmecorp
    enabled: true
```

### Application Settings

Edit `config/settings.yaml` for global settings:

```yaml
extraction:
  max_posts_per_account: 100
  rate_limit_delay_seconds: 5
  retry_attempts: 3

storage:
  database_path: ./data/extractor.db

export:
  default_format: json
  output_directory: ./data/exports
```

---

## Running Extractions

### Using the CLI

```bash
# Extract from a single account
python scripts/extract_companies.py \
  --companies acme \
  --platforms facebook \
  --max-posts 50

# Extract from multiple platforms
python scripts/extract_companies.py \
  --companies acme \
  --platforms facebook,instagram \
  --max-posts 100

# Full re-extraction (ignore previous dates)
python scripts/extract_companies.py \
  --companies acme \
  --platforms facebook \
  --max-posts 100 \
  --full

# Run in visible browser mode (for debugging)
python scripts/extract_companies.py \
  --companies acme \
  --platforms facebook \
  --max-posts 20 \
  --no-headless
```

### Using the Container (Programmatic)

```python
from src.core import Container, get_container

# Create container
container = Container()

# Get extraction service
service = container.extraction_service()

# Run extraction
stats = service.extract(
    client="acme",
    platform="facebook",
    account_id="AcmeCorp",
    max_posts=100,
)

print(f"Extracted {stats.posts_scraped} posts, {stats.new_comments_saved} comments")

# Export results
export_path = service.export(
    client="acme",
    format="json",
    platform="facebook",
)
print(f"Exported to: {export_path}")

# Cleanup
container.close()
```

### Scheduled Extractions

For automated daily extractions, create a scheduled task:

**Windows Task Scheduler:**

```cmd
schtasks /create /tn "Comment Extraction" /tr "C:\path\to\venv\Scripts\python.exe C:\path\to\scripts\extract_companies.py --companies acme --platforms facebook --max-posts 100" /sc daily /st 02:00
```

**Linux cron:**

```bash
# Add to crontab (crontab -e)
0 2 * * * /path/to/venv/bin/python /path/to/scripts/extract_companies.py --companies acme --platforms facebook --max-posts 100 >> /var/log/extractor.log 2>&1
```

---

## Monitoring

### Using the Event Bus

```python
from src.core import EventBus, EventType, get_event_bus

# Get global event bus
bus = get_event_bus()

# Subscribe to progress events
def on_progress(event):
    print(f"Progress: {event.data}")

bus.subscribe(EventType.PROGRESS_UPDATE, on_progress)

# Subscribe to errors
def on_error(event):
    print(f"ERROR: {event.data.get('error')}")

bus.subscribe(EventType.ERROR_OCCURRED, on_error)
```

### Logging Configuration

Configure logging in your extraction script:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler()
    ]
)
```

### Extraction Statistics

After extraction, review statistics:

```python
from src.core import Container

container = Container()
service = container.extraction_service()

# Get client stats
stats = service.get_stats("acme")
print(f"Total comments: {stats['total_comments']}")
print(f"Total posts: {stats['total_posts']}")
print(f"Platforms: {stats['platforms']}")

container.close()
```

---

## Troubleshooting

### Common Issues

#### 1. Login Failed

```
AuthenticationError: Login failed
```

**Solutions:**
- Verify credentials in `.env` file
- Check if Facebook requires two-factor authentication
- Try running in non-headless mode to see the login flow:
  ```bash
  python scripts/extract_companies.py --no-headless ...
  ```

#### 2. Rate Limiting

```
RateLimitError: Facebook rate limit detected
```

**Solutions:**
- Reduce extraction frequency
- Use proxies (configure in `.env`)
- Implement longer delays between requests

#### 3. Element Not Found

```
TimeoutError: Element not found
```

**Solutions:**
- Facebook may have updated their UI
- Check selectors in `src/scrapers/facebook/selectors.py`
- Try running in non-headless mode to debug

#### 4. Database Locked

```
OperationalError: database is locked
```

**Solutions:**
- Only run one extraction at a time
- Check for stale lock files
- Increase SQLite timeout

### Debug Mode

Enable debug HTML logging:

```python
from src.utils.html_debug_logger import set_debug_client

set_debug_client("acme")
# Now HTML snapshots are saved to data/debug/
```

### Checking Logs

Review logs in these locations:
- Application logs: `extraction.log`
- Debug HTML: `data/debug/{client}/`

---

## Security Considerations

### Credential Storage

- **Never commit `.env` files** to version control
- Use environment variables in production
- Consider using a secrets manager (AWS Secrets Manager, HashiCorp Vault)

### Proxy Usage

For high-volume extraction, use rotating proxies:

```env
PROXY_ENABLED=true
PROXY_URLS=http://user:pass@proxy1:8080,http://user:pass@proxy2:8080
```

### Rate Limiting

Respect platform rate limits:
- Don't extract too frequently (daily is usually safe)
- Use reasonable delays between requests
- Monitor for rate limit warnings

### Data Protection

- Store extracted data securely
- Follow GDPR/privacy regulations for personal data
- Implement data retention policies

---

## Production Checklist

Before deploying to production:

- [ ] Configure credentials in environment variables
- [ ] Set up client configurations
- [ ] Test extraction in non-headless mode
- [ ] Configure logging
- [ ] Set up monitoring/alerts
- [ ] Create backup strategy for database
- [ ] Document extraction schedule
- [ ] Test export functionality
- [ ] Set up scheduled tasks
- [ ] Configure proxies (if needed)

---

## Architecture Overview

```
Comment-Exctractor/
├── src/
│   ├── core/              # Core models, container, events
│   ├── scrapers/          # Platform-specific scrapers
│   ├── storage/           # Storage backends (SQLite)
│   ├── exporters/         # Export formats (JSON, CSV)
│   └── services/          # Business logic (ExtractionService)
├── config/
│   ├── clients/           # Client configurations
│   └── settings.yaml      # Global settings
├── data/
│   ├── extractor.db       # SQLite database
│   ├── exports/           # Exported files
│   └── debug/             # Debug HTML snapshots
├── scripts/               # CLI scripts
└── tests/                 # Test suite
```

### Key Components

1. **Container**: Dependency injection container for managing services
2. **ExtractionService**: Main orchestrator for scraping and storage
3. **EventBus**: Publish/subscribe for monitoring
4. **Scrapers**: Platform-specific scraping logic
5. **Storage**: SQLite backend for persistence

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs for error details
3. Open an issue on the repository

---

## Version History

- **v1.0**: Initial release with Facebook and Instagram support
- **v1.1**: Added DI Container and Event Bus
