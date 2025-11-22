#!/usr/bin/env python
"""
Script to extract comments from pre-collected posts data.
Supports both Instagram and Facebook posts JSON files.

Usage:
    # Extract from Instagram posts
    python scripts/extract_comments.py data/instagram_posts/personalpy_posts_*.json --platform instagram

    # Extract from Facebook posts
    python scripts/extract_comments.py data/facebook_posts/personalpy_posts_*.json --platform facebook

    # With options
    python scripts/extract_comments.py posts.json --platform instagram --min-comments 5 --max-posts 100
"""

import json
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings, get_settings
from src.config.paths import get_paths
from src.scrapers.facebook.scraper import FacebookScraper
from src.scrapers.instagram.scraper import InstagramScraper
from src.storage.sqlite import SQLiteStorage

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


def load_posts_file(filepath: str) -> dict:
    """Load posts from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_comments(
    posts_file: str,
    platform: str,
    min_comments: int = 1,
    max_posts: int = None,
    resume: bool = True,
    save_to_db: bool = True
):
    """
    Extract comments from posts in a JSON file.

    Args:
        posts_file: Path to JSON file with post list
        platform: Platform name (instagram or facebook)
        min_comments: Only extract from posts with at least this many comments
        max_posts: Maximum number of posts to process
        resume: Skip posts that already have comments extracted
        save_to_db: Save comments to SQLite database
    """
    # Load posts
    data = load_posts_file(posts_file)
    account_id = data.get("account_id") or data.get("account", "unknown")
    all_posts = data.get("posts", [])

    logger.info(f"Loaded {len(all_posts)} posts from {posts_file}")
    logger.info(f"Platform: {platform}")

    # Filter posts by comment count
    comment_key = "comments_count" if "comments_count" in (all_posts[0] if all_posts else {}) else "comments"
    posts_to_process = [
        p for p in all_posts
        if p.get(comment_key, 0) >= min_comments
    ]

    if max_posts:
        posts_to_process = posts_to_process[:max_posts]

    logger.info(f"Processing {len(posts_to_process)} posts with >= {min_comments} comments")

    # Setup scraper based on platform
    if platform.lower() == "instagram":
        settings = get_settings()
        config = settings.get_platform_config('instagram')
        config["headless"] = False
        scraper = InstagramScraper(config)
    elif platform.lower() == "facebook":
        settings = Settings()
        config = settings.get_platform_config('facebook')
        scraper = FacebookScraper(config)
    else:
        raise ValueError(f"Unknown platform: {platform}")

    # Use new account-based folder structure from centralized paths
    paths = get_paths()
    output_dir = paths.comments_dir(account_id, platform.lower())

    # Setup storage
    storage = SQLiteStorage() if save_to_db else None

    # Track progress
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = output_dir / "progress.json"

    # Load existing progress
    processed_ids = set()
    if resume and progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
                processed_ids = set(progress.get("processed_post_ids", []))
            logger.info(f"Resuming - {len(processed_ids)} posts already processed")
        except Exception as e:
            logger.warning(f"Could not load progress: {e}")

    # Store all extracted comments
    all_comments = []

    try:
        scraper._ensure_logged_in()

        total_comments = 0
        posts_processed = 0
        posts_skipped = 0

        for i, post in enumerate(posts_to_process, 1):
            post_id = post.get("post_id", "")
            url = post.get("url", "")
            expected_comments = post.get(comment_key, 0)

            # Skip if already processed
            if post_id in processed_ids:
                posts_skipped += 1
                continue

            # Skip if no URL
            if not url:
                logger.warning(f"Post {i} has no URL, skipping")
                continue

            try:
                # Navigate to post
                logger.info(f"Post {i}/{len(posts_to_process)} | {expected_comments} comments | {url[:60]}...")

                scraper._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                scraper._page.wait_for_timeout(2000)

                # Check rate limit
                if scraper._check_rate_limit():
                    logger.warning("Rate limit detected, waiting 60 seconds...")
                    scraper._page.wait_for_timeout(60000)
                    if scraper._check_rate_limit():
                        logger.error("Still rate limited, stopping")
                        break

                # Extract comments based on platform
                if platform.lower() == "instagram":
                    # For Instagram, use the comments section to extract comments
                    raw_comments = scraper._comments_section.extract_comments_for_post(post_id or f"post_{i}")
                else:
                    # For Facebook
                    raw_comments = scraper._comments_section.extract_comments_for_post(post_id or f"post_{i}")

                if raw_comments:
                    # Convert to Comment objects
                    try:
                        comments = scraper._create_comment_objects(raw_comments, post_id)
                    except Exception as conv_err:
                        import traceback
                        logger.error(f"Error converting comments for post {post_id}: {conv_err}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        logger.error(f"raw_comments type: {type(raw_comments)}, len: {len(raw_comments) if hasattr(raw_comments, '__len__') else 'N/A'}")
                        if raw_comments and len(raw_comments) > 0:
                            logger.error(f"First raw comment type: {type(raw_comments[0])}, value: {str(raw_comments[0])[:200]}")
                        continue

                    # Save to database if enabled
                    if storage:
                        for comment in comments:
                            storage.save_comment(account_id, comment)

                    # Store for JSON export
                    all_comments.extend([{
                        "post_id": post_id,
                        "post_url": url,
                        "comment_id": c.platform_id,
                        "author": c.author.username if c.author else "",
                        "author_url": c.author.profile_url if c.author else "",
                        "text": c.text,
                        "likes": c.likes,
                        "parent_id": c.parent_id,
                        "replies_count": c.replies_count,
                        "depth": c.raw_data.get("depth", 1) if c.raw_data else 1,
                        "published_at": c.published_at.isoformat() if c.published_at else None,
                    } for c in comments])

                    total_comments += len(comments)
                    logger.info(f"Extracted {len(comments)} comments from post {post_id}")
                else:
                    logger.warning(f"No comments extracted from post {post_id}")

                # Mark as processed
                processed_ids.add(post_id)
                posts_processed += 1

                # Save progress every 5 posts
                if posts_processed % 5 == 0:
                    _save_progress(progress_file, account_id, processed_ids, total_comments)
                    logger.debug(f"Progress saved: {posts_processed} posts, {total_comments} comments")

                # Delay between posts
                scraper._page.wait_for_timeout(1500)

            except Exception as e:
                import traceback
                logger.error(f"Error processing post {post_id}: {e}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                continue

        # Final progress save
        _save_progress(progress_file, account_id, processed_ids, total_comments, completed=True)

        # Save all comments to JSON
        if all_comments:
            # Use date-based filename (e.g., 2025-11-21.json)
            date_str = datetime.now().strftime("%Y-%m-%d")
            comments_file = output_dir / f"{date_str}.json"

            # Calculate stats
            total_replies = sum(1 for c in all_comments if c.get("parent_id"))
            top_level = len(all_comments) - total_replies

            # Calculate expected comments from input posts
            expected_comments = sum(p.get(comment_key, 0) for p in posts_to_process if p.get("post_id") in processed_ids)

            with open(comments_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "meta": {
                        "version": "2.0",
                        "extraction_type": "full" if not max_posts else "partial",
                        "posts_processed": posts_processed,
                        "is_complete": True,
                    },
                    "account_id": account_id,
                    "platform": platform,
                    "extracted_at": datetime.now().isoformat(),
                    "total_posts_processed": posts_processed,
                    "total_comments": len(all_comments),
                    "stats": {
                        "top_level_comments": top_level,
                        "replies": total_replies,
                        "expected_comments": expected_comments,
                        "extraction_ratio": round(len(all_comments) / expected_comments, 2) if expected_comments > 0 else 0,
                    },
                    "comments": all_comments
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(all_comments)} comments to {comments_file}")

            # Create/update latest.json symlink (or copy on Windows)
            latest_file = output_dir / "latest.json"
            try:
                if latest_file.exists():
                    latest_file.unlink()
                # On Windows, use copy instead of symlink
                import shutil
                shutil.copy2(comments_file, latest_file)
                logger.info(f"Updated latest.json -> {comments_file.name}")
            except Exception as e:
                logger.warning(f"Could not create latest.json: {e}")

        # Summary
        print("\n" + "="*60)
        print("COMMENT EXTRACTION COMPLETE")
        print("="*60)
        print(f"Platform: {platform}")
        print(f"Account: {account_id}")
        print(f"Posts processed: {posts_processed}")
        print(f"Posts skipped (already done): {posts_skipped}")
        print(f"Total comments extracted: {total_comments}")
        if all_comments:
            print(f"Comments file: {comments_file}")
        print("="*60)

    finally:
        scraper.close()


def _save_progress(progress_file, account_id, processed_ids, total_comments, completed=False):
    """Save extraction progress to file."""
    progress_data = {
        "account_id": account_id,
        "updated_at": datetime.now().isoformat(),
        "processed_post_ids": list(processed_ids),
        "total_comments": total_comments,
    }
    if completed:
        progress_data["completed_at"] = datetime.now().isoformat()

    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Extract comments from pre-collected posts data"
    )
    parser.add_argument(
        "posts_file",
        help="Path to JSON file with post list"
    )
    parser.add_argument(
        "--platform", "-p",
        required=True,
        choices=["instagram", "facebook"],
        help="Platform (instagram or facebook)"
    )
    parser.add_argument(
        "--min-comments", "-m",
        type=int,
        default=1,
        help="Only process posts with at least this many comments (default: 1)"
    )
    parser.add_argument(
        "--max-posts", "-n",
        type=int,
        default=None,
        help="Maximum number of posts to process"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't skip already processed posts"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Don't save to SQLite database"
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.posts_file).exists():
        logger.error(f"File not found: {args.posts_file}")
        sys.exit(1)

    try:
        extract_comments(
            posts_file=args.posts_file,
            platform=args.platform,
            min_comments=args.min_comments,
            max_posts=args.max_posts,
            resume=not args.no_resume,
            save_to_db=not args.no_db
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user - progress saved")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
