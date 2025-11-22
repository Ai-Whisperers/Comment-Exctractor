"""LinkedIn Login Page Object."""

import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """Page object for LinkedIn login functionality."""

    def __init__(self, page: Page):
        super().__init__(page)

    def login(self, email: str, password: str) -> None:
        logger.info(f"LOGIN START | email={email[:3]}***")

        self.navigate(Selectors.URLs.LOGIN, wait_until="domcontentloaded")
        self.wait(3000)

        # Handle cookie consent
        if self.is_visible(Selectors.Login.COOKIE_ACCEPT, timeout=2000):
            self.click(Selectors.Login.COOKIE_ACCEPT)
            self.human_delay(500, 1000)

        # Check if we're already on a page that shows we're logged in
        current_url = self.page.url
        logger.debug(f"LOGIN | current URL after navigate: {current_url}")

        if '/feed' in current_url or '/mynetwork' in current_url:
            logger.info("LOGIN | already logged in (redirected to feed)")
            return

        # Handle LinkedIn's "Remember Me" login page
        # This page shows saved accounts with buttons to click directly
        # The main elements are:
        # - button.member-profile__details (saved account button)
        # - button.signin-other-account (sign in with different account)

        # First check if we're on the Remember Me page
        member_profile_btn = self.page.locator("button.member-profile__details")
        signin_other_btn = self.page.locator("button.signin-other-account")

        if member_profile_btn.count() > 0:
            logger.debug(f"LOGIN | found {member_profile_btn.count()} saved account(s) on Remember Me page")

            # Check if the saved account matches our email
            for i in range(member_profile_btn.count()):
                btn = member_profile_btn.nth(i)
                aria_label = btn.get_attribute("aria-label") or ""
                logger.debug(f"LOGIN | saved account {i}: {aria_label}")

                # Click the button - it will take us to password prompt or log us in directly
                logger.debug(f"LOGIN | clicking saved account button")
                btn.click()
                self.wait(3000)

                # Check if we're now logged in (auto-login from saved session)
                current_url = self.page.url
                if '/feed' in current_url or '/mynetwork' in current_url:
                    logger.info("LOGIN SUCCESS | logged in via saved account")
                    return
                break
            else:
                # No saved accounts found, click "sign in with other account"
                if signin_other_btn.is_visible(timeout=1000):
                    logger.debug("LOGIN | clicking 'Sign in with other account'")
                    signin_other_btn.click()
                    self.wait(2000)
        elif signin_other_btn.is_visible(timeout=1000):
            # Only "sign in with other" button visible
            logger.debug("LOGIN | clicking 'Sign in with other account'")
            signin_other_btn.click()
            self.wait(2000)

        # Handle other "Sign in with different account" variations
        different_account_selectors = [
            "button:has-text('Sign in with a different account')",
            "button:has-text('Use another account')",
            "a:has-text('Sign in with a different account')",
            "a:has-text('Use another account')",
            "button:has-text('Sign in with another account')",
            # Spanish variants
            "button:has-text('Iniciar sesión con otra cuenta')",
            "a:has-text('Usar otra cuenta')",
        ]

        for selector in different_account_selectors:
            try:
                element = self.page.locator(selector)
                if element.is_visible(timeout=500):
                    logger.debug(f"LOGIN | clicking '{selector}'")
                    element.click()
                    self.wait(2000)
                    break
            except (PlaywrightTimeout, TimeoutError):
                continue

        # Check if we're on a password-only prompt (after clicking saved account)
        password_only = self.is_visible(Selectors.Login.PASSWORD_INPUT, timeout=2000)
        email_visible = self.is_visible(Selectors.Login.USERNAME_INPUT, timeout=500)

        # Also try alternative selectors
        if not email_visible:
            # LinkedIn sometimes uses different input selectors
            alt_selectors = ['input[name="session_key"]', 'input[autocomplete="username"]']
            for sel in alt_selectors:
                if self.is_visible(sel, timeout=500):
                    logger.debug(f"LOGIN | found alternative email selector: {sel}")
                    email_visible = True
                    break

        if password_only and not email_visible:
            # We're on password-only prompt (saved account was clicked)
            logger.debug("LOGIN | on password-only prompt")
        elif not email_visible:
            # Log current state for debugging
            current_url = self.page.url
            logger.warning(f"LOGIN | current URL: {current_url}")
            logger.warning("LOGIN | email input not found, page may require manual interaction")
            logger.warning("LOGIN | Please click on your account or navigate to the login form...")
            logger.warning("LOGIN | Waiting 60 seconds for manual intervention...")

            # Save debug HTML
            self.save_debug_html("login_form_not_found", f"url={current_url}")

            for i in range(12):  # 12 x 5 seconds = 60 seconds
                self.wait(5000)
                if self.is_visible(Selectors.Login.USERNAME_INPUT, timeout=500) or \
                   self.is_visible(Selectors.Login.PASSWORD_INPUT, timeout=500):
                    break
                if i == 11:
                    # Save another debug snapshot before failing
                    self.save_debug_html("login_timeout", f"url={self.page.url}")
                    raise Exception("Login form not found after 60s - LinkedIn may be showing a CAPTCHA or other challenge")

        # Re-check what fields are visible now
        email_visible = self.is_visible(Selectors.Login.USERNAME_INPUT, timeout=1000)
        password_visible = self.is_visible(Selectors.Login.PASSWORD_INPUT, timeout=1000)

        # Enter email (if field is visible)
        if email_visible:
            logger.debug("LOGIN | entering email")
            if not self.fill(Selectors.Login.USERNAME_INPUT, email):
                logger.warning("LOGIN | failed to fill email field")
            self.human_delay(300, 600)
        else:
            logger.debug("LOGIN | skipping email entry (password-only prompt)")

        # Enter password
        if password_visible:
            logger.debug("LOGIN | entering password")
            if not self.fill(Selectors.Login.PASSWORD_INPUT, password):
                raise Exception("Failed to enter password - input field not found")
            self.human_delay(300, 600)
        else:
            raise Exception("Password field not found")

        # Click login
        logger.debug("LOGIN | clicking submit button")
        self.click(Selectors.Login.LOGIN_BUTTON)
        self.wait(8000)  # Wait longer for login to complete

        self.dismiss_popups()

        # Check for checkpoint/verification pages
        current_url = self.page.url
        if '/checkpoint' in current_url:
            logger.warning("LOGIN | Checkpoint/verification detected - please complete it manually")
            logger.warning("LOGIN | Waiting up to 60 seconds for manual verification...")
            # Wait for user to complete verification
            for i in range(12):  # 12 x 5 seconds = 60 seconds
                self.wait(5000)
                current_url = self.page.url
                if '/checkpoint' not in current_url and '/uas/login' not in current_url:
                    break
                if i == 11:
                    logger.warning("LOGIN | Verification timeout - please complete it faster next time")

        # Check for security challenges
        if self.is_visible(Selectors.RateLimit.CHALLENGE, timeout=2000):
            logger.warning("LOGIN | Security challenge detected - you may need to complete it manually")
            self.wait(30000)  # Wait for user to complete challenge

        if self.is_visible(Selectors.RateLimit.CAPTCHA, timeout=2000):
            logger.warning("LOGIN | CAPTCHA detected - you may need to complete it manually")
            self.wait(30000)  # Wait for user to complete CAPTCHA

        if not self.is_logged_in():
            # Try waiting a bit more
            logger.debug("LOGIN | waiting additional time for page load")
            self.wait(5000)
            if not self.is_logged_in():
                raise Exception("Login verification failed - please check your LinkedIn credentials and complete any security challenges")

        logger.info("LOGIN SUCCESS")

    def is_logged_in(self) -> bool:
        # Check URL first - if we're on the feed, we're logged in
        current_url = self.page.url
        logger.debug(f"LOGIN CHECK | current URL: {current_url}")

        if '/feed' in current_url or '/mynetwork' in current_url:
            return True

        if self.is_visible(Selectors.Home.LOGIN_BUTTON, timeout=1000):
            return False

        for selector in Selectors.Home.LOGGED_IN_INDICATORS:
            if self.is_visible(selector, timeout=1000):
                logger.debug(f"LOGIN CHECK | found indicator: {selector}")
                return True
        return False
