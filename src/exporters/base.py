"""Base exporter class with common functionality."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from ..core.models import Comment, Post, ExportMetadata
from .options import ExportOptions

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for all data exporters."""

    format: str = ""  # Override in subclass

    def __init__(self, options: Optional[ExportOptions] = None):
        """
        Initialize exporter with options.

        Args:
            options: Export customization options
        """
        self.options = options or ExportOptions()

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

    def _comment_to_dict(self, comment: Comment) -> Dict[str, Any]:
        """
        Convert comment to dictionary for export.

        Args:
            comment: Comment object

        Returns:
            Dictionary representation
        """
        # Build base data
        if self.options.flatten_author:
            data = {
                "id": comment.platform_id,
                "platform": comment.platform.value,
                "post_id": comment.post_id,
                "text": self.options.truncate_text_field(comment.text),
                "author_id": comment.author.platform_id,
                "author_username": comment.author.username,
                "author_display_name": comment.author.display_name,
                "author_is_verified": comment.author.is_verified,
                "published_at": self.options.format_date(comment.published_at),
                "likes": comment.likes,
                "replies_count": comment.replies_count,
                "parent_id": comment.parent_id,
            }
        else:
            data = {
                "id": comment.platform_id,
                "platform": comment.platform.value,
                "post_id": comment.post_id,
                "text": self.options.truncate_text_field(comment.text),
                "author": {
                    "id": comment.author.platform_id,
                    "username": comment.author.username,
                    "display_name": comment.author.display_name,
                    "is_verified": comment.author.is_verified,
                },
                "published_at": self.options.format_date(comment.published_at),
                "likes": comment.likes,
                "replies_count": comment.replies_count,
                "parent_id": comment.parent_id,
            }

        # Apply field filtering
        available_fields = list(data.keys())
        effective_fields = self.options.get_effective_fields(available_fields)
        data = {k: v for k, v in data.items() if k in effective_fields}

        # Apply field mapping
        data = {self.options.apply_field_mapping(k): v for k, v in data.items()}

        # Filter empty fields if configured
        data = self.options.filter_empty_fields(data)

        return data

    def _post_to_dict(self, post: Post) -> Dict[str, Any]:
        """
        Convert post to dictionary for export.

        Args:
            post: Post object

        Returns:
            Dictionary representation
        """
        data = {
            "id": post.platform_id,
            "platform": post.platform.value,
            "account_id": post.account_id,
            "url": post.url,
            "text": self.options.truncate_text_field(post.text),
            "published_at": self.options.format_date(post.published_at),
            "likes": post.likes,
            "comments_count": post.comments_count,
            "shares": post.shares,
            "media_type": post.media_type,
        }

        # Apply field filtering
        available_fields = list(data.keys())
        effective_fields = self.options.get_effective_fields(available_fields)
        data = {k: v for k, v in data.items() if k in effective_fields}

        # Apply field mapping
        data = {self.options.apply_field_mapping(k): v for k, v in data.items()}

        # Filter empty fields if configured
        data = self.options.filter_empty_fields(data)

        return data
