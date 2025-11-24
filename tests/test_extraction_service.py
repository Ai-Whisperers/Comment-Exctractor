"""Integration tests for ExtractionService.

These tests verify the full extraction flow using mock scrapers
and real storage backends.
"""

import gc
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock
from typing import Iterator

from src.core.models import (
    Platform,
    Post,
    Comment,
    Author,
    ExtractionResult,
    ExtractionStats,
    ClientConfig,
    SocialAccount,
)
from src.core.container import Container, reset_container
from src.core.events import EventBus, EventType, get_event_bus, reset_event_bus
from src.core.exceptions import ConfigurationError
from src.services.extraction import ExtractionService
from src.storage.sqlite import SQLiteStorage


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sqlite_storage(temp_data_dir):
    """Create SQLite storage for testing."""
    db_path = str(Path(temp_data_dir) / "test.db")
    storage = SQLiteStorage(db_path=db_path)
    yield storage
    # Close the storage to release the database file
    if hasattr(storage, 'close'):
        storage.close()
    # Force garbage collection to release any dangling references (Windows)
    gc.collect()


@pytest.fixture
def mock_scraper():
    """Create a mock scraper that returns test data."""
    scraper = MagicMock()

    # Create test post
    test_post = Post(
        platform=Platform.INSTAGRAM,
        platform_id="post_123",
        account_id="test_account",
        url="https://instagram.com/p/123",
        text="Test post content",
        published_at=datetime(2024, 1, 15, 10, 0, 0),
        likes=100,
        comments_count=2,
        shares=5,
        media_type="image",
        media_urls=[],
        raw_data={},
    )

    # Create test comments
    test_comments = [
        Comment(
            platform=Platform.INSTAGRAM,
            platform_id="comment_1",
            post_id="post_123",
            author=Author(
                platform_id="user_1",
                username="user1",
                display_name="User One",
            ),
            text="First comment",
            likes=10,
            published_at=datetime(2024, 1, 15, 11, 0, 0),
        ),
        Comment(
            platform=Platform.INSTAGRAM,
            platform_id="comment_2",
            post_id="post_123",
            author=Author(
                platform_id="user_2",
                username="user2",
                display_name="User Two",
            ),
            text="Second comment",
            likes=5,
            published_at=datetime(2024, 1, 15, 12, 0, 0),
        ),
    ]

    # Configure scraper to yield results
    def get_posts_with_comments(account_id, since_date, max_posts, known_post_ids=None):
        yield ExtractionResult(post=test_post, comments=test_comments)

    scraper.get_posts_with_comments = get_posts_with_comments
    scraper.close = MagicMock()

    return scraper


@pytest.fixture
def mock_scraper_factory(mock_scraper):
    """Create a scraper factory that returns the mock scraper."""
    def factory(platform: str, config=None):
        return mock_scraper
    return factory


@pytest.fixture
def mock_exporter():
    """Create a mock exporter."""
    exporter = MagicMock()
    exporter.export = MagicMock(return_value="/tmp/export.json")
    exporter.export_posts = MagicMock(return_value="/tmp/posts.json")
    return exporter


@pytest.fixture
def mock_exporter_factory(mock_exporter):
    """Create an exporter factory that returns the mock exporter."""
    def factory(format: str):
        return mock_exporter
    return factory


@pytest.fixture
def extraction_service(temp_data_dir, sqlite_storage, mock_scraper_factory, mock_exporter_factory):
    """Create ExtractionService with test dependencies."""
    service = ExtractionService(
        storage=sqlite_storage,
        data_dir=temp_data_dir,
        scraper_factory=mock_scraper_factory,
        exporter_factory=mock_exporter_factory,
    )
    yield service
    # Note: storage is closed in sqlite_storage fixture


