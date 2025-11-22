"""Twitter Scraper using Page Object Model architecture."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict, Any, Set

from playwright.sync_api import Page

from ...core.models import (
    Platform,
    Post,
    Profile,
    ExtractionResult,
)
from ...core.exceptions import (
    AuthenticationError,
    AccountNotFoundError,
    RateLimitError,
)
from ..base import BaseScraper
from ..shared.browser_manager import BrowserManager, BrowserConfig
from ..shared.rate_limiting import TwitterRateLimitDetector
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

        # Google OAuth credentials
        google_auth = config.get("google_auth", {})
        self._use_google_auth = google_auth.get("enabled", False)
        self._google_email = google_auth.get("email")
        self._google_password = google_auth.get("password")

        # Browser settings
        browser_config = config.get("browser", {})
        self._headless = browser_config.get("headless", config.get("headless", False))
        self._browser_profile = browser_config.get("profile_dir") or config.get("browser_profile")

        # Browser manager (handles lifecycle)
        self._browser_manager: Optional[BrowserManager] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._tweet_page: Optional[TweetPage] = None
        self._replies_section: Optional[RepliesSection] = None

        # Rate limit detector
        self._rate_limit_detector = TwitterRateLimitDetector()

        # Initialize browser
        self._init_browser()

    def _init_browser(self) -> None:
        """Initialize browser using BrowserManager."""
        # Get session file path for storage state
        session_file = self.config.get("session_file")
        storage_state = None
        if session_file:
            session_path = Path(session_file)
            playwright_session = session_path.with_suffix('.playwright.json')
            if playwright_session.exists():
                storage_state = str(playwright_session)

        browser_config = BrowserConfig(
            headless=self._headless,
            profile_dir=self._browser_profile,
            storage_state=storage_state,
            proxy=self._current_proxy,
        )

        self._browser_manager = BrowserManager(browser_config, "twitter")
        self._page = self._browser_manager.page

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._tweet_page = TweetPage(self._page)
        self._replies_section = RepliesSection(self._page)

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_manager:
            self._browser_manager.close()
            self._browser_manager = None
        super().close()

    def _check_rate_limit(self) -> bool:
        """
        Check if Twitter is rate limiting us.

        Returns:
            True if rate limited, False otherwise
        """
        return self._rate_limit_detector.is_rate_limited(self._page)

    def _navigate_to_url(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to URL with retry and rate limit detection.

        Uses the base class _navigate_with_retry method with Twitter-specific selectors.

        Args:
            url: URL to navigate to
            max_retries: Maximum number of retry attempts

        Returns:
            True if navigation succeeded, False otherwise
        """
        return super()._navigate_with_retry(
            page=self._page,
            url=url,
            content_selectors=["article[data-testid='tweet']", "div[data-testid='primaryColumn']"],
            rate_limit_detector=self._rate_limit_detector,
            max_retries=max_retries
        )

    def _ensure_logged_in(self) -> None:
        """Ensure we are logged in to Twitter."""
        self._page.goto(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

        if not self._login_page.is_logged_in():
            # Check if using Google OAuth
            if self._use_google_auth:
                if not self._google_email or not self._google_password:
                    raise AuthenticationError(
                        "Google OAuth credentials not configured. Set EXTRACTOR_TWITTER__GOOGLE_EMAIL and EXTRACTOR_TWITTER__GOOGLE_PASSWORD",
                        platform=self.platform.value
                    )

                logger.info("LOGIN | attempting Google OAuth login for %s", self._google_email)
                self._login_page.login_with_google(self._google_email, self._google_password)

            else:
                # Traditional Twitter credentials
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

            # Save session to Playwright format
            session_file = self.config.get("session_file")
            if session_file:
                session_path = Path(session_file)
                playwright_session = session_path.with_suffix('.playwright.json')
                self._browser_manager.save_storage_state(str(playwright_session))
                logger.info(f"SESSION | saved Playwright session to {playwright_session}")

            login_id = self._google_email if self._use_google_auth else self._username
            logger.info("LOGIN SUCCESS | user=%s", login_id)
        else:
            logger.info("LOGIN | already logged in (session restored)")

    def _handle_session_expiry(self, account_id: str) -> None:
        """Handle session expiry by re-logging in."""
        logger.info("SESSION | forcing re-login")

        # Use Google OAuth if configured
        if self._use_google_auth and self._google_email and self._google_password:
            self._login_page.login_with_google(self._google_email, self._google_password)
        elif self._username and self._password:
            self._login_page.login(self._username, self._password)
        else:
            raise AuthenticationError(
                "Session expired and no credentials available for re-login",
                platform=self.platform.value
            )

        # Save new session
        session_file = self.config.get("session_file")
        if session_file:
            session_path = Path(session_file)
            playwright_session = session_path.with_suffix('.playwright.json')
            self._browser_manager.save_storage_state(str(playwright_session))
            logger.info(f"SESSION | saved new Playwright session to {playwright_session}")
        # Navigate back to profile
        self._profile_page.navigate(account_id)

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape Twitter profile information.

        Args:
            account_id: Twitter username

        Returns:
            Profile model with account information
        """
        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            raise AccountNotFoundError(
                f"Twitter profile not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        return Profile(
            platform=self.platform,
            platform_id=account_id,
            username=account_id,
            display_name=self._profile_page.get_display_name() or account_id,
            followers_count=self._profile_page.get_followers_count(),
            following_count=self._profile_page.get_following_count(),
            is_verified=self._profile_page.is_verified(),
            raw_data={},
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int,
        known_post_ids: Optional[Set[str]] = None
    ) -> Iterator[ExtractionResult]:
        """
        Scrape tweets and their replies.

        Args:
            account_id: Twitter username
            since_date: Only get posts after this date (optional)
            max_posts: Maximum number of posts to scrape
            known_post_ids: Set of tweet IDs to skip (already extracted)

        Yields:
            ExtractionResult with post and comments
        """
        logger.info(f"SCRAPING TWEETS | target={account_id} | max={max_posts}")

        # Ensure logged in
        self._ensure_logged_in()

        # Navigate to profile
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            raise AccountNotFoundError(
                f"Twitter profile not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Load checkpoint if resuming
        checkpoint_ids = self._load_checkpoint(account_id)

        # Combine known_post_ids with checkpoint
        all_known_ids = (known_post_ids or set()) | checkpoint_ids

        # Get tweet links
        scroll_all = max_posts > 50
        tweet_links = self._tweet_page.get_tweet_links(
            account_id,
            max_posts,
            scroll_all=scroll_all,
            known_post_ids=all_known_ids
        )

        if not tweet_links:
            logger.warning("No tweets found on profile")
            return

        logger.info(f"PHASE 1 COMPLETE | Collected {len(tweet_links)} tweet links")

        # Define extraction function for each tweet
        def extract_tweet(tweet_url: str):
            # Extract tweet data
            tweet_data = self._tweet_page.extract_tweet_data(account_id)
            tweet_id = tweet_data.get("id", "")

            if not tweet_id:
                return None

            # Check date filter
            tweet_date = tweet_data.get("timestamp")
            if since_date and tweet_date:
                try:
                    if isinstance(tweet_date, str):
                        tweet_datetime = datetime.fromisoformat(tweet_date.replace('Z', '+00:00'))
                    else:
                        tweet_datetime = tweet_date
                    if tweet_datetime.replace(tzinfo=None) < since_date:
                        logger.info(f"Tweet {tweet_id} before since_date, stopping")
                        return None
                except (ValueError, TypeError):
                    pass  # If we can't parse date, include the tweet

            # Create Post model
            post = Post(
                platform=self.platform,
                platform_id=tweet_id,
                account_id=account_id,
                url=tweet_url,
                text=tweet_data.get("text", ""),
                published_at=tweet_date if isinstance(tweet_date, datetime) else None,
                likes=tweet_data.get("likes", 0),
                comments_count=tweet_data.get("replies", 0),
                shares=tweet_data.get("retweets", 0),
                media_type=tweet_data.get("media_type", "text"),
                media_urls=[],
                raw_data={},
            )

            # Extract replies
            raw_replies = self._replies_section.extract_replies_for_tweet(tweet_id)
            comments = self._create_comment_objects(raw_replies, tweet_id)
            post.comments_count = len(comments)

            return ExtractionResult(post=post, comments=comments)

        # Use unified post iteration from base class
        yield from self._iterate_posts(
            post_links=tweet_links,
            max_posts=max_posts,
            known_post_ids=all_known_ids,
            extract_fn=extract_tweet,
            page=self._page,
            check_rate_limit_fn=self._check_rate_limit,
            human_delay_fn=self._tweet_page.human_delay,
            account_id=account_id,
            checkpoint_ids=checkpoint_ids,
            use_navigate_method=True,
            navigate_fn=self._navigate_to_url
        )

        logger.info(f"EXTRACTION COMPLETE | account={account_id}")
