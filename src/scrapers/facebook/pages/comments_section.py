"""Facebook Comments Section Page Object."""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class CommentsSection(BasePage):
    """Page object for Facebook comment extraction."""

    def __init__(self, page: Page):
        """
        Initialize comments section.

        Args:
            page: Playwright page instance
        """
        super().__init__(page)
        self._js_injected = False

    def extract_comments_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Extract all comments from the current post.

        Args:
            post_id: ID of the parent post

        Returns:
            List of comment dictionaries
        """
        logger.info(f"EXTRACTING COMMENTS | post_id={post_id}")

        # Log initial page state for debugging
        self._log_initial_state()

        # Load more comments first (using batch method)
        loads = self._load_all_comments_batch()
        logger.info(f"LOAD COMMENTS | loaded {loads} batches")

        # Scroll comments section
        scrolls = self._scroll_comments_section()
        logger.info(f"SCROLL COMMENTS | scrolled {scrolls} times")

        # Expand truncated text ("See more" / "Ver más") - batch
        text_expanded = self._expand_truncated_text_batch()
        logger.info(f"EXPANDED TEXT | {text_expanded} comments")

        # Expand replies (using batch method)
        expanded = self._expand_all_replies_batch()
        logger.info(f"EXPANDED REPLIES | {expanded} threads")

        # Extract comments with fallback
        comments = self._extract_comments_with_fallback(post_id)

        # Calculate reply stats
        total_replies = sum(1 for c in comments if c.get('parent_id'))
        top_level = len(comments) - total_replies
        logger.debug(
            f"COMMENTS EXTRACTED | total={len(comments)} | top_level={top_level} | replies={total_replies}"
        )
        logger.info(f"COMMENTS EXTRACTED | post_id={post_id} | count={len(comments)}")

        # Save HTML if no comments found - indicates potential scraping issue
        if len(comments) == 0:
            self.save_debug_html(
                reason="No comments extracted - possible page structure change",
                context=post_id,
                additional_info={
                    "loads": loads,
                    "scrolls": scrolls,
                    "expanded": expanded,
                }
            )

        return comments

    def _log_initial_state(self) -> None:
        """Log initial page state for debugging."""
        try:
            state = self.evaluate('''
                () => {
                    return {
                        hasDialog: !!document.querySelector('div[role="dialog"]'),
                        totalButtons: document.querySelectorAll('div[role="button"]').length,
                        commentContainers: document.querySelectorAll('[aria-label*="Comment"], [role="article"]').length,
                        viewport: window.innerWidth + 'x' + window.innerHeight
                    };
                }
            ''')
            logger.info(f"INITIAL PAGE STATE | {state}")
        except Exception as e:
            logger.debug(f"Could not get initial state: {e}")

    def _load_all_comments(self, max_loads: int = 30) -> int:
        """
        Load all comments by clicking 'View more comments'.

        Args:
            max_loads: Maximum number of times to load more

        Returns:
            Number of times load more was clicked
        """
        loads = 0
        for _ in range(max_loads):
            try:
                # Try different load more selectors
                load_more = self.page.locator(Selectors.Comments.VIEW_MORE_COMMENTS).first
                if load_more.is_visible(timeout=1000):
                    load_more.click()
                    self.wait(800)  # Reduced from 1500ms
                    loads += 1
                    continue

                # Try view previous
                view_prev = self.page.locator(Selectors.Comments.VIEW_PREVIOUS).first
                if view_prev.is_visible(timeout=1000):
                    view_prev.click()
                    self.wait(800)  # Reduced from 1500ms
                    loads += 1
                    continue

                # No more to load
                break

            except Exception as e:
                logger.debug(f"Load more comments stopped: {e}")
                break

        logger.debug(f"COMMENTS | loaded more {loads} times")
        return loads

    def _load_all_comments_batch(self, max_iterations: int = 20) -> int:
        """Load all comments by clicking all 'load more' buttons in batches."""
        total_loads = 0

        for iteration in range(max_iterations):
            # Click ALL "view more" / "view previous" buttons at once
            clicked = self.evaluate('''
                () => {
                    const patterns = [
                        /view\\s+more\\s+comment/i,
                        /ver\\s+más\\s+comentario/i,
                        /view\\s+previous/i,
                        /ver\\s+anterior/i,
                        /\\d+\\s+more\\s+comment/i,
                        /\\d+\\s+comentarios?\\s+más/i,
                        /see\\s+more\\s+comment/i,
                        /mostrar\\s+más/i,
                        /load\\s+more/i,
                        /cargar\\s+más/i,
                        /view\\s+all/i,
                        /ver\\s+todos/i
                    ];

                    const buttons = document.querySelectorAll('div[role="button"], span[role="button"]');
                    let count = 0;

                    for (const btn of buttons) {
                        const text = btn.textContent?.trim() || '';
                        if (text.length > 50) continue;

                        for (const pattern of patterns) {
                            if (pattern.test(text)) {
                                try {
                                    btn.click();
                                    count++;
                                } catch(e) {}
                                break;
                            }
                        }
                    }
                    return count;
                }
            ''')

            if clicked == 0:
                break

            total_loads += clicked
            logger.debug(f"COMMENTS | batch loaded {clicked} more (iteration {iteration + 1})")
            self.wait(1500)  # Wait for comments to load

        logger.info(f"COMMENTS | loaded {total_loads} comment batches in {iteration + 1 if total_loads else 0} iterations")
        return total_loads

    def _scroll_comments_section(self, max_scrolls: int = 10) -> int:
        """
        Scroll within the comments section to load more comments.

        This scrolls only the comments container, not the whole page,
        to avoid loading unrelated content.

        Args:
            max_scrolls: Maximum number of scroll iterations

        Returns:
            Number of scrolls performed
        """
        scrolls = 0

        # Try to find and scroll the comments container specifically
        try:
            scrolled = self.evaluate('''
                () => {
                    // Find the comments section container
                    const selectors = [
                        'div[role="dialog"] [role="list"]',
                        'div[aria-label*="Comment"] ul',
                        '[data-pagelet*="Comment"] ul',
                        'ul[class*="comment"]',
                        // Fallback to any scrollable container with comments
                        'div[role="dialog"]'
                    ];

                    let container = null;
                    for (const sel of selectors) {
                        const elem = document.querySelector(sel);
                        if (elem && elem.scrollHeight > elem.clientHeight) {
                            container = elem;
                            break;
                        }
                    }

                    if (container) {
                        // Return the container selector for repeated scrolling
                        return 'found';
                    }
                    return 'not_found';
                }
            ''')

            if scrolled == 'found':
                logger.debug("COMMENTS | found scrollable comments container")
            else:
                logger.debug("COMMENTS | no scrollable container found, using page scroll")
        except Exception as e:
            logger.debug(f"COMMENTS | container detection failed: {e}")

        # Perform scrolling - only scroll comment containers, NEVER the page
        for _ in range(max_scrolls):
            try:
                # Only scroll comments container, do NOT scroll the page
                scroll_result = self.evaluate('''
                    () => {
                        // Find comments container - only scroll if we find one
                        const selectors = [
                            'div[role="dialog"] [role="list"]',
                            'div[aria-label*="Comment"] ul',
                            '[data-pagelet*="Comment"] ul',
                            'div[role="dialog"]'
                        ];

                        for (const sel of selectors) {
                            const elem = document.querySelector(sel);
                            if (elem && elem.scrollHeight > elem.clientHeight) {
                                const beforeScroll = elem.scrollTop;
                                elem.scrollTop += 500;
                                return elem.scrollTop !== beforeScroll ? 'scrolled' : 'at_bottom';
                            }
                        }

                        // No scrollable container found - do NOT scroll the page
                        return 'no_container';
                    }
                ''')

                if scroll_result == 'at_bottom':
                    logger.debug(f"COMMENTS | reached bottom after {scrolls} scrolls")
                    break

                if scroll_result == 'no_container':
                    logger.debug("COMMENTS | no scrollable container found, stopping")
                    break

                scrolls += 1
                self.wait(500)  # Reduced from 800ms

            except Exception as e:
                logger.debug(f"COMMENTS | scroll error: {e}")
                break

        logger.debug(f"COMMENTS | scrolled {scrolls} times")
        return scrolls

    def _expand_truncated_text(self, max_expansions: int = 20) -> int:
        """
        Expand truncated comment text by clicking 'See more' / 'Ver más' buttons.

        This reveals the full text of comments that were truncated with ellipsis.

        Args:
            max_expansions: Maximum number of text expansions to perform

        Returns:
            Number of text expansions performed
        """
        expanded = 0

        # Log initial state for debugging
        try:
            debug_info = self.evaluate('''
                () => {
                    const buttons = [];
                    const allElements = document.querySelectorAll('div[role="button"], span[role="button"], span');

                    for (const elem of allElements) {
                        const text = elem.textContent?.toLowerCase().trim() || '';
                        if ((text.includes('see more') || text.includes('ver más') ||
                             text.includes('show more') || text.includes('mostrar más') ||
                             text === 'more' || text === 'más') && text.length < 30) {
                            buttons.push(text);
                        }
                    }

                    return {
                        see_more_buttons: buttons.length,
                        button_samples: buttons.slice(0, 5)
                    };
                }
            ''')
            logger.info(f"SEE MORE BUTTONS DEBUG | {debug_info}")
        except Exception as e:
            logger.debug(f"Could not get see more button debug info: {e}")

        for _ in range(max_expansions):
            try:
                # Find and click "See more" / "Ver más" buttons within comment text
                clicked = self.evaluate('''
                    () => {
                        // Patterns for truncated text expansion - English and Spanish
                        const patterns = [
                            /^see more$/i,
                            /^show more$/i,
                            /^ver más$/i,
                            /^mostrar más$/i,
                            /^more$/i,
                            /^más$/i,
                            /see more\\.{0,3}$/i,
                            /ver más\\.{0,3}$/i
                        ];

                        // Look in both button elements and plain spans
                        const elements = document.querySelectorAll(
                            'div[role="button"], span[role="button"], span[dir="auto"], span'
                        );

                        for (const elem of elements) {
                            const text = elem.textContent?.trim() || '';

                            // Skip if text is too long (not a "see more" button)
                            if (text.length > 30) continue;

                            // Skip elements that are hidden or not in comments section
                            if (elem.offsetParent === null) continue;

                            for (const pattern of patterns) {
                                if (pattern.test(text)) {
                                    // Make sure this is in a comment context, not the main post
                                    const inComment = elem.closest('[aria-label*="Comment"], [role="article"]');
                                    if (inComment || elem.closest('ul') || elem.closest('[role="list"]')) {
                                        elem.click();
                                        return true;
                                    }
                                }
                            }
                        }

                        return false;
                    }
                ''')

                if clicked:
                    expanded += 1
                    self.wait(400)  # Short wait for text to expand
                else:
                    break

            except Exception as e:
                logger.debug(f"Error expanding truncated text: {e}")
                break

        logger.info(f"COMMENTS | expanded {expanded} truncated texts")
        return expanded

    def _expand_truncated_text_batch(self, max_iterations: int = 5) -> int:
        """Expand all truncated text in batches for efficiency."""
        total_expanded = 0

        for iteration in range(max_iterations):
            clicked = self.evaluate('''
                () => {
                    const patterns = [
                        /^see more$/i,
                        /^show more$/i,
                        /^ver más$/i,
                        /^mostrar más$/i,
                        /^more$/i,
                        /^más$/i
                    ];

                    const elements = document.querySelectorAll(
                        'div[role="button"], span[role="button"], span[dir="auto"], span'
                    );
                    let count = 0;

                    for (const elem of elements) {
                        const text = elem.textContent?.trim() || '';
                        if (text.length > 30) continue;
                        if (elem.offsetParent === null) continue;

                        for (const pattern of patterns) {
                            if (pattern.test(text)) {
                                const inComment = elem.closest('[aria-label*="Comment"], [role="article"]');
                                if (inComment || elem.closest('ul') || elem.closest('[role="list"]')) {
                                    try {
                                        elem.click();
                                        count++;
                                    } catch(e) {}
                                }
                                break;
                            }
                        }
                    }
                    return count;
                }
            ''')

            if clicked == 0:
                break

            total_expanded += clicked
            self.wait(500)

        logger.info(f"COMMENTS | batch expanded {total_expanded} truncated texts")
        return total_expanded

    def _expand_all_replies(self, max_expansions: int = 30) -> int:
        """
        Expand all reply threads by clicking 'View X replies' buttons.

        Args:
            max_expansions: Maximum number of reply threads to expand

        Returns:
            Number of reply threads expanded
        """
        expanded = 0

        # Log reply button debug info
        try:
            debug_info = self.evaluate('''
                () => {
                    const buttons = [];
                    const allButtons = document.querySelectorAll('div[role="button"], span');

                    for (const btn of allButtons) {
                        const text = btn.textContent?.toLowerCase() || '';
                        if (text.includes('view') && (text.includes('repl') || text.includes('more'))) {
                            buttons.push(text.substring(0, 50));
                        }
                    }

                    return {
                        view_reply_buttons: buttons.length,
                        button_samples: buttons.slice(0, 5)
                    };
                }
            ''')
            logger.info(f"REPLY BUTTONS DEBUG | {debug_info}")
        except Exception as e:
            logger.debug(f"Could not get reply button debug info: {e}")

        for _ in range(max_expansions):
            try:
                # Find "View X replies" or similar buttons
                clicked = self.evaluate('''
                    () => {
                        // Look for reply expansion buttons - English and Spanish
                        const patterns = [
                            // English reply patterns
                            /view\\s+\\d+\\s+repl/i,
                            /view\\s+more\\s+repl/i,
                            /\\d+\\s+repl/i,
                            /view\\s+repl/i,
                            /see\\s+previous\\s+repl/i,
                            /\\d+\\s+previous\\s+repl/i,
                            /\\d+\\s+more\\s+repl/i,
                            // Spanish reply patterns
                            /ver\\s+\\d+\\s+respuesta/i,
                            /ver\\s+más\\s+respuesta/i,
                            /\\d+\\s+respuesta/i,
                            /ver\\s+respuesta/i,
                            /ver\\s+anteriores/i,
                            /\\d+\\s+respuestas?\\s+anterior/i,
                            /\\d+\\s+más\\s+respuesta/i,
                            // Numbered comment variations (English)
                            /\\d+\\s+more\\s+comment/i,
                            /view\\s+\\d+\\s+comment/i,
                            /see\\s+\\d+\\s+comment/i,
                            // Numbered comment variations (Spanish)
                            /\\d+\\s+más\\s+comentario/i,
                            /ver\\s+\\d+\\s+comentario/i,
                            /\\d+\\s+comentarios?\\s+más/i
                        ];

                        const buttons = document.querySelectorAll('div[role="button"], span[role="button"]');

                        for (const btn of buttons) {
                            const text = btn.textContent?.trim() || '';
                            for (const pattern of patterns) {
                                if (pattern.test(text)) {
                                    btn.click();
                                    return true;
                                }
                            }
                        }

                        return false;
                    }
                ''')

                if clicked:
                    expanded += 1
                    self.wait(600)  # Reduced from 1000ms
                else:
                    break

            except Exception as e:
                logger.debug(f"Error expanding replies: {e}")
                break

        logger.info(f"COMMENTS | expanded {expanded} reply threads")
        return expanded

    def _expand_all_replies_batch(self, max_iterations: int = 5) -> int:
        """Expand all reply threads in batches for efficiency."""
        total_expanded = 0

        for iteration in range(max_iterations):
            # Click ALL visible reply buttons in one JS call
            clicked = self.evaluate('''
                () => {
                    const patterns = [
                        /view\\s+\\d+\\s+repl/i,
                        /ver\\s+\\d+\\s+respuesta/i,
                        /\\d+\\s+more\\s+repl/i,
                        /\\d+\\s+respuestas?\\s+más/i,
                        /see\\s+previous\\s+repl/i,
                        /ver\\s+anteriores/i,
                        /view\\s+more\\s+repl/i,
                        /\\d+\\s+repl/i,
                        /\\d+\\s+respuesta/i
                    ];

                    const buttons = document.querySelectorAll('div[role="button"], span[role="button"]');
                    let count = 0;

                    for (const btn of buttons) {
                        const text = btn.textContent?.trim() || '';
                        if (text.length > 50) continue;

                        for (const pattern of patterns) {
                            if (pattern.test(text)) {
                                try {
                                    btn.click();
                                    count++;
                                } catch(e) {}
                                break;
                            }
                        }
                    }
                    return count;
                }
            ''')

            if clicked == 0:
                break

            total_expanded += clicked
            logger.debug(f"COMMENTS | batch expanded {clicked} replies (iteration {iteration + 1})")
            self.wait(1000)  # Single wait for entire batch to load

        logger.info(f"COMMENTS | expanded {total_expanded} reply threads in {iteration + 1 if total_expanded else 0} batches")
        return total_expanded

    def _extract_comments_with_fallback(self, post_id: str) -> List[Dict[str, Any]]:
        """Extract comments with multi-level fallback."""

        # Level 1: Full JS extraction
        try:
            comments = self._extract_comments_js(post_id)
            if comments:
                return comments
            logger.warning(f"JS extraction returned 0 comments for {post_id}")
        except Exception as e:
            logger.warning(f"JS extraction failed: {e}")

        # Level 2: DOM-based fallback
        try:
            comments = self._extract_comments_fallback_dom(post_id)
            if comments:
                logger.info(f"FALLBACK DOM | extracted {len(comments)} comments")
                return comments
        except Exception as e:
            logger.warning(f"DOM fallback failed: {e}")

        # Level 3: Basic text extraction
        return self._extract_comments_basic(post_id)

    def _extract_comments_fallback_dom(self, post_id: str) -> List[Dict[str, Any]]:
        """Fallback extraction using Playwright locators when JS fails."""
        comments = []

        try:
            comment_elements = self.page.locator(
                '[aria-label*="Comment"], [role="article"]'
            ).all()

            for i, elem in enumerate(comment_elements):
                try:
                    # Get text
                    text_locator = elem.locator('div[dir="auto"]').first
                    text = text_locator.text_content() if text_locator.count() > 0 else ""

                    if not text or len(text.strip()) < 3:
                        continue

                    # Get author
                    author_locator = elem.locator('a[role="link"] span').first
                    author = author_locator.text_content() if author_locator.count() > 0 else "unknown"

                    comments.append({
                        'id': f"{post_id}_c{i}",
                        'author': author.strip() if author else "unknown",
                        'author_url': '',
                        'text': text.strip(),
                        'published_at': None,
                        'likes': 0,
                        'parent_id': None,
                        'replies_count': 0,
                        'depth': 1
                    })

                except Exception as e:
                    logger.debug(f"Failed to extract comment {i}: {e}")
                    continue

            return comments

        except Exception as e:
            logger.warning(f"Fallback DOM extraction failed: {e}")
            return []

    def _extract_comments_basic(self, post_id: str) -> List[Dict[str, Any]]:
        """Basic text-only extraction as last resort."""
        try:
            # Get all visible text that looks like comments
            texts = self.evaluate('''
                () => {
                    const results = [];
                    const elements = document.querySelectorAll('div[dir="auto"]');

                    for (const elem of elements) {
                        const text = elem.textContent?.trim();
                        if (text && text.length > 10 && text.length < 2000) {
                            const lower = text.toLowerCase();
                            if (!lower.includes('like') && !lower.includes('reply') &&
                                !lower.includes('share') && !lower.includes('comment') &&
                                lower !== 'me gusta' && lower !== 'responder') {
                                results.push(text);
                            }
                        }
                    }
                    return [...new Set(results)];
                }
            ''')

            comments = []
            for i, text in enumerate(texts):
                comments.append({
                    'id': f"{post_id}_c{i}",
                    'author': 'unknown',
                    'author_url': '',
                    'text': text,
                    'published_at': None,
                    'likes': 0,
                    'parent_id': None,
                    'replies_count': 0,
                    'depth': 1
                })

            logger.info(f"FALLBACK BASIC | extracted {len(comments)} text blocks")
            return comments

        except Exception as e:
            logger.warning(f"Basic extraction failed: {e}")
            return []

    def _extract_comments_js(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Extract comments using JavaScript for better performance.

        Args:
            post_id: ID of the parent post

        Returns:
            List of comment dictionaries
        """
        try:
            # First, get diagnostic info about page structure
            page_diagnostics = self.evaluate('''
                () => {
                    return {
                        hasCommentContainers: document.querySelectorAll('[aria-label*="Comment"], [role="article"]').length,
                        hasDialogs: document.querySelectorAll('div[role="dialog"]').length,
                        hasCommentInput: !!document.querySelector('[aria-label*="comment" i], [placeholder*="comment" i]'),
                        totalButtons: document.querySelectorAll('div[role="button"]').length,
                        hasArticles: document.querySelectorAll('article, [role="article"]').length,
                        bodyText: document.body.innerText.substring(0, 500),
                        url: window.location.href
                    };
                }
            ''')

            # Log diagnostics for quality validation
            logger.debug(f"PAGE DIAGNOSTICS | containers={page_diagnostics.get('hasCommentContainers', 0)} | "
                        f"dialogs={page_diagnostics.get('hasDialogs', 0)} | "
                        f"articles={page_diagnostics.get('hasArticles', 0)}")

            # Validate page structure - warn if something looks off
            if page_diagnostics.get('hasCommentContainers', 0) == 0 and page_diagnostics.get('hasArticles', 0) == 0:
                logger.warning(f"QUALITY CHECK FAILED | No comment containers found on page - possible structure change")
                self.save_debug_html(
                    reason="No comment containers found",
                    context=post_id,
                    additional_info=page_diagnostics
                )

            comments_data = self.evaluate('''
                () => {
                    const comments = [];
                    const seenTexts = new Set();

                    // Find all comment containers
                    const commentElements = document.querySelectorAll('[aria-label*="Comment"], [role="article"]');

                    commentElements.forEach((elem, index) => {
                        try {
                            // Get author - use multiple strategies
                            let author = 'unknown';
                            let authorUrl = '';

                            // Strategy 1: Look for profile links (most reliable)
                            const profileLinks = elem.querySelectorAll('a[href*="/user/"], a[href*="/profile.php"], a[href*="facebook.com/"]');
                            for (const link of profileLinks) {
                                const href = link.getAttribute('href') || '';
                                // Skip non-profile links
                                if (href.includes('/comment') || href.includes('/posts/') || href.includes('/photo')) continue;

                                // Get text from the link or its spans
                                let linkText = '';
                                const spans = link.querySelectorAll('span');
                                for (const span of spans) {
                                    const text = span.textContent.trim();
                                    if (text && text.length > 1 && text.length < 100 && !text.match(/^\\d+$/)) {
                                        linkText = text;
                                        break;
                                    }
                                }
                                if (!linkText) linkText = link.textContent.trim();

                                // Validate it looks like a name (not a number, not too short)
                                if (linkText && linkText.length > 1 && !linkText.match(/^\\d+$/) && !linkText.match(/^(like|reply|share|me gusta|responder|compartir)$/i)) {
                                    author = linkText;
                                    authorUrl = href.startsWith('http') ? href : 'https://www.facebook.com' + href;
                                    break;
                                }
                            }

                            // Strategy 2: Fallback to first link with role="link" containing a name-like span
                            if (author === 'unknown') {
                                const links = elem.querySelectorAll('a[role="link"]');
                                for (const link of links) {
                                    const spans = link.querySelectorAll('span');
                                    for (const span of spans) {
                                        const text = span.textContent.trim();
                                        // Must look like a name: 2+ chars, not all digits, not a button label
                                        if (text && text.length > 1 && text.length < 100 &&
                                            !text.match(/^\\d+$/) &&
                                            !text.match(/^(like|reply|share|me gusta|responder|compartir|\\d+\\s*(h|d|w|m|min|hr))$/i)) {
                                            author = text;
                                            const href = link.getAttribute('href');
                                            if (href) {
                                                authorUrl = href.startsWith('http') ? href : 'https://www.facebook.com' + href;
                                            }
                                            break;
                                        }
                                    }
                                    if (author !== 'unknown') break;
                                }
                            }

                            // Strategy 3: Look for strong or bold text at the beginning (often used for names)
                            if (author === 'unknown') {
                                const strongText = elem.querySelector('strong, b, span[style*="font-weight"]');
                                if (strongText) {
                                    const text = strongText.textContent.trim();
                                    if (text && text.length > 1 && text.length < 100) {
                                        author = text;
                                    }
                                }
                            }

                            // Get comment text - be more thorough
                            let text = '';
                            const textElements = elem.querySelectorAll('div[dir="auto"]');
                            for (const textEl of textElements) {
                                const content = textEl.textContent.trim();
                                if (content && content.length > text.length && content.length < 2000) {
                                    // Skip only if content is EXACTLY a button label (not a real comment)
                                    const lowerContent = content.toLowerCase();
                                    const isButtonText = lowerContent === 'like' || lowerContent === 'reply' ||
                                                        lowerContent === 'me gusta' || lowerContent === 'responder' ||
                                                        lowerContent === 'share' || lowerContent === 'compartir' ||
                                                        /^\\d+\\s*(like|me gusta|reply|responder|share|compartir)s?$/i.test(content);
                                    if (!isButtonText) {
                                        text = content;
                                    }
                                }
                            }

                            // Skip if no text
                            if (!text || text.length < 2) return;

                            // Skip duplicates
                            const key = author + ':' + text.substring(0, 50);
                            if (seenTexts.has(key)) return;
                            seenTexts.add(key);

                            // Get timestamp - try multiple approaches
                            let timestamp = null;

                            // Method 1: Look for link with comment_id (most reliable)
                            const timeLink = elem.querySelector('a[href*="comment_id"]');
                            if (timeLink) {
                                timestamp = timeLink.textContent.trim();
                            }

                            // Method 2: Look for aria-label with time info
                            if (!timestamp) {
                                const timeElements = elem.querySelectorAll('[aria-label]');
                                for (const el of timeElements) {
                                    const label = el.getAttribute('aria-label') || '';
                                    // Look for date/time patterns in aria-label
                                    if (label.match(/\\d{1,2}[:\\/\\-]\\d{1,2}|\\d{4}|january|february|march|april|may|june|july|august|september|october|november|december|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre/i)) {
                                        timestamp = label;
                                        break;
                                    }
                                }
                            }

                            // Method 3: Look for time-like text patterns in links
                            if (!timestamp) {
                                const allLinks = elem.querySelectorAll('a');
                                for (const link of allLinks) {
                                    const linkText = link.textContent.trim();
                                    // Match patterns like "1h", "2d", "3w", "29 sem", "1 hr", "2 days", "Nov 15", etc.
                                    // Include Spanish abbreviations: sem (semana), min, h, d, a (año)
                                    if (linkText.match(/^\\d+\\s*(h|d|w|m|y|hr|min|hour|day|week|month|year|hora|día|sem|semana|mes|año|a)s?$/i) ||
                                        linkText.match(/^(just now|ahora|ayer|yesterday|today|hoy)$/i) ||
                                        linkText.match(/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\\s+\\d{1,2}/i) ||
                                        linkText.match(/^\\d{1,2}\\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)/i)) {
                                        timestamp = linkText;
                                        break;
                                    }
                                }
                            }

                            // Method 4: Look for spans with time patterns (broader matching)
                            if (!timestamp) {
                                const spans = elem.querySelectorAll('span');
                                for (const span of spans) {
                                    const spanText = span.textContent.trim();
                                    // Skip if too long (not a timestamp)
                                    if (spanText.length > 30) continue;

                                    if (spanText.match(/^\\d+\\s*(h|d|w|m|y|hr|min|hour|day|week|month|year|hora|día|sem|semana|mes|año|a)s?$/i) ||
                                        spanText.match(/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\s+\\d{1,2}/i) ||
                                        spanText.match(/^\\d{1,2}\\s*[:\\/\\-]\\s*\\d{1,2}/i)) {
                                        timestamp = spanText;
                                        break;
                                    }
                                }
                            }

                            // Method 5: Look for abbr or time elements
                            if (!timestamp) {
                                const timeEl = elem.querySelector('abbr[data-utime], time, [datetime]');
                                if (timeEl) {
                                    timestamp = timeEl.getAttribute('title') || timeEl.getAttribute('datetime') || timeEl.textContent.trim();
                                }
                            }

                            // Get likes - look for reaction count
                            let likes = 0;
                            const likeSpan = elem.querySelector('span[aria-label*="reaction"]');
                            if (likeSpan) {
                                const match = likeSpan.textContent.match(/\\d+/);
                                if (match) likes = parseInt(match[0]);
                            }

                            // Detect if this is a reply using offsetLeft position
                            // Facebook uses consistent indentation for replies vs top-level comments
                            // Top-level comments are around 794px from left, replies are ~846px (52px more)
                            const rect = elem.getBoundingClientRect();
                            const offsetLeft = Math.round(rect.left);

                            // Also check if text starts with @mention (common for replies)
                            const startsWithMention = text.trim().startsWith('@');

                            // We'll determine the threshold dynamically based on the minimum offset seen
                            // For now, we'll return the raw offset and determine replies in post-processing
                            const nestingDepth = 0;  // Will be calculated based on offset

                            // Debug: capture all link texts and position info for first 10 comments
                            let debugLinks = [];
                            let debugOffsetLeft = 0;
                            if (index < 10) {
                                const allLinks = elem.querySelectorAll('a');
                                allLinks.forEach(link => {
                                    const linkText = link.textContent.trim();
                                    const href = link.getAttribute('href') || '';
                                    if (linkText && linkText.length < 100) {
                                        debugLinks.push({text: linkText, href: href.substring(0, 50)});
                                    }
                                });
                                // Get the actual left offset from viewport
                                const rect = elem.getBoundingClientRect();
                                debugOffsetLeft = Math.round(rect.left);
                            }

                            comments.push({
                                author: author,
                                author_url: authorUrl,
                                text: text,
                                timestamp: timestamp,
                                likes: likes,
                                index: index,
                                offset_left: offsetLeft,
                                starts_with_mention: startsWithMention,
                                debug_links: debugLinks
                            });
                        } catch (e) {
                            // Skip problematic elements
                        }
                    });

                    return comments;
                }
            ''')

            # Process comments with parent tracking
            processed = []
            last_top_level_id = None

            # Determine reply threshold based on offset_left values
            # Find the minimum offset (top-level comments)
            if comments_data:
                offsets = [c.get('offset_left', 0) for c in comments_data if c.get('offset_left', 0) > 0]
                min_offset = min(offsets) if offsets else 0
                # Replies are typically 30-60px more indented than top-level
                reply_threshold = min_offset + 30

                timestamp_count = sum(1 for c in comments_data if c.get('timestamp'))
                logger.debug(f"JS EXTRACTION | total={len(comments_data)} | with_timestamp={timestamp_count}")
                logger.debug(f"  Offset analysis: min={min_offset}px | reply_threshold={reply_threshold}px")

                # Log first 10 comments with offset for debugging
                for idx, c in enumerate(comments_data[:10]):
                    offset_left = c.get('offset_left', 0)
                    is_reply = offset_left > reply_threshold
                    logger.debug(f"  Comment {idx}: timestamp='{c.get('timestamp')}' | offset={offset_left}px | reply={is_reply} | author={c.get('author', '')[:20]}")
            else:
                min_offset = 0
                reply_threshold = 0

            for i, comment in enumerate(comments_data):
                text = comment.get('text', '').strip()

                # Skip empty
                if not text:
                    continue

                comment_id = f"{post_id}_c{i}"

                # Determine if this is a reply based on offset_left
                offset_left = comment.get('offset_left', 0)
                is_reply = offset_left > reply_threshold or comment.get('starts_with_mention', False)

                # Calculate depth level: 1 = top-level, 2 = reply
                depth = 2 if is_reply else 1

                processed.append({
                    'id': comment_id,
                    'author': comment.get('author', 'unknown'),
                    'author_url': comment.get('author_url', ''),
                    'text': text,
                    'published_at': self._parse_timestamp(comment.get('timestamp')),
                    'likes': comment.get('likes', 0),
                    'parent_id': last_top_level_id if is_reply else None,
                    'replies_count': 0,
                    'depth': depth,
                })

                # Track the last top-level comment for reply association
                if not is_reply:
                    last_top_level_id = comment_id

            # Second pass: count replies for each parent
            reply_counts = {}
            for comment in processed:
                if comment.get('parent_id'):
                    parent = comment['parent_id']
                    reply_counts[parent] = reply_counts.get(parent, 0) + 1

            for comment in processed:
                if comment['id'] in reply_counts:
                    comment['replies_count'] = reply_counts[comment['id']]

            # Quality validation - check if extraction seems healthy
            expected_containers = page_diagnostics.get('hasCommentContainers', 0)
            actual_comments = len(processed)

            # Warn if we found containers but extracted no comments
            if expected_containers > 5 and actual_comments == 0:
                logger.warning(f"QUALITY CHECK | Found {expected_containers} containers but extracted 0 comments")
                self.save_debug_html(
                    reason=f"Mismatch: {expected_containers} containers, 0 comments",
                    context=post_id,
                    additional_info={
                        "expected_containers": expected_containers,
                        "actual_comments": actual_comments,
                        "page_diagnostics": page_diagnostics
                    }
                )

            # Warn if extraction rate is suspiciously low
            elif expected_containers > 10 and actual_comments < expected_containers * 0.1:
                logger.warning(f"QUALITY CHECK | Low extraction rate: {actual_comments}/{expected_containers} "
                              f"({actual_comments/expected_containers*100:.1f}%)")
                # Save debug HTML for analysis
                self.save_debug_html(
                    reason=f"Low extraction rate: {actual_comments}/{expected_containers}",
                    context=f"{post_id}_low_rate",
                    additional_info={
                        "expected_containers": expected_containers,
                        "actual_comments": actual_comments,
                        "extraction_rate": actual_comments/expected_containers*100
                    }
                )

            # Check for anomalies in comment data
            comments_with_text = sum(1 for c in processed if len(c.get('text', '')) > 5)
            comments_with_author = sum(1 for c in processed if c.get('author') != 'unknown')

            if actual_comments > 0:
                text_rate = comments_with_text / actual_comments * 100
                author_rate = comments_with_author / actual_comments * 100

                if text_rate < 50:
                    logger.warning(f"QUALITY CHECK | Only {text_rate:.1f}% of comments have text > 5 chars")
                    # Save debug HTML for text extraction issues
                    self.save_debug_html(
                        reason=f"Low text rate: {text_rate:.1f}%",
                        context=f"{post_id}_low_text",
                        additional_info={
                            "text_rate": text_rate,
                            "comments_with_text": comments_with_text,
                            "total_comments": actual_comments
                        }
                    )
                if author_rate < 30:
                    logger.warning(f"QUALITY CHECK | Only {author_rate:.1f}% of comments have known authors")
                    # Save debug HTML for author extraction issues
                    self.save_debug_html(
                        reason=f"Low author rate: {author_rate:.1f}%",
                        context=f"{post_id}_low_authors",
                        additional_info={
                            "author_rate": author_rate,
                            "comments_with_author": comments_with_author,
                            "total_comments": actual_comments
                        }
                    )

            return processed

        except Exception as e:
            logger.warning(f"JS comment extraction failed: {e}")
            self.save_on_error(e, context=post_id)
            return []

    def _parse_timestamp(self, time_text: Optional[str]) -> Optional[datetime]:
        """Parse Facebook timestamp (English and Spanish)."""
        if not time_text:
            return None

        from datetime import timedelta
        now = datetime.now()
        time_text = time_text.lower().strip()

        # Pattern to extract numbers
        number_pattern = r"(\d+)"

        try:
            # English and Spanish "just now"
            if "just now" in time_text or "ahora" in time_text or "hace un momento" in time_text:
                return now

            # English and Spanish "yesterday"
            if "yesterday" in time_text or "ayer" in time_text:
                return now - timedelta(days=1)

            match = re.search(number_pattern, time_text)
            if not match:
                return None

            value = int(match.group(1))

            # Minutes - English: "min", "m" | Spanish: "min"
            if "min" in time_text or (time_text.endswith("m") and "h" not in time_text):
                return now - timedelta(minutes=value)
            # Hours - English: "h", "hour" | Spanish: "hora"
            elif "h" in time_text or "hour" in time_text or "hora" in time_text:
                return now - timedelta(hours=value)
            # Days - English: "d", "day" | Spanish: "día", "dia"
            elif "d" in time_text or "day" in time_text or "día" in time_text or "dia" in time_text:
                return now - timedelta(days=value)
            # Weeks - English: "w", "week" | Spanish: "sem", "semana"
            elif "w" in time_text or "week" in time_text or "sem" in time_text:
                return now - timedelta(weeks=value)
            # Months - English: "month" | Spanish: "mes"
            elif "month" in time_text or "mes" in time_text:
                return now - timedelta(days=value * 30)
            # Years - English: "y", "year" | Spanish: "año"
            elif "y" in time_text or "year" in time_text or "año" in time_text:
                return now - timedelta(days=value * 365)
        except Exception:
            pass

        return None
