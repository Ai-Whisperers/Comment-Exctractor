"""Browser factory for creating Playwright browser instances."""

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path

from playwright.sync_api import sync_playwright, Playwright, BrowserContext

from .constants import VIEWPORTS, USER_AGENTS, BROWSER_ARGS

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for browser creation."""
    profile_dir: str
    headless: bool = False
    viewport: Dict[str, int] = field(default_factory=lambda: VIEWPORTS.DEFAULT.copy())
    user_agent: Optional[str] = None
    browser_args: List[str] = field(default_factory=lambda: BROWSER_ARGS.copy())

    def __post_init__(self):
        if self.user_agent is None:
            self.user_agent = random.choice(USER_AGENTS)


class BrowserFactory:
    """Factory for creating and managing Playwright browser instances."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None

    def create_persistent_context(self, config: BrowserConfig) -> BrowserContext:
        """
        Create a persistent browser context.

        Args:
            config: Browser configuration

        Returns:
            Playwright BrowserContext
        """
        if not self._playwright:
            self._playwright = sync_playwright().start()

        # Ensure profile directory exists
        profile_path = Path(config.profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        context = self._playwright.chromium.launch_persistent_context(
            str(profile_path),
            headless=config.headless,
            viewport=config.viewport,
            user_agent=config.user_agent,
            args=config.browser_args,
        )

        logger.info(f"Created persistent browser context | profile={config.profile_dir}")
        return context

    def close(self) -> None:
        """Close the Playwright instance."""
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
            logger.debug("Browser factory closed")

    def __enter__(self) -> "BrowserFactory":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
