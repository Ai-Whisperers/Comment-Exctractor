"""Main extraction service for orchestrating scraping, storage, and export."""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from ..core.models import (
    Platform,
    ExtractionStats,
    ExportMetadata,
    ClientConfig,
    SocialAccount,
)
from ..core.exceptions import ExtractionError, ConfigurationError
from ..scrapers.registry import ScraperRegistry
from ..storage.sqlite import SQLiteStorage
from ..exporters.registry import ExporterRegistry

logger = logging.getLogger(__name__)

# Validation constants
MAX_POSTS_LIMIT = 10000
MIN_POSTS_LIMIT = 1
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
VALID_PLATFORMS = {'facebook', 'instagram', 'twitter', 'linkedin'}


def _validate_name(value: str, field_name: str) -> None:
    """Validate client/account names to prevent path traversal and injection."""
    if not value:
        raise ConfigurationError(f"{field_name} cannot be empty")
    if len(value) > 100:
        raise ConfigurationError(f"{field_name} too long (max 100 characters)")
    if not VALID_NAME_PATTERN.match(value):
        raise ConfigurationError(
            f"Invalid {field_name}: '{value}'. "
            f"Only alphanumeric, underscore, hyphen, and dot allowed."
        )
    # Prevent path traversal
    if '..' in value or value.startswith('/') or value.startswith('\\'):
        raise ConfigurationError(f"Invalid characters in {field_name}: '{value}'")


class ExtractionService:
    """
    Main service for extracting social media comments.

    Orchestrates scrapers, storage, and exporters.
    """

    def __init__(
        self,
        storage: Optional[SQLiteStorage] = None,
        data_dir: str = "data"
    ):
        """
        Initialize extraction service.

        Args:
            storage: Storage backend (defaults to SQLite)
            data_dir: Directory for data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.storage = storage or SQLiteStorage(
            db_path=str(self.data_dir / "extractor.db")
        )

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
        _validate_name(client, "client")
        _validate_name(account_id, "account_id")

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

        try:
            # Get scraper
            scraper = ScraperRegistry.get(platform_lower, config)

            # Determine since_date for incremental extraction
            since_date = None
            if not full:
                since_date = self.storage.get_last_extraction_date(
                    client, platform, account_id
                )
                if since_date:
                    logger.info(f"Incremental extraction since {since_date}")

            # Extract posts and comments
            for result in scraper.get_posts_with_comments(
                account_id, since_date, max_posts
            ):
                stats.posts_scraped += 1

                # Save post
                self.storage.save_post(client, result.post)

                # Save comments
                stats.comments_found += len(result.comments)

                for comment in result.comments:
                    if self.storage.save_comment(client, comment):
                        stats.new_comments_saved += 1
                    else:
                        stats.duplicates_skipped += 1

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
        Export comments to a file.

        Args:
            client: Client name
            format: Export format (json, csv, jsonl)
            platform: Filter by platform
            since: Comments after this date
            until: Comments before this date
            output_dir: Output directory

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

        # Create metadata
        metadata = ExportMetadata(
            client=client,
            format=format,
            total_comments=len(comments),
            platforms=list(set(c.platform.value for c in comments)),
        )

        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.data_dir / "exports"

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{client}_comments_{timestamp}.{format}"
        full_path = str(output_path / filename)

        # Get exporter and export
        exporter = ExporterRegistry.get(format)
        return exporter.export(comments, metadata, full_path)

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
        Export posts to a file.

        Args:
            client: Client name
            format: Export format (json, csv, jsonl)
            platform: Filter by platform
            since: Posts after this date
            until: Posts before this date
            output_dir: Output directory

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

        # Create metadata
        metadata = ExportMetadata(
            client=client,
            format=format,
            total_comments=len(posts),
            platforms=list(set(p.platform.value for p in posts)),
        )

        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.data_dir / "exports"

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{client}_posts_{timestamp}.{format}"
        full_path = str(output_path / filename)

        # Get exporter and export
        exporter = ExporterRegistry.get(format)
        return exporter.export_posts(posts, metadata, full_path)

    def get_stats(self, client: str) -> dict:
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
