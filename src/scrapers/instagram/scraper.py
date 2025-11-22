"""Instagram Scraper using Page Object Model architecture."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict, Any

from playwright.sync_api import Page

from ...core.models import (
    Platform,
    Post,
    Profile,
    ExtractionResult,
)
from ...core.exceptions import (
    AuthenticationError,
    PrivateAccountError,
    RateLimitError,
)
from ..base import BaseScraper
from ..shared.browser_manager import BrowserManager, BrowserConfig
from ..shared.rate_limiting import InstagramRateLimitDetector
from ..shared.constants import TIMEOUTS
from .pages import LoginPage, ProfilePage, PostModal, CommentsSection
from .selectors import Selectors

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    """
    Instagram scraper using Page Object Model pattern.

    This scraper uses a clean separation between page interactions
    (via Page Objects) and business logic (in this class).
    """

    platform = Platform.INSTAGRAM

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Instagram scraper.

        Args:
            config: Configuration dictionary with credentials and settings
        """
        super().__init__(config)

        # Credentials (support both flat and nested config)
        credentials = config.get("credentials", {})
        self._username = credentials.get("username") or config.get("username")
        self._password = credentials.get("password") or config.get("password")

        # Browser settings (support both flat and nested config)
        browser_config = config.get("browser", {})
        self._headless = browser_config.get("headless", config.get("headless", False))
        self._browser_profile = browser_config.get("profile_dir") or config.get("browser_profile")

        # Browser manager (handles lifecycle)
        self._browser_manager: Optional[BrowserManager] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._post_modal: Optional[PostModal] = None
        self._comments_section: Optional[CommentsSection] = None

        # Rate limit detector
        self._rate_limit_detector = InstagramRateLimitDetector()

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

        self._browser_manager = BrowserManager(browser_config, "instagram")
        self._page = self._browser_manager.page

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._post_modal = PostModal(self._page)
        self._comments_section = CommentsSection(self._page)

    def _check_rate_limit(self) -> bool:
        """
        Check if Instagram is rate limiting us.

        Returns:
            True if rate limited, False otherwise
        """
        return self._rate_limit_detector.is_rate_limited(self._page)

    def _navigate_to_url(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to URL with retry and rate limit detection.

        Uses the base class _navigate_with_retry method with Instagram-specific selectors.

        Args:
            url: URL to navigate to
            max_retries: Maximum number of retry attempts

        Returns:
            True if navigation succeeded, False otherwise
        """
        return super()._navigate_with_retry(
            page=self._page,
            url=url,
            content_selectors=["article", "button", "div[role='dialog']"],
            rate_limit_detector=self._rate_limit_detector,
            max_retries=max_retries
        )

    def _ensure_logged_in(self):
        """Ensure user is logged in, performing login if necessary."""
        # Navigate to Instagram home to check login state
        # Use domcontentloaded instead of networkidle to avoid timeout issues
        self._page.goto(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self._page.wait_for_timeout(TIMEOUTS.LONG_WAIT)  # Wait for dynamic content to load

        # Dismiss any popups that might be blocking
        self._profile_page.dismiss_popups()
        self._page.wait_for_timeout(TIMEOUTS.SHORT_WAIT)

        # Check if we were redirected to login page
        current_url = self._page.url
        if Selectors.URLs.ACCOUNTS_LOGIN in current_url or Selectors.URLs.ACCOUNTS_SIGNUP in current_url:
            logger.info("SESSION | redirected to login page, need to authenticate")
        elif self._profile_page.is_logged_in():
            # Double-check for login form even if is_logged_in() returns True
            has_login_form = self._page.evaluate('''
                () => {
                    const hasUsername = !!document.querySelector('input[name="username"]');
                    const hasPassword = !!document.querySelector('input[name="password"]');
                    return hasUsername && hasPassword;
                }
            ''')
            if not has_login_form:
                logger.info("SESSION | already logged in")
                return
            else:
                logger.info("SESSION | login form detected despite positive indicators, need to authenticate")

        # Need to login
        if not self._username or not self._password:
            raise AuthenticationError(
                "Instagram username and password required",
                platform=self.platform.value
            )

        try:
            logger.info(f"SESSION | performing login with username={self._username}")
            self._login_page.login(self._username, self._password)

            # Save session to Playwright format
            session_file = self.config.get("session_file")
            if session_file:
                session_path = Path(session_file)
                playwright_session = session_path.with_suffix('.playwright.json')
                self._browser_manager.save_storage_state(str(playwright_session))
                logger.info(f"SESSION | saved Playwright session to {playwright_session}")

        except Exception as e:
            logger.error(f"LOGIN FAILED | {e}")
            raise AuthenticationError(str(e), platform=self.platform.value)

    def _verify_logged_in_on_profile(self) -> bool:
        """
        Verify we're still logged in when on a profile page.

        Returns:
            True if logged in, False if login form is present
        """
        # Check if login form is present
        has_login_form = self._page.evaluate('''
            () => {
                const hasUsername = !!document.querySelector('input[name="username"]');
                const hasPassword = !!document.querySelector('input[name="password"]');
                return hasUsername && hasPassword;
            }
        ''')

        if has_login_form:
            logger.warning("SESSION | login form detected on profile page, need to re-login")
            return False

        return True

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape profile information for an account.

        Args:
            account_id: Instagram username

        Returns:
            Profile object
        """
        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

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
        known_post_ids: set = None
    ) -> Iterator[ExtractionResult]:
        """
        Scrape posts and comments from an Instagram account.

        Uses a 2-phase approach like Facebook:
        - Phase 1: Collect all post links from profile grid
        - Phase 2: Visit each post and extract data + comments

        Args:
            account_id: Instagram username
            since_date: Only get posts after this date
            max_posts: Maximum number of posts to extract
            known_post_ids: Set of post IDs to skip (already extracted)

        Yields:
            ExtractionResult objects with post and comments
        """
        logger.debug(f"_scrape_posts | account={account_id} | max_posts={max_posts}")

        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        # Verify we're still logged in after navigation
        if not self._verify_logged_in_on_profile():
            self._handle_session_expiry(account_id)

        # Check for private account
        if self._profile_page.is_private():
            raise PrivateAccountError(
                f"Account is private: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # ============================================================
        # PHASE 1: Collect post links from profile grid
        # ============================================================
        scroll_all = max_posts > 50

        post_links = self._profile_page.get_post_links(
            count=max_posts,
            scroll_all=scroll_all,
            known_post_ids=known_post_ids
        )

        if not post_links:
            logger.warning("No posts found on profile")
            return

        logger.info(f"PHASE 1 COMPLETE | Collected {len(post_links)} post links")

        # ============================================================
        # PHASE 2: Extract data from each post
        # ============================================================

        # Define extraction function for each post
        def extract_post(post_url: str):
            # Extract post data
            post_data = self._post_modal.extract_post_data(account_id)
            post_id = post_data.get("id") or self._post_modal.get_post_id()

            if not post_id:
                logger.warning(f"Could not get post ID from {post_url}")
                return None

            # Create Post object
            post = Post(
                platform=self.platform,
                platform_id=post_id,
                account_id=account_id,
                url=post_data["url"],
                text=post_data["caption"],
                published_at=post_data["timestamp"],
                likes=post_data["likes"],
                comments_count=0,
                shares=0,
                media_type=post_data["media_type"],
                media_urls=[],
                raw_data={},
            )

            # Check date filter
            if since_date and post.published_at and post.published_at < since_date:
                logger.info(f"Post {post.platform_id} before since_date, stopping")
                return None

            # Extract comments
            raw_comments = self._comments_section.extract_comments_for_post(post.platform_id)
            comments = self._create_comment_objects(raw_comments, post.platform_id)
            post.comments_count = len(comments)

            return ExtractionResult(post=post, comments=comments)

        # Use unified post iteration from base class
        yield from self._iterate_posts(
            post_links=post_links,
            max_posts=max_posts,
            known_post_ids=known_post_ids or set(),
            extract_fn=extract_post,
            page=self._page,
            check_rate_limit_fn=self._check_rate_limit,
            human_delay_fn=self._post_modal.human_delay
        )

        logger.info(f"PHASE 2 COMPLETE | account={account_id}")

    def _handle_session_expiry(self, account_id: str) -> None:
        """Handle session expiry by re-logging in."""
        logger.info("SESSION | forcing re-login")
        if self._username and self._password:
            self._login_page.login(self._username, self._password)
            # Save new session
            session_file = self.config.get("session_file")
            if session_file:
                session_path = Path(session_file)
                playwright_session = session_path.with_suffix('.playwright.json')
                self._browser_manager.save_storage_state(str(playwright_session))
                logger.info(f"SESSION | saved new Playwright session to {playwright_session}")
            # Navigate back to profile
            self._profile_page.navigate(account_id)
        else:
            raise AuthenticationError(
                "Session expired and no credentials available for re-login",
                platform=self.platform.value
            )

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_manager:
            self._browser_manager.close()
            self._browser_manager = None
        super().close()
