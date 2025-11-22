#!/usr/bin/env python
"""
Script to extract all posts from personalpy Instagram account.
Collects post links with likes/comments counts using improved hover detection.
Includes progress persistence for resumable extraction.
"""

import json
import logging
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.instagram import InstagramScraper
from src.config.settings import get_settings
from src.config.paths import get_paths

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Reduce noise
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def extract_instagram_posts(account: str = "personalpy", max_posts: int = 1000, resume: bool = True):
    """
    Extract all posts from an Instagram account.

    Args:
        account: Instagram username
        max_posts: Maximum posts to collect
        resume: Resume from previous progress if available

    Returns:
        List of post data dictionaries
    """
    settings = get_settings()
    config = settings.get_platform_config("instagram")

    # Use non-headless mode for better reliability
    config["headless"] = False

    logger.info(f"EXTRACTING ALL POSTS FROM INSTAGRAM: {account}")
    logger.info(f"Max posts: {max_posts}")

    # Progress persistence setup
    output_dir = Path("data/instagram_posts")
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = output_dir / f"{account}_progress.json"

    # Load existing progress
    results = []
    processed_hrefs = set()

    if resume and progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                results = progress.get("posts", [])
                processed_hrefs = set(progress.get("processed_hrefs", []))
            logger.info(f"Resuming from {len(results)} posts already collected")
        except Exception as e:
            logger.warning(f"Could not load progress: {e}")

    scraper = InstagramScraper(config)

    try:
        # Login
        scraper._ensure_logged_in()

        # Navigate to profile
        profile_url = f"https://www.instagram.com/{account}/"
        scraper._page.goto(profile_url, wait_until="domcontentloaded")
        scraper._page.wait_for_timeout(5000)

        # Dismiss popups
        scraper._profile_page.dismiss_popups()
        scraper._page.wait_for_timeout(1000)

        # Scroll and hover to collect posts with counts
        logger.info("Scrolling and hovering over posts to get counts...")

        previous_count = len(processed_hrefs)
        no_new_count = 0
        scroll_count = 0
        max_no_new = 20  # Tolerance for slow loading
        hover_failures = 0

        while no_new_count < max_no_new and len(results) < max_posts:
            # Get current post links - filter by account
            current_hrefs = scraper._page.evaluate(f'''
                () => {{
                    const hrefs = [];
                    document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]').forEach(a => {{
                        const href = a.getAttribute('href');
                        // Only include posts from the target account
                        if (href && !hrefs.includes(href) && href.includes('/{account}/')) {{
                            hrefs.push(href);
                        }}
                    }});
                    return hrefs;
                }}
            ''')

            # Process new posts
            new_hrefs = [h for h in current_hrefs if h not in processed_hrefs]

            for href in new_hrefs:
                if len(results) >= max_posts:
                    break

                # Extract post ID
                post_id = None
                for pattern in [r'/p/([^/]+)', r'/reel/([^/]+)']:
                    match = re.search(pattern, href)
                    if match:
                        post_id = match.group(1)
                        break

                try:
                    link_selector = f'a[href="{href}"]'
                    link = scraper._page.locator(link_selector).first

                    if link.is_visible(timeout=500):
                        # Hover to get overlay data
                        link.hover()
                        scraper._page.wait_for_timeout(500)

                        # Improved overlay detection - prioritize UL with exactly 2 LIs
                        overlay_data = scraper._page.evaluate('''
                            () => {
                                // PRIORITY 1: Look for ul with exactly 2 li elements
                                // This is the most reliable - Instagram's overlay uses this structure
                                const allUls = document.querySelectorAll('ul');
                                for (const ul of allUls) {
                                    const lis = ul.querySelectorAll('li');
                                    // Must have exactly 2 li elements (likes and comments)
                                    if (lis.length === 2) {
                                        const rect = ul.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {
                                            const texts = [];
                                            lis.forEach(li => {
                                                const text = li.textContent.trim();
                                                // Extract just the number from each li
                                                const match = text.match(/([\\d,\\.]+[KMB]?)/i);
                                                if (match) {
                                                    texts.push(match[1]);
                                                }
                                            });
                                            if (texts.length === 2) {
                                                return { texts: texts, strategy: 'ul_2_li' };
                                            }
                                        }
                                    }
                                }

                                // FALLBACK 1: Look for opacity div with spans
                                const overlays = document.querySelectorAll('div[style*="opacity"]');
                                for (const overlay of overlays) {
                                    const style = window.getComputedStyle(overlay);
                                    if (style.opacity === '1' || parseFloat(style.opacity) > 0.5) {
                                        const spans = overlay.querySelectorAll('span');
                                        const numbers = [];
                                        for (const span of spans) {
                                            const text = span.textContent.trim();
                                            if (/^[\\d,\\.]+[KMB]?$/i.test(text)) {
                                                numbers.push(text);
                                            }
                                        }
                                        if (numbers.length >= 2) {
                                            return { texts: numbers.slice(0, 2), strategy: 'opacity_div' };
                                        }
                                    }
                                }

                                // FALLBACK 2: Look for ul with 2+ li elements containing numbers
                                for (const ul of allUls) {
                                    const style = window.getComputedStyle(ul);
                                    const lis = ul.querySelectorAll('li');
                                    if (style.opacity !== '0' && lis.length >= 2) {
                                        const rect = ul.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {
                                            const texts = [];
                                            lis.forEach(li => {
                                                const text = li.textContent.trim();
                                                const match = text.match(/([\\d,\\.]+[KMB]?)/i);
                                                if (match) {
                                                    texts.push(match[1]);
                                                }
                                            });
                                            if (texts.length >= 2) {
                                                return { texts: texts.slice(0, 2), strategy: 'ul_multi_li' };
                                            }
                                        }
                                    }
                                }

                                return { error: 'no overlay detected' };
                            }
                        ''')

                        # Parse counts
                        likes = 0
                        comments = 0

                        if 'texts' in overlay_data:
                            for j, text in enumerate(overlay_data['texts']):
                                # Clean the text and extract number
                                clean_text = text.replace(',', '').replace('.', '')
                                num_match = re.search(r'([\d]+)\s*([KMB])?', clean_text, re.IGNORECASE)
                                if num_match:
                                    num = float(num_match.group(1))
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
                        else:
                            hover_failures += 1

                        results.append({
                            'post_id': post_id,
                            'url': f"https://www.instagram.com{href}",
                            'likes': likes,
                            'comments_count': comments
                        })
                    else:
                        results.append({
                            'post_id': post_id,
                            'url': f"https://www.instagram.com{href}",
                            'likes': 0,
                            'comments_count': -1,
                            'error': 'not visible'
                        })

                except Exception as e:
                    results.append({
                        'post_id': post_id,
                        'url': f"https://www.instagram.com{href}",
                        'likes': 0,
                        'comments_count': -1,
                        'error': str(e)[:50]
                    })

                processed_hrefs.add(href)

            current_count = len(processed_hrefs)

            if current_count == previous_count:
                no_new_count += 1
            else:
                no_new_count = 0
                previous_count = current_count

            # Scroll down
            scraper._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            scraper._page.wait_for_timeout(2000)

            scroll_count += 1
            if scroll_count % 10 == 0:
                logger.info(f"Scroll {scroll_count}: {current_count} posts processed (hover failures: {hover_failures})")

                # Save progress periodically
                _save_progress(progress_file, account, results, list(processed_hrefs))

        logger.info(f"Total posts processed: {len(results)}")
        logger.info(f"Hover detection failures: {hover_failures}")

        # Final progress save
        _save_progress(progress_file, account, results, list(processed_hrefs))

        return results

    finally:
        scraper.close()


