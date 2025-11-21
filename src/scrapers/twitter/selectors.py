"""CSS and XPath selectors for Twitter/X pages.

All selectors are centralized here for easy maintenance when Twitter updates their UI.
"""


class Selectors:
    """All Twitter CSS/XPath selectors organized by page/component."""

    # =========================================================================
    # LOGIN PAGE SELECTORS
    # =========================================================================
    class Login:
        """Login page selectors."""
        USERNAME_INPUT = "input[autocomplete='username']"
        PASSWORD_INPUT = "input[autocomplete='current-password']"
        NEXT_BUTTON = "div[role='button']:has-text('Next')"
        LOGIN_BUTTON = "div[role='button']:has-text('Log in')"

        # Cookie consent
        COOKIE_ACCEPT = "div[role='button']:has-text('Accept all cookies')"

    # =========================================================================
    # HOME PAGE / LOGGED IN STATE SELECTORS
    # =========================================================================
    class Home:
        """Home page and logged-in state selectors."""
        LOGGED_IN_INDICATORS = [
            "a[aria-label='Home']",
            "a[href='/home']",
            "a[aria-label='Profile']",
            "nav[aria-label='Primary']",
            "div[data-testid='primaryColumn']",
        ]
        TIMELINE = "div[aria-label='Timeline: Your Home Timeline']"

        # Logged out indicators
        LOGIN_BUTTON = "a[href='/login']"

    # =========================================================================
    # PROFILE PAGE SELECTORS
    # =========================================================================
    class Profile:
        """Profile page selectors."""
        # Profile info
        DISPLAY_NAME = "div[data-testid='UserName'] span"
        USERNAME = "div[data-testid='UserName'] div:has-text('@')"
        BIO = "div[data-testid='UserDescription']"
        FOLLOWERS_COUNT = "a[href$='/verified_followers'] span, a[href$='/followers'] span"
        FOLLOWING_COUNT = "a[href$='/following'] span"
        VERIFIED_BADGE = "svg[aria-label='Verified account']"

        # Profile not found
        NOT_FOUND = "span:has-text('This account doesn\\'t exist')"

        # Tweets tab
        TWEETS_TAB = "a[href$='/']:has-text('Posts')"

    # =========================================================================
    # TWEET/POST SELECTORS
    # =========================================================================
    class Tweet:
        """Tweet/Post selectors."""
        # Tweet containers
        TWEET_ARTICLE = "article[data-testid='tweet']"
        TWEET_TEXT = "div[data-testid='tweetText']"
        TWEET_LINK = "a[href*='/status/']"

        # Metrics
        REPLY_COUNT = "div[data-testid='reply'] span"
        RETWEET_COUNT = "div[data-testid='retweet'] span"
        LIKE_COUNT = "div[data-testid='like'] span"
        VIEW_COUNT = "a[href$='/analytics'] span"

        # Timestamp
        TIME_ELEMENT = "time"

        # Media
        VIDEO = "video"
        IMAGE = "div[data-testid='tweetPhoto'] img"

    # =========================================================================
    # REPLIES/COMMENTS SELECTORS
    # =========================================================================
    class Replies:
        """Replies section selectors."""
        # Reply containers
        REPLY_ARTICLE = "article[data-testid='tweet']"

        # Show more replies
        SHOW_REPLIES = "div[role='button']:has-text('Show replies')"
        SHOW_MORE = "div[role='button']:has-text('Show more replies')"

        # Reply elements
        REPLY_TEXT = "div[data-testid='tweetText']"
        REPLY_AUTHOR = "div[data-testid='User-Name'] a"
        REPLY_TIME = "time"

    # =========================================================================
    # COMMON / POPUP SELECTORS
    # =========================================================================
    class Popups:
        """Common popup and dialog selectors."""
        DIALOG = "div[role='dialog']"
        CLOSE_BUTTON = "div[aria-label='Close']"

        # Common dismiss
        NOT_NOW = "div[role='button']:has-text('Not now')"
        DISMISS = "div[role='button']:has-text('Dismiss')"

    # =========================================================================
    # URL PATTERNS
    # =========================================================================
    class URLs:
        """URL patterns for Twitter."""
        BASE = "https://x.com"
        LOGIN = "https://x.com/i/flow/login"
        HOME = "https://x.com/home"

        # URL patterns
        STATUS_PATTERN = "/status/"

        @staticmethod
        def profile(username: str) -> str:
            return f"https://x.com/{username}"

        @staticmethod
        def tweet(username: str, tweet_id: str) -> str:
            return f"https://x.com/{username}/status/{tweet_id}"
