"""
Real-time extraction monitoring and metrics.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class ExtractionMonitor:
    """
    Monitors extraction progress with metrics and alerting.
    """

    def __init__(self, alert_callback: Optional[Callable] = None):
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "posts_extracted": 0,
            "comments_extracted": 0,
            "errors": 0,
            "rate_limits": 0,
            "start_time": None,
            "last_update": None,
            "extraction_rate": 0.0,
            "avg_comments_per_post": 0.0
        })
        self.alert_callback = alert_callback or self._default_alert

    def start_extraction(self, account_id: str) -> None:
        """Record extraction start."""
        self.metrics[account_id]["start_time"] = time.time()
        self.metrics[account_id]["last_update"] = time.time()
        logger.info(f"MONITOR | Started extraction for {account_id}")

    def record_post(
        self,
        account_id: str,
        post_id: str,
        comment_count: int
    ) -> None:
        """Record successful post extraction."""
        m = self.metrics[account_id]
        m["posts_extracted"] += 1
        m["comments_extracted"] += comment_count
        m["last_update"] = time.time()

        # Calculate rates
        elapsed = m["last_update"] - m["start_time"]
        if elapsed > 0:
            m["extraction_rate"] = m["posts_extracted"] / elapsed * 60
            m["avg_comments_per_post"] = m["comments_extracted"] / m["posts_extracted"]

        # Check for anomalies
        self._check_anomalies(account_id)

        # Log progress
        if m["posts_extracted"] % 10 == 0:
            logger.info(
                f"MONITOR | {account_id}: {m['posts_extracted']} posts, "
                f"{m['comments_extracted']} comments, "
                f"{m['extraction_rate']:.1f} posts/min"
            )

    def record_error(self, account_id: str, error_type: str) -> None:
        """Record extraction error."""
        self.metrics[account_id]["errors"] += 1
        self._check_anomalies(account_id)

    def record_rate_limit(self, account_id: str) -> None:
        """Record rate limiting event."""
        self.metrics[account_id]["rate_limits"] += 1
        self.alert_callback("rate_limit", account_id, "Rate limit detected")

    def get_summary(self, account_id: str) -> Dict[str, Any]:
        """Get extraction summary for account."""
        m = self.metrics[account_id]
        elapsed = time.time() - m["start_time"] if m["start_time"] else 0

        return {
            "account_id": account_id,
            "posts": m["posts_extracted"],
            "comments": m["comments_extracted"],
            "errors": m["errors"],
            "rate_limits": m["rate_limits"],
            "duration_seconds": elapsed,
            "extraction_rate": m["extraction_rate"],
            "avg_comments_per_post": m["avg_comments_per_post"]
        }

    def _check_anomalies(self, account_id: str) -> None:
        """Check for anomalies and alert."""
        m = self.metrics[account_id]

        # Slow extraction alert
        if m["posts_extracted"] > 5 and m["extraction_rate"] < 0.5:
            self.alert_callback(
                "slow_extraction",
                account_id,
                f"Extraction rate dropped to {m['extraction_rate']:.2f} posts/min"
            )

        # High error rate alert
        total = m["posts_extracted"] + m["errors"]
        if total > 10 and m["errors"] / total > 0.3:
            self.alert_callback(
                "high_error_rate",
                account_id,
                f"Error rate at {m['errors']/total*100:.1f}%"
            )

        # Zero comments alert
        if m["posts_extracted"] > 5 and m["avg_comments_per_post"] < 0.1:
            self.alert_callback(
                "low_comments",
                account_id,
                f"Average comments per post: {m['avg_comments_per_post']:.2f}"
            )

    def _default_alert(self, alert_type: str, account_id: str, message: str) -> None:
        """Default alert handler - just log."""
        logger.warning(f"ALERT [{alert_type}] {account_id}: {message}")
