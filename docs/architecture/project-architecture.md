# Social Media Comment Extractor - Project Architecture

## System Overview

```
+-------------------------------------------------------------------+
|              Social Media Comment Extractor                        |
|              (Data Extraction Only - Playwright-based)             |
+-------------------------------------------------------------------+
|                                                                    |
|  +------------+  +------------+  +------------+  +------------+    |
|  | Facebook   |  | Instagram  |  | Twitter/X  |  | LinkedIn   |    |
|  | Scraper    |  | Scraper    |  | Scraper    |  | Scraper    |    |
|  | (POM)      |  | (POM)      |  |            |  |            |    |
|  +-----+------+  +-----+------+  +-----+------+  +-----+------+    |
|        |              |              |              |               |
|        +------+-------+------+-------+------+-------+               |
|               |              |              |                       |
|        +------v------+  +----v-----+  +-----v------+               |
|        | Browser     |  | Rate     |  | Session    |               |
|        | Manager     |  | Limiter  |  | Handler    |               |
|        +------+------+  +----+-----+  +-----+------+               |
|               |              |              |                       |
|               +------+-------+------+-------+                       |
|                      |                                              |
|               +------v------+                                       |
|               | BaseScraper |                                       |
|               | (Template)  |                                       |
|               +------+------+                                       |
|                      |                                              |
|               +------v------+                                       |
|               | ExtractionResult                                    |
|               | (Post + Comments)                                   |
|               +------+------+                                       |
|                      |                                              |
|        +-------------+-------------+                                |
|        |             |             |                                |
|  +-----v---+   +-----v---+   +-----v---+                           |
|  |  JSON   |   |   CSV   |   |  Excel  |                           |
|  | Storage |   | Storage |   | Storage |                           |
|  +---------+   +---------+   +---------+                           |
|                      |                                              |
|                      v                                              |
|        +--------------------------+                                 |
|        |  External AI Analyzer    |                                 |
|        |  (Separate Project)      |                                 |
|        +--------------------------+                                 |
+-------------------------------------------------------------------+
```

## Technology Stack

### Core
- **Language**: Python 3.10+
- **Package Manager**: pip
- **Data Validation**: Pydantic 2.0+
- **Configuration**: pydantic-settings with .env support

### Data Extraction
- **Browser Automation**: Playwright (primary method)
- **Rate Limiting**: Custom implementation with exponential backoff
- **Proxy Support**: HTTP/HTTPS/SOCKS4/SOCKS5

### Data Storage
- **Primary**: JSON files (incremental updates)
- **Alternative**: CSV, Excel, SQLite
- **Session Persistence**: Playwright storage state

### Data Export
- **Formats**: JSON, CSV, JSONL, Excel
- **Serialization**: Built-in JSON with Pydantic

## Project Structure (Current)

