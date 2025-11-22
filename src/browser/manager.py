"""Browser lifecycle management."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from ..config.constants import BROWSER, TIMEOUTS

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages browser lifecycle with anti-detection and session persistence.

    This class centralizes all browser initialization, context creation,
    and cleanup operations that were previously duplicated across scrapers.
    """

    def __init__(
        self,
        headless: bool = False,
        viewport_width: int = None,
        viewport_height: int = None,
        user_agent: str = None,
    ):
        """
        Initialize browser manager.

        Args:
            headless: Run browser in headless mode (default False for reliable scraping)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            user_agent: Custom user agent string
        """
        self._headless = headless
        self._viewport_width = viewport_width or BROWSER.DEFAULT_WIDTH
        self._viewport_height = viewport_height or BROWSER.DEFAULT_HEIGHT
        self._user_agent = user_agent or BROWSER.DESKTOP_USER_AGENT

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self._is_initialized = False

    def initialize(self, session_file: Optional[str] = None) -> "BrowserManager":
        """
        Initialize Playwright browser with anti-detection settings.

        Args:
            session_file: Path to session storage file for persistence

        Returns:
            Self for chaining
        """
        if self._is_initialized:
            logger.warning("Browser already initialized")
            return self

        logger.info(
            f"BROWSER INIT | headless={self._headless} | "
            f"viewport={self._viewport_width}x{self._viewport_height}"
        )

        # Start Playwright
        self._playwright = sync_playwright().start()

        # Launch browser with anti-detection
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            args=BROWSER.CHROMIUM_ARGS,
        )

        # Load session if available
        storage_state = None
        if session_file and Path(session_file).exists():
            try:
                storage_state = session_file
                logger.info(f"BROWSER INIT | loading session from {session_file}")
            except Exception as e:
                logger.warning(f"Failed to load session: {e}")

        # Create context with settings
        self._context = self._browser.new_context(
            storage_state=storage_state,
            viewport={
                "width": self._viewport_width,
                "height": self._viewport_height,
            },
            user_agent=self._user_agent,
        )

        # Create page
        self._page = self._context.new_page()

        # Set default timeouts
        self._page.set_default_timeout(TIMEOUTS.PAGE_LOAD)
        self._page.set_default_navigation_timeout(TIMEOUTS.PAGE_LOAD)

        self._is_initialized = True
        logger.info("BROWSER INIT | complete")

        return self

    @property
    def page(self) -> Page:
        """Get the current page instance."""
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """Get the current browser context."""
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self._context

    @property
    def browser(self) -> Browser:
        """Get the browser instance."""
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self._browser

    def new_page(self) -> Page:
        """
        Create a new page in the current context.

        Returns:
            New Page instance
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self._context.new_page()

    def save_session(self, session_file: str) -> None:
        """
        Save current session state for persistence.

        Args:
            session_file: Path to save session state
        """
        if not self._is_initialized:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        try:
            # Ensure directory exists
            session_path = Path(session_file)
            session_path.parent.mkdir(parents=True, exist_ok=True)

            self._context.storage_state(path=session_file)
            logger.info(f"SESSION | saved to {session_file}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise

    def close(self) -> None:
        """Clean up browser resources."""
        try:
            if self._page:
                self._page.close()
                self._page = None

            if self._context:
                self._context.close()
                self._context = None

            if self._browser:
                self._browser.close()
                self._browser = None

            if self._playwright:
                self._playwright.stop()
                self._playwright = None

            self._is_initialized = False
            logger.info("BROWSER SHUTDOWN | complete")

        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")

    def __enter__(self) -> "BrowserManager":
        """Context manager entry."""
        return self.initialize()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass
