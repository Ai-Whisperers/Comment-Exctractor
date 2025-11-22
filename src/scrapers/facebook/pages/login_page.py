"""Facebook Login Page Object."""

import logging
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Page object for Facebook login functionality."""

    def __init__(self, page: Page):
        """
        Initialize login page.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)

    def login(self, email: str, password: str) -> None:
        """
        Perform login to Facebook.

        Args:
            email: Facebook email
            password: Facebook password

        Raises:
            Exception: If login fails
        """
        logger.info(f"LOGIN START | email={email[:3]}***")

        # Navigate to Facebook
        self.navigate(Selectors.URLs.HOME, wait_until="domcontentloaded")
        self.wait(2000)

        # Handle cookie consent
        self._handle_cookie_consent()

        # Check if already logged in
        if self.is_logged_in():
            logger.info("LOGIN | already logged in")
            return

        # Fill login form
        logger.debug("LOGIN | filling email")
        self.fill(Selectors.Login.EMAIL_INPUT, email)
        self.human_delay(300, 600)

        logger.debug("LOGIN | filling password")
        self.fill(Selectors.Login.PASSWORD_INPUT, password)
        self.human_delay(300, 600)

        # Submit
        logger.debug("LOGIN | submitting")
        self.click(Selectors.Login.LOGIN_BUTTON)
        self.wait(3000)

        # Wait for navigation with extended timeout for 2FA/verification
        try:
            self.wait_for_load(timeout=30000)
        except Exception:
            logger.debug("LOGIN | load timeout, continuing...")

        # Wait longer for manual verification if needed
        max_verification_wait = 120  # 2 minutes for manual verification
        check_interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < max_verification_wait:
            # Check if we're past the login
            if self.is_logged_in():
                break

            # Check for checkpoint - wait for user to complete
            if Selectors.URLs.CHECKPOINT in self.current_url:
                logger.info(f"LOGIN | security checkpoint detected - waiting for manual verification ({elapsed}s/{max_verification_wait}s)")
                self.wait(check_interval * 1000)
                elapsed += check_interval
                continue

            # Check if still on login page
            if Selectors.URLs.LOGIN_PATH in self.current_url:
                logger.debug(f"LOGIN | still on login page, waiting... ({elapsed}s)")
                self.wait(check_interval * 1000)
                elapsed += check_interval
                continue

            # Neither checkpoint nor login page - might be logged in or elsewhere
            break

        self.human_delay(1000, 2000)

        # Dismiss any post-login popups
        self.dismiss_popups()

        # Verify login
        if not self.is_logged_in():
            # Check for checkpoint
            if Selectors.URLs.CHECKPOINT in self.current_url:
                # Save HTML debug on checkpoint
                self._get_debug_logger().save_on_login_failure(
                    page=self.page,
                    reason="Security checkpoint timeout",
                    username=email,
                    platform="facebook"
                )
                raise Exception("Security checkpoint detected - manual verification required (timeout)")
            # Save HTML debug on login failure
            self._get_debug_logger().save_on_login_failure(
                page=self.page,
                reason="Login verification failed",
                username=email,
                platform="facebook"
            )
            raise Exception("Login verification failed")

        logger.info("LOGIN SUCCESS")

    def is_logged_in(self) -> bool:
        """
        Check if user is logged in.

        Returns:
            True if logged in
        """
        # Check if login form is present (not logged in)
        if self.is_visible(Selectors.Login.EMAIL_INPUT, timeout=1000):
            return False

        # Check URL
        if Selectors.URLs.LOGIN_PATH in self.current_url:
            return False

        # Check for logged-in indicators
        for selector in Selectors.Home.LOGGED_IN_INDICATORS:
            try:
                if self.is_visible(selector, timeout=1000):
                    return True
            except Exception:
                continue

        # Check for news feed
        if self.is_visible(Selectors.Home.NEWS_FEED, timeout=1000):
            return True

        return False

    def _handle_cookie_consent(self) -> None:
        """Handle cookie consent popup if present."""
        try:
            if self.is_visible(Selectors.Login.COOKIE_ACCEPT, timeout=2000):
                logger.debug("POPUP | handling cookie consent")
                self.click(Selectors.Login.COOKIE_ACCEPT)
                self.human_delay(500, 1000)
        except Exception:
            pass
