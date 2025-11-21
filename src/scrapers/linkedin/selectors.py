"""LinkedIn CSS Selectors - Centralized selector management."""


class Selectors:
    """All LinkedIn selectors organized by page/feature."""

    class URLs:
        """LinkedIn URL patterns."""
        BASE = "https://www.linkedin.com"
        LOGIN = "https://www.linkedin.com/login"
        FEED = "https://www.linkedin.com/feed/"

        @staticmethod
        def profile(username: str) -> str:
            return f"https://www.linkedin.com/in/{username}/"

        @staticmethod
        def profile_posts(username: str) -> str:
            return f"https://www.linkedin.com/in/{username}/recent-activity/all/"

    class Login:
        """Login page selectors."""
        USERNAME_INPUT = 'input#username'
        PASSWORD_INPUT = 'input#password'
        LOGIN_BUTTON = 'button[type="submit"]'
        COOKIE_ACCEPT = 'button[action-type="ACCEPT"]'

    class Home:
        """Home/feed page selectors."""
        FEED_CONTAINER = 'div.feed-shared-update-v2'
        LOGGED_IN_INDICATORS = [
            'input[placeholder*="Search"]',
            'div[data-test-id="nav-search-bar"]',
            'button[data-control-name="nav.homepage"]',
        ]
        LOGIN_BUTTON = 'a[href*="/login"]'

    class Profile:
        """Profile page selectors."""
        DISPLAY_NAME = 'h1.text-heading-xlarge'
        HEADLINE = 'div.text-body-medium'
        FOLLOWERS_COUNT = 'span.t-bold:has-text("followers")'
        CONNECTIONS_COUNT = 'span.t-bold:has-text("connections")'
        VERIFIED_BADGE = 'div[data-test-icon="verified"]'
        NOT_FOUND = 'h1:has-text("Page not found")'
        ACTIVITY_TAB = 'a[href*="recent-activity"]'

    class Post:
        """Post selectors."""
        POST_CONTAINER = 'div.feed-shared-update-v2'
        POST_LINK = 'a[data-control-name="update_topbar_overflow_accessory"]'
        POST_TEXT = 'div.feed-shared-text'
        POST_TEXT_ALT = 'span.break-words'
        LIKE_COUNT = 'button[aria-label*="reaction"] span.social-details-social-counts__reactions-count'
        COMMENT_COUNT = 'button[aria-label*="comment"] span'
        REPOST_COUNT = 'button[aria-label*="repost"] span'
        TIME_ELEMENT = 'time'
        VIDEO = 'video'
        IMAGE = 'div.feed-shared-image'
        ARTICLE_LINK = 'a.feed-shared-article__meta'

    class Comments:
        """Comment selectors."""
        COMMENTS_BUTTON = 'button[aria-label*="comment"]'
        COMMENT_CONTAINER = 'article.comments-comment-item'
        COMMENT_TEXT = 'span.comments-comment-item__main-content'
        COMMENT_AUTHOR = 'span.comments-post-meta__name-text'
        COMMENT_TIME = 'time.comments-comment-item__timestamp'
        LOAD_MORE = 'button.comments-comments-list__load-more-comments-button'
        SHOW_REPLIES = 'button[aria-label*="replies"]'

    class Popups:
        """Popup/modal selectors."""
        DISMISS = 'button[aria-label="Dismiss"]'
        CLOSE = 'button[aria-label="Close"]'
        NOT_NOW = 'button:has-text("Not now")'
        SKIP = 'button:has-text("Skip")'
