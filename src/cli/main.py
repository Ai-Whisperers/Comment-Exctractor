"""Main CLI implementation for the Social Media Comment Extractor."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..services.extraction import ExtractionService
from ..scrapers.registry import ScraperRegistry
from ..exporters.registry import ExporterRegistry
from ..config.settings import get_settings
from ..core.models import ClientConfig, SocialAccount, Platform

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_level: Optional[str] = None):
    """
    Set up logging configuration.

    Args:
        verbose: If True, use DEBUG level
        log_level: Explicit log level (DEBUG, INFO, WARNING, ERROR)
    """
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def print_result_box(title: str, content: dict, width: int = 50):
    """Print a formatted result box."""
    print(f"\n{'=' * width}")
    print(title)
    print(f"{'=' * width}")
    for key, value in content.items():
        print(f"{key}: {value}")
    print(f"{'=' * width}\n")


# Command handlers

def cmd_extract(args):
    """Extract comments from a platform."""
    service = ExtractionService(data_dir=args.data_dir)
    settings = get_settings()

    # Get platform config
    config = settings.get_platform_config(args.platform)

    try:
        stats = service.extract(
            client=args.client,
            platform=args.platform,
            account_id=args.account,
            max_posts=args.max_posts,
            full=args.full,
            config=config
        )

        print_result_box(
            f"Extraction Complete: {args.client}",
            {
                "Platform": stats.platform,
                "Account": stats.account,
                "Posts scraped": stats.posts_scraped,
                "Comments found": stats.comments_found,
                "New comments saved": stats.new_comments_saved,
                "Duplicates skipped": stats.duplicates_skipped,
                "Duration": f"{stats.duration_seconds:.1f}s"
            }
        )

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_export(args):
    """Export comments to a file."""
    service = ExtractionService(data_dir=args.data_dir)

    # Parse date filters
    since = None
    until = None
    if args.since:
        since = datetime.fromisoformat(args.since)
    if args.until:
        until = datetime.fromisoformat(args.until)

    try:
        output_path = service.export(
            client=args.client,
            format=args.format,
            platform=args.platform,
            since=since,
            until=until,
            output_dir=args.output_dir
        )

        print(f"Exported to: {output_path}")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_export_posts(args):
    """Export posts to a file."""
    service = ExtractionService(data_dir=args.data_dir)

    # Parse date filters
    since = None
    until = None
    if args.since:
        since = datetime.fromisoformat(args.since)
    if args.until:
        until = datetime.fromisoformat(args.until)

    try:
        output_path = service.export_posts(
            client=args.client,
            format=args.format,
            platform=args.platform,
            since=since,
            until=until,
            output_dir=args.output_dir
        )

        print(f"Exported posts to: {output_path}")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stats(args):
    """Show statistics for a client."""
    service = ExtractionService(data_dir=args.data_dir)

    try:
        stats = service.get_stats(args.client)

        content = {
            "Total comments": stats["total_comments"],
            "Total posts": stats["total_posts"],
        }

        if stats["platforms"]:
            content[""] = ""  # Spacer
            content["Per platform:"] = ""
            for platform, count in stats["platforms"].items():
                content[f"  {platform}"] = f"{count} comments"

        print_result_box(f"Statistics: {stats['client']}", content)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list_platforms(args):
    """List available platforms."""
    platforms = ScraperRegistry.list_available()

    print("\nAvailable platforms:")
    for platform in platforms:
        print(f"  - {platform}")
    print()


def cmd_list_formats(args):
    """List available export formats."""
    formats = ExporterRegistry.list_available()

    print("\nAvailable export formats:")
    for fmt in formats:
        print(f"  - {fmt}")
    print()


def cmd_batch(args):
    """Run extraction for multiple accounts from a config file."""
    service = ExtractionService(data_dir=args.data_dir)
    settings = get_settings()

    # Load config file
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config_data = json.load(f)

    # Create client config
    accounts = []
    for acc in config_data.get("accounts", []):
        accounts.append(SocialAccount(
            platform=Platform(acc["platform"]),
            identifier=acc["identifier"],
            display_name=acc.get("display_name"),
            enabled=acc.get("enabled", True)
        ))

    client_config = ClientConfig(
        name=config_data.get("name", args.client or "default"),
        accounts=accounts
    )

    # Get platform configs
    platform_configs = {}
    for platform in Platform:
        platform_configs[platform.value] = settings.get_platform_config(platform.value)

    try:
        results = service.extract_all(
            client_config=client_config,
            max_posts=args.max_posts,
            full=args.full,
            platform_configs=platform_configs
        )

        print(f"\n{'=' * 50}")
        print(f"Batch Extraction Complete: {client_config.name}")
        print(f"{'=' * 50}")

        total_comments = 0
        for stats in results:
            status = "OK" if stats.is_success else "FAILED"
            print(f"  {stats.platform}:{stats.account} - {status}")
            print(f"    Posts: {stats.posts_scraped}, New comments: {stats.new_comments_saved}")
            total_comments += stats.new_comments_saved

            if stats.error:
                print(f"    Error: {stats.error}")

        print(f"\nTotal new comments: {total_comments}")
        print(f"{'=' * 50}\n")

        # Auto-export if requested
        if args.export:
            output_path = service.export(
                client=client_config.name,
                format=args.export,
            )
            print(f"Exported to: {output_path}")

    except Exception as e:
        logger.error(f"Batch extraction failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_profile(args):
    """Get profile information for an account."""
    settings = get_settings()
    config = settings.get_platform_config(args.platform)

    try:
        scraper = ScraperRegistry.get(args.platform, config)
        profile = scraper.get_profile(args.account)

        print_result_box(
            f"Profile: {args.account}",
            {
                "Username": profile.username,
                "Display Name": profile.display_name or "N/A",
                "Bio": (profile.bio[:50] + "...") if profile.bio and len(profile.bio) > 50 else (profile.bio or "N/A"),
                "Followers": f"{profile.followers_count:,}" if profile.followers_count else "N/A",
                "Following": f"{profile.following_count:,}" if profile.following_count else "N/A",
                "Posts": f"{profile.posts_count:,}" if profile.posts_count else "N/A",
                "Verified": profile.is_verified,
                "Private": profile.is_private,
                "Platform": profile.platform,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Social Media Comment Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from Facebook
  python -m src.cli extract personalpy facebook personalpy --max-posts 50

  # Export to CSV
  python -m src.cli export personalpy --format csv

  # Export posts to JSON
  python -m src.cli export-posts personalpy --format json

  # Run batch extraction
  python -m src.cli batch --config config/personal-paraguay.json --export json

  # Show stats
  python -m src.cli stats personalpy

  # Get profile info
  python -m src.cli profile facebook personalpy

  # List available platforms
  python -m src.cli list-platforms
        """
    )

    # Global options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set log level")
    parser.add_argument("--data-dir", default="data", help="Data directory")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract from a single account")
    extract_parser.add_argument("client", help="Client name")
    extract_parser.add_argument("platform", help="Platform (facebook, instagram, twitter)")
    extract_parser.add_argument("account", help="Account username or ID")
    extract_parser.add_argument("--max-posts", type=int, default=100, help="Max posts to extract")
    extract_parser.add_argument("--full", action="store_true", help="Full extraction (ignore last date)")
    extract_parser.set_defaults(func=cmd_extract)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export comments")
    export_parser.add_argument("client", help="Client name")
    export_parser.add_argument("--format", default="json", help="Export format (json, csv, jsonl)")
    export_parser.add_argument("--platform", help="Filter by platform")
    export_parser.add_argument("--since", help="Comments after date (ISO format)")
    export_parser.add_argument("--until", help="Comments before date (ISO format)")
    export_parser.add_argument("--output-dir", help="Output directory")
    export_parser.set_defaults(func=cmd_export)

    # Export posts command
    export_posts_parser = subparsers.add_parser("export-posts", help="Export posts")
    export_posts_parser.add_argument("client", help="Client name")
    export_posts_parser.add_argument("--format", default="json", help="Export format (json, csv, jsonl)")
    export_posts_parser.add_argument("--platform", help="Filter by platform")
    export_posts_parser.add_argument("--since", help="Posts after date (ISO format)")
    export_posts_parser.add_argument("--until", help="Posts before date (ISO format)")
    export_posts_parser.add_argument("--output-dir", help="Output directory")
    export_posts_parser.set_defaults(func=cmd_export_posts)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("client", help="Client name")
    stats_parser.set_defaults(func=cmd_stats)

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch extraction from config")
    batch_parser.add_argument("--config", required=True, help="Config file path")
    batch_parser.add_argument("--client", help="Override client name")
    batch_parser.add_argument("--max-posts", type=int, default=100, help="Max posts per account")
    batch_parser.add_argument("--full", action="store_true", help="Full extraction")
    batch_parser.add_argument("--export", help="Auto-export format after extraction")
    batch_parser.set_defaults(func=cmd_batch)

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Get account profile")
    profile_parser.add_argument("platform", help="Platform (facebook, instagram, twitter)")
    profile_parser.add_argument("account", help="Account username or ID")
    profile_parser.set_defaults(func=cmd_profile)

    # List commands
    list_platforms_parser = subparsers.add_parser("list-platforms", help="List available platforms")
    list_platforms_parser.set_defaults(func=cmd_list_platforms)

    list_formats_parser = subparsers.add_parser("list-formats", help="List export formats")
    list_formats_parser.set_defaults(func=cmd_list_formats)

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose, getattr(args, "log_level", None))
    args.func(args)


if __name__ == "__main__":
    main()
