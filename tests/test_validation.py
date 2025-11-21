"""Tests for data validation utilities."""

import pytest
from datetime import datetime, timedelta, timezone

from src.core.models import (
    Platform,
    Post,
    Comment,
    Author,
    ExtractionResult,
)
from src.core.validation import (
    DataValidator,
    ValidationResult,
    validate_results,
)
from src.core.exceptions import ExtractionError


class TestValidationResult:
    """Tests for ValidationResult class."""

    @pytest.mark.unit
    def test_valid_result_is_truthy(self):
        """Test that valid result evaluates to True."""
        result = ValidationResult(True, [], [])
        assert result
        assert result.is_valid

    @pytest.mark.unit
    def test_invalid_result_is_falsy(self):
        """Test that invalid result evaluates to False."""
        result = ValidationResult(False, ["error"], [])
        assert not result
        assert not result.is_valid

    @pytest.mark.unit
    def test_result_stores_errors(self):
        """Test that errors are stored correctly."""
        errors = ["error1", "error2"]
        result = ValidationResult(False, errors, [])
        assert result.errors == errors

    @pytest.mark.unit
    def test_result_stores_warnings(self):
        """Test that warnings are stored correctly."""
        warnings = ["warning1"]
        result = ValidationResult(True, [], warnings)
        assert result.warnings == warnings


