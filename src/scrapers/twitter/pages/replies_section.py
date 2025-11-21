"""Twitter Replies Section Page Object."""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
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

    def _load_more_replies(self, max_loads: int = 5) -> None:
        for i in range(max_loads):
            try:
                if self.is_visible(Selectors.Replies.SHOW_MORE, timeout=1000):
                    self.click(Selectors.Replies.SHOW_MORE)
                    self.wait(1500)
                else:
                    break
            except Exception:
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

                            replies.push({
                                author: author,
                                text: text,
                                timestamp: timestamp,
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
                    except Exception:
                        pass

                processed.append({
                    'id': f"{tweet_id}_r{i}",
                    'author': reply.get('author', 'unknown'),
                    'text': text,
                    'published_at': timestamp,
                    'likes': 0,
                    'parent_id': None,
                    'replies_count': 0,
                })

            return processed

        except Exception as e:
            logger.warning(f"JS reply extraction failed: {e}")
            return []
