"""Google Maps/Business CSS Selectors - Centralized selector management."""


class Selectors:
    """All Google Maps/Business selectors organized by page/feature."""

    class URLs:
        """Google Maps URL patterns."""
        BASE = "https://www.google.com/maps"
        SEARCH = "https://www.google.com/maps/search/"

        @staticmethod
        def place(place_id: str) -> str:
            return f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        @staticmethod
        def search(query: str) -> str:
            return f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    class Business:
        """Business profile selectors."""
        # Business info
        NAME = 'h1.DUwDvf'
        NAME_ALT = 'div.qBF1Pd'
        CATEGORY = 'button.DkEaL'
        ADDRESS = 'button[data-item-id="address"]'
        PHONE = 'button[data-item-id^="phone"]'
        WEBSITE = 'a[data-item-id="authority"]'
        HOURS = 'div[aria-label*="hours"]'

        # Ratings
        RATING = 'div.F7nice span[aria-hidden="true"]'
        RATING_ALT = 'span.ceNzKf'
        TOTAL_REVIEWS = 'span.UY7F9'
        TOTAL_REVIEWS_ALT = 'button[jsaction*="reviews"] span'

        # Photos
        PHOTO_COUNT = 'button[aria-label*="photos"]'
        MAIN_PHOTO = 'button.aoRNLd img'

        # Additional info
        PRICE_LEVEL = 'span[aria-label*="Price"]'
        POPULAR_TIMES = 'div.g2BVhd'

        # Not found
        NOT_FOUND = 'div:has-text("can\'t find")'

    class Reviews:
        """Review section selectors."""
        # Review tab/button
        REVIEWS_TAB = 'button[aria-label*="Reviews"]'
        REVIEWS_TAB_ALT = 'button[data-tab-index="1"]'

        # Review containers
        REVIEW_CONTAINER = 'div.jftiEf'
        REVIEW_CARD = 'div[data-review-id]'

        # Review elements
        REVIEW_TEXT = 'span.wiI7pd'
        REVIEW_TEXT_EXPANDED = 'span.MyEned'
        REVIEW_RATING = 'span.kvMYJc'
        REVIEW_DATE = 'span.rsqaWe'
        REVIEW_OWNER_RESPONSE = 'div.CDe7pd'

        # Reviewer info
        REVIEWER_NAME = 'div.d4r55'
        REVIEWER_NAME_ALT = 'button.WEBjve'
        REVIEWER_PHOTO = 'img.NBa7we'
        REVIEWER_REVIEWS_COUNT = 'span.RfnDt'
        REVIEWER_PHOTOS_COUNT = 'span.RfnDt:nth-child(2)'
        LOCAL_GUIDE = 'span:has-text("Local Guide")'

        # Interactions
        HELPFUL_COUNT = 'span[aria-label*="found this helpful"]'

        # Sort options
        SORT_BUTTON = 'button[aria-label="Sort reviews"]'
        SORT_NEWEST = 'div[data-index="1"]'
        SORT_HIGHEST = 'div[data-index="2"]'
        SORT_LOWEST = 'div[data-index="3"]'

        # Load more
        SHOW_MORE_BUTTON = 'button[aria-label="More reviews"]'
        EXPAND_REVIEW = 'button[aria-label*="See more"]'
        SCROLL_CONTAINER = 'div.m6QErb.DxyBCb'

    class Photos:
        """Photo section selectors."""
        PHOTOS_TAB = 'button[aria-label*="Photos"]'
        PHOTO_GRID = 'div.U39Pmb'
        PHOTO_ITEM = 'button.U39Pmb'
        PHOTO_COUNT_LABEL = 'div.YkuOqf'

    class Popups:
        """Popup/modal selectors."""
        COOKIE_ACCEPT = 'button[aria-label="Accept all"]'
        COOKIE_REJECT = 'button[aria-label="Reject all"]'
        CLOSE_BUTTON = 'button[aria-label="Close"]'
        DISMISS = 'button[aria-label="Dismiss"]'

    class RateLimit:
        """Rate limit and error detection selectors."""
        CAPTCHA = 'iframe[title*="recaptcha"]'
        UNUSUAL_TRAFFIC = 'div:has-text("unusual traffic")'
        BLOCKED = 'div:has-text("blocked")'
        TRY_AGAIN = 'div:has-text("Try again later")'
