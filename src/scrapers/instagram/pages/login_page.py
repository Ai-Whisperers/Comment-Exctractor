"""Login Page Object for Instagram authentication."""

import logging
from typing import Optional
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Page Object for Instagram login page."""

    def navigate(self) -> "LoginPage":
        """
        Navigate to login page.

        Returns:
            Self for chaining
        """
        # Use domcontentloaded instead of networkidle to avoid timeout issues
        # Instagram keeps making background requests that prevent networkidle
        super().navigate(Selectors.URLs.LOGIN, wait_until="domcontentloaded")
        self.wait(3000)
        return self

    def handle_cookie_consent(self) -> "LoginPage":
        """
        Handle cookie consent popup if present.

        Returns:
            Self for chaining
        """
        cookie_selectors = [
            Selectors.Login.COOKIE_ALLOW_ALL,
            Selectors.Login.COOKIE_ALLOW_ESSENTIAL,
            Selectors.Login.COOKIE_DECLINE,
        ]

        for selector in cookie_selectors:
            if self.click(selector, timeout=2000):
                logger.debug(f"COOKIE CONSENT | clicked {selector}")
                self.human_delay()
                break

        return self

    def has_login_form(self) -> bool:
        """
        Check if login form is present.

        Returns:
            True if both username and password fields exist
        """
        return self.evaluate('''
            () => {
                const hasUsername = !!document.querySelector('input[name="username"]');
                const hasPassword = !!document.querySelector('input[name="password"]');
                return hasUsername && hasPassword;
            }
        ''')

    def enter_username(self, username: str) -> "LoginPage":
        """
        Enter username.

        Args:
            username: Instagram username

        Returns:
            Self for chaining
        """
        logger.debug("LOGIN | entering username")
        self.fill(Selectors.Login.USERNAME_INPUT, username)
        self.human_delay(300, 700)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """
        Enter password.

        Args:
            password: Instagram password

        Returns:
            Self for chaining
        """
        logger.debug("LOGIN | entering password")
        self.fill(Selectors.Login.PASSWORD_INPUT, password)
        self.human_delay(300, 700)
        return self

    def enter_credentials(self, username: str, password: str) -> "LoginPage":
        """
        Enter both username and password.

        Args:
            username: Instagram username
            password: Instagram password

        Returns:
            Self for chaining
        """
        return self.enter_username(username).enter_password(password)

    def submit(self) -> "LoginPage":
        """
        Submit the login form.

        Returns:
            Self for chaining
        """
        logger.debug("LOGIN | submitting form")
        self.human_delay()
        self.click(Selectors.Login.SUBMIT_BUTTON)
        self.wait_for_load()
        self.wait(3000)  # Give Instagram time to process
        return self

    def get_error_message(self) -> Optional[str]:
        """
        Get login error message if present.

        Returns:
            Error message or None
        """
        error_selectors = [
            Selectors.Login.ERROR_ALERT,
            Selectors.Login.ERROR_ROLE,
            Selectors.Login.ERROR_MESSAGE,
            Selectors.Login.ERROR_DIV,
        ]

        for selector in error_selectors:
            text = self.get_text(selector, timeout=1000)
            if text:
                return text

        return None

    def is_challenge_required(self) -> bool:
        """
        Check if login challenge/verification is required.

        Returns:
            True if on challenge page
        """
        return (
            self.url_contains(Selectors.URLs.CHALLENGE) or
            self.url_contains(Selectors.URLs.CHECKPOINT)
        )

    def is_still_on_login_page(self) -> bool:
        """
        Check if still on login page after submission.

        Returns:
            True if still on login page
        """
        return self.url_contains(Selectors.URLs.ACCOUNTS_LOGIN)

    def has_incorrect_credentials(self) -> bool:
        """
        Check if credentials were incorrect.

        Returns:
            True if error indicates wrong credentials
        """
        page_content = self.evaluate('() => document.body.innerText').lower()
        return "incorrect" in page_content or "wrong" in page_content

    def dismiss_save_login_popup(self) -> "LoginPage":
        """
        Dismiss 'Save login info' popup after login.

        Returns:
            Self for chaining
        """
        if self.click(Selectors.Login.NOT_NOW_BUTTON, timeout=5000):
            logger.debug("POPUP | dismissed save login info")
            self.human_delay()
        return self

    def dismiss_notifications_popup(self) -> "LoginPage":
        """
        Dismiss 'Turn on notifications' popup.

        Returns:
            Self for chaining
        """
        if self.click(Selectors.Login.NOT_NOW_BUTTON, timeout=3000):
            logger.debug("POPUP | dismissed notifications")
            self.human_delay()
        return self

    def login(self, username: str, password: str) -> bool:
        """
        Complete login flow.

        Args:
            username: Instagram username
            password: Instagram password

        Returns:
            True if login successful

        Raises:
            Exception: If login fails
        """
        logger.info(f"LOGIN START | username={username}")

        # Navigate and handle cookies
        self.navigate()
        self.handle_cookie_consent()

        # Check if already logged in (redirected away from login page)
        if not self.url_contains(Selectors.URLs.ACCOUNTS_LOGIN):
            logger.info("LOGIN | already logged in, redirected from login page")
            self.dismiss_save_login_popup()
            self.dismiss_notifications_popup()
            return True

        # Wait for form
        if not self.wait_for_selector(Selectors.Login.USERNAME_INPUT, timeout=10000):
            # Double check if we're logged in
            if not self.url_contains(Selectors.URLs.ACCOUNTS_LOGIN):
                logger.info("LOGIN | already logged in")
                return True
            raise Exception("Login form not found")

        # Enter credentials and submit
        self.enter_credentials(username, password)
        self.submit()

        # Check for errors
        error = self.get_error_message()
        if error:
            logger.error(f"LOGIN ERROR | {error}")
            # Save HTML debug on login error
            self._get_debug_logger().save_on_login_failure(
                page=self.page,
                reason=error,
                username=username,
                platform="instagram"
            )
            raise Exception(f"Login failed: {error}")

        # Check for challenge
        if self.is_challenge_required():
            # Save HTML debug on challenge required
            self._get_debug_logger().save_on_login_failure(
                page=self.page,
                reason="Challenge/verification required",
                username=username,
                platform="instagram"
            )
            raise Exception("Login requires verification (CAPTCHA, 2FA, or suspicious login challenge)")

        # Check if still on login page
        if self.is_still_on_login_page():
            if self.has_incorrect_credentials():
                # Save HTML debug on incorrect credentials
                self._get_debug_logger().save_on_login_failure(
                    page=self.page,
                    reason="Incorrect credentials",
                    username=username,
                    platform="instagram"
                )
                raise Exception("Incorrect username or password")
            self.wait(5000)  # Wait longer

        # Dismiss post-login popups
        self.dismiss_save_login_popup()
        self.dismiss_notifications_popup()

        logger.info("LOGIN SUCCESS")
        return True
