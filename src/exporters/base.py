"""Base exporter class with common functionality."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import logging

from ..core.models import Comment, Post, ExportMetadata

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for all data exporters."""

    format: str = ""  # Override in subclass

    @abstractmethod
    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export comments to file.

        Args:
            comments: Comments to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        pass

    @abstractmethod
    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export posts to file.

        Args:
            posts: Posts to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        pass

    def _ensure_output_dir(self, output_path: str) -> Path:
        """
        Ensure output directory exists.

        Args:
            output_path: Output file path

        Returns:
            Path object for the output file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        return output_file

    def _comment_to_dict(self, comment: Comment) -> dict:
        """
        Convert comment to dictionary for export.

        Args:
            comment: Comment object

        Returns:
            Dictionary representation
        """
        return {
            "id": comment.platform_id,
            "platform": comment.platform.value,
            "post_id": comment.post_id,
            "text": comment.text,
            "author": {
                "id": comment.author.platform_id,
                "username": comment.author.username,
                "display_name": comment.author.display_name,
                "is_verified": comment.author.is_verified,
            },
            "published_at": comment.published_at.isoformat() if comment.published_at else None,
            "likes": comment.likes,
            "replies_count": comment.replies_count,
            "parent_id": comment.parent_id,
        }

    def _post_to_dict(self, post: Post) -> dict:
        """
        Convert post to dictionary for export.

        Args:
            post: Post object

        Returns:
            Dictionary representation
        """
        return {
            "id": post.platform_id,
            "platform": post.platform.value,
            "account_id": post.account_id,
            "url": post.url,
            "text": post.text,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "likes": post.likes,
            "comments_count": post.comments_count,
            "shares": post.shares,
            "media_type": post.media_type,
        }
