"""Abstract protocols/interfaces for the comment extractor."""

from typing import Protocol, Iterator, Optional, List, Dict, Any
from datetime import datetime

from .models import (
    Platform,
    Comment,
    Post,
    Profile,
    ExtractionResult,
    ExtractionStats,
    ExportMetadata,
)


class ScraperProtocol(Protocol):
    """Protocol for platform scrapers."""

    platform: Platform

    def get_posts_with_comments(
        self,
        account_id: str,
        since_date: Optional[datetime] = None,
        max_posts: int = 100
    ) -> Iterator[ExtractionResult]:
        """
        Get posts with their comments from an account.

        Args:
            account_id: Username, page ID, or identifier
            since_date: Only get posts after this date (for incremental extraction)
            max_posts: Maximum number of posts to retrieve

        Yields:
            ExtractionResult with post and its comments
        """
        ...

    def get_profile(self, account_id: str) -> Profile:
        """
        Get profile information for an account.

        Args:
            account_id: Username, page ID, or identifier

        Returns:
            Profile information
        """
        ...

    def get_comments(
        self,
        post_id: str,
        max_comments: int = 1000
    ) -> Iterator[Comment]:
        """
        Get comments for a specific post.

        Args:
            post_id: Platform post ID
            max_comments: Maximum comments to retrieve

        Yields:
            Comment objects
        """
        ...


class StorageProtocol(Protocol):
    """Protocol for data storage backends."""

    def save_comment(self, client: str, comment: Comment) -> bool:
        """
        Save a comment to storage.

        Args:
            client: Client name
            comment: Comment to save

        Returns:
            True if new comment saved, False if duplicate
        """
        ...

    def save_post(self, client: str, post: Post) -> bool:
        """
        Save a post to storage.

        Args:
            client: Client name
            post: Post to save

        Returns:
            True if new post saved, False if duplicate
        """
        ...

    def save_profile(self, client: str, profile: Profile) -> bool:
        """
        Save a profile to storage.

        Args:
            client: Client name
            profile: Profile to save

        Returns:
            True if saved/updated
        """
        ...

    def get_comments(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Comment]:
        """
        Get comments from storage.

        Args:
            client: Client name
            platform: Filter by platform
            since: Comments after this date
            until: Comments before this date
            limit: Maximum number to return

        Returns:
            List of comments
        """
        ...

    def get_posts(
        self,
        client: str,
        platform: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Post]:
        """
        Get posts from storage.

        Args:
            client: Client name
            platform: Filter by platform
            since: Posts after this date
            until: Posts before this date

        Returns:
            List of posts
        """
        ...

    def get_last_extraction_date(
        self,
        client: str,
        platform: str,
        account_id: str
    ) -> Optional[datetime]:
        """
        Get the date of the last extraction for an account.

        Args:
            client: Client name
            platform: Platform name
            account_id: Account identifier

        Returns:
            Last extraction date or None if never extracted
        """
        ...

    def update_extraction_history(
        self,
        client: str,
        platform: str,
        account_id: str,
        stats: ExtractionStats
    ) -> None:
        """
        Update extraction history for tracking.

        Args:
            client: Client name
            platform: Platform name
            account_id: Account identifier
            stats: Extraction statistics
        """
        ...

    def get_comment_count(
        self,
        client: str,
        platform: Optional[str] = None
    ) -> int:
        """
        Get total comment count.

        Args:
            client: Client name
            platform: Optional platform filter

        Returns:
            Number of comments
        """
        ...


class ExporterProtocol(Protocol):
    """Protocol for data exporters."""

    format: str

    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export comments to a file.

        Args:
            comments: Comments to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        ...

    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export posts to a file.

        Args:
            posts: Posts to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        ...


class QueueProtocol(Protocol):
    """Protocol for job queue backends."""

    def enqueue(
        self,
        task_name: str,
        payload: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Enqueue a task for processing.

        Args:
            task_name: Name of the task
            payload: Task data
            priority: Task priority (higher = more urgent)

        Returns:
            Job ID
        """
        ...

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status.

        Args:
            job_id: Job ID

        Returns:
            Job status information
        """
        ...

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a queued job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled
        """
        ...
