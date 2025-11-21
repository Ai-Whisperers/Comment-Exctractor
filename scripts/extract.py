#!/usr/bin/env python
"""CLI entry point for the Comment Extractor."""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.extraction import ExtractionService
from src.scrapers.registry import ScraperRegistry
from src.exporters.registry import ExporterRegistry
from src.config.settings import get_settings
from src.core.models import ClientConfig, SocialAccount, Platform


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


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

        print(f"\n{'='*50}")
        print(f"Extraction Complete: {args.client}")
        print(f"{'='*50}")
        print(f"Platform: {stats.platform}")
        print(f"Account: {stats.account}")
        print(f"Posts scraped: {stats.posts_scraped}")
        print(f"Comments found: {stats.comments_found}")
        print(f"New comments saved: {stats.new_comments_saved}")
        print(f"Duplicates skipped: {stats.duplicates_skipped}")
        print(f"Duration: {stats.duration_seconds:.1f}s")
        print(f"{'='*50}\n")

    except Exception as e:
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
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stats(args):
    """Show statistics for a client."""
    service = ExtractionService(data_dir=args.data_dir)

    try:
        stats = service.get_stats(args.client)

        print(f"\n{'='*50}")
        print(f"Statistics: {stats['client']}")
        print(f"{'='*50}")
        print(f"Total comments: {stats['total_comments']}")
        print(f"Total posts: {stats['total_posts']}")

        if stats['platforms']:
            print("\nPer platform:")
            for platform, count in stats['platforms'].items():
                print(f"  {platform}: {count} comments")

        print(f"{'='*50}\n")

    except Exception as e:
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

        print(f"\n{'='*50}")
        print(f"Batch Extraction Complete: {client_config.name}")
        print(f"{'='*50}")

        total_comments = 0
        for stats in results:
            status = "OK" if stats.is_success else "FAILED"
            print(f"  {stats.platform}:{stats.account} - {status}")
            print(f"    Posts: {stats.posts_scraped}, New comments: {stats.new_comments_saved}")
            total_comments += stats.new_comments_saved

            if stats.error:
                print(f"    Error: {stats.error}")

        print(f"\nTotal new comments: {total_comments}")
        print(f"{'='*50}\n")

        # Auto-export if requested
        if args.export:
            output_path = service.export(
                client=client_config.name,
                format=args.export,
            )
            print(f"Exported to: {output_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Social Media Comment Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from Facebook
  python extract.py extract personalpy facebook personalpy --max-posts 50

  # Export to JSON
  python extract.py export personalpy --format json

  # Run batch extraction
  python extract.py batch --config config/personal-paraguay.json --export json

  # Show stats
  python extract.py stats personalpy
        """
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
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

    # List commands
    list_platforms_parser = subparsers.add_parser("list-platforms", help="List available platforms")
    list_platforms_parser.set_defaults(func=cmd_list_platforms)

    list_formats_parser = subparsers.add_parser("list-formats", help="List export formats")
    list_formats_parser.set_defaults(func=cmd_list_formats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
