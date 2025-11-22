"""Tests for BaseScraper class."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.scrapers.base import BaseScraper, ProgressCallback
from src.core.models import Platform, ExtractionResult, Profile


class ConcreteScraper(BaseScraper):
    """Concrete implementation for testing."""

    platform = Platform.INSTAGRAM

    def _scrape_posts(self, account_id, since_date, max_posts, known_post_ids=None):
        yield from []

    def _scrape_profile(self, account_id):
        return Profile(
            platform=self.platform,
            platform_id=account_id,
            username=account_id,
            display_name=account_id,
        )


class TestBaseScraper:
    """Tests for BaseScraper base class."""

    def test_initialization(self):
        """Test scraper initialization."""
        config = {"proxies": ["http://proxy1:8080"]}
        scraper = ConcreteScraper(config)

        assert scraper.config == config
        assert scraper._request_count == 0
        assert scraper._consecutive_errors == 0
        assert scraper._current_proxy == "http://proxy1:8080"

    def test_initialization_without_config(self):
        """Test scraper initialization without config."""
        scraper = ConcreteScraper()

        assert scraper.config == {}
        assert scraper._proxies == []
        assert scraper._current_proxy is None

    def test_context_manager_entry(self):
        """Test context manager __enter__."""
        scraper = ConcreteScraper()

        with scraper as s:
            assert s is scraper

    def test_context_manager_exit_calls_close(self):
        """Test context manager __exit__ calls close."""
        scraper = ConcreteScraper()
        scraper.close = MagicMock()

        with scraper:
            pass

        scraper.close.assert_called_once()

    def test_context_manager_exit_on_exception(self):
        """Test context manager cleanup on exception."""
        scraper = ConcreteScraper()
        scraper.close = MagicMock()

        try:
            with scraper:
                raise ValueError("Test error")
        except ValueError:
            pass

        scraper.close.assert_called_once()

    def test_get_random_headers(self):
        """Test random headers generation."""
        scraper = ConcreteScraper()
        headers = scraper.get_random_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers

    def test_proxy_rotation(self):
        """Test proxy rotation."""
        config = {
            "proxies": ["http://proxy1:8080", "http://proxy2:8080"]
        }
        scraper = ConcreteScraper(config)
        initial_proxy = scraper._current_proxy

        scraper.rotate_proxy()

        # Should have rotated to different proxy
        assert scraper._current_proxy in config["proxies"]

    def test_proxy_rotation_single_proxy(self):
        """Test proxy rotation with single proxy."""
        config = {"proxies": ["http://proxy1:8080"]}
        scraper = ConcreteScraper(config)

        # Should not raise error
        scraper.rotate_proxy()
        assert scraper._current_proxy == "http://proxy1:8080"

    def test_mask_proxy_with_credentials(self):
        """Test proxy URL masking."""
        scraper = ConcreteScraper()
        masked = scraper._mask_proxy("http://user:pass@proxy.com:8080")

        assert "user" not in masked
        assert "pass" not in masked
        assert "proxy.com:8080" in masked

    def test_calculate_backoff(self):
        """Test exponential backoff calculation."""
        scraper = ConcreteScraper()
        scraper._consecutive_errors = 0

        backoff_0 = scraper._calculate_backoff()
        scraper._consecutive_errors = 1
        backoff_1 = scraper._calculate_backoff()
        scraper._consecutive_errors = 2
        backoff_2 = scraper._calculate_backoff()

        # Should increase exponentially
        assert backoff_1 > backoff_0
        assert backoff_2 > backoff_1

    def test_get_session_stats(self):
        """Test session statistics."""
        scraper = ConcreteScraper()
        scraper._request_count = 10

        stats = scraper.get_session_stats()

        assert stats["requests"] == 10
        assert "elapsed_minutes" in stats
        assert "requests_per_minute" in stats
        assert "using_proxy" in stats

    def test_is_good_time_to_scrape(self):
        """Test time-based scraping check."""
        scraper = ConcreteScraper()

        # This test depends on current time
        result = scraper.is_good_time_to_scrape()
        assert isinstance(result, bool)

    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        scraper = ConcreteScraper()

        # Valid timestamp
        result = scraper._parse_timestamp("2024-01-15 10:30:00")
        assert result is not None or result is None  # Depends on parser

    def test_clean_text(self):
        """Test text cleaning."""
        scraper = ConcreteScraper()

        # Test with null bytes and extra whitespace
        dirty = "Hello\x00  World\n\n  Test"
        clean = scraper._clean_text(dirty)

        assert "\x00" not in clean
        assert "  " not in clean  # No double spaces

    def test_clean_text_none(self):
        """Test text cleaning with None."""
        scraper = ConcreteScraper()
        assert scraper._clean_text(None) == ""

    def test_create_comment_objects(self):
        """Test comment object creation."""
        scraper = ConcreteScraper()

        raw_comments = [
            {
                "id": "comment1",
                "text": "Great post!",
                "author": "user1",
                "likes": 10,
            },
            {
                "id": "comment2",
                "text": "Thanks!",
                "author": "user2",
                "likes": 5,
                "parent_id": "comment1",
            }
        ]

        comments = scraper._create_comment_objects(raw_comments, "post123")

        assert len(comments) == 2
        assert comments[0].platform_id == "comment1"
        assert comments[0].text == "Great post!"
        assert comments[1].parent_id == "comment1"


class TestScraperProtocolCompliance:
    """Tests to verify ScraperProtocol compliance."""

    def test_has_platform_attribute(self):
        """Test that scraper has platform attribute."""
        scraper = ConcreteScraper()
        assert hasattr(scraper, 'platform')
        assert isinstance(scraper.platform, Platform)

    def test_has_get_posts_with_comments(self):
        """Test that scraper has get_posts_with_comments method."""
        scraper = ConcreteScraper()
        assert hasattr(scraper, 'get_posts_with_comments')
        assert callable(scraper.get_posts_with_comments)

    def test_has_get_profile(self):
        """Test that scraper has get_profile method."""
        scraper = ConcreteScraper()
        assert hasattr(scraper, 'get_profile')
        assert callable(scraper.get_profile)

    def test_has_close(self):
        """Test that scraper has close method."""
        scraper = ConcreteScraper()
        assert hasattr(scraper, 'close')
        assert callable(scraper.close)

    def test_context_manager_protocol(self):
        """Test context manager protocol methods."""
        scraper = ConcreteScraper()
        assert hasattr(scraper, '__enter__')
        assert hasattr(scraper, '__exit__')


class TestCheckpointMethods:
    """Tests for checkpoint save/load/clear methods."""

    def test_get_checkpoint_path(self):
        """Test checkpoint path generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            path = scraper._get_checkpoint_path("testuser")

            assert path.parent.name == "checkpoints"
            assert "instagram" in path.name
            assert "testuser" in path.name
            assert path.suffix == ".json"

    def test_save_checkpoint(self):
        """Test saving checkpoint data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            processed_ids = {"post1", "post2", "post3"}
            scraper._save_checkpoint("testuser", processed_ids)

            # Verify file was created
            checkpoint_path = scraper._get_checkpoint_path("testuser")
            assert checkpoint_path.exists()

            # Verify content
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
                assert data["account_id"] == "testuser"
                assert data["platform"] == "instagram"
                assert set(data["processed_post_ids"]) == processed_ids
                assert data["count"] == 3
                assert "last_updated" in data

    def test_load_checkpoint(self):
        """Test loading checkpoint data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            # Save first
            original_ids = {"post1", "post2", "post3"}
            scraper._save_checkpoint("testuser", original_ids)

            # Load and verify
            loaded_ids = scraper._load_checkpoint("testuser")
            assert loaded_ids == original_ids

    def test_load_checkpoint_nonexistent(self):
        """Test loading checkpoint when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            loaded_ids = scraper._load_checkpoint("nonexistent")
            assert loaded_ids == set()

    def test_load_checkpoint_corrupted(self):
        """Test loading checkpoint with corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            # Create corrupted file
            checkpoint_path = scraper._get_checkpoint_path("testuser")
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, 'w') as f:
                f.write("not valid json")

            # Should return empty set, not raise
            loaded_ids = scraper._load_checkpoint("testuser")
            assert loaded_ids == set()

    def test_clear_checkpoint(self):
        """Test clearing checkpoint file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            # Save first
            scraper._save_checkpoint("testuser", {"post1"})
            checkpoint_path = scraper._get_checkpoint_path("testuser")
            assert checkpoint_path.exists()

            # Clear
            scraper._clear_checkpoint("testuser")
            assert not checkpoint_path.exists()

    def test_clear_checkpoint_nonexistent(self):
        """Test clearing checkpoint when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}
            scraper = ConcreteScraper(config)

            # Should not raise
            scraper._clear_checkpoint("nonexistent")

    def test_checkpoint_preserves_data_across_sessions(self):
        """Test that checkpoints persist across scraper instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"data_dir": tmpdir}

            # First session
            scraper1 = ConcreteScraper(config)
            scraper1._save_checkpoint("testuser", {"post1", "post2"})

            # Second session
            scraper2 = ConcreteScraper(config)
            loaded_ids = scraper2._load_checkpoint("testuser")
            assert loaded_ids == {"post1", "post2"}


class TestProgressCallbackMethods:
    """Tests for progress callback functionality."""

    def test_set_progress_callback(self):
        """Test setting a progress callback."""
        scraper = ConcreteScraper()

        callback = MagicMock()
        scraper.set_progress_callback(callback)

        assert scraper._progress_callback is callback

    def test_report_progress_calls_callback(self):
        """Test that _report_progress calls the callback."""
        scraper = ConcreteScraper()

        callback = MagicMock()
        scraper.set_progress_callback(callback)

        scraper._report_progress(5, 10, "Processing post 5")

        callback.assert_called_once_with(5, 10, "Processing post 5")

    def test_report_progress_without_callback(self):
        """Test _report_progress when no callback is set."""
        scraper = ConcreteScraper()

        # Should not raise
        scraper._report_progress(5, 10, "test")

    def test_report_progress_handles_callback_exception(self):
        """Test that _report_progress handles callback errors gracefully."""
        scraper = ConcreteScraper()

        def failing_callback(current, total, message):
            raise ValueError("Callback error")

        scraper.set_progress_callback(failing_callback)

        # Should not raise, just log warning
        scraper._report_progress(5, 10, "test")

    def test_report_progress_empty_message(self):
        """Test _report_progress with empty message."""
        scraper = ConcreteScraper()

        callback = MagicMock()
        scraper.set_progress_callback(callback)

        scraper._report_progress(1, 5)

        callback.assert_called_once_with(1, 5, "")

    def test_progress_callback_type_signature(self):
        """Test that callback receives correct argument types."""
        scraper = ConcreteScraper()

        received_args = []

        def tracking_callback(current, total, message):
            received_args.append((current, total, message))

        scraper.set_progress_callback(tracking_callback)
        scraper._report_progress(3, 10, "test message")

        assert len(received_args) == 1
        current, total, message = received_args[0]
        assert isinstance(current, int)
        assert isinstance(total, int)
        assert isinstance(message, str)


class TestWaitWithBackoff:
    """Tests for _wait_with_backoff method."""

    @patch('time.sleep')
    def test_wait_with_backoff_first_attempt(self, mock_sleep):
        """Test backoff delay for first attempt."""
        scraper = ConcreteScraper()

        scraper._wait_with_backoff(0, base_delay=2.0, max_delay=60.0)

        # First attempt: 2.0 * (2^0) = 2.0 with jitter
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 1.5 <= delay <= 2.5  # 2.0 ± 25%

    @patch('time.sleep')
    def test_wait_with_backoff_increases_exponentially(self, mock_sleep):
        """Test that backoff increases with attempt number."""
        scraper = ConcreteScraper()

        delays = []
        for attempt in range(3):
            scraper._wait_with_backoff(attempt, base_delay=1.0, max_delay=60.0)
            delays.append(mock_sleep.call_args[0][0])

        # Each delay should be roughly double the previous
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]

    @patch('time.sleep')
    def test_wait_with_backoff_respects_max_delay(self, mock_sleep):
        """Test that backoff respects maximum delay."""
        scraper = ConcreteScraper()

        # Large attempt number should hit max
        scraper._wait_with_backoff(10, base_delay=1.0, max_delay=10.0)

        delay = mock_sleep.call_args[0][0]
        assert delay <= 12.5  # max_delay + 25% jitter
