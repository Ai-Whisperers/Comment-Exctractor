"""Tests for BrowserManager and related components."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.scrapers.shared.browser_manager import (
    BrowserManager,
    BrowserConfig,
    create_browser_manager,
)
from src.scrapers.shared.constants import VIEWPORTS, BROWSER_ARGS


class TestBrowserConfig:
    """Tests for BrowserConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BrowserConfig()

        assert config.headless is False
        assert config.profile_dir is None
        assert config.viewport == VIEWPORTS.DEFAULT
        assert config.user_agent is not None  # Random user agent
        assert config.storage_state is None
        assert config.browser_args == BROWSER_ARGS
        assert config.proxy is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BrowserConfig(
            headless=True,
            profile_dir="/tmp/test_profile",
            proxy="http://proxy:8080"
        )

        assert config.headless is True
        assert config.profile_dir == "/tmp/test_profile"
        assert config.proxy == "http://proxy:8080"

    def test_user_agent_randomization(self):
        """Test that user agent is randomized if not provided."""
        config1 = BrowserConfig()
        config2 = BrowserConfig()

        # Both should have user agents
        assert config1.user_agent is not None
        assert config2.user_agent is not None

    def test_custom_user_agent(self):
        """Test setting custom user agent."""
        custom_ua = "Custom User Agent"
        config = BrowserConfig(user_agent=custom_ua)

        assert config.user_agent == custom_ua


class TestBrowserManager:
    """Tests for BrowserManager class."""

    @patch('src.scrapers.shared.browser_manager.sync_playwright')
    def test_initialization(self, mock_playwright):
        """Test BrowserManager initialization."""
        # Setup mocks
        mock_pw_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start.return_value = mock_pw_instance
        mock_pw_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        config = BrowserConfig(headless=True)
        manager = BrowserManager(config, "test")

        # Verify initialization
        assert manager.page == mock_page
        assert manager.context == mock_context
        assert manager.platform == "test"

    @patch('src.scrapers.shared.browser_manager.sync_playwright')
    def test_context_manager(self, mock_playwright):
        """Test context manager protocol."""
        mock_pw_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start.return_value = mock_pw_instance
        mock_pw_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        config = BrowserConfig(headless=True)

        with BrowserManager(config, "test") as manager:
            assert manager.page is not None

        # Verify cleanup was called
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()

    @patch('src.scrapers.shared.browser_manager.sync_playwright')
    def test_close_cleans_up_resources(self, mock_playwright):
        """Test that close() properly cleans up resources."""
        mock_pw_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start.return_value = mock_pw_instance
        mock_pw_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        config = BrowserConfig(headless=True)
        manager = BrowserManager(config, "test")
        manager.close()

        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()

    @patch('src.scrapers.shared.browser_manager.sync_playwright')
    def test_from_config_factory(self, mock_playwright):
        """Test from_config factory method."""
        mock_pw_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start.return_value = mock_pw_instance
        mock_pw_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        config = {
            "headless": True,
            "browser_profile": "/tmp/profile",
        }

        manager = BrowserManager.from_config(config, "instagram")

        assert manager is not None
        assert manager.platform == "instagram"

    def test_mask_proxy_with_credentials(self):
        """Test proxy masking with credentials."""
        proxy = "http://user:pass@proxy.com:8080"
        masked = BrowserManager._mask_proxy(proxy)

        assert "user" not in masked
        assert "pass" not in masked
        assert "proxy.com:8080" in masked

    def test_mask_proxy_without_credentials(self):
        """Test proxy masking without credentials."""
        proxy = "http://proxy.com:8080"
        masked = BrowserManager._mask_proxy(proxy)

        assert masked == proxy


class TestCreateBrowserManager:
    """Tests for create_browser_manager convenience function."""

    @patch('src.scrapers.shared.browser_manager.sync_playwright')
    def test_basic_creation(self, mock_playwright):
        """Test basic browser manager creation."""
        mock_pw_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.start.return_value = mock_pw_instance
        mock_pw_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        manager = create_browser_manager("test", headless=True)

        assert manager is not None
        assert manager.platform == "test"
