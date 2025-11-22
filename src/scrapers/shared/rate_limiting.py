"""
Rate limiting detection and handling strategies for all platforms.

This module provides a unified approach to detecting and handling
rate limits across different social media platforms.
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Callable

from playwright.sync_api import Page

from .constants import TIMEOUTS

logger = logging.getLogger(__name__)


@dataclass
class PlatformRateLimitConfig:
    """Platform-specific rate limiting configuration."""
    # Base settings
    base_delay_ms: int = 2000
    min_delay_ms: int = 500
    max_delay_ms: int = 30000

    # Requests per time window
    requests_per_minute: int = 30
    burst_limit: int = 5  # Max requests in burst

    # Adaptive settings
    increase_factor: float = 1.5  # Multiply delay on rate limit
    decrease_factor: float = 0.9  # Multiply delay on success
    success_threshold: int = 10  # Successes before decreasing delay

    # Recovery settings
    cooldown_seconds: int = 300  # Wait after rate limit
    max_consecutive_errors: int = 3


# Platform-specific configurations
PLATFORM_CONFIGS: Dict[str, PlatformRateLimitConfig] = {
    "instagram": PlatformRateLimitConfig(
        base_delay_ms=3000,
        min_delay_ms=1500,
        max_delay_ms=60000,
        requests_per_minute=15,
        burst_limit=3,
        cooldown_seconds=600,  # 10 minutes - Instagram is strict
    ),
    "facebook": PlatformRateLimitConfig(
        base_delay_ms=2000,
        min_delay_ms=1000,
        max_delay_ms=30000,
        requests_per_minute=30,
        burst_limit=5,
        cooldown_seconds=300,
    ),
    "twitter": PlatformRateLimitConfig(
        base_delay_ms=2500,
        min_delay_ms=1000,
        max_delay_ms=45000,
        requests_per_minute=20,
        burst_limit=4,
        cooldown_seconds=900,  # 15 minutes - Twitter rate limits are strict
    ),
    "linkedin": PlatformRateLimitConfig(
        base_delay_ms=4000,
        min_delay_ms=2000,
        max_delay_ms=60000,
        requests_per_minute=10,
        burst_limit=2,
        cooldown_seconds=600,  # LinkedIn is very strict
    ),
    "google": PlatformRateLimitConfig(
        base_delay_ms=2000,
        min_delay_ms=1000,
        max_delay_ms=30000,
        requests_per_minute=30,
        burst_limit=5,
        cooldown_seconds=300,
    ),
}


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts delays based on observed behavior.

    Features:
    - Platform-specific default configurations
    - Automatic delay adjustment based on success/failure
    - Sliding window request tracking
    - Burst protection
    - Cooldown periods after rate limits
    """

    def __init__(
        self,
        platform: str,
        config: Optional[PlatformRateLimitConfig] = None
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            platform: Platform name for default config
            config: Optional custom configuration
        """
        self.platform = platform.lower()
        self.config = config or PLATFORM_CONFIGS.get(
            self.platform,
            PlatformRateLimitConfig()
        )

        # Current state
        self._current_delay_ms = self.config.base_delay_ms
        self._consecutive_successes = 0
        self._consecutive_errors = 0
        self._total_requests = 0
        self._total_rate_limits = 0

        # Request tracking for sliding window
        self._request_times: List[float] = []
        self._last_rate_limit_time: Optional[float] = None

        logger.debug(
            f"Initialized adaptive rate limiter for {platform} | "
            f"base_delay={self.config.base_delay_ms}ms | "
            f"rpm={self.config.requests_per_minute}"
        )

    @property
    def current_delay_seconds(self) -> float:
        """Get current delay in seconds."""
        return self._current_delay_ms / 1000

    @property
    def stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "platform": self.platform,
            "current_delay_ms": self._current_delay_ms,
            "total_requests": self._total_requests,
            "total_rate_limits": self._total_rate_limits,
            "consecutive_successes": self._consecutive_successes,
            "consecutive_errors": self._consecutive_errors,
            "requests_in_window": len(self._request_times),
        }

    def _clean_old_requests(self):
        """Remove requests older than 1 minute from tracking."""
        cutoff = time.time() - 60
        self._request_times = [t for t in self._request_times if t > cutoff]

    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period after rate limit."""
        if self._last_rate_limit_time is None:
            return False

        elapsed = time.time() - self._last_rate_limit_time
        return elapsed < self.config.cooldown_seconds

    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds."""
        if self._last_rate_limit_time is None:
            return 0

        elapsed = time.time() - self._last_rate_limit_time
        remaining = self.config.cooldown_seconds - elapsed
        return max(0, remaining)

    def wait(self) -> float:
        """
        Wait the appropriate amount of time before next request.

        Returns:
            Actual delay in seconds
        """
        self._clean_old_requests()

        # Check cooldown
        if self._is_in_cooldown():
            remaining = self._get_cooldown_remaining()
            logger.warning(
                f"COOLDOWN | {self.platform} | {remaining:.1f}s remaining"
            )
            time.sleep(remaining)

        # Check burst limit
        if len(self._request_times) >= self.config.burst_limit:
            burst_delay = 1.0  # Wait at least 1 second between bursts
            logger.debug(f"BURST LIMIT | waiting {burst_delay}s")
            time.sleep(burst_delay)

        # Check requests per minute limit
        if len(self._request_times) >= self.config.requests_per_minute:
            oldest = min(self._request_times)
            wait_until = oldest + 60
            delay_needed = wait_until - time.time()
            if delay_needed > 0:
                logger.info(
                    f"RPM LIMIT | {self.platform} | waiting {delay_needed:.1f}s"
                )
                time.sleep(delay_needed)
                self._clean_old_requests()

        # Apply current delay with jitter
        jitter = random.uniform(-0.1, 0.1) * self._current_delay_ms
        actual_delay_ms = self._current_delay_ms + jitter
        actual_delay_s = actual_delay_ms / 1000

        if actual_delay_s > 0.1:  # Only log if delay is meaningful
            logger.debug(
                f"RATE LIMIT WAIT | {self.platform} | {actual_delay_ms:.0f}ms"
            )

        time.sleep(actual_delay_s)

        # Record this request
        self._request_times.append(time.time())
        self._total_requests += 1

        return actual_delay_s

    def record_success(self):
        """Record a successful request and potentially decrease delay."""
        self._consecutive_successes += 1
        self._consecutive_errors = 0

        # After enough successes, try reducing delay
        if self._consecutive_successes >= self.config.success_threshold:
            new_delay = int(self._current_delay_ms * self.config.decrease_factor)
            new_delay = max(new_delay, self.config.min_delay_ms)

            if new_delay < self._current_delay_ms:
                old_delay = self._current_delay_ms
                self._current_delay_ms = new_delay
                self._consecutive_successes = 0
                logger.debug(
                    f"DELAY DECREASED | {self.platform} | "
                    f"{old_delay}ms -> {new_delay}ms"
                )

    def record_rate_limit(self):
        """Record a rate limit and increase delay."""
        self._consecutive_errors += 1
        self._consecutive_successes = 0
        self._total_rate_limits += 1
        self._last_rate_limit_time = time.time()

        # Increase delay
        old_delay = self._current_delay_ms
        self._current_delay_ms = int(
            self._current_delay_ms * self.config.increase_factor
        )
        self._current_delay_ms = min(
            self._current_delay_ms,
            self.config.max_delay_ms
        )

        logger.warning(
            f"RATE LIMIT DETECTED | {self.platform} | "
            f"delay increased: {old_delay}ms -> {self._current_delay_ms}ms | "
            f"cooldown: {self.config.cooldown_seconds}s"
        )

    def record_error(self):
        """Record a non-rate-limit error."""
        self._consecutive_errors += 1
        self._consecutive_successes = 0

        # Slight delay increase on errors
        if self._consecutive_errors > 1:
            self._current_delay_ms = min(
                int(self._current_delay_ms * 1.2),
                self.config.max_delay_ms
            )

    def should_continue(self) -> bool:
        """
        Check if we should continue after errors.

        Returns:
            True if under max consecutive errors
        """
        return self._consecutive_errors < self.config.max_consecutive_errors

    def reset(self):
        """Reset limiter state (e.g., after long pause)."""
        self._current_delay_ms = self.config.base_delay_ms
        self._consecutive_successes = 0
        self._consecutive_errors = 0
        self._request_times = []
        self._last_rate_limit_time = None
        logger.debug(f"RATE LIMITER RESET | {self.platform}")


def get_platform_config(platform: str) -> PlatformRateLimitConfig:
    """
    Get rate limit configuration for a platform.

    Args:
        platform: Platform name

    Returns:
        Platform-specific configuration
    """
    return PLATFORM_CONFIGS.get(
        platform.lower(),
        PlatformRateLimitConfig()
    )


class RateLimitDetector(ABC):
    """
    Abstract base class for platform-specific rate limit detection.

    Each platform has different indicators for rate limiting.
    Subclasses implement platform-specific detection logic.
    """

    @abstractmethod
    def is_rate_limited(self, page: Page) -> bool:
        """
        Check if the current page indicates rate limiting.

        Args:
            page: Playwright page to check

        Returns:
            True if rate limited, False otherwise
        """
        pass

    @abstractmethod
    def get_indicators(self) -> List[str]:
        """
        Get list of rate limit indicators for this platform.

        Returns:
            List of text indicators that suggest rate limiting
        """
        pass


class FacebookRateLimitDetector(RateLimitDetector):
    """Rate limit detector for Facebook."""

    INDICATORS = [
        "you're temporarily blocked",
        "temporarily blocked",
        "try again later",
        "slow down",
        "too many requests",
        "rate limit",
        # Spanish
        "estás bloqueado temporalmente",
        "intenta de nuevo más tarde",
        "demasiadas solicitudes",
    ]

    CHECKPOINT_URLS = [
        "/checkpoint/",
        "/accounts/suspended",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        """Check if Facebook is rate limiting."""
        try:
            # Check URL for checkpoint
            current_url = page.url
            for url_pattern in self.CHECKPOINT_URLS:
                if url_pattern in current_url:
                    logger.warning(f"RATE LIMIT | checkpoint URL detected: {current_url}")
                    return True

            # Check page content
            page_content = page.content().lower()
            for indicator in self.INDICATORS:
                if indicator in page_content:
                    logger.warning(f"RATE LIMIT | indicator detected: {indicator}")
                    return True

            return False
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False

    def get_indicators(self) -> List[str]:
        return self.INDICATORS


class InstagramRateLimitDetector(RateLimitDetector):
    """Rate limit detector for Instagram."""

    INDICATORS = [
        "try again later",
        "please wait",
        "action blocked",
        "temporarily blocked",
        "too many requests",
        "we limit how often",
        "suspicious activity",
    ]

    BLOCKED_URLS = [
        "/challenge/",
        "/accounts/suspended",
        "/accounts/consent",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        """Check if Instagram is rate limiting."""
        try:
            # Check URL patterns
            current_url = page.url
            for url_pattern in self.BLOCKED_URLS:
                if url_pattern in current_url:
                    logger.warning(f"RATE LIMIT | blocked URL detected: {current_url}")
                    return True

            # Check page text content
            page_text = page.evaluate("document.body?.innerText || ''").lower()
            for indicator in self.INDICATORS:
                if indicator in page_text:
                    logger.warning(f"RATE LIMIT | indicator detected: {indicator}")
                    return True

            return False
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False

    def get_indicators(self) -> List[str]:
        return self.INDICATORS


class TwitterRateLimitDetector(RateLimitDetector):
    """Rate limit detector for Twitter/X."""

    INDICATORS = [
        "rate limit exceeded",
        "try again later",
        "something went wrong",
        "over capacity",
        "too many requests",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        """Check if Twitter is rate limiting."""
        try:
            page_text = page.evaluate("document.body?.innerText || ''").lower()
            for indicator in self.INDICATORS:
                if indicator in page_text:
                    logger.warning(f"RATE LIMIT | indicator detected: {indicator}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False

    def get_indicators(self) -> List[str]:
        return self.INDICATORS


class LinkedInRateLimitDetector(RateLimitDetector):
    """Rate limit detector for LinkedIn."""

    INDICATORS = [
        "unusual activity",
        "security verification",
        "too many requests",
        "please try again",
        "temporarily restricted",
    ]

    BLOCKED_URLS = [
        "/checkpoint/",
        "/authwall",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        """Check if LinkedIn is rate limiting."""
        try:
            # Check URL patterns
            current_url = page.url
            for url_pattern in self.BLOCKED_URLS:
                if url_pattern in current_url:
                    logger.warning(f"RATE LIMIT | blocked URL detected: {current_url}")
                    return True

            page_text = page.evaluate("document.body?.innerText || ''").lower()
            for indicator in self.INDICATORS:
                if indicator in page_text:
                    logger.warning(f"RATE LIMIT | indicator detected: {indicator}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False

    def get_indicators(self) -> List[str]:
        return self.INDICATORS


class GoogleRateLimitDetector(RateLimitDetector):
    """Rate limit detector for Google Maps/Business."""

    INDICATORS = [
        "unusual traffic",
        "automated queries",
        "try again later",
        "blocked",
        "captcha",
        "verify you're not a robot",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        """Check if Google is rate limiting."""
        try:
            # Check for CAPTCHA iframe
            captcha_present = page.locator('iframe[title*="recaptcha"]').count() > 0
            if captcha_present:
                logger.warning("RATE LIMIT | CAPTCHA detected")
                return True

            page_text = page.evaluate("document.body?.innerText || ''").lower()
            for indicator in self.INDICATORS:
                if indicator in page_text:
                    logger.warning(f"RATE LIMIT | indicator detected: {indicator}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False

    def get_indicators(self) -> List[str]:
        return self.INDICATORS


class RateLimitHandler:
    """
    Handles rate limit responses with exponential backoff.

    Provides consistent rate limit handling across all scrapers.
    """

    def __init__(
        self,
        base_delay: float = TIMEOUTS.RETRY_BASE / 1000,
        max_delay: float = TIMEOUTS.RETRY_MAX / 1000,
        max_retries: int = 3
    ):
        """
        Initialize rate limit handler.

        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            max_retries: Maximum retry attempts
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self._consecutive_errors = 0

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff time with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Backoff time in seconds
        """
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter (+-25%)
        jitter = delay * random.uniform(-0.25, 0.25)
        return delay + jitter

    def wait_with_backoff(self, attempt: int) -> None:
        """
        Wait with exponential backoff.

        Args:
            attempt: Current attempt number
        """
        delay = self.calculate_backoff(attempt)
        logger.info(f"RETRY BACKOFF | waiting {delay:.1f}s | attempt {attempt + 1}")
        time.sleep(delay)

    def handle_rate_limit(self, rotate_proxy_callback: Optional[Callable[[], None]] = None) -> None:
        """
        Handle a rate limit with extended wait and optional proxy rotation.

        Args:
            rotate_proxy_callback: Optional callback to rotate proxy
        """
        self._consecutive_errors += 1

        # Try rotating proxy first
        if rotate_proxy_callback:
            logger.info("RATE LIMIT RECOVERY | rotating proxy")
            rotate_proxy_callback()

        # Calculate wait time
        backoff_time = self.calculate_backoff(self._consecutive_errors)
        extra_wait = random.uniform(
            TIMEOUTS.RATE_LIMIT_EXTRA_MIN / 1000,
            TIMEOUTS.RATE_LIMIT_EXTRA_MAX / 1000
        )
        total_wait = backoff_time + extra_wait

        logger.warning(
            f"RATE LIMIT WAIT | total={total_wait/60:.1f}min | "
            f"backoff={backoff_time:.1f}s | extra={extra_wait:.1f}s"
        )
        time.sleep(total_wait)

    def reset(self) -> None:
        """Reset consecutive error counter after successful operation."""
        self._consecutive_errors = 0

    def should_retry(self) -> bool:
        """
        Check if we should retry after an error.

        Returns:
            True if under max retries
        """
        return self._consecutive_errors < self.max_retries


# Factory function for getting platform-specific detector
def get_rate_limit_detector(platform: str) -> RateLimitDetector:
    """
    Get the appropriate rate limit detector for a platform.

    Args:
        platform: Platform name (facebook, instagram, twitter, linkedin)

    Returns:
        Platform-specific RateLimitDetector instance

    Raises:
        ValueError: If platform is not supported
    """
    detectors = {
        "facebook": FacebookRateLimitDetector,
        "instagram": InstagramRateLimitDetector,
        "twitter": TwitterRateLimitDetector,
        "linkedin": LinkedInRateLimitDetector,
        "google": GoogleRateLimitDetector,
    }

    platform_lower = platform.lower()
    if platform_lower not in detectors:
        raise ValueError(f"Unknown platform: {platform}")

    return detectors[platform_lower]()
