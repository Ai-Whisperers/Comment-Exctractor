"""Twitter Tweet Page Object."""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class TweetPage(BasePage):
    """Page object for Twitter tweet extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def get_tweet_links(
        self,
        username: str,
        max_tweets: int = 10,
        scroll_all: bool = False,
        known_post_ids: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Collect tweet links from profile page.

        Args:
            username: Twitter username
            max_tweets: Maximum number of tweets to collect
            scroll_all: If True, scroll more aggressively for larger extractions
            known_post_ids: Set of tweet IDs to skip (already extracted)

        Returns:
            List of tweet URLs
        """
        logger.info(f"COLLECTING TWEET LINKS | max={max_tweets} | scroll_all={scroll_all}")

        tweet_links = []
        seen_urls = set()
        known_post_ids = known_post_ids or set()
        scroll_attempts = 0
        max_scroll = 20 if scroll_all else 10
        no_new_tweets_count = 0

        while len(tweet_links) < max_tweets and scroll_attempts < max_scroll:
            articles = self.get_elements(Selectors.Tweet.TWEET_ARTICLE)

            new_tweets_this_scroll = 0
            for article in articles:
                if len(tweet_links) >= max_tweets:
                    break
                try:
                    link = article.locator(Selectors.Tweet.TWEET_LINK).first
                    href = link.get_attribute("href")
                    if href and "/status/" in href and href not in seen_urls:
                        seen_urls.add(href)

                        if not href.startswith("http"):
                            href = f"https://x.com{href}"

                        # Extract tweet ID to check against known_post_ids
                        tweet_id = self._extract_tweet_id_from_url(href)
                        if tweet_id and tweet_id in known_post_ids:
                            logger.debug(f"Skipping known tweet: {tweet_id}")
                            continue

                        tweet_links.append(href)
                        new_tweets_this_scroll += 1
                except Exception:
                    continue

            if len(tweet_links) >= max_tweets:
                break

            # Check if we're getting new tweets
            if new_tweets_this_scroll == 0:
                no_new_tweets_count += 1
                if no_new_tweets_count >= 3:
                    logger.info("No new tweets found after 3 scrolls, stopping")
                    break
            else:
                no_new_tweets_count = 0

            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.wait(2000)
            scroll_attempts += 1

            # Log progress
            if scroll_attempts % 5 == 0:
                logger.debug(f"Scroll {scroll_attempts}/{max_scroll} | tweets={len(tweet_links)}")

        logger.info(f"COLLECTED {len(tweet_links)} TWEET LINKS")
        return tweet_links

    def _extract_tweet_id_from_url(self, url: str) -> Optional[str]:
        """Extract tweet ID from Twitter URL."""
        match = re.search(r"/status/(\d+)", url)
        return match.group(1) if match else None

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
