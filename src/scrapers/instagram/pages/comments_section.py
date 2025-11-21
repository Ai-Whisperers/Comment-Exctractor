"""Comments Section Page Object for Instagram comment extraction."""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class CommentsSection(BasePage):
    """Page Object for Instagram comments section."""

    def load_all_comments(self, max_clicks: int = 10) -> int:
        """
        Load all comments by clicking 'Load more' repeatedly.

        Args:
            max_clicks: Maximum number of times to click load more

        Returns:
            Number of times load more was clicked
        """
        clicks = 0
        load_selectors = [
            Selectors.Comments.LOAD_MORE_BUTTON,
            Selectors.Comments.VIEW_ALL_COMMENTS,
            Selectors.Comments.LOAD_MORE_ALT,
        ]

        for _ in range(max_clicks):
            clicked = False
            for selector in load_selectors:
                if self.click(selector, timeout=2000):
                    clicks += 1
                    clicked = True
                    self.wait(1500)
                    break

            if not clicked:
                break

        logger.debug(f"COMMENTS | loaded more {clicks} times")
        return clicks

    def get_comments(self) -> List[Dict[str, Any]]:
        """
        Extract all visible comments.

        Returns:
            List of comment dictionaries
        """
        comments = []

        # Debug: Log what we can find on the page
        debug_info = self.evaluate('''
            () => {
                const container = document.querySelector('div[role="dialog"]') || document.querySelector('article') || document.querySelector('main');
                if (!container) return { error: 'No container found' };

                // Find elements that have time (timestamps are key for comments)
                const timeElements = container.querySelectorAll('time');
                const commentCandidates = [];

                timeElements.forEach((time, i) => {
                    // Go up to find the parent that contains the full comment
                    let parent = time.parentElement;
                    for (let j = 0; j < 5 && parent; j++) {
                        const hasAuthorLink = parent.querySelector('a[href^="/"][href$="/"]');
                        const textContent = parent.innerText?.trim() || '';

                        if (hasAuthorLink && textContent.length > 5) {
                            commentCandidates.push({
                                index: i,
                                parentTag: parent.tagName,
                                tagPath: '',
                                textLength: textContent.length,
                                firstAuthor: hasAuthorLink.textContent?.trim() || ''
                            });
                            break;
                        }
                        parent = parent.parentElement;
                    }
                });

                // Get span samples
                const spanWithText = [];
                container.querySelectorAll('span').forEach(s => {
                    if (s.innerText && s.innerText.length > 20 && s.innerText.length < 500) {
                        const hasNestedSpan = s.querySelector('span');
                        if (!hasNestedSpan) {
                            spanWithText.push(s.innerText.substring(0, 50));
                        }
                    }
                });

                return {
                    containerTag: container.tagName,
                    timeElementsCount: timeElements.length,
                    commentCandidates: commentCandidates.slice(0, 10),
                    spanSamples: spanWithText.slice(0, 3)
                };
            }
        ''')
        logger.info(f"COMMENT DEBUG | {debug_info}")

        # Extract comments by finding comment blocks with author + text + timestamp
        raw_comments = self.evaluate('''
            () => {
                const comments = [];
                const container = document.querySelector('div[role="dialog"]') || document.querySelector('article') || document.querySelector('main');
                if (!container) return comments;

                const seenTexts = new Set();
                const timeElements = container.querySelectorAll('time');

                // Skip first time element (it's usually the post itself)
                for (let i = 1; i < timeElements.length; i++) {
                    const timeEl = timeElements[i];

                    // Go up to find comment container (try multiple levels)
                    let commentDiv = timeEl.parentElement;
                    let foundComment = false;

                    for (let level = 0; level < 8 && commentDiv && !foundComment; level++) {
                        // Look for author link in this container
                        const links = commentDiv.querySelectorAll('a[href^="/"]');
                        let author = '';
                        let authorLink = null;

                        for (const link of links) {
                            const href = link.getAttribute('href');
                            if (href && href.match(/^\\/[^\\/]+\\/?$/) &&
                                !href.includes('/p/') && !href.includes('/reel/') && !href.includes('/explore/')) {
                                const linkText = link.textContent?.trim() || '';
                                if (linkText && linkText.length > 0 && linkText.length < 50) {
                                    author = linkText.replace(/Verified$/, '').trim();
                                    authorLink = link;
                                    break;
                                }
                            }
                        }

                        if (!author) {
                            commentDiv = commentDiv.parentElement;
                            continue;
                        }

                        // Find comment text - look for spans with class containing comment text
                        let text = '';

                        // First try to find the specific comment text span
                        const textSpans = commentDiv.querySelectorAll('span[dir="auto"]');
                        for (const span of textSpans) {
                            const spanText = span.innerText?.trim();
                            if (!spanText || spanText.length <= 1) continue;
                            // Skip if it's just the author name
                            if (spanText === author) continue;
                            // Skip timestamps and actions
                            if (spanText.match(/^\\d+[hdwms]?$/)) continue;
                            if (spanText.match(/^\\d+\\s*(like|repl|day|hour|week|ago)/i)) continue;
                            if (spanText.match(/^View\\s+(all)?/i)) continue;
                            if (spanText.match(/^Hide\\s+repl/i)) continue;
                            if (['like', 'reply', 'translate', 'verified'].includes(spanText.toLowerCase())) continue;

                            // This is likely the comment text
                            if (spanText.length > text.length && spanText.length < 1000) {
                                text = spanText;
                            }
                        }

                        // Fallback: look for any span with meaningful content
                        if (!text) {
                            const allSpans = commentDiv.querySelectorAll('span');
                            for (const span of allSpans) {
                                const spanText = span.innerText?.trim();
                                if (!spanText || spanText.length <= 1) continue;
                                if (spanText === author) continue;
                                if (spanText.match(/^\\d+[hdwms]?$/)) continue;
                                if (spanText.match(/^\\d+\\s*(like|repl|day|hour|week|ago)/i)) continue;
                                if (spanText.match(/^View\\s+(all)?/i)) continue;
                                if (spanText.match(/^Hide\\s+repl/i)) continue;
                                if (['like', 'reply', 'translate', 'verified'].includes(spanText.toLowerCase())) continue;

                                // Check if this is a leaf span (no nested spans with text)
                                const hasNestedText = span.querySelector('span')?.innerText?.trim();
                                if (!hasNestedText && spanText.length > text.length && spanText.length < 1000) {
                                    text = spanText;
                                }
                            }
                        }

                        // Get timestamp
                        const datetime = timeEl.getAttribute('datetime');

                        // Get likes
                        let likes = 0;
                        const spans = commentDiv.querySelectorAll('span');
                        for (const span of spans) {
                            const match = (span.textContent || '').match(/(\\d+)\\s*like/i);
                            if (match) {
                                likes = parseInt(match[1]);
                                break;
                            }
                        }

                        // Check if this is a reply (nested in _a9yo class or has reply indicator)
                        const isReply = !!commentDiv.closest('ul._a9yo') ||
                                       !!commentDiv.closest('li._a9ye') ||
                                       (commentDiv.querySelector('li') && commentDiv.querySelector('li').classList.contains('_a9ye'));

                        // Add if we found meaningful content
                        if (author && text && text.length > 0) {
                            const key = author + ':' + text.substring(0, 50);
                            if (!seenTexts.has(key)) {
                                seenTexts.add(key);
                                comments.push({
                                    index: i,
                                    author: author,
                                    text: text,
                                    datetime: datetime,
                                    likes: likes,
                                    is_reply: isReply
                                });
                                foundComment = true;
                            }
                        }

                        commentDiv = commentDiv.parentElement;
                    }
                }

                return comments;
            }
        ''')

        # Process raw comments
        for i, raw in enumerate(raw_comments):
            if not raw.get('text') and not raw.get('author'):
                continue

            # Extract content ID from current URL
            content_id = None
            current_url = self.current_url
            for pattern in ['/p/', '/reel/', '/tv/']:
                if pattern in current_url:
                    match = re.search(rf'{pattern}([^/]+)/', current_url)
                    if match:
                        content_id = match.group(1)
                        break

            comment = {
                'id': f"{content_id or 'unknown'}_{i}",
                'text': raw.get('text', ''),
                'author': raw.get('author', ''),
                'published_at': None,
                'likes': raw.get('likes', 0),
                'parent_id': None,
                'replies_count': 0,
            }

            # Parse datetime
            if raw.get('datetime'):
                try:
                    comment['published_at'] = datetime.fromisoformat(
                        raw['datetime'].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            comments.append(comment)

        logger.debug(f"COMMENTS EXTRACTED | count={len(comments)}")
        return comments

    def scroll_comments_section(self, max_scrolls: int = 20) -> int:
        """
        Scroll within the comments section to load more comments.

        Args:
            max_scrolls: Maximum number of scroll iterations

        Returns:
            Number of scrolls performed
        """
        scrolls = 0
        previous_count = 0
        no_new_count = 0

        for _ in range(max_scrolls):
            # Get current comment count
            current_count = self.evaluate('''
                () => {
                    const container = document.querySelector('div[role="dialog"]') || document.querySelector('article');
                    if (!container) return 0;
                    return container.querySelectorAll('time').length;
                }
            ''')

            # Scroll the comments container (NOT the page)
            self.evaluate('''
                () => {
                    // First, find the comments container by looking for the scrollable div
                    // Instagram typically uses a div with overflow-y: scroll/auto

                    // Strategy 1: Find scrollable container within dialog
                    const dialog = document.querySelector('div[role="dialog"]');
                    if (dialog) {
                        // Look for divs with overflow scroll/auto within dialog
                        const scrollableDivs = dialog.querySelectorAll('div');
                        for (const div of scrollableDivs) {
                            const style = window.getComputedStyle(div);
                            const hasOverflow = style.overflowY === 'scroll' || style.overflowY === 'auto';
                            const isScrollable = div.scrollHeight > div.clientHeight + 10;
                            if (hasOverflow && isScrollable) {
                                div.scrollTop = div.scrollHeight;
                                return 'scrolled_dialog_div';
                            }
                        }
                    }

                    // Strategy 2: Find the ul containing comments and its scrollable parent
                    const commentLists = document.querySelectorAll('ul');
                    for (const ul of commentLists) {
                        // Check if this ul has time elements (comments have timestamps)
                        if (ul.querySelectorAll('time').length > 0) {
                            // Find scrollable parent
                            let parent = ul.parentElement;
                            while (parent && parent !== document.body) {
                                const style = window.getComputedStyle(parent);
                                const hasOverflow = style.overflowY === 'scroll' || style.overflowY === 'auto';
                                const isScrollable = parent.scrollHeight > parent.clientHeight + 10;
                                if (hasOverflow && isScrollable) {
                                    parent.scrollTop = parent.scrollHeight;
                                    return 'scrolled_comment_parent';
                                }
                                parent = parent.parentElement;
                            }
                        }
                    }

                    // Strategy 3: Look for any div with class containing 'scroll' or specific patterns
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {
                        const style = window.getComputedStyle(div);
                        const hasOverflow = style.overflowY === 'scroll' || style.overflowY === 'auto';
                        const isScrollable = div.scrollHeight > div.clientHeight + 50;
                        // Make sure it's not the whole page
                        const isNotFullPage = div.clientHeight < window.innerHeight * 0.9;
                        if (hasOverflow && isScrollable && isNotFullPage) {
                            div.scrollTop = div.scrollHeight;
                            return 'scrolled_overflow_div';
                        }
                    }

                    // DO NOT fall back to window scroll - we want to stay at top of page
                    // If no scrollable container found, return false
                    return false;
                }
            ''')

            self.wait(1500)
            scrolls += 1

            if current_count == previous_count:
                no_new_count += 1
                if no_new_count >= 3:
                    break
            else:
                no_new_count = 0
                previous_count = current_count

        logger.debug(f"COMMENTS | scrolled {scrolls} times")
        return scrolls

    def expand_all_replies(self, max_clicks: int = 50) -> int:
        """
        Click all "View replies" buttons to expand hidden replies.

        Args:
            max_clicks: Maximum number of reply expansions

        Returns:
            Number of replies expanded
        """
        clicks = 0

        for _ in range(max_clicks):
            clicked = self.evaluate('''
                () => {
                    // First look for specific "View replies" spans with _a9yi class (most reliable)
                    const replySpans = document.querySelectorAll('span._a9yi');
                    for (const span of replySpans) {
                        const text = span.textContent?.toLowerCase() || '';
                        if (text.includes('view') && text.includes('repl')) {
                            const btn = span.closest('button');
                            if (btn) {
                                btn.click();
                                return 'clicked_a9yi_button';
                            }
                            span.click();
                            return 'clicked_a9yi_span';
                        }
                    }

                    // Look for ANY span containing "View replies" text (class-agnostic)
                    const allSpans = document.querySelectorAll('span');
                    for (const span of allSpans) {
                        const text = span.textContent?.toLowerCase() || '';
                        // Match "View replies (N)" or "View N replies"
                        if (text.match(/view.*repl/i) && !text.includes('hide')) {
                            // Try to click parent button first
                            const btn = span.closest('button');
                            if (btn) {
                                btn.click();
                                return 'clicked_text_match_button';
                            }
                            // Try clicking the span itself if it looks clickable
                            const style = window.getComputedStyle(span);
                            if (style.cursor === 'pointer' || span.getAttribute('role') === 'button') {
                                span.click();
                                return 'clicked_text_match_span';
                            }
                            // Last resort - click anyway
                            span.click();
                            return 'clicked_text_match_fallback';
                        }
                    }

                    // Fallback: look for any button with view replies text
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = btn.textContent?.toLowerCase() || '';
                        if (text.includes('view') && (text.includes('repl') || text.includes('more'))) {
                            if (!text.includes('hide')) {
                                btn.click();
                                return 'clicked_button_text';
                            }
                        }
                    }

                    // Also check for clickable spans with role/tabindex
                    const clickableSpans = document.querySelectorAll('span[role="button"], span[tabindex="0"]');
                    for (const span of clickableSpans) {
                        const text = span.textContent?.toLowerCase() || '';
                        if (text.includes('view') && text.includes('repl')) {
                            span.click();
                            return 'clicked_role_span';
                        }
                    }

                    return false;
                }
            ''')

            if clicked:
                clicks += 1
                self.wait(1000)
            else:
                break

        logger.info(f"COMMENTS | expanded {clicks} reply threads")
        return clicks

    def click_view_all_comments(self) -> bool:
        """
        Click "View all X comments" link if present.

        Returns:
            True if clicked
        """
        clicked = self.evaluate('''
            () => {
                const links = document.querySelectorAll('a, span, button');
                for (const el of links) {
                    const text = el.textContent?.toLowerCase() || '';
                    if (text.includes('view all') && text.includes('comment')) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        ''')

        if clicked:
            logger.debug("COMMENTS | clicked 'View all comments'")
            self.wait(2000)
            return True

        return False

    def extract_comments_for_post(self, post_id: str, max_load_clicks: int = 10) -> List[Dict[str, Any]]:
        """
        Extract all comments for current post, loading more if needed.

        Args:
            post_id: Post ID for generating comment IDs
            max_load_clicks: Maximum times to click load more

        Returns:
            List of comment dictionaries
        """
        logger.info(f"EXTRACTING COMMENTS | post_id={post_id}")

        # Wait for page to fully load and React to hydrate
        self.wait(3000)

        # Try to wait for interactive elements that indicate React has loaded
        try:
            self.page.wait_for_selector(
                "article, button, ul[class*='_a9']",
                timeout=5000
            )
        except Exception:
            logger.debug("COMMENTS | interactive elements not found, continuing anyway")

        # Debug: Initial page state
        initial_state = self.evaluate('''
            () => {
                const results = {
                    hasDialog: !!document.querySelector('div[role="dialog"]'),
                    hasArticle: !!document.querySelector('article'),
                    hasMain: !!document.querySelector('main'),
                    totalButtons: document.querySelectorAll('button').length,
                    commentListClasses: [],
                    timeElements: document.querySelectorAll('time').length,
                    pageHtml: '',
                    allUlClasses: [],
                    viewport: `${window.innerWidth}x${window.innerHeight}`
                };

                // Find all ul elements that might be comment lists
                document.querySelectorAll('ul').forEach(ul => {
                    if (ul.className) {
                        results.allUlClasses.push(ul.className.substring(0, 30));
                        if (ul.className.includes('_a9')) {
                            results.commentListClasses.push(ul.className.substring(0, 50));
                        }
                    }
                });

                // Sample of page structure around comments
                const main = document.querySelector('main');
                if (main) {
                    results.pageHtml = main.innerHTML.substring(0, 200);
                }

                return results;
            }
        ''')
        logger.info(f"INITIAL PAGE STATE | {initial_state}")

        # First, click "View all X comments" if it exists
        self.click_view_all_comments()

        # Comments are at the top of the post page, no need to scroll down
        self.wait(1000)

        # Load all comments by clicking "Load more" buttons
        load_clicks = self.load_all_comments(max_load_clicks)
        logger.info(f"LOAD COMMENTS | clicked {load_clicks} times")

        # Scroll within comments section to load more
        scroll_count = self.scroll_comments_section(max_scrolls=10)
        logger.info(f"SCROLL COMMENTS | scrolled {scroll_count} times")

        # Wait for any lazy-loaded content
        self.wait(2000)

        # Scroll through the comment list to trigger lazy loading of reply buttons
        # NOTE: We scroll within the comments container, not the main page
        scroll_result = self.evaluate('''
            () => {
                let scrolledItems = 0;
                let scrollContainer = null;

                // Find the scrollable comments container first
                const dialog = document.querySelector('div[role="dialog"]');
                if (dialog) {
                    const divs = dialog.querySelectorAll('div');
                    for (const div of divs) {
                        const style = window.getComputedStyle(div);
                        const hasOverflow = style.overflowY === 'scroll' || style.overflowY === 'auto';
                        const isScrollable = div.scrollHeight > div.clientHeight + 10;
                        if (hasOverflow && isScrollable) {
                            scrollContainer = div;
                            break;
                        }
                    }
                }

                // Try multiple selectors for comment lists
                const selectors = ['ul._a9ym', 'ul._a9z6', 'ul[class*="_a9"]', 'article ul'];

                for (const sel of selectors) {
                    const lists = document.querySelectorAll(sel);
                    for (const list of lists) {
                        const items = list.querySelectorAll('li');
                        for (const item of items) {
                            if (scrollContainer) {
                                // Scroll within container instead of page
                                const itemRect = item.getBoundingClientRect();
                                const containerRect = scrollContainer.getBoundingClientRect();
                                const scrollTop = item.offsetTop - scrollContainer.offsetTop - (containerRect.height / 2);
                                scrollContainer.scrollTop = Math.max(0, scrollTop);
                            }
                            // Don't use scrollIntoView as it scrolls the page
                            scrolledItems++;
                        }
                    }
                    if (scrolledItems > 0) break;
                }

                return { scrolledItems, hasContainer: !!scrollContainer };
            }
        ''')
        logger.info(f"SCROLL ITEMS | {scroll_result}")
        self.wait(1000)

        # Debug: check what buttons and reply elements exist on the page
        reply_debug = self.evaluate('''
            () => {
                const results = {
                    a9yi_spans: 0,
                    view_reply_buttons: 0,
                    view_reply_text_matches: 0,
                    all_buttons_text: [],
                    reply_containers: 0,
                    has_comment_list: false,
                    total_buttons: 0,
                    total_spans: 0
                };

                // Check for _a9yi class spans (Instagram's reply button text)
                const a9yiSpans = document.querySelectorAll('span._a9yi');
                results.a9yi_spans = a9yiSpans.length;
                a9yiSpans.forEach(s => {
                    results.all_buttons_text.push('_a9yi: ' + s.textContent?.trim().substring(0, 30));
                });

                // Search ALL spans for "View replies" text (class-agnostic)
                const allSpans = document.querySelectorAll('span');
                results.total_spans = allSpans.length;
                allSpans.forEach(span => {
                    const text = span.textContent?.toLowerCase() || '';
                    if (text.match(/view.*repl/i)) {
                        results.view_reply_text_matches++;
                        results.all_buttons_text.push('text_match: ' + text.substring(0, 40));
                    }
                });

                // Check ALL buttons on page for any view/reply text
                const buttons = document.querySelectorAll('button');
                results.total_buttons = buttons.length;
                buttons.forEach(btn => {
                    const text = btn.textContent?.toLowerCase() || '';
                    if (text.includes('view') || text.includes('repl')) {
                        results.view_reply_buttons++;
                        results.all_buttons_text.push('btn: ' + text.substring(0, 30));
                    }
                });

                // Check if ul._a9yo exists (reply container)
                const replyContainers = document.querySelectorAll('ul._a9yo');
                results.reply_containers = replyContainers.length;

                // Check for comment list with various selectors
                const commentList = document.querySelector('ul._a9z6') ||
                                   document.querySelector('ul._a9ym') ||
                                   document.querySelector('article ul');
                results.has_comment_list = !!commentList;

                // Also check for clickable spans that might be reply buttons
                const clickableSpans = document.querySelectorAll('span[role="button"], span[tabindex="0"]');
                clickableSpans.forEach(span => {
                    const text = span.textContent?.toLowerCase() || '';
                    if (text.includes('view') && text.includes('repl')) {
                        results.all_buttons_text.push('clickable_span: ' + text.substring(0, 30));
                    }
                });

                return results;
            }
        ''')
        logger.info(f"REPLY BUTTONS DEBUG | {reply_debug}")

        # Expand all reply threads
        expanded = self.expand_all_replies(max_clicks=30)
        logger.info(f"EXPANDED REPLIES | {expanded} threads")

        # Give it a moment to render
        self.wait(1000)

        # Extract comments
        comments = self.get_comments()

        # Update IDs with post_id
        for i, comment in enumerate(comments):
            comment['id'] = f"{post_id}_{i}"

        logger.info(f"COMMENTS EXTRACTED | post_id={post_id} | count={len(comments)}")
        return comments
