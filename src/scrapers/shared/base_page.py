"""Unified Base Page Object with common functionality for all platforms."""

import logging
import random
import re
from typing import Optional, List, Any

from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

from .constants import TIMEOUTS

logger = logging.getLogger(__name__)


class BasePage:
    """Base class for all platform page objects with proper error handling."""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str, wait_until: str = "networkidle") -> "BasePage":
        """Navigate to a URL."""
        logger.debug(f"NAVIGATE | url={url}")
        self.page.goto(url, wait_until=wait_until)
        return self

    def wait(self, ms: int) -> "BasePage":
        """Wait for specified milliseconds."""
        self.page.wait_for_timeout(ms)
        return self

    def human_delay(self, min_ms: int = None, max_ms: int = None) -> "BasePage":
        """Wait for a random human-like delay."""
        min_ms = min_ms or TIMEOUTS.HUMAN_MIN
        max_ms = max_ms or TIMEOUTS.HUMAN_MAX
        delay = random.randint(min_ms, max_ms)
        self.page.wait_for_timeout(delay)
        return self

    def wait_for_load(self, timeout: int = 10000) -> "BasePage":
        """
        Wait for page to finish loading.

        Args:
            timeout: Maximum wait time in milliseconds

        Returns:
            Self for chaining
        """
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.debug(f"Wait for load timeout: {e}")
        return self

    def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """
        Wait for selector to appear.

        Args:
            selector: CSS selector
            timeout: Maximum wait time

        Returns:
            True if found
        """
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def click(self, selector: str, timeout: int = None, force: bool = False) -> bool:
        """
        Click an element with proper error handling.

        Args:
            selector: CSS selector
            timeout: Timeout in ms
            force: Force click without visibility check

        Returns:
            True if click succeeded, False otherwise
        """
        timeout = timeout or TIMEOUTS.ELEMENT_VISIBLE
        try:
            element = self.page.locator(selector).first
            if element.is_visible(timeout=timeout):
                element.click(force=force)
                return True
            return False
        except PlaywrightTimeout:
            logger.debug(f"Timeout clicking | selector={selector}")
            return False
        except PlaywrightError as e:
            logger.warning(f"Click failed | selector={selector} | error={type(e).__name__}: {e}")
            return False

    def fill(self, selector: str, text: str, timeout: int = None) -> bool:
        """
        Fill text into an input element.

        Args:
            selector: CSS selector
            text: Text to fill
            timeout: Timeout in ms

        Returns:
            True if fill succeeded, False otherwise
        """
        timeout = timeout or TIMEOUTS.ELEMENT_VISIBLE
        try:
            element = self.page.locator(selector).first
            element.wait_for(timeout=timeout)
            element.click()
            element.fill(text)
            return True
        except PlaywrightTimeout:
            logger.debug(f"Timeout filling | selector={selector}")
            return False
        except PlaywrightError as e:
            logger.warning(f"Fill failed | selector={selector} | error={type(e).__name__}: {e}")
            return False

    def get_text(self, selector: str, timeout: int = None) -> Optional[str]:
        """
        Get text content of an element.

        Args:
            selector: CSS selector
            timeout: Timeout in ms

        Returns:
            Text content or None if not found
        """
        timeout = timeout or TIMEOUTS.LONG_WAIT
        try:
            element = self.page.locator(selector).first
            if element.is_visible(timeout=timeout):
                return element.inner_text().strip()
            return None
        except PlaywrightTimeout:
            return None
        except PlaywrightError as e:
            logger.debug(f"Get text failed | selector={selector} | error={type(e).__name__}")
            return None

    def get_attribute(self, selector: str, attribute: str, timeout: int = None) -> Optional[str]:
        """
        Get an attribute value from an element.

        Args:
            selector: CSS selector
            attribute: Attribute name
            timeout: Timeout in ms

        Returns:
            Attribute value or None if not found
        """
        timeout = timeout or TIMEOUTS.LONG_WAIT
        try:
            element = self.page.locator(selector).first
            if element.is_visible(timeout=timeout):
                return element.get_attribute(attribute)
            return None
        except PlaywrightTimeout:
            return None
        except PlaywrightError:
            return None

    def is_visible(self, selector: str, timeout: int = None) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector
            timeout: Timeout in ms

        Returns:
            True if visible, False otherwise
        """
        timeout = timeout or TIMEOUTS.LONG_WAIT
        try:
            return self.page.locator(selector).first.is_visible(timeout=timeout)
        except PlaywrightTimeout:
            return False
        except PlaywrightError:
            return False

    def get_elements(self, selector: str) -> List[Locator]:
        """
        Get all elements matching a selector.

        Args:
            selector: CSS selector

        Returns:
            List of Locator objects
        """
        return self.page.locator(selector).all()

    def evaluate(self, script: str) -> Any:
        """
        Evaluate JavaScript in the page context.

        Args:
            script: JavaScript code to evaluate

        Returns:
            Result of the evaluation
        """
        return self.page.evaluate(script)

    def scroll_to_bottom(self) -> "BasePage":
        """Scroll to the bottom of the page."""
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        return self

    def scroll_by(self, pixels: int) -> "BasePage":
        """Scroll by a number of pixels."""
        self.evaluate(f"window.scrollBy(0, {pixels})")
        return self

    @property
    def current_url(self) -> str:
        """Get the current page URL."""
        return self.page.url

    def dismiss_popups(self, selectors: List[str]) -> "BasePage":
        """
        Attempt to dismiss popups using provided selectors.

        Args:
            selectors: List of CSS selectors for dismiss buttons

        Returns:
            Self for chaining
        """
        for selector in selectors:
            try:
                if self.is_visible(selector, timeout=500):
                    self.click(selector)
                    self.wait(500)
                    break
            except Exception:
                continue
        return self

    @staticmethod
    def parse_count(text: str) -> int:
        """
        Parse a count string like '1.5K', '2M', or '1B' into an integer.

        Args:
            text: Count string

        Returns:
            Integer count
        """
        if not text:
            return 0

        text = text.strip().lower()

        # Extract number and suffix
        match = re.search(r'([\d,.]+)\s*([kmb])?', text, re.IGNORECASE)
        if not match:
            return 0

        number_str = match.group(1).replace(',', '')
        suffix = match.group(2)

        try:
            number = float(number_str)

            # Apply multiplier based on suffix
            if suffix:
                suffix = suffix.lower()
                if suffix == 'k':
                    number *= 1000
                elif suffix == 'm':
                    number *= 1000000
                elif suffix == 'b':
                    number *= 1000000000

            return int(number)

        except (ValueError, TypeError):
            return 0
