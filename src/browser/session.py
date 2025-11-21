"""Session persistence management."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages browser session persistence and validation.

    Handles saving, loading, and validating session states
    for maintaining login across scraping runs.
    """

    def __init__(self, sessions_dir: str = "data/sessions"):
        """
        Initialize session manager.

        Args:
            sessions_dir: Directory to store session files
        """
        self._sessions_dir = Path(sessions_dir)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, platform: str, username: str) -> Path:
        """
        Get the session file path for a platform/user combination.

        Args:
            platform: Platform name (e.g., 'instagram', 'facebook')
            username: Account username

        Returns:
            Path to session file
        """
        # Sanitize username for filename
        safe_username = "".join(c if c.isalnum() else "_" for c in username)
        filename = f"{platform}_{safe_username}_session.json"
        return self._sessions_dir / filename

    def session_exists(self, platform: str, username: str) -> bool:
        """
        Check if a session file exists.

        Args:
            platform: Platform name
            username: Account username

        Returns:
            True if session file exists
        """
        return self.get_session_path(platform, username).exists()

    def load_session(self, platform: str, username: str) -> Optional[str]:
        """
        Load session file path if it exists and is valid.

        Args:
            platform: Platform name
            username: Account username

        Returns:
            Session file path if valid, None otherwise
        """
        session_path = self.get_session_path(platform, username)

        if not session_path.exists():
            logger.debug(f"No session file found for {platform}/{username}")
            return None

        # Check if session is expired (optional: implement expiry logic)
        try:
            # Verify file is valid JSON
            with open(session_path, 'r') as f:
                session_data = json.load(f)

            # Basic validation
            if not isinstance(session_data, dict):
                logger.warning(f"Invalid session file format for {platform}/{username}")
                return None

            logger.info(f"SESSION | loaded from {session_path}")
            return str(session_path)

        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted session file for {platform}/{username}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error loading session for {platform}/{username}: {e}")
            return None

    def delete_session(self, platform: str, username: str) -> bool:
        """
        Delete a session file.

        Args:
            platform: Platform name
            username: Account username

        Returns:
            True if deleted successfully
        """
        session_path = self.get_session_path(platform, username)

        if session_path.exists():
            try:
                session_path.unlink()
                logger.info(f"SESSION | deleted {session_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")
                return False

        return False

    def list_sessions(self, platform: Optional[str] = None) -> list:
        """
        List all available sessions.

        Args:
            platform: Filter by platform name (optional)

        Returns:
            List of session info dictionaries
        """
        sessions = []

        for session_file in self._sessions_dir.glob("*_session.json"):
            try:
                parts = session_file.stem.rsplit("_session", 1)[0].split("_", 1)
                if len(parts) >= 2:
                    file_platform = parts[0]
                    file_username = parts[1]

                    if platform and file_platform != platform:
                        continue

                    stat = session_file.stat()
                    sessions.append({
                        "platform": file_platform,
                        "username": file_username,
                        "path": str(session_file),
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "size": stat.st_size,
                    })
            except Exception as e:
                logger.warning(f"Error reading session file {session_file}: {e}")

        return sessions

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Remove sessions older than specified days.

        Args:
            days: Maximum age in days

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for session_file in self._sessions_dir.glob("*_session.json"):
            try:
                modified = datetime.fromtimestamp(session_file.stat().st_mtime)
                if modified < cutoff:
                    session_file.unlink()
                    deleted += 1
                    logger.info(f"Deleted old session: {session_file}")
            except Exception as e:
                logger.warning(f"Error cleaning up session {session_file}: {e}")

        return deleted
