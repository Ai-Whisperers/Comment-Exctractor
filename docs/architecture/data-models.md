# Data Models & Schemas

## Overview

All data models are defined using Pydantic v2 in `src/core/models.py`. Models use `ConfigDict(extra="allow")` to preserve platform-specific fields in `raw_data`.

## Core Data Models

### 1. Platform (Enum)

```python
class Platform(str, Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
```

### 2. Author

Represents the author of a comment or post.

```python
class Author(BaseModel):
    """Comment author information."""
    model_config = ConfigDict(extra="allow")

    platform_id: Optional[str] = None      # Platform-specific user ID
    username: Optional[str] = None         # @handle or username
    display_name: Optional[str] = None     # Full name
    profile_url: Optional[str] = None      # Link to profile
    profile_image: Optional[str] = None    # Avatar URL
    is_verified: bool = False              # Blue checkmark
    followers_count: Optional[int] = None  # Number of followers
```

### 3. Post

Represents a social media post.

```python
class Post(BaseModel):
    """Social media post."""
    model_config = ConfigDict(extra="allow")

    # Identification
    platform: Platform                     # Which platform
    platform_id: str                       # Platform's unique ID
    account_id: str                        # Account username/ID
    url: Optional[str] = None              # Direct link to post

    # Content
    text: Optional[str] = None             # Post text/caption
    media_type: Optional[str] = None       # text, image, video, carousel
    media_urls: List[str] = Field(default_factory=list)

    # Timestamps
    published_at: Optional[datetime] = None

    # Engagement metrics
    likes: int = 0
    comments_count: int = 0
    shares: int = 0

    # Platform-specific data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
```

### 4. Comment

Represents a comment on a post. Includes text validation.

```python
class Comment(BaseModel):
    """Social media comment."""
    model_config = ConfigDict(extra="allow")

    # Identification
    platform: Platform
    platform_id: str                       # Platform's unique comment ID
    post_id: str                           # Parent post ID

    # Content
    text: str                              # Comment text (validated)

    # Author
    author: Author                         # Who wrote it

    # Timestamps
    published_at: Optional[datetime] = None

    # Engagement
    likes: int = 0
    replies_count: int = 0

    # Threading
    parent_id: Optional[str] = None        # For nested replies

    # Reserved for AI analyzer
    sentiment_score: Optional[float] = None

    # Platform-specific data
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Clean and normalize comment text."""
        if v:
            # Remove null characters and normalize whitespace
            v = v.replace("\x00", "").strip()
        return v
```

### 5. Profile

Represents a social media account/page profile.

```python
class Profile(BaseModel):
    """Social media profile/page information."""
    model_config = ConfigDict(extra="allow")

    # Identification
    platform: Platform
    platform_id: str                       # Platform's unique ID
    username: str                          # @handle
    display_name: Optional[str] = None     # Full name
    description: Optional[str] = None      # Bio
    url: Optional[str] = None              # Profile URL

    # Images
    profile_image: Optional[str] = None
    cover_image: Optional[str] = None

    # Metrics
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0

    # Status
    is_verified: bool = False
    created_at: Optional[datetime] = None

    # Platform-specific data
    raw_data: Dict[str, Any] = Field(default_factory=dict)
```

### 6. ExtractionResult

Container for a post and its comments (yielded by scrapers).

```python
class ExtractionResult(BaseModel):
    """Result of extracting a single post with its comments."""
    post: Post
    comments: List[Comment] = Field(default_factory=list)
```

### 7. ExtractionStats

Statistics for tracking extraction progress.

```python
class ExtractionStats(BaseModel):
    """Statistics for an extraction job."""

    # Context
    client: str
    platform: str
    account: str

    # Counters
    posts_scraped: int = 0
    comments_found: int = 0
    new_comments_saved: int = 0
    duplicates_skipped: int = 0
    errors: List[str] = Field(default_factory=list)

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get extraction duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None
```

## Configuration Models

### 8. SocialAccount

Configuration for a social media account to scrape.

```python
class SocialAccount(BaseModel):
    """Social media account configuration for a client."""
    platform: Platform
    identifier: str           # username, page ID, or URL
    display_name: Optional[str] = None
    enabled: bool = True
```

### 9. ClientConfig

Client with multiple social accounts.

```python
class ClientConfig(BaseModel):
    """Client configuration with social accounts."""
    name: str
    accounts: List[SocialAccount] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def get_accounts_by_platform(self, platform: Platform) -> List[SocialAccount]:
        """Get all accounts for a specific platform."""
        return [a for a in self.accounts if a.platform == platform and a.enabled]
```

