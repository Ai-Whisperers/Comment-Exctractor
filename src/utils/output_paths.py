"""
Organized output path utilities for consistent file organization.

This module provides utilities for generating organized output paths
following a consistent directory structure:

    data/
    └── exports/
        └── {client}/
            └── {platform}/
                └── {YYYY-MM}/
                    ├── {client}_{platform}_comments_{timestamp}.{format}
                    └── {client}_{platform}_posts_{timestamp}.{format}
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class OutputPathManager:
    """
    Manages organized output paths for exports.

    Provides consistent directory structure and filename generation
    for all exported data.

    Example:
        >>> manager = OutputPathManager("data/exports")
        >>> path = manager.get_export_path("acme", "instagram", "comments", "json")
        >>> print(path)
        data/exports/acme/instagram/2024-01/acme_instagram_comments_20240115_103045.json
    """

    def __init__(self, base_dir: str = "data/exports"):
        """
        Initialize output path manager.

        Args:
            base_dir: Base directory for all exports
        """
        self.base_dir = Path(base_dir)

    def get_export_dir(
        self,
        client: str,
        platform: Optional[str] = None,
        include_month: bool = True
    ) -> Path:
        """
        Get the export directory for a client/platform.

        Args:
            client: Client name
            platform: Platform name (instagram, facebook, etc.)
            include_month: Include YYYY-MM subdirectory

        Returns:
            Path to export directory
        """
        path = self.base_dir / self._sanitize_name(client)

        if platform:
            path = path / self._sanitize_name(platform)

        if include_month:
            path = path / datetime.now(timezone.utc).strftime("%Y-%m")

        return path

    def get_export_path(
        self,
        client: str,
        platform: str,
        data_type: str,
        format: str,
        timestamp: Optional[datetime] = None
    ) -> Path:
        """
        Get full export file path with organized directory structure.

        Args:
            client: Client name
            platform: Platform name
            data_type: Type of data (comments, posts, profile)
            format: File format (json, csv, xlsx)
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Full path to export file
        """
        export_dir = self.get_export_dir(client, platform)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{self._sanitize_name(client)}_{self._sanitize_name(platform)}_{data_type}_{ts_str}.{format}"

        return export_dir / filename

    def get_combined_export_path(
        self,
        client: str,
        data_type: str,
        format: str,
        platforms: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None
    ) -> Path:
        """
        Get export path for combined multi-platform exports.

        Args:
            client: Client name
            data_type: Type of data (comments, posts)
            format: File format
            platforms: List of platforms included
            timestamp: Optional timestamp

        Returns:
            Full path to export file
        """
        export_dir = self.get_export_dir(client, platform=None, include_month=True)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Include platforms in filename if specified
        if platforms and len(platforms) > 1:
            platforms_str = "_".join(sorted(p.lower() for p in platforms))
            filename = f"{self._sanitize_name(client)}_{platforms_str}_{data_type}_{ts_str}.{format}"
        else:
            platform_str = platforms[0].lower() if platforms else "all"
            filename = f"{self._sanitize_name(client)}_{platform_str}_{data_type}_{ts_str}.{format}"

        return export_dir / filename

    def ensure_dir(self, path: Path) -> Path:
        """
        Ensure directory exists, creating if necessary.

        Args:
            path: Directory path

        Returns:
            The path (for chaining)
        """
        if path.suffix:
            # It's a file path, get parent
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def get_latest_export(
        self,
        client: str,
        platform: str,
        data_type: str,
        format: str
    ) -> Optional[Path]:
        """
        Get the most recent export file for given parameters.

        Args:
            client: Client name
            platform: Platform name
            data_type: Type of data
            format: File format

        Returns:
            Path to most recent file or None
        """
        export_dir = self.get_export_dir(client, platform, include_month=False)

        if not export_dir.exists():
            return None

        # Pattern to match files
        pattern = f"{self._sanitize_name(client)}_{self._sanitize_name(platform)}_{data_type}_*.{format}"

        # Find all matching files
        matches = list(export_dir.rglob(pattern))

        if not matches:
            return None

        # Return most recent by modification time
        return max(matches, key=lambda p: p.stat().st_mtime)

    def list_exports(
        self,
        client: Optional[str] = None,
        platform: Optional[str] = None,
        format: Optional[str] = None
    ) -> List[Path]:
        """
        List all exports matching criteria.

        Args:
            client: Filter by client
            platform: Filter by platform
            format: Filter by format

        Returns:
            List of export file paths
        """
        if client:
            search_dir = self.base_dir / self._sanitize_name(client)
            if platform:
                search_dir = search_dir / self._sanitize_name(platform)
        else:
            search_dir = self.base_dir

        if not search_dir.exists():
            return []

        pattern = f"*.{format}" if format else "*"
        return sorted(search_dir.rglob(pattern))

    def cleanup_old_exports(
        self,
        client: str,
        keep_count: int = 10,
        data_type: Optional[str] = None
    ) -> int:
        """
        Remove old exports, keeping only the most recent ones.

        Args:
            client: Client name
            keep_count: Number of recent exports to keep per type
            data_type: Optional filter by data type

        Returns:
            Number of files deleted
        """
        export_dir = self.get_export_dir(client, platform=None, include_month=False)

        if not export_dir.exists():
            return 0

        # Group files by type
        from collections import defaultdict
        files_by_type = defaultdict(list)

        for file_path in export_dir.rglob("*.*"):
            if file_path.is_file():
                # Extract type from filename
                parts = file_path.stem.split("_")
                if len(parts) >= 3:
                    file_type = parts[-2]  # Second to last part is type
                    if data_type is None or file_type == data_type:
                        files_by_type[file_type].append(file_path)

        deleted = 0
        for file_type, files in files_by_type.items():
            # Sort by modification time, newest first
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Delete old files
            for old_file in files[keep_count:]:
                try:
                    old_file.unlink()
                    deleted += 1
                    logger.debug(f"Deleted old export: {old_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete {old_file}: {e}")

        return deleted

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize a name for use in file paths.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name
        """
        # Replace problematic characters
        sanitized = name.lower().strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
            sanitized = sanitized.replace(char, '_')
        return sanitized


# Convenience functions

def get_export_path(
    client: str,
    platform: str,
    data_type: str,
    format: str,
    base_dir: str = "data/exports"
) -> str:
    """
    Get organized export file path.

    Args:
        client: Client name
        platform: Platform name
        data_type: Type of data
        format: File format
        base_dir: Base exports directory

    Returns:
        Full path as string
    """
    manager = OutputPathManager(base_dir)
    path = manager.get_export_path(client, platform, data_type, format)
    manager.ensure_dir(path)
    return str(path)


def ensure_export_dir(client: str, platform: str = None, base_dir: str = "data/exports") -> str:
    """
    Ensure export directory exists and return path.

    Args:
        client: Client name
        platform: Optional platform name
        base_dir: Base exports directory

    Returns:
        Directory path as string
    """
    manager = OutputPathManager(base_dir)
    export_dir = manager.get_export_dir(client, platform)
    manager.ensure_dir(export_dir)
    return str(export_dir)
