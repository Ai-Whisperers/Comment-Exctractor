"""Base storage abstraction classes."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Type
from datetime import datetime

from ..core.models import Post, Comment, Profile

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    All storage implementations (JSON, CSV, Excel, etc.) must implement
    these methods for consistent data persistence.
    """

    def __init__(self, output_dir: str):
        """
        Initialize storage backend.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def save_posts(
        self,
        posts: List[Post],
        account: str,
        platform: str
    ) -> str:
        """
        Save posts to storage.

        Args:
            posts: List of Post objects
            account: Account username
            platform: Platform name

        Returns:
            Path to saved file
        """
        pass

    @abstractmethod
    def save_comments(
        self,
        comments: List[Comment],
        account: str,
        platform: str
    ) -> str:
        """
        Save comments to storage.

        Args:
            comments: List of Comment objects
            account: Account username
            platform: Platform name

        Returns:
            Path to saved file
        """
        pass

    @abstractmethod
    def save_profile(
        self,
        profile: Profile,
        account: str,
        platform: str
    ) -> str:
        """
        Save profile to storage.

        Args:
            profile: Profile object
            account: Account username
            platform: Platform name

        Returns:
            Path to saved file
        """
        pass

    def save_extraction_result(
        self,
        posts: List[Post],
        comments: List[Comment],
        profile: Optional[Profile],
        account: str,
        platform: str
    ) -> Dict[str, str]:
        """
        Save complete extraction result.

        Args:
            posts: List of Post objects
            comments: List of Comment objects
            profile: Optional Profile object
            account: Account username
            platform: Platform name

        Returns:
            Dictionary mapping data type to file path
        """
        results = {}

        if posts:
            results["posts"] = self.save_posts(posts, account, platform)
            logger.info(f"Saved {len(posts)} posts to {results['posts']}")

        if comments:
            results["comments"] = self.save_comments(comments, account, platform)
            logger.info(f"Saved {len(comments)} comments to {results['comments']}")

        if profile:
            results["profile"] = self.save_profile(profile, account, platform)
            logger.info(f"Saved profile to {results['profile']}")

        return results

    def _generate_filename(
        self,
        account: str,
        platform: str,
        data_type: str,
        extension: str
    ) -> Path:
        """
        Generate standardized filename.

        Args:
            account: Account username
            platform: Platform name
            data_type: Type of data (posts, comments, profile)
            extension: File extension (json, csv, xlsx)

        Returns:
            Path to file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{platform}_{account}_{data_type}_{timestamp}.{extension}"
        return self.output_dir / filename

    @staticmethod
    def post_to_dict(post: Post) -> Dict[str, Any]:
        """Convert Post to dictionary for serialization."""
        return {
            "platform_id": post.platform_id,
            "account_id": post.account_id,
            "text": post.text,
            "likes": post.likes,
            "comments_count": post.comments_count,
            "shares": post.shares,
            "url": post.url,
            "media_type": post.media_type,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "platform": post.platform.value if hasattr(post.platform, 'value') else post.platform,
        }

    @staticmethod
    def comment_to_dict(comment: Comment) -> Dict[str, Any]:
        """Convert Comment to dictionary for serialization."""
        return {
            "platform_id": comment.platform_id,
            "post_id": comment.post_id,
            "author": {
                "platform_id": comment.author.platform_id,
                "username": comment.author.username,
                "display_name": comment.author.display_name,
                "is_verified": comment.author.is_verified,
            } if comment.author else None,
            "text": comment.text,
            "likes": comment.likes,
            "parent_id": comment.parent_id,
            "replies_count": comment.replies_count,
            "published_at": comment.published_at.isoformat() if comment.published_at else None,
            "platform": comment.platform.value if hasattr(comment.platform, 'value') else comment.platform,
        }

    @staticmethod
    def profile_to_dict(profile: Profile) -> Dict[str, Any]:
        """Convert Profile to dictionary for serialization."""
        return {
            "platform_id": profile.platform_id,
            "username": profile.username,
            "display_name": profile.display_name,
            "description": profile.description,
            "followers_count": profile.followers_count,
            "following_count": profile.following_count,
            "posts_count": profile.posts_count,
            "url": profile.url,
            "profile_image": profile.profile_image,
            "is_verified": profile.is_verified,
            "platform": profile.platform.value if hasattr(profile.platform, 'value') else profile.platform,
        }


class StorageFactory:
    """Factory for creating storage backends."""

    _backends: Dict[str, Type[StorageBackend]] = {}

    @classmethod
    def register(cls, format_name: str, backend_class: Type[StorageBackend]) -> None:
        """
        Register a storage backend.

        Args:
            format_name: Format identifier (json, csv, xlsx)
            backend_class: Storage backend class
        """
        cls._backends[format_name.lower()] = backend_class
        logger.debug(f"Registered storage backend: {format_name}")

    @classmethod
    def create(cls, format_name: str, output_dir: str) -> StorageBackend:
        """
        Create a storage backend instance.

        Args:
            format_name: Format identifier (json, csv, xlsx)
            output_dir: Directory for output files

        Returns:
            Storage backend instance

        Raises:
            ValueError: If format not supported
        """
        format_name = format_name.lower()
        if format_name not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise ValueError(
                f"Unknown storage format: {format_name}. "
                f"Available formats: {available}"
            )

        return cls._backends[format_name](output_dir)

    @classmethod
    def available_formats(cls) -> List[str]:
        """Get list of available storage formats."""
        return list(cls._backends.keys())
