"""Integration tests for Instagram scraper with mocked browser responses."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from src.scrapers.instagram.scraper import InstagramScraper
from src.scrapers.instagram.selectors import Selectors
from src.core.models import Platform, Post, Comment, Profile, ExtractionResult
from src.storage.base import StorageFactory


class MockElement:
    """Mock Playwright element for testing."""

    def __init__(self, text="", inner_html="", attributes=None):
        self._text = text
        self._inner_html = inner_html
        self._attributes = attributes or {}

    def inner_text(self):
        return self._text

    def inner_html(self):
        return self._inner_html

    def get_attribute(self, name):
        return self._attributes.get(name)

    def click(self):
        pass

    def is_visible(self):
        return True


class MockLocator:
    """Mock Playwright locator for testing."""

    def __init__(self, elements=None):
        self._elements = elements or []
        self._count = len(self._elements)

    def count(self):
        return self._count

    def all(self):
        return self._elements

    def first(self):
        return self._elements[0] if self._elements else None

    def nth(self, index):
        return self._elements[index] if index < len(self._elements) else None

    def click(self):
        pass

    def fill(self, value):
        pass

    def is_visible(self):
        return bool(self._elements)

    def wait_for(self, **kwargs):
        pass


@pytest.fixture
def mock_instagram_html():
    """Sample Instagram HTML responses for testing."""
    return {
        "profile_page": """
            <main>
                <header>
                    <section>
                        <h2>test_user</h2>
                    </section>
                    <section>
                        <ul>
                            <li><span>150</span> posts</li>
                            <li><span>10,500</span> followers</li>
                            <li><span>500</span> following</li>
                        </ul>
                    </section>
                </header>
            </main>
        """,
        "post_page": """
            <article>
                <div data-testid="post-content">
                    <span>This is a test post caption #testing</span>
                </div>
                <section>
                    <span>1,234 likes</span>
                </section>
                <time datetime="2024-01-15T10:30:00.000Z">January 15, 2024</time>
            </article>
        """,
        "comments_section": """
            <div data-testid="comments">
                <ul>
                    <li>
                        <a href="/commenter1/">commenter1</a>
                        <span>Great post!</span>
                        <time datetime="2024-01-15T11:00:00.000Z"></time>
                    </li>
                    <li>
                        <a href="/commenter2/">commenter2</a>
                        <span>Love this!</span>
                        <time datetime="2024-01-15T12:00:00.000Z"></time>
                    </li>
                </ul>
            </div>
        """
    }


@pytest.fixture
def mock_browser_manager():
    """Create a mock BrowserManager for testing."""
    manager = MagicMock()
    page = MagicMock()

    # Setup page mock
    page.url = "https://www.instagram.com/"
    page.content = MagicMock(return_value="<html></html>")
    page.goto = MagicMock(return_value=None)
    page.wait_for_timeout = MagicMock()
    page.wait_for_selector = MagicMock()
    page.query_selector = MagicMock(return_value=None)
    page.query_selector_all = MagicMock(return_value=[])
    page.evaluate = MagicMock(return_value=None)
    page.locator = MagicMock(return_value=MockLocator())
    page.keyboard = MagicMock()
    page.mouse = MagicMock()

    manager.page = page
    manager.context = MagicMock()
    manager.close = MagicMock()

    return manager


class TestInstagramScraperInitialization:
    """Tests for InstagramScraper initialization."""

    def test_scraper_has_correct_platform(self):
        """Test that scraper has Instagram platform."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = MagicMock()
            scraper = InstagramScraper({})
            assert scraper.platform == Platform.INSTAGRAM
            scraper.close()

    def test_scraper_initializes_page_objects(self):
        """Test that scraper initializes page objects."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_manager = MagicMock()
            mock_manager.page = MagicMock()
            mock_bm.from_config.return_value = mock_manager

            scraper = InstagramScraper({})

            assert scraper._login_page is not None
            assert scraper._profile_page is not None
            assert scraper._post_modal is not None
            assert scraper._comments_section is not None
            scraper.close()

    def test_scraper_uses_config_values(self):
        """Test that scraper uses configuration values."""
        config = {
            "max_posts": 50,
            "max_comments_per_post": 200,
            "headless": True,
        }

        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = MagicMock()
            scraper = InstagramScraper(config)

            assert scraper.config == config
            scraper.close()


class TestInstagramScraperProfileExtraction:
    """Tests for profile extraction functionality."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    def test_scrape_profile_extracts_username(self, scraper_with_mock_browser):
        """Test profile extraction gets username."""
        # Setup mock profile page
        mock_profile = MagicMock()
        mock_profile.get_username.return_value = "test_user"
        mock_profile.get_display_name.return_value = "Test User"
        mock_profile.get_bio.return_value = "Test bio"
        mock_profile.get_followers_count.return_value = 10500
        mock_profile.get_following_count.return_value = 500
        mock_profile.get_posts_count.return_value = 150
        mock_profile.get_profile_image.return_value = "https://example.com/avatar.jpg"
        mock_profile.is_verified.return_value = False

        scraper_with_mock_browser._profile_page = mock_profile
        scraper_with_mock_browser._page.goto = MagicMock(return_value=True)

        # Mock _navigate_to_url to return True
        scraper_with_mock_browser._navigate_to_url = MagicMock(return_value=True)

        profile = scraper_with_mock_browser._scrape_profile("test_user")

        assert profile.username == "test_user"
        assert profile.display_name == "Test User"
        assert profile.followers_count == 10500
        assert profile.platform == Platform.INSTAGRAM


