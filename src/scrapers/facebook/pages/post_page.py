"""Facebook Post Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class PostPage(BasePage):
    """Page object for Facebook post extraction."""

    def __init__(self, page: Page):
        """
        Initialize post page.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)

    def get_post_links(self, max_posts: int = 10, scroll_all: bool = False) -> List[str]:
        """
        Get post links from the current page.

        Args:
            max_posts: Maximum number of post links to collect
            scroll_all: Whether to scroll to load all posts

        Returns:
            List of post URLs
        """
        logger.info(f"COLLECTING POST LINKS | max={max_posts} | scroll_all={scroll_all}")

        post_links = []
        seen_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 20 if scroll_all else 5

        while len(post_links) < max_posts and scroll_attempts < max_scroll_attempts:
            # Find all post links
            links = self.page.locator(Selectors.Post.POST_LINK).all()

            for link in links:
                if len(post_links) >= max_posts:
                    break

                try:
                    href = link.get_attribute("href")
                    if href and href not in seen_urls:
                        # Normalize URL
                        if not href.startswith("http"):
                            href = f"https://www.facebook.com{href}"
                        post_links.append(href)
                        seen_urls.add(href)
                except Exception:
                    continue

            if len(post_links) >= max_posts:
                break

            # Scroll to load more
            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.wait(2000)
            scroll_attempts += 1

        logger.info(f"COLLECTED {len(post_links)} POST LINKS")
        return post_links

    def extract_post_data(self, page_name: str) -> Dict[str, Any]:
        """
        Extract data from the current post.

        Args:
            page_name: Name of the page/profile

        Returns:
            Dictionary with post data
        """
        post_id = self._get_post_id()

        return {
            "id": post_id,
            "url": self.current_url,
            "text": self._get_post_text(),
            "likes": self._get_reactions_count(),
            "comments_count": self._get_comments_count(),
            "shares": self._get_shares_count(),
            "timestamp": self._get_timestamp(),
            "media_type": self._get_media_type(),
        }

    def _get_post_id(self) -> str:
        """Extract post ID from URL."""
        url = self.current_url

        # Try /posts/ pattern
        match = re.search(r"/posts/(\d+)", url)
        if match:
            return match.group(1)

        # Try story_fbid pattern
        match = re.search(r"story_fbid=(\d+)", url)
        if match:
            return match.group(1)

        # Try photo pattern
        match = re.search(r"/photos/[^/]+/(\d+)", url)
        if match:
            return match.group(1)

        # Generate from URL hash
        return str(hash(url) % 10**10)

    def _get_post_text(self) -> str:
        """Get post text content."""
        # Try multiple selectors
        selectors = [
            Selectors.Post.POST_MESSAGE,
            "div[data-ad-comet-preview='message']",
            "div[dir='auto']",
        ]

        for selector in selectors:
            text = self.get_text(selector, timeout=2000)
            if text and len(text) > 10:
                return text

        return ""

    def _get_reactions_count(self) -> int:
        """Get reactions count."""
        text = self.get_text(Selectors.Post.REACTIONS_COUNT, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def _get_comments_count(self) -> int:
        """Get comments count."""
        text = self.get_text(Selectors.Post.COMMENTS_COUNT, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def _get_shares_count(self) -> int:
        """Get shares count."""
        text = self.get_text(Selectors.Post.SHARES_COUNT, timeout=2000)
        if text:
            return self.parse_count(text)
        return 0

    def _get_timestamp(self) -> Optional[datetime]:
        """Get post timestamp."""
        # Facebook uses relative time, try to parse
        text = self.get_text(Selectors.Post.POST_TIME, timeout=2000)
        if text:
            return self._parse_facebook_time(text)
        return None

    def _get_media_type(self) -> str:
        """Determine media type of post."""
        if self.is_visible(Selectors.Post.VIDEO, timeout=1000):
            return "video"
        if self.is_visible(Selectors.Post.IMAGE, timeout=1000):
            return "image"
        return "text"

    @staticmethod
    def _parse_facebook_time(time_text: str) -> Optional[datetime]:
        """
        Parse Facebook's relative time format.

        Args:
            time_text: Time text like "2h", "Yesterday", etc.

        Returns:
            Datetime object or None
        """
        from datetime import timedelta
        now = datetime.now()
        time_text = time_text.lower().strip()

        try:
            if "just now" in time_text:
                return now
            elif "min" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    minutes = int(match.group(1))
                    return now - timedelta(minutes=minutes)
            elif "hour" in time_text or "hr" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)
            elif "day" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    days = int(match.group(1))
                    return now - timedelta(days=days)
            elif "yesterday" in time_text:
                return now - timedelta(days=1)
        except Exception:
            pass

        return None
