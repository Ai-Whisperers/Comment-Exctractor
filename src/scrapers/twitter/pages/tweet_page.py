"""Twitter Tweet Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class TweetPage(BasePage):
    """Page object for Twitter tweet extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def get_tweet_links(self, username: str, max_tweets: int = 10) -> List[str]:
        logger.info(f"COLLECTING TWEET LINKS | max={max_tweets}")

        tweet_links = []
        seen_urls = set()
        scroll_attempts = 0
        max_scroll = 10

        while len(tweet_links) < max_tweets and scroll_attempts < max_scroll:
            articles = self.get_elements(Selectors.Tweet.TWEET_ARTICLE)

            for article in articles:
                if len(tweet_links) >= max_tweets:
                    break
                try:
                    link = article.locator(Selectors.Tweet.TWEET_LINK).first
                    href = link.get_attribute("href")
                    if href and "/status/" in href and href not in seen_urls:
                        if not href.startswith("http"):
                            href = f"https://x.com{href}"
                        tweet_links.append(href)
                        seen_urls.add(href)
                except Exception:
                    continue

            if len(tweet_links) >= max_tweets:
                break

            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.wait(2000)
            scroll_attempts += 1

        logger.info(f"COLLECTED {len(tweet_links)} TWEET LINKS")
        return tweet_links

    def extract_tweet_data(self, username: str) -> Dict[str, Any]:
        tweet_id = self._get_tweet_id()
        return {
            "id": tweet_id,
            "url": self.current_url,
            "text": self._get_tweet_text(),
            "likes": self._get_like_count(),
            "retweets": self._get_retweet_count(),
            "replies": self._get_reply_count(),
            "timestamp": self._get_timestamp(),
            "media_type": self._get_media_type(),
        }

    def _get_tweet_id(self) -> str:
        match = re.search(r"/status/(\d+)", self.current_url)
        return match.group(1) if match else str(hash(self.current_url) % 10**10)

    def _get_tweet_text(self) -> str:
        return self.get_text(Selectors.Tweet.TWEET_TEXT, timeout=2000) or ""

    def _get_like_count(self) -> int:
        text = self.get_text(Selectors.Tweet.LIKE_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_retweet_count(self) -> int:
        text = self.get_text(Selectors.Tweet.RETWEET_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_reply_count(self) -> int:
        text = self.get_text(Selectors.Tweet.REPLY_COUNT, timeout=2000)
        return self.parse_count(text) if text else 0

    def _get_timestamp(self) -> Optional[datetime]:
        try:
            time_elem = self.page.locator(Selectors.Tweet.TIME_ELEMENT).first
            if time_elem.is_visible(timeout=2000):
                datetime_str = time_elem.get_attribute("datetime")
                if datetime_str:
                    return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except Exception:
            pass
        return None

    def _get_media_type(self) -> str:
        if self.is_visible(Selectors.Tweet.VIDEO, timeout=1000):
            return "video"
        if self.is_visible(Selectors.Tweet.IMAGE, timeout=1000):
            return "image"
        return "text"
