"""Unified Base Page Object with common functionality for all platforms."""

import logging
import random
import re
from typing import Optional, List, Any, Dict

from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

from .constants import TIMEOUTS
from ...utils.html_debug_logger import HTMLDebugLogger, get_debug_logger

logger = logging.getLogger(__name__)


class BasePage:
    """Base class for all platform page objects with proper error handling."""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str, wait_until: str = "networkidle", timeout: int = 60000) -> "BasePage":
        """Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
            timeout: Navigation timeout in milliseconds (default: 60000)
        """
        logger.debug(f"NAVIGATE | url={url}")
        self.page.goto(url, wait_until=wait_until, timeout=timeout)
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
        except (PlaywrightTimeout, TimeoutError):
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

    def url_contains(self, pattern: str) -> bool:
        """
        Check if current URL contains pattern.

        Args:
            pattern: String pattern to search for

        Returns:
            True if pattern found in URL
        """
        return pattern in self.page.url

    def press_key(self, key: str) -> "BasePage":
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., "ArrowRight", "Escape", "Enter")

        Returns:
            Self for chaining
        """
        self.page.keyboard.press(key)
        return self

    def query_selector(self, selector: str):
        """
        Query selector using page.query_selector.

        Args:
            selector: CSS selector

        Returns:
            Element handle or None
        """
        return self.page.query_selector(selector)

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
            except (PlaywrightTimeout, TimeoutError):
                continue
        return self

    @staticmethod
    def parse_count(text: str) -> int:
        """
        Parse a count string like '1.5K', '2M', '1B', or Spanish formats into an integer.

        Supports:
        - English: 1.5K, 2M, 1B
        - Spanish: 8,5 mil, 1,2 millones, 500 mil
        - Plain numbers: 1,234 or 1.234

        Args:
            text: Count string

        Returns:
            Integer count
        """
        if not text:
            return 0

        text = text.strip().lower()

        # Handle Spanish word multipliers first
        # "mil" = thousands, "millon/millones" = millions
        if 'millon' in text or 'mill' in text:
            # Extract number before "millon/millones"
            match = re.search(r'([\d,.]+)', text)
            if match:
                # Spanish uses comma as decimal separator
                number_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    return int(float(number_str) * 1000000)
                except (ValueError, TypeError):
                    return 0

        if ' mil' in text or text.endswith('mil'):
            # Extract number before "mil"
            match = re.search(r'([\d,.]+)', text)
            if match:
                # Spanish uses comma as decimal separator
                number_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    return int(float(number_str) * 1000)
                except (ValueError, TypeError):
                    return 0

        # Extract number and suffix for English format (K, M, B)
        # Suffix must be:
        # 1. Followed by whitespace or non-alphanumeric (to avoid "7b09" -> 7B)
        # 2. The number must look like a social media count (not embedded in garbage text)
        # 3. Prefer numbers that appear early in the text (more likely to be the actual count)

        # First, try to find a clean number with optional K/M/B suffix
        # Pattern: number optionally followed by K/M/B, then word boundary or non-letter
        match = re.search(r'\b([\d,.]+)\s*([kmb])\b', text, re.IGNORECASE)
        if match:
            number_str = match.group(1)
            suffix = match.group(2)
        else:
            # Try without suffix - look for clean number at word boundary
            match = re.search(r'\b([\d,.]+)\b', text)
            if not match:
                # Last resort: any number
                match = re.search(r'([\d,.]+)', text)
                if not match:
                    return 0
            number_str = match.group(1)
            suffix = None

        # Determine decimal separator based on format
        # If string has both . and , check which comes last (that's the decimal)
        if '.' in number_str and ',' in number_str:
            # European format: 1.234,56 -> comma is decimal
            if number_str.rfind(',') > number_str.rfind('.'):
                number_str = number_str.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234.56 -> period is decimal
                number_str = number_str.replace(',', '')
        elif ',' in number_str:
            # Could be Spanish decimal (8,5) or US thousands (1,000)
            # If comma is followed by 1-2 digits at end, it's decimal
            if re.search(r',\d{1,2}$', number_str):
                number_str = number_str.replace(',', '.')
            else:
                number_str = number_str.replace(',', '')

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

    # HTML Debug Logging Methods
    # These methods allow pages to save HTML snapshots when issues occur

    def _get_debug_logger(self) -> HTMLDebugLogger:
        """Get the HTML debug logger instance."""
        return get_debug_logger()

    def _get_platform_name(self) -> str:
        """
        Get the platform name from the class hierarchy.
        Override in subclasses if needed.
        """
        # Try to determine platform from class name or module
        class_name = self.__class__.__name__.lower()
        module_name = self.__class__.__module__.lower()

        for platform in ['instagram', 'facebook', 'twitter', 'linkedin']:
            if platform in module_name or platform in class_name:
                return platform

        return "unknown"

    def _get_page_type(self) -> str:
        """
        Get the page type from the class name.
        Override in subclasses if needed.
        """
        class_name = self.__class__.__name__.lower()

        if 'login' in class_name:
            return HTMLDebugLogger.PAGE_LOGIN
        elif 'profile' in class_name:
            return HTMLDebugLogger.PAGE_PROFILE
        elif 'comment' in class_name:
            return HTMLDebugLogger.PAGE_COMMENTS
        elif 'post' in class_name or 'modal' in class_name:
            return HTMLDebugLogger.PAGE_POST
        elif 'home' in class_name:
            return HTMLDebugLogger.PAGE_HOME
        else:
            return HTMLDebugLogger.PAGE_UNKNOWN

    def save_debug_html(
        self,
        reason: str,
        context: str = "",
        page_type: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save HTML snapshot for debugging.

        Args:
            reason: Why this dump was triggered
            context: Additional context (e.g., post_id, username)
            page_type: Override auto-detected page type
            additional_info: Any additional debug information

        Returns:
            Path to saved file
        """
        return self._get_debug_logger().save_debug_html(
            page=self.page,
            page_type=page_type or self._get_page_type(),
            reason=reason,
            context=context,
            platform=self._get_platform_name(),
            additional_info=additional_info
        )

    def save_on_error(self, error: Exception, context: str = "") -> str:
        """
        Save HTML when an error occurs.

        Args:
            error: The exception that occurred
            context: Additional context

        Returns:
            Path to saved file
        """
        return self._get_debug_logger().save_on_error(
            page=self.page,
            page_type=self._get_page_type(),
            error=error,
            context=context,
            platform=self._get_platform_name()
        )

    def save_on_unexpected(
        self,
        expected: str,
        actual: str,
        context: str = ""
    ) -> str:
        """
        Save HTML when something unexpected happens.

        Args:
            expected: What was expected
            actual: What actually happened
            context: Additional context

        Returns:
            Path to saved file
        """
        return self._get_debug_logger().save_on_unexpected(
            page=self.page,
            page_type=self._get_page_type(),
            expected=expected,
            actual=actual,
            context=context,
            platform=self._get_platform_name()
        )

    def save_on_timeout(
        self,
        waiting_for: str,
        timeout_ms: int,
        context: str = ""
    ) -> str:
        """
        Save HTML when a timeout occurs.

        Args:
            waiting_for: What we were waiting for
            timeout_ms: Timeout in milliseconds
            context: Additional context

        Returns:
            Path to saved file
        """
        return self._get_debug_logger().save_on_timeout(
            page=self.page,
            page_type=self._get_page_type(),
            waiting_for=waiting_for,
            timeout_ms=timeout_ms,
            context=context,
            platform=self._get_platform_name()
        )
