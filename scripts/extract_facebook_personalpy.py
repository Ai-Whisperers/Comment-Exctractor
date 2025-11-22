#!/usr/bin/env python
"""
Script to extract all posts from personalpy Facebook page.
Collects post links with comment counts, likes, and shares.
"""

import json
import logging
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings
from src.config.paths import get_paths
from src.scrapers.facebook.scraper import FacebookScraper


def clean_facebook_url(url: str) -> str:
    """
    Clean Facebook URL by removing tracking parameters.

    Removes: comment_id, __cft__, __tn__, etc.

    Args:
        url: Original Facebook URL

    Returns:
        Cleaned URL
    """
    parsed = urlparse(url)

    # Parse query parameters
    params = parse_qs(parsed.query)

    # Remove tracking/noise parameters
    params_to_remove = [
        'comment_id', '__cft__', '__tn__', '__eep__',
        'ref', 'fref', 'hc_ref', 'notif_id', 'notif_t'
    ]

    cleaned_params = {
        k: v for k, v in params.items()
        if not any(k.startswith(p) for p in params_to_remove)
    }

    # Rebuild URL
    if cleaned_params:
        query_string = urlencode(cleaned_params, doseq=True)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query_string}"
    else:
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    return clean_url

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

# Reduce noise
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def extract_facebook_posts(account_id: str = "personalpy", max_posts: int = 1000) -> list:
    """
    Extract all posts from a Facebook page with comment counts.

    Args:
        account_id: Facebook page name
        max_posts: Maximum posts to collect

    Returns:
        List of dicts with post URL and metadata
    """
    settings = Settings()
    config = settings.get_platform_config('facebook')

    logger.info(f"EXTRACTING ALL POSTS FROM FACEBOOK: {account_id}")
    logger.info(f"Max posts: {max_posts}")

    scraper = FacebookScraper(config)

    try:
        # Ensure logged in
        scraper._ensure_logged_in()

        # Navigate to profile
        scraper._profile_page.navigate(account_id)

        if not scraper._profile_page.is_page_available():
            logger.error(f"Page not found: {account_id}")
            return []

        # Collect post links - scroll all the way down
        logger.info("Collecting post links - this may take a while...")
        post_links = scraper._post_page.get_post_links(
            max_posts=max_posts,
            scroll_all=True,
            known_post_ids=set(),  # Empty = collect all
            skip_existing=False    # Don't skip any
        )

        logger.info(f"Collected {len(post_links)} post links")
        logger.info("Now getting metadata for each post...")

        # Get metadata for each post
        posts_with_data = []
        for i, url in enumerate(post_links, 1):
            try:
                # Navigate to post
                scraper._page.goto(url, wait_until="domcontentloaded")
                scraper._page.wait_for_timeout(2000)

                # Get post data including comment count
                post_data = scraper._post_page.extract_post_data(account_id)

                posts_with_data.append({
                    "url": clean_facebook_url(url),
                    "post_id": post_data.get("id", ""),
                    "comments_count": post_data.get("comments_count", 0),
                    "likes": post_data.get("likes", 0),
                    "shares": post_data.get("shares", 0),
                    "text": post_data.get("text", "")[:200] if post_data.get("text") else ""
                })

                logger.info(f"Post {i}/{len(post_links)} | comments={post_data.get('comments_count', 0)} | {url[:60]}...")

            except Exception as e:
                logger.warning(f"Error getting data for post {url[:60]}...: {e}")
                posts_with_data.append({
                    "url": clean_facebook_url(url),
                    "post_id": "",
                    "comments_count": -1,  # Error indicator
                    "likes": 0,
                    "shares": 0,
                    "text": ""
                })

            # Small delay between posts
            scraper._post_page.human_delay(500, 1000)

        # Deduplicate by post_id
        seen_ids = set()
        unique_posts = []
        for p in posts_with_data:
            pid = p.get('post_id', '')
            if pid and pid not in seen_ids:
                unique_posts.append(p)
                seen_ids.add(pid)
            elif not pid:
                unique_posts.append(p)  # Keep posts without ID

        if len(unique_posts) < len(posts_with_data):
            logger.info(f"Deduplicated {len(posts_with_data)} -> {len(unique_posts)} unique posts")

        return unique_posts

    finally:
        scraper.close()


def main():
    parser = argparse.ArgumentParser(description="Extract Facebook posts from a page")
    parser.add_argument("--account", "-a", default="personalpy", help="Facebook page name")
    parser.add_argument("--max-posts", "-n", type=int, default=1000, help="Maximum posts to collect")
    args = parser.parse_args()

    account_id = args.account
    max_posts = args.max_posts

    # Extract posts
    posts = extract_facebook_posts(account_id, max_posts)

    if not posts:
        logger.error("No posts extracted!")
        return

    # Save to file using centralized path configuration
    paths = get_paths()
    output_dir = paths.posts_dir(account_id, "facebook")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use date-based filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = output_dir / f"{date_str}.json"

    # Calculate stats
    posts_with_comments = [p for p in posts if p.get("comments_count", 0) > 0]
    total_comments = sum(p.get("comments_count", 0) for p in posts if p.get("comments_count", 0) > 0)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": {
                "version": "2.0",
                "extraction_type": "full" if max_posts >= 1000 else "partial",
                "is_complete": True,
            },
            "account_id": account_id,
            "platform": "facebook",
            "collected_at": datetime.now().isoformat(),
            "total_posts": len(posts),
            "posts_with_comments": len(posts_with_comments),
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
    print("FACEBOOK POST EXTRACTION COMPLETE")
    print("="*60)
    print(f"Account: {account_id}")
    print(f"Total posts collected: {len(posts)}")
    print(f"Posts with comments: {len(posts_with_comments)}")
    print(f"Total comments to extract: {total_comments}")
    print(f"Output file: {output_file}")
    print("="*60)

    # Print top posts by comment count
    print("\nTop 10 posts by comment count:")
    sorted_posts = sorted(posts, key=lambda x: x.get("comments_count", 0), reverse=True)
    for i, post in enumerate(sorted_posts[:10], 1):
        print(f"  {i}. {post.get('comments_count', 0)} comments - {post['url'][:60]}...")


if __name__ == "__main__":
    main()
