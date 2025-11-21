#!/usr/bin/env python3
"""
CLI tool to extract posts and comments from social media platforms.

Usage:
    python extract.py --account personalpy --max-posts 10 --output data/exports
    python extract.py --account mypage --platforms instagram facebook --format csv
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import get_settings
from src.scrapers.registry import ScraperRegistry
from src.scrapers.base import BaseScraper
from src.exporters.registry import ExporterRegistry
from src.core.models import ExtractionResult, Post, Comment, ExportMetadata


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging."""
    settings = get_settings()
    settings.log_level = log_level
    settings.setup_logging()


def extract_from_platform(
    platform: str,
    account: str,
    max_posts: int,
    headless: bool = True
) -> List[ExtractionResult]:
    """
    Extract posts and comments from a platform using the registry.

    Args:
        platform: Platform name (instagram, facebook, etc.)
        account: Account username
        max_posts: Maximum posts to extract
        headless: Run browser in headless mode

    Returns:
        List of extraction results
    """
    settings = get_settings()
    config = settings.get_platform_config(platform)
    config['headless'] = headless

    results: List[ExtractionResult] = []
    scraper: Optional[BaseScraper] = None

    try:
        # Use registry to get the appropriate scraper
        scraper = ScraperRegistry.get(platform, config)

        print(f"\nExtracting from {platform.title()}: @{account}")
        print("-" * 50)

        for result in scraper.get_posts_with_comments(account, max_posts=max_posts):
            results.append(result)
            print(f"  Post {len(results)}: {result.post.platform_id} | "
                  f"Likes: {result.post.likes:,} | "
                  f"Comments: {len(result.comments)}")

        print(f"\n{platform.title()}: {len(results)} posts extracted")
        return results

    except Exception as e:
        print(f"\n{platform.title()} Error: {e}")
        return results
    finally:
        if scraper:
            scraper.close()


def load_existing_data(file_path: Path) -> Dict[str, Any]:
    """Load existing JSON data from file if it exists."""
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load existing file {file_path}: {e}")
    return {}


def merge_extractions(
    existing: Dict[str, Any],
    new_results: List[ExtractionResult],
    account: str
) -> Dict[str, Any]:
    """
    Merge new extraction results with existing data, deduplicating by post ID.

    Args:
        existing: Existing combined data (or empty dict)
        new_results: New extraction results to merge
        account: Account name

    Returns:
        Merged data with duplicates removed
    """
    # Build a map of existing posts by ID
    existing_posts: Dict[str, Dict[str, Any]] = {}
    if "extractions" in existing:
        for extraction in existing["extractions"]:
            post_id = extraction["post"]["id"]
            existing_posts[post_id] = extraction

    # Track statistics
    new_posts_count = 0
    updated_posts_count = 0

    # Process new results
    for result in new_results:
        post_id = result.post.platform_id

        new_extraction = {
            "post": {
                "id": post_id,
                "platform": result.post.platform.value,
                "url": result.post.url,
                "text": result.post.text,
                "published_at": result.post.published_at.isoformat() if result.post.published_at else None,
                "likes": result.post.likes,
                "comments_count": result.post.comments_count,
                "shares": result.post.shares,
                "media_type": result.post.media_type,
            },
            "comments": [
                {
                    "id": c.platform_id,
                    "text": c.text,
                    "author": c.author.username or c.author.display_name,
                    "published_at": c.published_at.isoformat() if c.published_at else None,
                    "likes": c.likes,
                    "parent_id": c.parent_id,
                    "replies_count": c.replies_count,
                }
                for c in result.comments
            ]
        }

        if post_id in existing_posts:
            # Update existing post - merge comments
            existing_extraction = existing_posts[post_id]
            existing_comment_ids = {c["id"] for c in existing_extraction.get("comments", [])}

            # Add new comments that don't exist
            for new_comment in new_extraction["comments"]:
                if new_comment["id"] not in existing_comment_ids:
                    existing_extraction["comments"].append(new_comment)

            # Update post metrics (likes, comments_count may have changed)
            existing_extraction["post"] = new_extraction["post"]
            updated_posts_count += 1
        else:
            # New post
            existing_posts[post_id] = new_extraction
            new_posts_count += 1

    # Convert back to list, sorted by published_at (newest first)
    all_extractions = list(existing_posts.values())
    all_extractions.sort(
        key=lambda x: x["post"].get("published_at") or "",
        reverse=True
    )

    # Calculate totals
    total_posts = len(all_extractions)
    total_comments = sum(len(e.get("comments", [])) for e in all_extractions)

    # Collect all platforms
    platforms = list(set(e["post"]["platform"] for e in all_extractions))

    print(f"  Merge stats: {new_posts_count} new posts, {updated_posts_count} updated posts")

    return {
        "metadata": {
            "account": account,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "created_at": existing.get("metadata", {}).get("created_at", datetime.now(timezone.utc).isoformat()),
            "total_posts": total_posts,
            "total_comments": total_comments,
            "platforms": platforms,
        },
        "extractions": all_extractions
    }


