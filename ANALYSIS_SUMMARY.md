# CODEBASE ANALYSIS SUMMARY

## Project Overview
- **Name**: Social Media Comment Extractor
- **Purpose**: Extract posts and comments from Facebook, Instagram, and other platforms
- **Language**: Python 3.10+
- **Architecture**: Modular, registry-based with multiple design patterns

## Directory Structure

```
src/
├── browser/           - Playwright browser lifecycle management
├── cli/              - CLI implementations (main.py, __main__.py)
├── config/           - Settings (settings.py) & Constants (constants.py)
├── core/             - Data models (models.py) & Exceptions (exceptions.py)
├── exporters/        - JSON, CSV, JSONL exporters + registry
├── pages/            - Page Object Model base + Facebook-specific pages
├── scrapers/         - Platform scrapers (Facebook, Instagram)
├── services/         - ExtractionService orchestrator
├── storage/          - Data persistence (JSON, CSV, SQLite, Excel)
└── utils/            - Helper functions (delays, parsing, retry)
```

## Key Entry Points

1. **extract.py** (399 lines) - Root CLI entry point
   - Most used but has architectural issues
   
2. **src/cli/main.py** - Newer CLI (recommended)
   - Better designed with ExtractionService
   
3. **scripts/extract.py** - Alternative entry point

## Core Data Models (src/core/models.py)

- **Platform** enum: facebook, instagram, twitter, linkedin, tiktok
- **Author**: username, display_name, is_verified
- **Post**: platform_id, text, likes, comments_count, shares
- **Comment**: text, author, likes, replies_count, parent_id
- **ExtractionResult**: post + list of comments
- **ExtractionStats**: tracking metrics
- **ClientConfig/SocialAccount**: account management
- **ExportMetadata**: export tracking

## Configuration (src/config/)

**settings.py**:
- Pydantic BaseSettings with environment variable support
- FacebookSettings: email, password, cookies_file
- InstagramSettings: username, password, session_file
- ProxySettings: proxy list with rotation
- Methods: get_platform_config(), validate_all(), setup_logging()

**constants.py**:
- TimeoutConfig: page load, element visibility, delays
- HumanDelayConfig: typing, actions, breaks
- BrowserConfig: viewport, user agents, anti-detection args
- ScrapingConfig: limits, scroll settings, breaks

## Architecture Patterns

1. **Registry Pattern**: ScraperRegistry, ExporterRegistry
   - Add new platforms/formats without code changes
   
2. **Template Method**: BaseScraper
   - Base class handles logging, delays, errors
   - Subclasses implement _scrape_posts(), _scrape_profile()
   
3. **Page Object Model**: Instagram scraper
   - pages/: LoginPage, ProfilePage, PostModal, CommentsSection
   - Clean separation of locators and logic
   
4. **Service Layer**: ExtractionService
   - Orchestrates scrapers, storage, exporters
   
5. **Adapter Pattern**: StorageBackend
   - JSON, CSV, SQLite, Excel implementations

## Data Flow

```
CLI Arguments
    ↓
Initialize (settings, scraper, config)
    ↓
Scrape (for each platform):
  - Browser automation via Playwright
  - Human-like delays (0.5-1.0s normal, 3-5s breaks every 20 requests)
  - Yield ExtractionResult(post + comments)
    ↓
Load Existing Data (combined.json)
    ↓
Merge (deduplicate by post ID, combine comments)
    ↓
Export (save posts.json, comments.json, combined.json)
    ↓
Print Summary
```

## High-Priority Issues

1. **Duplicate Instagram Scraper** (HIGH)
   - instagram_playwright.py (2077 lines legacy)
   - instagram/scraper.py (new POM-based)
   - Both do same thing → remove legacy
   
2. **Mixed Responsibilities in extract.py** (HIGH)
   - Contains export logic that should be in ExtractionService
   - Hardcoded platform imports instead of using registry
   - JSON-only export instead of using ExporterRegistry
   - Data merging logic duplicated
   
3. **Inconsistent Entry Points** (MEDIUM)
   - Three entry points (extract.py, src/cli/main.py, scripts/extract.py)
   - No clear "official" one
   - Different features in each
   
4. **No Validation of Scraper Output** (MEDIUM)
   - Raw data goes directly to export
   - No data quality checks
   
5. **Incomplete Type Hints** (LOW-MEDIUM)
   - Missing return types
   - Dict[str, Any] instead of specific types

## Design Strengths

✓ Clear data models with Pydantic validation  
✓ Registry pattern for extensibility  
✓ Sophisticated human-like behavior (delays, breaks, proxy rotation)  
✓ Comprehensive error handling with custom exceptions  
✓ Extensive logging throughout  
✓ Flexible Pydantic-based configuration  
✓ Modular architecture with clear separation  
✓ Incremental data updates (deduplication)  
✓ Platform abstraction (same interface for all)  
✓ Storage abstraction (JSON, CSV, SQLite, Excel)  

## Test Coverage

- **test_cli.py**: CLI tests
- **test_storage.py**: Storage backend tests
- **test_utils.py**: Utility function tests

**Gaps**: No tests for scrapers, exporters, browser interactions, POM classes

## Refactoring Roadmap

**Phase 1 (1-2 days)**: Consolidate entry points
- Choose official entry point
- Merge features
- Deprecate others

**Phase 2 (2-3 days)**: Fix extract.py duplication
- Move logic to ExtractionService
- Use registry for platforms
- Support all export formats

**Phase 3 (1 day)**: Remove duplicate Instagram scraper
- Keep POM version
- Delete legacy version

**Phase 4 (3-5 days)**: Improve test coverage
- Unit tests for scrapers, exporters, storage
- Integration tests
- Aim for 80%+ coverage

**Phase 5 (1-2 days)**: Type hints & linting
- Complete type coverage
- Run mypy --strict
- Add py.typed marker

**Phase 6 (1-2 days)**: Documentation
- Update README
- Add architecture diagrams
- Document patterns

**Total: 2-3 weeks**

## Key Files for Refactoring

**Hub modules** (modify carefully):
- extract.py
- src/cli/main.py
- src/services/extraction.py
- src/scrapers/registry.py

**Core dependencies** (changes ripple):
- src/core/models.py
- src/core/exceptions.py
- src/config/settings.py

**Isolated modules** (safe to modify):
- src/exporters/json_exporter.py
- src/utils/delays.py
- src/storage/json_storage.py

## Dependencies

```
pydantic>=2.0.0           # Data validation
pydantic-settings>=2.0.0  # Environment config
playwright>=1.40.0       # Browser automation
pytest>=7.0.0            # Testing
pytest-asyncio>=0.21.0   # Async tests
pytest-cov>=4.0.0        # Coverage
```

Optional:
```
fastapi>=0.100.0         # REST API (commented out)
uvicorn>=0.22.0          # ASGI server (commented out)
```

## Conclusion

Well-structured application with good architectural patterns. Main improvements needed:
1. Consolidate entry points
2. Remove duplicate code
3. Improve test coverage
4. Complete type hints

Ready for refactoring with clear path forward.