```
comment-extractor/
+-- src/
|   +-- __init__.py
|   +-- browser/                    # Browser lifecycle management
|   |   +-- __init__.py
|   |   +-- manager.py              # BrowserManager (deprecated, use shared)
|   |   +-- session.py              # Session persistence
|   |
|   +-- cli/                        # Command-line interfaces
|   |   +-- __init__.py
|   |   +-- main.py                 # CLI using ExtractionService
|   |
|   +-- config/                     # Configuration management
|   |   +-- __init__.py
|   |   +-- settings.py             # Pydantic Settings with env support
|   |
|   +-- core/                       # Core domain models
|   |   +-- __init__.py
|   |   +-- models.py               # Pydantic models (Post, Comment, etc.)
|   |   +-- protocols.py            # Abstract interfaces (ScraperProtocol)
|   |   +-- exceptions.py           # Custom exceptions
|   |   +-- validation.py           # Data validation utilities
|   |
|   +-- exporters/                  # Data export formatters
|   |   +-- __init__.py
|   |   +-- base.py                 # BaseExporter abstract class
|   |   +-- json_exporter.py
|   |   +-- csv_exporter.py
|   |   +-- jsonl_exporter.py
|   |   +-- registry.py             # ExporterRegistry
|   |
|   +-- scrapers/                   # Platform-specific scrapers
|   |   +-- __init__.py
|   |   +-- base.py                 # BaseScraper with common logic
|   |   +-- registry.py             # ScraperRegistry
|   |   +-- facebook/
|   |   |   +-- scraper.py          # FacebookScraper (POM-based)
|   |   |   +-- selectors.py        # CSS selectors
|   |   |   +-- pages/              # Page objects
|   |   |       +-- login_page.py
|   |   |       +-- post_page.py
|   |   |       +-- comments_section.py
|   |   +-- instagram/
|   |   |   +-- scraper.py          # InstagramScraper (POM-based)
|   |   |   +-- selectors.py
|   |   |   +-- pages/
|   |   |       +-- login_page.py
|   |   |       +-- profile_page.py
|   |   |       +-- post_modal.py
|   |   |       +-- comments_section.py
|   |   +-- twitter/
|   |   |   +-- scraper.py          # TwitterScraper
|   |   |   +-- pages/
|   |   +-- linkedin/
|   |   |   +-- scraper.py          # LinkedInScraper
|   |   |   +-- pages/
|   |   +-- shared/                 # Shared scraper utilities
|   |       +-- browser_manager.py  # Centralized BrowserManager
|   |       +-- rate_limiting.py    # Platform-specific rate limit detection
|   |       +-- constants.py        # Timeouts, user agents, viewports
|   |       +-- base_page.py        # Base page object class
|   |
|   +-- services/                   # Business logic orchestration
|   |   +-- __init__.py
|   |   +-- extraction.py           # ExtractionService
|   |
|   +-- storage/                    # Data persistence backends
|   |   +-- __init__.py
|   |   +-- base.py                 # StorageBackend abstract class
|   |   +-- json_storage.py
|   |   +-- csv_storage.py
|   |   +-- excel_storage.py
|   |   +-- sqlite.py
|   |
|   +-- utils/                      # Utility functions
|       +-- __init__.py
|       +-- parsing.py              # DateTime parsing
|       +-- security.py             # Credential masking
|       +-- output_paths.py         # Path management
|       +-- html_debug_logger.py    # Debug HTML snapshots
|
+-- extract.py                      # Main CLI entry point
+-- scripts/                        # Utility scripts
|   +-- extract_comments.py
|   +-- extract_facebook_personalpy.py
|   +-- extract_instagram_personalpy.py
|
+-- tests/                          # Test suite
|   +-- test_cli.py
|   +-- test_storage.py
|   +-- test_exporters.py
|   +-- test_rate_limiting.py
|   +-- test_browser_manager.py
|   +-- test_utils.py
|
+-- config/                         # Configuration files
|   +-- personal-paraguay.json      # Test case config
|
+-- docs/                           # Documentation
|   +-- architecture/
|   +-- research/
|   +-- development/
|
+-- data/                           # Data directory (gitignored)
|   +-- exports/                    # Exported data
|   +-- sessions/                   # Browser sessions
|   +-- browser_profiles/           # Persistent browser profiles
|   +-- checkpoints/                # Extraction checkpoints
|
+-- requirements.txt
+-- .env                            # Environment configuration
+-- .gitignore
+-- README.md
```

## Architecture Patterns

### 1. Registry Pattern
Pluggable components without code modification:
- **ScraperRegistry**: Dynamically loads platform scrapers
- **StorageFactory**: Creates storage backends
- **ExporterRegistry**: Export format handlers

### 2. Page Object Model (POM)
Clean separation between page interactions and business logic (Instagram & Facebook):
- **LoginPage**: Authentication handling
- **ProfilePage**: Profile data extraction
- **PostModal/PostPage**: Post details extraction
- **CommentsSection**: Comment extraction and pagination

### 3. Template Method Pattern
`BaseScraper` provides common functionality:
- Human-like delay simulation
- Rate limiting with exponential backoff
- Proxy rotation
- Session statistics
- Error handling and recovery

### 4. Protocol-based Interfaces
`ScraperProtocol`, `StorageProtocol`, `ExporterProtocol` define contracts:
- Runtime checkable
- Enables dependency injection
- Facilitates testing

## Data Flow

### Extraction Pipeline

