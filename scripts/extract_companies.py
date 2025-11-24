#!/usr/bin/env python3
"""
Optimized batch extraction script for multiple companies across platforms.

Features:
- Browser session reuse per platform (major performance gain)
- Checkpoint/resume for interrupted extractions
- Progress tracking with ETA
- Incremental output streaming

Usage:
    # Extract all companies, all platforms
    python scripts/extract_companies.py

    # Extract specific companies
    python scripts/extract_companies.py --companies personal-py tigo-py

    # Extract specific platforms only
    python scripts/extract_companies.py --platforms instagram facebook

    # Resume interrupted extraction
    python scripts/extract_companies.py --resume

    # Dry run (show what would be extracted)
    python scripts/extract_companies.py --dry-run

    # Custom settings
    python scripts/extract_companies.py --max-posts 5 --headless
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.company_registry import get_registry, Company
from src.core.models import Platform, ExtractionResult
from src.utils.company_output import get_output_manager
from src.config.settings import get_settings
from src.scrapers.registry import ScraperRegistry
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging."""
    settings = get_settings()
    settings.log_level = log_level
    settings.setup_logging()


class ProgressTracker:
    """Track extraction progress with ETA calculation."""

    def __init__(self, total_accounts: int):
        self.total = total_accounts
        self.completed = 0
        self.start_time = time.time()
        self.account_times: List[float] = []

    def account_done(self, duration: float) -> None:
        """Record completion of an account extraction."""
        self.completed += 1
        self.account_times.append(duration)

    def get_eta(self) -> str:
        """Calculate estimated time remaining."""
        if not self.account_times:
            return "calculating..."

        avg_time = sum(self.account_times) / len(self.account_times)
        remaining = self.total - self.completed
        eta_seconds = avg_time * remaining

        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        elif eta_seconds < 3600:
            return f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
        else:
            hours = int(eta_seconds / 3600)
            mins = int((eta_seconds % 3600) / 60)
            return f"{hours}h {mins}m"

    def get_progress_str(self) -> str:
        """Get formatted progress string."""
        pct = (self.completed / self.total * 100) if self.total > 0 else 0
        elapsed = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        return f"[{self.completed}/{self.total}] {pct:.0f}% | Elapsed: {elapsed_str} | ETA: {self.get_eta()}"


class CheckpointManager:
    """Manage checkpoints for resumable extractions."""

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        if checkpoint_dir is None:
            checkpoint_dir = Path(__file__).parent.parent / "data" / ".checkpoints"
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / "extraction_checkpoint.json"

    def save(self, state: Dict[str, Any]) -> None:
        """Save current extraction state atomically."""
        import tempfile
        state['saved_at'] = datetime.now().isoformat()

        # Write to temp file first for atomic operation
        fd, temp_path = tempfile.mkstemp(
            dir=self.checkpoint_dir,
            suffix='.tmp',
            prefix='checkpoint_'
        )

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)

            # Atomic rename (on same filesystem)
            os.replace(temp_path, self.checkpoint_file)
            logger.debug(f"CHECKPOINT | saved atomically: {len(state.get('completed', []))} completed")

        except Exception as e:
            # Clean up temp file on error
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
            logger.error(f"CHECKPOINT | failed to save: {e}")
            raise

    def load(self) -> Optional[Dict[str, Any]]:
        """Load previous checkpoint if exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def clear(self) -> None:
        """Clear checkpoint after successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

    def get_completed_keys(self) -> set:
        """Get set of completed extraction keys (platform/identifier)."""
        state = self.load()
        if state:
            return set(state.get('completed', []))
        return set()


