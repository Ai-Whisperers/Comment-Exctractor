#!/usr/bin/env python
"""Test script for LinkedIn extraction."""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.scrapers.linkedin.scraper import LinkedInScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Test LinkedIn extraction")
    parser.add_argument(
        "account",
        help="LinkedIn profile username (e.g., 'satlokomern' or company page)"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=5,
        help="Maximum posts to extract (default: 5)"
    )
    args = parser.parse_args()

    settings = get_settings()
    config = settings.get_platform_config("linkedin")

    logger.info(f"LinkedIn account: {args.account}")
    logger.info(f"Max posts: {args.max_posts}")

    # Check configuration
    if not config['credentials']['email'] or not config['credentials']['password']:
        logger.error("LinkedIn credentials not configured!")
        logger.error("Set EXTRACTOR_LINKEDIN__EMAIL and EXTRACTOR_LINKEDIN__PASSWORD in .env")
        sys.exit(1)

    logger.info(f"Using LinkedIn credentials for: {config['credentials']['email'][:5]}***")

    try:
        scraper = LinkedInScraper(config)

        # Test profile scraping
        logger.info(f"Scraping profile: {args.account}")
        profile = scraper._scrape_profile(args.account)
        logger.info(f"Profile: {profile.display_name} (@{profile.username})")
        logger.info(f"Followers: {profile.followers_count}, Connections: {profile.following_count}")

        # Test post scraping
        logger.info(f"Scraping {args.max_posts} posts...")
        posts_count = 0
        for result in scraper._scrape_posts(args.account, None, args.max_posts):
            posts_count += 1
            post = result.post
            logger.info(
                f"Post {posts_count}: {post.platform_id} | "
                f"likes={post.likes} | comments={post.comments_count} | "
                f"text={post.text[:50] if post.text else 'N/A'}..."
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
