"""Tests for SQLiteStorage protocol compliance and batch operations."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from src.storage.sqlite import SQLiteStorage, SQLiteStorageAdapter
from src.storage.base import StorageFactory
from src.core.models import Post, Comment, Profile, Author, Platform
from src.core.exceptions import ValidationError


def create_temp_db():
    """Create a temporary database file that can be cleaned up."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def cleanup_db(path):
    """Clean up temporary database file."""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass  # Windows may have file locks


class TestSQLiteStorageInit:
    """Tests for SQLiteStorage initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default database path."""
        storage = SQLiteStorage()
        assert storage.db_path.exists()

    def test_init_with_custom_path(self):
        """Test initialization with custom database path."""
        db_path = create_temp_db()
        try:
            storage = SQLiteStorage(db_path)
            assert storage.db_path == Path(db_path)
            assert Path(db_path).exists()
        finally:
            cleanup_db(db_path)

    def test_init_creates_parent_directories(self):
        """Test that initialization creates parent directories."""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "nested" / "dir" / "test.db"
            storage = SQLiteStorage(str(db_path))
            assert db_path.parent.exists()
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_init_rejects_path_traversal(self):
        """Test that initialization rejects path traversal attempts."""
        with pytest.raises(ValidationError) as exc_info:
            SQLiteStorage("../../../etc/test.db")
        assert "path traversal" in str(exc_info.value).lower()

    def test_init_rejects_embedded_traversal(self):
        """Test that embedded path traversal is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SQLiteStorage("data/../../../escape/test.db")
        assert "path traversal" in str(exc_info.value).lower()


class TestSQLiteStorageAdapter:
    """Tests for SQLiteStorageAdapter factory integration."""

    def test_adapter_creates_storage_instance(self):
        """Test that adapter creates SQLiteStorage instance."""
        tmpdir = tempfile.mkdtemp()
        try:
            storage = SQLiteStorageAdapter(tmpdir)
            assert isinstance(storage, SQLiteStorage)
            # Resolve both paths to handle Windows short path names (8.3 format)
            assert storage.db_path.resolve() == (Path(tmpdir) / "storage.db").resolve()
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_adapter_registered_with_factory(self):
        """Test that SQLite is registered with StorageFactory."""
        assert "sqlite" in StorageFactory.available_formats()

    def test_factory_creates_sqlite_storage(self):
        """Test creating SQLiteStorage via StorageFactory."""
        tmpdir = tempfile.mkdtemp()
        try:
            storage = StorageFactory.create("sqlite", tmpdir)
            assert isinstance(storage, SQLiteStorage)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSQLiteStorageBatchMethods:
    """Tests for StorageBackend-compatible batch methods."""

    @pytest.fixture
    def storage(self):
        """Create temporary storage for testing."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)
        yield storage
        cleanup_db(db_path)

    @pytest.fixture
    def sample_posts(self):
        """Create sample posts for testing."""
        return [
            Post(
                platform=Platform.INSTAGRAM,
                platform_id=f"post_{i}",
                account_id="testuser",
                text=f"Test post {i}",
                likes=i * 10,
                comments_count=i,
                url=f"https://instagram.com/p/{i}",
            )
            for i in range(3)
        ]

    @pytest.fixture
    def sample_comments(self):
        """Create sample comments for testing."""
        return [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_{i}",
                post_id="post_1",
                text=f"Test comment {i}",
                author=Author(
                    platform_id=f"user_{i}",
                    username=f"user{i}",
                    display_name=f"User {i}",
                ),
                likes=i * 5,
            )
            for i in range(5)
        ]

    @pytest.fixture
    def sample_profile(self):
        """Create sample profile for testing."""
        return Profile(
            platform=Platform.INSTAGRAM,
            platform_id="user_123",
            username="testuser",
            display_name="Test User",
            description="A test profile",
            followers_count=1000,
            following_count=500,
            posts_count=50,
        )

    def test_save_posts_batch(self, storage, sample_posts):
        """Test saving multiple posts at once."""
        result = storage.save_posts(sample_posts, "testclient", "instagram")

        assert "sqlite" in result
        assert "posts" in result
        assert "testclient" in result

        # Verify posts were saved
        posts = storage.get_posts("testclient", "instagram")
        assert len(posts) == 3

    def test_save_comments_batch(self, storage, sample_comments):
        """Test saving multiple comments at once."""
        result = storage.save_comments(sample_comments, "testclient", "instagram")

        assert "sqlite" in result
        assert "comments" in result
        assert "testclient" in result

        # Verify comments were saved
        comments = storage.get_comments("testclient", "instagram")
        assert len(comments) == 5

    def test_save_extraction_result(self, storage, sample_posts, sample_comments, sample_profile):
        """Test saving complete extraction result."""
        results = storage.save_extraction_result(
            posts=sample_posts,
            comments=sample_comments,
            profile=sample_profile,
            account="testclient",
            platform="instagram"
        )

        assert "posts" in results
        assert "comments" in results
        assert "profile" in results

        # Verify all data saved
        posts = storage.get_posts("testclient", "instagram")
        comments = storage.get_comments("testclient", "instagram")
        assert len(posts) == 3
        assert len(comments) == 5

    def test_save_extraction_result_empty_posts(self, storage, sample_comments, sample_profile):
        """Test saving extraction with no posts."""
        results = storage.save_extraction_result(
            posts=[],
            comments=sample_comments,
            profile=sample_profile,
            account="testclient",
            platform="instagram"
        )

        assert "posts" not in results
        assert "comments" in results
        assert "profile" in results

    def test_save_extraction_result_empty_comments(self, storage, sample_posts, sample_profile):
        """Test saving extraction with no comments."""
        results = storage.save_extraction_result(
            posts=sample_posts,
            comments=[],
            profile=sample_profile,
            account="testclient",
            platform="instagram"
        )

        assert "posts" in results
        assert "comments" not in results
        assert "profile" in results

    def test_save_extraction_result_no_profile(self, storage, sample_posts, sample_comments):
        """Test saving extraction with no profile."""
        results = storage.save_extraction_result(
            posts=sample_posts,
            comments=sample_comments,
            profile=None,
            account="testclient",
            platform="instagram"
        )

        assert "posts" in results
        assert "comments" in results
        assert "profile" not in results

    def test_save_posts_handles_duplicates(self, storage, sample_posts):
        """Test that duplicate posts are handled gracefully."""
        # Save once
        storage.save_posts(sample_posts, "testclient", "instagram")

        # Save again - should not error
        storage.save_posts(sample_posts, "testclient", "instagram")

        # Should still only have original count
        posts = storage.get_posts("testclient", "instagram")
        assert len(posts) == 3

    def test_save_comments_handles_duplicates(self, storage, sample_comments):
        """Test that duplicate comments are handled gracefully."""
        # Save once
        storage.save_comments(sample_comments, "testclient", "instagram")

        # Save again - should not error
        storage.save_comments(sample_comments, "testclient", "instagram")

        # Should still only have original count
        comments = storage.get_comments("testclient", "instagram")
        assert len(comments) == 5


