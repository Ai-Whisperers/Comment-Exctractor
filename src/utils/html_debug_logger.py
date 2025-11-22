"""HTML Debug Logger for capturing page state during scraping issues."""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import Page

from ..config.paths import get_paths

logger = logging.getLogger(__name__)


class HTMLDebugLogger:
    """Utility class for saving HTML snapshots when issues occur during scraping."""

    # Page type constants
    PAGE_HOME = "home_page"
    PAGE_LOGIN = "login_page"
    PAGE_POST = "post_page"
    PAGE_PROFILE = "profile_page"
    PAGE_COMMENTS = "comments_section"
    PAGE_MODAL = "modal"
    PAGE_UNKNOWN = "unknown"

    def __init__(self, base_dir: str = None, client_name: str = None):
        """
        Initialize the HTML debug logger.

        Args:
            base_dir: Base directory for HTML logs (uses centralized config if None)
            client_name: Client/account name for organizing logs
        """
        if base_dir is None:
            self.base_dir = get_paths().html_logs_dir
        else:
            self.base_dir = Path(base_dir)
        self._client_name = client_name
        self._ensure_directories()

    def set_client(self, client_name: str):
        """
        Set the current client name for organizing logs.

        Args:
            client_name: Client/account name
        """
        self._client_name = client_name
        self._ensure_directories()

    def _get_client_dir(self) -> Path:
        """Get the directory for the current client."""
        if self._client_name:
            # Clean client name to be folder-safe
            safe_name = re.sub(r'[^\w\-]', '_', self._client_name)
            return self.base_dir / safe_name
        return self.base_dir / "_default"

    def _ensure_directories(self):
        """Create the folder structure for HTML logs."""
        # Get client directory
        client_dir = self._get_client_dir()

        # Main pages directory under client
        pages_dir = client_dir / "pages"

        # Create subdirectories for each page type
        page_types = [
            self.PAGE_HOME,
            self.PAGE_LOGIN,
            self.PAGE_POST,
            self.PAGE_PROFILE,
            self.PAGE_COMMENTS,
            self.PAGE_MODAL,
            self.PAGE_UNKNOWN,
        ]

        for page_type in page_types:
            (pages_dir / page_type).mkdir(parents=True, exist_ok=True)

        logger.debug(f"HTML debug directories initialized at {client_dir}")

    def _generate_filename(self, page_type: str, context: str = "", platform: str = "") -> str:
        """
        Generate a timestamped filename for the HTML dump.

        Args:
            page_type: Type of page being logged
            context: Additional context (e.g., post_id, username)
            platform: Platform name (instagram, facebook, etc.)

        Returns:
            Filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds

        parts = [timestamp]
        if platform:
            parts.append(platform)
        if context:
            # Clean context to be filename-safe
            safe_context = re.sub(r'[^\w\-]', '_', context)[:50]
            parts.append(safe_context)

        return "_".join(parts) + ".html"

    def _extract_html_content(self, page: Page) -> Dict[str, Any]:
        """
        Extract HTML content from the page, excluding styles and scripts.

        Args:
            page: Playwright Page object

        Returns:
            Dictionary with HTML content and metadata
        """
        result = page.evaluate('''
            () => {
                // Clone the document to avoid modifying the original
                const clone = document.documentElement.cloneNode(true);

                // Remove all script tags
                const scripts = clone.querySelectorAll('script');
                scripts.forEach(s => s.remove());

                // Remove all style tags
                const styles = clone.querySelectorAll('style');
                styles.forEach(s => s.remove());

                // Remove all link tags for stylesheets
                const links = clone.querySelectorAll('link[rel="stylesheet"]');
                links.forEach(l => l.remove());

                // Remove inline styles (optional - keeps structure cleaner)
                // Uncomment if you want to remove inline styles too:
                // clone.querySelectorAll('[style]').forEach(el => el.removeAttribute('style'));

                // Get metadata
                const metadata = {
                    title: document.title || '',
                    url: window.location.href,
                    viewport: `${window.innerWidth}x${window.innerHeight}`,
                    scrollPosition: `${window.scrollX},${window.scrollY}`,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                };

                // Check for popups/dialogs
                const dialogs = [];
                document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, [aria-modal="true"]').forEach(d => {
                    dialogs.push({
                        role: d.getAttribute('role') || 'unknown',
                        classes: d.className,
                        visible: window.getComputedStyle(d).display !== 'none',
                    });
                });
                metadata.dialogs = dialogs;

                // Check for error indicators
                const errors = [];
                document.querySelectorAll('[role="alert"], .error, .warning, [class*="error"], [class*="Error"]').forEach(e => {
                    const text = e.innerText?.trim();
                    if (text && text.length < 500) {
                        errors.push(text);
                    }
                });
                metadata.errorElements = errors;

                return {
                    html: clone.outerHTML,
                    metadata: metadata
                };
            }
        ''')

        return result

    def save_debug_html(
        self,
        page: Page,
        page_type: str,
        reason: str,
        context: str = "",
        platform: str = "",
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save the current page HTML for debugging.

        Args:
            page: Playwright Page object
            page_type: Type of page (use class constants)
            reason: Why this dump was triggered
            context: Additional context (e.g., post_id, username)
            platform: Platform name
            additional_info: Any additional debug information

        Returns:
            Path to saved file
        """
        try:
            # Extract HTML content
            content = self._extract_html_content(page)

            # Generate filename and path
            filename = self._generate_filename(page_type, context, platform)
            client_dir = self._get_client_dir()
            file_path = client_dir / "pages" / page_type / filename

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Build the HTML file with metadata header
            metadata = content['metadata']
            html_content = content['html']

            # Create a debug header with useful information
            debug_header = f'''<!--
================================================================================
HTML DEBUG DUMP
================================================================================
Timestamp: {metadata['timestamp']}
URL: {metadata['url']}
Page Title: {metadata['title']}
Viewport: {metadata['viewport']}
Scroll Position: {metadata['scrollPosition']}
Client: {self._client_name or '_default'}
Platform: {platform}
Page Type: {page_type}
Context: {context}
Reason: {reason}

User Agent: {metadata['userAgent']}

Dialogs/Popups Found: {len(metadata.get('dialogs', []))}
'''

            # Add dialog details if present
            if metadata.get('dialogs'):
                debug_header += "\nDialogs:\n"
                for i, dialog in enumerate(metadata['dialogs']):
                    debug_header += f"  [{i+1}] Role: {dialog['role']}, Visible: {dialog['visible']}, Classes: {dialog['classes'][:100]}\n"

            # Add error elements if found
            if metadata.get('errorElements'):
                debug_header += "\nError Elements Found:\n"
                for error in metadata['errorElements'][:5]:  # Limit to first 5
                    debug_header += f"  - {error[:200]}\n"

            # Add additional info if provided
            if additional_info:
                debug_header += "\nAdditional Debug Info:\n"
                for key, value in additional_info.items():
                    debug_header += f"  {key}: {value}\n"

            debug_header += '''
================================================================================
-->

'''

            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(debug_header + html_content)

            logger.info(f"HTML DEBUG | saved={file_path} | reason={reason} | size={len(html_content)}bytes")

            return str(file_path)

        except Exception as e:
            logger.error(f"HTML DEBUG | failed to save | error={e}")
            return ""

    def save_on_error(
        self,
        page: Page,
        page_type: str,
        error: Exception,
        context: str = "",
        platform: str = ""
    ) -> str:
        """
        Convenience method to save HTML when an error occurs.

        Args:
            page: Playwright Page object
            page_type: Type of page
            error: The exception that occurred
            context: Additional context
            platform: Platform name

        Returns:
            Path to saved file
        """
        return self.save_debug_html(
            page=page,
            page_type=page_type,
            reason=f"Error: {type(error).__name__}: {str(error)[:200]}",
            context=context,
            platform=platform,
            additional_info={
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )

    def save_on_unexpected(
        self,
        page: Page,
        page_type: str,
        expected: str,
        actual: str,
        context: str = "",
        platform: str = ""
    ) -> str:
        """
        Convenience method to save HTML when something unexpected happens.

        Args:
            page: Playwright Page object
            page_type: Type of page
            expected: What was expected
            actual: What actually happened
            context: Additional context
            platform: Platform name

        Returns:
            Path to saved file
        """
        return self.save_debug_html(
            page=page,
            page_type=page_type,
            reason=f"Unexpected: expected '{expected}', got '{actual}'",
            context=context,
            platform=platform,
            additional_info={
                "expected": expected,
                "actual": actual,
            }
        )

    def save_on_timeout(
        self,
        page: Page,
        page_type: str,
        waiting_for: str,
        timeout_ms: int,
        context: str = "",
        platform: str = ""
    ) -> str:
        """
        Convenience method to save HTML when a timeout occurs.

        Args:
            page: Playwright Page object
            page_type: Type of page
            waiting_for: What we were waiting for
            timeout_ms: Timeout in milliseconds
            context: Additional context
            platform: Platform name

        Returns:
            Path to saved file
        """
        return self.save_debug_html(
            page=page,
            page_type=page_type,
            reason=f"Timeout ({timeout_ms}ms) waiting for: {waiting_for}",
            context=context,
            platform=platform,
            additional_info={
                "waiting_for": waiting_for,
                "timeout_ms": timeout_ms,
            }
        )

    def save_on_login_failure(
        self,
        page: Page,
        reason: str,
        username: str = "",
        platform: str = ""
    ) -> str:
        """
        Convenience method to save HTML when login fails.

        Args:
            page: Playwright Page object
            reason: Reason for login failure
            username: Username attempted (will be partially masked)
            platform: Platform name

        Returns:
            Path to saved file
        """
        # Mask username for privacy
        masked_user = username[:2] + "***" if len(username) > 2 else "***"

        return self.save_debug_html(
            page=page,
            page_type=self.PAGE_LOGIN,
            reason=f"Login failed: {reason}",
            context=f"user_{masked_user}",
            platform=platform,
            additional_info={
                "login_reason": reason,
            }
        )

    def save_on_no_comments(
        self,
        page: Page,
        post_id: str,
        expected_count: int = 0,
        platform: str = ""
    ) -> str:
        """
        Convenience method when comments extraction yields unexpected results.

        Args:
            page: Playwright Page object
            post_id: Post ID
            expected_count: Expected minimum comment count
            platform: Platform name

        Returns:
            Path to saved file
        """
        return self.save_debug_html(
            page=page,
            page_type=self.PAGE_COMMENTS,
            reason=f"No comments found (expected at least {expected_count})",
            context=post_id,
            platform=platform,
            additional_info={
                "post_id": post_id,
                "expected_count": expected_count,
            }
        )


# Global instance for convenience
_debug_logger: Optional[HTMLDebugLogger] = None


def get_debug_logger() -> HTMLDebugLogger:
    """Get or create the global HTML debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = HTMLDebugLogger()
    return _debug_logger


def set_debug_client(client_name: str):
    """
    Set the client name for the global debug logger.

    Args:
        client_name: Client/account name for organizing logs
    """
    get_debug_logger().set_client(client_name)


def save_debug_html(
    page: Page,
    page_type: str,
    reason: str,
    context: str = "",
    platform: str = "",
    additional_info: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to save debug HTML using global logger."""
    return get_debug_logger().save_debug_html(
        page, page_type, reason, context, platform, additional_info
    )
