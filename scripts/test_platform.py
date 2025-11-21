"""Unified test script for platform extraction with comments."""

import sys
import os
import logging
import argparse

# Fix Windows console encoding for UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from src.config.settings import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def get_scraper(platform: str, config: dict):
    """Get the appropriate scraper for the platform."""
    platform_lower = platform.lower()

    if platform_lower == 'instagram':
        from src.scrapers.instagram.scraper import InstagramScraper
        return InstagramScraper(config)
    elif platform_lower == 'facebook':
        from src.scrapers.facebook.scraper import FacebookScraper
        return FacebookScraper(config)
    elif platform_lower == 'twitter':
        from src.scrapers.twitter.scraper import TwitterScraper
        return TwitterScraper(config)
    elif platform_lower == 'linkedin':
        from src.scrapers.linkedin.scraper import LinkedInScraper
        return LinkedInScraper(config)
    else:
        raise ValueError(f"Unknown platform: {platform}")


def get_platform_config(platform: str, settings, browser_profile: str) -> dict:
    """Get platform-specific configuration."""
    platform_lower = platform.lower()

    if platform_lower == 'instagram':
        return {
            "username": settings.instagram.username or os.getenv("EXTRACTOR_INSTAGRAM__USERNAME"),
            "password": settings.instagram.password or os.getenv("EXTRACTOR_INSTAGRAM__PASSWORD"),
            "browser_profile": browser_profile,
            "headless": False,
        }
    elif platform_lower == 'facebook':
        return {
            "email": settings.facebook.email or os.getenv("EXTRACTOR_FACEBOOK__EMAIL"),
            "password": settings.facebook.password or os.getenv("EXTRACTOR_FACEBOOK__PASSWORD"),
            "browser_profile": browser_profile,
            "headless": False,
        }
    elif platform_lower == 'twitter':
        return {
            "credentials": {
                "username": settings.twitter.username or os.getenv("EXTRACTOR_TWITTER__USERNAME"),
                "password": settings.twitter.password or os.getenv("EXTRACTOR_TWITTER__PASSWORD"),
            },
            "browser": {
                "headless": False,
                "profile_dir": browser_profile,
            }
        }
    elif platform_lower == 'linkedin':
        return {
            "credentials": {
                "email": settings.linkedin.email or os.getenv("EXTRACTOR_LINKEDIN__EMAIL"),
                "password": settings.linkedin.password or os.getenv("EXTRACTOR_LINKEDIN__PASSWORD"),
            },
            "browser": {
                "headless": False,
                "profile_dir": browser_profile,
            }
        }
    else:
        raise ValueError(f"Unknown platform: {platform}")


def test_extract_with_comments(platform: str, account_id: str, max_posts: int = 10):
    """Test extracting posts with comments from a profile."""

    # Load settings from config
    settings = get_settings()

    # Get browser profile path
    browser_profile = os.path.join(
        project_root,
        "data",
        "browser_profiles",
        f"{platform.lower()}_{account_id}"
    )

    config = get_platform_config(platform, settings, browser_profile)

    print(f"\n{'='*60}")
    print(f"Platform: {platform.upper()}")
    print(f"Account: {account_id}")
    print(f"Max posts: {max_posts}")
    print(f"Browser profile: {browser_profile}")
    print(f"{'='*60}\n")

    # Check if browser profile exists
    if os.path.exists(browser_profile):
        print(f"Found existing browser profile with cookies/session data")
    else:
        print(f"No existing browser profile found, will create new one")

    scraper = None
    all_results = []

    try:
        scraper = get_scraper(platform, config)

        print(f"\nStarting extraction...")

        for result in scraper._scrape_posts(account_id, since_date=None, max_posts=max_posts):
            post = result.post
            comments = result.comments

            all_results.append({
                'post_id': post.platform_id,
                'url': post.url,
                'caption': post.text[:100] + '...' if len(post.text) > 100 else post.text,
                'likes': post.likes,
                'comments_count': len(comments),
                'comments': [
                    {
                        'author': c.author.username,
                        'text': c.text[:50] + '...' if len(c.text) > 50 else c.text,
                        'likes': c.likes
                    }
                    for c in comments[:5]  # Show first 5 comments
                ]
            })

            print(f"\nPost {len(all_results)}: {post.platform_id}")
            print(f"  Likes: {post.likes}")
            print(f"  Comments: {len(comments)}")
            if comments:
                for i, c in enumerate(comments[:3]):
                    text_preview = c.text[:60] if c.text else "(empty)"
                    print(f"    [{i+1}] @{c.author.username}: {text_preview}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if scraper:
            scraper.close()
        return []

    # Print summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Platform: {platform}")
    print(f"Account: {account_id}")
    print(f"Total posts: {len(all_results)}")
    total_comments = sum(r['comments_count'] for r in all_results)
    print(f"Total comments: {total_comments}")
    print(f"{'='*60}")

    # Summary of posts with comments
    posts_with_comments = [r for r in all_results if r['comments_count'] > 0]
    if posts_with_comments:
        print(f"\nPosts with comments ({len(posts_with_comments)}):")
        for r in posts_with_comments:
            print(f"  - {r['post_id']}: {r['comments_count']} comments")
    else:
        print("\nNo comments found on any posts.")
        print("This could mean:")
        print("  - Comments are disabled on these posts")
        print("  - The comment selectors need updating")
        print("  - Comments require additional loading")

    if scraper:
        scraper.close()

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description='Test extraction from social media platforms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_platform.py instagram personalpy 10
  python test_platform.py facebook meta 5
  python test_platform.py twitter elonmusk 20
  python test_platform.py linkedin microsoft 10
        """
    )
    parser.add_argument('platform', choices=['instagram', 'facebook', 'twitter', 'linkedin'],
                        help='Platform to extract from')
    parser.add_argument('account', help='Account username or ID')
    parser.add_argument('max_posts', nargs='?', type=int, default=10,
                        help='Maximum posts to extract (default: 10)')

    args = parser.parse_args()

    test_extract_with_comments(args.platform, args.account, args.max_posts)


if __name__ == "__main__":
    main()
