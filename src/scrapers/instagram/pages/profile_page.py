"""Profile Page Object for Instagram profile/account pages."""

import logging
import re
from typing import List, Optional, Dict, Any, Union
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

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
        self.wait(1500)  # Reduced from 3000ms - content loads faster
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

    def get_post_links(self, count: int = 12, scroll_all: bool = False, known_post_ids: set = None) -> List[str]:
        """
        Get all content links from the profile grid (posts, reels, IGTV).

        Args:
            count: Maximum number of links to collect (ignored if scroll_all=True)
            scroll_all: If True, scroll until no more content appears
            known_post_ids: Set of post IDs already in database - stop scrolling when we hit these

        Returns:
            List of content URLs
        """
        logger.debug(f"COLLECTING CONTENT LINKS | target={count} | scroll_all={scroll_all} | known_posts={len(known_post_ids) if known_post_ids else 0}")

        # Wait for page to load content
        self.wait(1500)  # Reduced from 3000ms

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
            self.wait(2000)  # Reduced from 3000ms
            # Scroll to trigger lazy loading
            self.evaluate('window.scrollBy(0, 300)')
            self.wait(1500)  # Reduced from 2000ms
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(500)  # Reduced from 1000ms

        # Click Posts tab to ensure we're on the main grid
        self.click_posts_tab()

        # Wait for any content grid
        try:
            self.wait_for_selector(Selectors.Profile.POST_GRID, timeout=10000)
        except (PlaywrightTimeout, TimeoutError):
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

        # Helper to extract post ID from URL
        def extract_post_id(url: str) -> str:
            """Extract post ID from Instagram URL."""
            import re
            for pattern in [r'/p/([^/]+)', r'/reel/([^/]+)', r'/tv/([^/]+)']:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None

        if scroll_all:
            # Infinite scroll to collect ALL posts
            all_links = set()
            previous_count = 0
            no_new_content_count = 0
            max_no_new_content = 10  # Stop after 10 scrolls with no new content
            scroll_count = 0
            max_scrolls = 500  # Safety limit for very large profiles
            consecutive_known_posts = 0
            max_consecutive_known = 5  # Stop after 5 scrolls with mostly known posts

            logger.info("INFINITE SCROLL | starting to collect all posts")

            while scroll_count < max_scrolls:
                # Collect current links
                current_links = collect_links()
                new_links = set(current_links) - all_links
                all_links.update(current_links)
                current_count = len(all_links)

                logger.debug(f"SCROLL {scroll_count} | found {len(current_links)} visible | new: {len(new_links)} | total unique: {current_count}")

                # Check if newly found posts are already in database
                if known_post_ids and new_links:
                    new_post_ids = {extract_post_id(url) for url in new_links}
                    new_post_ids.discard(None)
                    known_count = len(new_post_ids & known_post_ids)

                    if known_count > 0:
                        logger.debug(f"SCROLL {scroll_count} | {known_count}/{len(new_post_ids)} new posts already in database")

                        # If most new posts are known, we've likely reached already-scraped content
                        if known_count >= len(new_post_ids) * 0.8:  # 80% or more are known
                            consecutive_known_posts += 1
                            if consecutive_known_posts >= max_consecutive_known:
                                logger.info(f"INFINITE SCROLL | reached known posts ({consecutive_known_posts} scrolls with mostly known content), stopping early")
                                break
                        else:
                            consecutive_known_posts = 0
                    else:
                        consecutive_known_posts = 0

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
                self.wait(2000)  # Reduced from 3000ms - Instagram loads posts quickly

                # Also try scrolling within main content area
                self.evaluate('''
                    () => {
                        const main = document.querySelector('main');
                        if (main) {
                            main.scrollTop = main.scrollHeight;
                        }
                    }
                ''')
                self.wait(500)  # Reduced from 1000ms

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

    def get_post_data_with_counts(self, count: int = 12, scroll_all: bool = False, known_post_ids: set = None) -> List[Dict[str, Any]]:
        """
        Get all content from the profile grid with likes and comment counts.

        This method extracts metadata from the hover overlay on each post thumbnail,
        which shows the number of likes and comments without needing to open each post.

        Args:
            count: Maximum number of posts to collect (ignored if scroll_all=True)
            scroll_all: If True, scroll until no more content appears
            known_post_ids: Set of post IDs already in database - stop scrolling when we hit these

        Returns:
            List of dicts with keys: url, likes, comments, post_id
        """
        logger.debug(f"COLLECTING CONTENT WITH COUNTS | target={count} | scroll_all={scroll_all} | known_posts={len(known_post_ids) if known_post_ids else 0}")

        # Wait for page to load content
        self.wait(1500)  # Reduced from 3000ms

        # Handle dialog if present
        page_debug = self.evaluate('''
            () => ({
                hasDialog: !!document.querySelector('[role="dialog"]'),
            })
        ''')
        if page_debug['hasDialog']:
            self.dismiss_popups()
            self.wait(1000)

        # Click Posts tab to ensure we're on the main grid
        self.click_posts_tab()

        # Wait for any content grid
        try:
            self.wait_for_selector(Selectors.Profile.POST_GRID, timeout=10000)
        except (PlaywrightTimeout, TimeoutError):
            self.wait(2000)

        def collect_posts_with_data():
            """Helper to collect all visible posts with their likes/comments counts."""
            return self.evaluate('''
                () => {
                    const posts = [];
                    const seenUrls = new Set();
                    const patterns = ['/p/', '/reel/', '/tv/'];

                    // Find all post thumbnail links
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.getAttribute('href');
                        if (!href) return;

                        let isContent = false;
                        for (const pattern of patterns) {
                            if (href.includes(pattern)) {
                                isContent = true;
                                break;
                            }
                        }
                        if (!isContent) return;

                        const fullUrl = href.startsWith('http')
                            ? href
                            : 'https://www.instagram.com' + href;

                        if (seenUrls.has(fullUrl)) return;
                        seenUrls.add(fullUrl);

                        // Try to find likes and comments from the overlay
                        // Instagram shows these in a ul > li structure when hovering
                        let likes = 0;
                        let comments = 0;

                        // Look for the overlay container (usually a sibling or child)
                        const container = a.closest('div');
                        if (container) {
                            // Instagram typically has the overlay as a sibling div
                            const overlay = container.querySelector('ul');
                            if (overlay) {
                                const items = overlay.querySelectorAll('li');
                                items.forEach((li, index) => {
                                    const text = li.textContent || '';
                                    // Extract numbers
                                    const numMatch = text.match(/([\\d,\\.]+)\\s*([KMB])?/i);
                                    if (numMatch) {
                                        let num = parseFloat(numMatch[1].replace(/,/g, ''));
                                        const suffix = numMatch[2];
                                        if (suffix) {
                                            if (suffix.toUpperCase() === 'K') num *= 1000;
                                            else if (suffix.toUpperCase() === 'M') num *= 1000000;
                                            else if (suffix.toUpperCase() === 'B') num *= 1000000000;
                                        }
                                        // First item is usually likes, second is comments
                                        if (index === 0) likes = Math.round(num);
                                        else if (index === 1) comments = Math.round(num);
                                    }
                                });
                            }
                        }

                        // Extract post ID from URL
                        let postId = null;
                        for (const pattern of ['/p/', '/reel/', '/tv/']) {
                            const match = fullUrl.match(new RegExp(pattern + '([^/]+)'));
                            if (match) {
                                postId = match[1];
                                break;
                            }
                        }

                        posts.push({
                            url: fullUrl,
                            likes: likes,
                            comments: comments,
                            post_id: postId
                        });
                    });

                    return posts;
                }
            ''')

        # Helper to extract post ID from URL
        def extract_post_id(url: str) -> str:
            """Extract post ID from Instagram URL."""
            import re
            for pattern in [r'/p/([^/]+)', r'/reel/([^/]+)', r'/tv/([^/]+)']:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None

        if scroll_all:
            # Infinite scroll to collect ALL posts with data
            # Use combined scroll+hover approach for reliable count extraction
            all_posts = {}  # url -> post_data
            processed_hrefs = set()  # Track which hrefs we've hovered
            previous_count = 0
            no_new_content_count = 0
            max_no_new_content = 15  # Increased for slower loading
            scroll_count = 0
            max_scrolls = 500
            consecutive_known_posts = 0
            max_consecutive_known = 5

            logger.info("INFINITE SCROLL WITH HOVER | starting to collect all posts with counts")

            while scroll_count < max_scrolls:
                # Get current visible post links from the main content grid
                # Filter to only posts in the profile grid area, not suggested posts or tagged content
                current_hrefs = self.evaluate('''
                    () => {
                        const hrefs = [];

                        // Focus on the main content area - look for posts within main or article
                        const mainContent = document.querySelector('main') || document.body;

                        // Find posts in the profile grid (articles or divs with post grid structure)
                        mainContent.querySelectorAll('a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]').forEach(a => {
                            const href = a.getAttribute('href');
                            if (!href || hrefs.includes(href)) return;

                            // Skip if this looks like it's in a modal or suggested section
                            const parent = a.closest('[role="dialog"]');
                            if (parent) return;  // Skip posts in dialogs

                            // Skip suggested posts (often in specific containers)
                            const container = a.closest('div');
                            if (container) {
                                const text = container.textContent || '';
                                if (text.includes('Suggested for you') || text.includes('More posts from')) {
                                    return;
                                }
                            }

                            hrefs.push(href);
                        });
                        return hrefs;
                    }
                ''')

                # Process new posts by hovering over them while visible
                new_hrefs = [h for h in current_hrefs if h not in processed_hrefs]
                new_count = 0

                for href in new_hrefs:
                    # Extract post ID from href
                    post_id = extract_post_id('https://www.instagram.com' + href)

                    try:
                        link_selector = f'a[href="{href}"]'
                        link = self.page.locator(link_selector).first

                        if link.is_visible(timeout=300):
                            # Hover to get overlay data
                            link.hover()
                            self.wait(350)

                            # Extract overlay data
                            overlay_data = self.evaluate('''
                                () => {
                                    const allUls = document.querySelectorAll('ul');
                                    for (const ul of allUls) {
                                        const style = window.getComputedStyle(ul);
                                        if (style.opacity !== '0' && ul.querySelectorAll('li').length >= 2) {
                                            const rect = ul.getBoundingClientRect();
                                            if (rect.width > 0 && rect.height > 0) {
                                                const items = ul.querySelectorAll('li');
                                                const texts = [];
                                                items.forEach(li => {
                                                    texts.push(li.textContent.trim());
                                                });
                                                if (texts.some(t => /\\d/.test(t))) {
                                                    return { texts: texts };
                                                }
                                            }
                                        }
                                    }
                                    return { error: 'no overlay' };
                                }
                            ''')

                            # Parse counts from overlay
                            likes = 0
                            comments = 0

                            if 'texts' in overlay_data:
                                for j, text in enumerate(overlay_data['texts']):
                                    num_match = re.search(r'([\d,.]+)\s*([KMB])?', text, re.IGNORECASE)
                                    if num_match:
                                        num = float(num_match.group(1).replace(',', ''))
                                        suffix = num_match.group(2)
                                        if suffix:
                                            if suffix.upper() == 'K':
                                                num *= 1000
                                            elif suffix.upper() == 'M':
                                                num *= 1000000
                                            elif suffix.upper() == 'B':
                                                num *= 1000000000
                                        if j == 0:
                                            likes = int(num)
                                        elif j == 1:
                                            comments = int(num)

                            full_url = f"https://www.instagram.com{href}"
                            all_posts[full_url] = {
                                'url': full_url,
                                'likes': likes,
                                'comments': comments,
                                'post_id': post_id
                            }
                            new_count += 1
                        else:
                            # Post not visible but still track it
                            full_url = f"https://www.instagram.com{href}"
                            if full_url not in all_posts:
                                all_posts[full_url] = {
                                    'url': full_url,
                                    'likes': 0,
                                    'comments': -1,  # -1 indicates unknown
                                    'post_id': post_id
                                }
                                new_count += 1

                    except Exception as e:
                        logger.debug(f"Error hovering post {href}: {e}")
                        full_url = f"https://www.instagram.com{href}"
                        if full_url not in all_posts:
                            all_posts[full_url] = {
                                'url': full_url,
                                'likes': 0,
                                'comments': -1,
                                'post_id': post_id
                            }
                            new_count += 1

                    processed_hrefs.add(href)

                current_count = len(all_posts)
                logger.debug(f"SCROLL {scroll_count} | found {len(current_hrefs)} visible | new: {new_count} | total: {current_count}")

                # Check if newly found posts are already in database
                if known_post_ids and new_count > 0:
                    # Get post IDs from the newly processed hrefs
                    new_post_ids = {extract_post_id('https://www.instagram.com' + href) for href in new_hrefs}
                    new_post_ids.discard(None)
                    if new_post_ids:
                        known_count = len(new_post_ids & known_post_ids)
                        if known_count >= len(new_post_ids) * 0.8:
                            consecutive_known_posts += 1
                            if consecutive_known_posts >= max_consecutive_known:
                                logger.info(f"INFINITE SCROLL | reached known posts, stopping early")
                                break
                        else:
                            consecutive_known_posts = 0

                # Check if we found new content
                if current_count == previous_count:
                    no_new_content_count += 1
                    if no_new_content_count >= max_no_new_content:
                        logger.info(f"INFINITE SCROLL | no new content after {max_no_new_content} scrolls, stopping")
                        break
                else:
                    no_new_content_count = 0
                    previous_count = current_count

                # Scroll down
                self.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                self.wait(2000)  # Reduced from 3000ms

                scroll_count += 1
                if scroll_count % 5 == 0:
                    logger.info(f"INFINITE SCROLL | progress: {scroll_count} scrolls, {current_count} posts collected")

            # Scroll back to top
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(500)

            result = list(all_posts.values())
            logger.info(f"INFINITE SCROLL COMPLETE | total posts collected: {len(result)} | scrolls: {scroll_count}")
            return result

        else:
            # Just collect visible posts
            self.evaluate('window.scrollBy(0, 500)')
            self.wait(1500)
            self.evaluate('window.scrollTo(0, 0)')
            self.wait(500)

            posts = collect_posts_with_data()
            result = posts[:count] if len(posts) > count else posts
            logger.info(f"CONTENT WITH COUNTS COLLECTED | count={len(result)}")
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
            except (PlaywrightTimeout, TimeoutError):
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
