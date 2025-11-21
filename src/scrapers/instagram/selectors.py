"""CSS and XPath selectors for Instagram pages.

All selectors are centralized here for easy maintenance when Instagram updates their UI.
"""


class Selectors:
    """All Instagram CSS/XPath selectors organized by page/component."""

    # =========================================================================
    # LOGIN PAGE SELECTORS
    # =========================================================================
    class Login:
        """Login page selectors."""
        USERNAME_INPUT = "input[name='username']"
        PASSWORD_INPUT = "input[name='password']"
        SUBMIT_BUTTON = "button[type='submit']"

        # Error messages
        ERROR_ALERT = "#slfErrorAlert"
        ERROR_ROLE = "[role='alert']"
        ERROR_MESSAGE = "p[data-testid='login-error-message']"
        ERROR_DIV = "div[class*='error']"

        # Cookie consent
        COOKIE_ALLOW_ALL = "button:has-text('Allow all cookies')"
        COOKIE_ALLOW_ESSENTIAL = "button:has-text('Allow essential and optional cookies')"
        COOKIE_DECLINE = "button:has-text('Decline optional cookies')"

        # Post-login popups
        NOT_NOW_BUTTON = "button:has-text('Not Now')"
        SAVE_INFO_DISMISS = "button:has-text('Not now')"

    # =========================================================================
    # HOME PAGE / LOGGED IN STATE SELECTORS
    # =========================================================================
    class Home:
        """Home page and logged-in state selectors."""
        # Positive indicators of logged-in state
        DIRECT_INBOX = "a[href*='/direct/inbox/']"
        NEW_POST_ICON = "svg[aria-label='New post']"
        SEARCH_ICON = "svg[aria-label='Search']"
        NOTIFICATIONS = "span[aria-label='Notifications']"
        PROFILE_ICON = "span[aria-label='Profile']"
        FEED_ARTICLE = "article"

        # Negative indicators (logged out)
        LOGIN_FORM_USERNAME = "input[name='username']"
        LOGIN_FORM_PASSWORD = "input[name='password']"

    # =========================================================================
    # PROFILE PAGE SELECTORS
    # =========================================================================
    class Profile:
        """Profile page selectors."""
        # Navigation tabs
        POSTS_TAB = "a[href*='/']:has-text('Posts')"
        REELS_TAB = "a[href*='/reels/']"
        TAGGED_TAB = "a[href*='/tagged/']"

        # Post grid - all content types (posts, reels, IGTV)
        # Posts use /p/, Reels use /reel/, IGTV uses /tv/
        POST_LINK = "a[href*='/p/'], a[href*='/reel/'], a[href*='/tv/']"
        POST_GRID = "article a[href*='/p/'], article a[href*='/reel/'], article a[href*='/tv/']"

        # Alternative grid selectors for main content area
        GRID_ITEM = "main article a"
        CONTENT_LINK = "a[href^='/']"

        # Profile info
        FOLLOWERS_COUNT = "a[href*='/followers/'] span"
        FOLLOWING_COUNT = "a[href*='/following/'] span"
        POSTS_COUNT = "span:has-text('posts')"
        BIO = "div.-vDIg span"
        DISPLAY_NAME = "header section h2"

        # Private account
        PRIVATE_ACCOUNT = "h2:has-text('This Account is Private')"

        # Verified badge
        VERIFIED_BADGE = "svg[aria-label='Verified']"

    # =========================================================================
    # POST MODAL SELECTORS
    # =========================================================================
    class PostModal:
        """Post modal/dialog selectors."""
        # Modal container
        DIALOG = "div[role='dialog']"
        ARTICLE = "article[role='presentation']"

        # Caption
        CAPTION_H1 = "article h1"
        CAPTION_DIALOG_H1 = "div[role='dialog'] h1"
        CAPTION_BUTTON_SPAN = "article div[role='button'] span"
        CAPTION_DIALOG_SPAN = "div[role='dialog'] div[role='button'] span"

        # Engagement
        LIKES_SECTION = "section span:has-text('likes')"
        LIKE_SINGLE = "section span:has-text('like')"
        LIKES_DIALOG = "div[role='dialog'] section span:has-text('likes')"
        LIKED_BY_LINK = "a[href*='/liked_by/'] span"

        # Timestamp
        TIME_ELEMENT = "time"
        TIME_DATETIME = "time[datetime]"

        # Media
        VIDEO = "video"
        CAROUSEL_NEXT = "button[aria-label='Next']"

        # Navigation
        NEXT_BUTTON = "button[aria-label='Next'], button:has-text('Next'), svg[aria-label='Next']"
        PREV_BUTTON = "button[aria-label='Go Back'], svg[aria-label='Go Back']"
        CLOSE_BUTTON = "svg[aria-label='Close']"

        # Post link (to extract post ID) - includes reels and IGTV
        POST_LINK_IN_MODAL = "div[role='dialog'] a[href*='/p/'], div[role='dialog'] a[href*='/reel/'], div[role='dialog'] a[href*='/tv/']"
        TIME_LINK = "div[role='dialog'] time[datetime] a[href*='/p/'], div[role='dialog'] time[datetime] a[href*='/reel/'], div[role='dialog'] time[datetime] a[href*='/tv/']"

        # Any content link in modal
        CONTENT_LINK_IN_MODAL = "div[role='dialog'] a[href^='/p/'], div[role='dialog'] a[href^='/reel/'], div[role='dialog'] a[href^='/tv/']"

    # =========================================================================
    # COMMENTS SECTION SELECTORS
    # =========================================================================
    class Comments:
        """Comments section selectors."""
        # Load more
        LOAD_MORE_BUTTON = "button:has-text('Load more comments')"
        VIEW_ALL_COMMENTS = "button:has-text('View all')"
        LOAD_MORE_ALT = "svg[aria-label='Load more comments']"

        # Comment items
        COMMENT_LIST = "ul > div > li"
        COMMENT_CONTAINER = "div[role='dialog'] ul li"

        # Comment elements
        COMMENT_TEXT = "span"
        COMMENT_AUTHOR = "a span"
        COMMENT_TIME = "time"
        COMMENT_LIKES = "button span"

        # Reply elements
        REPLY_BUTTON = "button:has-text('View replies')"
        REPLY_CONTAINER = "ul ul li"

    # =========================================================================
    # COMMON / POPUP SELECTORS
    # =========================================================================
    class Popups:
        """Common popup and dialog selectors."""
        # Generic dialog
        DIALOG = "div[role='dialog']"
        CLOSE_BUTTON = "button[aria-label='Close']"
        CLOSE_SVG = "svg[aria-label='Close']"

        # Common dismiss buttons
        NOT_NOW = "button:has-text('Not Now')"
        NOT_NOW_LOWER = "button:has-text('Not now')"
        DISMISS = "button:has-text('Dismiss')"
        ACCEPT = "button:has-text('Accept')"
        CANCEL = "button:has-text('Cancel')"

        # Turn on notifications
        NOTIFICATIONS_DISMISS = "button:has-text('Not Now')"

    # =========================================================================
    # URL PATTERNS
    # =========================================================================
    class URLs:
        """URL patterns for Instagram."""
        BASE = "https://www.instagram.com"
        LOGIN = "https://www.instagram.com/accounts/login/"
        HOME = "https://www.instagram.com/"

        # URL patterns for detection
        CHALLENGE = "/challenge/"
        CHECKPOINT = "/checkpoint/"
        ACCOUNTS_LOGIN = "/accounts/login"
        ACCOUNTS_SIGNUP = "/accounts/emailsignup"
        POST_PATTERN = "/p/"
        REEL_PATTERN = "/reel/"
        TV_PATTERN = "/tv/"

        @staticmethod
        def profile(username: str) -> str:
            return f"https://www.instagram.com/{username}/"

        @staticmethod
        def post(post_id: str) -> str:
            return f"https://www.instagram.com/p/{post_id}/"

        @staticmethod
        def reel(reel_id: str) -> str:
            return f"https://www.instagram.com/reel/{reel_id}/"

        @staticmethod
        def tv(tv_id: str) -> str:
            return f"https://www.instagram.com/tv/{tv_id}/"
