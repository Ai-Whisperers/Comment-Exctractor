"""Pydantic models for the comment extractor."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Platform(str, Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    GOOGLE = "google"  # Google Reviews / Google Business


class Author(BaseModel):
    """Comment author information."""
    model_config = ConfigDict(extra="allow")

    platform_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    profile_image: Optional[str] = None
    is_verified: bool = False
    followers_count: Optional[int] = None


class Post(BaseModel):
    """Social media post."""
    model_config = ConfigDict(extra="allow")

    platform: Platform
    platform_id: str
    account_id: str
    url: Optional[str] = None
    text: Optional[str] = None
    published_at: Optional[datetime] = None
    likes: int = 0
    comments_count: int = 0
    shares: int = 0
    media_type: Optional[str] = None  # text, image, video, etc.
    media_urls: List[str] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class Comment(BaseModel):
    """Social media comment."""
    model_config = ConfigDict(extra="allow")

    platform: Platform
    platform_id: str
    post_id: str
    text: str
    author: Author
    published_at: Optional[datetime] = None
    likes: int = 0
    replies_count: int = 0
    parent_id: Optional[str] = None  # For nested replies
    sentiment_score: Optional[float] = None  # Reserved for AI analyzer
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Clean and normalize comment text."""
        if v:
            # Remove null characters and normalize whitespace
            v = v.replace("\x00", "").strip()
        return v


class Profile(BaseModel):
    """Social media profile/page information."""
    model_config = ConfigDict(extra="allow")

    platform: Platform
    platform_id: str
    username: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    profile_image: Optional[str] = None
    cover_image: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_verified: bool = False
    created_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Result of extracting a single post with its comments."""
    post: Post
    comments: List[Comment] = Field(default_factory=list)


class ExtractionStats(BaseModel):
    """Statistics for an extraction job."""
    client: str
    platform: str
    account: str
    posts_scraped: int = 0
    comments_found: int = 0
    new_comments_saved: int = 0
    duplicates_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
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


class SocialAccount(BaseModel):
    """Social media account configuration for a client."""
    platform: Platform
    identifier: str  # username, page ID, or URL
    display_name: Optional[str] = None
    enabled: bool = True


class ClientConfig(BaseModel):
    """Client configuration with social accounts."""
    name: str
    accounts: List[SocialAccount] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def get_accounts_by_platform(self, platform: Platform) -> List[SocialAccount]:
        """Get all accounts for a specific platform."""
        return [a for a in self.accounts if a.platform == platform and a.enabled]


class ExportMetadata(BaseModel):
    """Metadata for exported data."""
    client: str
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    format: str
    total_comments: int = 0
    platforms: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    version: str = "1.0"
