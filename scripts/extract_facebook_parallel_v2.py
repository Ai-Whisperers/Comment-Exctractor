#!/usr/bin/env python3
"""
Parallel Facebook extraction - launches all companies simultaneously using Popen.

Usage:
    python scripts/extract_facebook_parallel_v2.py --max-posts 100 --no-headless
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.company_registry import get_registry
from src.core.models import Platform


def main():
    parser = argparse.ArgumentParser(
        description="Run Facebook extraction for all companies in parallel"
    )
    parser.add_argument(
        "--max-posts", "-m",
        type=int,
        default=100,
        help="Maximum posts per company (default: 100)"
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

    # Get all companies that have Facebook accounts
    registry = get_registry()
    companies_with_facebook = []

    for company in registry.get_all_companies():
        if company.get_accounts_by_platform(Platform.FACEBOOK):
            companies_with_facebook.append(company.id)

    if not companies_with_facebook:
        print("No companies with Facebook accounts found.")
        return

    print("=" * 60)
    print("PARALLEL FACEBOOK EXTRACTION (v2 - Popen)")
    print("=" * 60)
    print(f"\nCompanies: {', '.join(companies_with_facebook)}")
    print(f"Max posts per company: {args.max_posts}")
    print(f"Headless: {headless}")
    print("=" * 60)

    script_path = Path(__file__).parent / "extract_companies.py"
    start_time = datetime.now()

    # Base profile directory
    base_profile_dir = Path(__file__).parent.parent / "data" / ".cache" / "browser_profiles"

    # Launch all processes simultaneously
    processes = {}
    for company_id in companies_with_facebook:
        cmd = [
            sys.executable,
            str(script_path),
            "--companies", company_id,
            "--platforms", "facebook",
            "--max-posts", str(args.max_posts),
        ]

        if headless:
            cmd.append("--headless")
        else:
            cmd.append("--no-headless")

        print(f"\n[{company_id.upper()}] Launching...")

        # Create company-specific environment with unique browser profile
        env = os.environ.copy()
        company_profile = base_profile_dir / f"facebook_profile_{company_id}"
        env["BROWSER_PROFILE_OVERRIDE"] = str(company_profile)

        # Launch without capturing output so we can see it in real-time
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            env=env
        )
        processes[company_id] = proc

        # Small delay between launches to avoid resource contention
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print(f"Launched {len(processes)} parallel extractions")
    print("Waiting for completion...")
    print("=" * 60)

    # Monitor processes
    completed = set()
    while len(completed) < len(processes):
        for company_id, proc in processes.items():
            if company_id in completed:
                continue

            # Check if process finished
            retcode = proc.poll()
            if retcode is not None:
                completed.add(company_id)
                status = "SUCCESS" if retcode == 0 else f"FAILED (code {retcode})"
                print(f"\n[{company_id.upper()}] {status}")

                # Read any remaining output
                if proc.stdout:
                    output = proc.stdout.read()
                    if output:
                        # Show last few lines
                        lines = output.strip().split('\n')
                        for line in lines[-10:]:
                            if line.strip():
                                print(f"  {line}")

        if len(completed) < len(processes):
            time.sleep(5)

    # Summary
    elapsed = datetime.now() - start_time

    print("\n" + "=" * 60)
    print("FACEBOOK EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Companies: {len(processes)}")
    print(f"Total time: {elapsed}")
    print("=" * 60)

    # Check for new files
    print("\nChecking extracted files...")
    from src.utils.company_output import get_output_manager
    output_manager = get_output_manager()

    for company_id in companies_with_facebook:
        try:
            exports = output_manager.list_company_exports(company_id)
            if 'facebook' in exports:
                for account, files in exports['facebook'].items():
                    recent_posts = [f for f in files if 'posts' in f]
                    if recent_posts:
                        print(f"  {company_id}/{account}: {len(recent_posts)} export(s)")
        except Exception as e:
            print(f"  {company_id}: Error checking exports - {e}")


if __name__ == "__main__":
    main()
