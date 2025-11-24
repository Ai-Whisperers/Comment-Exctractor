#!/usr/bin/env python3
"""
Parallel extraction script - runs multiple platforms simultaneously.

Each platform runs in its own process with its own browser.

Usage:
    # Run all platforms in parallel (4 browsers)
    python scripts/extract_parallel.py

    # Run specific platforms in parallel
    python scripts/extract_parallel.py --platforms instagram facebook

    # Limit concurrent browsers
    python scripts/extract_parallel.py --workers 2
"""

import argparse
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.company_registry import get_registry
from src.core.models import Platform


def run_platform_extraction(platform: str, max_posts: int, headless: bool) -> dict:
    """Run extraction for a single platform in a subprocess."""
    script_path = Path(__file__).parent / "extract_companies.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--platforms", platform,
        "--max-posts", str(max_posts),
    ]

    if headless:
        cmd.append("--headless")
    else:
        cmd.append("--no-headless")

    print(f"\n[{platform.upper()}] Starting extraction...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout per platform
        )

        success = result.returncode == 0

        return {
            "platform": platform,
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",  # Last 2000 chars
            "stderr": result.stderr[-1000:] if result.stderr else ""
        }

    except subprocess.TimeoutExpired:
        return {
            "platform": platform,
            "success": False,
            "error": "Timeout after 2 hours"
        }
    except Exception as e:
        return {
            "platform": platform,
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Run platform extractions in parallel"
    )
    parser.add_argument(
        "--platforms", "-p",
        nargs="+",
        choices=["facebook", "instagram", "twitter", "linkedin", "google"],
        help="Platforms to extract (default: all configured)"
    )
    parser.add_argument(
        "--max-posts", "-m",
        type=int,
        default=1000,
        help="Maximum posts per account (default: 1000)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Maximum concurrent browsers (default: 4)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browsers in headless mode"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser windows"
    )

    args = parser.parse_args()
    headless = args.headless and not args.no_headless

    # Get platforms to run
    registry = get_registry()

    if args.platforms:
        platforms = args.platforms
    else:
        # Get all unique platforms from companies
        all_platforms = set()
        for company in registry.get_all_companies():
            for p in company.get_platforms():
                all_platforms.add(p.value)
        platforms = list(all_platforms)

    print("=" * 60)
    print("PARALLEL EXTRACTION")
    print("=" * 60)
    print(f"\nPlatforms: {', '.join(platforms)}")
    print(f"Max posts per account: {args.max_posts}")
    print(f"Concurrent workers: {min(args.workers, len(platforms))}")
    print(f"Headless: {headless}")
    print("=" * 60)

    start_time = datetime.now()
    results = []

    # Run platforms in parallel
    with ProcessPoolExecutor(max_workers=min(args.workers, len(platforms))) as executor:
        futures = {
            executor.submit(run_platform_extraction, platform, args.max_posts, headless): platform
            for platform in platforms
        }

        for future in as_completed(futures):
            platform = futures[future]
            try:
                result = future.result()
                results.append(result)

                status = "SUCCESS" if result.get("success") else "FAILED"
                print(f"\n[{platform.upper()}] {status}")

                if not result.get("success"):
                    error = result.get("error", result.get("stderr", "Unknown error"))
                    print(f"  Error: {error[:200]}")

            except Exception as e:
                print(f"\n[{platform.upper()}] EXCEPTION: {e}")
                results.append({
                    "platform": platform,
                    "success": False,
                    "error": str(e)
                })

    # Summary
    elapsed = datetime.now() - start_time
    successful = sum(1 for r in results if r.get("success"))

    print("\n" + "=" * 60)
    print("PARALLEL EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Platforms: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {elapsed}")
    print("=" * 60)

    # Show failures
    failures = [r for r in results if not r.get("success")]
    if failures:
        print("\nFailed platforms:")
        for f in failures:
            print(f"  - {f['platform']}: {f.get('error', 'Unknown')[:100]}")


if __name__ == "__main__":
    main()
