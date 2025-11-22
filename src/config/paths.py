"""Centralized path configuration for the Comment Extractor project.

All file system paths should be accessed through this module to ensure
consistency and easy configuration changes.
"""

from pathlib import Path
from typing import Optional


class PathConfig:
    """Central configuration for all application paths."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize path configuration.

        Args:
            base_dir: Base directory for the project. Defaults to project root.
        """
        if base_dir is None:
            # Default to project root (3 levels up from this file)
            base_dir = Path(__file__).parent.parent.parent

        self._base_dir = base_dir
        self._data_dir = base_dir / "data"

    @property
    def base_dir(self) -> Path:
        """Project root directory."""
        return self._base_dir

    @property
    def data_dir(self) -> Path:
        """Main data directory."""
        return self._data_dir

    # -------------------------------------------------------------------------
    # Cache directories (not tracked in git)
    # -------------------------------------------------------------------------

    @property
    def cache_dir(self) -> Path:
        """Cache directory for temporary/large files."""
        return self._data_dir / ".cache"

    @property
    def browser_profiles_dir(self) -> Path:
        """Directory for browser profiles (session persistence)."""
        return self.cache_dir / "browser_profiles"

    def browser_profile_path(self, platform: str) -> Path:
        """
        Get browser profile path for a specific platform.

        Args:
            platform: Platform name (facebook, instagram, twitter, linkedin)

        Returns:
            Path to the browser profile directory
        """
        profile_names = {
            "facebook": "facebook_profile",
            "instagram": "instagram_profile",
            "twitter": "twitter",
            "linkedin": "linkedin",
        }
        profile_name = profile_names.get(platform.lower(), f"{platform.lower()}_profile")
        return self.browser_profiles_dir / profile_name

    @property
    def html_logs_dir(self) -> Path:
        """Directory for HTML debug logs."""
        return self.cache_dir / "HTML_logs"

    @property
    def sessions_dir(self) -> Path:
        """Directory for session files."""
        return self.cache_dir / "sessions"

    @property
    def checkpoints_dir(self) -> Path:
        """Directory for checkpoint files."""
        return self.cache_dir / "checkpoints"

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    @property
    def database_path(self) -> Path:
        """Path to SQLite database file."""
        return self._data_dir / "extractor.db"

    # -------------------------------------------------------------------------
    # Export directory
    # -------------------------------------------------------------------------

    @property
    def exports_dir(self) -> Path:
        """Directory for exported files (CSV, Excel, etc.)."""
        return self._data_dir / "exports"

    # -------------------------------------------------------------------------
    # Account-based data directories
    # -------------------------------------------------------------------------

    @property
    def accounts_dir(self) -> Path:
        """Base directory for account data."""
        return self._data_dir / "accounts"

    def account_dir(self, account_id: str, platform: str) -> Path:
        """
        Get directory for a specific account on a platform.

        Args:
            account_id: Account identifier (e.g., 'personalpy')
            platform: Platform name (e.g., 'instagram', 'facebook')

        Returns:
            Path to the account's platform directory
        """
        return self.accounts_dir / account_id / platform.lower()

    def posts_dir(self, account_id: str, platform: str) -> Path:
        """
        Get posts directory for a specific account.

        Args:
            account_id: Account identifier
            platform: Platform name

        Returns:
            Path to the posts directory
        """
        return self.account_dir(account_id, platform) / "posts"

    def comments_dir(self, account_id: str, platform: str) -> Path:
        """
        Get comments directory for a specific account.

        Args:
            account_id: Account identifier
            platform: Platform name

        Returns:
            Path to the comments directory
        """
        return self.account_dir(account_id, platform) / "comments"

    def posts_file(self, account_id: str, platform: str, date_str: str) -> Path:
        """
        Get path for a dated posts file.

        Args:
            account_id: Account identifier
            platform: Platform name
            date_str: Date string (e.g., '2025-11-21')

        Returns:
            Path to the posts JSON file
        """
        return self.posts_dir(account_id, platform) / f"{date_str}.json"

    def comments_file(self, account_id: str, platform: str, date_str: str) -> Path:
        """
        Get path for a dated comments file.

        Args:
            account_id: Account identifier
            platform: Platform name
            date_str: Date string (e.g., '2025-11-21')

        Returns:
            Path to the comments JSON file
        """
        return self.comments_dir(account_id, platform) / f"{date_str}.json"

    def progress_file(self, account_id: str, platform: str, data_type: str) -> Path:
        """
        Get path for a progress tracking file.

        Args:
            account_id: Account identifier
            platform: Platform name
            data_type: Type of data ('posts' or 'comments')

        Returns:
            Path to the progress JSON file
        """
        if data_type == "posts":
            return self.posts_dir(account_id, platform) / "progress.json"
        else:
            return self.comments_dir(account_id, platform) / "progress.json"

    # -------------------------------------------------------------------------
    # Logs directory
    # -------------------------------------------------------------------------

    @property
    def logs_dir(self) -> Path:
        """Directory for application logs."""
        return self._base_dir / "logs"

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        directories = [
            self.data_dir,
            self.cache_dir,
            self.browser_profiles_dir,
            self.html_logs_dir,
            self.sessions_dir,
            self.checkpoints_dir,
            self.exports_dir,
            self.accounts_dir,
            self.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def as_string(self, path: Path) -> str:
        """
        Convert a Path to string for compatibility with older code.

        Args:
            path: Path object

        Returns:
            String representation of the path
        """
        return str(path)


# Global instance for easy access
_paths: Optional[PathConfig] = None


def get_paths() -> PathConfig:
    """
    Get the global PathConfig instance.

    Returns:
        PathConfig instance
    """
    global _paths
    if _paths is None:
        _paths = PathConfig()
    return _paths


def reset_paths(base_dir: Optional[Path] = None) -> PathConfig:
    """
    Reset the global PathConfig instance with a new base directory.

    Args:
        base_dir: New base directory (or None for default)

    Returns:
        New PathConfig instance
    """
    global _paths
    _paths = PathConfig(base_dir)
    return _paths
