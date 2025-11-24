"""
Tests for the improvement implementations.
"""

import pytest
import tempfile
import json
from pathlib import Path

# Import new utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.error_handling import categorize_error, ErrorCategory, RetryStrategy
from src.utils.data_integrity import DataIntegrity
from src.validation.quality import DataQualityValidator


class TestErrorCategorization:
    """Test error categorization logic."""

    def test_network_error(self):
        error = Exception("net::ERR_CONNECTION_REFUSED")
        assert categorize_error(error) == ErrorCategory.NETWORK

    def test_timeout_error(self):
        error = TimeoutError("Page load timeout")
        assert categorize_error(error) == ErrorCategory.TIMEOUT

    def test_rate_limit_error(self):
        error = Exception("429 Too Many Requests")
        assert categorize_error(error) == ErrorCategory.RATE_LIMIT

    def test_auth_error(self):
        error = Exception("Login failed: invalid credentials")
        assert categorize_error(error) == ErrorCategory.AUTH

    def test_not_found_error(self):
        error = Exception("Page not found - 404")
        assert categorize_error(error) == ErrorCategory.NOT_FOUND

    def test_browser_error(self):
        error = Exception("Target page closed")
        assert categorize_error(error) == ErrorCategory.BROWSER

    def test_unknown_error(self):
        error = Exception("Something weird happened")
        assert categorize_error(error) == ErrorCategory.UNKNOWN


class TestRetryStrategy:
    """Test retry strategy logic."""

    def test_should_not_retry_after_max_attempts(self):
        strategy = RetryStrategy(max_retries=3)
        error = Exception("net::ERR_CONNECTION_REFUSED")

        should_retry, _ = strategy.should_retry(error, attempt=3)
        assert should_retry is False

    def test_should_retry_network_error(self):
        strategy = RetryStrategy(max_retries=3)
        error = Exception("net::ERR_CONNECTION_REFUSED")

        should_retry, wait_time = strategy.should_retry(error, attempt=0)
        assert should_retry is True
        assert wait_time > 0

    def test_should_not_retry_unknown_error(self):
        strategy = RetryStrategy(max_retries=3)
        error = Exception("Unknown error")

        should_retry, _ = strategy.should_retry(error, attempt=0)
        assert should_retry is False


class TestDataIntegrity:
    """Test data integrity utilities."""

    def test_atomic_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            integrity = DataIntegrity(Path(tmpdir))
            data = {"test": "data", "count": 42}
            path = Path(tmpdir) / "test.json"

            checksum = integrity.save_atomic(data, path)

            assert path.exists()
            assert integrity.verify_integrity(path, checksum)

            # Verify content
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["test"] == "data"
            assert loaded["count"] == 42

    def test_journal_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            integrity = DataIntegrity(Path(tmpdir))

            # Start and commit operation 1
            integrity.start_transaction("op1")
            dummy_path = Path(tmpdir) / "dummy.json"
            with open(dummy_path, 'w') as f:
                f.write("{}")
            integrity.commit_transaction("op1", dummy_path)

            # Start but don't commit operation 2
            integrity.start_transaction("op2")

            # Check incomplete
            incomplete = integrity.get_incomplete_operations()
            assert "op2" in incomplete
            assert "op1" not in incomplete


class TestDataQualityValidator:
    """Test data quality validation."""

    def test_good_quality(self):
        validator = DataQualityValidator()

        posts = [
            {"platform_id": "1", "text": "Post content here"},
            {"platform_id": "2", "text": "Another post"}
        ]
        comments = [
            {"text": "Good comment text here", "author": "user1", "published_at": "2024-01-01"},
            {"text": "Another comment here", "author": "user2", "published_at": "2024-01-01"},
            {"text": "Third comment text", "author": "user3", "published_at": "2024-01-01"}
        ]

        result = validator.validate_extraction(posts, comments)
        assert result["score"] >= 70
        assert result["grade"] in ["A", "B", "C"]

    def test_poor_quality_duplicates(self):
        validator = DataQualityValidator()

        posts = [{"platform_id": "1", "text": "Post"}]
        comments = [
            {"text": "Same text here", "author": "unknown"},
            {"text": "Same text here", "author": "unknown"},
            {"text": "Same text here", "author": "unknown"}
        ]

        result = validator.validate_extraction(posts, comments)
        assert result["score"] < 80
        assert any("duplicate" in issue.lower() for issue in result["issues"])

    def test_empty_extraction(self):
        validator = DataQualityValidator()

        result = validator.validate_extraction([], [])
        assert result["score"] < 100
        assert "No posts" in str(result["issues"])


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