class TestDataValidator:
    """Tests for DataValidator class."""

    def create_valid_post(self) -> Post:
        """Create a valid post for testing."""
        return Post(
            platform=Platform.INSTAGRAM,
            platform_id="test_post_123",
            account_id="test_account",
            url="https://instagram.com/p/test",
            text="Test post content",
            published_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1),
            likes=100,
            comments_count=10,
            shares=5,
            media_type="image",
        )

    def create_valid_comment(self, post_id: str = "test_post_123") -> Comment:
        """Create a valid comment for testing."""
        return Comment(
            platform=Platform.INSTAGRAM,
            platform_id=f"comment_{post_id}_1",
            post_id=post_id,
            text="This is a test comment",
            author=Author(
                platform_id="author_123",
                username="testuser",
                display_name="Test User",
            ),
            published_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
            likes=5,
            replies_count=0,
        )

    @pytest.mark.unit
    def test_validate_valid_post(self):
        """Test validation of a valid post."""
        validator = DataValidator()
        post = self.create_valid_post()

        result = validator.validate_post(post)

        assert result.is_valid
        assert len(result.errors) == 0

    @pytest.mark.unit
    def test_validate_post_missing_platform_id(self):
        """Test validation fails for post without platform_id."""
        validator = DataValidator()
        post = self.create_valid_post()
        post.platform_id = ""

        result = validator.validate_post(post)

        assert not result.is_valid
        assert any("platform_id" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_post_missing_account_id(self):
        """Test validation fails for post without account_id."""
        validator = DataValidator()
        post = self.create_valid_post()
        post.account_id = ""

        result = validator.validate_post(post)

        assert not result.is_valid
        assert any("account_id" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_post_negative_likes(self):
        """Test validation fails for post with negative likes."""
        validator = DataValidator()
        post = self.create_valid_post()
        post.likes = -1

        result = validator.validate_post(post)

        assert not result.is_valid
        assert any("negative likes" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_post_missing_url_warning(self):
        """Test validation warns for post without URL."""
        validator = DataValidator()
        post = self.create_valid_post()
        post.url = None

        result = validator.validate_post(post)

        assert result.is_valid  # Warning doesn't fail
        assert any("URL" in w for w in result.warnings)

    @pytest.mark.unit
    def test_validate_post_future_date_warning(self):
        """Test validation warns for post with future date."""
        validator = DataValidator()
        post = self.create_valid_post()
        post.published_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)

        result = validator.validate_post(post)

        assert result.is_valid  # Warning doesn't fail
        assert any("future" in w for w in result.warnings)

    @pytest.mark.unit
    def test_validate_valid_comment(self):
        """Test validation of a valid comment."""
        validator = DataValidator()
        comment = self.create_valid_comment()

        result = validator.validate_comment(comment)

        assert result.is_valid
        assert len(result.errors) == 0

    @pytest.mark.unit
    def test_validate_comment_missing_platform_id(self):
        """Test validation fails for comment without platform_id."""
        validator = DataValidator()
        comment = self.create_valid_comment()
        comment.platform_id = ""

        result = validator.validate_comment(comment)

        assert not result.is_valid
        assert any("platform_id" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_comment_missing_post_id(self):
        """Test validation fails for comment without post_id."""
        validator = DataValidator()
        comment = self.create_valid_comment()
        comment.post_id = ""

        result = validator.validate_comment(comment)

        assert not result.is_valid
        assert any("post_id" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_comment_empty_text_warning(self):
        """Test validation warns for comment with empty text."""
        validator = DataValidator()
        comment = self.create_valid_comment()
        comment.text = ""

        result = validator.validate_comment(comment)

        assert result.is_valid  # Warning doesn't fail
        assert any("empty text" in w for w in result.warnings)

    @pytest.mark.unit
    def test_validate_comment_negative_likes(self):
        """Test validation fails for comment with negative likes."""
        validator = DataValidator()
        comment = self.create_valid_comment()
        comment.likes = -1

        result = validator.validate_comment(comment)

        assert not result.is_valid
        assert any("negative likes" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_extraction_result_valid(self):
        """Test validation of valid extraction result."""
        validator = DataValidator()
        post = self.create_valid_post()
        comments = [self.create_valid_comment(post.platform_id)]
        result = ExtractionResult(post=post, comments=comments)

        validation = validator.validate_extraction_result(result)

        assert validation.is_valid
        assert len(validation.errors) == 0

    @pytest.mark.unit
    def test_validate_extraction_result_mismatched_post_id(self):
        """Test validation fails when comment post_id doesn't match."""
        validator = DataValidator()
        post = self.create_valid_post()
        comment = self.create_valid_comment("different_post_id")
        result = ExtractionResult(post=post, comments=[comment])

        validation = validator.validate_extraction_result(result)

        assert not validation.is_valid
        assert any("belongs to post" in e for e in validation.errors)

    @pytest.mark.unit
    def test_strict_mode_treats_warnings_as_errors(self):
        """Test strict mode treats warnings as errors."""
        validator = DataValidator(strict=True)
        post = self.create_valid_post()
        post.url = None  # This would normally be a warning

        result = validator.validate_post(post)

        assert not result.is_valid
        assert any("URL" in e for e in result.errors)

    @pytest.mark.unit
    def test_validate_batch_all_valid(self):
        """Test batch validation with all valid results."""
        validator = DataValidator()

        results = []
        for i in range(3):
            post = self.create_valid_post()
            post.platform_id = f"post_{i}"
            comment = self.create_valid_comment(post.platform_id)
            results.append(ExtractionResult(post=post, comments=[comment]))

        valid, invalid = validator.validate_batch(results)

        assert len(valid) == 3
        assert len(invalid) == 0

    @pytest.mark.unit
    def test_validate_batch_some_invalid(self):
        """Test batch validation with some invalid results."""
        validator = DataValidator()

        # Create valid result
        valid_post = self.create_valid_post()
        valid_post.platform_id = "valid_post"
        valid_comment = self.create_valid_comment(valid_post.platform_id)
        valid_result = ExtractionResult(post=valid_post, comments=[valid_comment])

        # Create invalid result (negative likes)
        invalid_post = self.create_valid_post()
        invalid_post.platform_id = "invalid_post"
        invalid_post.likes = -1
        invalid_result = ExtractionResult(post=invalid_post, comments=[])

        valid, invalid = validator.validate_batch([valid_result, invalid_result])

        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid[0].post.platform_id == "valid_post"

    @pytest.mark.unit
    def test_validate_batch_fail_fast(self):
        """Test batch validation stops on first error in fail_fast mode."""
        validator = DataValidator()

        results = []
        for i in range(3):
            post = self.create_valid_post()
            post.platform_id = f"post_{i}"
            post.likes = -1  # All invalid
            results.append(ExtractionResult(post=post, comments=[]))

        valid, invalid = validator.validate_batch(results, fail_fast=True)

        assert len(valid) == 0
        assert len(invalid) == 1  # Stopped after first


class TestValidateResultsFunction:
    """Tests for validate_results convenience function."""

    def create_valid_extraction(self, post_id: str = "test") -> ExtractionResult:
        """Create a valid extraction result."""
        post = Post(
            platform=Platform.INSTAGRAM,
            platform_id=post_id,
            account_id="account",
            likes=10,
        )
        return ExtractionResult(post=post, comments=[])

    @pytest.mark.unit
    def test_validate_results_returns_valid(self):
        """Test validate_results returns valid results."""
        results = [self.create_valid_extraction(f"post_{i}") for i in range(3)]

        valid = validate_results(results)

        assert len(valid) == 3

    @pytest.mark.unit
    def test_validate_results_filters_invalid(self):
        """Test validate_results filters out invalid results."""
        valid_result = self.create_valid_extraction("valid")

        invalid_result = self.create_valid_extraction("invalid")
        invalid_result.post.likes = -1

        valid = validate_results([valid_result, invalid_result])

        assert len(valid) == 1
        assert valid[0].post.platform_id == "valid"

    @pytest.mark.unit
    def test_validate_results_raises_when_all_invalid(self):
        """Test validate_results raises error when all results are invalid."""
        invalid_result = self.create_valid_extraction("invalid")
        invalid_result.post.likes = -1

        with pytest.raises(ExtractionError) as exc_info:
            validate_results([invalid_result])

        assert "failed validation" in str(exc_info.value)

    @pytest.mark.unit
    def test_validate_results_empty_list_returns_empty(self):
        """Test validate_results with empty list returns empty."""
        valid = validate_results([])
        assert valid == []
