"""Instagram Scraper using Page Object Model architecture."""

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
    PrivateAccountError,
    RateLimitError,
)
from ..base import BaseScraper
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

        # Credentials
        self._username = config.get("username")
        self._password = config.get("password")

        # Browser settings
        self._headless = config.get("headless", True)

        # Session
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._login_page: Optional[LoginPage] = None
        self._profile_page: Optional[ProfilePage] = None
        self._post_modal: Optional[PostModal] = None
        self._comments_section: Optional[CommentsSection] = None

        # Initialize browser
        self._init_browser()

    def _init_browser(self):
        """Initialize Playwright browser and page objects."""
        logger.info("BROWSER INIT | platform=instagram | headless=%s", self._headless)

        self._playwright = sync_playwright().start()

        # Check for persistent browser profile
        browser_profile = self.config.get("browser_profile")

        if browser_profile and Path(browser_profile).exists():
            # Use persistent context with existing browser profile (includes cookies, localStorage, etc.)
            logger.info(f"BROWSER INIT | using persistent context from {browser_profile}")
            self._context = self._playwright.chromium.launch_persistent_context(
                browser_profile,
                headless=self._headless,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            self._browser = None  # No separate browser object with persistent context
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            # Standard browser launch
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )

            # Create context with session storage
            # Note: Playwright requires JSON format for storage_state
            # The session file should be a Playwright-exported JSON, not an Instaloader pickle file
            session_file = self.config.get("session_file")
            storage_state = None

            if session_file:
                session_path = Path(session_file)
                # Check if it's a Playwright session file (JSON format)
                playwright_session = session_path.with_suffix('.playwright.json')

                if playwright_session.exists():
                    try:
                        # Verify it's valid JSON
                        import json
                        with open(playwright_session, 'r') as f:
                            json.load(f)
                        storage_state = str(playwright_session)
                        logger.info(f"BROWSER INIT | loading Playwright session from {playwright_session}")
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Failed to load Playwright session {playwright_session}: {e}")
                else:
                    logger.debug(f"BROWSER INIT | no Playwright session file found at {playwright_session}")

            self._context = self._browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            self._page = self._context.new_page()

        # Initialize page objects
        self._login_page = LoginPage(self._page)
        self._profile_page = ProfilePage(self._page)
        self._post_modal = PostModal(self._page)
        self._comments_section = CommentsSection(self._page)

        logger.info("BROWSER INIT | complete")

    def _ensure_logged_in(self):
        """Ensure user is logged in, performing login if necessary."""
        # Navigate to Instagram home to check login state
        # Use domcontentloaded instead of networkidle to avoid timeout issues
        self._page.goto(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self._page.wait_for_timeout(3000)  # Wait for dynamic content to load

        # Dismiss any popups that might be blocking
        self._profile_page.dismiss_popups()
        self._page.wait_for_timeout(1000)

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
                self._context.storage_state(path=str(playwright_session))
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
        max_posts: int
    ) -> Iterator[ExtractionResult]:
        """
        Scrape posts and comments from an Instagram account.

        Args:
            account_id: Instagram username
            since_date: Only get posts after this date
            max_posts: Maximum number of posts to extract

        Yields:
            ExtractionResult objects with post and comments
        """
        logger.debug(f"_scrape_posts | account={account_id} | max_posts={max_posts}")

        self._ensure_logged_in()
        self._profile_page.navigate(account_id)

        # Verify we're still logged in after navigation
        if not self._verify_logged_in_on_profile():
            # Force re-login
            logger.info("SESSION | forcing re-login")
            if self._username and self._password:
                self._login_page.login(self._username, self._password)
                # Save new session
                session_file = self.config.get("session_file")
                if session_file:
                    session_path = Path(session_file)
                    playwright_session = session_path.with_suffix('.playwright.json')
                    self._context.storage_state(path=str(playwright_session))
                    logger.info(f"SESSION | saved new Playwright session to {playwright_session}")
                # Navigate back to profile
                self._profile_page.navigate(account_id)
            else:
                raise AuthenticationError(
                    "Session expired and no credentials available for re-login",
                    platform=self.platform.value
                )

        # Check for private account
        if self._profile_page.is_private():
            raise PrivateAccountError(
                f"Account is private: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Collect all content links upfront (more reliable than ArrowRight navigation)
        # Use scroll_all if max_posts is very high (indicates user wants all posts)
        # Only enable scroll_all for very large requests (> 100 posts)
        scroll_all = max_posts > 100
        content_links = self._profile_page.get_post_links(max_posts, scroll_all=scroll_all)
        if not content_links:
            logger.error("No content found on profile")
            return

        logger.info(f"COLLECTED {len(content_links)} CONTENT LINKS")

        # Navigation variables
        posts_scraped = 0
        consecutive_failures = 0
        max_failures = 5
        seen_post_ids = set()

        # Iterate through collected content links
        for content_url in content_links:
            if posts_scraped >= max_posts:
                break

            # Navigate directly to the content
            try:
                self._page.goto(content_url, wait_until="domcontentloaded")
                # Wait for Instagram's React app to hydrate and render interactive elements
                # Try to wait for article element (indicates full page load) or buttons
                try:
                    self._page.wait_for_selector(
                        "article, button, div[role='dialog']",
                        timeout=10000
                    )
                except Exception:
                    pass  # Continue even if selector not found
                # Additional wait for JavaScript to fully execute
                self._page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Failed to navigate to {content_url}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
                continue

            # Get post ID from URL
            post_id = self._post_modal.get_post_id()

            if not post_id:
                # Try waiting a bit longer for the content to load
                self._post_modal.wait(1500)
                post_id = self._post_modal.get_post_id()

            if not post_id:
                logger.warning(f"Could not get post ID from {content_url}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
                continue

            # Skip if already seen
            if post_id in seen_post_ids:
                continue

            seen_post_ids.add(post_id)
            consecutive_failures = 0

            # Extract post data
            try:
                post_data = self._post_modal.extract_post_data(account_id)

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
                    logger.info(f"Post {post_id} before since_date, stopping")
                    break

                # Extract comments
                raw_comments = self._comments_section.extract_comments_for_post(post_id)
                comments = self._create_comment_objects(raw_comments, post_id)
                post.comments_count = len(comments)

                yield ExtractionResult(post=post, comments=comments)
                posts_scraped += 1
                consecutive_failures = 0

                logger.info(
                    f"SCRAPED | {posts_scraped}/{max_posts} | "
                    f"post_id={post_id} | comments={len(comments)}"
                )

                # Extended break check
                if self.should_take_extended_break():
                    self.take_extended_break()

            except Exception as e:
                logger.warning(f"Error extracting post {post_id}: {e}")
                consecutive_failures += 1

            if consecutive_failures >= max_failures:
                logger.warning("Too many failures, stopping")
                break

            # Human-like delay before next navigation
            self._post_modal.human_delay(1000, 2000)

        logger.info(
            f"EXTRACTION COMPLETE | account={account_id} | "
            f"posts={posts_scraped} | seen={len(seen_post_ids)}"
        )

    def close(self):
        """Clean up browser resources."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()

            logger.info("BROWSER SHUTDOWN | complete")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass
