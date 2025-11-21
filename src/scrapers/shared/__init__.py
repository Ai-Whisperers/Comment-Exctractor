"""Shared scraper components."""

from .base_page import BasePage
from .browser_factory import BrowserFactory, BrowserConfig
from .constants import TIMEOUTS, USER_AGENTS, VIEWPORTS, ACCEPT_LANGUAGES

__all__ = [
    "BasePage",
    "BrowserFactory",
    "BrowserConfig",
    "TIMEOUTS",
    "USER_AGENTS",
    "VIEWPORTS",
    "ACCEPT_LANGUAGES",
]
