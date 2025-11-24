"""FastAPI application factory.

Note: Requires FastAPI to be installed:
    pip install fastapi uvicorn

Usage:
    # Run with uvicorn
    uvicorn src.api.app:app --reload --port 8000

    # Or programmatically
    from src.api import create_app
    app = create_app()
"""

import logging
from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global app instance
_app: Optional["FastAPI"] = None


def create_app(
    title: str = "Comment Extractor API",
    version: str = "1.0.0",
    debug: bool = False,
) -> "FastAPI":
    """
    Create and configure FastAPI application.

    Args:
        title: API title
        version: API version
        debug: Enable debug mode

    Returns:
        Configured FastAPI application

    Raises:
        ImportError: If FastAPI is not installed
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required for the API server. "
            "Install with: pip install fastapi uvicorn"
        )

    from .routes import router

    app = FastAPI(
        title=title,
        version=version,
        description="""
        REST API for Comment Extractor.

        ## Features

        - **Extraction**: Trigger extractions from social media accounts
        - **Data Queries**: Query comments and posts with filtering
        - **Export**: Export data to JSON, CSV, or JSONL
        - **Monitoring**: Health checks and statistics

        ## Authentication

        Currently, no authentication is required. For production use,
        consider adding API key or OAuth2 authentication.
        """,
        debug=debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router, prefix="/api/v1")

    # Add startup/shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info("API server starting up")
        # Initialize container
        from ..core.container import get_container
        get_container()

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("API server shutting down")
        # Cleanup
        from ..core.container import reset_container
        reset_container()

    return app


def get_app() -> "FastAPI":
    """
    Get or create the global FastAPI application.

    Returns:
        FastAPI application instance
    """
    global _app
    if _app is None:
        _app = create_app()
    return _app


# Create default app for uvicorn
if FASTAPI_AVAILABLE:
    app = get_app()
else:
    app = None
