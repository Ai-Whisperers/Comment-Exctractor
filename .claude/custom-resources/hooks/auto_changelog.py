#!/usr/bin/env python3
"""
Auto-Changelog Generation Hook

Automatically generates and updates CHANGELOG.md entries based on git commits.
Triggers on git commit operations to maintain up-to-date changelog.

Hook Type: PostToolUse
Trigger: Bash(git commit*)
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class ChangelogGenerator:
    """Generate changelog entries from git commits."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.changelog_path = repo_root / "CHANGELOG.md"

    def get_latest_commit(self) -> Optional[Dict[str, str]]:
        """Get the most recent commit information."""
        try:
            # Get commit hash
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                text=True
            ).strip()

            # Get commit message
            commit_msg = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%B"],
                cwd=self.repo_root,
                text=True
            ).strip()

            # Get commit author and date
            commit_info = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%an|%ae|%aI"],
                cwd=self.repo_root,
                text=True
            ).strip().split("|")

            # Get changed files
            changed_files = subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=self.repo_root,
                text=True
            ).strip().split("\n")

            return {
                "hash": commit_hash[:8],
                "message": commit_msg,
                "author": commit_info[0],
                "email": commit_info[1],
                "date": commit_info[2],
                "files": [f for f in changed_files if f]
            }
        except subprocess.CalledProcessError:
            return None

    def parse_conventional_commit(self, message: str) -> Dict[str, str]:
        """Parse conventional commit format (type: description)."""
        lines = message.split("\n")
        first_line = lines[0]

        # Extract type and scope
        if ":" in first_line:
            type_part, description = first_line.split(":", 1)
            type_part = type_part.strip()
            description = description.strip()

            # Check for scope
            if "(" in type_part and ")" in type_part:
                commit_type = type_part.split("(")[0]
                scope = type_part.split("(")[1].split(")")[0]
            else:
                commit_type = type_part
                scope = None
        else:
            commit_type = "chore"
            description = first_line
            scope = None

        # Extract body and footer
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        return {
            "type": commit_type,
            "scope": scope,
            "description": description,
            "body": body
        }

    def categorize_commit(self, commit_type: str) -> str:
        """Categorize commit type for changelog sections."""
        categories = {
            "feat": "Features",
            "feature": "Features",
            "fix": "Bug Fixes",
            "bugfix": "Bug Fixes",
            "docs": "Documentation",
            "doc": "Documentation",
            "style": "Style Changes",
            "refactor": "Refactoring",
            "perf": "Performance",
            "test": "Tests",
            "chore": "Maintenance",
            "ci": "CI/CD",
            "build": "Build System",
            "revert": "Reverts"
        }
        return categories.get(commit_type.lower(), "Other")

    def format_changelog_entry(self, commit: Dict[str, str]) -> str:
        """Format a commit as a changelog entry."""
        parsed = self.parse_conventional_commit(commit["message"])
        category = self.categorize_commit(parsed["type"])

        # Format entry
        scope_part = f"**{parsed['scope']}**: " if parsed["scope"] else ""
        entry = f"- {scope_part}{parsed['description']} ({commit['hash']})"

        # Add body if present and relevant
        if parsed["body"] and not parsed["body"].startswith("Generated with"):
            # Only include first 2 lines of body for brevity
            body_lines = [line for line in parsed["body"].split("\n") if line.strip()][:2]
            if body_lines:
                entry += "\n  - " + "\n  - ".join(body_lines)

        return entry, category

    def read_existing_changelog(self) -> str:
        """Read existing changelog content."""
        if self.changelog_path.exists():
            return self.changelog_path.read_text()
        return self._create_initial_changelog()

    def _create_initial_changelog(self) -> str:
        """Create initial changelog template."""
        return """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""

    def update_changelog(self, commit: Dict[str, str]) -> bool:
        """Update changelog with new commit entry."""
        try:
            content = self.read_existing_changelog()
            entry, category = self.format_changelog_entry(commit)

            # Get current date
            date = datetime.fromisoformat(commit["date"]).strftime("%Y-%m-%d")

            # Check if there's an unreleased section
            if "## [Unreleased]" not in content:
                # Add unreleased section after header
                header_end = content.find("\n##")
                if header_end == -1:
                    header_end = len(content)

                unreleased_section = f"\n## [Unreleased]\n\n### {category}\n\n{entry}\n"
                content = content[:header_end] + unreleased_section + content[header_end:]
            else:
                # Find unreleased section
                unreleased_start = content.find("## [Unreleased]")
                next_section = content.find("\n## [", unreleased_start + 1)
                if next_section == -1:
                    next_section = len(content)

                unreleased_content = content[unreleased_start:next_section]

                # Check if category exists
                if f"### {category}" in unreleased_content:
                    # Add to existing category
                    category_pos = unreleased_content.find(f"### {category}")
                    next_category = unreleased_content.find("\n###", category_pos + 1)
                    if next_category == -1:
                        next_category = len(unreleased_content)

                    # Insert after category header
                    insert_pos = unreleased_content.find("\n", category_pos) + 1
                    unreleased_content = (
                        unreleased_content[:insert_pos] +
                        entry + "\n" +
                        unreleased_content[insert_pos:]
                    )
                else:
                    # Add new category
                    insert_pos = unreleased_content.find("\n", unreleased_content.find("## [Unreleased]")) + 1
                    unreleased_content = (
                        unreleased_content[:insert_pos] +
                        f"\n### {category}\n\n{entry}\n" +
                        unreleased_content[insert_pos:]
                    )

                # Replace in content
                content = content[:unreleased_start] + unreleased_content + content[next_section:]

            # Write updated changelog
            self.changelog_path.write_text(content)
            return True

        except Exception as e:
            print(f"Error updating changelog: {e}", file=sys.stderr)
            return False


def main():
    """Main hook execution."""
    # Get repository root
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True
        ).strip()
        repo_root = Path(repo_root)
    except subprocess.CalledProcessError:
        print("Not in a git repository", file=sys.stderr)
        return 1

    # Initialize generator
    generator = ChangelogGenerator(repo_root)

    # Get latest commit
    commit = generator.get_latest_commit()
    if not commit:
        print("No commits found", file=sys.stderr)
        return 1

    # Update changelog
    if generator.update_changelog(commit):
        print(f"Changelog updated with commit {commit['hash']}")
        print(f"  Type: {generator.parse_conventional_commit(commit['message'])['type']}")
        print(f"  Description: {generator.parse_conventional_commit(commit['message'])['description']}")
        print(f"\nRun 'git add CHANGELOG.md' to stage the changes")
        return 0
    else:
        print("Failed to update changelog", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
