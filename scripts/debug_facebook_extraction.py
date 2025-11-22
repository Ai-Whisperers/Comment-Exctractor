#!/usr/bin/env python
"""
Debug script to investigate Facebook post data extraction.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings
from src.scrapers.facebook.scraper import FacebookScraper
from src.scrapers.facebook.selectors import Selectors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def debug_facebook_extraction(account: str = "personalpy"):
    """Debug Facebook post data extraction."""
    settings = Settings()
    config = settings.get_platform_config("facebook")
    config["headless"] = False

    scraper = FacebookScraper(config)

    try:
        scraper._ensure_logged_in()

        # Navigate to profile
        scraper._profile_page.navigate(account)

        # Get first few post links
        post_links = scraper._post_page.get_post_links(max_posts=3)

        logger.info(f"Found {len(post_links)} posts to debug")

        for i, url in enumerate(post_links, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Post {i}: {url[:80]}...")
            logger.info(f"{'='*60}")

            # Navigate to post
            scraper._page.goto(url, wait_until="domcontentloaded")
            scraper._page.wait_for_timeout(3000)

            # Debug: Get ALL text from reaction/comment/share areas
            debug_data = scraper._page.evaluate('''
                () => {
                    const result = {
                        reactions_matches: [],
                        comments_matches: [],
                        shares_matches: [],
                        all_spans_with_numbers: []
                    };

                    // Get all spans with numbers (for reference)
                    document.querySelectorAll('span').forEach(span => {
                        const text = span.textContent.trim();
                        if (/\\d/.test(text) && text.length < 100) {
                            // Check if it looks like a count
                            if (/(reaction|comment|share|like|view|veces|compartido|reaccion)/i.test(text)) {
                                result.all_spans_with_numbers.push(text);

                                // Categorize
                                if (/(reaction|reaccion)/i.test(text)) {
                                    result.reactions_matches.push(text);
                                }
                                if (/(comment|comentario)/i.test(text)) {
                                    result.comments_matches.push(text);
                                }
                                if (/(share|compartido|veces)/i.test(text)) {
                                    result.shares_matches.push(text);
                                }
                            }
                        }
                    });

                    return result;
                }
            ''')

            print(f"\n--- Reactions Matches ---")
            for text in debug_data['reactions_matches'][:5]:
                print(f"  '{text}'")

            print(f"\n--- Comments Matches ---")
            for text in debug_data['comments_matches'][:5]:
                print(f"  '{text}'")

            print(f"\n--- Shares Matches ---")
            for text in debug_data['shares_matches'][:5]:
                print(f"  '{text}'")

            print(f"\n--- All Spans with Count Keywords ---")
            for text in debug_data['all_spans_with_numbers'][:15]:
                print(f"  '{text}'")

            # Debug what Playwright selectors actually find
            print(f"\n--- Playwright Selector Results ---")

            # Reactions selector
            try:
                reactions_locator = scraper._page.locator(Selectors.Post.REACTIONS_COUNT).first
                if reactions_locator.is_visible(timeout=2000):
                    reactions_text = reactions_locator.inner_text().strip()
                    print(f"  Reactions selector: '{reactions_text}'")
                else:
                    print(f"  Reactions selector: NOT VISIBLE")
            except Exception as e:
                print(f"  Reactions selector: ERROR - {e}")

            # Comments selector
            try:
                comments_locator = scraper._page.locator(Selectors.Post.COMMENTS_COUNT).first
                if comments_locator.is_visible(timeout=2000):
                    comments_text = comments_locator.inner_text().strip()
                    print(f"  Comments selector: '{comments_text}'")
                else:
                    print(f"  Comments selector: NOT VISIBLE")
            except Exception as e:
                print(f"  Comments selector: ERROR - {e}")

            # Shares selector
            try:
                shares_locator = scraper._page.locator(Selectors.Post.SHARES_COUNT).first
                if shares_locator.is_visible(timeout=2000):
                    shares_text = shares_locator.inner_text().strip()
                    print(f"  Shares selector: '{shares_text}'")
                else:
                    print(f"  Shares selector: NOT VISIBLE")
            except Exception as e:
                print(f"  Shares selector: ERROR - {e}")

            # Also get the actual extracted values
            post_data = scraper._post_page.extract_post_data(account)
            print(f"\n--- Extracted Data ---")
            print(f"  Likes: {post_data['likes']}")
            print(f"  Comments: {post_data['comments_count']}")
            print(f"  Shares: {post_data['shares']}")

        input("\nPress Enter to close browser...")

    finally:
        scraper.close()


if __name__ == "__main__":
    debug_facebook_extraction()