class TestSQLiteStorageProtocolCompliance:
    """Tests to verify StorageProtocol compliance."""

    @pytest.fixture
    def storage(self):
        """Create temporary storage for testing."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)
        yield storage
        cleanup_db(db_path)

    def test_has_save_comment(self, storage):
        """Test that storage has save_comment method."""
        assert hasattr(storage, 'save_comment')
        assert callable(storage.save_comment)

    def test_has_save_post(self, storage):
        """Test that storage has save_post method."""
        assert hasattr(storage, 'save_post')
        assert callable(storage.save_post)

    def test_has_save_profile(self, storage):
        """Test that storage has save_profile method."""
        assert hasattr(storage, 'save_profile')
        assert callable(storage.save_profile)

    def test_has_get_comments(self, storage):
        """Test that storage has get_comments method."""
        assert hasattr(storage, 'get_comments')
        assert callable(storage.get_comments)

    def test_has_get_posts(self, storage):
        """Test that storage has get_posts method."""
        assert hasattr(storage, 'get_posts')
        assert callable(storage.get_posts)

    def test_has_get_last_extraction_date(self, storage):
        """Test that storage has get_last_extraction_date method."""
        assert hasattr(storage, 'get_last_extraction_date')
        assert callable(storage.get_last_extraction_date)

    def test_has_update_extraction_history(self, storage):
        """Test that storage has update_extraction_history method."""
        assert hasattr(storage, 'update_extraction_history')
        assert callable(storage.update_extraction_history)

    def test_has_get_comment_count(self, storage):
        """Test that storage has get_comment_count method."""
        assert hasattr(storage, 'get_comment_count')
        assert callable(storage.get_comment_count)


class TestSQLiteStorageBackendCompatibility:
    """Tests for StorageBackend-compatible methods."""

    @pytest.fixture
    def storage(self):
        """Create temporary storage for testing."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)
        yield storage
        cleanup_db(db_path)

    def test_has_save_posts_batch(self, storage):
        """Test that storage has batch save_posts method."""
        assert hasattr(storage, 'save_posts')
        assert callable(storage.save_posts)

    def test_has_save_comments_batch(self, storage):
        """Test that storage has batch save_comments method."""
        assert hasattr(storage, 'save_comments')
        assert callable(storage.save_comments)

    def test_has_save_extraction_result(self, storage):
        """Test that storage has save_extraction_result method."""
        assert hasattr(storage, 'save_extraction_result')
        assert callable(storage.save_extraction_result)


