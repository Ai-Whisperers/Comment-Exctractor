"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import Post, Comment, Profile, Platform, Author
from src.storage import StorageFactory


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_post():
    """Create a sample Post object for testing."""
    return Post(
        platform_id="test-post-123",
        platform=Platform.INSTAGRAM,
        account_id="test_account",
        text="This is a test post with some content. #test #sample",
        likes=100,
        comments_count=5,
        shares=10,
        url="https://instagram.com/p/test123",
        media_type="image",
        published_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_posts():
    """Create multiple sample Post objects."""
    posts = []
    for i in range(5):
        post = Post(
            platform_id=f"test-post-{i}",
            platform=Platform.INSTAGRAM,
            account_id="test_account",
            text=f"Test post {i}",
            likes=100 * (i + 1),
            comments_count=i * 2,
            shares=i,
            url=f"https://instagram.com/p/test{i}",
            media_type="image",
            published_at=datetime(2024, 1, i + 1, 10, 0, 0),
        )
        posts.append(post)
    return posts


@pytest.fixture
def sample_comment():
    """Create a sample Comment object for testing."""
    return Comment(
        platform_id="test-comment-123",
        post_id="test-post-123",
        platform=Platform.INSTAGRAM,
        author=Author(
            platform_id="commenter_123",
            username="commenter_user",
            display_name="Commenter User",
        ),
        text="This is a test comment!",
        likes=25,
        parent_id=None,
        replies_count=3,
        published_at=datetime(2024, 1, 15, 11, 0, 0),
    )


@pytest.fixture
def sample_comments():
    """Create multiple sample Comment objects."""
    comments = []
    for i in range(10):
        comment = Comment(
            platform_id=f"test-comment-{i}",
            post_id="test-post-123",
            platform=Platform.INSTAGRAM,
            author=Author(
                platform_id=f"user_{i}",
                username=f"user_{i}",
                display_name=f"User {i}",
            ),
            text=f"Test comment {i}",
            likes=i * 5,
            parent_id=None if i < 5 else f"test-comment-{i-5}",
            replies_count=0,
            published_at=datetime(2024, 1, 15, 11 + i, 0, 0),
        )
        comments.append(comment)
    return comments


@pytest.fixture
def sample_profile():
    """Create a sample Profile object for testing."""
    return Profile(
        platform_id="test_account_123",
        username="test_account",
        display_name="Test Account",
        platform=Platform.INSTAGRAM,
        description="This is a test account bio. Testing 123.",
        followers_count=10000,
        following_count=500,
        posts_count=150,
        url="https://instagram.com/test_account",
        profile_image="https://example.com/avatar.jpg",
        is_verified=True,
    )


@pytest.fixture
def json_storage(temp_dir):
    """Create a JSON storage backend for testing."""
    return StorageFactory.create("json", temp_dir)


@pytest.fixture
def csv_storage(temp_dir):
    """Create a CSV storage backend for testing."""
    return StorageFactory.create("csv", temp_dir)


@pytest.fixture
def excel_storage(temp_dir):
    """Create an Excel storage backend for testing."""
    return StorageFactory.create("xlsx", temp_dir)


@pytest.fixture
def mock_page():
    """Create a mock Playwright page for testing."""
    page = MagicMock()
    page.goto = MagicMock(return_value=None)
    page.wait_for_selector = MagicMock(return_value=MagicMock())
    page.query_selector = MagicMock(return_value=MagicMock())
    page.query_selector_all = MagicMock(return_value=[])
    page.evaluate = MagicMock(return_value=None)
    page.locator = MagicMock(return_value=MagicMock())
    return page


@pytest.fixture
def mock_browser_context():
    """Create a mock Playwright browser context."""
    context = MagicMock()
    context.new_page = MagicMock(return_value=MagicMock())
    return context


# Markers for different test types
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow-running")
    config.addinivalue_line("markers", "requires_browser: mark test as requiring a browser")
    config.addinivalue_line("markers", "requires_network: mark test as requiring network access")
