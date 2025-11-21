# Data Models & Schemas

## Core Data Models

### 1. Company

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Company(BaseModel):
    id: Optional[int] = None
    name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime = datetime.utcnow()

    # Social media accounts
    social_accounts: List['SocialAccount'] = []

class SocialAccount(BaseModel):
    id: Optional[int] = None
    company_id: int
    platform: str  # facebook, instagram, twitter, linkedin, tiktok
    account_id: str  # Platform-specific ID
    username: str
    display_name: Optional[str] = None
    profile_url: str
    followers: Optional[int] = None
    verified: bool = False
    profile_picture_url: Optional[str] = None
```

### 2. Post

```python
from typing import Dict, Any
from enum import Enum

class MediaType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    REEL = "reel"
    STORY = "story"
    LINK = "link"

class Post(BaseModel):
    id: Optional[int] = None
    platform: str
    platform_id: str  # Original ID from platform

    # Content
    text: Optional[str] = None
    media_type: MediaType = MediaType.TEXT
    media_urls: List[str] = []

    # Metadata
    author_id: str
    published_at: datetime
    url: str

    # Engagement metrics
    likes: int = 0
    comments_count: int = 0
    shares: int = 0
    views: Optional[int] = None

    # Reactions breakdown (Facebook)
    reactions: Dict[str, int] = {}  # {like: 100, love: 50, ...}

    # Raw data for platform-specific fields
    raw_data: Dict[str, Any] = {}

    class Config:
        use_enum_values = True
```

### 3. Comment (Unified)

```python
class Comment(BaseModel):
    id: Optional[int] = None
    platform: str
    platform_id: str  # Original ID from platform
    post_id: int  # Reference to Post

    # Content
    text: str
    media_url: Optional[str] = None  # If comment has attachment

    # Author
    author_id: str
    author_username: str
    author_name: Optional[str] = None
    author_verified: bool = False
    author_profile_url: Optional[str] = None

    # Threading
    parent_id: Optional[int] = None  # For nested replies
    is_reply: bool = False

    # Metadata
    published_at: datetime

    # Engagement
    likes: int = 0
    replies_count: int = 0

    # Analysis results (populated after processing)
    sentiment: Optional['SentimentResult'] = None
    cluster_id: Optional[int] = None
    is_duplicate: bool = False
    duplicate_of: Optional[int] = None

    # Raw data
    raw_data: Dict[str, Any] = {}
```

### 4. Commenter Profile

```python
class CommenterProfile(BaseModel):
    id: Optional[int] = None

    # Identity (may have multiple per platform)
    platform_profiles: List['PlatformProfile'] = []

    # Aggregate metrics
    total_comments: int = 0
    total_likes_received: int = 0
    avg_likes_per_comment: float = 0.0

    # Behavior
    first_seen: datetime
    last_seen: datetime
    platforms_active: List[str] = []

    # Classification
    classification: str  # super_fan, frequent_positive, etc.
    influence_score: float = 0.0

    # Sentiment profile
    positive_ratio: float = 0.0
    negative_ratio: float = 0.0
    neutral_ratio: float = 0.0

    # Topics/issues
    primary_topics: List[str] = []
    primary_issues: List[str] = []

class PlatformProfile(BaseModel):
    platform: str
    user_id: str
    username: str
    display_name: Optional[str] = None
    profile_url: str
    verified: bool = False
    followers: Optional[int] = None
```

## Analysis Result Models

### 5. Sentiment Analysis

```python
class SentimentResult(BaseModel):
    comment_id: int
    label: str  # POS, NEG, NEU
    positive_score: float
    negative_score: float
    neutral_score: float
    confidence: float

    # Extended analysis
    emotions: Optional[Dict[str, float]] = None  # {joy: 0.8, anger: 0.1, ...}
    aspects: Optional[List[str]] = None  # Topics mentioned
    irony_detected: bool = False

class SentimentSummary(BaseModel):
    total_analyzed: int
    distribution: Dict[str, int]  # {positive: 100, negative: 50, neutral: 30}
    percentages: Dict[str, float]
    avg_confidence: float
    emotion_distribution: Optional[Dict[str, int]] = None
```

### 6. Comment Cluster

```python
class CommentCluster(BaseModel):
    id: int
    theme: str  # Human-readable theme
    representative_text: str  # Best example

    # Members
    comment_ids: List[int]
    count: int
    percentage_of_total: float

    # Aggregates
    sentiment: str
    avg_sentiment_score: float
    unique_authors: int

    # Keywords
    keywords: List[str]
    sample_comments: List[str]

    # Distribution
    platform_breakdown: Dict[str, int]  # {facebook: 100, instagram: 50}
    time_distribution: Dict[str, int]  # {2024-01-01: 10, 2024-01-02: 15}

    # Geographic (if detected)
    locations_mentioned: List[str] = []
```

### 7. Analysis Run

```python
class AnalysisRun(BaseModel):
    id: Optional[int] = None
    company_id: int

    # Scope
    platforms: List[str]
    date_range_start: datetime
    date_range_end: datetime

    # Status
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Counts
    total_posts: int = 0
    total_comments: int = 0
    unique_commenters: int = 0

    # Results
    sentiment_summary: Optional[SentimentSummary] = None
    clusters: List[CommentCluster] = []
    top_commenters: List[CommenterProfile] = []

    # Generated outputs
    outputs: Dict[str, str] = {}  # {csv: "/path/to/csv", pdf: "/path/to/pdf"}