class TestSQLiteStorageQueryMethods:
    """Tests for query methods."""

    @pytest.fixture
    def storage_with_data(self):
        """Create storage with pre-populated data."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)

        # Add some comments
        for i in range(10):
            comment = Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_{i}",
                post_id="post_1",
                text=f"Comment {i}",
                author=Author(
                    platform_id=f"user_{i}",
                    username=f"user{i}",
                    display_name=f"User {i}",
                ),
                likes=i,
                published_at=datetime(2024, 1, i + 1),
            )
            storage.save_comment("testclient", comment)

        yield storage
        cleanup_db(db_path)

    def test_get_comments_with_limit(self, storage_with_data):
        """Test getting comments with limit."""
        comments = storage_with_data.get_comments("testclient", limit=5)
        assert len(comments) == 5

    def test_get_comments_with_since_date(self, storage_with_data):
        """Test getting comments after a date."""
        since = datetime(2024, 1, 5)
        comments = storage_with_data.get_comments("testclient", since=since)
        assert all(c.published_at >= since for c in comments if c.published_at)

    def test_get_comments_with_until_date(self, storage_with_data):
        """Test getting comments before a date."""
        until = datetime(2024, 1, 5)
        comments = storage_with_data.get_comments("testclient", until=until)
        assert all(c.published_at <= until for c in comments if c.published_at)

    def test_get_comment_count(self, storage_with_data):
        """Test getting total comment count."""
        count = storage_with_data.get_comment_count("testclient")
        assert count == 10

    def test_get_comment_count_by_platform(self, storage_with_data):
        """Test getting comment count filtered by platform."""
        count = storage_with_data.get_comment_count("testclient", "instagram")
        assert count == 10

        # Different platform should be 0
        count = storage_with_data.get_comment_count("testclient", "facebook")
        assert count == 0


class TestSQLiteStorageBatchOperations:
    """Tests for optimized batch database operations."""

    @pytest.fixture
    def storage(self):
        """Create temporary storage for testing."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)
        yield storage
        cleanup_db(db_path)

    def create_comments(self, count: int, post_id: str = "post_1"):
        """Helper to create multiple comments."""
        return [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_{i}",
                post_id=post_id,
                text=f"Comment text {i}",
                author=Author(
                    platform_id=f"user_{i}",
                    username=f"user{i}",
                    display_name=f"User {i}",
                ),
                likes=i,
                published_at=datetime(2024, 1, 15, 10, i % 60),
            )
            for i in range(count)
        ]

    def create_posts(self, count: int):
        """Helper to create multiple posts."""
        return [
            Post(
                platform=Platform.INSTAGRAM,
                platform_id=f"post_{i}",
                account_id="test_account",
                url=f"https://instagram.com/p/{i}",
                text=f"Post text {i}",
                likes=i * 10,
                comments_count=i,
                shares=i,
                published_at=datetime(2024, 1, 15, 10, i % 60),
            )
            for i in range(count)
        ]

    def test_save_comments_batch_empty(self, storage):
        """Test batch save with empty list."""
        saved, duplicates = storage.save_comments_batch("testclient", [])
        assert saved == 0
        assert duplicates == 0

    def test_save_comments_batch_small(self, storage):
        """Test batch save with small list."""
        comments = self.create_comments(10)
        saved, duplicates = storage.save_comments_batch("testclient", comments)
        assert saved == 10
        assert duplicates == 0

        # Verify data is in database
        stored = storage.get_comments("testclient")
        assert len(stored) == 10

    def test_save_comments_batch_large(self, storage):
        """Test batch save with large list (tests batching)."""
        comments = self.create_comments(1000)
        saved, duplicates = storage.save_comments_batch("testclient", comments)
        assert saved == 1000
        assert duplicates == 0

        # Verify count
        count = storage.get_comment_count("testclient")
        assert count == 1000

    def test_save_comments_batch_with_duplicates(self, storage):
        """Test batch save handles duplicates correctly."""
        comments = self.create_comments(50)

        # Save first time
        saved1, dup1 = storage.save_comments_batch("testclient", comments)
        assert saved1 == 50
        assert dup1 == 0

        # Save same comments again
        saved2, dup2 = storage.save_comments_batch("testclient", comments)
        assert saved2 == 0
        assert dup2 == 50

        # Count should still be 50
        count = storage.get_comment_count("testclient")
        assert count == 50

    def test_save_comments_batch_custom_batch_size(self, storage):
        """Test batch save with custom batch size."""
        comments = self.create_comments(100)
        saved, duplicates = storage.save_comments_batch(
            "testclient", comments, batch_size=25
        )
        assert saved == 100
        assert duplicates == 0

    def test_save_posts_batch_empty(self, storage):
        """Test batch save posts with empty list."""
        saved, duplicates = storage.save_posts_batch("testclient", [])
        assert saved == 0
        assert duplicates == 0

    def test_save_posts_batch_small(self, storage):
        """Test batch save posts with small list."""
        posts = self.create_posts(10)
        saved, duplicates = storage.save_posts_batch("testclient", posts)
        assert saved == 10
        assert duplicates == 0

        # Verify data
        stored = storage.get_posts("testclient")
        assert len(stored) == 10

    def test_save_posts_batch_large(self, storage):
        """Test batch save posts with large list."""
        posts = self.create_posts(500)
        saved, duplicates = storage.save_posts_batch("testclient", posts)
        assert saved == 500
        assert duplicates == 0

    def test_save_posts_batch_with_duplicates(self, storage):
        """Test batch save posts handles duplicates correctly."""
        posts = self.create_posts(30)

        # Save first time
        saved1, dup1 = storage.save_posts_batch("testclient", posts)
        assert saved1 == 30
        assert dup1 == 0

        # Save same posts again
        saved2, dup2 = storage.save_posts_batch("testclient", posts)
        assert saved2 == 0
        assert dup2 == 30

    def test_exists_comment(self, storage):
        """Test checking if a comment exists."""
        comments = self.create_comments(5)
        storage.save_comments_batch("testclient", comments)

        # Check existing
        assert storage.exists_comment("instagram", "comment_0") is True
        assert storage.exists_comment("instagram", "comment_4") is True

        # Check non-existing
        assert storage.exists_comment("instagram", "comment_999") is False
        assert storage.exists_comment("facebook", "comment_0") is False

    def test_exists_comments_batch_empty(self, storage):
        """Test batch existence check with empty list."""
        result = storage.exists_comments_batch("instagram", [])
        assert result == {}

    def test_exists_comments_batch(self, storage):
        """Test batch existence check."""
        comments = self.create_comments(10)
        storage.save_comments_batch("testclient", comments)

        # Check mix of existing and non-existing
        platform_ids = [
            "comment_0", "comment_5", "comment_9",  # Exist
            "comment_100", "comment_999"  # Don't exist
        ]
        result = storage.exists_comments_batch("instagram", platform_ids)

        assert result["comment_0"] is True
        assert result["comment_5"] is True
        assert result["comment_9"] is True
        assert result["comment_100"] is False
        assert result["comment_999"] is False

    def test_exists_comments_batch_large(self, storage):
        """Test batch existence check with large list."""
        comments = self.create_comments(100)
        storage.save_comments_batch("testclient", comments)

        # Generate IDs to check (some exist, some don't)
        platform_ids = [f"comment_{i}" for i in range(150)]
        result = storage.exists_comments_batch("instagram", platform_ids)

        # First 100 should exist
        for i in range(100):
            assert result[f"comment_{i}"] is True

        # Rest shouldn't exist
        for i in range(100, 150):
            assert result[f"comment_{i}"] is False

    def test_get_existing_comment_ids(self, storage):
        """Test getting set of existing comment IDs."""
        comments = self.create_comments(20)
        storage.save_comments_batch("testclient", comments)

        existing_ids = storage.get_existing_comment_ids("testclient", "instagram")
        assert len(existing_ids) == 20
        assert "comment_0" in existing_ids
        assert "comment_19" in existing_ids
        assert "comment_100" not in existing_ids

    def test_get_existing_comment_ids_by_post(self, storage):
        """Test getting existing IDs filtered by post."""
        # Create comments for different posts
        comments_post1 = [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_p1_{i}",
                post_id="post_1",
                text=f"Comment {i}",
                author=Author(platform_id="u1", username="user1"),
                likes=0,
            )
            for i in range(5)
        ]
        comments_post2 = [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_p2_{i}",
                post_id="post_2",
                text=f"Comment {i}",
                author=Author(platform_id="u1", username="user1"),
                likes=0,
            )
            for i in range(5)
        ]

        storage.save_comments_batch("testclient", comments_post1 + comments_post2)

        # Get IDs for post_1 only
        ids_post1 = storage.get_existing_comment_ids(
            "testclient", "instagram", post_ids=["post_1"]
        )
        assert len(ids_post1) == 5
        assert "comment_p1_0" in ids_post1
        assert "comment_p2_0" not in ids_post1

    def test_batch_performance_is_faster(self, storage):
        """Test that batch operations are faster than individual saves."""
        import time

        # Create test data
        comments_batch = self.create_comments(200)
        comments_individual = [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"ind_comment_{i}",
                post_id="post_ind",
                text=f"Individual Comment {i}",
                author=Author(platform_id=f"ind_u{i}", username=f"induser{i}"),
                likes=i,
                published_at=datetime(2024, 1, 15),
            )
            for i in range(200)
        ]

        # Time batch operation
        start_batch = time.time()
        storage.save_comments_batch("testclient", comments_batch)
        batch_time = time.time() - start_batch

        # Time individual operations
        start_individual = time.time()
        for comment in comments_individual:
            storage.save_comment("testclient", comment)
        individual_time = time.time() - start_individual

        # Batch should be significantly faster (at least 2x)
        # Note: This may vary based on system, so we use a generous margin
        assert batch_time < individual_time, (
            f"Batch ({batch_time:.3f}s) should be faster than individual "
            f"({individual_time:.3f}s)"
        )


