"""CSV storage backend implementation."""

import csv
import logging
from typing import List

from .base import StorageBackend, StorageFactory
from ..core.models import Post, Comment, Profile

logger = logging.getLogger(__name__)


class CSVStorage(StorageBackend):
    """CSV file storage backend."""

    def save_posts(
        self,
        posts: List[Post],
        account: str,
        platform: str
    ) -> str:
        """Save posts to CSV file."""
        filepath = self._generate_filename(account, platform, "posts", "csv")

        if not posts:
            return str(filepath)

        fieldnames = [
            "platform_id", "account_id", "text", "likes",
            "comments_count", "shares", "url", "media_type",
            "published_at", "platform"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for post in posts:
                writer.writerow(self.post_to_dict(post))

        logger.debug(f"Saved {len(posts)} posts to {filepath}")
        return str(filepath)

    def save_comments(
        self,
        comments: List[Comment],
        account: str,
        platform: str
    ) -> str:
        """Save comments to CSV file."""
        filepath = self._generate_filename(account, platform, "comments", "csv")

        if not comments:
            return str(filepath)

        fieldnames = [
            "platform_id", "post_id", "author", "text", "likes",
            "parent_id", "replies_count", "published_at", "platform"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for comment in comments:
                writer.writerow(self.comment_to_dict(comment))

        logger.debug(f"Saved {len(comments)} comments to {filepath}")
        return str(filepath)

    def save_profile(
        self,
        profile: Profile,
        account: str,
        platform: str
    ) -> str:
        """Save profile to CSV file."""
        filepath = self._generate_filename(account, platform, "profile", "csv")

        fieldnames = [
            "platform_id", "username", "display_name", "description",
            "followers_count", "following_count", "posts_count", "url",
            "profile_image", "is_verified", "platform"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(self.profile_to_dict(profile))

        logger.debug(f"Saved profile to {filepath}")
        return str(filepath)


# Register the backend
StorageFactory.register("csv", CSVStorage)