class TestInstagramScraperCommentExtraction:
    """Tests for comment extraction functionality."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    def test_create_comment_objects_from_raw(self, scraper_with_mock_browser):
        """Test converting raw comment data to Comment objects."""
        raw_comments = [
            {
                "id": "comment_1",
                "text": "Great post!",
                "author": "commenter1",
                "author_id": "user_1",
                "likes": 10,
                "timestamp": "2024-01-15T11:00:00.000Z",
            },
            {
                "id": "comment_2",
                "text": "Love this!",
                "author": "commenter2",
                "author_id": "user_2",
                "likes": 5,
                "timestamp": "2024-01-15T12:00:00.000Z",
                "parent_id": "comment_1",
            }
        ]

        comments = scraper_with_mock_browser._create_comment_objects(raw_comments, "post_123")

        assert len(comments) == 2
        assert comments[0].platform_id == "comment_1"
        assert comments[0].text == "Great post!"
        assert comments[0].author.username == "commenter1"
        assert comments[1].parent_id == "comment_1"


class TestInstagramScraperRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    def test_rate_limit_detection(self, scraper_with_mock_browser):
        """Test that rate limiting is properly detected."""
        # Mock page content with rate limit indicators
        scraper_with_mock_browser._page.content.return_value = """
            <html>
                <body>
                    <div>Action Blocked</div>
                </body>
            </html>
        """
        scraper_with_mock_browser._page.url = "https://www.instagram.com/challenge/"

        is_limited = scraper_with_mock_browser._check_rate_limit()

        assert is_limited is True

    def test_no_rate_limit_on_normal_page(self, scraper_with_mock_browser):
        """Test that normal pages don't trigger rate limit."""
        scraper_with_mock_browser._page.content.return_value = """
            <html>
                <body>
                    <main>Normal Instagram content</main>
                </body>
            </html>
        """
        scraper_with_mock_browser._page.url = "https://www.instagram.com/test_user/"

        is_limited = scraper_with_mock_browser._check_rate_limit()

        assert is_limited is False


class TestInstagramScraperNavigationRetry:
    """Tests for navigation with retry logic."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    @patch('time.sleep')
    def test_navigate_retries_on_failure(self, mock_sleep, scraper_with_mock_browser):
        """Test that navigation retries on failure."""
        # First two calls fail, third succeeds
        scraper_with_mock_browser._page.goto.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            None,
        ]
        scraper_with_mock_browser._page.content.return_value = "<html></html>"
        scraper_with_mock_browser._page.url = "https://www.instagram.com/test/"
        scraper_with_mock_browser._check_rate_limit = MagicMock(return_value=False)

        result = scraper_with_mock_browser._navigate_to_url(
            "https://www.instagram.com/test/",
            max_retries=3
        )

        assert result is True
        assert scraper_with_mock_browser._page.goto.call_count == 3

    @patch('time.sleep')
    def test_navigate_fails_after_max_retries(self, mock_sleep, scraper_with_mock_browser):
        """Test that navigation fails after max retries."""
        scraper_with_mock_browser._page.goto.side_effect = Exception("Network error")

        result = scraper_with_mock_browser._navigate_to_url(
            "https://www.instagram.com/test/",
            max_retries=3
        )

        assert result is False
        assert scraper_with_mock_browser._page.goto.call_count == 3


class TestInstagramScraperCheckpointIntegration:
    """Tests for checkpoint functionality in scraping workflow."""

    @pytest.fixture
    def scraper_with_temp_dir(self, mock_browser_manager):
        """Create scraper with temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
                mock_bm.from_config.return_value = mock_browser_manager
                scraper = InstagramScraper(config)
                scraper._browser_manager = mock_browser_manager
                scraper._page = mock_browser_manager.page
                yield scraper, tmpdir
                scraper.close()

    def test_checkpoint_saves_progress(self, scraper_with_temp_dir):
        """Test that checkpoints save extraction progress."""
        scraper, tmpdir = scraper_with_temp_dir

        # Simulate processing posts
        processed_ids = {"post_1", "post_2", "post_3"}
        scraper._save_checkpoint("test_user", processed_ids)

        # Verify checkpoint file exists
        checkpoint_path = scraper._get_checkpoint_path("test_user")
        assert checkpoint_path.exists()

        # Verify content
        with open(checkpoint_path) as f:
            data = json.load(f)
            assert set(data["processed_post_ids"]) == processed_ids

    def test_checkpoint_resumes_extraction(self, scraper_with_temp_dir):
        """Test that extraction resumes from checkpoint."""
        scraper, tmpdir = scraper_with_temp_dir

        # Save initial checkpoint
        initial_ids = {"post_1", "post_2"}
        scraper._save_checkpoint("test_user", initial_ids)

        # Load checkpoint
        loaded_ids = scraper._load_checkpoint("test_user")

        assert loaded_ids == initial_ids


