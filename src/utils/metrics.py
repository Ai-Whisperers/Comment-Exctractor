"""Performance metrics collection and reporting.

Provides metrics for monitoring extraction performance:
- Extraction duration
- Posts/comments per second
- Error rates
- Rate limit occurrences
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractionMetrics:
    """Metrics for a single extraction run."""
    client: str
    platform: str
    account: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0
    posts_extracted: int = 0
    comments_extracted: int = 0
    errors: int = 0
    rate_limits: int = 0

    @property
    def posts_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0
        return self.posts_extracted / self.duration_seconds

    @property
    def comments_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0
        return self.comments_extracted / self.duration_seconds


class MetricsCollector:
    """
    Collects and aggregates performance metrics.

    Usage:
        collector = MetricsCollector()

        # Record metrics
        collector.record_extraction(
            client="acme",
            platform="facebook",
            account="AcmeCorp",
            duration=120.5,
            posts=50,
            comments=500,
        )

        # Get summary
        summary = collector.get_summary()
        print(f"Total extractions: {summary['total_extractions']}")
    """

    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector.

        Args:
            retention_hours: How long to keep metrics
        """
        self._lock = Lock()
        self._extractions: List[ExtractionMetrics] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._retention = timedelta(hours=retention_hours)

    def record_extraction(
        self,
        client: str,
        platform: str,
        account: str,
        duration: float,
        posts: int,
        comments: int,
        errors: int = 0,
        rate_limits: int = 0,
    ) -> ExtractionMetrics:
        """
        Record metrics for an extraction.

        Args:
            client: Client name
            platform: Platform
            account: Account ID
            duration: Duration in seconds
            posts: Posts extracted
            comments: Comments extracted
            errors: Number of errors
            rate_limits: Number of rate limits hit

        Returns:
            ExtractionMetrics object
        """
        with self._lock:
            metrics = ExtractionMetrics(
                client=client,
                platform=platform,
                account=account,
                started_at=datetime.utcnow() - timedelta(seconds=duration),
                completed_at=datetime.utcnow(),
                duration_seconds=duration,
                posts_extracted=posts,
                comments_extracted=comments,
                errors=errors,
                rate_limits=rate_limits,
            )

            self._extractions.append(metrics)
            self._cleanup_old_metrics()

            # Update counters
            self._counters["total_extractions"] += 1
            self._counters["total_posts"] += posts
            self._counters["total_comments"] += comments
            self._counters["total_errors"] += errors
            self._counters["total_rate_limits"] += rate_limits

            # Update histograms
            self._histograms["extraction_duration"].append(duration)
            if posts > 0:
                self._histograms["posts_per_extraction"].append(posts)
            if comments > 0:
                self._histograms["comments_per_extraction"].append(comments)

            logger.debug(
                f"Recorded metrics: {client}/{platform}/{account} - "
                f"{posts} posts, {comments} comments in {duration:.1f}s"
            )

            return metrics

    def increment(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.

        Returns:
            Dictionary with aggregated metrics
        """
        with self._lock:
            self._cleanup_old_metrics()

            # Calculate aggregates
            recent_extractions = self._extractions

            if not recent_extractions:
                return {
                    "total_extractions": self._counters["total_extractions"],
                    "total_posts": self._counters["total_posts"],
                    "total_comments": self._counters["total_comments"],
                    "total_errors": self._counters["total_errors"],
                    "total_rate_limits": self._counters["total_rate_limits"],
                    "recent_extractions": 0,
                    "avg_duration": 0,
                    "avg_posts_per_extraction": 0,
                    "avg_comments_per_extraction": 0,
                    "error_rate": 0,
                }

            durations = [e.duration_seconds for e in recent_extractions]
            posts = [e.posts_extracted for e in recent_extractions]
            comments = [e.comments_extracted for e in recent_extractions]
            errors = sum(e.errors for e in recent_extractions)

            return {
                "total_extractions": self._counters["total_extractions"],
                "total_posts": self._counters["total_posts"],
                "total_comments": self._counters["total_comments"],
                "total_errors": self._counters["total_errors"],
                "total_rate_limits": self._counters["total_rate_limits"],
                "recent_extractions": len(recent_extractions),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "avg_posts_per_extraction": sum(posts) / len(posts) if posts else 0,
                "avg_comments_per_extraction": sum(comments) / len(comments) if comments else 0,
                "error_rate": errors / len(recent_extractions) if recent_extractions else 0,
            }

    def get_client_metrics(self, client: str) -> Dict[str, Any]:
        """
        Get metrics for a specific client.

        Args:
            client: Client name

        Returns:
            Client-specific metrics
        """
        with self._lock:
            client_extractions = [
                e for e in self._extractions
                if e.client == client
            ]

            if not client_extractions:
                return {"client": client, "extractions": 0}

            return {
                "client": client,
                "extractions": len(client_extractions),
                "total_posts": sum(e.posts_extracted for e in client_extractions),
                "total_comments": sum(e.comments_extracted for e in client_extractions),
                "avg_duration": sum(e.duration_seconds for e in client_extractions) / len(client_extractions),
                "errors": sum(e.errors for e in client_extractions),
                "platforms": list(set(e.platform for e in client_extractions)),
            }

    def get_platform_metrics(self, platform: str) -> Dict[str, Any]:
        """
        Get metrics for a specific platform.

        Args:
            platform: Platform name

        Returns:
            Platform-specific metrics
        """
        with self._lock:
            platform_extractions = [
                e for e in self._extractions
                if e.platform == platform
            ]

            if not platform_extractions:
                return {"platform": platform, "extractions": 0}

            return {
                "platform": platform,
                "extractions": len(platform_extractions),
                "total_posts": sum(e.posts_extracted for e in platform_extractions),
                "total_comments": sum(e.comments_extracted for e in platform_extractions),
                "avg_duration": sum(e.duration_seconds for e in platform_extractions) / len(platform_extractions),
                "rate_limits": sum(e.rate_limits for e in platform_extractions),
            }

    def get_recent_extractions(self, limit: int = 10) -> List[ExtractionMetrics]:
        """Get most recent extractions."""
        with self._lock:
            return sorted(
                self._extractions,
                key=lambda e: e.started_at,
                reverse=True
            )[:limit]

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._extractions.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - self._retention
        self._extractions = [
            e for e in self._extractions
            if e.started_at > cutoff
        ]


# =============================================================================
# TIMER CONTEXT MANAGER
# =============================================================================

class Timer:
    """
    Context manager for timing operations.

    Usage:
        with Timer() as t:
            do_work()

        print(f"Took {t.elapsed:.2f}s")
    """

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time


# =============================================================================
# GLOBAL METRICS COLLECTOR
# =============================================================================

_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_metrics() -> None:
    """Reset global metrics collector."""
    global _global_collector
    if _global_collector:
        _global_collector.reset()
    _global_collector = None
