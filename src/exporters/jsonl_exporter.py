"""JSONL (JSON Lines) exporter for streaming/batch processing."""

import json
import logging
from typing import List, Optional

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter
from .options import ExportOptions

logger = logging.getLogger(__name__)


class JSONLExporter(BaseExporter):
    """Export data to JSONL (JSON Lines) format for streaming processing."""

    format = "jsonl"

    def __init__(self, options: Optional[ExportOptions] = None):
        """Initialize JSONL exporter with options."""
        super().__init__(options)

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
            # First line is metadata (if enabled)
            if self.options.jsonl_include_metadata_line:
                meta_line = {
                    "type": "metadata",
                    "client": metadata.client,
                    "exported_at": self.options.format_date(metadata.exported_at),
                    "format": self.format,
                    "version": metadata.version,
                    "total_comments": len(comments),
                }
                f.write(json.dumps(meta_line, default=str) + "\n")

            # Each comment on its own line
            for comment in comments:
                comment_line = self._comment_to_dict(comment)

                # Add type field if enabled
                if self.options.jsonl_include_type_field:
                    comment_line = {"type": "comment", **comment_line}

                f.write(json.dumps(
                    comment_line,
                    ensure_ascii=self.options.json_ensure_ascii,
                    default=str
                ) + "\n")

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
            # First line is metadata (if enabled)
            if self.options.jsonl_include_metadata_line:
                meta_line = {
                    "type": "metadata",
                    "client": metadata.client,
                    "exported_at": self.options.format_date(metadata.exported_at),
                    "format": self.format,
                    "version": metadata.version,
                    "total_posts": len(posts),
                }
                f.write(json.dumps(meta_line, default=str) + "\n")

            # Each post on its own line
            for post in posts:
                post_line = self._post_to_dict(post)

                # Add type field if enabled
                if self.options.jsonl_include_type_field:
                    post_line = {"type": "post", **post_line}

                f.write(json.dumps(
                    post_line,
                    ensure_ascii=self.options.json_ensure_ascii,
                    default=str
                ) + "\n")

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
