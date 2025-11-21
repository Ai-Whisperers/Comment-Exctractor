"""CSV exporter for comments and posts."""

import csv
import logging
from typing import List

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Export data to CSV format."""

    format = "csv"

    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export comments to CSV file.

        Args:
            comments: Comments to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        fieldnames = [
            "id",
            "platform",
            "post_id",
            "text",
            "author_id",
            "author_username",
            "author_display_name",
            "author_is_verified",
            "published_at",
            "likes",
            "replies_count",
            "parent_id",
        ]

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for comment in comments:
                writer.writerow({
                    "id": comment.platform_id,
                    "platform": comment.platform.value,
                    "post_id": comment.post_id,
                    "text": comment.text,
                    "author_id": comment.author.platform_id,
                    "author_username": comment.author.username,
                    "author_display_name": comment.author.display_name,
                    "author_is_verified": comment.author.is_verified,
                    "published_at": comment.published_at.isoformat() if comment.published_at else "",
                    "likes": comment.likes,
                    "replies_count": comment.replies_count,
                    "parent_id": comment.parent_id or "",
                })

        logger.info(f"Exported {len(comments)} comments to {output_file}")
        return str(output_file)

    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export posts to CSV file.

        Args:
            posts: Posts to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        fieldnames = [
            "id",
            "platform",
            "account_id",
            "url",
            "text",
            "published_at",
            "likes",
            "comments_count",
            "shares",
            "media_type",
        ]

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for post in posts:
                writer.writerow({
                    "id": post.platform_id,
                    "platform": post.platform.value,
                    "account_id": post.account_id,
                    "url": post.url or "",
                    "text": post.text or "",
                    "published_at": post.published_at.isoformat() if post.published_at else "",
                    "likes": post.likes,
                    "comments_count": post.comments_count,
                    "shares": post.shares,
                    "media_type": post.media_type or "",
                })

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
