#!/usr/bin/env python
"""Test script for Twitter extraction using Google OAuth."""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.scrapers.twitter.scraper import TwitterScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Test Twitter extraction")
    parser.add_argument(
        "account",
        help="Twitter account to scrape (e.g., 'elonmusk')"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=5,
        help="Maximum posts to extract (default: 5)"
    )
    args = parser.parse_args()

    settings = get_settings()
    config = settings.get_platform_config("twitter")

    logger.info(f"Twitter config: google_auth_enabled={config['google_auth']['enabled']}")
    logger.info(f"Twitter account: {args.account}")
    logger.info(f"Max posts: {args.max_posts}")

    # Check configuration
    if config['google_auth']['enabled']:
        if not config['google_auth']['email'] or not config['google_auth']['password']:
            logger.error("Google OAuth enabled but credentials not set!")
            logger.error("Set EXTRACTOR_TWITTER__GOOGLE_EMAIL and EXTRACTOR_TWITTER__GOOGLE_PASSWORD in .env")
            sys.exit(1)
        logger.info(f"Using Google OAuth with email: {config['google_auth']['email'][:5]}***")
    else:
        if not config['credentials']['username'] or not config['credentials']['password']:
            logger.error("Twitter credentials not configured!")
            logger.error("Either set EXTRACTOR_TWITTER__USERNAME/PASSWORD or enable Google OAuth")
            sys.exit(1)
        logger.info(f"Using Twitter credentials for: {config['credentials']['username']}")

    try:
        scraper = TwitterScraper(config)

        # Test profile scraping
        logger.info(f"Scraping profile: {args.account}")
        profile = scraper._scrape_profile(args.account)
        logger.info(f"Profile: {profile.display_name} (@{profile.username})")
        logger.info(f"Followers: {profile.followers_count}, Following: {profile.following_count}")

        # Test post scraping
        logger.info(f"Scraping {args.max_posts} posts...")
        posts_count = 0
        for result in scraper._scrape_posts(args.account, None, args.max_posts):
            posts_count += 1
            post = result.post
            logger.info(
                f"Post {posts_count}: {post.platform_id} | "
                f"likes={post.likes} | replies={post.comments_count} | "
                f"text={post.text[:50]}..."
            )

        logger.info(f"Successfully scraped {posts_count} posts")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'scraper' in locals():
            scraper.close()


if __name__ == "__main__":
    main()
