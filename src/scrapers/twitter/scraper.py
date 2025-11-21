"""Twitter Scraper using Page Object Model architecture."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict, Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from ...core.models import (
    Platform,
    Post,
    Profile,
    Comment,
    Author,
    ExtractionResult,
)
from ...core.exceptions import (
    AuthenticationError,
    PrivateAccountError,
    RateLimitError,
)
from ..base import BaseScraper
from ..shared.constants import TIMEOUTS
from .pages import LoginPage, ProfilePage, TweetPage, RepliesSection
from .selectors import Selectors

logger = logging.getLogger(__name__)


class TwitterScraper(BaseScraper):
    """
    Twitter scraper using Page Object Model pattern.

    This scraper uses a clean separation between page interactions
    (via Page Objects) and business logic (in this class).
    """

    platform = Platform.TWITTER

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Twitter scraper.

        Args:
            config: Configuration dictionary with credentials and settings
        """
        super().__init__(config)

        # Credentials (support both flat and nested config)
        credentials = config.get("credentials", {})
        self._username = credentials.get("username") or config.get("username")
        self._password = credentials.get("password") or config.get("password")

        # Browser settings
        browser_config = config.get("browser", {})
        self._headless = browser_config.get("headless", config.get("headless", False))
        self._browser_profile = browser_config.get("profile_dir") or config.get("browser_profile")

        # Session
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._tweet_page: Optional[TweetPage] = None
        self._replies_section: Optional[RepliesSection] = None

        # Initialize browser
        self._init_browser()

    def _init_browser(self):
        """Initialize Playwright browser and page objects."""
        logger.info("BROWSER INIT | platform=twitter | headless=%s", self._headless)

        self._playwright = sync_playwright().start()

        # Check for persistent browser profile
        if self._browser_profile and Path(self._browser_profile).exists():
            # Use persistent context with existing browser profile
            logger.info(f"BROWSER INIT | using persistent context from {self._browser_profile}")
            self._context = self._playwright.chromium.launch_persistent_context(
                self._browser_profile,
                headless=self._headless,
                viewport={"width": 1280, "height": 800},
                user_agent=self._current_user_agent,
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            # Create new browser profile directory if specified
            if self._browser_profile:
                Path(self._browser_profile).mkdir(parents=True, exist_ok=True)
                logger.info(f"BROWSER INIT | creating new persistent context at {self._browser_profile}")
                self._context = self._playwright.chromium.launch_persistent_context(
                    self._browser_profile,
                    headless=self._headless,
                    viewport={"width": 1280, "height": 800},
                    user_agent=self._current_user_agent,
                )
                self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            else:
                # Non-persistent browser
                self._browser = self._playwright.chromium.launch(headless=self._headless)
                self._context = self._browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=self._current_user_agent,
                )
                self._page = self._context.new_page()

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._tweet_page = TweetPage(self._page)
        self._replies_section = RepliesSection(self._page)

        logger.info("PAGE OBJECTS | initialized login, profile, tweet, replies")

    def close(self):
        """Clean up browser resources."""
        logger.info("BROWSER CLEANUP | platform=twitter")
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _ensure_logged_in(self) -> None:
        """Ensure we are logged in to Twitter."""
        self._page.goto(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

        if not self._login_page.is_logged_in():
            if not self._username or not self._password:
                raise AuthenticationError(
                    "Twitter credentials not configured",
                    platform=self.platform.value
                )

            logger.info("LOGIN | attempting login for %s", self._username)
            self._login_page.login(self._username, self._password)

            # Verify login succeeded
            self._page.wait_for_timeout(TIMEOUTS.LONG_WAIT)
            if not self._login_page.is_logged_in():
                raise AuthenticationError(
                    "Twitter login failed",
                    platform=self.platform.value
                )

            logger.info("LOGIN SUCCESS | user=%s", self._username)
        else:
            logger.info("LOGIN | already logged in (session restored)")

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape Twitter profile information.

        Args:
            account_id: Twitter username

        Returns:
            Profile model with account information
        """
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            logger.warning(f"Profile not available: {account_id}")
            # Return minimal profile
            return Profile(
                platform=Platform.TWITTER,
                username=account_id,
                display_name=account_id,
                followers=0,
                following=0,
            )

        return Profile(
            platform=Platform.TWITTER,
            username=account_id,
            display_name=self._profile_page.get_display_name() or account_id,
            followers=self._profile_page.get_followers_count(),
            following=self._profile_page.get_following_count(),
            is_verified=self._profile_page.is_verified(),
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int
    ) -> Iterator[ExtractionResult]:
        """
        Scrape tweets and their replies.

        Args:
            account_id: Twitter username
            since_date: Only get posts after this date (optional)
            max_posts: Maximum number of posts to scrape

        Yields:
            ExtractionResult with post and comments
        """
        logger.info(f"SCRAPING TWEETS | target={account_id} | max={max_posts}")

        # Ensure logged in
        self._ensure_logged_in()

        # Navigate to profile
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            logger.warning(f"Profile not available: {account_id}")
            return

        # Get tweet links
        tweet_links = self._tweet_page.get_tweet_links(account_id, max_posts)
        logger.info(f"Found {len(tweet_links)} tweets to process")

        for idx, tweet_url in enumerate(tweet_links, 1):
            try:
                logger.info(f"PROCESSING TWEET {idx}/{len(tweet_links)} | url={tweet_url}")

                # Navigate to tweet
                self._page.goto(tweet_url, wait_until="domcontentloaded")
                self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

                # Extract tweet data
                tweet_data = self._tweet_page.extract_tweet_data(account_id)

                # Check date filter
                tweet_date = tweet_data.get("timestamp")
                if since_date and tweet_date:
                    try:
                        if isinstance(tweet_date, str):
                            tweet_datetime = datetime.fromisoformat(tweet_date.replace('Z', '+00:00'))
                        else:
                            tweet_datetime = tweet_date
                        if tweet_datetime.replace(tzinfo=None) < since_date:
                            logger.debug(f"Skipping tweet {tweet_data.get('id')} - before since_date")
                            continue
                    except (ValueError, TypeError):
                        pass  # If we can't parse date, include the tweet

                # Create Post model
                post = Post(
                    platform=Platform.TWITTER,
                    platform_id=tweet_data.get("id", f"tweet_{idx}"),
                    url=tweet_url,
                    text=tweet_data.get("text", ""),
                    likes=tweet_data.get("likes", 0),
                    comments_count=tweet_data.get("replies", 0),
                    shares=tweet_data.get("retweets", 0),
                    published_at=tweet_date if isinstance(tweet_date, datetime) else None,
                    author=Author(
                        username=account_id,
                        display_name=tweet_data.get("author_name", account_id),
                    ),
                )

                # Extract replies
                replies_data = self._replies_section.extract_replies_for_tweet(tweet_data.get("id", ""))

                comments = []
                for reply in replies_data:
                    comment = Comment(
                        platform=Platform.TWITTER,
                        platform_id=reply.get("id", f"reply_{len(comments)}"),
                        post_id=post.platform_id,
                        text=reply.get("text", ""),
                        likes=reply.get("likes", 0),
                        published_at=reply.get("timestamp") if isinstance(reply.get("timestamp"), datetime) else None,
                        author=Author(
                            username=reply.get("author", "unknown"),
                            display_name=reply.get("author_name", reply.get("author", "unknown")),
                        ),
                    )
                    comments.append(comment)

                logger.info(f"Tweet {idx} extracted | replies={len(comments)}")

                yield ExtractionResult(post=post, comments=comments)

                # Human-like delay
                self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

            except Exception as e:
                logger.error(f"Error processing tweet {tweet_url}: {e}")
                continue

        logger.info(f"COMPLETED | total_tweets={len(tweet_links)}")