class TestInstagramScraperStorageIntegration:
    """Tests for storage integration in extraction workflow."""

    def test_extraction_result_can_be_saved(self, sample_post, sample_comments):
        """Test that extraction results can be saved to storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageFactory.create("json", tmpdir)

            # Save extraction result
            results = storage.save_extraction_result(
                posts=[sample_post],
                comments=sample_comments,
                profile=None,
                account="test_account",
                platform="instagram"
            )

            assert "posts" in results
            assert "comments" in results
            assert Path(results["posts"]).exists()
            assert Path(results["comments"]).exists()

    def test_full_extraction_workflow_saves_all_data(self, sample_post, sample_comments, sample_profile):
        """Test complete extraction workflow with all data types."""
        # Use JSON storage to avoid SQLite file lock issues on Windows
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageFactory.create("json", tmpdir)

            # Save complete extraction
            results = storage.save_extraction_result(
                posts=[sample_post],
                comments=sample_comments,
                profile=sample_profile,
                account="test_account",
                platform="instagram"
            )

            assert "posts" in results
            assert "comments" in results
            assert "profile" in results
            # Verify files were created
            assert Path(results["posts"]).exists()
            assert Path(results["comments"]).exists()
            assert Path(results["profile"]).exists()


class TestInstagramScraperProgressCallback:
    """Tests for progress callback integration."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    def test_progress_callback_receives_updates(self, scraper_with_mock_browser):
        """Test that progress callback receives updates during extraction."""
        progress_updates = []

        def track_progress(current, total, message):
            progress_updates.append((current, total, message))

        scraper_with_mock_browser.set_progress_callback(track_progress)

        # Simulate progress updates
        scraper_with_mock_browser._report_progress(1, 10, "Processing post 1")
        scraper_with_mock_browser._report_progress(2, 10, "Processing post 2")

        assert len(progress_updates) == 2
        assert progress_updates[0] == (1, 10, "Processing post 1")
        assert progress_updates[1] == (2, 10, "Processing post 2")


class TestInstagramScraperContextManager:
    """Tests for context manager behavior."""

    def test_context_manager_closes_browser(self):
        """Test that context manager properly closes browser."""
        mock_browser_manager = MagicMock()
        mock_browser_manager.page = MagicMock()

        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager

            with InstagramScraper({}) as scraper:
                # Store reference to browser manager
                browser_mgr = scraper._browser_manager

            # Verify close was called on the browser manager
            browser_mgr.close.assert_called()

    def test_context_manager_closes_on_exception(self):
        """Test that context manager closes browser even on exception."""
        mock_browser_manager = MagicMock()
        mock_browser_manager.page = MagicMock()

        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager

            try:
                with InstagramScraper({}) as scraper:
                    browser_mgr = scraper._browser_manager
                    raise ValueError("Test error")
            except ValueError:
                pass

            browser_mgr.close.assert_called()


class TestInstagramScraperErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def scraper_with_mock_browser(self, mock_browser_manager):
        """Create scraper with mocked browser."""
        with patch('src.scrapers.instagram.scraper.BrowserManager') as mock_bm:
            mock_bm.from_config.return_value = mock_browser_manager
            scraper = InstagramScraper({})
            scraper._browser_manager = mock_browser_manager
            scraper._page = mock_browser_manager.page
            yield scraper
            scraper.close()

    def test_handles_missing_profile_gracefully(self, scraper_with_mock_browser):
        """Test handling of profile not found."""
        # Setup mock to return empty results
        mock_profile = MagicMock()
        mock_profile.get_username.return_value = None
        mock_profile.get_display_name.return_value = None
        mock_profile.get_bio.return_value = None
        mock_profile.get_followers_count.return_value = 0
        mock_profile.get_following_count.return_value = 0
        mock_profile.get_posts_count.return_value = 0
        mock_profile.get_profile_image.return_value = None
        mock_profile.is_verified.return_value = False

        scraper_with_mock_browser._profile_page = mock_profile
        scraper_with_mock_browser._navigate_to_url = MagicMock(return_value=True)

        profile = scraper_with_mock_browser._scrape_profile("nonexistent_user")

        # Should return profile with empty/default values, not raise
        assert profile is not None
        assert profile.platform == Platform.INSTAGRAM

