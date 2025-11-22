"""
Unified Browser Manager for all platform scrapers.

This module provides centralized browser lifecycle management,
eliminating code duplication across scrapers.
"""

import logging
import os
import random
import stat
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
)

from .constants import VIEWPORTS, USER_AGENTS, BROWSER_ARGS, TIMEOUTS

logger = logging.getLogger(__name__)


class BrowserPool:
    """
    Thread-safe pool of browser instances for reuse across scraping sessions.

    This pool reduces the overhead of repeatedly starting and stopping
    Playwright/browsers by maintaining a set of ready-to-use browser instances.

    Features:
    - Configurable pool size per platform
    - Automatic browser recreation on errors
    - Thread-safe access to browsers
    - Automatic cleanup of idle browsers

    Example:
        >>> pool = BrowserPool(max_browsers=3)
        >>> browser, playwright = pool.acquire("instagram")
        >>> # Use browser...
        >>> pool.release("instagram", browser, playwright)
        >>> pool.close()
    """

    def __init__(self, max_browsers: int = 2, idle_timeout: int = 300):
        """
        Initialize browser pool.

        Args:
            max_browsers: Maximum browsers per platform
            idle_timeout: Seconds before idle browser is closed
        """
        self._max_browsers = max_browsers
        self._idle_timeout = idle_timeout
        self._lock = threading.RLock()

        # pool structure: {platform: [(browser, playwright, last_used_time), ...]}
        self._pool: Dict[str, List[tuple]] = {}
        self._in_use: Dict[str, int] = {}  # Track browsers in use per platform

        logger.info(f"BROWSER POOL | initialized | max={max_browsers} | idle_timeout={idle_timeout}s")

    def acquire(
        self,
        platform: str,
        headless: bool = False,
        browser_args: Optional[List[str]] = None,
        proxy: Optional[str] = None
    ) -> tuple:
        """
        Acquire a browser from the pool or create a new one.

        Args:
            platform: Platform name
            headless: Run in headless mode
            browser_args: Additional browser arguments
            proxy: Proxy server URL

        Returns:
            Tuple of (Browser, Playwright)
        """
        with self._lock:
            if platform not in self._pool:
                self._pool[platform] = []
                self._in_use[platform] = 0

            # Try to get an existing browser
            available = self._pool[platform]
            if available:
                browser, playwright, _ = available.pop(0)
                self._in_use[platform] += 1
                logger.debug(f"BROWSER POOL | acquired existing | platform={platform}")
                return browser, playwright

            # Check if we can create a new one
            if self._in_use[platform] < self._max_browsers:
                browser, playwright = self._create_browser(
                    headless, browser_args or BROWSER_ARGS.copy(), proxy
                )
                self._in_use[platform] += 1
                logger.debug(f"BROWSER POOL | created new | platform={platform}")
                return browser, playwright

            # All browsers in use - wait and retry
            logger.warning(
                f"BROWSER POOL | all browsers in use | platform={platform} | "
                f"in_use={self._in_use[platform]}/{self._max_browsers}"
            )
            raise RuntimeError(f"No available browsers for {platform}")

    def release(self, platform: str, browser: Browser, playwright: Playwright) -> None:
        """
        Release a browser back to the pool.

        Args:
            platform: Platform name
            browser: Browser instance to release
            playwright: Playwright instance
        """
        with self._lock:
            if platform not in self._pool:
                self._pool[platform] = []

            # Check if browser is still usable
            try:
                if browser.is_connected():
                    self._pool[platform].append((browser, playwright, time.time()))
                    logger.debug(f"BROWSER POOL | released | platform={platform}")
                else:
                    self._close_browser(browser, playwright)
                    logger.debug(f"BROWSER POOL | browser disconnected, closed | platform={platform}")
            except Exception as e:
                logger.warning(f"BROWSER POOL | error releasing browser: {e}")
                self._close_browser(browser, playwright)

            if platform in self._in_use:
                self._in_use[platform] = max(0, self._in_use[platform] - 1)

    def _create_browser(
        self,
        headless: bool,
        browser_args: List[str],
        proxy: Optional[str]
    ) -> tuple:
        """Create a new browser instance."""
        playwright = sync_playwright().start()

        launch_options = {
            "headless": headless,
            "args": browser_args,
        }

        if proxy:
            launch_options["proxy"] = {"server": proxy}

        browser = playwright.chromium.launch(**launch_options)
        return browser, playwright

    def _close_browser(self, browser: Browser, playwright: Playwright) -> None:
        """Close a browser and its playwright instance."""
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    def cleanup_idle(self) -> int:
        """
        Close browsers that have been idle too long.

        Returns:
            Number of browsers closed
        """
        closed = 0
        current_time = time.time()

        with self._lock:
            for platform in list(self._pool.keys()):
                remaining = []
                for browser, playwright, last_used in self._pool[platform]:
                    if current_time - last_used > self._idle_timeout:
                        self._close_browser(browser, playwright)
                        closed += 1
                    else:
                        remaining.append((browser, playwright, last_used))
                self._pool[platform] = remaining

        if closed > 0:
            logger.info(f"BROWSER POOL | cleanup | closed={closed} idle browsers")

        return closed

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            stats = {
                "max_browsers": self._max_browsers,
                "platforms": {},
            }
            for platform in self._pool:
                stats["platforms"][platform] = {
                    "available": len(self._pool[platform]),
                    "in_use": self._in_use.get(platform, 0),
                }
            return stats

    def close(self) -> None:
        """Close all browsers in the pool."""
        with self._lock:
            for platform in list(self._pool.keys()):
                for browser, playwright, _ in self._pool[platform]:
                    self._close_browser(browser, playwright)
                self._pool[platform] = []
                self._in_use[platform] = 0

        logger.info("BROWSER POOL | closed all browsers")

    def __enter__(self) -> "BrowserPool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False