def load_existing_post_ids(company_id: str, platform: Platform, identifier: str) -> set:
    """
    Load existing post IDs from saved exports for a specific account.

    Args:
        company_id: Company ID (e.g., 'personal-py')
        platform: Platform enum
        identifier: Account identifier (e.g., 'personalpy')

    Returns:
        Set of post IDs that have already been extracted
    """
    from glob import glob

    # Find the export directory for this account
    export_dir = Path(__file__).parent.parent / "data" / "exports" / company_id / platform.value / identifier

    if not export_dir.exists():
        return set()

    existing_ids = set()

    # Find all posts files
    posts_files = list(export_dir.glob("*_posts.json"))

    for posts_file in posts_files:
        try:
            with open(posts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Handle both formats: list of posts or dict with 'posts' key
                if isinstance(data, list):
                    posts = data
                elif isinstance(data, dict) and 'posts' in data:
                    posts = data['posts']
                else:
                    continue

                for post in posts:
                    if 'id' in post:
                        existing_ids.add(post['id'])
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.debug(f"Could not load post IDs from {posts_file}: {e}")
            continue

    if existing_ids:
        logger.info(f"SKIP EXISTING | loaded {len(existing_ids)} existing post IDs for {platform.value}/{identifier}")

    return existing_ids


def save_results(
    results: List[ExtractionResult],
    company_id: str,
    platform: Platform,
    identifier: str,
    timestamp: datetime
) -> dict:
    """Save extraction results to company-organized output with streaming."""
    output_manager = get_output_manager()

    # Prepare data
    posts_data = []
    comments_data = []

    for result in results:
        post_dict = {
            "id": result.post.platform_id,
            "platform": result.post.platform.value,
            "url": result.post.url,
            "text": result.post.text,
            "published_at": result.post.published_at.isoformat() if result.post.published_at else None,
            "likes": result.post.likes,
            "comments_count": result.post.comments_count,
            "shares": result.post.shares,
            "media_type": result.post.media_type,
        }
        posts_data.append(post_dict)

        for comment in result.comments:
            comment_dict = {
                "id": comment.platform_id,
                "post_id": result.post.platform_id,
                "text": comment.text,
                "author": comment.author.username or comment.author.display_name,
                "author_id": comment.author.platform_id,
                "published_at": comment.published_at.isoformat() if comment.published_at else None,
                "likes": comment.likes,
                "parent_id": comment.parent_id,
                "replies_count": comment.replies_count,
            }
            comments_data.append(comment_dict)

    # Save posts
    posts_path = output_manager.get_output_path(
        company_id, platform, identifier, "posts", "json", timestamp
    )
    with open(posts_path, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "company_id": company_id,
                "platform": platform.value,
                "account": identifier,
                "extracted_at": timestamp.isoformat(),
                "total_posts": len(posts_data),
            },
            "posts": posts_data
        }, f, indent=2, ensure_ascii=False)

    # Save comments
    comments_path = output_manager.get_output_path(
        company_id, platform, identifier, "comments", "json", timestamp
    )
    with open(comments_path, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "company_id": company_id,
                "platform": platform.value,
                "account": identifier,
                "extracted_at": timestamp.isoformat(),
                "total_comments": len(comments_data),
            },
            "comments": comments_data
        }, f, indent=2, ensure_ascii=False)

    return {
        "posts_file": str(posts_path),
        "comments_file": str(comments_path),
        "posts_count": len(posts_data),
        "comments_count": len(comments_data)
    }


