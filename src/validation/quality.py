"""
Data quality validation for extraction results.
"""

import logging
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """
    Validates extraction data quality and provides recommendations.
    """

    def __init__(self):
        self.thresholds = {
            "min_text_length": 5,
            "min_author_rate": 0.7,
            "min_timestamp_rate": 0.5,
            "max_duplicate_rate": 0.1,
            "min_comments_per_post": 0.5
        }

    def validate_extraction(self, posts: List[Dict], comments: List[Dict]) -> Dict[str, Any]:
        """
        Validate complete extraction results.

        Returns quality report with score and recommendations.
        """
        issues = []
        score = 100

        # Validate posts
        post_issues = self._validate_posts(posts)
        issues.extend(post_issues)
        score -= len(post_issues) * 5

        # Validate comments
        comment_metrics = self._validate_comments(comments)

        # Check metrics against thresholds
        if comment_metrics["text_rate"] < self.thresholds["min_text_length"]:
            issues.append(f"Low text quality: {comment_metrics['text_rate']:.1%}")
            score -= 20

        if comment_metrics["author_rate"] < self.thresholds["min_author_rate"]:
            issues.append(f"Low author rate: {comment_metrics['author_rate']:.1%}")
            score -= 15

        if comment_metrics["duplicate_rate"] > self.thresholds["max_duplicate_rate"]:
            issues.append(f"High duplicates: {comment_metrics['duplicate_rate']:.1%}")
            score -= 25

        # Check comments per post ratio
        if posts:
            comments_per_post = len(comments) / len(posts)
            if comments_per_post < self.thresholds["min_comments_per_post"]:
                issues.append(f"Low comments/post: {comments_per_post:.1f}")
                score -= 10

        return {
            "score": max(0, min(100, score)),
            "grade": self._score_to_grade(score),
            "issues": issues,
            "metrics": comment_metrics,
            "post_count": len(posts),
            "comment_count": len(comments),
            "recommendation": self._get_recommendation(score, issues)
        }

    def _validate_posts(self, posts: List[Dict]) -> List[str]:
        """Validate post data quality."""
        issues = []

        if not posts:
            issues.append("No posts extracted")
            return issues

        # Check for missing required fields
        missing_text = sum(1 for p in posts if not p.get("text"))
        if missing_text > len(posts) * 0.5:
            issues.append(f"{missing_text} posts missing text")

        missing_id = sum(1 for p in posts if not p.get("platform_id"))
        if missing_id > 0:
            issues.append(f"{missing_id} posts missing ID")

        return issues

    def _validate_comments(self, comments: List[Dict]) -> Dict[str, float]:
        """Calculate comment quality metrics."""
        if not comments:
            return {
                "text_rate": 0,
                "author_rate": 0,
                "timestamp_rate": 0,
                "duplicate_rate": 0
            }

        total = len(comments)

        # Quality counts
        has_text = sum(1 for c in comments if len(c.get("text", "").strip()) >= 5)
        has_author = sum(1 for c in comments
                       if c.get("author") and c.get("author") != "unknown")
        has_timestamp = sum(1 for c in comments if c.get("published_at"))

        # Duplicate detection
        texts = [c.get("text", "")[:50] for c in comments]
        text_counts = Counter(texts)
        duplicates = sum(count - 1 for count in text_counts.values() if count > 1)

        return {
            "text_rate": has_text / total,
            "author_rate": has_author / total,
            "timestamp_rate": has_timestamp / total,
            "duplicate_rate": duplicates / total
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_recommendation(self, score: int, issues: List[str]) -> str:
        """Generate recommendation based on quality assessment."""
        if score >= 80:
            return "Good quality - proceed with export"
        elif score >= 60:
            return "Moderate quality - review issues before using data"
        elif score >= 40:
            return "Poor quality - consider re-extraction with different settings"
        else:
            return "Critical issues - manual investigation required"
