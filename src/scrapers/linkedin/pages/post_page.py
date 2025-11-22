"""LinkedIn Post Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from playwright.sync_api import Page
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
            urls = self.evaluate('''
                () => {
                    const links = [];
                    const seenUrls = new Set();

                    // Selectors for different LinkedIn post containers
                    const postSelectors = [
                        'div.feed-shared-update-v2',                    // Standard feed post
                        'div.org-grid-container__grid-item',             // Company page grid item
                        'article.org-update-item',                       // Company update item
                        'div.feed-shared-actor',                         // Feed shared actor
                        'li.occludable-update',                          // Occludable update item
                        'div[data-urn*="activity"]',                     // Any element with activity URN
                    ];

                    // Link selectors for finding post URLs
                    const linkSelectors = [
                        'a[href*="/feed/update/"]',                      // Standard activity link
                        'a[data-control-name="update_topbar_overflow_accessory"]',  // Topbar link
                        'a[href*="urn:li:activity:"]',                   // URN-based link
                    ];

                    // Try each post container selector
                    for (const postSelector of postSelectors) {
                        const posts = document.querySelectorAll(postSelector);
                        posts.forEach(post => {
                            // Try each link selector
                            for (const linkSelector of linkSelectors) {
                                const activityLink = post.querySelector(linkSelector);
                                if (activityLink && !seenUrls.has(activityLink.href)) {
                                    links.push(activityLink.href);
                                    seenUrls.add(activityLink.href);
                                    break;  // Found link for this post
                                }
                            }
                        });
                    }

                    // Also try to find any links with /feed/update/ directly
                    if (links.length === 0) {
                        const allActivityLinks = document.querySelectorAll('a[href*="/feed/update/"]');
                        allActivityLinks.forEach(link => {
                            if (!seenUrls.has(link.href)) {
                                links.push(link.href);
                                seenUrls.add(link.href);
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
