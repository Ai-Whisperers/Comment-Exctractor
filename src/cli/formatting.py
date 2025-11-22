"""CLI formatting utilities with colors and progress display."""

import sys
import time
from typing import Optional, Dict, Any, List
from enum import Enum


class Color(Enum):
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


# Check if colors are supported
def supports_color() -> bool:
    """Check if the terminal supports colors."""
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    # Windows cmd and PowerShell support ANSI colors in Windows 10+
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences on Windows
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True


_colors_enabled = supports_color()


def set_colors_enabled(enabled: bool):
    """Enable or disable colored output."""
    global _colors_enabled
    _colors_enabled = enabled


def colorize(text: str, color: Color, bold: bool = False) -> str:
    """
    Apply color to text.

    Args:
        text: Text to colorize
        color: Color to apply
        bold: Make text bold

    Returns:
        Colored text string
    """
    if not _colors_enabled:
        return text

    prefix = ""
    if bold:
        prefix = Color.BOLD.value

    return f"{prefix}{color.value}{text}{Color.RESET.value}"


def success(text: str) -> str:
    """Format text as success (green)."""
    return colorize(text, Color.GREEN)


def error(text: str) -> str:
    """Format text as error (red)."""
    return colorize(text, Color.RED, bold=True)


def warning(text: str) -> str:
    """Format text as warning (yellow)."""
    return colorize(text, Color.YELLOW)


def info(text: str) -> str:
    """Format text as info (blue)."""
    return colorize(text, Color.BLUE)


def highlight(text: str) -> str:
    """Format text as highlighted (cyan, bold)."""
    return colorize(text, Color.CYAN, bold=True)


def dim(text: str) -> str:
    """Format text as dimmed."""
    if not _colors_enabled:
        return text
    return f"{Color.DIM.value}{text}{Color.RESET.value}"


class ProgressBar:
    """Simple progress bar for CLI operations."""

    def __init__(
        self,
        total: int,
        description: str = "",
        width: int = 40,
        show_count: bool = True,
        show_percent: bool = True,
        show_eta: bool = True
    ):
        """
        Initialize progress bar.

        Args:
            total: Total number of items
            description: Description to show
            width: Bar width in characters
            show_count: Show count (e.g., "5/100")
            show_percent: Show percentage
            show_eta: Show estimated time remaining
        """
        self.total = total
        self.description = description
        self.width = width
        self.show_count = show_count
        self.show_percent = show_percent
        self.show_eta = show_eta

        self.current = 0
        self.start_time = time.time()
        self._last_update = 0

    def update(self, n: int = 1):
        """Update progress by n items."""
        self.current += n
        self._render()

    def set_progress(self, n: int):
        """Set progress to specific value."""
        self.current = n
        self._render()

    def _render(self):
        """Render progress bar to terminal."""
        # Only update every 100ms to reduce flicker
        now = time.time()
        if now - self._last_update < 0.1 and self.current < self.total:
            return
        self._last_update = now

        # Calculate progress
        if self.total > 0:
            progress = self.current / self.total
        else:
            progress = 0

        # Build bar
        filled = int(self.width * progress)
        bar = "=" * filled + ">" + " " * (self.width - filled - 1)
        bar = bar[:self.width]  # Ensure exact width

        # Build status parts
        parts = []

        if self.description:
            parts.append(self.description)

        # Progress bar
        bar_color = Color.GREEN if progress >= 1 else Color.CYAN
        colored_bar = colorize(f"[{bar}]", bar_color)
        parts.append(colored_bar)

        # Count
        if self.show_count:
            count_str = f"{self.current}/{self.total}"
            parts.append(count_str)

        # Percentage
        if self.show_percent:
            percent_str = f"{progress * 100:.1f}%"
            parts.append(percent_str)

        # ETA
        if self.show_eta and self.current > 0 and self.current < self.total:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate
            eta_str = f"ETA: {_format_duration(remaining)}"
            parts.append(dim(eta_str))

        # Print
        line = " ".join(parts)
        sys.stdout.write(f"\r{line}")
        sys.stdout.flush()

        # New line when complete
        if self.current >= self.total:
            sys.stdout.write("\n")

    def finish(self):
        """Finish progress bar."""
        self.current = self.total
        self._render()


