"""Data validation utilities for extraction results."""

import logging
from typing import List, Tuple, Optional
from datetime import datetime, timezone

from .models import ExtractionResult, Post, Comment
from .exceptions import ExtractionError

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation check."""

    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]) -> None:
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    def __bool__(self) -> bool:
        return self.is_valid


class DataValidator:
    """Validates extraction data before persistence or export."""

    def __init__(self, strict: bool = False) -> None:
        """
        Initialize validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict

    def validate_post(self, post: Post) -> ValidationResult:
        """
        Validate a post.

        Args:
            post: Post to validate

        Returns:
            ValidationResult with any errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Required fields
        if not post.platform_id:
            errors.append("Post missing platform_id")

        if not post.platform:
            errors.append("Post missing platform")

        if not post.account_id:
            errors.append("Post missing account_id")

        # Warnings for potentially missing data
        if not post.url:
            warnings.append(f"Post {post.platform_id} missing URL")

        if post.likes < 0:
            errors.append(f"Post {post.platform_id} has negative likes: {post.likes}")

        if post.comments_count < 0:
            errors.append(f"Post {post.platform_id} has negative comments_count")

        # Check for suspicious text
        if post.text and len(post.text) > 50000:
            warnings.append(f"Post {post.platform_id} has unusually long text: {len(post.text)} chars")

        # Future date check
        if post.published_at and post.published_at > datetime.now(timezone.utc).replace(tzinfo=None):
            warnings.append(f"Post {post.platform_id} has future published_at date")

        is_valid = len(errors) == 0
        if self.strict and warnings:
            is_valid = False
            errors.extend(warnings)
            warnings = []

        return ValidationResult(is_valid, errors, warnings)

    def validate_comment(self, comment: Comment) -> ValidationResult:
        """
        Validate a comment.

        Args:
            comment: Comment to validate

        Returns:
            ValidationResult with any errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Required fields
        if not comment.platform_id:
            errors.append("Comment missing platform_id")

        if not comment.post_id:
            errors.append("Comment missing post_id")

        if not comment.text:
            warnings.append(f"Comment {comment.platform_id} has empty text")

        # Author validation
        if not comment.author:
            errors.append(f"Comment {comment.platform_id} missing author")
        elif not comment.author.username and not comment.author.display_name:
            warnings.append(f"Comment {comment.platform_id} has anonymous author")

        if comment.likes < 0:
            errors.append(f"Comment {comment.platform_id} has negative likes")

        # Check for suspicious text
        if comment.text and len(comment.text) > 10000:
            warnings.append(f"Comment {comment.platform_id} has unusually long text")

        # Future date check
        if comment.published_at and comment.published_at > datetime.now(timezone.utc).replace(tzinfo=None):
            warnings.append(f"Comment {comment.platform_id} has future date")

        is_valid = len(errors) == 0
        if self.strict and warnings:
            is_valid = False
            errors.extend(warnings)
            warnings = []

        return ValidationResult(is_valid, errors, warnings)

    def validate_extraction_result(self, result: ExtractionResult) -> ValidationResult:
        """
        Validate an extraction result (post + comments).

        Args:
            result: Extraction result to validate

        Returns:
            ValidationResult with any errors/warnings
        """
        all_errors: List[str] = []
        all_warnings: List[str] = []

        # Validate post
        post_result = self.validate_post(result.post)
        all_errors.extend(post_result.errors)
        all_warnings.extend(post_result.warnings)

        # Validate comments
        for comment in result.comments:
            comment_result = self.validate_comment(comment)
            all_errors.extend(comment_result.errors)
            all_warnings.extend(comment_result.warnings)

            # Check comment belongs to post
            if comment.post_id != result.post.platform_id:
                all_errors.append(
                    f"Comment {comment.platform_id} has post_id {comment.post_id} "
                    f"but belongs to post {result.post.platform_id}"
                )

        is_valid = len(all_errors) == 0

        return ValidationResult(is_valid, all_errors, all_warnings)

    def validate_batch(
        self,
        results: List[ExtractionResult],
        fail_fast: bool = False
    ) -> Tuple[List[ExtractionResult], List[Tuple[ExtractionResult, ValidationResult]]]:
        """
        Validate a batch of extraction results.

        Args:
            results: List of extraction results
            fail_fast: If True, stop on first error

        Returns:
            Tuple of (valid_results, invalid_results_with_errors)
        """
        valid: List[ExtractionResult] = []
        invalid: List[Tuple[ExtractionResult, ValidationResult]] = []

        for result in results:
            validation = self.validate_extraction_result(result)

            if validation.is_valid:
                valid.append(result)
                if validation.warnings:
                    logger.warning(
                        f"Post {result.post.platform_id} has warnings: {validation.warnings}"
                    )
            else:
                invalid.append((result, validation))
                logger.error(
                    f"Post {result.post.platform_id} validation failed: {validation.errors}"
                )
                if fail_fast:
                    break

        logger.info(f"Validation complete: {len(valid)} valid, {len(invalid)} invalid")

        return valid, invalid


def validate_results(
    results: List[ExtractionResult],
    strict: bool = False
) -> List[ExtractionResult]:
    """
    Convenience function to validate and filter extraction results.

    Args:
        results: Extraction results to validate
        strict: If True, treat warnings as errors

    Returns:
        List of valid extraction results

    Raises:
        ExtractionError: If all results are invalid
    """
    validator = DataValidator(strict=strict)
    valid, invalid = validator.validate_batch(results)

    if not valid and results:
        error_details = [
            f"{r.post.platform_id}: {v.errors}"
            for r, v in invalid[:5]  # Show first 5 errors
        ]
        raise ExtractionError(
            f"All {len(results)} results failed validation. "
            f"First errors: {error_details}"
        )

    return valid