class TestSQLiteStorageBatchIntegration:
    """Integration tests for batch operations with save_posts and save_comments."""

    @pytest.fixture
    def storage(self):
        """Create temporary storage for testing."""
        db_path = create_temp_db()
        storage = SQLiteStorage(db_path)
        yield storage
        cleanup_db(db_path)

    def test_save_posts_uses_batch(self, storage):
        """Test that save_posts method uses batch operations."""
        posts = [
            Post(
                platform=Platform.INSTAGRAM,
                platform_id=f"post_{i}",
                account_id="test_account",
                url=f"https://instagram.com/p/{i}",
                text=f"Post {i}",
                likes=i,
                comments_count=0,
                shares=0,
            )
            for i in range(50)
        ]

        result = storage.save_posts(posts, "testclient", "instagram")

        assert "sqlite:" in result
        assert "posts" in result

        # Verify all saved
        stored = storage.get_posts("testclient")
        assert len(stored) == 50

    def test_save_comments_uses_batch(self, storage):
        """Test that save_comments method uses batch operations."""
        comments = [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment_{i}",
                post_id="post_1",
                text=f"Comment {i}",
                author=Author(platform_id=f"u{i}", username=f"user{i}"),
                likes=i,
            )
            for i in range(50)
        ]

        result = storage.save_comments(comments, "testclient", "instagram")

        assert "sqlite:" in result
        assert "comments" in result

        # Verify all saved
        stored = storage.get_comments("testclient")
        assert len(stored) == 50
