"""Post Modal Page Object for Instagram post viewing."""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from playwright.sync_api import Page

from .base_page import BasePage
from ..selectors import Selectors

logger = logging.getLogger(__name__)


class PostModal(BasePage):
    """Page Object for Instagram post modal/dialog."""

    def get_post_id(self) -> Optional[str]:
        """
        Get current content ID (post, reel, or IGTV).

        Returns:
            Content ID or None
        """
        # Try URL first - check all content patterns
        content_id = self.extract_content_id_from_url()
        if content_id:
            return content_id

        # Try modal links - check all content types
        try:
            # Try to find any content link in modal
            modal_link = self.query_selector(Selectors.PostModal.POST_LINK_IN_MODAL)
            if modal_link:
                href = modal_link.get_attribute('href')
                content_id = self._extract_id_from_href(href)
                if content_id:
                    return content_id

            # Try time link
            time_link = self.query_selector(Selectors.PostModal.TIME_LINK)
            if time_link:
                href = time_link.get_attribute('href')
                content_id = self._extract_id_from_href(href)
                if content_id:
                    return content_id

            # Try dialog HTML - search for any content pattern
            dialog = self.query_selector(Selectors.PostModal.DIALOG)
            if dialog:
                html = self.evaluate("el => el.innerHTML", dialog)
                # Check for posts, reels, and IGTV
                for pattern in [r'/p/([A-Za-z0-9_-]+)/', r'/reel/([A-Za-z0-9_-]+)/', r'/tv/([A-Za-z0-9_-]+)/']:
                    match = re.search(pattern, html)
                    if match:
                        return match.group(1)
        except Exception as e:
            logger.debug(f"Error extracting content ID: {e}")

        return None

    def _extract_id_from_href(self, href: str) -> Optional[str]:
        """
        Extract content ID from href attribute.

        Args:
            href: URL or path

        Returns:
            Content ID or None
        """
        if not href:
            return None

        # Check for posts, reels, and IGTV
        patterns = [
            r"/p/([^/]+)/",
            r"/reel/([^/]+)/",
            r"/tv/([^/]+)/"
        ]

        for pattern in patterns:
            match = re.search(pattern, href)
            if match:
                return match.group(1)

        return None

    def extract_content_id_from_url(self, url: Optional[str] = None) -> Optional[str]:
        """
        Extract content ID from URL (post, reel, or IGTV).

        Args:
            url: URL to parse (defaults to current URL)

        Returns:
            Content ID or None
        """
        url = url or self.current_url
        return self._extract_id_from_href(url)

    def get_post_url(self) -> str:
        """
        Get full URL for current content.

        Returns:
            Content URL
        """
        # Just return the current URL since it already contains the full path
        # This handles all content types correctly
        current = self.current_url
        if '/p/' in current or '/reel/' in current or '/tv/' in current:
            return current

        # Fallback: construct URL from ID
        content_id = self.get_post_id()
        if content_id:
            # Try to determine type from page
            if '/reel/' in current:
                return Selectors.URLs.reel(content_id)
            elif '/tv/' in current:
                return Selectors.URLs.tv(content_id)
            else:
                return Selectors.URLs.post(content_id)

        return current

    def get_caption(self) -> str:
        """
        Get post caption/text.

        Returns:
            Caption text
        """
        # Try multiple selectors
        caption_selectors = [
            Selectors.PostModal.CAPTION_H1,
            Selectors.PostModal.CAPTION_DIALOG_H1,
            Selectors.PostModal.CAPTION_BUTTON_SPAN,
            Selectors.PostModal.CAPTION_DIALOG_SPAN,
        ]

        for selector in caption_selectors:
            text = self.get_text(selector, timeout=1000)
            if text and len(text) > 3:
                return text

        # JavaScript fallback
        try:
            caption = self.evaluate('''
                () => {
                    const container = document.querySelector('div[role="dialog"]') ||
                                     document.querySelector('article');
                    if (container) {
                        const spans = container.querySelectorAll('span');
                        for (const span of spans) {
                            const text = span.innerText?.trim();
                            if (text && text.length > 20 && text.length < 2200 &&
                                !text.includes('likes') && !text.includes('comments') &&
                                !text.includes('Log in') && !text.match(/^\\d+[hdwms]$/)) {
                                return text;
                            }
                        }
                    }
                    const meta = document.querySelector('meta[property="og:description"]');
                    return meta?.content || '';
                }
            ''')
            return caption or ""
        except Exception:
            return ""

    def get_likes(self) -> int:
        """
        Get like count.

        Returns:
            Number of likes
        """
        like_selectors = [
            Selectors.PostModal.LIKES_SECTION,
            Selectors.PostModal.LIKE_SINGLE,
            Selectors.PostModal.LIKES_DIALOG,
            Selectors.PostModal.LIKED_BY_LINK,
        ]

        for selector in like_selectors:
            text = self.get_text(selector, timeout=1000)
            if text:
                count = self.parse_count(text)
                if count > 0:
                    return count

        return 0

    def get_timestamp(self) -> Optional[datetime]:
        """
        Get post publication timestamp.

        Returns:
            Datetime or None
        """
        try:
            datetime_str = self.get_attribute(Selectors.PostModal.TIME_ELEMENT, "datetime")
            if datetime_str:
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except Exception:
            pass
        return None

    def get_media_type(self) -> str:
        """
        Determine media type (image, video, carousel).

        Returns:
            Media type string
        """
        try:
            if self.is_visible(Selectors.PostModal.VIDEO, timeout=1000):
                return "video"
            if self.is_visible(Selectors.PostModal.CAROUSEL_NEXT, timeout=1000):
                return "carousel"
        except Exception:
            pass
        return "image"

    def navigate_next(self) -> bool:
        """
        Navigate to next post using keyboard.

        Returns:
            True if navigation succeeded (different post)
        """
        current_id = self.get_post_id()
        self.press_key("ArrowRight")
        self.wait(2000)
        self.wait_for_load(timeout=5000)

        new_id = self.get_post_id()
        return new_id != current_id

    def navigate_prev(self) -> bool:
        """
        Navigate to previous post using keyboard.

        Returns:
            True if navigation succeeded
        """
        current_id = self.get_post_id()
        self.press_key("ArrowLeft")
        self.wait(2000)
        self.wait_for_load(timeout=5000)

        new_id = self.get_post_id()
        return new_id != current_id

    def close(self) -> None:
        """Close the modal."""
        self.press_key("Escape")
        self.wait(500)

    def extract_post_data(self, account_id: str) -> Dict[str, Any]:
        """
        Extract all post data from modal.

        Args:
            account_id: Instagram username

        Returns:
            Dictionary with post data
        """
        self.dismiss_popups()

        post_id = self.get_post_id()
        caption = self.get_caption()
        likes = self.get_likes()
        timestamp = self.get_timestamp()
        media_type = self.get_media_type()

        logger.debug(
            f"POST DATA | id={post_id} | likes={likes} | "
            f"caption_len={len(caption)} | media={media_type}"
        )

        return {
            "post_id": post_id,
            "url": self.get_post_url(),
            "account_id": account_id,
            "caption": caption,
            "likes": likes,
            "timestamp": timestamp,
            "media_type": media_type,
        }
