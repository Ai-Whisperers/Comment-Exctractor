"""Facebook Comments Section Page Object."""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class CommentsSection(BasePage):
    """Page object for Facebook comment extraction."""

    def __init__(self, page: Page):
        """
        Initialize comments section.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)

    def extract_comments_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Extract all comments from the current post.

        Args:
            post_id: ID of the parent post

        Returns:
            List of comment dictionaries
        """
        logger.debug(f"EXTRACTING COMMENTS | post_id={post_id}")

        # Load more comments first
        self._load_all_comments()

        # Extract comments using JavaScript for better performance
        comments = self._extract_comments_js(post_id)

        logger.info(f"EXTRACTED {len(comments)} COMMENTS | post_id={post_id}")
        return comments

    def _load_all_comments(self, max_loads: int = 10) -> None:
        """
        Load all comments by clicking 'View more comments'.

        Args:
            max_loads: Maximum number of times to load more
        """
        for i in range(max_loads):
            try:
                # Try different load more selectors
                load_more = self.page.locator(Selectors.Comments.VIEW_MORE_COMMENTS).first
                if load_more.is_visible(timeout=1000):
                    load_more.click()
                    self.wait(1500)
                    continue

                # Try view previous
                view_prev = self.page.locator(Selectors.Comments.VIEW_PREVIOUS).first
                if view_prev.is_visible(timeout=1000):
                    view_prev.click()
                    self.wait(1500)
                    continue

                # No more to load
                break

            except Exception as e:
                logger.debug(f"Load more comments stopped: {e}")
                break

    def _extract_comments_js(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Extract comments using JavaScript for better performance.

        Args:
            post_id: ID of the parent post

        Returns:
            List of comment dictionaries
        """
        try:
            comments_data = self.evaluate('''
                () => {
                    const comments = [];

                    // Find all comment containers
                    const commentElements = document.querySelectorAll('[aria-label*="Comment"], [role="article"]');

                    commentElements.forEach((elem, index) => {
                        try {
                            // Get author - look for links
                            let author = 'unknown';
                            const authorLink = elem.querySelector('a[role="link"] span');
                            if (authorLink) {
                                author = authorLink.textContent.trim();
                            }

                            // Get comment text
                            let text = '';
                            const textElements = elem.querySelectorAll('div[dir="auto"]');
                            for (const textEl of textElements) {
                                const content = textEl.textContent.trim();
                                if (content && content.length > text.length && !content.includes('Like') && !content.includes('Reply')) {
                                    text = content;
                                }
                            }

                            // Skip if no text
                            if (!text || text.length < 2) return;

                            // Get timestamp
                            let timestamp = null;
                            const timeLink = elem.querySelector('a[href*="comment_id"]');
                            if (timeLink) {
                                timestamp = timeLink.textContent.trim();
                            }

                            // Get likes - look for reaction count
                            let likes = 0;
                            const likeSpan = elem.querySelector('span[aria-label*="reaction"]');
                            if (likeSpan) {
                                const match = likeSpan.textContent.match(/\\d+/);
                                if (match) likes = parseInt(match[0]);
                            }

                            comments.push({
                                author: author,
                                text: text,
                                timestamp: timestamp,
                                likes: likes,
                                index: index
                            });
                        } catch (e) {
                            // Skip problematic elements
                        }
                    });

                    return comments;
                }
            ''')

            # Process and deduplicate
            processed = []
            seen_texts = set()

            for i, comment in enumerate(comments_data):
                text = comment.get('text', '').strip()

                # Skip duplicates and empty
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)

                processed.append({
                    'id': f"{post_id}_c{i}",
                    'author': comment.get('author', 'unknown'),
                    'text': text,
                    'published_at': self._parse_timestamp(comment.get('timestamp')),
                    'likes': comment.get('likes', 0),
                    'parent_id': None,
                    'replies_count': 0,
                })

            return processed

        except Exception as e:
            logger.warning(f"JS comment extraction failed: {e}")
            return []

    def _parse_timestamp(self, time_text: Optional[str]) -> Optional[datetime]:
        """Parse Facebook timestamp."""
        if not time_text:
            return None

        from datetime import timedelta
        now = datetime.now()
        time_text = time_text.lower().strip()

        try:
            if "just now" in time_text:
                return now
            elif "min" in time_text or "m" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - timedelta(minutes=int(match.group(1)))
            elif "h" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - timedelta(hours=int(match.group(1)))
            elif "d" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - timedelta(days=int(match.group(1)))
            elif "w" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - timedelta(weeks=int(match.group(1)))
        except Exception:
            pass

        return None
