"""Twitter Replies Section Page Object."""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class RepliesSection(BasePage):
    """Page object for Twitter reply extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def extract_replies_for_tweet(self, tweet_id: str) -> List[Dict[str, Any]]:
        logger.debug(f"EXTRACTING REPLIES | tweet_id={tweet_id}")

        self._load_more_replies()
        replies = self._extract_replies_js(tweet_id)

        logger.info(f"EXTRACTED {len(replies)} REPLIES | tweet_id={tweet_id}")
        return replies

    def _load_more_replies(self, max_loads: int = 100) -> None:
        """Load more replies by clicking show more buttons."""
        for i in range(max_loads):
            try:
                # Try show more replies
                if self.is_visible(Selectors.Replies.SHOW_MORE, timeout=1000):
                    self.click(Selectors.Replies.SHOW_MORE)
                    self.wait(1500)
                # Try show replies
                elif self.is_visible(Selectors.Replies.SHOW_REPLIES, timeout=500):
                    self.click(Selectors.Replies.SHOW_REPLIES)
                    self.wait(1500)
                else:
                    break
            except (PlaywrightTimeout, TimeoutError):
                break

    def _extract_replies_js(self, tweet_id: str) -> List[Dict[str, Any]]:
        try:
            replies_data = self.evaluate('''
                () => {
                    const replies = [];
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');

                    // Skip first article (main tweet)
                    for (let i = 1; i < articles.length; i++) {
                        const article = articles[i];
                        try {
                            let author = 'unknown';
                            const authorLink = article.querySelector('a[role="link"][href^="/"]');
                            if (authorLink) {
                                const href = authorLink.getAttribute('href');
                                author = href.replace('/', '');
                            }

                            let text = '';
                            const textDiv = article.querySelector('div[data-testid="tweetText"]');
                            if (textDiv) {
                                text = textDiv.textContent.trim();
                            }

                            if (!text) continue;

                            let timestamp = null;
                            const timeElem = article.querySelector('time');
                            if (timeElem) {
                                timestamp = timeElem.getAttribute('datetime');
                            }

                            // Extract likes count
                            let likes = 0;
                            const likeBtn = article.querySelector('div[data-testid="like"] span');
                            if (likeBtn) {
                                const likesText = likeBtn.textContent.trim();
                                const likesMatch = likesText.match(/\\d+/);
                                if (likesMatch) {
                                    likes = parseInt(likesMatch[0], 10);
                                }
                            }

                            // Extract reply count for this reply
                            let repliesCount = 0;
                            const replyBtn = article.querySelector('div[data-testid="reply"] span');
                            if (replyBtn) {
                                const repliesText = replyBtn.textContent.trim();
                                const repliesMatch = repliesText.match(/\\d+/);
                                if (repliesMatch) {
                                    repliesCount = parseInt(repliesMatch[0], 10);
                                }
                            }

                            replies.push({
                                author: author,
                                text: text,
                                timestamp: timestamp,
                                likes: likes,
                                replies_count: repliesCount,
                                index: i
                            });
                        } catch (e) {}
                    }
                    return replies;
                }
            ''')

            processed = []
            seen_texts = set()

            for i, reply in enumerate(replies_data):
                text = reply.get('text', '').strip()
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)

                timestamp = None
                if reply.get('timestamp'):
                    try:
                        timestamp = datetime.fromisoformat(reply['timestamp'].replace("Z", "+00:00"))
                    except ValueError:
                        pass

                processed.append({
                    'id': f"{tweet_id}_r{i}",
                    'author': reply.get('author', 'unknown'),
                    'text': text,
                    'published_at': timestamp,
                    'likes': reply.get('likes', 0),
                    'parent_id': None,
                    'replies_count': reply.get('replies_count', 0),
                })

            return processed

        except Exception as e:
            logger.warning(f"JS reply extraction failed: {e}")
            return []