def run_extraction(
    company_ids: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    max_posts: int = 10,
    headless: bool = True,
    dry_run: bool = False,
    resume: bool = False,
    skip_existing: bool = False
) -> dict:
    """Run optimized batch extraction for companies.

    Key optimization: Reuses browser sessions per platform instead of
    creating a new browser for each account (50-70% faster).

    Args:
        company_ids: List of company IDs to extract (None = all)
        platforms: List of platforms to extract (None = all)
        max_posts: Maximum posts per account
        headless: Run browser in headless mode
        dry_run: Only show what would be extracted
        resume: Resume from last checkpoint

    Returns:
        Summary of extraction results
    """
    registry = get_registry()
    timestamp = datetime.now()
    checkpoint_mgr = CheckpointManager()

    # Convert platform strings to enums
    platform_filter = None
    if platforms:
        platform_filter = [Platform(p) for p in platforms]

    # Get extraction targets
    targets = registry.get_extraction_targets(company_ids, platform_filter)

    if not targets:
        print("No extraction targets found.")
        return {"error": "No targets"}

    # Group targets by platform for browser reuse
    by_platform: Dict[Platform, List[dict]] = defaultdict(list)
    for target in targets:
        by_platform[target['platform']].append(target)

    # Get completed extractions if resuming
    completed_keys = set()
    if resume:
        completed_keys = checkpoint_mgr.get_completed_keys()
        if completed_keys:
            print(f"\nResuming: {len(completed_keys)} accounts already completed")

    # Filter out completed targets
    total_accounts = 0
    for platform in by_platform:
        by_platform[platform] = [
            t for t in by_platform[platform]
            if f"{t['platform'].value}/{t['identifier']}" not in completed_keys
        ]
        total_accounts += len(by_platform[platform])

    if total_accounts == 0:
        print("All extractions already completed!")
        checkpoint_mgr.clear()
        return {"status": "already_complete"}

    # Show extraction plan
    print("\n" + "=" * 60)
    print("OPTIMIZED EXTRACTION PLAN")
    print("=" * 60)
    print("\nGrouped by platform (browser reuse):")

    for platform, platform_targets in sorted(by_platform.items(), key=lambda x: x[0].value):
        if not platform_targets:
            continue
        print(f"\n  {platform.value.upper()} ({len(platform_targets)} accounts):")
        for t in platform_targets:
            print(f"    - {t['company_name']}: @{t['identifier']}")

    print(f"\nTotal: {total_accounts} accounts across {len([p for p in by_platform if by_platform[p]])} platforms")
    print(f"Max posts per account: {max_posts}")
    print(f"Browser sessions needed: {len([p for p in by_platform if by_platform[p]])} (one per platform)")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN] No extraction performed.")
        return {"dry_run": True, "targets": total_accounts}

    # Initialize tracking
    progress = ProgressTracker(total_accounts)
    settings = get_settings()

    results_summary = {
        "timestamp": timestamp.isoformat(),
        "companies": {},
        "totals": {
            "accounts": 0,
            "posts": 0,
            "comments": 0,
            "errors": 0
        },
        "completed": list(completed_keys)  # Track for checkpointing
    }

    # Extract by platform (reusing browser)
    for platform, platform_targets in by_platform.items():
        if not platform_targets:
            continue

        print(f"\n{'=' * 60}")
        print(f"Platform: {platform.value.upper()} ({len(platform_targets)} accounts)")
        print("=" * 60)

        # Get platform config and create scraper once
        config = settings.get_platform_config(platform.value)
        config['headless'] = headless

        scraper: Optional[BaseScraper] = None

        try:
            # Create single scraper for all accounts on this platform
            scraper = ScraperRegistry.get(platform.value, config)

            for target in platform_targets:
                company_id = target['company_id']
                identifier = target['identifier']
                account_key = f"{platform.value}/{identifier}"

                print(f"\n  [{target['company_name']}] @{identifier}")
                print("  " + "-" * 40)

                account_start = time.time()
                results: List[ExtractionResult] = []

                try:
                    # Load existing post IDs if skip_existing is enabled
                    known_post_ids = None
                    if skip_existing:
                        known_post_ids = load_existing_post_ids(company_id, platform, identifier)
                        if known_post_ids:
                            print(f"    Skipping {len(known_post_ids)} existing posts")

                    # Extract using the shared scraper
                    for result in scraper.get_posts_with_comments(
                        identifier,
                        max_posts=max_posts,
                        known_post_ids=known_post_ids
                    ):
                        results.append(result)
                        print(f"    Post {len(results)}: {result.post.platform_id} | "
                              f"Likes: {result.post.likes:,} | "
                              f"Comments: {len(result.comments)}")

                    if results:
                        # Save results
                        save_info = save_results(
                            results, company_id, platform, identifier, timestamp
                        )

                        # Update company results
                        if company_id not in results_summary["companies"]:
                            company = registry.get_company(company_id)
                            results_summary["companies"][company_id] = {
                                "name": company.name,
                                "accounts": {}
                            }

                        results_summary["companies"][company_id]["accounts"][account_key] = save_info
                        results_summary["totals"]["posts"] += save_info["posts_count"]
                        results_summary["totals"]["comments"] += save_info["comments_count"]
                        results_summary["totals"]["accounts"] += 1

                        print(f"  Saved: {save_info['posts_count']} posts, "
                              f"{save_info['comments_count']} comments")
                    else:
                        results_summary["totals"]["errors"] += 1
                        print(f"  No results extracted")

                except Exception as e:
                    print(f"  Error: {e}")
                    results_summary["totals"]["errors"] += 1

                # Update progress
                account_duration = time.time() - account_start
                progress.account_done(account_duration)
                results_summary["completed"].append(account_key)

                # Save checkpoint after each account
                checkpoint_mgr.save(results_summary)

                print(f"  {progress.get_progress_str()}")

        except Exception as e:
            print(f"\n  Platform error: {e}")
            results_summary["totals"]["errors"] += len(platform_targets)

        finally:
            # Close scraper after all accounts on this platform
            if scraper:
                scraper.close()
                print(f"\n  Browser closed for {platform.value}")

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Companies: {len(results_summary['companies'])}")
    print(f"Accounts:  {results_summary['totals']['accounts']}")
    print(f"Posts:     {results_summary['totals']['posts']}")
    print(f"Comments:  {results_summary['totals']['comments']}")
    print(f"Errors:    {results_summary['totals']['errors']}")

    total_time = time.time() - progress.start_time
    print(f"Total time: {str(timedelta(seconds=int(total_time)))}")
    print("=" * 60)

    # Save final summary
    output_manager = get_output_manager()
    summary_path = output_manager.base_dir / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_extraction_summary.json"

    # Remove checkpoint tracking from final output
    final_summary = {k: v for k, v in results_summary.items() if k != 'completed'}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved: {summary_path}")

    # Clear checkpoint on successful completion
    checkpoint_mgr.clear()

    return results_summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimized batch extraction for multiple companies"
    )
    parser.add_argument(
        "--companies", "-c",
        nargs="+",
        help="Company IDs to extract (default: all)"
    )
    parser.add_argument(
        "--platforms", "-p",
        nargs="+",
        choices=["facebook", "instagram", "twitter", "linkedin", "google"],
        help="Platforms to extract (default: all)"
    )
    parser.add_argument(
        "--max-posts", "-m",
        type=int,
        default=10,
        help="Maximum posts per account (default: 10)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show extraction plan without running"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--list-companies",
        action="store_true",
        help="List available companies and exit"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-extract all posts even if already extracted (default: skip existing)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # List companies mode
    if args.list_companies:
        registry = get_registry()
        print("\nAvailable Companies:")
        print("-" * 60)
        for company in registry.get_all_companies():
            platforms = [p.value for p in company.get_platforms()]
            print(f"  {company.id}: {company.name}")
            print(f"    Platforms: {', '.join(platforms)}")
            print(f"    Accounts: {len(company.get_enabled_accounts())}")
        return

    # Run extraction
    headless = args.headless and not args.no_headless

    run_extraction(
        company_ids=args.companies,
        platforms=args.platforms,
        max_posts=args.max_posts,
        headless=headless,
        dry_run=args.dry_run,
        resume=args.resume,
        skip_existing=not args.no_skip_existing
    )


if __name__ == "__main__":
    main()