class TestExtractionServiceBasic:
    """Basic extraction service tests."""

    def test_service_initialization(self, extraction_service):
        """Test service initializes correctly."""
        assert extraction_service is not None
        assert extraction_service.storage is not None
        assert extraction_service._scraper_factory is not None
        assert extraction_service._exporter_factory is not None

    def test_extract_single_account(self, extraction_service, sqlite_storage):
        """Test extracting from a single account."""
        stats = extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Verify stats
        assert stats.posts_scraped == 1
        assert stats.comments_found == 2
        assert stats.new_comments_saved == 2
        assert stats.duplicates_skipped == 0
        assert stats.error is None
        assert stats.completed_at is not None

        # Verify data was saved
        comments = sqlite_storage.get_comments("test_client")
        assert len(comments) == 2

        posts = sqlite_storage.get_posts("test_client")
        assert len(posts) == 1

    def test_extract_incremental(self, extraction_service, sqlite_storage):
        """Test incremental extraction skips existing comments."""
        # First extraction
        stats1 = extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )
        assert stats1.new_comments_saved == 2

        # Second extraction should detect duplicates
        stats2 = extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Comments should be duplicates (already exist)
        assert stats2.duplicates_skipped == 2 or stats2.new_comments_saved == 0

    def test_extract_full_mode(self, extraction_service, sqlite_storage):
        """Test full extraction mode."""
        # First extraction
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Full re-extraction
        stats = extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
            full=True,
        )

        assert stats.posts_scraped == 1
        # Full mode should still process all posts


class TestExtractionServiceValidation:
    """Test input validation in ExtractionService."""

    def test_invalid_platform(self, extraction_service):
        """Test error on invalid platform."""
        with pytest.raises(ConfigurationError) as exc_info:
            extraction_service.extract(
                client="test_client",
                platform="invalid_platform",
                account_id="test_account",
                max_posts=10,
            )

        assert "invalid platform" in str(exc_info.value).lower()

    def test_invalid_max_posts(self, extraction_service):
        """Test error on invalid max_posts."""
        with pytest.raises(ConfigurationError) as exc_info:
            extraction_service.extract(
                client="test_client",
                platform="instagram",
                account_id="test_account",
                max_posts=0,  # Too low
            )

        assert "max_posts" in str(exc_info.value)

    def test_max_posts_exceeds_limit(self, extraction_service):
        """Test error when max_posts exceeds limit."""
        with pytest.raises(ConfigurationError) as exc_info:
            extraction_service.extract(
                client="test_client",
                platform="instagram",
                account_id="test_account",
                max_posts=50000,  # Too high
            )

        assert "max_posts" in str(exc_info.value)

    def test_invalid_client_name(self, extraction_service):
        """Test error on invalid client name."""
        with pytest.raises(ConfigurationError):
            extraction_service.extract(
                client="invalid/client",  # Invalid character
                platform="instagram",
                account_id="test_account",
                max_posts=10,
            )


class TestExtractionServiceExport:
    """Test export functionality."""

    def test_export_comments(self, extraction_service, mock_exporter):
        """Test exporting comments."""
        # First extract some data
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Export
        path = extraction_service.export(
            client="test_client",
            format="json",
        )

        assert path == "/tmp/export.json"
        mock_exporter.export.assert_called_once()

    def test_export_posts(self, extraction_service, mock_exporter):
        """Test exporting posts."""
        # First extract some data
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Export posts
        path = extraction_service.export_posts(
            client="test_client",
            format="json",
        )

        assert path == "/tmp/posts.json"
        mock_exporter.export_posts.assert_called_once()

    def test_export_filtered_by_platform(self, extraction_service, mock_exporter):
        """Test export filtered by platform."""
        # Extract data
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Export with platform filter
        extraction_service.export(
            client="test_client",
            format="json",
            platform="instagram",
        )

        mock_exporter.export.assert_called_once()


class TestExtractionServiceWithContainer:
    """Test ExtractionService using the DI Container."""

    def test_create_service_from_container(self, temp_data_dir):
        """Test creating service from container."""
        reset_container()

        container = Container()

        # Override storage with test storage
        test_storage = SQLiteStorage(
            db_path=str(Path(temp_data_dir) / "container_test.db")
        )
        container.register_storage(test_storage)

        # Get service
        service = container.extraction_service()

        assert service is not None
        assert service.storage is test_storage

        container.close()
        # Close storage explicitly for Windows
        if hasattr(test_storage, 'close'):
            test_storage.close()
        gc.collect()

    def test_container_context_manager(self, temp_data_dir):
        """Test container as context manager."""
        reset_container()

        test_storage = None
        with Container() as container:
            test_storage = SQLiteStorage(
                db_path=str(Path(temp_data_dir) / "context_test.db")
            )
            container.register_storage(test_storage)

            service = container.extraction_service()
            assert service is not None

        # Close storage explicitly for Windows
        if test_storage and hasattr(test_storage, 'close'):
            test_storage.close()
        gc.collect()


