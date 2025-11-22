"""Google Maps Reviews Section Page Object."""

import logging
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import Page
from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class ReviewsSection(BasePage):
    """Page object for Google Maps review extraction."""

    def __init__(self, page: Page):
        super().__init__(page)

    def extract_reviews_for_business(self, business_id: str, max_reviews: int = 100) -> List[Dict[str, Any]]:
        """
        Extract reviews for a business.

        Args:
            business_id: Identifier for the business
            max_reviews: Maximum number of reviews to extract

        Returns:
            List of review dictionaries
        """
        logger.debug(f"EXTRACTING REVIEWS | business_id={business_id} | max={max_reviews}")

        # Sort by newest if possible
        self._sort_by_newest()

        # Scroll to load more reviews
        self._scroll_reviews_container(max_reviews)

        # Extract all visible reviews
        reviews = self._extract_reviews_js(business_id)

        # Limit to max_reviews
        reviews = reviews[:max_reviews]

        logger.info(f"EXTRACTED {len(reviews)} REVIEWS | business_id={business_id}")
        return reviews

    def _sort_by_newest(self) -> None:
        """Sort reviews by newest first."""
        try:
            # Click sort button
            if self.click(Selectors.Reviews.SORT_BUTTON, timeout=3000):
                self.wait(1000)
                # Click newest option
                if self.click(Selectors.Reviews.SORT_NEWEST, timeout=2000):
                    self.wait(2000)
                    logger.debug("Sorted reviews by newest")
        except Exception as e:
            logger.debug(f"Failed to sort reviews: {e}")

    def _scroll_reviews_container(self, target_reviews: int, max_scrolls: int = 50) -> None:
        """
        Scroll the reviews container to load more reviews.

        Args:
            target_reviews: Target number of reviews to load
            max_scrolls: Maximum scroll attempts
        """
        scroll_container = Selectors.Reviews.SCROLL_CONTAINER

        for i in range(max_scrolls):
            # Check current review count
            current_count = self._get_visible_review_count()
            if current_count >= target_reviews:
                logger.debug(f"Reached target reviews: {current_count}")
                break

            # Scroll the container
            try:
                self.evaluate(f'''
                    () => {{
                        const container = document.querySelector('{scroll_container}');
                        if (container) {{
                            container.scrollTop = container.scrollHeight;
                        }}
                    }}
                ''')
                self.wait(1500)
            except Exception as e:
                logger.debug(f"Scroll failed: {e}")
                break

            # Check if we've stopped loading new reviews
            new_count = self._get_visible_review_count()
            if new_count == current_count and i > 3:
                logger.debug(f"No new reviews loading after {i} scrolls")
                break

        logger.debug(f"Finished scrolling, loaded {self._get_visible_review_count()} reviews")

    def _get_visible_review_count(self) -> int:
        """Get count of currently visible reviews."""
        try:
            return self.evaluate(f'''
                () => document.querySelectorAll('{Selectors.Reviews.REVIEW_CONTAINER}').length
            ''')
        except Exception:
            return 0

    def _expand_review_texts(self) -> None:
        """Click 'See more' on truncated reviews."""
        try:
            # Click all expand buttons
            expand_count = self.evaluate(f'''
                () => {{
                    const buttons = document.querySelectorAll('{Selectors.Reviews.EXPAND_REVIEW}');
                    let clicked = 0;
                    buttons.forEach(btn => {{
                        try {{
                            btn.click();
                            clicked++;
                        }} catch (e) {{}}
                    }});
                    return clicked;
                }}
            ''')
            if expand_count > 0:
                self.wait(1000)
                logger.debug(f"Expanded {expand_count} review texts")
        except Exception as e:
            logger.debug(f"Failed to expand reviews: {e}")

    def _extract_reviews_js(self, business_id: str) -> List[Dict[str, Any]]:
        """
        Extract reviews using JavaScript.

        Args:
            business_id: Business identifier for review IDs

        Returns:
            List of review dictionaries
        """
        # First expand all truncated reviews
        self._expand_review_texts()

        try:
            reviews_data = self.evaluate('''
                () => {
                    const reviews = [];
                    const reviewElements = document.querySelectorAll('div.jftiEf');

                    reviewElements.forEach((review, index) => {
                        try {
                            // Reviewer name
                            let reviewerName = 'anonymous';
                            const nameElem = review.querySelector('div.d4r55, button.WEBjve');
                            if (nameElem) {
                                reviewerName = nameElem.textContent.trim();
                            }

                            // Reviewer photo
                            let reviewerPhoto = '';
                            const photoElem = review.querySelector('img.NBa7we');
                            if (photoElem) {
                                reviewerPhoto = photoElem.src || '';
                            }

                            // Review text - try expanded first, then regular
                            let text = '';
                            const expandedText = review.querySelector('span.MyEned');
                            if (expandedText) {
                                text = expandedText.textContent.trim();
                            } else {
                                const textElem = review.querySelector('span.wiI7pd');
                                if (textElem) {
                                    text = textElem.textContent.trim();
                                }
                            }

                            // Rating (from aria-label like "5 stars")
                            let rating = 0;
                            const ratingElem = review.querySelector('span.kvMYJc');
                            if (ratingElem) {
                                const ariaLabel = ratingElem.getAttribute('aria-label');
                                if (ariaLabel) {
                                    const match = ariaLabel.match(/\\d+/);
                                    if (match) {
                                        rating = parseInt(match[0], 10);
                                    }
                                }
                            }

                            // Date
                            let dateText = '';
                            const dateElem = review.querySelector('span.rsqaWe');
                            if (dateElem) {
                                dateText = dateElem.textContent.trim();
                            }

                            // Owner response
                            let ownerResponse = '';
                            const responseElem = review.querySelector('div.CDe7pd');
                            if (responseElem) {
                                ownerResponse = responseElem.textContent.trim();
                            }

                            // Helpful count
                            let helpfulCount = 0;
                            const helpfulElem = review.querySelector('span[aria-label*="found this helpful"]');
                            if (helpfulElem) {
                                const helpfulText = helpfulElem.getAttribute('aria-label');
                                if (helpfulText) {
                                    const match = helpfulText.match(/\\d+/);
                                    if (match) {
                                        helpfulCount = parseInt(match[0], 10);
                                    }
                                }
                            }

                            // Reviewer stats (reviews count, photos count)
                            let reviewerReviews = 0;
                            let reviewerPhotos = 0;
                            const statsElems = review.querySelectorAll('span.RfnDt');
                            if (statsElems.length > 0) {
                                const text1 = statsElems[0].textContent;
                                const match1 = text1.match(/\\d+/);
                                if (match1) {
                                    reviewerReviews = parseInt(match1[0], 10);
                                }
                            }
                            if (statsElems.length > 1) {
                                const text2 = statsElems[1].textContent;
                                const match2 = text2.match(/\\d+/);
                                if (match2) {
                                    reviewerPhotos = parseInt(match2[0], 10);
                                }
                            }

                            // Check for Local Guide badge
                            const isLocalGuide = review.querySelector('span:has-text("Local Guide")') !== null ||
                                               review.textContent.includes('Local Guide');

                            // Get review ID from data attribute if available
                            let reviewId = review.getAttribute('data-review-id') || '';

                            reviews.push({
                                reviewer_name: reviewerName,
                                reviewer_photo: reviewerPhoto,
                                text: text,
                                rating: rating,
                                date_text: dateText,
                                owner_response: ownerResponse,
                                helpful_count: helpfulCount,
                                reviewer_reviews: reviewerReviews,
                                reviewer_photos: reviewerPhotos,
                                is_local_guide: isLocalGuide,
                                review_id: reviewId,
                                index: index
                            });
                        } catch (e) {}
                    });
                    return reviews;
                }
            ''')

            processed = []
            seen_texts = set()

            for i, review in enumerate(reviews_data):
                text = review.get('text', '').strip()
                # Allow empty text reviews (rating only)
                reviewer_name = review.get('reviewer_name', 'anonymous')

                # Create unique key for deduplication
                unique_key = f"{reviewer_name}:{text}:{review.get('rating', 0)}"
                if unique_key in seen_texts:
                    continue
                seen_texts.add(unique_key)

                # Parse relative date text into approximate datetime
                published_at = self._parse_relative_date(review.get('date_text', ''))

                # Use review_id if available, otherwise generate
                review_id = review.get('review_id') or f"{business_id}_r{i}"

                processed.append({
                    'id': review_id,
                    'author': reviewer_name,
                    'author_photo': review.get('reviewer_photo', ''),
                    'text': text,
                    'rating': review.get('rating', 0),
                    'published_at': published_at,
                    'owner_response': review.get('owner_response', ''),
                    'helpful_count': review.get('helpful_count', 0),
                    'reviewer_reviews': review.get('reviewer_reviews', 0),
                    'reviewer_photos': review.get('reviewer_photos', 0),
                    'is_local_guide': review.get('is_local_guide', False),
                    'parent_id': None,
                    'likes': review.get('helpful_count', 0),
                    'replies_count': 1 if review.get('owner_response') else 0,
                })

            return processed

        except Exception as e:
            logger.warning(f"JS review extraction failed: {e}")
            return []

    def _parse_relative_date(self, date_text: str) -> datetime:
        """
        Parse relative date text like '2 weeks ago' into datetime.

        Args:
            date_text: Relative date string

        Returns:
            Approximate datetime
        """
        from datetime import timedelta
        now = datetime.utcnow()

        if not date_text:
            return now

        date_text = date_text.lower().strip()

        try:
            # Parse patterns like "2 weeks ago", "a month ago", "3 years ago"
            if 'year' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(days=365 * match)
            elif 'month' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(days=30 * match)
            elif 'week' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(weeks=match)
            elif 'day' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(days=match)
            elif 'hour' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(hours=match)
            elif 'minute' in date_text:
                match = self._extract_number(date_text)
                return now - timedelta(minutes=match)
            else:
                return now
        except Exception:
            return now

    @staticmethod
    def _extract_number(text: str) -> int:
        """Extract number from text, defaulting to 1 for 'a' or 'an'."""
        import re
        if text.startswith('a ') or text.startswith('an '):
            return 1
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 1
