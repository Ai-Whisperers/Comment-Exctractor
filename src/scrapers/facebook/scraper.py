"""Facebook Scraper using Page Object Model architecture."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict, Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from ...core.models import (
    Platform,
    Post,
    Profile,
    ExtractionResult,
)
from ...core.exceptions import (
    AuthenticationError,
    AccountNotFoundError,
)
from ..base import BaseScraper
from ..shared.browser_manager import BrowserManager, BrowserConfig
from ..shared.rate_limiting import FacebookRateLimitDetector
from ..shared.constants import TIMEOUTS
from .pages import LoginPage, ProfilePage, PostPage, CommentsSection
from .selectors import Selectors

logger = logging.getLogger(__name__)


class FacebookScraper(BaseScraper):
    """
    Facebook scraper using Page Object Model pattern.

    This scraper uses a clean separation between page interactions
    (via Page Objects) and business logic (in this class).
    """

    platform = Platform.FACEBOOK

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Facebook scraper.

        Args:
            config: Configuration dictionary with credentials and settings
        """
        super().__init__(config)

        # Credentials
        self._email = config.get("email")
        self._password = config.get("password")

        # Browser settings
        self._headless = config.get("headless", False)

        # Browser manager (handles lifecycle)
        self._browser_manager: Optional[BrowserManager] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._post_page: Optional[PostPage] = None
        self._comments_section: Optional[CommentsSection] = None

        # Rate limit detector
        self._rate_limit_detector = FacebookRateLimitDetector()

        # Initialize browser
        self._init_browser()

    def _init_browser(self) -> None:
        """Initialize browser using BrowserManager."""
        browser_config = BrowserConfig(
            headless=self._headless,
            profile_dir=self.config.get("browser_profile"),
            proxy=self._current_proxy,
        )

        self._browser_manager = BrowserManager(browser_config, "facebook")
        self._page = self._browser_manager.page

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._post_page = PostPage(self._page)
        self._comments_section = CommentsSection(self._page)

    def _check_rate_limit(self) -> bool:
        """
        Check if Facebook is rate limiting us.

        Returns:
            True if rate limited, False otherwise
        """
        return self._rate_limit_detector.is_rate_limited(self._page)

    def _ensure_logged_in(self):
        """Ensure user is logged in, performing login if necessary."""
        # Check if already logged in
        self._page.goto(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self._page.wait_for_timeout(2000)

        if self._login_page.is_logged_in():
            logger.info("SESSION | already logged in")
            return

        # Need to login
        if not self._email or not self._password:
            raise AuthenticationError(
                "Facebook email and password required",
                platform=self.platform.value
            )

        try:
            logger.info(f"SESSION | performing login with email={self._email[:3]}***")
            self._login_page.login(self._email, self._password)

        except Exception as e:
            logger.error(f"LOGIN FAILED | {e}")
            raise AuthenticationError(str(e), platform=self.platform.value)

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape profile information for an account.

        Args:
            account_id: Facebook page name or ID

        Returns:
            Profile object
        """
        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_page_available():
            raise AccountNotFoundError(
                f"Facebook page not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        return Profile(
            platform=self.platform,
            platform_id=account_id,
            username=account_id,
            display_name=self._profile_page.get_display_name() or account_id,
            followers_count=self._profile_page.get_followers_count(),
            following_count=0,
            is_verified=self._profile_page.is_verified(),
            raw_data={"likes_count": self._profile_page.get_likes_count()},
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int,
        known_post_ids: set = None
    ) -> Iterator[ExtractionResult]:
        """
        Scrape posts and comments from a Facebook page/profile.

        Args:
            account_id: Facebook page name or ID
            since_date: Only get posts after this date
            max_posts: Maximum number of posts to extract
            known_post_ids: Set of post IDs that already exist (for skipping)

        Yields:
            ExtractionResult objects with post and comments
        """
        logger.debug(f"_scrape_posts | account={account_id} | max_posts={max_posts}")

        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        # Check if page exists
        if not self._profile_page.is_page_available():
            raise AccountNotFoundError(
                f"Facebook page not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Collect post links
        scroll_all = max_posts > 50
        # Pass known_post_ids to skip existing posts
        # Only skip existing posts if we have known_post_ids (incremental mode)
        # If known_post_ids is empty/None, this is a full extraction
        should_skip_existing = bool(known_post_ids)
        post_links = self._post_page.get_post_links(
            max_posts,
            scroll_all=scroll_all,
            known_post_ids=known_post_ids,
            skip_existing=should_skip_existing
        )

        if not post_links:
            logger.warning("No posts found on profile")
            return

        logger.info(f"COLLECTED {len(post_links)} POST LINKS")

        # Scrape each post
        posts_scraped = 0
        posts_skipped = 0
        consecutive_failures = 0
        max_failures = 5
        known_post_ids = known_post_ids or set()

        for post_url in post_links:
            if posts_scraped >= max_posts:
                break

            # Navigate with retry logic
            nav_success = False
            for attempt in range(3):
                try:
                    self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                    self._page.wait_for_timeout(1500)
                    nav_success = True
                    break
                except Exception as nav_error:
                    logger.warning(f"Navigation attempt {attempt + 1}/3 failed for {post_url[:60]}...: {nav_error}")
                    if attempt < 2:
                        self._page.wait_for_timeout(2000)  # Wait before retry

            if not nav_success:
                logger.warning(f"Failed to navigate to post after 3 attempts: {post_url[:60]}...")
                consecutive_failures += 1
                continue

            # Check for rate limiting after navigation
            if self._check_rate_limit():
                logger.warning("Rate limit detected, waiting 60 seconds before retry...")
                self._page.wait_for_timeout(60000)
                # Try once more after waiting
                if self._check_rate_limit():
                    logger.error("Still rate limited after waiting, stopping extraction")
                    break

            try:

                # Extract post data
                post_data = self._post_page.extract_post_data(account_id)

                # Skip if post already exists in database
                if post_data["id"] in known_post_ids:
                    posts_skipped += 1
                    logger.debug(f"Skipping existing post: {post_data['id']}")
                    continue

                # Create Post object
                post = Post(
                    platform=self.platform,
                    platform_id=post_data["id"],
                    account_id=account_id,
                    url=post_data["url"],
                    text=post_data["text"],
                    published_at=post_data["timestamp"],
                    likes=post_data["likes"],
                    comments_count=post_data["comments_count"],
                    shares=post_data["shares"],
                    media_type=post_data["media_type"],
                    media_urls=[],
                    raw_data={},
                )

                # Check date filter
                if since_date and post.published_at and post.published_at < since_date:
                    logger.info(f"Post {post.platform_id} before since_date, stopping")
                    break

                # Extract comments
                raw_comments = self._comments_section.extract_comments_for_post(post.platform_id)
                comments = self._create_comment_objects(raw_comments, post.platform_id)
                post.comments_count = len(comments)

                yield ExtractionResult(post=post, comments=comments)
                posts_scraped += 1
                consecutive_failures = 0

                logger.info(
                    f"SCRAPED | {posts_scraped}/{max_posts} | "
                    f"post_id={post.platform_id} | comments={len(comments)}"
                )

                # Extended break check
                if self.should_take_extended_break():
                    self.take_extended_break()

            except Exception as e:
                logger.warning(f"Error extracting post from {post_url}: {e}")
                consecutive_failures += 1

            if consecutive_failures >= max_failures:
                logger.warning("Too many failures, stopping")
                break

            # Human-like delay
            self._post_page.human_delay(1000, 2000)

        logger.info(
            f"EXTRACTION COMPLETE | account={account_id} | "
            f"posts={posts_scraped} | skipped={posts_skipped}"
        )

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_manager:
            self._browser_manager.close()
            self._browser_manager = None
        super().close()
