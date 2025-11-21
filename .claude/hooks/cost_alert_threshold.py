#!/usr/bin/env python3
"""
Cost Alert Threshold Hook

Monitors daily spending and alerts when budget thresholds are exceeded.
Runs after tool use to track cumulative costs.

Configuration via environment variables in settings.local.json:
- CLAUDE_DAILY_BUDGET: Daily budget in dollars (default: $1.50)
- CLAUDE_ALERT_THRESHOLD: Alert percentage (default: 80)

Usage: Automatically triggered by Claude Code PostToolUse hook
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration
DAILY_BUDGET = float(os.getenv("CLAUDE_DAILY_BUDGET", "1.50"))
ALERT_THRESHOLD = int(os.getenv("CLAUDE_ALERT_THRESHOLD", "80"))

# Cost tracking file
COST_TRACKING_FILE = Path.home() / ".claude" / "cost_tracking.json"

# Model costs (per 1M tokens)
# Approximate costs - actual costs may vary
COSTS = {
    "input": {
        "haiku": 0.25,     # $0.25 per 1M input tokens
        "sonnet": 3.00,    # $3.00 per 1M input tokens
        "opus": 15.00      # $15.00 per 1M input tokens
    },
    "output": {
        "haiku": 1.25,     # $1.25 per 1M output tokens
        "sonnet": 15.00,   # $15.00 per 1M output tokens
        "opus": 75.00      # $75.00 per 1M output tokens
    }
}


def load_cost_tracking() -> Dict:
    """
    Load cost tracking data from file.
    """
    if not COST_TRACKING_FILE.exists():
        return {
            "daily_costs": {},
            "weekly_costs": {},
            "monthly_costs": {},
            "sessions": []
        }

    try:
        with open(COST_TRACKING_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "daily_costs": {},
            "weekly_costs": {},
            "monthly_costs": {},
            "sessions": []
        }


def save_cost_tracking(data: Dict):
    """
    Save cost tracking data to file.
    """
    COST_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(COST_TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def estimate_operation_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate cost for a single operation.

    Args:
        model: Model name (haiku, sonnet, opus)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        float: Estimated cost in dollars
    """
    model_key = "haiku"  # Default
    if "sonnet" in model.lower():
        model_key = "sonnet"
    elif "opus" in model.lower():
        model_key = "opus"

    input_cost = (input_tokens / 1_000_000) * COSTS["input"][model_key]
    output_cost = (output_tokens / 1_000_000) * COSTS["output"][model_key]

    return input_cost + output_cost


def get_daily_spend(tracking_data: Dict) -> Tuple[float, List[Dict]]:
    """
    Get today's spending.

    Returns:
        tuple: (total_spend, cost_breakdown)
    """
    today = str(date.today())
    daily_costs = tracking_data.get("daily_costs", {})

    if today not in daily_costs:
        return 0.0, []

    today_data = daily_costs[today]
    total = today_data.get("total", 0.0)
    breakdown = today_data.get("breakdown", [])

    return total, breakdown


def update_daily_spend(
    tracking_data: Dict,
    operation: str,
    cost: float,
    model: str
):
    """
    Update daily spending with new operation.
    """
    today = str(date.today())

    if "daily_costs" not in tracking_data:
        tracking_data["daily_costs"] = {}

    if today not in tracking_data["daily_costs"]:
        tracking_data["daily_costs"][today] = {
            "total": 0.0,
            "breakdown": []
        }

    today_data = tracking_data["daily_costs"][today]
    today_data["total"] += cost
    today_data["breakdown"].append({
        "operation": operation,
        "cost": cost,
        "model": model,
        "timestamp": datetime.now().isoformat()
    })


def check_budget_alert(current_spend: float) -> Dict:
    """
    Check if budget threshold exceeded.

    Returns:
        dict: Alert information
    """
    percentage = (current_spend / DAILY_BUDGET) * 100
    remaining = DAILY_BUDGET - current_spend

    alert_level = "ok"
    if percentage >= 100:
        alert_level = "exceeded"
    elif percentage >= ALERT_THRESHOLD:
        alert_level = "warning"

    return {
        "alert_level": alert_level,
        "percentage": percentage,
        "current_spend": current_spend,
        "daily_budget": DAILY_BUDGET,
        "remaining": remaining
    }


def get_top_cost_drivers(breakdown: List[Dict], top_n: int = 3) -> List[Dict]:
    """
    Get top N cost drivers.
    """
    # Sort by cost descending
    sorted_breakdown = sorted(breakdown, key=lambda x: x["cost"], reverse=True)
    return sorted_breakdown[:top_n]


def suggest_optimizations(alert: Dict, breakdown: List[Dict]) -> List[str]:
    """
    Suggest cost optimization strategies.
    """
    suggestions = []

    # Analyze model usage
    sonnet_cost = sum(op["cost"] for op in breakdown if "sonnet" in op["model"].lower())
    haiku_cost = sum(op["cost"] for op in breakdown if "haiku" in op["model"].lower())

    sonnet_percentage = (sonnet_cost / alert["current_spend"] * 100) if alert["current_spend"] > 0 else 0

    if sonnet_percentage > 30:
        suggestions.append(
            f"High Sonnet usage ({sonnet_percentage:.0f}%). Use Haiku for simple tasks (tests, edits, file reads)"
        )

    if alert["percentage"] >= 80:
        suggestions.append("Run /compact to reduce context size and token usage")
        suggestions.append("Use batch operations: 'Read A, B, C' instead of sequential reads")
        suggestions.append("Follow strict 3-file rule to minimize token usage")

    if len(breakdown) > 20:
        suggestions.append("Consider breaking work into multiple focused sessions")

    return suggestions


def format_alert(alert: Dict, breakdown: List[Dict]) -> str:
    """
    Format cost alert for display.
    """
    if alert["alert_level"] == "ok":
        return ""  # No alert needed

    # Color codes
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"

    color = YELLOW if alert["alert_level"] == "warning" else RED

    output = []
    output.append(f"\n{color}Cost Alert:{NC}")
    output.append("")
    output.append(f"  Daily spending: ${alert['current_spend']:.2f} / ${alert['daily_budget']:.2f} ({alert['percentage']:.0f}%)")
    output.append(f"  Remaining: ${alert['remaining']:.2f}")
    output.append("")

    # Top cost drivers
    top_drivers = get_top_cost_drivers(breakdown, top_n=3)
    if top_drivers:
        output.append("  Top cost drivers:")
        for driver in top_drivers:
            output.append(f"    - {driver['operation']}: ${driver['cost']:.4f} ({driver['model']})")
        output.append("")

    # Suggestions
    suggestions = suggest_optimizations(alert, breakdown)
    if suggestions:
        output.append("  Suggestions:")
        for suggestion in suggestions:
            output.append(f"    - {suggestion}")
        output.append("")

    return "\n".join(output)


def main():
    """
    Main hook execution.
    """
    # Load tracking data
    tracking_data = load_cost_tracking()

    # Get current daily spend
    current_spend, breakdown = get_daily_spend(tracking_data)

    # Check for alerts
    alert = check_budget_alert(current_spend)

    # Format and print alert
    alert_message = format_alert(alert, breakdown)
    if alert_message:
        print(alert_message, file=sys.stderr)

    # Always exit 0 (don't block operations)
    return 0


if __name__ == "__main__":
    sys.exit(main())
