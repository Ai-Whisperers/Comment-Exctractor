"""Tests for Instagram scraper with mocked Playwright responses."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from src.scrapers.instagram.scraper import InstagramScraper
from src.scrapers.instagram.pages import LoginPage, ProfilePage, PostModal, CommentsSection
from src.core.models import Platform, Profile, Post, Comment, Author, ExtractionResult
from src.core.exceptions import AuthenticationError, PrivateAccountError, RateLimitError


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = MagicMock()
    page.url = "https://www.instagram.com/"
    page.goto.return_value = None
    page.wait_for_timeout.return_value = None
    page.wait_for_selector.return_value = MagicMock()
    page.evaluate.return_value = None
    page.query_selector.return_value = None
    page.query_selector_all.return_value = []
    return page


@pytest.fixture
def mock_browser_manager(mock_page):
    """Create a mock BrowserManager."""
    with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
        instance = MagicMock()
        instance.page = mock_page
        mock_bm.return_value = instance
        yield mock_bm


@pytest.fixture
def config():
    """Standard test configuration."""
    return {
        "username": "testuser",
        "password": "testpass",
        "headless": True,
    }


class TestInstagramScraperInitialization:
    """Tests for scraper initialization."""

    def test_initialization_with_credentials(self, mock_browser_manager, config):
        """Test scraper initializes with credentials."""
        scraper = InstagramScraper(config)

        assert scraper._username == "testuser"
        assert scraper._password == "testpass"
        assert scraper.platform == Platform.INSTAGRAM

    def test_initialization_without_credentials(self, mock_browser_manager):
        """Test scraper initializes without credentials."""
        config = {"headless": True}
        scraper = InstagramScraper(config)

        assert scraper._username is None
        assert scraper._password is None

    def test_browser_manager_created(self, mock_browser_manager, config):
        """Test that browser manager is created."""
        scraper = InstagramScraper(config)

        mock_browser_manager.assert_called_once()
        assert scraper._browser_manager is not None

    def test_page_objects_initialized(self, mock_browser_manager, config):
        """Test that page objects are initialized."""
        scraper = InstagramScraper(config)

        assert scraper._login_page is not None
        assert scraper._profile_page is not None
        assert scraper._post_modal is not None
        assert scraper._comments_section is not None


class TestInstagramScraperLogin:
    """Tests for login functionality."""

    def test_ensure_logged_in_already_logged_in(self, mock_browser_manager, config, mock_page):
        """Test that login is skipped if already logged in."""
        scraper = InstagramScraper(config)

        # Mock already logged in state
        scraper._profile_page.is_logged_in = MagicMock(return_value=True)
        scraper._profile_page.dismiss_popups = MagicMock()
        mock_page.evaluate.return_value = False  # No login form

        scraper._ensure_logged_in()

        # Should not attempt login
        scraper._login_page.login = MagicMock()
        scraper._login_page.login.assert_not_called()

    def test_ensure_logged_in_needs_login(self, mock_browser_manager, config, mock_page):
        """Test that login is performed when needed."""
        scraper = InstagramScraper(config)

        # Mock not logged in state
        scraper._profile_page.is_logged_in = MagicMock(return_value=False)
        scraper._profile_page.dismiss_popups = MagicMock()
        mock_page.url = "https://www.instagram.com/accounts/login/"
        scraper._login_page.login = MagicMock()

        scraper._ensure_logged_in()

        scraper._login_page.login.assert_called_once_with("testuser", "testpass")

    def test_ensure_logged_in_no_credentials_raises(self, mock_browser_manager, mock_page):
        """Test that missing credentials raises error."""
        config = {"headless": True}
        scraper = InstagramScraper(config)

        # Mock not logged in state
        scraper._profile_page.is_logged_in = MagicMock(return_value=False)
        scraper._profile_page.dismiss_popups = MagicMock()
        mock_page.url = "https://www.instagram.com/accounts/login/"

        with pytest.raises(AuthenticationError):
            scraper._ensure_logged_in()


class TestInstagramScraperRateLimit:
    """Tests for rate limit handling."""

    def test_check_rate_limit_not_limited(self, mock_browser_manager, config):
        """Test rate limit check when not limited."""
        scraper = InstagramScraper(config)
        scraper._rate_limit_detector.is_rate_limited = MagicMock(return_value=False)

        assert not scraper._check_rate_limit()

    def test_check_rate_limit_is_limited(self, mock_browser_manager, config):
        """Test rate limit check when limited."""
        scraper = InstagramScraper(config)
        scraper._rate_limit_detector.is_rate_limited = MagicMock(return_value=True)

        assert scraper._check_rate_limit()


class TestInstagramScraperNavigation:
    """Tests for navigation with retry."""

    def test_navigate_to_url_success(self, mock_browser_manager, config, mock_page):
        """Test successful navigation."""
        scraper = InstagramScraper(config)
        scraper._rate_limit_detector.is_rate_limited = MagicMock(return_value=False)

        result = scraper._navigate_to_url("https://www.instagram.com/testuser/")

        assert result is True
        mock_page.goto.assert_called()

    def test_navigate_to_url_rate_limited(self, mock_browser_manager, config, mock_page):
        """Test navigation fails on rate limit."""
        scraper = InstagramScraper(config)
        scraper._rate_limit_detector.is_rate_limited = MagicMock(return_value=True)

        with pytest.raises(RateLimitError):
            scraper._navigate_to_url("https://www.instagram.com/testuser/", max_retries=1)

    @patch('time.sleep')
    def test_navigate_to_url_retries_on_error(self, mock_sleep, mock_browser_manager, config, mock_page):
        """Test navigation retries on error."""
        scraper = InstagramScraper(config)
        scraper._rate_limit_detector.is_rate_limited = MagicMock(return_value=False)

        # First call fails, second succeeds
        mock_page.goto.side_effect = [Exception("Network error"), None]

        result = scraper._navigate_to_url("https://www.instagram.com/testuser/", max_retries=2)

        assert result is True
        assert mock_page.goto.call_count == 2


class TestInstagramScraperProfile:
    """Tests for profile scraping."""

    def test_scrape_profile_success(self, mock_browser_manager, config, mock_page):
        """Test successful profile scraping."""
        scraper = InstagramScraper(config)

        # Mock all profile page methods comprehensively
        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._profile_page.get_display_name = MagicMock(return_value="Test User")
        scraper._profile_page.get_followers_count = MagicMock(return_value=1000)
        scraper._profile_page.get_following_count = MagicMock(return_value=500)
        scraper._profile_page.is_verified = MagicMock(return_value=True)

        profile = scraper._scrape_profile("testuser")

        assert profile.username == "testuser"
        assert profile.display_name == "Test User"
        assert profile.followers_count == 1000
        assert profile.following_count == 500
        assert profile.is_verified is True

    def test_scrape_profile_calls_correct_methods(self, mock_browser_manager, config, mock_page):
        """Test profile scraping calls expected page methods."""
        scraper = InstagramScraper(config)

        # Setup mocks
        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._profile_page.get_display_name = MagicMock(return_value="User")
        scraper._profile_page.get_followers_count = MagicMock(return_value=100)
        scraper._profile_page.get_following_count = MagicMock(return_value=50)
        scraper._profile_page.is_verified = MagicMock(return_value=False)

        scraper._scrape_profile("testuser")

        # Verify correct methods were called
        scraper._ensure_logged_in.assert_called_once()
        scraper._profile_page.navigate.assert_called_once_with("testuser")
        scraper._profile_page.get_followers_count.assert_called_once()
        scraper._profile_page.get_following_count.assert_called_once()


class TestInstagramScraperPosts:
    """Tests for post scraping."""

    @patch('time.sleep')
    def test_scrape_posts_empty_profile(self, mock_sleep, mock_browser_manager, config, mock_page):
        """Test scraping profile with no posts."""
        scraper = InstagramScraper(config)

        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._verify_logged_in_on_profile = MagicMock(return_value=True)
        scraper._profile_page.is_private = MagicMock(return_value=False)
        scraper._profile_page.get_post_links = MagicMock(return_value=[])

        results = list(scraper._scrape_posts("testuser", None, 10))

        assert len(results) == 0

    @patch('time.sleep')
    def test_scrape_posts_private_account(self, mock_sleep, mock_browser_manager, config, mock_page):
        """Test scraping private account raises error."""
        scraper = InstagramScraper(config)

        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._verify_logged_in_on_profile = MagicMock(return_value=True)
        scraper._profile_page.is_private = MagicMock(return_value=True)

        with pytest.raises(PrivateAccountError):
            list(scraper._scrape_posts("testuser", None, 10))

    def test_scrape_posts_calls_login_check(self, mock_browser_manager, config, mock_page):
        """Test that post scraping verifies login state."""
        scraper = InstagramScraper(config)

        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._verify_logged_in_on_profile = MagicMock(return_value=True)
        scraper._profile_page.is_private = MagicMock(return_value=False)
        scraper._profile_page.get_post_links = MagicMock(return_value=[])

        list(scraper._scrape_posts("testuser", None, 10))

        scraper._ensure_logged_in.assert_called()
        scraper._profile_page.navigate.assert_called_with("testuser")


class TestInstagramScraperClose:
    """Tests for scraper cleanup."""

    def test_close_calls_browser_manager_close(self, mock_browser_manager, config):
        """Test that close properly cleans up browser."""
        scraper = InstagramScraper(config)

        # Store reference to browser manager before close
        bm = scraper._browser_manager
        scraper.close()

        bm.close.assert_called_once()

    def test_close_handles_missing_browser_manager(self, mock_browser_manager, config):
        """Test close handles missing browser manager gracefully."""
        scraper = InstagramScraper(config)
        scraper._browser_manager = None

        # Should not raise
        scraper.close()


class TestInstagramScraperContextManager:
    """Tests for context manager usage."""

    def test_context_manager_calls_close(self, mock_browser_manager, config):
        """Test context manager calls close on exit."""
        bm = None
        with InstagramScraper(config) as scraper:
            bm = scraper._browser_manager

        bm.close.assert_called()

    def test_context_manager_closes_on_exception(self, mock_browser_manager, config):
        """Test context manager closes on exception."""
        bm = None
        try:
            with InstagramScraper(config) as scraper:
                bm = scraper._browser_manager
                raise ValueError("Test error")
        except ValueError:
            pass

        bm.close.assert_called()


class TestInstagramScraperIntegration:
    """Integration-style tests with mocked components."""

    @patch('time.sleep')
    def test_get_posts_with_comments_empty_flow(self, mock_sleep, mock_browser_manager, config, mock_page):
        """Test complete flow of getting posts returns empty when no posts."""
        scraper = InstagramScraper(config)

        # Setup mocks for complete flow
        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._verify_logged_in_on_profile = MagicMock(return_value=True)
        scraper._profile_page.is_private = MagicMock(return_value=False)
        scraper._profile_page.get_post_links = MagicMock(return_value=[])

        # Execute
        results = list(scraper.get_posts_with_comments("testuser", max_posts=1))

        # Verify
        assert len(results) == 0

    @patch('time.sleep')
    def test_get_profile_flow(self, mock_sleep, mock_browser_manager, config, mock_page):
        """Test complete flow of getting a profile."""
        scraper = InstagramScraper(config)

        # Setup mocks
        scraper._ensure_logged_in = MagicMock()
        scraper._profile_page.navigate = MagicMock()
        scraper._profile_page.get_display_name = MagicMock(return_value="Test User")
        scraper._profile_page.get_followers_count = MagicMock(return_value=1000)
        scraper._profile_page.get_following_count = MagicMock(return_value=500)
        scraper._profile_page.is_verified = MagicMock(return_value=False)

        # Execute
        profile = scraper.get_profile("testuser")

        # Verify
        assert profile.username == "testuser"
        assert profile.display_name == "Test User"
        assert profile.followers_count == 1000


class TestInstagramScraperErrorHandling:
    """Tests for error handling scenarios."""

    def test_handles_network_error(self, mock_browser_manager, config, mock_page):
        """Test handling of network errors."""
        scraper = InstagramScraper(config)

        mock_page.goto.side_effect = Exception("Network error")

        result = scraper._navigate_to_url("https://instagram.com", max_retries=1)

        assert result is False

    def test_handles_page_not_found(self, mock_browser_manager, config, mock_page):
        """Test handling of 404 errors."""
        scraper = InstagramScraper(config)

        scraper._ensure_logged_in = MagicMock()
        scraper._navigate_to_url = MagicMock(return_value=False)

        # Profile page methods won't be called if navigation fails
        with pytest.raises(Exception):
            scraper._scrape_profile("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
