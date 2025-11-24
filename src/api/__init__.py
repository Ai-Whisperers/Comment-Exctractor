"""REST API for Comment Extractor.

Provides endpoints for:
- Triggering extractions
- Querying data
- Exporting results
- Monitoring status
"""

from .app import create_app, get_app
from .routes import router

__all__ = [
    "create_app",
    "get_app",
    "router",
]