```
CLI Input (extract.py)
    |
    v
Initialize Settings & Logger
    |
    v
Get Scraper from Registry
    |
    v
Initialize BrowserManager (Playwright)
    |
    +-- Persistent Profile (cookies preserved)
    +-- OR Storage State (session JSON)
    |
    v
For Each Platform:
    |
    +-- Authenticate (if needed)
    |   +-- Check existing session
    |   +-- Login if required
    |   +-- Save session state
    |
    +-- Navigate to Profile
    |
    +-- PHASE 1: Collect Post Links
    |   +-- Scroll profile grid
    |   +-- Filter known post IDs
    |   +-- Apply max_posts limit
    |
    +-- PHASE 2: Extract Each Post
    |   +-- Navigate to post URL
    |   +-- Extract post metadata
    |   +-- Extract comments (paginated)
    |   +-- Create ExtractionResult
    |   +-- Yield result
    |
    +-- Apply Human-like Delays
        +-- 0.5-1.0s between requests
        +-- 3-5s break every 20 requests
        +-- 10-20s break every 100 requests
    |
    v
Load Existing Data (combined.json)
    |
    v
Merge New + Existing
    +-- Deduplicate by post ID
    +-- Combine comments (union)
    +-- Update metadata
    |
    v
Export to Storage Backend
    +-- posts.{format}
    +-- comments.{format}
    +-- combined.json
    |
    v
Print Summary Statistics
```

### Anti-Detection Measures

1. **Random User Agents**: Rotates through 10+ realistic browser UAs
2. **Random Viewports**: Desktop, tablet, and mobile sizes
3. **Human-like Delays**: Variable timing with jitter
4. **Periodic Breaks**: Simulates natural browsing patterns
5. **Quiet Hours**: Avoids 2-6 AM scraping
6. **Proxy Rotation**: Rotates on errors
7. **Session Persistence**: Reuses authentication

## Configuration

### Environment Variables

```bash
# General
EXTRACTOR_DEBUG=false
EXTRACTOR_LOG_LEVEL=INFO

# Paths
EXTRACTOR_DATA_DIR=data
EXTRACTOR_EXPORTS_DIR=data/exports

# Database (SQLite)
EXTRACTOR_DATABASE_PATH=data/extractor.db

# Extraction defaults
EXTRACTOR_DEFAULT_MAX_POSTS=100
EXTRACTOR_DEFAULT_EXPORT_FORMAT=json

# Facebook settings
EXTRACTOR_FACEBOOK__ENABLED=true
EXTRACTOR_FACEBOOK__EMAIL=your_email
EXTRACTOR_FACEBOOK__PASSWORD=your_password
EXTRACTOR_FACEBOOK__REQUESTS_PER_MINUTE=20

# Instagram settings
EXTRACTOR_INSTAGRAM__ENABLED=true
EXTRACTOR_INSTAGRAM__USERNAME=your_username
EXTRACTOR_INSTAGRAM__PASSWORD=your_password
EXTRACTOR_INSTAGRAM__REQUESTS_PER_MINUTE=15

# Twitter settings
EXTRACTOR_TWITTER__ENABLED=true
EXTRACTOR_TWITTER__USERNAME=your_username
EXTRACTOR_TWITTER__PASSWORD=your_password
EXTRACTOR_TWITTER__REQUESTS_PER_MINUTE=25

# LinkedIn settings
EXTRACTOR_LINKEDIN__ENABLED=true
EXTRACTOR_LINKEDIN__EMAIL=your_email
EXTRACTOR_LINKEDIN__PASSWORD=your_password
EXTRACTOR_LINKEDIN__REQUESTS_PER_MINUTE=10

# Proxy Configuration (optional)
EXTRACTOR_INSTAGRAM__PROXIES__ENABLED=true
EXTRACTOR_INSTAGRAM__PROXIES__URLS=["http://proxy1:8080","http://proxy2:8080"]
```

### Settings Hierarchy

```python
Settings (BaseSettings)
+-- General
|   +-- app_name: str
|   +-- debug: bool
|   +-- log_level: str
+-- Paths
|   +-- data_dir: str
|   +-- exports_dir: str
|   +-- logs_dir: str
+-- Database
|   +-- database_path: str
+-- Extraction
|   +-- default_max_posts: int
|   +-- default_export_format: str
+-- Platform Settings
    +-- FacebookSettings
    |   +-- email, password, cookies_file
    |   +-- pages_per_request
    |   +-- requests_per_minute
    |   +-- proxies: ProxySettings
    +-- InstagramSettings
    |   +-- username, password, session_file
    |   +-- requests_per_minute
    |   +-- proxies: ProxySettings
    +-- TwitterSettings
    +-- LinkedInSettings
```