def export_results(
    results: List[ExtractionResult],
    output_dir: str,
    account: str,
    format: str = "json"
) -> Dict[str, str]:
    """
    Export extraction results to files with incremental updates.

    Creates a subfolder for each account and maintains files
    that are updated incrementally (no duplicates).

    Args:
        results: Extraction results
        output_dir: Output directory
        account: Account name
        format: Export format (json, csv, jsonl)

    Returns:
        Dictionary of exported file paths
    """
    # Create account-specific subfolder
    output_path = Path(output_dir) / account
    output_path.mkdir(parents=True, exist_ok=True)

    # Collect all posts and comments
    all_posts: List[Post] = []
    all_comments: List[Comment] = []

    for result in results:
        all_posts.append(result.post)
        all_comments.extend(result.comments)

    # Create metadata
    metadata = ExportMetadata(
        client=account,
        exported_at=datetime.now(timezone.utc),
        format=format,
        total_comments=len(all_comments),
        platforms=list(set(p.platform.value for p in all_posts)),
        version="1.0"
    )

    exported_files: Dict[str, str] = {}

    # Get exporter from registry
    exporter = ExporterRegistry.get(format)

    # Determine file extension
    ext = format if format != "jsonl" else "jsonl"

    # Export posts
    posts_file = output_path / f"posts.{ext}"
    exporter.export_posts(all_posts, metadata, str(posts_file))
    exported_files['posts'] = str(posts_file)

    # Export comments
    if all_comments:
        comments_file = output_path / f"comments.{ext}"
        exporter.export(all_comments, metadata, str(comments_file))
        exported_files['comments'] = str(comments_file)

    # For JSON format, also create a combined file with incremental merge
    if format == "json":
        combined_file = output_path / "combined.json"

        # Load existing data if file exists
        existing_data = load_existing_data(combined_file)

        # Merge new results with existing data
        combined_data = merge_extractions(existing_data, results, account)

        # Save merged data
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2, default=str)

        exported_files['combined'] = str(combined_file)

        # Print summary of what's in the combined file
        print(f"\n  Combined file now contains:")
        print(f"    Total posts: {combined_data['metadata']['total_posts']}")
        print(f"    Total comments: {combined_data['metadata']['total_comments']}")

    return exported_files


def main() -> int:
    """Main entry point."""
    # Get available platforms and formats from registries
    available_platforms = ScraperRegistry.list_available()
    available_formats = ExporterRegistry.list_available()

    parser = argparse.ArgumentParser(
        description="Extract posts and comments from social media platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python extract.py --account personalpy --max-posts 10
  python extract.py --account mypage --platforms instagram --max-posts 50
  python extract.py --account mypage --platforms instagram facebook --output data/exports
  python extract.py --account mypage --format csv  # Export as CSV
  python extract.py --account mypage --format jsonl  # Export as JSONL
  python extract.py --account mypage --no-headless  # Show browser window

Available platforms: {', '.join(available_platforms)}
Available formats: {', '.join(available_formats)}
        """
    )

    parser.add_argument(
        "--account",
        required=True,
        help="Account name/username to extract from"
    )

    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["instagram"],
        choices=available_platforms,
        help=f"Platforms to extract from (default: instagram). Available: {', '.join(available_platforms)}"
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=10,
        help="Maximum posts to extract per platform (default: 10)"
    )

    parser.add_argument(
        "--output",
        default="data/exports",
        help="Output directory for exported files (default: data/exports)"
    )

    parser.add_argument(
        "--format",
        default="json",
        choices=available_formats,
        help=f"Export format (default: json). Available: {', '.join(available_formats)}"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (useful for debugging)"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    print("=" * 60)
    print("  Social Media Comment Extractor")
    print("=" * 60)
    print(f"\nAccount: {args.account}")
    print(f"Platforms: {', '.join(args.platforms)}")
    print(f"Max posts: {args.max_posts}")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")
    print(f"Headless: {not args.no_headless}")

    headless = not args.no_headless
    all_results: List[ExtractionResult] = []

    # Extract from each platform using registry
    for platform in args.platforms:
        results = extract_from_platform(platform, args.account, args.max_posts, headless)
        all_results.extend(results)

    if not all_results:
        print("\nNo posts extracted. Check your credentials and account name.")
        return 1

    # Export results
    print("\n" + "=" * 60)
    print("  Exporting Results")
    print("=" * 60)

    exported = export_results(all_results, args.output, args.account, args.format)

    print("\nExported files:")
    for file_type, file_path in exported.items():
        print(f"  {file_type}: {file_path}")

    # Summary
    total_posts = len(all_results)
    total_comments = sum(len(r.comments) for r in all_results)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"\nTotal posts extracted: {total_posts}")
    print(f"Total comments extracted: {total_comments}")
    print(f"\nDone!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