# Global browser pool singleton
_global_pool: Optional[BrowserPool] = None
_pool_lock = threading.Lock()


def get_browser_pool(max_browsers: int = 2, idle_timeout: int = 300) -> BrowserPool:
    """
    Get or create the global browser pool.

    Args:
        max_browsers: Maximum browsers per platform
        idle_timeout: Seconds before idle browser is closed

    Returns:
        Global BrowserPool instance
    """
    global _global_pool
    with _pool_lock:
        if _global_pool is None:
            _global_pool = BrowserPool(max_browsers, idle_timeout)
        return _global_pool


def close_browser_pool() -> None:
    """Close the global browser pool."""
    global _global_pool
    with _pool_lock:
        if _global_pool is not None:
            _global_pool.close()
            _global_pool = None


@dataclass
class BrowserConfig:
    """
    Configuration for browser creation.

    Attributes:
        headless: Run browser in headless mode
        profile_dir: Directory for persistent browser profile
        viewport: Browser viewport dimensions
        user_agent: User agent string (random if None)
        storage_state: Path to storage state JSON file
        browser_args: Additional browser arguments
        proxy: Proxy server URL
    """
    headless: bool = False
    profile_dir: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=lambda: VIEWPORTS.DEFAULT.copy())
    user_agent: Optional[str] = None
    storage_state: Optional[str] = None
    browser_args: List[str] = field(default_factory=lambda: BROWSER_ARGS.copy())
    proxy: Optional[str] = None

    def __post_init__(self):
        if self.user_agent is None:
            self.user_agent = random.choice(USER_AGENTS)


