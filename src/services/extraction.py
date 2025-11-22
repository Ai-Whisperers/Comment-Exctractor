"""Main extraction service for orchestrating scraping, storage, and export."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Protocol, Dict, Any

from ..core.models import (
    Platform,
    ExtractionStats,
    ExportMetadata,
    ClientConfig,
    SocialAccount,
)
from ..core.exceptions import ExtractionError, ConfigurationError, ValidationError
from ..scrapers.registry import ScraperRegistry
from ..scrapers.base import BaseScraper
from ..storage.sqlite import SQLiteStorage
from ..storage.base import StorageBackend
from ..exporters.registry import ExporterRegistry
from ..exporters.base import BaseExporter
from ..utils.html_debug_logger import set_debug_client
from ..utils.output_paths import OutputPathManager
from ..utils.security import validate_name

logger = logging.getLogger(__name__)


class ScraperFactory(Protocol):
    """Protocol for scraper factory functions."""
    def __call__(self, platform: str, config: Optional[dict] = None) -> BaseScraper: ...


class ExporterFactory(Protocol):
    """Protocol for exporter factory functions."""
    def __call__(self, format: str) -> BaseExporter: ...

# Validation constants
MAX_POSTS_LIMIT = 10000
MIN_POSTS_LIMIT = 1
VALID_PLATFORMS = {'facebook', 'instagram', 'twitter', 'linkedin', 'google'}


def _validate_name_wrapper(value: str, field_name: str) -> None:
    """Wrapper for validate_name that converts ValidationError to ConfigurationError."""
    try:
        validate_name(value, field_name)
    except ValidationError as e:
        raise ConfigurationError(str(e), setting=field_name)


class ExtractionService:
    """
    Main service for extracting social media comments.

    Orchestrates scrapers, storage, and exporters.
    """

    def __init__(
        self,
        storage: Optional[StorageBackend] = None,
        data_dir: str = "data",
        scraper_factory: Optional[ScraperFactory] = None,
        exporter_factory: Optional[ExporterFactory] = None,
        path_manager: Optional[OutputPathManager] = None
    ):
        """
        Initialize extraction service.

        Args:
            storage: Storage backend (defaults to SQLite)
            data_dir: Directory for data files
            scraper_factory: Factory for creating scrapers (defaults to ScraperRegistry.get)
            exporter_factory: Factory for creating exporters (defaults to ExporterRegistry.get)
            path_manager: Output path manager (created if not provided)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Storage - defaults to SQLite
        self.storage = storage or SQLiteStorage(
            db_path=str(self.data_dir / "extractor.db")
        )

        # Scraper factory - defaults to registry
        self._scraper_factory = scraper_factory or ScraperRegistry.get

        # Exporter factory - defaults to registry
        self._exporter_factory = exporter_factory or ExporterRegistry.get

        # Path manager - defaults to exports directory
        self._default_exports_dir = str(self.data_dir / "exports")
        self._path_manager = path_manager

    def extract(
        self,
        client: str,
        platform: str,
        account_id: str,
        max_posts: int = 100,
        full: bool = False,
        config: Optional[dict] = None
    ) -> ExtractionStats:
        """
        Extract comments from a social media account.

        Args:
            client: Client name
            platform: Platform name (facebook, instagram, twitter)
            account_id: Account username or ID
            max_posts: Maximum posts to extract
            full: If True, ignore last extraction date (full re-extraction)
            config: Platform-specific configuration

        Returns:
            Extraction statistics
        """
        # Validate inputs
        _validate_name_wrapper(client, "client")
        _validate_name_wrapper(account_id, "account_id")

        platform_lower = platform.lower()
        if platform_lower not in VALID_PLATFORMS:
            raise ConfigurationError(
                f"Invalid platform: '{platform}'. "
                f"Must be one of: {', '.join(sorted(VALID_PLATFORMS))}"
            )

        if not MIN_POSTS_LIMIT <= max_posts <= MAX_POSTS_LIMIT:
            raise ConfigurationError(
                f"max_posts must be between {MIN_POSTS_LIMIT} and {MAX_POSTS_LIMIT}, "
                f"got {max_posts}"
            )

        stats = ExtractionStats(
            client=client,
            platform=platform,
            account=account_id
        )

        logger.info(
            f"Starting extraction for {client}: {platform}:{account_id} "
            f"(max_posts={max_posts}, full={full})"
        )

        # Set the client for HTML debug logging
        set_debug_client(client)

        try:
            # Get scraper using injected factory
            scraper = self._scraper_factory(platform_lower, config)

            # Determine since_date for incremental extraction
            since_date = None
            if not full:
                since_date = self.storage.get_last_extraction_date(
                    client, platform, account_id
                )
                if since_date:
                    logger.info(f"Incremental extraction since {since_date}")

            # Get set of posts that already have comments (for skipping)
            posts_with_comments = self.storage.get_posts_with_comments_set(
                client, platform_lower
            )
            if posts_with_comments:
                logger.info(f"Found {len(posts_with_comments)} posts with existing comments (will skip)")

            # Track skipped posts
            posts_skipped = 0

            # Extract posts and comments
            for result in scraper.get_posts_with_comments(
                account_id, since_date, max_posts, posts_with_comments
            ):
                stats.posts_scraped += 1

                # Save post
                self.storage.save_post(client, result.post)

                # Check if this post already has comments
                if result.post.platform_id in posts_with_comments:
                    posts_skipped += 1
                    logger.debug(f"Skipping post {result.post.platform_id} - already has comments")
                    continue

                # Save comments
                stats.comments_found += len(result.comments)

                for comment in result.comments:
                    if self.storage.save_comment(client, comment):
                        stats.new_comments_saved += 1
                    else:
                        stats.duplicates_skipped += 1

            if posts_skipped > 0:
                logger.info(f"Skipped {posts_skipped} posts that already had comments")

            # Mark as complete
            stats.completed_at = datetime.utcnow()

            # Update extraction history
            self.storage.update_extraction_history(
                client, platform, account_id, stats
            )

            logger.info(
                f"Extraction complete: {stats.posts_scraped} posts, "
                f"{stats.new_comments_saved} new comments, "
                f"{stats.duplicates_skipped} duplicates"
            )

        except Exception as e:
            stats.error = str(e)
            stats.completed_at = datetime.utcnow()

            # Still update history on error
            self.storage.update_extraction_history(
                client, platform, account_id, stats
            )

            logger.error(f"Extraction failed: {e}")
            raise

        return stats

    def extract_all(
        self,
        client_config: ClientConfig,
        max_posts: int = 100,
        full: bool = False,
        platform_configs: Optional[dict] = None
    ) -> List[ExtractionStats]:
        """
        Extract from all accounts for a client.

        Args:
            client_config: Client configuration with accounts
            max_posts: Maximum posts per account
            full: Full re-extraction
            platform_configs: Platform-specific configurations

        Returns:
            List of extraction statistics
        """
        results = []
        platform_configs = platform_configs or {}

        for account in client_config.accounts:
            if not account.enabled:
                continue

            try:
                stats = self.extract(
                    client=client_config.name,
                    platform=account.platform.value,
                    account_id=account.identifier,
                    max_posts=max_posts,
                    full=full,
                    config=platform_configs.get(account.platform.value)
                )
                results.append(stats)

            except Exception as e:
                logger.error(
                    f"Failed to extract {account.platform.value}:{account.identifier}: {e}"
                )
                # Create failed stats
                stats = ExtractionStats(
                    client=client_config.name,
                    platform=account.platform.value,
                    account=account.identifier,
                    error=str(e),
                    completed_at=datetime.utcnow()
                )
                results.append(stats)

        return results

    def export(
        self,
        client: str,
        format: str = "json",
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Export comments to a file with organized directory structure.

        Output structure:
            {base_dir}/{client}/{platform}/{YYYY-MM}/{client}_{platform}_comments_{timestamp}.{format}

        Args:
            client: Client name
            format: Export format (json, csv, jsonl)
            platform: Filter by platform
            since: Comments after this date
            until: Comments before this date
            output_dir: Override base output directory

        Returns:
            Path to exported file
        """
        # Get comments from storage
        comments = self.storage.get_comments(
            client=client,
            platform=platform,
            since=since,
            until=until
        )

        if not comments:
            logger.warning(f"No comments found for {client}")

        # Determine platforms in export
        platforms = list(set(c.platform.value for c in comments)) if comments else []

        # Create metadata
        metadata = ExportMetadata(
            client=client,
            format=format,
            total_comments=len(comments),
            platforms=platforms,
        )

        # Use OutputPathManager for organized paths
        base_dir = output_dir or self._default_exports_dir
        path_manager = self._path_manager or OutputPathManager(base_dir)

        # Generate organized path
        if platform:
            # Single platform export
            full_path = path_manager.get_export_path(
                client=client,
                platform=platform,
                data_type="comments",
                format=format
            )
        else:
            # Multi-platform export
            full_path = path_manager.get_combined_export_path(
                client=client,
                data_type="comments",
                format=format,
                platforms=platforms if platforms else None
            )

        # Ensure directory exists
        path_manager.ensure_dir(full_path)

        logger.info(f"EXPORT | path={full_path}")

        # Get exporter using injected factory
        exporter = self._exporter_factory(format)
        return exporter.export(comments, metadata, str(full_path))

    def export_posts(
        self,
        client: str,
        format: str = "json",
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Export posts to a file with organized directory structure.

        Output structure:
            {base_dir}/{client}/{platform}/{YYYY-MM}/{client}_{platform}_posts_{timestamp}.{format}

        Args:
            client: Client name
            format: Export format (json, csv, jsonl)
            platform: Filter by platform
            since: Posts after this date
            until: Posts before this date
            output_dir: Override base output directory

        Returns:
            Path to exported file
        """
        # Get posts from storage
        posts = self.storage.get_posts(
            client=client,
            platform=platform,
            since=since,
            until=until
        )

        if not posts:
            logger.warning(f"No posts found for {client}")

        # Determine platforms in export
        platforms = list(set(p.platform.value for p in posts)) if posts else []

        # Create metadata
        metadata = ExportMetadata(
            client=client,
            format=format,
            total_comments=len(posts),
            platforms=platforms,
        )

        # Use OutputPathManager for organized paths
        base_dir = output_dir or self._default_exports_dir
        path_manager = self._path_manager or OutputPathManager(base_dir)

        # Generate organized path
        if platform:
            # Single platform export
            full_path = path_manager.get_export_path(
                client=client,
                platform=platform,
                data_type="posts",
                format=format
            )
        else:
            # Multi-platform export
            full_path = path_manager.get_combined_export_path(
                client=client,
                data_type="posts",
                format=format,
                platforms=platforms if platforms else None
            )

        # Ensure directory exists
        path_manager.ensure_dir(full_path)

        logger.info(f"EXPORT | path={full_path}")

        # Get exporter using injected factory
        exporter = self._exporter_factory(format)
        return exporter.export_posts(posts, metadata, str(full_path))

    def get_stats(self, client: str) -> Dict[str, Any]:
        """
        Get statistics for a client.

        Args:
            client: Client name

        Returns:
            Statistics dictionary
        """
        total_comments = self.storage.get_comment_count(client)

        # Get per-platform counts
        platform_counts = {}
        for platform in Platform:
            count = self.storage.get_comment_count(client, platform.value)
            if count > 0:
                platform_counts[platform.value] = count

        # Get posts
        posts = self.storage.get_posts(client)

        return {
            "client": client,
            "total_comments": total_comments,
            "total_posts": len(posts),
            "platforms": platform_counts,
        }
