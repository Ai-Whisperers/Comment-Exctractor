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

    def load_all_comments(self, max_clicks: int = 100) -> int:
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

    def _get_comment_debug_info(self) -> Dict[str, Any]:
        """
        Collect debug information about comment elements on the page.

        Returns:
            Dictionary with container info, time elements count, and samples
        """
        return self.evaluate('''
            () => {
                const container = document.querySelector('div[role="dialog"]') || document.querySelector('article') || document.querySelector('main');
                if (!container) return { error: 'No container found' };

                const timeElements = container.querySelectorAll('time');
                const commentCandidates = [];

                timeElements.forEach((time, i) => {
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

    def get_comments(self) -> List[Dict[str, Any]]:
        """
        Extract all visible comments.

        Returns:
            List of comment dictionaries
        """
        # Debug: Log what we can find on the page
        debug_info = self._get_comment_debug_info()
        logger.info(f"COMMENT DEBUG | {debug_info}")

        # Extract raw comments from the DOM
        raw_comments = self._extract_raw_comments()

        # Process and structure the comments
        comments = self._process_raw_comments(raw_comments)

        # Log extraction statistics
        self._log_extraction_stats(comments, raw_comments)

        return comments

    def _extract_raw_comments(self) -> List[Dict[str, Any]]:
        """
        Extract raw comment data from the page using JavaScript.

        Returns:
            List of raw comment dictionaries with author, text, datetime, etc.
        """
        return self.evaluate('''
            () => {
                const comments = [];
                const container = document.querySelector('div[role="dialog"]') || document.querySelector('article') || document.querySelector('main');
                if (!container) return comments;

                const seenTexts = new Set();
                const seenCommentDivs = new Set();
                const timeElements = container.querySelectorAll('time');

                for (let i = 1; i < timeElements.length; i++) {
                    const timeEl = timeElements[i];
                    let commentDiv = timeEl.parentElement;
                    let foundComment = false;

                    for (let level = 0; level < 8 && commentDiv && !foundComment; level++) {
                        if (seenCommentDivs.has(commentDiv)) {
                            commentDiv = commentDiv.parentElement;
                            continue;
                        }

                        // Find author
                        const authorData = (() => {
                            const links = commentDiv.querySelectorAll('a[href^="/"]');
                            for (const link of links) {
                                const href = link.getAttribute('href');
                                if (href && href.match(/^\\/[^\\/]+\\/?$/) &&
                                    !href.includes('/p/') && !href.includes('/reel/') && !href.includes('/explore/')) {
                                    const linkText = link.textContent?.trim() || '';
                                    if (linkText && linkText.length > 0 && linkText.length < 50) {
                                        return {
                                            author: linkText.replace(/Verified$/, '').trim(),
                                            authorUrl: 'https://www.instagram.com' + href
                                        };
                                    }
                                }
                            }
                            return null;
                        })();

                        if (!authorData) {
                            commentDiv = commentDiv.parentElement;
                            continue;
                        }

                        // Find comment text
                        const text = (() => {
                            let bestText = '';
                            const textSpans = commentDiv.querySelectorAll('span[dir="auto"]');
                            for (const span of textSpans) {
                                const spanText = span.innerText?.trim();
                                if (!spanText || spanText.length <= 1) continue;
                                if (spanText === authorData.author) continue;
                                if (spanText.match(/^\\d+[hdwms]?$/)) continue;
                                if (spanText.match(/^\\d+\\s*(like|repl|day|hour|week|ago)/i)) continue;
                                if (spanText.match(/^View\\s+(all)?/i)) continue;
                                if (spanText.match(/^Hide\\s+repl/i)) continue;
                                if (['like', 'reply', 'translate', 'verified'].includes(spanText.toLowerCase())) continue;

                                const isInNestedComment = span.closest('li ul li');
                                if (isInNestedComment && !commentDiv.contains(isInNestedComment)) continue;

                                const nestedText = span.querySelector('span')?.innerText?.trim() || '';
                                const isLeaf = !nestedText || nestedText === spanText;

                                if (isLeaf && spanText.length > bestText.length && spanText.length < 1000) {
                                    bestText = spanText;
                                }
                            }
                            return bestText;
                        })();

                        // Get likes count
                        const likes = (() => {
                            const spans = commentDiv.querySelectorAll('span');
                            for (const span of spans) {
                                const text = (span.textContent || '').trim();
                                let match = text.match(/(\\d+)\\s*likes?/i);
                                if (match) return parseInt(match[1]);

                                if (/^\\d{1,4}$/.test(text) && !text.includes(':')) {
                                    const parent = span.parentElement;
                                    if (parent && (
                                        parent.tagName === 'BUTTON' ||
                                        parent.getAttribute('role') === 'button' ||
                                        parent.closest('button') ||
                                        parent.querySelector('svg') ||
                                        parent.parentElement?.querySelector('svg')
                                    )) {
                                        return parseInt(text);
                                    }
                                }
                            }
                            return 0;
                        })();

                        // Check if reply
                        const replyInfo = (() => {
                            let ulDepth = 0;
                            let parent = commentDiv;
                            while (parent) {
                                if (parent.tagName === 'UL') ulDepth++;
                                parent = parent.parentElement;
                            }

                            const startsWithMention = text.trim().startsWith('@');

                            let liCount = 0;
                            let checkParent = commentDiv;
                            while (checkParent) {
                                if (checkParent.tagName === 'LI') liCount++;
                                checkParent = checkParent.parentElement;
                            }

                            return {
                                isReply: ulDepth > 1 || liCount > 1 || startsWithMention,
                                ulDepth,
                                liCount,
                                startsWithMention
                            };
                        })();

                        if (authorData.author && text && text.length > 0) {
                            const textKey = text.replace(/^@[\\w.]+\\s*/, '').trim().substring(0, 100);

                            if (!seenTexts.has(textKey)) {
                                seenTexts.add(textKey);
                                seenCommentDivs.add(commentDiv);
                                comments.push({
                                    index: i,
                                    author: authorData.author,
                                    author_url: authorData.authorUrl,
                                    text: text,
                                    datetime: timeEl.getAttribute('datetime'),
                                    likes: likes,
                                    is_reply: replyInfo.isReply,
                                    ul_depth: replyInfo.ulDepth,
                                    nested_li_count: replyInfo.liCount,
                                    starts_with_mention: replyInfo.startsWithMention
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

    def _process_raw_comments(self, raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw comment data into structured comment objects.

        Args:
            raw_comments: Raw comment data from JavaScript extraction

        Returns:
            List of processed comment dictionaries
        """
        comments = []
        last_top_level_id = None

        for i, raw in enumerate(raw_comments):
            if not raw.get('text') and not raw.get('author'):
                continue

            # Extract content ID from current URL
            content_id = self._extract_content_id_from_url()
            comment_id = f"{content_id or 'unknown'}_{i}"
            is_reply = raw.get('is_reply', False)

            # Calculate depth level
            depth = 1
            if is_reply:
                depth = 2
                if raw.get('ul_depth', 0) > 2:
                    depth = raw.get('ul_depth', 2)

            comment = {
                'id': comment_id,
                'text': raw.get('text', ''),
                'author': raw.get('author', ''),
                'author_url': raw.get('author_url', ''),
                'published_at': None,
                'likes': raw.get('likes', 0),
                'parent_id': last_top_level_id if is_reply else None,
                'replies_count': 0,
                'is_reply': is_reply,
                'depth': depth,
            }

            if not is_reply:
                last_top_level_id = comment_id

            if raw.get('datetime'):
                try:
                    comment['published_at'] = datetime.fromisoformat(
                        raw['datetime'].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            comments.append(comment)

        # Count replies for each parent
        reply_counts = {}
        for comment in comments:
            if comment.get('parent_id'):
                reply_counts[comment['parent_id']] = reply_counts.get(comment['parent_id'], 0) + 1

        for comment in comments:
            if comment['id'] in reply_counts:
                comment['replies_count'] = reply_counts[comment['id']]

        return comments

    def _extract_content_id_from_url(self) -> Optional[str]:
        """Extract the content ID from the current URL."""
        current_url = self.current_url
        for pattern in ['/p/', '/reel/', '/tv/']:
            if pattern in current_url:
                match = re.search(rf'{pattern}([^/]+)/', current_url)
                if match:
                    return match.group(1)
        return None

    def _log_extraction_stats(self, comments: List[Dict[str, Any]], raw_comments: List[Dict[str, Any]]) -> None:
        """Log statistics about extracted comments."""
        total_replies = sum(1 for c in comments if c.get('parent_id'))
        top_level = len(comments) - total_replies

        ul_depth_detected = sum(1 for r in raw_comments if r.get('ul_depth', 0) > 1)
        legacy_class_detected = sum(1 for r in raw_comments if r.get('has_legacy_class', False))
        mention_detected = sum(1 for r in raw_comments if r.get('starts_with_mention', False))

        logger.debug(
            f"COMMENTS EXTRACTED | total={len(comments)} | top_level={top_level} | replies={total_replies} | "
            f"ul_depth_replies={ul_depth_detected} | legacy_class={legacy_class_detected} | mention_detected={mention_detected}"
        )

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

    def expand_all_replies(self, max_clicks: int = 100) -> int:
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
                    // Use class-agnostic approach to find "View replies" buttons
                    // This is more robust than relying on obfuscated class names like _a9yi

                    // Look for ANY span containing "View replies" text
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
        self.wait(1500)  # Reduced from 3000ms

        # Try to wait for interactive elements that indicate React has loaded
        # Use structural selectors instead of obfuscated class names
        try:
            self.page.wait_for_selector(
                "article, button, div[role='dialog'] ul",
                timeout=5000
            )
        except Exception:
            logger.debug("COMMENTS | interactive elements not found, continuing anyway")
            # Save HTML when interactive elements not found - indicates potential issue
            self.save_on_timeout(
                waiting_for="article, button, div[role='dialog'] ul",
                timeout_ms=5000,
                context=post_id
            )

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
                // Use structural detection instead of relying on obfuscated class names
                document.querySelectorAll('ul').forEach(ul => {
                    if (ul.className) {
                        results.allUlClasses.push(ul.className.substring(0, 30));
                    }
                    // Check if ul contains time elements (comments have timestamps)
                    if (ul.querySelector('time') && ul.querySelectorAll('li').length > 0) {
                        results.commentListClasses.push(ul.className?.substring(0, 50) || 'no-class');
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
        self.wait(500)  # Reduced from 1000ms

        # Load all comments by clicking "Load more" buttons
        load_clicks = self.load_all_comments(max_load_clicks)
        logger.info(f"LOAD COMMENTS | clicked {load_clicks} times")

        # Scroll within comments section to load more
        scroll_count = self.scroll_comments_section(max_scrolls=10)
        logger.info(f"SCROLL COMMENTS | scrolled {scroll_count} times")

        # Wait for any lazy-loaded content
        self.wait(1000)  # Reduced from 2000ms

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
                // Use structural selectors that identify comment lists by their content
                // Comment lists contain: li elements with time elements (timestamps) and anchor links (usernames)
                const findCommentLists = () => {
                    const candidates = [];
                    document.querySelectorAll('ul').forEach(ul => {
                        const hasTimestamps = ul.querySelector('time');
                        const hasListItems = ul.querySelectorAll('li').length > 0;
                        const hasUserLinks = ul.querySelector('a[href^="/"][href$="/"]');
                        if (hasTimestamps && hasListItems && hasUserLinks) {
                            candidates.push(ul);
                        }
                    });
                    // Fallback to article ul if no structural match
                    if (candidates.length === 0) {
                        const articleUl = document.querySelector('article ul');
                        if (articleUl) candidates.push(articleUl);
                    }
                    return candidates;
                };
                const commentLists = findCommentLists();

                for (const list of commentLists) {
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

                // Find spans that contain "View replies" text (class-agnostic approach)
                // The old approach used 'span._a9yi' but these class names change frequently
                let viewReplySpans = 0;
                document.querySelectorAll('span').forEach(span => {
                    const text = span.textContent?.toLowerCase() || '';
                    if (text.match(/view.*\\d+.*repl/i) || text.match(/view repl/i)) {
                        viewReplySpans++;
                        results.all_buttons_text.push('reply_span: ' + span.textContent?.trim().substring(0, 30));
                    }
                });
                results.a9yi_spans = viewReplySpans;

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

                // Check for nested ul elements (reply containers)
                // Reply containers are ul elements inside li elements
                let replyContainerCount = 0;
                document.querySelectorAll('ul li ul').forEach(ul => {
                    if (ul.querySelector('time')) {
                        replyContainerCount++;
                    }
                });
                results.reply_containers = replyContainerCount;

                // Check for comment list using structural detection
                // Comment lists have time elements and multiple li items
                let hasCommentList = false;
                document.querySelectorAll('ul').forEach(ul => {
                    if (ul.querySelector('time') && ul.querySelectorAll('li').length > 0) {
                        hasCommentList = true;
                    }
                });
                // Fallback to article ul
                if (!hasCommentList) {
                    hasCommentList = !!document.querySelector('article ul');
                }
                results.has_comment_list = hasCommentList;

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
        expanded = self.expand_all_replies(max_clicks=100)
        logger.info(f"EXPANDED REPLIES | {expanded} threads")

        # Give it a moment to render
        self.wait(1000)

        # Extract comments
        comments = self.get_comments()

        # Update IDs with post_id
        for i, comment in enumerate(comments):
            comment['id'] = f"{post_id}_{i}"

        logger.info(f"COMMENTS EXTRACTED | post_id={post_id} | count={len(comments)}")

        # Save HTML if no comments found - indicates potential scraping issue
        if len(comments) == 0:
            self.save_debug_html(
                reason="No comments extracted - possible page structure change",
                context=post_id,
                additional_info={
                    "load_clicks": load_clicks,
                    "scroll_count": scroll_count,
                    "expanded_replies": expanded,
                    "initial_state": initial_state,
                }
            )

        return comments
