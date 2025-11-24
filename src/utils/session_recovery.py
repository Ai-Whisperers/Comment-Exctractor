"""
Browser session recovery utilities.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class SessionRecovery:
    """
    Manages browser session health and recovery.
    """

    def __init__(self, browser_manager, max_recovery_attempts: int = 3):
        self.browser_manager = browser_manager
        self.max_attempts = max_recovery_attempts
        self._recovery_count = 0

    def is_healthy(self) -> bool:
        """Check if browser session is responsive."""
        try:
            result = self.browser_manager.page.evaluate("1 + 1")
            return result == 2
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def recover(self) -> bool:
        """
        Attempt to recover browser session.

        Returns True if recovery successful.
        """
        if self._recovery_count >= self.max_attempts:
            logger.error(f"Max recovery attempts ({self.max_attempts}) reached")
            return False

        self._recovery_count += 1
        logger.info(f"Recovering session (attempt {self._recovery_count})")

        # Level 1: Soft recovery - just reload
        if self._soft_recover():
            logger.info("Soft recovery successful")
            return True

        # Level 2: Context recovery - new context, same browser
        if self._context_recover():
            logger.info("Context recovery successful")
            return True

        # Level 3: Hard recovery - restart browser
        if self._hard_recover():
            logger.info("Hard recovery successful")
            return True

        logger.error("All recovery attempts failed")
        return False

    def _soft_recover(self) -> bool:
        """Try page reload."""
        try:
            self.browser_manager.page.reload(timeout=30000)
            time.sleep(2)
            return self.is_healthy()
        except Exception as e:
            logger.debug(f"Soft recovery failed: {e}")
            return False

    def _context_recover(self) -> bool:
        """Try creating new context."""
        try:
            # Close old context
            if hasattr(self.browser_manager, '_context'):
                try:
                    self.browser_manager._context.close()
                except:
                    pass

            # Create new context
            time.sleep(2)
            if hasattr(self.browser_manager, '_initialize_context'):
                self.browser_manager._initialize_context()
            return self.is_healthy()
        except Exception as e:
            logger.debug(f"Context recovery failed: {e}")
            return False

    def _hard_recover(self) -> bool:
        """Full browser restart."""
        try:
            self.browser_manager.close()
            time.sleep(5)
            if hasattr(self.browser_manager, '_initialize'):
                self.browser_manager._initialize()
            return self.is_healthy()
        except Exception as e:
            logger.debug(f"Hard recovery failed: {e}")
            return False

    def reset_counter(self) -> None:
        """Reset recovery attempt counter after successful operations."""
        if self._recovery_count > 0:
            logger.debug(f"Reset recovery counter (was {self._recovery_count})")
            self._recovery_count = 0
