"""LinkedIn Comments Section Page Object."""

import logging
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class CommentsSection(BasePage):
    """Page object for LinkedIn comment extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def extract_comments_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        logger.debug(f"EXTRACTING COMMENTS | post_id={post_id}")

        # Open comments section
        self._expand_comments()
        self._load_more_comments()
        comments = self._extract_comments_js(post_id)

        logger.info(f"EXTRACTED {len(comments)} COMMENTS | post_id={post_id}")
        return comments

    def _expand_comments(self) -> None:
        """Click to expand comments section."""
        try:
            if self.is_visible(Selectors.Comments.COMMENTS_BUTTON, timeout=2000):
                self.click(Selectors.Comments.COMMENTS_BUTTON)
                self.wait(2000)
        except Exception as e:
            logger.debug(f"Failed to expand comments: {e}")

    def _load_more_comments(self, max_loads: int = 5) -> None:
        for i in range(max_loads):
            try:
                if self.is_visible(Selectors.Comments.LOAD_MORE, timeout=1000):
                    self.click(Selectors.Comments.LOAD_MORE)
                    self.wait(1500)
                else:
                    break
            except Exception:
                break

    def _extract_comments_js(self, post_id: str) -> List[Dict[str, Any]]:
        try:
            comments_data = self.evaluate('''
                () => {
                    const comments = [];
                    const commentElements = document.querySelectorAll('article.comments-comment-item');

                    commentElements.forEach((comment, index) => {
                        try {
                            let author = 'unknown';
                            const authorElem = comment.querySelector('span.comments-post-meta__name-text');
                            if (authorElem) {
                                author = authorElem.textContent.trim();
                            }

                            let text = '';
                            const textElem = comment.querySelector('span.comments-comment-item__main-content');
                            if (textElem) {
                                text = textElem.textContent.trim();
                            }

                            if (!text) return;

                            let timestamp = null;
                            const timeElem = comment.querySelector('time.comments-comment-item__timestamp');
                            if (timeElem) {
                                timestamp = timeElem.getAttribute('datetime');
                            }

                            comments.push({
                                author: author,
                                text: text,
                                timestamp: timestamp,
                                index: index
                            });
                        } catch (e) {}
                    });
                    return comments;
                }
            ''')

            processed = []
            seen_texts = set()

            for i, comment in enumerate(comments_data):
                text = comment.get('text', '').strip()
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)

                timestamp = None
                if comment.get('timestamp'):
                    try:
                        timestamp = datetime.fromisoformat(comment['timestamp'].replace("Z", "+00:00"))
                    except Exception:
                        pass

                processed.append({
                    'id': f"{post_id}_c{i}",
                    'author': comment.get('author', 'unknown'),
                    'text': text,
                    'published_at': timestamp,
                    'likes': 0,
                    'parent_id': None,
                    'replies_count': 0,
                })

            return processed

        except Exception as e:
            logger.warning(f"JS comment extraction failed: {e}")
            return []
