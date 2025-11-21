#!/usr/bin/env python3
"""
Context Bloat Detector Hook

Monitors open files and token usage, automatically suggests /compact when needed.
Runs after Read operations to track context growth.

Usage: Automatically triggered by Claude Code PostToolUse hook
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# Thresholds
MAX_FILES_WARNING = 3  # 3-file rule
TOKEN_WARNING_THRESHOLD = 35000  # 17.5% of 200K limit
TOKEN_DANGER_THRESHOLD = 50000   # 25% of 200K limit

# Track state across hook invocations
STATE_FILE = Path.home() / ".claude" / "context_state.txt"


def count_open_files() -> int:
    """
    Estimate number of open files based on recent file operations.

    Note: This is a heuristic. Actual open file count would require
    integration with Claude Code's internal state.
    """
    # In a real implementation, this would be provided by Claude Code
    # For now, we'll use a placeholder
    return 0


def estimate_token_usage() -> int:
    """
    Estimate current token usage.

    Note: Actual token usage would come from Claude Code's context manager.
    """
    # Placeholder - would be provided by Claude Code
    return 0


def detect_context_bloat(file_count: int, token_count: int) -> Dict[str, any]:
    """
    Analyze context usage and detect bloat.

    Returns:
        dict: Analysis results with recommendations
    """
    issues = []
    recommendations = []
    severity = "ok"

    # Check file count (3-file rule)
    if file_count > MAX_FILES_WARNING:
        issues.append(f"{file_count} files open (3-file rule: max 3)")
        recommendations.append("Close extra files - keep only current implementation, test, and reference")
        severity = "warning"

    # Check token usage
    token_percentage = (token_count / 200000) * 100

    if token_count > TOKEN_DANGER_THRESHOLD:
        issues.append(f"Token usage: {token_count:,} ({token_percentage:.1f}% of limit)")
        recommendations.append("RUN /compact IMMEDIATELY - high token usage")
        severity = "danger"
    elif token_count > TOKEN_WARNING_THRESHOLD:
        issues.append(f"Token usage: {token_count:,} ({token_percentage:.1f}% of limit)")
        recommendations.append("Consider running /compact to reduce context")
        if severity != "danger":
            severity = "warning"

    return {
        "severity": severity,
        "file_count": file_count,
        "token_count": token_count,
        "token_percentage": token_percentage,
        "issues": issues,
        "recommendations": recommendations
    }


def format_output(analysis: Dict) -> str:
    """
    Format analysis results for display.
    """
    if analysis["severity"] == "ok":
        return ""  # No output if everything is OK

    # Color codes
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"

    color = YELLOW if analysis["severity"] == "warning" else RED

    output = []
    output.append(f"\n{color}Context Bloat Detected:{NC}")
    output.append("")

    for issue in analysis["issues"]:
        output.append(f"  - {issue}")

    output.append("")
    output.append("Recommendations:")
    for rec in analysis["recommendations"]:
        output.append(f"  - {rec}")

    output.append("")

    return "\n".join(output)


def main():
    """
    Main hook execution.
    """
    # Get file count and token usage
    # In production, these would come from Claude Code's context
    file_count = count_open_files()
    token_count = estimate_token_usage()

    # Detect bloat
    analysis = detect_context_bloat(file_count, token_count)

    # Format and print output
    output = format_output(analysis)
    if output:
        print(output, file=sys.stderr)

    # Always exit 0 (don't block the Read operation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
