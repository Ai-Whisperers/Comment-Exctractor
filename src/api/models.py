"""Pydantic models for API request/response."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ExtractionRequest(BaseModel):
    """Request to start an extraction."""
    client: str = Field(..., description="Client name")
    platform: str = Field(..., description="Platform (facebook, instagram, etc.)")
    account_id: str = Field(..., description="Account username or ID")
    max_posts: int = Field(100, ge=1, le=10000, description="Maximum posts to extract")
    full: bool = Field(False, description="Full re-extraction (ignore last date)")


class ExportRequest(BaseModel):
    """Request to export data."""
    client: str = Field(..., description="Client name")
    format: str = Field("json", description="Export format (json, csv, jsonl)")
    platform: Optional[str] = Field(None, description="Filter by platform")
    since: Optional[datetime] = Field(None, description="Start date filter")
    until: Optional[datetime] = Field(None, description="End date filter")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ExtractionStats(BaseModel):
    """Extraction statistics."""
    client: str
    platform: str
    account: str
    posts_scraped: int = 0
    comments_found: int = 0
    new_comments_saved: int = 0
    duplicates_skipped: int = 0
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class ExtractionResponse(BaseModel):
    """Response after starting extraction."""
    status: str = Field(..., description="Status (started, completed, error)")
    job_id: Optional[str] = Field(None, description="Job ID for tracking")
    stats: Optional[ExtractionStats] = None
    message: Optional[str] = None


class ExportResponse(BaseModel):
    """Response after export."""
    status: str
    path: Optional[str] = None
    records: int = 0
    message: Optional[str] = None


class ClientStats(BaseModel):
    """Statistics for a client."""
    client: str
    total_comments: int
    total_posts: int
    platforms: Dict[str, int]
    last_extraction: Optional[datetime] = None


class CommentResponse(BaseModel):
    """Comment data for API response."""
    platform_id: str
    post_id: str
    platform: str
    author_username: str
    author_display_name: Optional[str] = None
    text: str
    likes: int = 0
    published_at: Optional[datetime] = None
    parent_id: Optional[str] = None


class PostResponse(BaseModel):
    """Post data for API response."""
    platform_id: str
    platform: str
    account_id: str
    url: Optional[str] = None
    text: Optional[str] = None
    likes: int = 0
    comments_count: int = 0
    shares: int = 0
    published_at: Optional[datetime] = None
    media_type: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    data: List[Any]
    total: int
    page: int
    page_size: int
    has_more: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float
    database: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