```

## API Request/Response Models

### 8. Extraction Request

```python
class ExtractionRequest(BaseModel):
    company_name: str
    platforms: List[str]
    social_accounts: Dict[str, str]  # {facebook: "personalpy", instagram: "personalpy"}

    # Optional filters
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    max_posts: int = 100
    max_comments_per_post: int = 1000

class ExtractionResponse(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_completion: Optional[datetime] = None
```

### 9. Analysis Request

```python
class AnalysisRequest(BaseModel):
    job_id: str
    analysis_types: List[str] = ["sentiment", "clustering", "commenter"]

    # Clustering options
    similarity_threshold: float = 0.8
    min_cluster_size: int = 3

    # Sentiment options
    include_emotions: bool = True
    include_aspects: bool = False

class AnalysisResponse(BaseModel):
    job_id: str
    analysis_id: int
    status: str
    results_url: Optional[str] = None
```

### 10. Report Request

```python
class ReportRequest(BaseModel):
    analysis_id: int
    formats: List[str] = ["json", "csv", "pdf"]
    include_visualizations: bool = True

    # PDF report options
    executive_summary: bool = True
    detailed_clusters: bool = True
    commenter_profiles: bool = True

class ReportResponse(BaseModel):
    analysis_id: int
    files: Dict[str, str]  # {json: "url", csv: "url", pdf: "url"}
    dashboard_url: Optional[str] = None
```

## Transformation Schemas

### Platform to Unified Comment

```python
class FacebookCommentAdapter:
    @staticmethod
    def to_unified(fb_data: dict, post_id: int) -> Comment:
        return Comment(
            platform="facebook",
            platform_id=fb_data['id'],
            post_id=post_id,
            text=fb_data.get('message', ''),
            author_id=fb_data['from']['id'],
            author_username=fb_data['from']['name'],
            published_at=datetime.fromisoformat(fb_data['created_time'].replace('Z', '+00:00')),
            likes=fb_data.get('like_count', 0),
            replies_count=fb_data.get('comment_count', 0),
            parent_id=fb_data.get('parent', {}).get('id'),
            raw_data=fb_data
        )

class InstagramCommentAdapter:
    @staticmethod
    def to_unified(ig_data: dict, post_id: int) -> Comment:
        return Comment(
            platform="instagram",
            platform_id=ig_data['id'],
            post_id=post_id,
            text=ig_data['text'],
            author_id=ig_data.get('user_id', ig_data.get('owner_id', '')),
            author_username=ig_data.get('username', ''),
            published_at=datetime.fromisoformat(ig_data['timestamp'].replace('Z', '+00:00')),
            likes=ig_data.get('like_count', 0),
            replies_count=ig_data.get('reply_count', 0),
            raw_data=ig_data
        )

class TwitterCommentAdapter:
    @staticmethod
    def to_unified(tw_data: dict, post_id: int) -> Comment:
        return Comment(
            platform="twitter",
            platform_id=tw_data['id'],
            post_id=post_id,
            text=tw_data['text'],
            author_id=tw_data['author_id'],
            author_username=tw_data.get('author', {}).get('username', ''),
            published_at=datetime.fromisoformat(tw_data['created_at'].replace('Z', '+00:00')),
            likes=tw_data.get('public_metrics', {}).get('like_count', 0),
            replies_count=tw_data.get('public_metrics', {}).get('reply_count', 0),
            raw_data=tw_data
        )
```

## Export Schemas

### CSV Export Schema

```python
CSV_COMMENT_COLUMNS = [
    'comment_id',
    'platform',
    'post_id',
    'text',
    'author_id',
    'author_username',
    'published_at',
    'likes',
    'replies_count',
    'sentiment_label',
    'sentiment_positive',
    'sentiment_negative',
    'sentiment_neutral',
    'cluster_id',
    'cluster_theme'
]

CSV_COMMENTER_COLUMNS = [
    'commenter_id',
    'username',
    'platforms',
    'total_comments',
    'avg_likes',
    'positive_ratio',
    'negative_ratio',
    'classification',
    'influence_score',
    'first_seen',
    'last_seen'
]
```

### JSON Export Structure

```python
JSON_EXPORT_SCHEMA = {
    "metadata": {
        "company": str,
        "generated_at": datetime,
        "date_range": {"start": datetime, "end": datetime},
        "platforms": List[str],
        "totals": {
            "posts": int,
            "comments": int,
            "commenters": int
        }
    },
    "sentiment_summary": SentimentSummary,
    "clusters": List[CommentCluster],
    "top_commenters": List[CommenterProfile],
    "comments": List[Comment],
    "posts": List[Post]
}
```

## Validation Rules

```python
from pydantic import validator

class Comment(BaseModel):
    # ... fields ...

    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Comment text cannot be empty')
        return v.strip()

    @validator('published_at')
    def not_future_date(cls, v):
        if v > datetime.utcnow():
            raise ValueError('Published date cannot be in the future')
        return v

    @validator('likes', 'replies_count')
    def non_negative(cls, v):
        if v < 0:
            raise ValueError('Count cannot be negative')
        return v

class SentimentResult(BaseModel):
    @validator('positive_score', 'negative_score', 'neutral_score')
    def valid_probability(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v
```
