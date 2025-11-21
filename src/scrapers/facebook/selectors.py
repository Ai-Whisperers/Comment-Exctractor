"""CSS and XPath selectors for Facebook pages.

All selectors are centralized here for easy maintenance when Facebook updates their UI.
"""


class Selectors:
    """All Facebook CSS/XPath selectors organized by page/component."""

    # =========================================================================
    # LOGIN PAGE SELECTORS
    # =========================================================================
    class Login:
        """Login page selectors."""
        EMAIL_INPUT = "input#email"
        PASSWORD_INPUT = "input#pass"
        LOGIN_BUTTON = "button[name='login']"

        # Cookie consent
        COOKIE_ACCEPT = "button[data-cookiebanner='accept_button']"
        COOKIE_DECLINE = "button[data-cookiebanner='decline_optional_button']"

        # Post-login popups
        NOT_NOW_BUTTON = "div[aria-label='Close']"
        SAVE_INFO_DISMISS = "div[role='button']:has-text('Not now')"

    # =========================================================================
    # HOME PAGE / LOGGED IN STATE SELECTORS
    # =========================================================================
    class Home:
        """Home page and logged-in state selectors."""
        # Positive indicators of logged-in state
        LOGGED_IN_INDICATORS = [
            "a[href*='/messages/']",
            "div[aria-label='Your profile']",
            "div[aria-label='Account']",
            "a[aria-label='Home']",
            "div[role='navigation']",
            "[data-pagelet='LeftRail']",
            "div[aria-label='Facebook']",
        ]
        NEWS_FEED = "[role='feed']"

        # Negative indicators (logged out)
        LOGIN_FORM_EMAIL = "input#email"
        LOGIN_FORM_PASSWORD = "input#pass"

    # =========================================================================
    # PROFILE/PAGE SELECTORS
    # =========================================================================
    class Profile:
        """Profile/Page selectors."""
        # Page info
        PAGE_NAME = "h1"
        FOLLOWERS_LINK = "a[href*='/followers'] span"
        LIKES_COUNT = "span:has-text(' people like this')"
        VERIFIED_BADGE = "svg[aria-label='Verified']"

        # Page not found
        PAGE_NOT_FOUND = "text='This content isn\\'t available'"

        # Private/restricted
        PRIVATE_PROFILE = "text='This content isn\\'t available'"

    # =========================================================================
    # POST SELECTORS
    # =========================================================================
    class Post:
        """Post selectors."""
        # Post containers
        POST_MESSAGE = "div[data-ad-preview='message']"
        POST_FEED_UNIT = "div[data-pagelet*='FeedUnit']"
        POST_LINK = "a[href*='/posts/']"

        # Post metrics
        REACTIONS_COUNT = "span:has-text(' reactions')"
        COMMENTS_COUNT = "span:has-text(' comment')"
        SHARES_COUNT = "span:has-text(' share')"
        POST_TIME = "a[href*='/posts/'] span"

        # Media
        VIDEO = "video"
        IMAGE = "img[data-visualcompletion='media-vc-image']"

    # =========================================================================
    # COMMENTS SECTION SELECTORS
    # =========================================================================
    class Comments:
        """Comments section selectors."""
        # Load more
        VIEW_MORE_COMMENTS = "span:has-text('View more comments')"
        VIEW_PREVIOUS = "span:has-text('View previous')"
        LOAD_MORE_REPLIES = "span:has-text('View')"

        # Comment containers
        COMMENT_CONTAINER = "div[aria-label*='Comment']"
        COMMENT_LIST = "ul[class]"

        # Comment elements
        COMMENT_AUTHOR = "a span"
        COMMENT_TEXT = "div[dir='auto']"
        COMMENT_TIME = "a[href*='comment_id'] span"
        COMMENT_LIKES = "span:has-text('Like')"

        # Reply elements
        REPLY_BUTTON = "span:has-text('Reply')"
        REPLY_CONTAINER = "div[aria-label*='Reply']"

    # =========================================================================
    # COMMON / POPUP SELECTORS
    # =========================================================================
    class Popups:
        """Common popup and dialog selectors."""
        # Generic dialog
        DIALOG = "div[role='dialog']"
        CLOSE_BUTTON = "div[aria-label='Close']"

        # Common dismiss buttons
        NOT_NOW = "div[role='button']:has-text('Not Now')"
        NOT_NOW_LOWER = "div[role='button']:has-text('Not now')"
        DISMISS = "div[role='button']:has-text('Dismiss')"
        OK = "div[role='button']:has-text('OK')"

    # =========================================================================
    # URL PATTERNS
    # =========================================================================
    class URLs:
        """URL patterns for Facebook."""
        BASE = "https://www.facebook.com"
        LOGIN = "https://www.facebook.com/login"
        HOME = "https://www.facebook.com/"

        # URL patterns for detection
        CHECKPOINT = "/checkpoint/"
        LOGIN_PATH = "/login"
        POST_PATTERN = "/posts/"
        PHOTO_PATTERN = "/photo"
        VIDEO_PATTERN = "/videos/"

        @staticmethod
        def profile(page_name: str) -> str:
            return f"https://www.facebook.com/{page_name}"

        @staticmethod
        def post(post_id: str) -> str:
            return f"https://www.facebook.com/posts/{post_id}"