def _save_progress(progress_file, account, results, processed_hrefs):
    """Save extraction progress to file."""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            "account": account,
            "updated_at": datetime.now().isoformat(),
            "total_posts": len(results),
            "processed_hrefs": processed_hrefs,
            "posts": results
        }, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Extract Instagram posts from an account")
    parser.add_argument("--account", "-a", default="personalpy", help="Instagram username")
    parser.add_argument("--max-posts", "-n", type=int, default=1000, help="Maximum posts to collect")
    parser.add_argument("--no-resume", action="store_true", help="Start fresh instead of resuming")
    args = parser.parse_args()

    account = args.account
    max_posts = args.max_posts
    resume = not args.no_resume

    # Extract posts
    posts = extract_instagram_posts(account, max_posts, resume=resume)

    if not posts:
        logger.error("No posts extracted!")
        return

    # Save to file using centralized path configuration
    paths = get_paths()
    output_dir = paths.posts_dir(account, "instagram")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use date-based filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = output_dir / f"{date_str}.json"

    # Calculate stats
    posts_with_comments = [p for p in posts if p.get("comments_count", 0) > 0]
    total_comments = sum(p.get("comments_count", 0) for p in posts if p.get("comments_count", 0) > 0)
    posts_with_errors = [p for p in posts if p.get("error")]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": {
                "version": "2.0",
                "extraction_type": "full" if max_posts >= 1000 else "partial",
                "is_complete": True,
            },
            "account_id": account,
            "platform": "instagram",
            "collected_at": datetime.now().isoformat(),
            "total_posts": len(posts),
            "posts_with_comments": len(posts_with_comments),
            "posts_with_errors": len(posts_with_errors),
            "total_comments": total_comments,
            "posts": posts
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(posts)} posts to {output_file}")

    # Create/update latest.json
    latest_file = output_dir / "latest.json"
    try:
        if latest_file.exists():
            latest_file.unlink()
        import shutil
        shutil.copy2(output_file, latest_file)
        logger.info(f"Updated latest.json -> {output_file.name}")
    except Exception as e:
        logger.warning(f"Could not create latest.json: {e}")

    # Print stats
    print("\n" + "="*60)
    print("INSTAGRAM POST EXTRACTION COMPLETE")
    print("="*60)
    print(f"Account: {account}")
    print(f"Total posts collected: {len(posts)}")
    print(f"Posts with comments: {len(posts_with_comments)}")
    print(f"Posts with errors: {len(posts_with_errors)}")
    print(f"Total comments to extract: {total_comments}")
    print(f"Output file: {output_file}")
    print("="*60)

    # Print top posts by comment count
    print("\nTop 10 posts by comment count:")
    sorted_posts = sorted(posts, key=lambda x: x.get("comments_count", 0), reverse=True)
    for i, post in enumerate(sorted_posts[:10], 1):
        print(f"  {i}. {post.get('comments_count', 0)} comments - {post['url']}")


if __name__ == "__main__":
    main()