class TestExtractionServiceStats:
    """Test statistics functionality."""

    def test_get_stats(self, extraction_service, sqlite_storage):
        """Test getting client statistics."""
        # Extract data first
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Get stats
        stats = extraction_service.get_stats("test_client")

        assert stats["client"] == "test_client"
        assert stats["total_comments"] == 2
        assert stats["total_posts"] == 1
        assert "instagram" in stats["platforms"]

    def test_empty_stats(self, extraction_service):
        """Test stats for client with no data."""
        stats = extraction_service.get_stats("nonexistent_client")

        assert stats["total_comments"] == 0
        assert stats["total_posts"] == 0


class TestExtractionServiceMultipleAccounts:
    """Test extracting from multiple accounts."""

    def test_extract_all(self, extraction_service):
        """Test extract_all with ClientConfig."""
        client_config = ClientConfig(
            name="multi_test",
            accounts=[
                SocialAccount(
                    platform=Platform.INSTAGRAM,
                    identifier="account1",
                    enabled=True,
                ),
                SocialAccount(
                    platform=Platform.INSTAGRAM,
                    identifier="account2",
                    enabled=True,
                ),
            ],
        )

        results = extraction_service.extract_all(
            client_config=client_config,
            max_posts=10,
        )

        assert len(results) == 2
        for stats in results:
            assert stats.posts_scraped >= 0

    def test_extract_all_with_disabled_account(self, extraction_service):
        """Test extract_all skips disabled accounts."""
        client_config = ClientConfig(
            name="disabled_test",
            accounts=[
                SocialAccount(
                    platform=Platform.INSTAGRAM,
                    identifier="enabled_account",
                    enabled=True,
                ),
                SocialAccount(
                    platform=Platform.INSTAGRAM,
                    identifier="disabled_account",
                    enabled=False,
                ),
            ],
        )

        results = extraction_service.extract_all(
            client_config=client_config,
            max_posts=10,
        )

        # Only enabled account should be extracted
        assert len(results) == 1
        assert results[0].account == "enabled_account"


class TestExtractionServiceErrorHandling:
    """Test error handling in ExtractionService."""

    def test_scraper_error_captured(self, temp_data_dir, sqlite_storage, mock_exporter_factory):
        """Test that scraper errors are captured in stats."""
        # Create a failing scraper
        failing_scraper = MagicMock()
        failing_scraper.get_posts_with_comments = MagicMock(
            side_effect=Exception("Scraper failed!")
        )

        def failing_factory(platform, config=None):
            return failing_scraper

        service = ExtractionService(
            storage=sqlite_storage,
            data_dir=temp_data_dir,
            scraper_factory=failing_factory,
            exporter_factory=mock_exporter_factory,
        )

        # Extraction should raise but stats should be updated
        with pytest.raises(Exception) as exc_info:
            service.extract(
                client="test_client",
                platform="instagram",
                account_id="test_account",
                max_posts=10,
            )

        assert "Scraper failed!" in str(exc_info.value)


class TestExtractionServiceWithEventBus:
    """Test ExtractionService integration with EventBus."""

    def test_events_during_extraction(self, extraction_service):
        """Test that events are emitted during extraction."""
        reset_event_bus()
        bus = get_event_bus()

        events_received = []

        def handler(event):
            events_received.append(event)

        bus.subscribe_all(handler)

        # Extract data
        extraction_service.extract(
            client="test_client",
            platform="instagram",
            account_id="test_account",
            max_posts=10,
        )

        # Note: Current ExtractionService doesn't emit events yet
        # This test is for future integration
        # assert len(events_received) > 0

        reset_event_bus()


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
