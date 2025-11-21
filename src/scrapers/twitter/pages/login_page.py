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

    def is_logged_in(self) -> bool:
        if self.is_visible(Selectors.Home.LOGIN_BUTTON, timeout=1000):
            return False
        for selector in Selectors.Home.LOGGED_IN_INDICATORS:
            if self.is_visible(selector, timeout=1000):
                return True
        return False
