"""Twitter Login Page Object."""

import logging
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Page object for Twitter login functionality."""

    def __init__(self, page: Page):
        super().__init__(page)

    def login(self, username: str, password: str) -> None:
        logger.info(f"LOGIN START | username={username[:3]}***")

        self.navigate(Selectors.URLs.LOGIN, wait_until="domcontentloaded")
        self.wait(3000)

        # Handle cookie consent
        if self.is_visible(Selectors.Login.COOKIE_ACCEPT, timeout=2000):
            self.click(Selectors.Login.COOKIE_ACCEPT)
            self.human_delay(500, 1000)

        # Enter username
        logger.debug("LOGIN | entering username")
        self.fill(Selectors.Login.USERNAME_INPUT, username)
        self.human_delay(300, 600)
        self.click(Selectors.Login.NEXT_BUTTON)
        self.wait(2000)

        # Enter password
        logger.debug("LOGIN | entering password")
        self.fill(Selectors.Login.PASSWORD_INPUT, password)
        self.human_delay(300, 600)
        self.click(Selectors.Login.LOGIN_BUTTON)
        self.wait(3000)

        self.dismiss_popups()

        if not self.is_logged_in():
            raise Exception("Login verification failed")

        logger.info("LOGIN SUCCESS")

    def login_with_google(self, email: str, password: str) -> None:
        """
        Login to Twitter using Google OAuth.

        This will open a Google popup where the user enters their Google credentials.
        The browser profile should persist the session for future use.

        Args:
            email: Google account email
            password: Google account password
        """
        logger.info(f"GOOGLE LOGIN START | email={email[:3]}***")

        self.navigate(Selectors.URLs.LOGIN, wait_until="domcontentloaded")
        self.wait(3000)

        # Handle cookie consent
        if self.is_visible(Selectors.Login.COOKIE_ACCEPT, timeout=2000):
            self.click(Selectors.Login.COOKIE_ACCEPT)
            self.human_delay(500, 1000)

        # Click "Sign in with Google" button
        logger.debug("GOOGLE LOGIN | clicking Google sign-in button")

        # Wait for the Google button to appear
        if not self.is_visible(Selectors.Login.GOOGLE_SIGNIN, timeout=5000):
            raise Exception("Google sign-in button not found on login page")

        # Handle popup window for Google OAuth
        with self.page.context.expect_page() as popup_info:
            self.click(Selectors.Login.GOOGLE_SIGNIN)

        google_popup = popup_info.value
        logger.debug("GOOGLE LOGIN | Google popup opened")

        # Wait for popup to load
        google_popup.wait_for_load_state("domcontentloaded")
        self.human_delay(2000, 3000)

        try:
            # Enter email in Google popup
            email_input = google_popup.locator("input[type='email']")
            if email_input.is_visible(timeout=5000):
                logger.debug("GOOGLE LOGIN | entering email")
                email_input.fill(email)
                self.human_delay(300, 600)

                # Click Next button
                next_button = google_popup.locator("button:has-text('Next'), #identifierNext")
                next_button.click()
                google_popup.wait_for_timeout(3000)

            # Enter password in Google popup
            password_input = google_popup.locator("input[type='password']")
            if password_input.is_visible(timeout=5000):
                logger.debug("GOOGLE LOGIN | entering password")
                password_input.fill(password)
                self.human_delay(300, 600)

                # Click Next button
                next_button = google_popup.locator("button:has-text('Next'), #passwordNext")
                next_button.click()
                google_popup.wait_for_timeout(3000)

            # Handle "Continue" or "Allow" buttons if they appear
            continue_button = google_popup.locator("button:has-text('Continue'), button:has-text('Allow')")
            if continue_button.is_visible(timeout=3000):
                continue_button.click()
                google_popup.wait_for_timeout(2000)

        except Exception as e:
            logger.warning(f"GOOGLE LOGIN | popup interaction issue: {e}")
            # Popup may have closed automatically after auth

        # Wait for redirect back to Twitter
        self.wait(5000)
        self.dismiss_popups()

        if not self.is_logged_in():
            raise Exception("Google login verification failed - you may need to complete login manually")

        logger.info("GOOGLE LOGIN SUCCESS")

    def is_logged_in(self) -> bool:
        if self.is_visible(Selectors.Home.LOGIN_BUTTON, timeout=1000):
            return False
        for selector in Selectors.Home.LOGGED_IN_INDICATORS:
            if self.is_visible(selector, timeout=1000):
                return True
        return False