### 10. ExportMetadata

Metadata included in exported files.

```python
class ExportMetadata(BaseModel):
    """Metadata for exported data."""
    client: str
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    format: str                            # json, csv, excel
    total_comments: int = 0
    platforms: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    version: str = "1.0"
```

## Protocol Interfaces

Defined in `src/core/protocols.py` using `typing.Protocol`.

### ScraperProtocol

```python
@runtime_checkable
class ScraperProtocol(Protocol):
    """Protocol for platform scrapers."""

    platform: Platform

    def get_posts_with_comments(
        self,
        account_id: str,
        since_date: Optional[datetime] = None,
        max_posts: int = 100,
        known_post_ids: Optional[set] = None
    ) -> Iterator[ExtractionResult]:
        """Get posts with their comments from an account."""
        ...

    def get_profile(self, account_id: str) -> Profile:
        """Get profile information for an account."""
        ...

    def get_comments(
        self,
        post_id: str,
        max_comments: int = 1000
    ) -> Iterator[Comment]:
        """Get comments for a specific post."""
        ...

    def close(self) -> None:
        """Clean up resources."""
        ...

    def __enter__(self) -> "ScraperProtocol":
        """Context manager entry."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit with cleanup."""
        ...
```

### StorageProtocol

```python
class StorageProtocol(Protocol):
    """Protocol for data storage backends."""

    def save_comment(self, client: str, comment: Comment) -> bool:
        """Save a comment (returns True if new, False if duplicate)."""
        ...

    def save_post(self, client: str, post: Post) -> bool:
        """Save a post (returns True if new, False if duplicate)."""
        ...

    def save_profile(self, client: str, profile: Profile) -> bool:
        """Save a profile."""
        ...

    def get_comments(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Comment]:
        """Get comments from storage with filters."""
        ...

    def get_posts(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Post]:
        """Get posts from storage with filters."""
        ...

    def get_last_extraction_date(
        self,
        client: str,
        platform: str,
        account_id: str
    ) -> Optional[datetime]:
        """Get the date of the last extraction for an account."""
        ...
```

### ExporterProtocol

```python
class ExporterProtocol(Protocol):
    """Protocol for data exporters."""

    format: str

    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """Export comments to a file."""
        ...

    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """Export posts to a file."""
        ...
```

## Browser Configuration

### BrowserConfig (Dataclass)

```python
@dataclass
class BrowserConfig:
    """Configuration for browser creation."""
    headless: bool = False
    profile_dir: Optional[str] = None      # Persistent profile
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 800})
    user_agent: Optional[str] = None       # Random if None
    storage_state: Optional[str] = None    # Session JSON path
    browser_args: List[str] = field(default_factory=lambda: BROWSER_ARGS.copy())
    proxy: Optional[str] = None            # Proxy URL
```

## Exception Classes

Defined in `src/core/exceptions.py`.

```python
class ExtractionError(Exception):
    """Base exception for extraction errors."""
    def __init__(self, message: str, platform: Optional[str] = None):
        self.message = message
        self.platform = platform

class ScraperError(ExtractionError):
    """Error during scraping."""
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        account_id: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        ...

class RateLimitError(ScraperError):
    """Rate limit exceeded error."""
    retry_after: int = 60

class AuthenticationError(ScraperError):
    """Authentication failed error."""

class AccountNotFoundError(ScraperError):
    """Account/page not found."""

class PrivateAccountError(ScraperError):
    """Account is private and cannot be scraped."""

class StorageError(ExtractionError):
    """Error during storage operations."""
    operation: Optional[str] = None

class ExportError(ExtractionError):
    """Error during export."""
    format: Optional[str] = None

class ConfigurationError(ExtractionError):
    """Configuration error."""
    setting: Optional[str] = None

class ValidationError(ExtractionError):
    """Data validation error."""
    field: Optional[str] = None
```

## Settings Models

Defined in `src/config/settings.py`.

### ProxySettings

```python
class ProxySettings(BaseModel):
    """Proxy configuration settings."""
    enabled: bool = False
    urls: List[str] = Field(default_factory=list)
    rotate_on_error: bool = True

    @field_validator('urls')
    @classmethod
    def validate_proxy_urls(cls, v: List[str]) -> List[str]:
        """Validate proxy URL formats (http, https, socks4, socks5)."""
        ...
```

### Platform Settings

