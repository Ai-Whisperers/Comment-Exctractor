"""JSON exporter for comments and posts."""

import json
import logging
from typing import List

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """Export data to JSON format."""

    format = "json"

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

        # Structure for AI analyzer
        export_data = {
            "metadata": {
                "client": metadata.client,
                "exported_at": metadata.exported_at.isoformat(),
                "format": self.format,
                "version": metadata.version,
                "total_comments": len(comments),
                "platforms": list(set(c.platform.value for c in comments)),
            },
            "comments": [
                self._comment_to_dict(comment) for comment in comments
            ]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

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

        export_data = {
            "metadata": {
                "client": metadata.client,
                "exported_at": metadata.exported_at.isoformat(),
                "format": self.format,
                "version": metadata.version,
                "total_posts": len(posts),
                "platforms": list(set(p.platform.value for p in posts)),
            },
            "posts": [
                self._post_to_dict(post) for post in posts
            ]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
