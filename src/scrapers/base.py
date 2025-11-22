"""Base scraper class with common functionality."""

import json
import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Iterator, Optional, Dict, Any, List, Set, Callable, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..core.models import (
    Platform,
    Comment,
    Post,
    Profile,
    ExtractionResult,
    Author,
)
from ..core.exceptions import (
    ScraperError,
    RateLimitError,
)
from ..utils.parsing import parse_datetime_flexible
from .shared.constants import USER_AGENTS, ACCEPT_LANGUAGES, TIMEOUTS, RETRY_CONFIG
from .shared.rate_limiting import RateLimitHandler, RateLimitDetector

logger = logging.getLogger(__name__)


# Type alias for progress callback
ProgressCallback = Callable[[int, int, str], None]  # (current, total, message)


class BaseScraper(ABC):
    """Base class for all platform scrapers."""

    platform: Platform
    requests_per_minute: int = 5  # Very slow for human-like behavior
    max_retries: int = 3
    retry_delay: int = 5

    # Human-like delay settings (in seconds) - Fast mode
    min_delay: float = 0.5   # Minimum delay between requests
    max_delay: float = 1.0   # Maximum delay between requests

    # Periodic breaks to simulate human behavior
    long_pause_interval: int = 20   # Take a longer pause every N requests
    long_pause_min: float = 3.0     # Minimum long pause
    long_pause_max: float = 5.0     # Maximum long pause

    # Very long breaks to avoid detection
    very_long_pause_interval: int = 100  # Take a very long break every N requests
    very_long_pause_min: float = 10.0    # 10 seconds
    very_long_pause_max: float = 20.0    # 20 seconds

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._last_request_time = 0.0
        self._request_count = 0
        self._session_start = time.time()
        self._consecutive_errors = 0
        self._current_user_agent = random.choice(USER_AGENTS)
        self._current_accept_language = random.choice(ACCEPT_LANGUAGES)

        # Progress callback (optional)
        self._progress_callback: Optional[ProgressCallback] = None

        # Rate limit handler
        self._rate_limit_handler = RateLimitHandler(
            base_delay=self.retry_delay,
            max_delay=60.0,
            max_retries=self.max_retries
        )

        # Proxy configuration (optional)
        self._proxies: List[str] = config.get("proxies", []) if config else []
        self._current_proxy: Optional[str] = None
        if self._proxies:
            self._current_proxy = random.choice(self._proxies)
            logger.info(f"Proxy configured: {self._mask_proxy(self._current_proxy)}")

        logger.info(
            f"Initialized {self.__class__.__name__} | "
            f"platform={self.platform.value} | "
            f"rate_limit={self.requests_per_minute}/min | "
            f"delay={self.min_delay}-{self.max_delay}s"
        )

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """
        Set a callback function for progress updates.

        Args:
            callback: Function that receives (current, total, message)
        """
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Report extraction progress via callback.

        Args:
            current: Current progress count
            total: Total expected count
            message: Optional status message
        """
        if self._progress_callback:
            try:
                self._progress_callback(current, total, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> bool:
        """Context manager exit with cleanup."""
        self.close()
        return False

    def close(self) -> None:
        """
        Clean up resources. Override in subclasses.

        Subclasses should call super().close() after their cleanup.
        """
        logger.debug(f"BaseScraper.close() called for {self.__class__.__name__}")

    def _mask_proxy(self, proxy: str) -> str:
        """Mask proxy URL for logging (hide credentials)."""
        if "@" in proxy:
            # Has credentials
            parts = proxy.split("@")
            return f"***@{parts[-1]}"
        return proxy

    def get_random_headers(self) -> Dict[str, str]:
        """
        Get randomized headers to mimic real browser behavior.

        Returns:
            Dictionary of HTTP headers
        """
        # Occasionally rotate user agent (every ~10 requests)
        if random.random() < 0.1:
            self._current_user_agent = random.choice(USER_AGENTS)
            logger.debug("Rotated User-Agent")

        headers = {
            "User-Agent": self._current_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": self._current_accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add DNT header randomly (some users have it)
        if random.random() < 0.3:
            headers["DNT"] = "1"

        return headers

    def get_current_proxy(self) -> Optional[str]:
        """Get current proxy URL."""
        return self._current_proxy

    def rotate_proxy(self) -> None:
        """Rotate to a different proxy."""
        if len(self._proxies) > 1:
            available = [p for p in self._proxies if p != self._current_proxy]
            self._current_proxy = random.choice(available)
            logger.info(f"Rotated to proxy: {self._mask_proxy(self._current_proxy)}")
        elif self._proxies:
            logger.warning("Only one proxy available, cannot rotate")

    @abstractmethod
    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int,
        known_post_ids: Optional[Set[str]] = None
    ) -> Iterator[ExtractionResult]:
        pass

    @abstractmethod
    def _scrape_profile(self, account_id: str) -> Profile:
        pass

    def get_posts_with_comments(
        self,
        account_id: str,
        since_date: Optional[datetime] = None,
        max_posts: int = 100,
        known_post_ids: Optional[Set[str]] = None
    ) -> Iterator[ExtractionResult]:
        logger.info(
            f"EXTRACTION START | account={account_id} | "
            f"platform={self.platform.value} | "
            f"since={since_date.strftime('%Y-%m-%d') if since_date else 'None'} | "
            f"max_posts={max_posts}"
        )
        extraction_start = time.time()
        posts_extracted = 0
        total_comments = 0

        try:
            for result in self._scrape_posts(account_id, since_date, max_posts, known_post_ids):
                self._human_delay()
                self._consecutive_errors = 0  # Reset on success
                posts_extracted += 1
                comments_count = len(result.comments) if result.comments else 0
                total_comments += comments_count
                logger.debug(
                    f"Yielded post {posts_extracted}/{max_posts} | "
                    f"post_id={result.post.platform_id} | "
                    f"comments={comments_count}"
                )
                yield result

            elapsed = time.time() - extraction_start
            logger.info(
                f"EXTRACTION COMPLETE | account={account_id} | "
                f"posts={posts_extracted} | comments={total_comments} | "
                f"duration={elapsed:.1f}s | "
                f"avg_time={elapsed/posts_extracted:.1f}s/post" if posts_extracted > 0 else f"EXTRACTION COMPLETE | account={account_id} | posts=0 | duration={elapsed:.1f}s"
            )

        except RateLimitError as e:
            logger.warning(
                f"RATE LIMITED | platform={self.platform.value} | "
                f"account={account_id} | error={e}"
            )
            self._handle_rate_limit()
            raise
        except Exception as e:
            self._consecutive_errors += 1
            logger.error(
                f"EXTRACTION ERROR | platform={self.platform.value} | "
                f"account={account_id} | "
                f"error_type={type(e).__name__} | error={e}"
            )

            # Try to recover with exponential backoff
            if self._consecutive_errors < self.max_retries:
                backoff_time = self._calculate_backoff()
                logger.info(
                    f"BACKOFF | duration={backoff_time:.1f}s | "
                    f"attempt={self._consecutive_errors}/{self.max_retries}"
                )
                time.sleep(backoff_time)

            raise ScraperError(f"Failed to scrape {account_id}", platform=self.platform.value, account_id=account_id, original_error=e)

    def _handle_rate_limit(self) -> None:
        """Handle rate limit with exponential backoff and proxy rotation."""
        self._consecutive_errors += 1

        # Try rotating proxy first
        if self._proxies and len(self._proxies) > 1:
            logger.info("RATE LIMIT RECOVERY | action=rotating_proxy")
            self.rotate_proxy()

        # Calculate backoff time with exponential increase
        backoff_time = self._calculate_backoff()

        # For rate limits, add extra wait time
        rate_limit_extra = random.uniform(60, 180)  # 1-3 minutes extra
        total_wait = backoff_time + rate_limit_extra

        logger.warning(
            f"RATE LIMIT WAIT | total_wait={total_wait/60:.1f}min | "
            f"backoff={backoff_time:.1f}s | extra={rate_limit_extra:.1f}s"
        )
        time.sleep(total_wait)

    def _calculate_backoff(self) -> float:
        """
        Calculate exponential backoff time with jitter.

        Returns:
            Backoff time in seconds
        """
        # Exponential backoff: 2^n * base_delay + random jitter
        base_delay = self.retry_delay
        exponential = min(2 ** self._consecutive_errors, 32)  # Cap at 32x

        # Add random jitter (+-25%)
        jitter = random.uniform(0.75, 1.25)

        backoff = base_delay * exponential * jitter
        return backoff

    def _wait_with_backoff(self, attempt: int, base_delay: float = 2.0, max_delay: float = 60.0) -> None:
        """
        Wait with exponential backoff plus jitter.

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        delay = min(base_delay * (2 ** attempt), max_delay)
        # Add jitter (±25%)
        jitter = delay * random.uniform(-0.25, 0.25)
        actual_delay = delay + jitter
        logger.info(f"RETRY | waiting {actual_delay:.1f}s before attempt {attempt + 2}")
        time.sleep(actual_delay)

    def _navigate_with_retry(
        self,
        page: Any,
        url: str,
        content_selectors: List[str],
        rate_limit_detector: Optional[RateLimitDetector] = None,
        max_retries: int = 3,
        wait_after_load: int = 1500
    ) -> bool:
        """
        Navigate to URL with retry and rate limit detection.

        This is a generic navigation method that can be used by all scrapers.

        Args:
            page: Playwright page object
            url: URL to navigate to
            content_selectors: List of selectors to wait for (comma-separated in selector string)
            rate_limit_detector: Optional rate limit detector for the platform
            max_retries: Maximum number of retry attempts
            wait_after_load: Milliseconds to wait after page loads

        Returns:
            True if navigation succeeded, False otherwise

        Raises:
            RateLimitError: If rate limited and all retries exhausted
        """
        selector_string = ", ".join(content_selectors)

        for attempt in range(max_retries):
            try:
                page.goto(url, wait_until="domcontentloaded")

                # Wait for content to load
                try:
                    page.wait_for_selector(selector_string, timeout=10000)
                except (TimeoutError, Exception) as e:
                    # Continue even if selector not found - may be TimeoutError or other Playwright exceptions
                    logger.debug(f"Selector wait timed out or failed: {type(e).__name__}")

                page.wait_for_timeout(wait_after_load)

                # Check for rate limiting if detector provided
                if rate_limit_detector and rate_limit_detector.is_rate_limited(page):
                    if attempt < max_retries - 1:
                        self._wait_with_backoff(attempt)
                        continue
                    else:
                        raise RateLimitError(
                            f"{self.platform.value.title()} is rate limiting requests",
                            platform=self.platform.value
                        )

                return True

            except RateLimitError:
                raise
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    self._wait_with_backoff(attempt)
                else:
                    return False

        return False

    def _get_checkpoint_path(self, account_id: str) -> Path:
        """
        Get checkpoint file path for an account.

        Args:
            account_id: Account username/ID

        Returns:
            Path to checkpoint file
        """
        checkpoint_dir = Path(self.config.get("data_dir", "data")) / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / f"{self.platform.value}_{account_id}_checkpoint.json"

    def _load_checkpoint(self, account_id: str) -> Set[str]:
        """
        Load checkpoint data (processed post IDs).

        Args:
            account_id: Account username/ID

        Returns:
            Set of already processed post IDs
        """
        checkpoint_path = self._get_checkpoint_path(account_id)
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r') as f:
                    data = json.load(f)
                    processed_ids = set(data.get("processed_post_ids", []))
                    logger.info(f"CHECKPOINT | loaded {len(processed_ids)} processed posts from {checkpoint_path}")
                    return processed_ids
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return set()

    def _save_checkpoint(self, account_id: str, processed_post_ids: Set[str]) -> None:
        """
        Save checkpoint data.

        Args:
            account_id: Account username/ID
            processed_post_ids: Set of processed post IDs
        """
        checkpoint_path = self._get_checkpoint_path(account_id)
        try:
            data = {
                "account_id": account_id,
                "platform": self.platform.value,
                "processed_post_ids": list(processed_post_ids),
                "last_updated": datetime.now().isoformat(),
                "count": len(processed_post_ids)
            }
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"CHECKPOINT | saved {len(processed_post_ids)} processed posts")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def _clear_checkpoint(self, account_id: str) -> None:
        """
        Clear checkpoint file after successful completion.

        Args:
            account_id: Account username/ID
        """
        checkpoint_path = self._get_checkpoint_path(account_id)
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                logger.info("CHECKPOINT | cleared checkpoint file")
            except Exception as e:
                logger.warning(f"Failed to clear checkpoint: {e}")

    def _iterate_posts(
        self,
        post_links: List[str],
        max_posts: int,
        known_post_ids: Set[str],
        extract_fn: Callable[[str], Optional[ExtractionResult]],
        page: Any,
        check_rate_limit_fn: Callable[[], bool],
        human_delay_fn: Optional[Callable[[int, int], None]] = None,
        max_failures: int = RETRY_CONFIG.MAX_CONSECUTIVE_FAILURES,
        account_id: Optional[str] = None,
        checkpoint_ids: Optional[Set[str]] = None,
        use_navigate_method: bool = False,
        navigate_fn: Optional[Callable[[str], bool]] = None
    ) -> Iterator[ExtractionResult]:
        """
        Unified post iteration with navigation retry and failure tracking.

        This consolidates the common post iteration pattern found across all scrapers.

        Args:
            post_links: List of post URLs to iterate over
            max_posts: Maximum number of posts to scrape
            known_post_ids: Set of post IDs to skip (already extracted)
            extract_fn: Function that extracts post data, returns ExtractionResult or None
            page: Playwright page object for navigation
            check_rate_limit_fn: Function to check if rate limited
            human_delay_fn: Optional function for human-like delays between posts
            max_failures: Maximum consecutive failures before stopping
            account_id: Optional account ID for checkpoint saving
            checkpoint_ids: Optional existing checkpoint IDs to merge with
            use_navigate_method: Use navigate_fn instead of direct page.goto
            navigate_fn: Custom navigation function that returns bool

        Yields:
            ExtractionResult objects with post and comments
        """
        posts_scraped = 0
        posts_skipped = 0
        consecutive_failures = 0
        known_ids = known_post_ids or set()
        processed_this_session: Set[str] = set()
        checkpoint_base = checkpoint_ids or set()

        for post_url in post_links:
            if posts_scraped >= max_posts:
                break

            # Navigation with retry logic
            if use_navigate_method and navigate_fn:
                # Use custom navigation function
                nav_success = navigate_fn(post_url)
            else:
                # Default navigation with retry
                nav_success = False
                for attempt in range(RETRY_CONFIG.NAV_RETRIES):
                    try:
                        page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(TIMEOUTS.CONTENT_LOAD)
                        nav_success = True
                        break
                    except Exception as nav_error:
                        logger.warning(
                            f"Navigation attempt {attempt + 1}/{RETRY_CONFIG.NAV_RETRIES} "
                            f"failed for {post_url[:60]}...: {nav_error}"
                        )
                        if attempt < RETRY_CONFIG.NAV_RETRIES - 1:
                            page.wait_for_timeout(TIMEOUTS.MEDIUM_WAIT)

            if not nav_success:
                logger.warning(f"Failed to navigate to post after retries: {post_url[:60]}...")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.warning("Too many navigation failures, stopping")
                    break
                continue

            # Check for rate limiting after navigation
            if check_rate_limit_fn():
                logger.warning("Rate limit detected, waiting before retry...")
                page.wait_for_timeout(TIMEOUTS.RATE_LIMIT_WAIT)
                if check_rate_limit_fn():
                    logger.error("Still rate limited after waiting, stopping extraction")
                    break

            try:
                # Call the extraction function
                result = extract_fn(post_url)

                if result is None:
                    # Extraction returned None (e.g., post in known_ids)
                    posts_skipped += 1
                    continue

                # Check if post should be skipped
                if result.post.platform_id in known_ids:
                    posts_skipped += 1
                    logger.debug(f"Skipping existing post: {result.post.platform_id}")
                    continue

                yield result
                posts_scraped += 1
                consecutive_failures = 0
                processed_this_session.add(result.post.platform_id)

                logger.info(
                    f"SCRAPED | {posts_scraped}/{max_posts} | "
                    f"post_id={result.post.platform_id} | "
                    f"comments={len(result.comments) if result.comments else 0}"
                )

                # Save checkpoint periodically
                if account_id and posts_scraped % RETRY_CONFIG.CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(account_id, checkpoint_base | processed_this_session)

                # Extended break check
                if self.should_take_extended_break():
                    self.take_extended_break()

            except Exception as e:
                logger.warning(f"Error extracting post from {post_url}: {e}")
                consecutive_failures += 1

            if consecutive_failures >= max_failures:
                logger.warning("Too many failures, stopping")
                break

            # Human-like delay between posts
            if human_delay_fn:
                human_delay_fn(TIMEOUTS.HUMAN_MIN * 2, TIMEOUTS.HUMAN_MAX * 2)

        # Clear checkpoint on successful completion
        if account_id and consecutive_failures < max_failures:
            self._clear_checkpoint(account_id)

        logger.info(
            f"ITERATION COMPLETE | posts={posts_scraped} | skipped={posts_skipped}"
        )

    def get_profile(self, account_id: str) -> Profile:
        logger.info(f"PROFILE FETCH START | account={account_id} | platform={self.platform.value}")
        self._human_delay()
        try:
            profile = self._scrape_profile(account_id)
            logger.info(
                f"PROFILE FETCH COMPLETE | account={account_id} | "
                f"followers={profile.followers_count} | posts={profile.posts_count}"
            )
            return profile
        except Exception as e:
            logger.error(
                f"PROFILE FETCH ERROR | account={account_id} | "
                f"error_type={type(e).__name__} | error={e}"
            )
            raise ScraperError(f"Failed to get profile {account_id}", platform=self.platform.value, account_id=account_id, original_error=e)

    def get_comments(self, post_id: str, max_comments: int = 1000) -> Iterator[Comment]:
        raise NotImplementedError(f"{self.__class__.__name__} does not support get_comments directly")

    def _human_delay(self) -> None:
        """
        Apply human-like random delays between requests.

        Simulates natural browsing patterns:
        - Random delays between each request
        - Longer pauses periodically (like checking phone)
        - Very long pauses occasionally (like taking a break)
        """
        self._request_count += 1

        # Very long break every N requests (simulates taking a real break)
        if self._request_count % self.very_long_pause_interval == 0:
            pause_time = random.uniform(self.very_long_pause_min, self.very_long_pause_max)
            logger.info(
                f"LONG BREAK | duration={pause_time/60:.1f}min | "
                f"request_count={self._request_count} | reason=anti_detection"
            )
            time.sleep(pause_time)

        # Medium break every N requests (simulates distraction)
        elif self._request_count % self.long_pause_interval == 0:
            pause_time = random.uniform(self.long_pause_min, self.long_pause_max)
            logger.info(
                f"SHORT BREAK | duration={pause_time:.1f}s | "
                f"request_count={self._request_count}"
            )
            time.sleep(pause_time)

        else:
            # Normal random delay with some variation
            # Sometimes faster, sometimes slower (like real browsing)
            if random.random() < 0.2:  # 20% chance of quick action
                delay = random.uniform(self.min_delay * 0.5, self.min_delay)
                delay_type = "quick"
            elif random.random() < 0.1:  # 10% chance of long pause
                delay = random.uniform(self.max_delay, self.max_delay * 1.5)
                delay_type = "long"
            else:  # Normal delay
                delay = random.uniform(self.min_delay, self.max_delay)
                delay_type = "normal"

            logger.debug(f"DELAY | duration={delay:.1f}s | type={delay_type}")
            time.sleep(delay)

        self._last_request_time = time.time()

    def _rate_limit(self) -> None:
        """Legacy rate limiting method."""
        min_interval = 60.0 / self.requests_per_minute
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()
        self._request_count += 1

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current scraping session.

        Returns:
            Dictionary with session statistics
        """
        elapsed = time.time() - self._session_start
        return {
            "requests": self._request_count,
            "elapsed_minutes": elapsed / 60,
            "requests_per_minute": self._request_count / (elapsed / 60) if elapsed > 0 else 0,
            "consecutive_errors": self._consecutive_errors,
            "current_user_agent": self._current_user_agent[:50] + "..." if len(self._current_user_agent) > 50 else self._current_user_agent,
            "using_proxy": self._current_proxy is not None,
        }

    def should_take_extended_break(self) -> bool:
        """
        Check if we should take an extended break based on session duration.

        Human-like behavior: After scraping for a while, take a longer break
        as if stepping away from the computer.

        Returns:
            True if should take an extended break
        """
        elapsed_minutes = (time.time() - self._session_start) / 60

        # Take a 5-15 minute break every hour of scraping
        if elapsed_minutes > 60 and self._request_count > 0:
            # Check if we've taken enough breaks relative to time
            expected_breaks = int(elapsed_minutes / 60)
            actual_long_breaks = self._request_count // self.very_long_pause_interval

            if actual_long_breaks < expected_breaks:
                return True

        return False

    def take_extended_break(self) -> None:
        """Take an extended break to simulate real human behavior."""
        break_time = random.uniform(5 * 60, 15 * 60)  # 5-15 minutes
        logger.info(
            f"EXTENDED BREAK | duration={break_time/60:.1f}min | "
            f"reason=session_duration | resetting_session=true"
        )
        time.sleep(break_time)
        # Reset session tracking after break
        self._session_start = time.time()
        logger.debug("Session timer reset after extended break")

    def is_good_time_to_scrape(self) -> bool:
        """
        Check if current time is a reasonable time for browsing.

        Social media usage patterns vary by time of day.
        Early morning (2-6 AM) is suspicious for constant scraping.

        Returns:
            True if it's a reasonable time to scrape
        """
        current_hour = datetime.now().hour

        # Avoid heavy scraping during suspicious hours (2 AM - 6 AM)
        if 2 <= current_hour < 6:
            return False

        return True

    def wait_for_good_time(self) -> None:
        """Wait until a reasonable time to resume scraping."""
        while not self.is_good_time_to_scrape():
            # Calculate time until 6 AM
            now = datetime.now()
            if now.hour >= 2:
                # Wait until 6 AM
                wait_until = now.replace(hour=6, minute=0, second=0, microsecond=0)
                if wait_until <= now:
                    wait_until = wait_until.replace(day=now.day + 1)
            else:
                # Already past midnight but before 2 AM, we're fine
                break

            wait_seconds = (wait_until - now).total_seconds()
            logger.info(
                f"QUIET HOURS PAUSE | resume_at=06:00 | "
                f"wait_time={wait_seconds/3600:.1f}h | "
                f"current_hour={now.hour}"
            )
            time.sleep(min(wait_seconds, 3600))  # Check every hour

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string using unified parser."""
        return parse_datetime_flexible(timestamp_str)

    def _create_author(self, raw_data: Dict[str, Any]) -> Author:
        return Author(
            platform_id=raw_data.get("id") or raw_data.get("user_id"),
            username=raw_data.get("username") or raw_data.get("screen_name"),
            display_name=raw_data.get("name") or raw_data.get("full_name"),
            profile_url=raw_data.get("profile_url") or raw_data.get("url"),
            profile_image=raw_data.get("profile_image") or raw_data.get("avatar"),
            is_verified=raw_data.get("is_verified", False),
        )

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = text.replace("\x00", "")
        text = " ".join(text.split())
        return text.strip()

    def _create_comment_objects(
        self,
        raw_comments: List[Dict[str, Any]],
        post_id: str
    ) -> List[Comment]:
        """
        Convert raw comment data to Comment objects.

        Args:
            raw_comments: List of raw comment dictionaries
            post_id: Parent post ID

        Returns:
            List of Comment objects
        """
        comments = []

        for raw in raw_comments:
            comment = Comment(
                platform=self.platform,
                platform_id=raw.get("id", f"{post_id}_unknown"),
                post_id=post_id,
                text=raw.get("text", ""),
                author=Author(
                    platform=self.platform,
                    platform_id=raw.get("author", ""),
                    username=raw.get("author", ""),
                    display_name=raw.get("author", ""),
                    profile_url=raw.get("author_url", ""),
                ),
                published_at=raw.get("published_at"),
                likes=raw.get("likes", 0),
                parent_id=raw.get("parent_id"),
                replies_count=raw.get("replies_count", 0),
                raw_data={
                    "depth": raw.get("depth", 1),
                },
            )
            comments.append(comment)

        return comments