class BrowserManager:
    """
    Centralized browser lifecycle management for all scrapers.

    This class handles browser creation, configuration, and cleanup,
    providing a consistent interface across all platform scrapers.

    Supports:
    - Persistent browser profiles (preserves cookies/sessions)
    - Non-persistent contexts with optional storage state
    - Proxy configuration
    - Anti-detection measures

    Example:
        >>> config = BrowserConfig(headless=False, profile_dir="./profiles/instagram")
        >>> with BrowserManager(config, "instagram") as manager:
        ...     page = manager.page
        ...     page.goto("https://instagram.com")
        ...     # Do scraping

    Attributes:
        playwright: Playwright instance
        browser: Browser instance (None for persistent contexts)
        context: Browser context
        page: Active page
        platform: Platform name for logging
    """

    def __init__(self, config: BrowserConfig, platform: str):
        """
        Initialize browser manager.

        Args:
            config: Browser configuration
            platform: Platform name (for logging)
        """
        self.config = config
        self.platform = platform

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize Playwright browser and context."""
        logger.info(
            f"BROWSER INIT | platform={self.platform} | "
            f"headless={self.config.headless} | "
            f"profile={'persistent' if self.config.profile_dir else 'temporary'}"
        )

        self._playwright = sync_playwright().start()

        if self.config.profile_dir:
            self._init_persistent_context()
        else:
            self._init_standard_context()

        logger.info(f"BROWSER INIT | complete | platform={self.platform}")

    def _init_persistent_context(self) -> None:
        """Initialize a persistent browser context with saved profile."""
        profile_path = Path(self.config.profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Using persistent context: {profile_path}")

        # Build launch options
        launch_options = {
            "headless": self.config.headless,
            "viewport": self.config.viewport,
            "user_agent": self.config.user_agent,
            "args": self.config.browser_args,
        }

        # Add proxy if configured
        if self.config.proxy:
            launch_options["proxy"] = {"server": self.config.proxy}
            logger.debug(f"Proxy configured: {self._mask_proxy(self.config.proxy)}")

        self._context = self._playwright.chromium.launch_persistent_context(
            str(profile_path),
            **launch_options
        )

        # Use existing page or create new one
        self._page = (
            self._context.pages[0]
            if self._context.pages
            else self._context.new_page()
        )

    def _init_standard_context(self) -> None:
        """Initialize a standard (non-persistent) browser context."""
        # Launch browser
        launch_options = {
            "headless": self.config.headless,
            "args": self.config.browser_args,
        }

        if self.config.proxy:
            launch_options["proxy"] = {"server": self.config.proxy}
            logger.debug(f"Proxy configured: {self._mask_proxy(self.config.proxy)}")

        self._browser = self._playwright.chromium.launch(**launch_options)

        # Create context with optional storage state
        context_options = {
            "viewport": self.config.viewport,
            "user_agent": self.config.user_agent,
        }

        if self.config.storage_state and Path(self.config.storage_state).exists():
            context_options["storage_state"] = self.config.storage_state
            logger.debug(f"Loading storage state: {self.config.storage_state}")

        self._context = self._browser.new_context(**context_options)
        self._page = self._context.new_page()

    @staticmethod
    def _mask_proxy(proxy: str) -> str:
        """Mask proxy URL for logging (hide credentials)."""
        if "@" in proxy:
            parts = proxy.split("@")
            return f"***@{parts[-1]}"
        return proxy

    @property
    def playwright(self) -> Playwright:
        """Get Playwright instance."""
        return self._playwright

    @property
    def browser(self) -> Optional[Browser]:
        """Get Browser instance (None for persistent contexts)."""
        return self._browser

    @property
    def context(self) -> BrowserContext:
        """Get BrowserContext instance."""
        return self._context

    @property
    def page(self) -> Page:
        """Get active Page instance."""
        return self._page

    def new_page(self) -> Page:
        """
        Create a new page in the current context.

        Returns:
            New Page instance
        """
        return self._context.new_page()

    def save_storage_state(self, path: str) -> None:
        """
        Save current storage state (cookies, localStorage) to file.

        Sets restrictive file permissions (owner read/write only) for security,
        as session files contain authentication tokens.

        Args:
            path: Path to save storage state JSON
        """
        self._context.storage_state(path=path)

        # Set restrictive permissions (owner read/write only)
        # This protects session tokens from other users on the system
        try:
            file_path = Path(path)
            if file_path.exists():
                # Unix: 0o600 (rw-------)
                # Windows: This is a no-op but doesn't error
                if os.name != 'nt':  # Unix-like systems
                    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
                    logger.debug(f"Set secure permissions (600) on {path}")
        except Exception as e:
            logger.warning(f"Could not set file permissions on {path}: {e}")

        logger.info(f"Saved storage state to {path}")

    def close(self) -> None:
        """Clean up all browser resources."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()

            logger.info(f"BROWSER SHUTDOWN | platform={self.platform}")
        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

    def __enter__(self) -> "BrowserManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit with cleanup."""
        self.close()
        return False

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass

    @classmethod
    def from_config(cls, config: Dict[str, Any], platform: str) -> "BrowserManager":
        """
        Create BrowserManager from a configuration dictionary.

        This factory method handles various config formats for backward compatibility.

        Args:
            config: Configuration dictionary
            platform: Platform name

        Returns:
            Configured BrowserManager instance

        Example:
            >>> config = {
            ...     "headless": False,
            ...     "browser_profile": "./profiles/instagram",
            ...     "session_file": "./sessions/instagram.json"
            ... }
            >>> manager = BrowserManager.from_config(config, "instagram")
        """
        # Extract browser config from various formats
        browser_config = config.get("browser", {})

        # Build BrowserConfig with fallbacks for different config styles
        browser_cfg = BrowserConfig(
            headless=browser_config.get("headless", config.get("headless", False)),
            profile_dir=(
                browser_config.get("profile_dir") or
                config.get("browser_profile")
            ),
            storage_state=config.get("session_file"),
            proxy=config.get("proxy"),
        )

        # Handle proxy list (use first one)
        proxies = config.get("proxies", [])
        if proxies and not browser_cfg.proxy:
            browser_cfg.proxy = random.choice(proxies)

        return cls(browser_cfg, platform)


