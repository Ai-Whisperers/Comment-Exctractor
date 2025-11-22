#!/usr/bin/env python
"""Test all enabled platforms (excluding Twitter)."""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.scrapers.instagram.scraper import InstagramScraper
from src.scrapers.facebook.scraper import FacebookScraper
from src.scrapers.linkedin.scraper import LinkedInScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def test_instagram():
    """Test Instagram scraper."""
    logger.info("=" * 50)
    logger.info("TESTING INSTAGRAM")
    logger.info("=" * 50)

    settings = get_settings()
    if not settings.instagram.enabled:
        logger.warning("Instagram is disabled, skipping")
        return False

    config = settings.get_platform_config("instagram")

    try:
        scraper = InstagramScraper(config)
        account = "personalpy"

        # Test profile
        logger.info(f"Scraping profile: {account}")
        profile = scraper._scrape_profile(account)
        logger.info(f"Profile: {profile.display_name} | followers={profile.followers_count}")

        # Test posts
        logger.info("Scraping 3 posts...")
        posts_count = 0
        for result in scraper._scrape_posts(account, None, 3):
            posts_count += 1
            post = result.post
            logger.info(f"Post {posts_count}: likes={post.likes} | comments={post.comments_count}")

        logger.info(f"Instagram SUCCESS - scraped {posts_count} posts")
        return True

    except Exception as e:
        logger.error(f"Instagram FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()


def test_facebook():
    """Test Facebook scraper."""
    logger.info("=" * 50)
    logger.info("TESTING FACEBOOK")
    logger.info("=" * 50)

    settings = get_settings()
    if not settings.facebook.enabled:
        logger.warning("Facebook is disabled, skipping")
        return False

    config = settings.get_platform_config("facebook")

    try:
        scraper = FacebookScraper(config)
        account = "personalpy"

        # Test profile
        logger.info(f"Scraping profile: {account}")
        profile = scraper._scrape_profile(account)
        logger.info(f"Profile: {profile.display_name} | followers={profile.followers_count}")

        # Test posts
        logger.info("Scraping 3 posts...")
        posts_count = 0
        for result in scraper._scrape_posts(account, None, 3):
            posts_count += 1
            post = result.post
            logger.info(f"Post {posts_count}: likes={post.likes} | comments={post.comments_count} | shares={post.shares}")

        logger.info(f"Facebook SUCCESS - scraped {posts_count} posts")
        return True

    except Exception as e:
        logger.error(f"Facebook FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()


def test_linkedin():
    """Test LinkedIn scraper."""
    logger.info("=" * 50)
    logger.info("TESTING LINKEDIN")
    logger.info("=" * 50)

    settings = get_settings()
    if not settings.linkedin.enabled:
        logger.warning("LinkedIn is disabled, skipping")
        return False

    config = settings.get_platform_config("linkedin")

    try:
        scraper = LinkedInScraper(config)
        account = "microsoft"

        # Test profile
        logger.info(f"Scraping profile: {account}")
        profile = scraper._scrape_profile(account)
        logger.info(f"Profile: {profile.display_name} | followers={profile.followers_count}")

        # Test posts
        logger.info("Scraping 3 posts...")
        posts_count = 0
        for result in scraper._scrape_posts(account, None, 3):
            posts_count += 1
            post = result.post
            logger.info(f"Post {posts_count}: likes={post.likes} | comments={post.comments_count}")

        logger.info(f"LinkedIn SUCCESS - scraped {posts_count} posts")
        return True

    except Exception as e:
        logger.error(f"LinkedIn FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'scraper' in locals():
            scraper.close()


def main():
    logger.info("TESTING ALL PLATFORMS (excluding Twitter)")
    logger.info("")

    results = {}

    # Test each platform
    results['instagram'] = test_instagram()
    results['facebook'] = test_facebook()
    results['linkedin'] = test_linkedin()

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)

    for platform, success in results.items():
        status = "PASS" if success else "FAIL"
        logger.info(f"{platform.upper()}: {status}")

    total_passed = sum(results.values())
    total_tests = len(results)
    logger.info(f"\nTotal: {total_passed}/{total_tests} passed")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
