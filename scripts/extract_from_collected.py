#!/usr/bin/env python
"""Extract comments from posts using pre-collected hover data.

This script reads the post data collected by collect_all_posts_hover.py
and extracts comments only from posts that have them (skipping 0-comment posts).
"""

import json
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.instagram import InstagramScraper
from src.config.settings import get_settings
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Reduce noise
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def find_latest_collected_file(account: str) -> Path:
    """Find the most recent collected posts file for an account."""
    collected_dir = Path("data/collected_posts")
    if not collected_dir.exists():
        return None

    # Look for files matching pattern
    pattern = f"{account}_posts_*.json"
    files = list(collected_dir.glob(pattern))

    if not files:
        return None

    # Sort by modification time, most recent first
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0]


def load_collected_posts(file_path: Path) -> dict:
    """Load collected posts from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_from_collected(
    account: str,
    input_file: str = None,
    min_comments: int = 1,
    max_posts: int = None,
    skip_existing: bool = True,
    sort_by: str = "comments",  # "comments", "likes", "random"
    headless: bool = False
):
    """
    Extract comments from posts using pre-collected hover data.

    Args:
        account: Instagram account name
        input_file: Path to collected posts JSON (auto-detect if None)
        min_comments: Minimum comments to process a post (default 1)
        max_posts: Maximum posts to process (None = all)
        skip_existing: Skip posts already in database
        sort_by: How to sort posts - "comments", "likes", or "random"
        headless: Run browser in headless mode
    """
    # Find or use input file
    if input_file:
        input_path = Path(input_file)
    else:
        input_path = find_latest_collected_file(account)

    if not input_path or not input_path.exists():
        logger.error(f"No collected posts file found for {account}")
        logger.info("Run collect_all_posts_hover.py first to collect post data")
        return

    logger.info(f"Loading collected posts from: {input_path}")
    data = load_collected_posts(input_path)

    posts = data.get('posts', [])
    logger.info(f"Loaded {len(posts)} posts from collection")

    # Filter posts with minimum comments
    posts_to_extract = [
        p for p in posts
        if p.get('comments', 0) >= min_comments and p.get('comments', -1) != -1
    ]

    logger.info(f"Posts with >= {min_comments} comments: {len(posts_to_extract)}")

    if not posts_to_extract:
        logger.info("No posts to extract!")
        return

    # Sort posts
    if sort_by == "comments":
        posts_to_extract.sort(key=lambda p: p.get('comments', 0), reverse=True)
    elif sort_by == "likes":
        posts_to_extract.sort(key=lambda p: p.get('likes', 0), reverse=True)
    elif sort_by == "random":
        import random
        random.shuffle(posts_to_extract)

    # Limit if specified
    if max_posts and len(posts_to_extract) > max_posts:
        posts_to_extract = posts_to_extract[:max_posts]
        logger.info(f"Limited to {max_posts} posts")

    # Initialize database and check existing
    settings = get_settings()
    db_manager = DatabaseManager(settings.database_path)

    if skip_existing:
        existing_post_ids = db_manager.get_all_post_ids(account)
        original_count = len(posts_to_extract)
        posts_to_extract = [
            p for p in posts_to_extract
            if p.get('post_id') not in existing_post_ids
        ]
        skipped = original_count - len(posts_to_extract)
        if skipped > 0:
            logger.info(f"Skipped {skipped} posts already in database")

    if not posts_to_extract:
        logger.info("All posts already extracted!")
        return

    # Calculate expected comments
    total_expected_comments = sum(p.get('comments', 0) for p in posts_to_extract)
    logger.info(f"Posts to extract: {len(posts_to_extract)}")
    logger.info(f"Expected total comments: {total_expected_comments:,}")

    # Initialize scraper
    config = settings.get_platform_config("instagram")
    config["headless"] = headless

    scraper = InstagramScraper(config)

    try:
        # Login
        scraper._ensure_logged_in()

        # Process each post
        total_comments_extracted = 0
        successful_posts = 0
        failed_posts = 0

        for i, post in enumerate(posts_to_extract):
            post_url = post['url']
            post_id = post.get('post_id', 'unknown')
            expected_comments = post.get('comments', 0)

            logger.info(f"[{i+1}/{len(posts_to_extract)}] Processing {post_id} ({expected_comments} comments)")

            try:
                # Navigate to post
                scraper._page.goto(post_url, wait_until="domcontentloaded")
                scraper._page.wait_for_timeout(3000)

                # Extract comments
                comments = scraper._comments_section.extract_comments_for_post(post_id)

                if comments:
                    # Save to database
                    db_manager.save_post(
                        account=account,
                        post_id=post_id,
                        url=post_url,
                        platform="instagram"
                    )

                    for comment in comments:
                        db_manager.save_comment(
                            post_id=post_id,
                            author=comment.get('author', 'unknown'),
                            text=comment.get('text', ''),
                            likes=comment.get('likes', 0),
                            is_reply=comment.get('is_reply', False),
                            parent_author=comment.get('parent_author')
                        )

                    total_comments_extracted += len(comments)
                    successful_posts += 1
                    logger.info(f"  Extracted {len(comments)} comments (expected {expected_comments})")
                else:
                    logger.warning(f"  No comments extracted (expected {expected_comments})")
                    failed_posts += 1

                # Small delay between posts
                scraper._page.wait_for_timeout(1000)

            except Exception as e:
                logger.error(f"  Error: {e}")
                failed_posts += 1

                # Check for consecutive failures
                if failed_posts >= 5:
                    logger.error("Too many consecutive failures, stopping")
                    break

        # Summary
        logger.info("=" * 60)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Posts processed: {successful_posts + failed_posts}")
        logger.info(f"Successful: {successful_posts}")
        logger.info(f"Failed: {failed_posts}")
        logger.info(f"Total comments extracted: {total_comments_extracted:,}")
        logger.info(f"Expected comments: {total_expected_comments:,}")

        if total_expected_comments > 0:
            coverage = (total_comments_extracted / total_expected_comments) * 100
            logger.info(f"Coverage: {coverage:.1f}%")

    finally:
        scraper.close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract comments from posts using pre-collected hover data"
    )
    parser.add_argument(
        "account",
        help="Instagram account to extract from"
    )
    parser.add_argument(
        "-f", "--file",
        help="Path to collected posts JSON file (auto-detect if not specified)"
    )
    parser.add_argument(
        "-m", "--min-comments",
        type=int,
        default=1,
        help="Minimum comments to process a post (default: 1)"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        help="Maximum number of posts to process"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip posts already in database"
    )
    parser.add_argument(
        "--sort",
        choices=["comments", "likes", "random"],
        default="comments",
        help="How to sort posts (default: comments)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    args = parser.parse_args()

    extract_from_collected(
        account=args.account,
        input_file=args.file,
        min_comments=args.min_comments,
        max_posts=args.max_posts,
        skip_existing=not args.no_skip,
        sort_by=args.sort,
        headless=args.headless
    )


if __name__ == "__main__":
    main()
