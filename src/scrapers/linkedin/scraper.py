"""LinkedIn Scraper using Page Object Model architecture."""

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

        # Session
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._post_page: Optional[PostPage] = None
        self._comments_section: Optional[CommentsSection] = None

        # Initialize browser
        self._init_browser()

    def _init_browser(self):
        """Initialize Playwright browser and page objects."""
        logger.info("BROWSER INIT | platform=linkedin | headless=%s", self._headless)

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
        self._post_page = PostPage(self._page)
        self._comments_section = CommentsSection(self._page)

        logger.info("PAGE OBJECTS | initialized login, profile, post, comments")

    def close(self):
        """Clean up browser resources."""
        logger.info("BROWSER CLEANUP | platform=linkedin")
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

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

            logger.info("LOGIN SUCCESS | user=%s", self._email)
        else:
            logger.info("LOGIN | already logged in (session restored)")

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape LinkedIn profile information.

        Args:
            account_id: LinkedIn username or profile URL

        Returns:
            Profile model with account information
        """
        self._profile_page.navigate(account_id)

        if not self._profile_page.is_profile_available():
            logger.warning(f"Profile not available: {account_id}")
            # Return minimal profile
            return Profile(
                platform=Platform.LINKEDIN,
                username=account_id,
                display_name=account_id,
                followers=0,
                following=0,
            )

        # LinkedIn uses connections instead of following
        connections = self._profile_page.get_connections_count()

        return Profile(
            platform=Platform.LINKEDIN,
            username=account_id,
            display_name=self._profile_page.get_display_name() or account_id,
            bio=self._profile_page.get_headline(),
            followers=self._profile_page.get_followers_count(),
            following=connections,  # Use connections as following
            is_verified=self._profile_page.is_verified(),
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int
    ) -> Iterator[ExtractionResult]:
        """
        Scrape posts and their comments.

        Args:
            account_id: LinkedIn username or profile URL
            since_date: Only get posts after this date (optional)
            max_posts: Maximum number of posts to scrape

        Yields:
            ExtractionResult with post and comments
        """
        logger.info(f"SCRAPING POSTS | target={account_id} | max={max_posts}")

        # Ensure logged in
        self._ensure_logged_in()

        # Navigate to activity page
        self._profile_page.navigate_to_posts(account_id)

        if not self._profile_page.is_profile_available():
            logger.warning(f"Profile not available: {account_id}")
            return

        # Get post links
        post_links = self._post_page.get_post_links(account_id, max_posts)
        logger.info(f"Found {len(post_links)} posts to process")

        for idx, post_url in enumerate(post_links, 1):
            try:
                logger.info(f"PROCESSING POST {idx}/{len(post_links)} | url={post_url}")

                # Navigate to post
                self._page.goto(post_url, wait_until="domcontentloaded")
                self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

                # Extract post data
                post_data = self._post_page.extract_post_data(account_id)

                # Check date filter
                post_date = post_data.get("timestamp")
                if since_date and post_date:
                    try:
                        if isinstance(post_date, str):
                            post_datetime = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
                        else:
                            post_datetime = post_date
                        if post_datetime.replace(tzinfo=None) < since_date:
                            logger.debug(f"Skipping post {post_data.get('id')} - before since_date")
                            continue
                    except (ValueError, TypeError):
                        pass  # If we can't parse date, include the post

                # Create Post model
                post = Post(
                    platform=Platform.LINKEDIN,
                    platform_id=post_data.get("id", f"post_{idx}"),
                    url=post_url,
                    text=post_data.get("text", ""),
                    likes=post_data.get("likes", 0),
                    comments_count=post_data.get("comments_count", 0),
                    shares=post_data.get("shares", 0),
                    published_at=post_date if isinstance(post_date, datetime) else None,
                    author=Author(
                        username=account_id,
                        display_name=post_data.get("author_name", account_id),
                    ),
                )

                # Extract comments
                comments_data = self._comments_section.extract_comments_for_post(post_data.get("id", ""))

                comments = []
                for comment_item in comments_data:
                    comment = Comment(
                        platform=Platform.LINKEDIN,
                        platform_id=comment_item.get("id", f"comment_{len(comments)}"),
                        post_id=post.platform_id,
                        text=comment_item.get("text", ""),
                        likes=comment_item.get("likes", 0),
                        published_at=comment_item.get("timestamp") if isinstance(comment_item.get("timestamp"), datetime) else None,
                        author=Author(
                            username=comment_item.get("author", "unknown"),
                            display_name=comment_item.get("author_name", comment_item.get("author", "unknown")),
                        ),
                    )
                    comments.append(comment)

                logger.info(f"Post {idx} extracted | comments={len(comments)}")

                yield ExtractionResult(post=post, comments=comments)

                # Human-like delay
                self._page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

            except Exception as e:
                logger.error(f"Error processing post {post_url}: {e}")
                continue

        logger.info(f"COMPLETED | total_posts={len(post_links)}")
