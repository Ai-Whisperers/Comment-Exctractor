# Comment-Extractor: Comprehensive Architecture Analysis

## EXECUTIVE SUMMARY

Production-grade social media scraping system with Playwright browser automation, supporting 5 platforms (Facebook, Instagram, Twitter, LinkedIn, Google), with modular registry-based architecture.

**Current State**: Single-account extraction, manual URL input  
**Target State**: Multi-company management with centralized account registry  
**Key Finding**: Existing ClientConfig/SocialAccount models designed for multi-company but unused  
**Implementation Effort**: 8-9 days following established patterns  

---

## PROJECT STRUCTURE

```
src/
├── core/models.py               (12 Pydantic models, including unused ClientConfig)
├── config/settings.py           (470 lines, platform credentials)
├── scrapers/                    (5 platforms, registry-based auto-registration)
├── exporters/                   (JSON, CSV, JSONL, Excel)
├── storage/                     (Data persistence backends)
├── services/extraction.py       (Orchestration layer - needs company integration)
└── cli/main.py                  (CLI interface)

config/
├── env.example                  (Environment variable template)
├── personal-paraguay.json       (Example company config - currently UNUSED)
└── companies.json              (NEW - recommended company registry)

data/
└── exports/                     (Extracted data - currently flat by account)
```

---

## SUPPORTED PLATFORMS

| Platform | Auth | Status | Data |
|----------|------|--------|------|
| Facebook | Email/Password | Implemented | Posts, Comments, Profile |
| Instagram | Username/Password | Implemented | Posts, Comments, Profile |
| Twitter | Username/Password or Google OAuth | Implemented | Tweets, Replies, Profile |
| LinkedIn | Email/Password | Implemented | Posts, Comments, Profile |
| Google | Public (no auth) | Implemented | Reviews, Profile |

---

## HOW URLs/TARGETS ARE CURRENTLY SPECIFIED

**Current Methods**:

1. **CLI Arguments** (most common):
   ```bash
   python extract.py --account personalpy --platforms instagram
   ```
   Limitations: Only username, single account, no company mapping

2. **Environment Variables**:
   ```bash
   EXTRACTOR_FACEBOOK__EMAIL=user@example.com
   ```
   Limitations: Hard to manage multiple accounts

3. **Credential Manager Script**:
   ```bash
   python scripts/manage_credentials.py store facebook email user@example.com
   ```
   Limitations: Not company-linked

**Problem**: No centralized company-to-account mapping system

---

## EXISTING FOUNDATION FOR MULTI-COMPANY

**Models that already exist in src/core/models.py**:

```python
class SocialAccount(BaseModel):
    platform: Platform
    identifier: str
    display_name: Optional[str]
    enabled: bool = True

class ClientConfig(BaseModel):
    name: str
    accounts: List[SocialAccount]
    created_at: datetime
    
    def get_accounts_by_platform(self, platform):
        return [a for a in self.accounts if a.platform == platform]
```

**Status**: Models exist but ExtractionService never uses them

---

## REGISTRY PATTERN (Architecture Strength)

System successfully uses Factory/Registry pattern:

**ScraperRegistry**:
```python
scraper = ScraperRegistry.get("instagram", config)
```

**ExporterRegistry**:
```python
exporter = ExporterRegistry.get("csv")
```

**Recommendation**: Follow same pattern for CompanyRegistry

---

## RECOMMENDED IMPLEMENTATION

### 1. Extend Data Models (src/core/models.py)

```python
class CompanyAccount(BaseModel):
    platform: Platform
    identifier: str
    url: Optional[str]              # NEW
    display_name: Optional[str]
    enabled: bool = True
    max_posts: int = 100            # NEW
    requests_per_minute: Optional[int]  # NEW

class Company(BaseModel):
    id: str
    name: str
    description: Optional[str]
    enabled: bool = True
    accounts: List[CompanyAccount]
    tags: List[str]
    created_at: datetime
```

### 2. Create CompanyRegistryManager (src/core/company_registry.py)

```python
class CompanyRegistryManager:
    def load(self) -> CompanyRegistry
    def get_company(self, company_id: str)
    def get_company_accounts(self, company_id: str, platform=None)
    def validate(self) -> Dict[str, List[str]]
```

### 3. Configuration File (config/companies.json)

```json
{
  "version": "1.0",
  "companies": [
    {
      "id": "personal-py",
      "name": "Personal Paraguay",
      "enabled": true,
      "tags": ["telecom", "latin-america"],
      "accounts": [
        {
          "platform": "facebook",
          "identifier": "personalpy",
          "url": "https://www.facebook.com/personalpy",
          "enabled": true,
          "max_posts": 100
        }
      ]
    }
  ]
}
```

### 4. Integrate with ExtractionService

Add methods:
```python
def extract_company(self, company_id: str, platforms=None)
def batch_extract(self, company_ids=None, tags=None)
```

### 5. New CLI Commands

```bash
python -m src.cli.main list-companies
python -m src.cli.main extract-company personal-py
python -m src.cli.main batch-extract --tags telecom
```

### 6. Multi-Company Output Structure

```
data/exports/
├── personal-py/
│   ├── company_metadata.json
│   ├── facebook/personalpy/
│   │   ├── posts.json
│   │   ├── comments.json
│   │   └── profile.json
│   └── instagram/personalpy/
│       └── ...
```

---

## IMPLEMENTATION TIMELINE

| Phase | Days | Work | Lines |
|-------|------|------|-------|
| 1: Core Models | 2 | Models, Registry Manager, Config | +280 |
| 2: Integration | 2 | ExtractionService, CLI | +350 |
| 3: Output | 2 | Organize by company, reports | +150 |
| 4: Testing | 1-2 | Unit & integration tests | +350 |
| 5: Docs | 1 | Guides, examples | 3 docs |
| **TOTAL** | **8-9** | | **+1130** |

---

## KEY RECOMMENDATIONS

**DO:**
✓ Use existing ClientConfig/SocialAccount models as foundation
✓ Store companies in JSON (version-controlled)
✓ Follow ScraperRegistry pattern
✓ Create company-organized output
✓ Support batch extraction
✓ Keep backward compatibility

**DON'T:**
✗ Store companies in .env
✗ Embed credentials in registry
✗ Modify BaseScraper
✗ Use database for registry

---

## SECURITY DESIGN

**Company Registry** (JSON, public):
- No passwords
- Public account identifiers/URLs
- Company metadata

**Credentials** (.env, secret):
- Email/passwords stored separately
- One set per platform
- Shared across accounts

---

## CURRENT STATE ASSESSMENT

| Aspect | Status |
|--------|--------|
| Single-Account Extraction | ✓ Working |
| Multi-Platform | ✓ Working |
| Multi-Company Support | ✗ Missing |
| Company Models | ⚠ Unused |
| Output Organization | ⚠ Flat |
| Extensibility | ✓ Good |

---

## CONCLUSION

Well-architected production system. Main gap is multi-company management. 
Solution is JSON-based company registry following established patterns. 
Implementation effort: 8-9 days.

---
Generated: November 21, 2025
