"""Google Maps/Business Scraper using Page Object Model architecture."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Dict, Any, Set

from playwright.sync_api import Page

from ...core.models import (
    Platform,
    Post,
    Profile,
    ExtractionResult,
)
from ...core.exceptions import (
    AccountNotFoundError,
    RateLimitError,
)
from ..base import BaseScraper
from ..shared.browser_manager import BrowserManager, BrowserConfig
from ..shared.rate_limiting import GoogleRateLimitDetector
from ..shared.constants import TIMEOUTS
from .pages import BusinessPage, ReviewsSection
from .selectors import Selectors

logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """
    Google Maps/Business scraper using Page Object Model pattern.

    This scraper extracts reviews from Google Maps business listings.
    Note: Google doesn't require authentication for viewing reviews,
    but heavy scraping may trigger rate limits or CAPTCHAs.
    """

    platform = Platform.GOOGLE

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Google scraper.

        Args:
            config: Configuration dictionary with settings
        """
        super().__init__(config)

        # Browser settings
        browser_config = config.get("browser", {})
        self._headless = browser_config.get("headless", config.get("headless", False))
        self._browser_profile = browser_config.get("profile_dir") or config.get("browser_profile")

        # Browser manager (handles lifecycle)
        self._browser_manager: Optional[BrowserManager] = None
        self._page: Optional[Page] = None

        # Page objects (initialized after browser)
        self._business_page: Optional[BusinessPage] = None
        self._reviews_section: Optional[ReviewsSection] = None

        # Rate limit detector
        self._rate_limit_detector = GoogleRateLimitDetector()

        # Initialize browser
        self._init_browser()

    def _init_browser(self) -> None:
        """Initialize browser using BrowserManager."""
        browser_config = BrowserConfig(
            headless=self._headless,
            profile_dir=self._browser_profile,
            storage_state=None,  # Google doesn't require auth
            proxy=self._current_proxy,
        )

        self._browser_manager = BrowserManager(browser_config, "google")
        self._page = self._browser_manager.page

        # Initialize page objects
        self._business_page = BusinessPage(self._page)
        self._reviews_section = ReviewsSection(self._page)

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser_manager:
            self._browser_manager.close()
            self._browser_manager = None
        super().close()

    def _check_rate_limit(self) -> bool:
        """
        Check if Google is rate limiting us.

        Returns:
            True if rate limited, False otherwise
        """
        return self._rate_limit_detector.is_rate_limited(self._page)

    def _navigate_to_url(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to URL with retry and rate limit detection.

        Uses the base class _navigate_with_retry method with Google-specific selectors.
        Also dismisses any popups after successful navigation.

        Args:
            url: URL to navigate to
            max_retries: Maximum number of retry attempts

        Returns:
            True if navigation succeeded, False otherwise
        """
        success = super()._navigate_with_retry(
            page=self._page,
            url=url,
            content_selectors=["h1.DUwDvf", "div.jftiEf", "div.qBF1Pd"],
            rate_limit_detector=self._rate_limit_detector,
            max_retries=max_retries,
            wait_after_load=2000
        )

        if success:
            # Dismiss any popups after successful navigation
            self._business_page.dismiss_popups()

        return success

    def _scrape_profile(self, account_id: str) -> Profile:
        """
        Scrape Google business profile information.

        Args:
            account_id: Business place_id or search query

        Returns:
            Profile model with business information
        """
        # Determine if this is a place_id or search query
        if account_id.startswith('ChI'):  # Place IDs typically start with ChI
            self._business_page.navigate_to_place(account_id)
        else:
            self._business_page.navigate_to_search(account_id)

        if not self._business_page.is_business_available():
            raise AccountNotFoundError(
                f"Google business not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Extract business data
        business_data = self._business_page.extract_business_data()

        # Get actual place_id from URL if we searched
        place_id = self._business_page.extract_place_id_from_url() or account_id

        return Profile(
            platform=self.platform,
            platform_id=place_id,
            username=business_data.get("name", account_id),
            display_name=business_data.get("name", ""),
            description=business_data.get("category", ""),
            followers_count=business_data.get("total_reviews", 0),
            following_count=0,
            posts_count=business_data.get("photo_count", 0),
            is_verified=False,  # Google doesn't have verification badges
            raw_data={
                "address": business_data.get("address", ""),
                "phone": business_data.get("phone", ""),
                "website": business_data.get("website", ""),
                "hours": business_data.get("hours", ""),
                "rating": business_data.get("rating", 0),
                "price_level": business_data.get("price_level", ""),
            },
        )

    def _scrape_posts(
        self,
        account_id: str,
        since_date: Optional[datetime],
        max_posts: int,
        known_post_ids: Optional[Set[str]] = None
    ) -> Iterator[ExtractionResult]:
        """
        Scrape reviews for a Google business.

        For Google, "posts" are actually the business listing, and "comments"
        are the reviews. We create a single Post object representing the business
        and attach all reviews as Comments.

        Args:
            account_id: Business place_id or search query
            since_date: Only get reviews after this date (optional)
            max_posts: Maximum number of reviews to scrape (used as max_reviews)
            known_post_ids: Set of review IDs to skip (already extracted)

        Yields:
            ExtractionResult with business as post and reviews as comments
        """
        logger.info(f"SCRAPING REVIEWS | target={account_id} | max={max_posts}")

        # Navigate to business
        if account_id.startswith('ChI'):
            url = Selectors.URLs.place(account_id)
        else:
            url = Selectors.URLs.search(account_id)

        nav_success = self._navigate_to_url(url)
        if not nav_success:
            raise AccountNotFoundError(
                f"Failed to navigate to business: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        if not self._business_page.is_business_available():
            raise AccountNotFoundError(
                f"Google business not found: {account_id}",
                platform=self.platform.value,
                account_id=account_id
            )

        # Extract business data for the "post"
        business_data = self._business_page.extract_business_data()
        place_id = self._business_page.extract_place_id_from_url() or account_id

        # Load checkpoint
        checkpoint_ids = self._load_checkpoint(account_id)
        all_known_ids = (known_post_ids or set()) | checkpoint_ids

        # Click reviews tab to open reviews section
        if not self._business_page.click_reviews_tab():
            logger.warning("Could not open reviews tab")
            return

        # Extract reviews (these become our "comments")
        raw_reviews = self._reviews_section.extract_reviews_for_business(
            place_id,
            max_reviews=max_posts
        )

        if not raw_reviews:
            logger.warning("No reviews found for business")
            return

        # Filter out already known reviews
        new_reviews = []
        for review in raw_reviews:
            review_id = review.get('id', '')
            if review_id not in all_known_ids:
                # Apply date filter
                if since_date and review.get('published_at'):
                    review_date = review['published_at']
                    if review_date.replace(tzinfo=None) < since_date:
                        continue
                new_reviews.append(review)

        logger.info(f"Found {len(new_reviews)} new reviews (skipped {len(raw_reviews) - len(new_reviews)} existing)")

        if not new_reviews:
            return

        # Create the Post object representing the business
        post = Post(
            platform=self.platform,
            platform_id=place_id,
            account_id=account_id,
            url=self._page.url,
            text=f"{business_data.get('name', '')} - {business_data.get('category', '')}",
            published_at=datetime.utcnow(),  # No creation date for businesses
            likes=0,
            comments_count=len(new_reviews),
            shares=0,
            media_type="business",
            media_urls=[],
            raw_data={
                "rating": business_data.get("rating", 0),
                "total_reviews": business_data.get("total_reviews", 0),
                "address": business_data.get("address", ""),
                "phone": business_data.get("phone", ""),
                "website": business_data.get("website", ""),
            },
        )

        # Convert reviews to Comment objects
        comments = self._create_comment_objects(new_reviews, place_id)

        yield ExtractionResult(post=post, comments=comments)

        # Save checkpoint
        processed_this_session = set(r.get('id', '') for r in new_reviews)
        self._save_checkpoint(account_id, checkpoint_ids | processed_this_session)

        # Check for extended break
        if self.should_take_extended_break():
            self.take_extended_break()

        # Clear checkpoint on successful completion
        self._clear_checkpoint(account_id)

        logger.info(
            f"EXTRACTION COMPLETE | business={account_id} | "
            f"reviews={len(comments)}"
        )
