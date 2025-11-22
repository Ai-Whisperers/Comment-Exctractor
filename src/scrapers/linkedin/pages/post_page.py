"""LinkedIn Post Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class PostPage(BasePage):
    """Page object for LinkedIn post extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def get_post_links(
        self,
        username: str,
        max_posts: int = 10,
        scroll_all: bool = False,
        known_post_ids: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Collect post links from the activity page.

        Args:
            username: LinkedIn username
            max_posts: Maximum number of posts to collect
            scroll_all: If True, scroll more aggressively for larger extractions
            known_post_ids: Set of post IDs to skip (already extracted)

        Returns:
            List of post URLs
        """
        logger.info(f"COLLECTING POST LINKS | max={max_posts} | scroll_all={scroll_all}")

        # Log current URL for debugging
        current_url = self.page.url
        logger.debug(f"COLLECTING | current URL: {current_url}")

        # Wait for posts to load - company pages can be slow
        self.wait(5000)

        post_links = []
        seen_urls = set()
        known_post_ids = known_post_ids or set()
        scroll_attempts = 0
        max_scroll = 30 if scroll_all else 15
        no_new_posts_count = 0

        while len(post_links) < max_posts and scroll_attempts < max_scroll:
            # Extract post URLs from feed using JS
            # Try multiple selectors for different LinkedIn page layouts
            urls = self.evaluate(r'''
                () => {
                    const links = [];
                    const seenIds = new Set();

                    // Method 1: Find links with /feed/update/ URLs
                    const feedUpdateLinks = document.querySelectorAll('a[href*="/feed/update/"]');
                    feedUpdateLinks.forEach(link => {
                        const match = link.href.match(/activity:(\d+)/);
                        if (match && !seenIds.has(match[1])) {
                            seenIds.add(match[1]);
                            links.push(link.href);
                        }
                    });

                    // Method 2: Find occludable-update elements with data-urn
                    const occludableUpdates = document.querySelectorAll('li.occludable-update, div[data-id*="urn:li:activity"]');
                    occludableUpdates.forEach(element => {
                        const dataUrn = element.getAttribute('data-id') || element.getAttribute('data-urn');
                        if (dataUrn) {
                            const match = dataUrn.match(/activity:(\d+)/);
                            if (match && !seenIds.has(match[1])) {
                                seenIds.add(match[1]);
                                // Construct feed update URL from URN
                                links.push(`https://www.linkedin.com/feed/update/urn:li:activity:${match[1]}/`);
                            }
                        }
                    });

                    // Method 3: Extract activity IDs from any element with data attributes containing activity URNs
                    const elementsWithUrns = document.querySelectorAll('[data-urn*="activity:"], [data-id*="activity:"]');
                    elementsWithUrns.forEach(element => {
                        const urn = element.getAttribute('data-urn') || element.getAttribute('data-id');
                        if (urn) {
                            const match = urn.match(/activity:(\d+)/);
                            if (match && !seenIds.has(match[1])) {
                                seenIds.add(match[1]);
                                links.push(`https://www.linkedin.com/feed/update/urn:li:activity:${match[1]}/`);
                            }
                        }
                    });

                    // Method 4: Search for activity URNs in the page content (last resort)
                    if (links.length === 0) {
                        const pageContent = document.body.innerHTML;
                        const urnMatches = pageContent.match(/urn:li:activity:(\d+)/g) || [];
                        const uniqueUrns = [...new Set(urnMatches)];
                        uniqueUrns.forEach(urn => {
                            const match = urn.match(/activity:(\d+)/);
                            if (match && !seenIds.has(match[1])) {
                                seenIds.add(match[1]);
                                links.push(`https://www.linkedin.com/feed/update/${urn}/`);
                            }
                        });
                    }

                    return links;
                }
            ''')

            new_posts_this_scroll = 0
            for url in urls:
                if len(post_links) >= max_posts:
                    break
                if url not in seen_urls:
                    seen_urls.add(url)

                    # Extract post ID to check against known_post_ids
                    post_id = self._extract_post_id_from_url(url)
                    if post_id and post_id in known_post_ids:
                        logger.debug(f"Skipping known post: {post_id}")
                        continue

                    post_links.append(url)
                    new_posts_this_scroll += 1

            if len(post_links) >= max_posts:
                break

            # Check if we're getting new posts
            if new_posts_this_scroll == 0:
                no_new_posts_count += 1
                if no_new_posts_count >= 3:
                    logger.info("No new posts found after 3 scrolls, stopping")
                    break
            else:
                no_new_posts_count = 0

            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.wait(2000)
            scroll_attempts += 1

            # Log progress
            if scroll_attempts % 5 == 0:
                logger.debug(f"Scroll {scroll_attempts}/{max_scroll} | posts={len(post_links)}")

        logger.info(f"COLLECTED {len(post_links)} POST LINKS")

        # Save debug HTML if no posts found
        if len(post_links) == 0:
            self.save_debug_html("no_posts_found", f"username={username}")

        return post_links

    def _extract_post_id_from_url(self, url: str) -> Optional[str]:
        """Extract post ID from LinkedIn URL."""
        match = re.search(r'activity:(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'urn:li:activity:(\d+)', url)
        if match:
            return match.group(1)
        return None

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
        except (PlaywrightTimeout, TimeoutError, ValueError):
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
