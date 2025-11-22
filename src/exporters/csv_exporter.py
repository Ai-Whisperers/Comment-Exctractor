"""CSV exporter for comments and posts."""

import csv
import logging
from typing import List, Optional

from ..core.models import Comment, Post, ExportMetadata
from .base import BaseExporter
from .options import ExportOptions

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Export data to CSV format."""

    format = "csv"

    def __init__(self, options: Optional[ExportOptions] = None):
        """Initialize CSV exporter with options."""
        super().__init__(options)

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

        # Convert comments to dicts using options
        if comments:
            rows = [self._comment_to_dict(comment) for comment in comments]
            # Get fieldnames from first row (after options processing)
            fieldnames = list(rows[0].keys()) if rows else []
        else:
            fieldnames = []
            rows = []

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.options.csv_delimiter,
                quoting=self.options.csv_quoting.value,
                lineterminator=self.options.csv_line_terminator
            )

            if self.options.csv_include_header:
                writer.writeheader()

            for row in rows:
                # Convert None values to empty strings for CSV
                clean_row = {k: (v if v is not None else "") for k, v in row.items()}
                writer.writerow(clean_row)

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

        # Convert posts to dicts using options
        if posts:
            rows = [self._post_to_dict(post) for post in posts]
            # Get fieldnames from first row (after options processing)
            fieldnames = list(rows[0].keys()) if rows else []
        else:
            fieldnames = []
            rows = []

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.options.csv_delimiter,
                quoting=self.options.csv_quoting.value,
                lineterminator=self.options.csv_line_terminator
            )

            if self.options.csv_include_header:
                writer.writeheader()

            for row in rows:
                # Convert None values to empty strings for CSV
                clean_row = {k: (v if v is not None else "") for k, v in row.items()}
                writer.writerow(clean_row)

        logger.info(f"Exported {len(posts)} posts to {output_file}")
        return str(output_file)
