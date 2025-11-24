"""API routes for Comment Extractor.

Note: Requires FastAPI to be installed:
    pip install fastapi uvicorn
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Create a dummy router for when FastAPI isn't installed
    class DummyRouter:
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    APIRouter = DummyRouter

from .models import (
    ExtractionRequest,
    ExtractionResponse,
    ExportRequest,
    ExportResponse,
    ClientStats,
    CommentResponse,
    PostResponse,
    PaginatedResponse,
    HealthResponse,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Track start time for uptime
_start_time = time.time()


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Status"],
    summary="Health check",
)
async def health_check():
    """Check API health and database connectivity."""
    from ..core.container import get_container

    container = get_container()
    storage = container.storage()

    # Check database
    try:
        # Simple query to check database
        storage.get_comment_count("__health_check__")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=time.time() - _start_time,
        database=db_status,
    )


@router.get(
    "/stats/{client}",
    response_model=ClientStats,
    tags=["Status"],
    summary="Get client statistics",
)
async def get_client_stats(client: str):
    """Get extraction statistics for a client."""
    from ..core.container import get_container

    container = get_container()
    service = container.extraction_service()

    stats = service.get_stats(client)

    return ClientStats(
        client=stats["client"],
        total_comments=stats["total_comments"],
        total_posts=stats["total_posts"],
        platforms=stats["platforms"],
    )


# =============================================================================
# EXTRACTION
# =============================================================================

@router.post(
    "/extract",
    response_model=ExtractionResponse,
    tags=["Extraction"],
    summary="Start extraction",
)
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks = None,
):
    """
    Start an extraction for the specified account.

    This endpoint runs the extraction synchronously and returns the results.
    For long-running extractions, consider using the async endpoint.
    """
    from ..core.container import get_container
    from ..core.models import ExtractionStats as CoreStats

    container = get_container()
    service = container.extraction_service()

    started_at = datetime.utcnow()

    try:
        stats = service.extract(
            client=request.client,
            platform=request.platform,
            account_id=request.account_id,
            max_posts=request.max_posts,
            full=request.full,
        )

        from .models import ExtractionStats
        return ExtractionResponse(
            status="completed",
            stats=ExtractionStats(
                client=stats.client,
                platform=stats.platform,
                account=stats.account,
                posts_scraped=stats.posts_scraped,
                comments_found=stats.comments_found,
                new_comments_saved=stats.new_comments_saved,
                duplicates_skipped=stats.duplicates_skipped,
                error=stats.error,
                started_at=started_at,
                completed_at=stats.completed_at,
            ),
        )

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return ExtractionResponse(
            status="error",
            message=str(e),
            stats=None,
        )


# =============================================================================
# DATA QUERIES
# =============================================================================

@router.get(
    "/comments/{client}",
    response_model=PaginatedResponse,
    tags=["Data"],
    summary="Get comments",
)
async def get_comments(
    client: str,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    since: Optional[datetime] = Query(None, description="Start date"),
    until: Optional[datetime] = Query(None, description="End date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """Get comments for a client with optional filters."""
    from ..core.container import get_container

    container = get_container()
    storage = container.storage()

    # Get all comments (storage handles filtering)
    all_comments = storage.get_comments(
        client=client,
        platform=platform,
        since=since,
        until=until,
    )

    # Paginate
    total = len(all_comments)
    start = (page - 1) * page_size
    end = start + page_size
    page_comments = all_comments[start:end]

    # Convert to response format
    data = [
        CommentResponse(
            platform_id=c.platform_id,
            post_id=c.post_id,
            platform=c.platform.value,
            author_username=c.author.username,
            author_display_name=c.author.display_name,
            text=c.text,
            likes=c.likes,
            published_at=c.published_at,
            parent_id=c.parent_id,
        )
        for c in page_comments
    ]

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get(
    "/posts/{client}",
    response_model=PaginatedResponse,
    tags=["Data"],
    summary="Get posts",
)
async def get_posts(
    client: str,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    since: Optional[datetime] = Query(None, description="Start date"),
    until: Optional[datetime] = Query(None, description="End date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """Get posts for a client with optional filters."""
    from ..core.container import get_container

    container = get_container()
    storage = container.storage()

    # Get all posts
    all_posts = storage.get_posts(
        client=client,
        platform=platform,
        since=since,
        until=until,
    )

    # Paginate
    total = len(all_posts)
    start = (page - 1) * page_size
    end = start + page_size
    page_posts = all_posts[start:end]

    # Convert to response format
    data = [
        PostResponse(
            platform_id=p.platform_id,
            platform=p.platform.value,
            account_id=p.account_id,
            url=p.url,
            text=p.text,
            likes=p.likes,
            comments_count=p.comments_count,
            shares=p.shares,
            published_at=p.published_at,
            media_type=p.media_type,
        )
        for p in page_posts
    ]

    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


# =============================================================================
# EXPORT
# =============================================================================

@router.post(
    "/export",
    response_model=ExportResponse,
    tags=["Export"],
    summary="Export data",
)
async def export_data(request: ExportRequest):
    """Export comments to a file."""
    from ..core.container import get_container

    container = get_container()
    service = container.extraction_service()

    try:
        path = service.export(
            client=request.client,
            format=request.format,
            platform=request.platform,
            since=request.since,
            until=request.until,
        )

        # Get record count
        storage = container.storage()
        comments = storage.get_comments(
            client=request.client,
            platform=request.platform,
        )

        return ExportResponse(
            status="completed",
            path=path,
            records=len(comments),
        )

    except Exception as e:
        logger.error(f"Export failed: {e}")
        return ExportResponse(
            status="error",
            message=str(e),
        )


@router.post(
    "/export/posts",
    response_model=ExportResponse,
    tags=["Export"],
    summary="Export posts",
)
async def export_posts(request: ExportRequest):
    """Export posts to a file."""
    from ..core.container import get_container

    container = get_container()
    service = container.extraction_service()

    try:
        path = service.export_posts(
            client=request.client,
            format=request.format,
            platform=request.platform,
            since=request.since,
            until=request.until,
        )

        # Get record count
        storage = container.storage()
        posts = storage.get_posts(
            client=request.client,
            platform=request.platform,
        )

        return ExportResponse(
            status="completed",
            path=path,
            records=len(posts),
        )

    except Exception as e:
        logger.error(f"Export failed: {e}")
        return ExportResponse(
            status="error",
            message=str(e),
        )