```python
class ScraperSettings(BaseModel):
    """Base settings for a scraper."""
    enabled: bool = True
    requests_per_minute: int = 30
    max_retries: int = 3
    proxies: ProxySettings = Field(default_factory=ProxySettings)

class FacebookSettings(ScraperSettings):
    email: Optional[str] = None
    password: Optional[str] = None
    cookies_file: Optional[str] = None
    pages_per_request: int = 10

class InstagramSettings(ScraperSettings):
    username: Optional[str] = None
    password: Optional[str] = None
    session_file: Optional[str] = None
    requests_per_minute: int = 15

class TwitterSettings(ScraperSettings):
    username: Optional[str] = None
    password: Optional[str] = None
    requests_per_minute: int = 20

class LinkedInSettings(ScraperSettings):
    email: Optional[str] = None
    password: Optional[str] = None
    requests_per_minute: int = 10
```

### Main Settings

```python
class Settings(BaseSettings):
    """Main application settings."""

    # General
    app_name: str = "Comment Extractor"
    debug: bool = False
    log_level: str = "INFO"

    # Paths
    data_dir: str = "data"
    exports_dir: str = "data/exports"
    logs_dir: str = "logs"

    # Database
    database_path: str = "data/extractor.db"

    # Extraction defaults
    default_max_posts: int = 100
    default_export_format: str = "json"

    # Platform settings
    facebook: FacebookSettings = Field(default_factory=FacebookSettings)
    instagram: InstagramSettings = Field(default_factory=InstagramSettings)
    twitter: TwitterSettings = Field(default_factory=TwitterSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )
```

## Data Serialization

### Post to Dictionary

```python
@staticmethod
def post_to_dict(post: Post) -> Dict[str, Any]:
    return {
        "platform_id": post.platform_id,
        "account_id": post.account_id,
        "text": post.text,
        "likes": post.likes,
        "comments_count": post.comments_count,
        "shares": post.shares,
        "url": post.url,
        "media_type": post.media_type,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "platform": post.platform.value,
    }
```

### Comment to Dictionary

```python
@staticmethod
def comment_to_dict(comment: Comment) -> Dict[str, Any]:
    return {
        "platform_id": comment.platform_id,
        "post_id": comment.post_id,
        "author": {
            "platform_id": comment.author.platform_id,
            "username": comment.author.username,
            "display_name": comment.author.display_name,
            "is_verified": comment.author.is_verified,
        } if comment.author else None,
        "text": comment.text,
        "likes": comment.likes,
        "parent_id": comment.parent_id,
        "replies_count": comment.replies_count,
        "published_at": comment.published_at.isoformat() if comment.published_at else None,
        "platform": comment.platform.value,
    }
```

## Export Formats

### JSON Structure

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
        "platform": "instagram",
        "platform_id": "ig_12345",
        "account_id": "personalpy",
        "url": "https://instagram.com/p/...",
        "text": "Post caption here",
        "published_at": "2024-11-15T10:30:00Z",
        "likes": 450,
        "comments_count": 25,
        "shares": 0,
        "media_type": "image"
      },
      "comments": [
        {
          "platform": "instagram",
          "platform_id": "ig_comment_987",
          "post_id": "ig_12345",
          "text": "Great post!",
          "author": {
            "platform_id": "ig_user_555",
            "username": "john_doe",
            "display_name": "John Doe",
            "is_verified": false
          },
          "published_at": "2024-11-15T11:00:00Z",
          "likes": 5,
          "parent_id": null,
          "replies_count": 1
        }
      ]
    }
  ]
}
```

### CSV Columns

**Comments CSV**:
```
platform_id, post_id, platform, text, author_username, author_display_name,
author_verified, published_at, likes, parent_id, replies_count
```

**Posts CSV**:
```
platform_id, account_id, platform, text, url, published_at,
likes, comments_count, shares, media_type
```

## Validation Rules

### Text Cleaning

- Remove null characters (`\x00`)
- Strip leading/trailing whitespace
- Normalize internal whitespace

### Timestamp Parsing

Supports multiple formats:
- ISO 8601: `2024-11-21T18:51:00Z`
- ISO 8601 with microseconds: `2024-11-21T18:51:00.000Z`
- Custom: `2024-11-21 18:51:00`

### Platform ID Generation

Format: `{platform}_{original_id}`

Examples:
- Facebook post: `fb_123456789`
- Instagram comment: `ig_comment_987654321`
- Twitter reply: `tw_reply_555444333`

## Type Safety

All models use strict typing:
- `Optional[T]` for nullable fields
- `List[T]` for arrays
- `Dict[str, Any]` for raw platform data
- `datetime` for timestamps (not strings)
- `int` for counts (not strings)

Models are `@runtime_checkable` for protocol validation.