class Spinner:
    """Simple spinner for indeterminate progress."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    SIMPLE_FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, message: str = "Working"):
        """Initialize spinner."""
        self.message = message
        self.frame_idx = 0
        # Use simple frames on Windows if Unicode doesn't work
        self.frames = self.SIMPLE_FRAMES if sys.platform == 'win32' else self.FRAMES

    def spin(self):
        """Update spinner frame."""
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)

        spinner_colored = colorize(frame, Color.CYAN)
        sys.stdout.write(f"\r{spinner_colored} {self.message}")
        sys.stdout.flush()

    def finish(self, message: Optional[str] = None):
        """Finish spinner with completion message."""
        check = colorize("OK", Color.GREEN)
        msg = message or self.message
        sys.stdout.write(f"\r{check} {msg}\n")
        sys.stdout.flush()

    def fail(self, message: Optional[str] = None):
        """Finish spinner with failure message."""
        x = colorize("FAIL", Color.RED)
        msg = message or self.message
        sys.stdout.write(f"\r{x} {msg}\n")
        sys.stdout.flush()


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def print_header(text: str, char: str = "=", width: int = 60):
    """Print a header with decorations."""
    line = char * width
    print(f"\n{colorize(line, Color.CYAN)}")
    print(colorize(text, Color.WHITE, bold=True))
    print(f"{colorize(line, Color.CYAN)}")


def print_result_box(title: str, content: Dict[str, Any], width: int = 50):
    """Print a formatted result box with colors."""
    line = "=" * width

    print(f"\n{colorize(line, Color.CYAN)}")
    print(colorize(title, Color.WHITE, bold=True))
    print(colorize(line, Color.CYAN))

    for key, value in content.items():
        if key == "":  # Spacer
            print()
        else:
            key_colored = colorize(f"{key}:", Color.BLUE)
            print(f"{key_colored} {value}")

    print(f"{colorize(line, Color.CYAN)}\n")


def print_table(headers: List[str], rows: List[List[Any]], min_widths: Optional[List[int]] = None):
    """Print a formatted table."""
    # Calculate column widths
    num_cols = len(headers)
    widths = [len(str(h)) for h in headers]

    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Apply minimum widths
    if min_widths:
        for i, min_w in enumerate(min_widths):
            widths[i] = max(widths[i], min_w)

    # Print header
    header_line = " | ".join(
        colorize(str(h).ljust(widths[i]), Color.CYAN, bold=True)
        for i, h in enumerate(headers)
    )
    print(header_line)

    # Print separator
    sep = "-+-".join("-" * w for w in widths)
    print(colorize(sep, Color.DIM))

    # Print rows
    for row in rows:
        row_line = " | ".join(
            str(cell).ljust(widths[i])
            for i, cell in enumerate(row)
        )
        print(row_line)


def print_status(status: str, message: str):
    """Print a status message with colored indicator."""
    status_lower = status.lower()

    if status_lower in ("ok", "success", "done", "pass"):
        indicator = colorize(f"[{status.upper()}]", Color.GREEN)
    elif status_lower in ("fail", "error", "failed"):
        indicator = colorize(f"[{status.upper()}]", Color.RED)
    elif status_lower in ("warn", "warning", "skip", "skipped"):
        indicator = colorize(f"[{status.upper()}]", Color.YELLOW)
    else:
        indicator = colorize(f"[{status.upper()}]", Color.BLUE)

    print(f"{indicator} {message}")


def print_list(items: List[str], bullet: str = "-", color: Color = Color.BLUE):
    """Print a bulleted list."""
    bullet_colored = colorize(bullet, color)
    for item in items:
        print(f"  {bullet_colored} {item}")


# Convenience exports
__all__ = [
    'Color',
    'supports_color',
    'set_colors_enabled',
    'colorize',
    'success',
    'error',
    'warning',
    'info',
    'highlight',
    'dim',
    'ProgressBar',
    'Spinner',
    'print_header',
    'print_result_box',
    'print_table',
    'print_status',
    'print_list',
]
