"""JSON exporter for comments and posts."""

import json
import logging
from typing import List, Optional

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter
from .options import ExportOptions

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """Export data to JSON format."""

    format = "json"

    def __init__(self, options: Optional[ExportOptions] = None):
        """Initialize JSON exporter with options."""
        super().__init__(options)

    def export(
        self,
        comments: List[Comment],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export comments to JSON file.

        Args:
            comments: Comments to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        # Build export data
        comments_data = [self._comment_to_dict(comment) for comment in comments]

        if self.options.json_include_metadata:
            export_data = {
                "metadata": {
                    "client": metadata.client,
                    "exported_at": self.options.format_date(metadata.exported_at),
                    "format": self.format,
                    "version": metadata.version,
                    "total_comments": len(comments),
                    "platforms": list(set(c.platform.value for c in comments)),
                },
                "comments": comments_data
            }

            if self.options.include_export_stats:
                export_data["metadata"]["stats"] = {
                    "avg_likes": sum(c.likes for c in comments) / len(comments) if comments else 0,
                    "total_replies": sum(c.replies_count for c in comments),
                }
        else:
            export_data = comments_data

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                export_data,
                f,
                ensure_ascii=self.options.json_ensure_ascii,
                indent=self.options.json_indent,
                sort_keys=self.options.json_sort_keys,
                default=str
            )

        logger.info(f"Exported {len(comments)} comments to {output_file}")
        return str(output_file)

    def export_posts(
        self,
        posts: List[Post],
        metadata: ExportMetadata,
        output_path: str
    ) -> str:
        """
        Export posts to JSON file.

        Args:
            posts: Posts to export
            metadata: Export metadata
            output_path: Output file path

        Returns:
            Path to exported file
        """
        output_file = self._ensure_output_dir(output_path)

        # Build export data
        posts_data = [self._post_to_dict(post) for post in posts]

        if self.options.json_include_metadata:
            export_data = {
                "metadata": {
                    "client": metadata.client,
                    "exported_at": self.options.format_date(metadata.exported_at),
                    "format": self.format,
                    "version": metadata.version,
                    "total_posts": len(posts),
                    "platforms": list(set(p.platform.value for p in posts)),
                },
                "posts": posts_data
            }

            if self.options.include_export_stats:
                export_data["metadata"]["stats"] = {
                    "avg_likes": sum(p.likes for p in posts) / len(posts) if posts else 0,
                    "total_comments": sum(p.comments_count for p in posts),
                    "total_shares": sum(p.shares for p in posts),
                }
        else:
            export_data = posts_data

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                export_data,
                f,
                ensure_ascii=self.options.json_ensure_ascii,
                indent=self.options.json_indent,
                sort_keys=self.options.json_sort_keys,
                default=str
            )

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