## Supported Platforms

| Platform    | Status | Method               | Auth Type          | Features                          |
|-------------|--------|----------------------|--------------------|-----------------------------------|
| **Facebook**| Active | Playwright (POM)     | Email/Password     | Posts, Comments, Reactions        |
| **Instagram**| Active | Playwright (POM)     | Username/Password  | Posts, Comments, Likes            |
| **Twitter/X**| Active | Playwright           | Cookie-based       | Tweets, Replies                   |
| **LinkedIn**| Active | Playwright           | Email/Password     | Posts, Comments                   |
| **TikTok**  | Planned| Playwright           | Username/Password  | Videos, Comments                  |

## Rate Limiting

### Platform-Specific Limits

| Platform  | Requests/Min | Long Pause | Very Long Pause |
|-----------|--------------|------------|-----------------|
| Facebook  | 20           | Every 20   | Every 100       |
| Instagram | 15           | Every 20   | Every 100       |
| Twitter   | 25           | Every 20   | Every 100       |
| LinkedIn  | 10           | Every 20   | Every 100       |

### Rate Limit Detection

Each platform has specific indicators:

**Facebook**:
- URL patterns: `/checkpoint/`, `/accounts/suspended`
- Text: "temporarily blocked", "try again later"

**Instagram**:
- URL patterns: `/challenge/`, `/accounts/suspended`
- Text: "action blocked", "suspicious activity"

**Twitter**:
- Text: "rate limit exceeded", "over capacity"

**LinkedIn**:
- URL patterns: `/checkpoint/`, `/authwall`
- Text: "unusual activity", "security verification"

## Error Handling

### Exception Hierarchy

```
ExtractionError (base)
+-- ScraperError
|   +-- RateLimitError
|   +-- AuthenticationError
|   +-- AccountNotFoundError
|   +-- PrivateAccountError
+-- StorageError
+-- ExportError
+-- ConfigurationError
+-- ValidationError
```

### Recovery Strategies

1. **Exponential Backoff**: 2^n * base_delay with jitter
2. **Proxy Rotation**: Switch proxy on persistent errors
3. **Session Refresh**: Re-login on session expiry
4. **Checkpointing**: Resume from last successful post

## Output Structure

```
data/exports/{account}/{platform}/{YYYY-MM}/
+-- {account}_{platform}_posts_{timestamp}.json
+-- {account}_{platform}_comments_{timestamp}.json
+-- combined.json  # Incremental updates
```

### Combined JSON Format

```json
{
  "metadata": {
    "account": "personalpy",
    "last_updated": "2024-11-21T18:51:00Z",
    "created_at": "2024-11-20T19:00:00Z",
    "total_posts": 150,
    "total_comments": 5000,
    "platforms": ["instagram", "facebook"]
  },
  "extractions": [
    {
      "post": {
        "platform_id": "...",
        "text": "...",
        "likes": 450,
        "comments_count": 25
      },
      "comments": [...]
    }
  ]
}
```

## Dependencies

### Core (Required)
```
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
playwright>=1.40.0
```

### Testing
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
```

### Optional
```
openpyxl>=3.1.0           # Excel export
fastapi>=0.100.0          # REST API
uvicorn>=0.22.0           # ASGI server
```

## Test Coverage

**Current Tests**:
- CLI argument parsing
- Storage backend implementations
- Export format conversions
- Rate limit detection
- Browser manager lifecycle
- Utility functions

**Gaps**:
- Scraper integration tests
- Page Object Model tests
- End-to-end extraction tests
- Authentication flow tests

## Security Considerations

1. **Credential Masking**: SensitiveFilter in logging
2. **No Hardcoded Secrets**: All via environment variables
3. **Session Files Protected**: Outside git, in data/ directory
4. **Proxy Credentials Hidden**: Masked in logs

## Performance Estimates

### Extraction Speed
- **Instagram**: ~2-3 posts/minute with comments
- **Facebook**: ~3-4 posts/minute with comments
- **Twitter**: ~4-5 posts/minute with comments

### Data Volume (Personal Paraguay)
- **Monthly Comments**: 8,000-45,000 across all platforms
- **Storage**: ~10-50 MB/month (JSON)
