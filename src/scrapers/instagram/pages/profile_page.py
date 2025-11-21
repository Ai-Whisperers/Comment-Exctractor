"""Profile Page Object for Instagram profile/account pages."""

import logging
from typing import List, Optional
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class ProfilePage(BasePage):
    """Page Object for Instagram profile page."""

    def navigate(self, username: str) -> "ProfilePage":
        """
        Navigate to a user's profile.

        Args:
            username: Instagram username

        Returns:
            Self for chaining
        """
        url = Selectors.URLs.profile(username)
        # Use domcontentloaded instead of networkidle to avoid timeout issues
        # Instagram keeps making background requests that prevent networkidle
        super().navigate(url, wait_until="domcontentloaded")
        self.wait(3000)
        self.dismiss_popups()
        return self

    def is_private(self) -> bool:
        """
        Check if account is private.

        Returns:
            True if account is private
        """
        return self.is_visible(Selectors.Profile.PRIVATE_ACCOUNT, timeout=3000)

    def is_logged_in(self) -> bool:
        """
        Check if user is logged in by looking for logged-in indicators.

        Returns:
            True if logged in
        """
        # Check URL first
        if self.url_contains(Selectors.URLs.ACCOUNTS_LOGIN) or self.url_contains(Selectors.URLs.ACCOUNTS_SIGNUP):
            return False

        # Check for positive indicators
        indicators = [
            Selectors.Home.DIRECT_INBOX,
            Selectors.Home.NEW_POST_ICON,
            Selectors.Home.SEARCH_ICON,
            Selectors.Home.NOTIFICATIONS,
            Selectors.Home.PROFILE_ICON,
        ]

        for selector in indicators:
            if self.is_visible(selector, timeout=2000):
                logger.debug(f"LOGIN CHECK | found indicator: {selector}")
                return True

        # Check for feed article
        if self.is_visible(Selectors.Home.FEED_ARTICLE, timeout=3000):
            logger.debug("LOGIN CHECK | found article element")
            return True

        # Check for login form (negative indicator)
        has_login_form = self.evaluate('''
            () => {
                const hasUsername = !!document.querySelector('input[name="username"]');
                const hasPassword = !!document.querySelector('input[name="password"]');
                return hasUsername && hasPassword;
            }
        ''')
        if has_login_form:
            logger.debug("LOGIN CHECK | login form detected")
            return False

        return False

    def click_posts_tab(self) -> "ProfilePage":
        """
        Click the Posts tab if available.

        Returns:
            Self for chaining
        """
        if self.click(Selectors.Profile.POSTS_TAB, timeout=2000):
            self.wait(2000)
        return self

    def get_post_links(self, count: int = 12, scroll_all: bool = False) -> List[str]:
        """
        Get all content links from the profile grid (posts, reels, IGTV).

        Args:
            count: Maximum number of links to collect (ignored if scroll_all=True)
            scroll_all: If True, scroll until no more content appears

        Returns:
            List of content URLs
        """
        logger.debug(f"COLLECTING CONTENT LINKS | target={count} | scroll_all={scroll_all}")

        # Wait for page to load content
        self.wait(3000)

        # Log page state for debugging - count all content types
        page_debug = self.evaluate('''
            () => {
                const posts = document.querySelectorAll('a[href*="/p/"]').length;
                const reels = document.querySelectorAll('a[href*="/reel/"]').length;
                const tv = document.querySelectorAll('a[href*="/tv/"]').length;
                return {
                    postLinksCount: posts,
                    reelLinksCount: reels,
                    tvLinksCount: tv,
                    totalContent: posts + reels + tv,
                    hasDialog: !!document.querySelector('[role="dialog"]'),
                    hasLoginForm: !!document.querySelector('input[name="username"]')
                };
            }
        ''')
        logger.info(f"PAGE STATE | posts={page_debug['postLinksCount']} | reels={page_debug['reelLinksCount']} | tv={page_debug['tvLinksCount']} | total={page_debug['totalContent']} | dialog={page_debug['hasDialog']} | login_form={page_debug['hasLoginForm']}")

        # Handle dialog if present
        if page_debug['hasDialog']:
            self.dismiss_popups()
            self.wait(1000)

        # If no content found, wait longer and try again
        if page_debug['totalContent'] == 0:
            logger.debug("No content found initially, waiting for lazy load...")
            self.wait(3000)
            # Scroll to trigger lazy loading
            self.evaluate('window.scrollBy(0, 300)')
            self.wait(2000)
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(1000)

        # Click Posts tab to ensure we're on the main grid
        self.click_posts_tab()

        # Wait for any content grid
        try:
            self.wait_for_selector(Selectors.Profile.POST_GRID, timeout=10000)
        except Exception:
            # Try alternative - just wait for main content area
            self.wait(2000)

        def collect_links():
            """Helper to collect all visible content links."""
            return self.evaluate('''
                () => {
                    const links = new Set();
                    const patterns = ['/p/', '/reel/', '/tv/'];

                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href) {
                            for (const pattern of patterns) {
                                if (href.includes(pattern)) {
                                    const fullUrl = href.startsWith('http')
                                        ? href
                                        : 'https://www.instagram.com' + href;
                                    links.add(fullUrl);
                                    break;
                                }
                            }
                        }
                    });

                    return Array.from(links);
                }
            ''')

        if scroll_all:
            # Infinite scroll to collect ALL posts
            all_links = set()
            previous_count = 0
            no_new_content_count = 0
            max_no_new_content = 10  # Stop after 10 scrolls with no new content
            scroll_count = 0
            max_scrolls = 500  # Safety limit for very large profiles

            logger.info("INFINITE SCROLL | starting to collect all posts")

            while scroll_count < max_scrolls:
                # Collect current links
                current_links = collect_links()
                all_links.update(current_links)
                current_count = len(all_links)

                logger.debug(f"SCROLL {scroll_count} | found {len(current_links)} visible | total unique: {current_count}")

                # Check if we found new content
                if current_count == previous_count:
                    no_new_content_count += 1
                    if no_new_content_count >= max_no_new_content:
                        logger.info(f"INFINITE SCROLL | no new content after {max_no_new_content} scrolls, stopping")
                        break
                else:
                    no_new_content_count = 0
                    previous_count = current_count

                # Scroll down to bottom
                self.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                self.wait(3000)  # Wait for lazy loading - Instagram needs time to fetch posts

                # Also try scrolling within main content area
                self.evaluate('''
                    () => {
                        const main = document.querySelector('main');
                        if (main) {
                            main.scrollTop = main.scrollHeight;
                        }
                    }
                ''')
                self.wait(1000)  # Additional wait for content to render

                scroll_count += 1

                # Log progress every 5 scrolls
                if scroll_count % 5 == 0:
                    logger.info(f"INFINITE SCROLL | progress: {scroll_count} scrolls, {current_count} posts collected")

            # Scroll back to top
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(500)

            result = list(all_links)
            logger.info(f"INFINITE SCROLL COMPLETE | total posts collected: {len(result)} | scrolls: {scroll_count}")
            return result

        else:
            # Original behavior - just scroll once and collect
            self.evaluate('window.scrollBy(0, 500)')
            self.wait(1500)
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(500)

            links = collect_links()

            logger.debug(f"RAW LINKS FOUND | count={len(links) if links else 0}")

            result = links[:count] if len(links) > count else links
            logger.info(f"CONTENT LINKS COLLECTED | count={len(result)}")
            return result

    def click_first_post(self) -> bool:
        """
        Click the first content item (post/reel/IGTV) to open modal.

        Returns:
            True if content was clicked
        """
        links = self.get_post_links(1)
        if not links:
            logger.error("No content found to click")
            return False

        first_url = links[0]
        # Extract path for selector
        post_path = first_url.split("instagram.com")[-1]
        selector = f'a[href*="{post_path}"]'

        # Determine content type for logging
        content_type = "post"
        if "/reel/" in first_url:
            content_type = "reel"
        elif "/tv/" in first_url:
            content_type = "igtv"

        logger.info(f"CLICKING FIRST CONTENT | type={content_type} | url={first_url}")

        try:
            element = self.page.locator(selector).first
            element.scroll_into_view_if_needed()
            self.wait(500)
            element.click()

            # Wait for modal to open - check for any content URL pattern
            try:
                # Wait for URL to contain /p/, /reel/, or /tv/
                self.page.wait_for_function(
                    '''() => {
                        const url = window.location.href;
                        return url.includes('/p/') || url.includes('/reel/') || url.includes('/tv/');
                    }''',
                    timeout=10000
                )
                logger.info("CONTENT MODAL OPENED")
                return True
            except Exception:
                # Try alternative detection - modal dialog
                if self.wait_for_selector(Selectors.PostModal.ARTICLE, timeout=5000):
                    return True
                if self.wait_for_selector(Selectors.PostModal.DIALOG, timeout=3000):
                    return True

        except Exception as e:
            logger.warning(f"Click failed: {e}, navigating directly")
            super().navigate(first_url, wait_until="domcontentloaded")
            self.wait(2000)
            return True

        return False

    def get_followers_count(self) -> int:
        """
        Get followers count.

        Returns:
            Number of followers
        """
        text = self.get_text(Selectors.Profile.FOLLOWERS_COUNT)
        return self.parse_count(text) if text else 0

    def get_following_count(self) -> int:
        """
        Get following count.

        Returns:
            Number of accounts being followed
        """
        text = self.get_text(Selectors.Profile.FOLLOWING_COUNT)
        return self.parse_count(text) if text else 0

    def get_display_name(self) -> Optional[str]:
        """
        Get profile display name.

        Returns:
            Display name or None
        """
        return self.get_text(Selectors.Profile.DISPLAY_NAME)

    def is_verified(self) -> bool:
        """
        Check if account is verified.

        Returns:
            True if verified
        """
        return self.is_visible(Selectors.Profile.VERIFIED_BADGE, timeout=2000)
