#!/usr/bin/env python
"""
Debug script to investigate Instagram hover overlay structure.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.instagram import InstagramScraper
from src.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def debug_hover_overlay(account: str = "personalpy"):
    """Debug the hover overlay detection."""
    settings = get_settings()
    config = settings.get_platform_config("instagram")
    config["headless"] = False

    scraper = InstagramScraper(config)

    try:
        scraper._ensure_logged_in()

        # Navigate to profile
        profile_url = f"https://www.instagram.com/{account}/"
        scraper._page.goto(profile_url, wait_until="domcontentloaded")
        scraper._page.wait_for_timeout(5000)
        scraper._profile_page.dismiss_popups()

        # Get first few post links
        hrefs = scraper._page.evaluate(f'''
            () => {{
                const hrefs = [];
                document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]').forEach(a => {{
                    const href = a.getAttribute('href');
                    if (href && !hrefs.includes(href) && href.includes('/{account}/')) {{
                        hrefs.push(href);
                    }}
                }});
                return hrefs.slice(0, 3);
            }}
        ''')

        logger.info(f"Found {len(hrefs)} posts to test")

        for href in hrefs:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {href}")
            logger.info(f"{'='*60}")

            link = scraper._page.locator(f'a[href="{href}"]').first
            if not link.is_visible(timeout=500):
                logger.warning("Link not visible")
                continue

            # Hover
            link.hover()
            scraper._page.wait_for_timeout(1000)  # Wait longer for overlay

            # Debug: Get ALL overlay-like elements
            debug_data = scraper._page.evaluate('''
                () => {
                    const result = {
                        strategy1_opacity_divs: [],
                        strategy2_uls: [],
                        strategy3_all_numbers: [],
                        likely_overlay: null
                    };

                    // Strategy 1: Opacity divs
                    document.querySelectorAll('div[style*="opacity"]').forEach(div => {
                        const style = window.getComputedStyle(div);
                        const spans = div.querySelectorAll('span');
                        const texts = [];
                        spans.forEach(s => {
                            const t = s.textContent.trim();
                            if (t && t.length < 20) texts.push(t);
                        });
                        if (texts.length > 0) {
                            result.strategy1_opacity_divs.push({
                                opacity: style.opacity,
                                texts: texts.slice(0, 10),
                                rect: div.getBoundingClientRect()
                            });
                        }
                    });

                    // Strategy 2: ULs with LIs
                    document.querySelectorAll('ul').forEach(ul => {
                        const lis = ul.querySelectorAll('li');
                        if (lis.length >= 2) {
                            const texts = [];
                            lis.forEach(li => {
                                const t = li.textContent.trim();
                                if (/\\d/.test(t)) texts.push(t);
                            });
                            if (texts.length > 0) {
                                result.strategy2_uls.push({
                                    liCount: lis.length,
                                    texts: texts.slice(0, 5)
                                });
                            }
                        }
                    });

                    // Strategy 3: All visible numbers
                    document.querySelectorAll('span').forEach(span => {
                        const rect = span.getBoundingClientRect();
                        const style = window.getComputedStyle(span);
                        if (rect.width > 0 && rect.height > 0 &&
                            style.display !== 'none' && style.visibility !== 'hidden') {
                            const text = span.textContent.trim();
                            if (/^[\\d,\\.]+[KMB]?$/.test(text) && text.length < 15) {
                                result.strategy3_all_numbers.push({
                                    text: text,
                                    top: rect.top,
                                    left: rect.left
                                });
                            }
                        }
                    });

                    // NEW: Look for the actual Instagram overlay structure
                    // It's typically a div that appears on hover with absolute/fixed position
                    // and contains SVG icons for heart and comment
                    const hoveredPost = document.querySelector('a[href*="/p/"]:hover, a[href*="/reel/"]:hover');
                    if (hoveredPost) {
                        // Find overlay within or near the hovered element
                        const container = hoveredPost.closest('div');
                        if (container) {
                            // Look for overlay with gradient/dark background
                            const overlayDivs = container.querySelectorAll('div');
                            for (const div of overlayDivs) {
                                const style = window.getComputedStyle(div);
                                // Overlay usually has absolute/fixed position and covers the image
                                if (style.position === 'absolute' || style.position === 'fixed') {
                                    const svgs = div.querySelectorAll('svg');
                                    if (svgs.length >= 2) {
                                        // This might be our overlay!
                                        const spans = div.querySelectorAll('span');
                                        const numbers = [];
                                        spans.forEach(s => {
                                            const t = s.textContent.trim();
                                            if (/^[\\d,\\.]+[KMB]?$/.test(t)) numbers.push(t);
                                        });
                                        if (numbers.length >= 2) {
                                            result.likely_overlay = {
                                                numbers: numbers,
                                                svgCount: svgs.length,
                                                position: style.position
                                            };
                                        }
                                    }
                                }
                            }
                        }
                    }

                    return result;
                }
            ''')

            # Print debug info
            print(f"\n--- Strategy 1: Opacity Divs ---")
            for i, div in enumerate(debug_data['strategy1_opacity_divs'][:3]):
                print(f"  [{i}] opacity={div['opacity']}, texts={div['texts'][:5]}")

            print(f"\n--- Strategy 2: ULs ---")
            for i, ul in enumerate(debug_data['strategy2_uls'][:3]):
                print(f"  [{i}] lis={ul['liCount']}, texts={ul['texts']}")

            print(f"\n--- Strategy 3: All Numbers ---")
            numbers = debug_data['strategy3_all_numbers']
            print(f"  Total numbers found: {len(numbers)}")
            if numbers:
                print(f"  First 5: {[n['text'] for n in numbers[:5]]}")
                print(f"  Last 5: {[n['text'] for n in numbers[-5:]]}")

            print(f"\n--- Likely Overlay ---")
            if debug_data['likely_overlay']:
                print(f"  Numbers: {debug_data['likely_overlay']['numbers']}")
                print(f"  SVGs: {debug_data['likely_overlay']['svgCount']}")
            else:
                print("  Not found!")

            # Move mouse away
            scraper._page.mouse.move(0, 0)
            scraper._page.wait_for_timeout(500)

        input("\nPress Enter to close browser...")

    finally:
        scraper.close()


if __name__ == "__main__":
    debug_hover_overlay()
