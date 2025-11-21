"""LinkedIn Post Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class PostPage(BasePage):
    """Page object for LinkedIn post extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def get_post_links(self, username: str, max_posts: int = 10) -> List[str]:
        logger.info(f"COLLECTING POST LINKS | max={max_posts}")

        post_links = []
        seen_urls = set()
        scroll_attempts = 0
        max_scroll = 15

        while len(post_links) < max_posts and scroll_attempts < max_scroll:
            # Extract post URLs from feed using JS
            urls = self.evaluate('''
                () => {
                    const links = [];
                    const posts = document.querySelectorAll('div.feed-shared-update-v2');
                    posts.forEach(post => {
                        const activityLink = post.querySelector('a[href*="/feed/update/"]');
                        if (activityLink) {
                            links.push(activityLink.href);
                        }
                    });
                    return links;
                }
            ''')

            for url in urls:
                if len(post_links) >= max_posts:
                    break
                if url not in seen_urls:
                    post_links.append(url)
                    seen_urls.add(url)

            if len(post_links) >= max_posts:
                break

            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.wait(2000)
            scroll_attempts += 1

        logger.info(f"COLLECTED {len(post_links)} POST LINKS")
        return post_links

    def extract_post_data(self, username: str) -> Dict[str, Any]:
        post_id = self._get_post_id()
        return {
            "id": post_id,
            "url": self.current_url,
            "text": self._get_post_text(),
            "likes": self._get_like_count(),
            "comments": self._get_comment_count(),
            "reposts": self._get_repost_count(),
            "timestamp": self._get_timestamp(),
            "media_type": self._get_media_type(),
        }

    def _get_post_id(self) -> str:
        match = re.search(r'activity:(\d+)', self.current_url)
        if match:
            return match.group(1)
        match = re.search(r'urn:li:activity:(\d+)', self.current_url)
        if match:
            return match.group(1)
        return str(hash(self.current_url) % 10**10)

    def _get_post_text(self) -> str:
        text = self.get_text(Selectors.Post.POST_TEXT, timeout=2000)
        if not text:
            text = self.get_text(Selectors.Post.POST_TEXT_ALT, timeout=2000)
        return text or ""

    def _get_like_count(self) -> int:
        text = self.get_text(Selectors.Post.LIKE_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_comment_count(self) -> int:
        text = self.get_text(Selectors.Post.COMMENT_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_repost_count(self) -> int:
        text = self.get_text(Selectors.Post.REPOST_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_timestamp(self) -> Optional[datetime]:
        try:
            time_elem = self.page.locator(Selectors.Post.TIME_ELEMENT).first
            if time_elem.is_visible(timeout=2000):
                datetime_str = time_elem.get_attribute("datetime")
                if datetime_str:
                    return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except Exception:
            pass
        return None

    def _get_media_type(self) -> str:
        if self.is_visible(Selectors.Post.VIDEO, timeout=1000):
            return "video"
        if self.is_visible(Selectors.Post.IMAGE, timeout=1000):
            return "image"
        if self.is_visible(Selectors.Post.ARTICLE_LINK, timeout=1000):
            return "article"
        return "text"