class PooledBrowserManager(BrowserManager):
    """
    Browser manager that uses a shared browser pool for better performance.

    This manager reuses browser instances across multiple scraping sessions,
    reducing the overhead of repeatedly starting Playwright/Chromium.

    Note: Pooled managers only work with non-persistent contexts (no profile_dir).
    For persistent contexts, use the standard BrowserManager.

    Example:
        >>> config = BrowserConfig(headless=True)
        >>> with PooledBrowserManager(config, "instagram") as manager:
        ...     page = manager.page
        ...     page.goto("https://instagram.com")
    """

    def __init__(
        self,
        config: BrowserConfig,
        platform: str,
        pool: Optional[BrowserPool] = None
    ):
        """
        Initialize pooled browser manager.

        Args:
            config: Browser configuration
            platform: Platform name
            pool: Browser pool to use (uses global pool if None)
        """
        self.config = config
        self.platform = platform
        self._pool = pool or get_browser_pool()

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._from_pool = False

        self._initialize()

    def _initialize(self) -> None:
        """Initialize browser from pool or create new one."""
        # Pooling only works for non-persistent contexts
        if self.config.profile_dir:
            logger.debug(f"POOLED BROWSER | using standard init (has profile_dir)")
            super()._initialize()
            return

        logger.info(
            f"POOLED BROWSER INIT | platform={self.platform} | "
            f"headless={self.config.headless}"
        )

        try:
            self._browser, self._playwright = self._pool.acquire(
                self.platform,
                headless=self.config.headless,
                browser_args=self.config.browser_args,
                proxy=self.config.proxy
            )
            self._from_pool = True

            # Create context with optional storage state
            context_options = {
                "viewport": self.config.viewport,
                "user_agent": self.config.user_agent,
            }

            if self.config.storage_state and Path(self.config.storage_state).exists():
                context_options["storage_state"] = self.config.storage_state
                logger.debug(f"Loading storage state: {self.config.storage_state}")

            self._context = self._browser.new_context(**context_options)
            self._page = self._context.new_page()

            logger.info(f"POOLED BROWSER INIT | complete | platform={self.platform}")

        except Exception as e:
            logger.warning(f"Failed to get browser from pool: {e}, falling back to standard init")
            super()._initialize()

    def close(self) -> None:
        """Clean up resources and return browser to pool."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()

            # Return browser to pool if it came from there
            if self._from_pool and self._browser and self._playwright:
                self._pool.release(self.platform, self._browser, self._playwright)
                logger.debug(f"POOLED BROWSER | returned to pool | platform={self.platform}")
            else:
                # Standard cleanup
                if self._browser:
                    self._browser.close()
                if self._playwright:
                    self._playwright.stop()

            logger.info(f"POOLED BROWSER SHUTDOWN | platform={self.platform}")
        except Exception as e:
            logger.warning(f"Error during pooled browser cleanup: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None


def create_browser_manager(
    platform: str,
    headless: bool = False,
    profile_dir: Optional[str] = None,
    use_pool: bool = False,
    **kwargs
) -> BrowserManager:
    """
    Convenience function to create a BrowserManager.

    Args:
        platform: Platform name
        headless: Run in headless mode
        profile_dir: Directory for persistent profile
        use_pool: Use pooled browser manager for better performance
        **kwargs: Additional BrowserConfig options

    Returns:
        Configured BrowserManager instance

    Example:
        >>> manager = create_browser_manager(
        ...     "instagram",
        ...     headless=False,
        ...     profile_dir="./profiles/instagram"
        ... )

        >>> # Using pooled browser for better performance
        >>> manager = create_browser_manager(
        ...     "instagram",
        ...     headless=True,
        ...     use_pool=True
        ... )
    """
    config = BrowserConfig(
        headless=headless,
        profile_dir=profile_dir,
        **kwargs
    )

    if use_pool and not profile_dir:
        return PooledBrowserManager(config, platform)

    return BrowserManager(config, platform)
