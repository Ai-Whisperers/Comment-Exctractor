"""LinkedIn Scraper using Page Object Model architecture."""

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
from ..shared.rate_limiting import LinkedInRateLimitDetector
from ..shared.constants import TIMEOUTS
from .pages import LoginPage, ProfilePage, PostPage, CommentsSection
from .selectors import Selectors

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    LinkedIn scraper using Page Object Model pattern.

    This scraper uses a clean separation between page interactions
    (via Page Objects) and business logic (in this class).
    """

    platform = Platform.LINKEDIN

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LinkedIn scraper.

        Args:
            config: Configuration dictionary with credentials and settings
        """
        super().__init__(config)

        # Credentials (support both flat and nested config)
        credentials = config.get("credentials", {})
        self._email = credentials.get("email") or config.get("email")
        self._password = credentials.get("password") or config.get("password")

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
        self._post_page: Optional[PostPage] = None
        self._comments_section: Optional[CommentsSection] = None

        # Rate limit detector
        self._rate_limit_detector = LinkedInRateLimitDetector()

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

        self._browser_manager = BrowserManager(browser_config, "linkedin")
        self._page = self._browser_manager.page

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._post_page = PostPage(self._page)
        self._comments_section = CommentsSection(self._page)

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_manager:
            self._browser_manager.close()
            self._browser_manager = None
        super().close()

    def _check_rate_limit(self) -> bool:
        """
        Check if LinkedIn is rate limiting us.

        Returns:
            True if rate limited, False otherwise
        """
        return self._rate_limit_detector.is_rate_limited(self._page)

    def _navigate_to_url(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to URL with retry and rate limit detection.

        Uses the base class _navigate_with_retry method with LinkedIn-specific selectors.

        Args:
            url: URL to navigate to
            max_retries: Maximum number of retry attempts

        Returns:
            True if navigation succeeded, False otherwise
        """
        return super()._navigate_with_retry(
            page=self._page,
            url=url,
            content_selectors=["div.feed-shared-update-v2", "article", "main"],
            rate_limit_detector=self._rate_limit_detector,
            max_retries=max_retries
        )

    def _ensure_logged_in(self) -> None:
        """Ensure we are logged in to LinkedIn."""
        self._page.goto(Selectors.URLs.FEED, wait_until="domcontentloaded")
        self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

        if not self._login_page.is_logged_in():
            if not self._email or not self._password:
                raise AuthenticationError(
                    "LinkedIn credentials not configured",
                    platform=self.platform.value
                )

            logger.info("LOGIN | attempting login for %s", self._email)
            self._login_page.login(self._email, self._password)

            # Verify login succeeded
            self._page.wait_for_timeout(TIMEOUTS.LONG_WAIT)
            if not self._login_page.is_logged_in():
                raise AuthenticationError(
                    "LinkedIn login failed",
                    platform=self.platform.value
                )

            # Save session to Playwright format
            session_file = self.config.get("session_file")
            if session_file:
                session_path = Path(session_file)
                playwright_session = session_path.with_suffix('.playwright.json')
                self._browser_manager.save_storage_state(str(playwright_session))
                logger.info(f"SESSION | saved Playwright session to {playwright_session}")

            logger.info("LOGIN SUCCESS | user=%s", self._email)
        else:
            logger.info("LOGIN | already logged in (session restored)")

    def _handle_session_expiry(self, account_id: str) -> None:
        """Handle session expiry by re-logging in."""
        logger.info("SESSION | forcing re-login")
        if self._email and self._password:
            self._login_page.login(self._email, self._password)
            # Save new session
            session_file = self.config.get("session_file")
            if session_file:
                session_path = Path(session_file)
                playwright_session = session_path.with_suffix('.playwright.json')
                self._browser_manager.save_storage_state(str(playwright_session))
                logger.info(f"SESSION | saved new Playwright session to {playwright_session}")
            # Navigate back to posts
            self._profile_page.navigate_to_posts(account_id)
        else:
            raise AuthenticationError(
                "Session expired and no credentials available for re-login",
                platform=self.platform.value
            )

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape LinkedIn profile information.

        Args:
            account_id: LinkedIn username or profile URL

        Returns:
            Profile model with account information
        """
        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            raise AccountNotFoundError(
                f"LinkedIn profile not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # LinkedIn uses connections instead of following
        connections = self._profile_page.get_connections_count()

        return Profile(
            platform=self.platform,
            platform_id=account_id,
            username=account_id,
            display_name=self._profile_page.get_display_name() or account_id,
            followers_count=self._profile_page.get_followers_count(),
            following_count=connections,  # Use connections as following
            is_verified=self._profile_page.is_verified(),
            raw_data={"headline": self._profile_page.get_headline()},
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int,
        known_post_ids: Optional[Set[str]] = None
    ) -> Iterator[ExtractionResult]:
        """
        Scrape posts and their comments.

        Args:
            account_id: LinkedIn username or profile URL
            since_date: Only get posts after this date (optional)
            max_posts: Maximum number of posts to scrape
            known_post_ids: Set of post IDs to skip (already extracted)

        Yields:
            ExtractionResult with post and comments
        """
        logger.info(f"SCRAPING POSTS | target={account_id} | max={max_posts}")

        # Ensure logged in
        self._ensure_logged_in()

        # Navigate to activity page
        self._profile_page.navigate_to_posts(account_id)

        if not self._profile_page.is_profile_available():
            raise AccountNotFoundError(
                f"LinkedIn profile not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Load checkpoint if resuming
        checkpoint_ids = self._load_checkpoint(account_id)

        # Combine known_post_ids with checkpoint
        all_known_ids = (known_post_ids or set()) | checkpoint_ids

        # Get post links
        scroll_all = max_posts > 50
        post_links = self._post_page.get_post_links(
            account_id,
            max_posts,
            scroll_all=scroll_all,
            known_post_ids=all_known_ids
        )

        if not post_links:
            logger.warning("No posts found on profile")
            return

        logger.info(f"PHASE 1 COMPLETE | Collected {len(post_links)} post links")

        # Define extraction function for each post
        def extract_post(post_url: str):
            # Extract post data
            post_data = self._post_page.extract_post_data(account_id)
            post_id = post_data.get("id", "")

            if not post_id:
                return None

            # Check date filter
            post_date = post_data.get("timestamp")
            if since_date and post_date:
                try:
                    if isinstance(post_date, str):
                        post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                    else:
                        post_datetime = post_date
                    if post_datetime.replace(tzinfo=None) < since_date:
                        logger.info(f"Post {post_id} before since_date, stopping")
                        return None
                except (ValueError, TypeError):
                    pass  # If we can't parse date, include the post

            # Create Post model
            post = Post(
                platform=self.platform,
                platform_id=post_id,
                account_id=account_id,
                url=post_url,
                text=post_data.get("text", ""),
                published_at=post_date if isinstance(post_date, datetime) else None,
                likes=post_data.get("likes", 0),
                comments_count=post_data.get("comments", 0),
                shares=post_data.get("reposts", 0),
                media_type=post_data.get("media_type", "text"),
                media_urls=[],
                raw_data={},
            )

            # Extract comments
            raw_comments = self._comments_section.extract_comments_for_post(post_id)
            comments = self._create_comment_objects(raw_comments, post_id)
            post.comments_count = len(comments)

            return ExtractionResult(post=post, comments=comments)

        # Use unified post iteration from base class
        yield from self._iterate_posts(
            post_links=post_links,
            max_posts=max_posts,
            known_post_ids=all_known_ids,
            extract_fn=extract_post,
            page=self._page,
            check_rate_limit_fn=self._check_rate_limit,
            human_delay_fn=self._post_page.human_delay,
            account_id=account_id,
            checkpoint_ids=checkpoint_ids,
            use_navigate_method=True,
            navigate_fn=self._navigate_to_url
        )

        logger.info(f"EXTRACTION COMPLETE | account={account_id}")
