"""JSONL (JSON Lines) exporter for streaming/batch processing."""

import json
import logging
from typing import List

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter

logger = logging.getLogger(__name__)


class JSONLExporter(BaseExporter):
    """Export data to JSONL (JSON Lines) format for streaming processing."""

    format = "jsonl"

    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export comments to JSONL file.

        Args:
            comments: Comments to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        with open(output_file, "w", encoding="utf-8") as f:
            # First line is metadata
            meta_line = {
                "type": "metadata",
                "client": metadata.client,
                "exported_at": metadata.exported_at.isoformat(),
                "format": self.format,
                "version": metadata.version,
                "total_comments": len(comments),
            }
            f.write(json.dumps(meta_line, default=str) + "\n")

            # Each comment on its own line
            for comment in comments:
                comment_line = {
                    "type": "comment",
                    "id": comment.platform_id,
                    "platform": comment.platform.value,
                    "post_id": comment.post_id,
                    "text": comment.text,
                    "author_id": comment.author.platform_id,
                    "author_username": comment.author.username,
                    "author_display_name": comment.author.display_name,
                    "author_is_verified": comment.author.is_verified,
                    "published_at": comment.published_at.isoformat() if comment.published_at else None,
                    "likes": comment.likes,
                    "replies_count": comment.replies_count,
                    "parent_id": comment.parent_id,
                }
                f.write(json.dumps(comment_line, ensure_ascii=False, default=str) + "\n")

        logger.info(f"Exported {len(comments)} comments to {output_file}")
        return str(output_file)

    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export posts to JSONL file.

        Args:
            posts: Posts to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        with open(output_file, "w", encoding="utf-8") as f:
            # First line is metadata
            meta_line = {
                "type": "metadata",
                "client": metadata.client,
                "exported_at": metadata.exported_at.isoformat(),
                "format": self.format,
                "version": metadata.version,
                "total_posts": len(posts),
            }
            f.write(json.dumps(meta_line, default=str) + "\n")

            # Each post on its own line
            for post in posts:
                post_line = {
                    "type": "post",
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
                f.write(json.dumps(post_line, ensure_ascii=False, default=str) + "\n")

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
