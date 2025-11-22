"""Facebook Post Page Object."""

import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)

# Throttle detection constants
SCROLL_THROTTLE_THRESHOLD_MS = 30000  # 30 seconds = likely throttled
SCROLL_NORMAL_THRESHOLD_MS = 5000      # 5 seconds = normal response
THROTTLE_BACKOFF_MS = 45000            # 45 second wait when throttled
MAX_THROTTLE_RETRIES = 3               # Max retries before giving up


class PostPage(BasePage):
    """Page object for Facebook post extraction."""

    def __init__(self, page: Page):
        """
        Initialize post page.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)

    def get_post_links(
        self,
        max_posts: int = 10,
        scroll_all: bool = False,
        known_post_ids: set = None,
        skip_existing: bool = True
    ) -> List[str]:
        """
        Get post links from the current page.

        Args:
            max_posts: Maximum number of post links to collect
            scroll_all: Whether to scroll to load all posts
            known_post_ids: Set of post IDs already in database
            skip_existing: Stop when encountering existing posts (set False for full re-scrape)

        Returns:
            List of post URLs
        """
        logger.info(f"COLLECTING POST LINKS | max={max_posts} | scroll_all={scroll_all} | skip_existing={skip_existing}")

        # Get the page name from current URL to filter posts
        current_url = self.current_url
        page_name = None
        if "facebook.com/" in current_url:
            parts = current_url.split("facebook.com/")
            if len(parts) > 1:
                page_name = parts[1].split("/")[0].split("?")[0].lower()

        logger.debug(f"Filtering posts for page: {page_name}")

        post_links = []
        seen_post_ids = set()  # Track by post ID, not URL, to avoid duplicates
        scroll_attempts = 0
        max_scroll_attempts = 50 if scroll_all else 10
        no_new_posts_count = 0
        existing_posts_found = 0
        known_post_ids = known_post_ids or set()

        # Find all post links using multiple selectors
        # Facebook posts can have various URL patterns
        post_selectors = [
            "a[href*='/posts/']",
            "a[href*='/photos/']",
            "a[href*='/videos/']",
            "a[href*='story_fbid=']",
            "a[href*='/permalink/']",
            "a[href*='pfbid']",  # New Facebook post ID format
        ]

        while len(post_links) < max_posts and scroll_attempts < max_scroll_attempts:
            previous_count = len(post_links)

            for selector in post_selectors:
                if len(post_links) >= max_posts:
                    break

                try:
                    links = self.page.locator(selector).all()
                except Exception as e:
                    logger.warning(f"Error getting links with selector {selector}: {e}")
                    continue

                for link in links:
                    if len(post_links) >= max_posts:
                        break

                    try:
                        href = link.get_attribute("href")
                        if not href:
                            continue

                        # Skip non-post links
                        if '/groups/' in href or '/events/' in href:
                            continue

                        # Filter to only include posts from this page
                        if page_name:
                            href_lower = href.lower()
                            if f"/{page_name}/" not in href_lower and f"facebook.com/{page_name}" not in href_lower:
                                continue

                        # Normalize URL
                        if not href.startswith("http"):
                            href = f"https://www.facebook.com{href}"

                        # Extract post ID to check against known posts
                        post_id = self._extract_post_id_from_url(href)

                        # Use post ID for deduplication (key improvement)
                        # This prevents collecting same post with different URL params
                        dedup_key = post_id if post_id else href

                        if dedup_key in seen_post_ids:
                            continue

                        # Check if post already exists in database
                        if post_id and post_id in known_post_ids:
                            existing_posts_found += 1
                            logger.debug(f"Found existing post: {post_id}")

                            # Stop if we've found enough existing posts (indicates we've reached old content)
                            if skip_existing and existing_posts_found >= 3:
                                logger.info(f"Found {existing_posts_found} existing posts, stopping collection")
                                return post_links
                            continue

                        post_links.append(href)
                        seen_post_ids.add(dedup_key)
                        logger.debug(f"Found post link: {href[:80]}...")
                    except Exception:
                        continue

            # Check if we found new posts
            if len(post_links) == previous_count:
                no_new_posts_count += 1
                # Be more patient - wait for 10 empty scrolls before stopping
                if no_new_posts_count >= 10:
                    logger.info("No new posts found after 10 scrolls, stopping")
                    break
            else:
                no_new_posts_count = 0

            if len(post_links) >= max_posts:
                break

            # Scroll to load more with crash protection and throttle detection
            try:
                # Measure scroll response time to detect throttling
                scroll_start = time.time()
                self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.wait(2000)  # Initial wait for content
                scroll_attempts += 1

                # Measure how long it took
                scroll_time_ms = (time.time() - scroll_start) * 1000

                # Detect throttling based on response time
                if scroll_time_ms > SCROLL_THROTTLE_THRESHOLD_MS:
                    logger.warning(f"THROTTLE DETECTED | scroll took {scroll_time_ms/1000:.1f}s (threshold: {SCROLL_THROTTLE_THRESHOLD_MS/1000}s)")
                    logger.info(f"Backing off for {THROTTLE_BACKOFF_MS/1000}s to avoid rate limit...")
                    self.wait(THROTTLE_BACKOFF_MS)

                    # Track throttle events
                    if not hasattr(self, '_throttle_count'):
                        self._throttle_count = 0
                    self._throttle_count += 1

                    if self._throttle_count >= MAX_THROTTLE_RETRIES:
                        logger.warning(f"Too many throttle events ({self._throttle_count}), stopping to avoid ban")
                        if post_links:
                            logger.info(f"Returning {len(post_links)} posts collected before throttle limit")
                            return post_links
                        break
                elif scroll_time_ms > SCROLL_NORMAL_THRESHOLD_MS:
                    # Moderately slow - add small extra delay
                    logger.debug(f"Slow scroll response: {scroll_time_ms/1000:.1f}s, adding brief delay")
                    self.wait(3000)

                logger.info(f"Scroll {scroll_attempts}/{max_scroll_attempts} | posts: {len(post_links)} | time: {scroll_time_ms/1000:.1f}s")
            except Exception as scroll_error:
                logger.warning(f"Scroll error (possible browser crash): {scroll_error}")
                # Return what we have so far
                if post_links:
                    logger.info(f"Returning {len(post_links)} posts collected before crash")
                    return post_links
                break

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

    def _extract_post_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract post ID from a URL.

        Handles multiple Facebook URL formats:
        - /posts/123456789
        - story_fbid=123456789
        - /photos/a.123/456/
        - pfbid02abc... (base62 encoded, typically 20-30 chars)
        - /videos/123456789
        - /reel/123456789

        Args:
            url: The post URL

        Returns:
            Post ID or None if not found
        """
        # Try /posts/ pattern (most common)
        match = re.search(r"/posts/(\d+)", url)
        if match:
            return match.group(1)

        # Try story_fbid pattern (older format)
        match = re.search(r"story_fbid=(\d+)", url)
        if match:
            return match.group(1)

        # Try photo pattern with album
        match = re.search(r"/photos/[^/]+/(\d+)", url)
        if match:
            return match.group(1)

        # Try pfbid pattern (new Facebook format - base62 encoded)
        # pfbid is followed by 20-35 alphanumeric characters
        # More robust pattern: must be at least 20 chars to be valid
        match = re.search(r"pfbid([a-zA-Z0-9]{20,35})", url)
        if match:
            pfbid = f"pfbid{match.group(1)}"
            logger.debug(f"Extracted pfbid: {pfbid}")
            return pfbid

        # Try shorter pfbid (some are shorter, minimum 15 chars)
        match = re.search(r"pfbid([a-zA-Z0-9]{15,19})", url)
        if match:
            pfbid = f"pfbid{match.group(1)}"
            logger.debug(f"Extracted short pfbid: {pfbid}")
            return pfbid

        # Try video pattern
        match = re.search(r"/videos/(\d+)", url)
        if match:
            return match.group(1)

        # Try reel pattern (similar to video)
        match = re.search(r"/reel/(\d+)", url)
        if match:
            return match.group(1)

        # Try watch pattern (videos shared via watch)
        match = re.search(r"[?&]v=(\d+)", url)
        if match:
            return match.group(1)

        # Try permalink pattern
        match = re.search(r"/permalink/(\d+)", url)
        if match:
            return match.group(1)

        logger.debug(f"Could not extract post ID from URL: {url[:80]}...")
        return None

    def _get_post_id(self) -> str:
        """Extract post ID from current URL."""
        url = self.current_url
        post_id = self._extract_post_id_from_url(url)
        if post_id:
            return post_id

        # Generate from URL hash as fallback
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

    def _is_valid_count_text(self, text: str) -> bool:
        """
        Check if text looks like a valid count (not Facebook's obfuscated garbage).

        Facebook obfuscates some text with random letters/numbers like:
        'oedtsSropna0i52mds71tp198gtfe150eae818m2489ged61r1emc0b09'

        Valid counts look like:
        '417 reacciones', '41 veces compartida', '133 comments'

        Args:
            text: Text to validate

        Returns:
            True if text looks like a valid count
        """
        if not text:
            return False

        # If the text is very long and has many digit/letter alternations, it's garbage
        if len(text) > 100:
            return False

        # Count ratio of letters to digits - garbage has too many of each mixed
        letters = sum(1 for c in text if c.isalpha())
        digits = sum(1 for c in text if c.isdigit())

        # Valid: "41 veces compartida" (16 letters, 2 digits)
        # Garbage: "oedtsSropna0i52mds71..." (many letters AND many digits)
        if digits > 3 and letters > 20:
            # Check for number-letter alternation pattern (sign of obfuscation)
            alternations = 0
            for i in range(len(text) - 1):
                if (text[i].isdigit() and text[i+1].isalpha()) or \
                   (text[i].isalpha() and text[i+1].isdigit()):
                    alternations += 1

            if alternations > 5:
                return False

        return True

    def _get_reactions_count(self) -> int:
        """Get reactions count using JavaScript DOM traversal."""
        try:
            result = self.page.evaluate('''
                () => {
                    // Look for spans containing reaction-related text
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        // Match "Todas las reacciones:N" or "X reactions/reacciones"
                        if (/(reacciones|reactions)/i.test(text) && /\\d/.test(text)) {
                            // Must be reasonably short (avoid grabbing entire page sections)
                            if (text.length < 100) {
                                return text;
                            }
                        }
                        // Also check for aria-label on reaction buttons
                        const ariaLabel = span.getAttribute('aria-label') || '';
                        if (/(reaction|reaccion)/i.test(ariaLabel) && /\\d/.test(ariaLabel)) {
                            return ariaLabel;
                        }
                    }
                    return '';
                }
            ''')
            logger.debug(f"Reactions raw text: {repr(result)}")
            if result and self._is_valid_count_text(result):
                return self.parse_count(result)
        except Exception as e:
            logger.debug(f"Error getting reactions: {e}")
        return 0

    def _get_comments_count(self) -> int:
        """Get comments count using JavaScript DOM traversal."""
        try:
            result = self.page.evaluate('''
                () => {
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        // Match "X comentarios" or "X comments"
                        if (/(comentarios?|comments?)/i.test(text) && /\\d/.test(text)) {
                            // Must have number before the word
                            if (/^\\d/.test(text) || /^\\s*\\d/.test(text)) {
                                return text;
                            }
                        }
                    }
                    return '';
                }
            ''')
            if result and self._is_valid_count_text(result):
                return self.parse_count(result)
        except Exception as e:
            logger.debug(f"Error getting comments: {e}")
        return 0

    def _get_shares_count(self) -> int:
        """Get shares count using JavaScript DOM traversal."""
        try:
            result = self.page.evaluate('''
                () => {
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        // Match "X shares", "X veces compartida", "X vez compartido"
                        // Avoid "Compartido con:" which is privacy setting
                        if (/(shares?|veces?\\s+compartid)/i.test(text) && /\\d/.test(text)) {
                            // Must not be privacy setting
                            if (!/compartido\\s+con/i.test(text)) {
                                return text;
                            }
                        }
                    }
                    return '';
                }
            ''')
            if result and self._is_valid_count_text(result):
                return self.parse_count(result)
        except Exception as e:
            logger.debug(f"Error getting shares: {e}")
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
