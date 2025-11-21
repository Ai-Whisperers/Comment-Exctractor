"""JSON storage backend implementation."""

import json
import logging
from typing import List

from .base import StorageBackend, StorageFactory
from ..core.models import Post, Comment, Profile

logger = logging.getLogger(__name__)


class JSONStorage(StorageBackend):
    """JSON file storage backend."""

    def save_posts(
        self,
        posts: List[Post],
        account: str,
        platform: str
    ) -> str:
        """Save posts to JSON file."""
        filepath = self._generate_filename(account, platform, "posts", "json")

        data = [self.post_to_dict(post) for post in posts]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {len(posts)} posts to {filepath}")
        return str(filepath)

    def save_comments(
        self,
        comments: List[Comment],
        account: str,
        platform: str
    ) -> str:
        """Save comments to JSON file."""
        filepath = self._generate_filename(account, platform, "comments", "json")

        data = [self.comment_to_dict(comment) for comment in comments]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {len(comments)} comments to {filepath}")
        return str(filepath)

    def save_profile(
        self,
        profile: Profile,
        account: str,
        platform: str
    ) -> str:
        """Save profile to JSON file."""
        filepath = self._generate_filename(account, platform, "profile", "json")

        data = self.profile_to_dict(profile)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved profile to {filepath}")
        return str(filepath)


# Register the backend
StorageFactory.register("json", JSONStorage)
