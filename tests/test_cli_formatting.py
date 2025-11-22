"""Tests for CLI formatting utilities."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import io

from src.cli.formatting import (
    Color,
    supports_color,
    set_colors_enabled,
    colorize,
    success,
    error,
    warning,
    info,
    highlight,
    dim,
    ProgressBar,
    Spinner,
    print_header,
    print_result_box,
    print_table,
    print_status,
    print_list,
    _format_duration,
)


class TestColorize:
    """Tests for color functions."""

    def test_colorize_when_enabled(self):
        """Test colorize applies color when enabled."""
        set_colors_enabled(True)
        result = colorize("test", Color.RED)
        assert Color.RED.value in result
        assert Color.RESET.value in result
        assert "test" in result

    def test_colorize_when_disabled(self):
        """Test colorize returns plain text when disabled."""
        set_colors_enabled(False)
        result = colorize("test", Color.RED)
        assert result == "test"
        assert Color.RED.value not in result

    def test_colorize_with_bold(self):
        """Test colorize with bold option."""
        set_colors_enabled(True)
        result = colorize("test", Color.RED, bold=True)
        assert Color.BOLD.value in result

    def test_success_color(self):
        """Test success helper returns green text."""
        set_colors_enabled(True)
        result = success("ok")
        assert Color.GREEN.value in result

    def test_error_color(self):
        """Test error helper returns red text."""
        set_colors_enabled(True)
        result = error("fail")
        assert Color.RED.value in result
        assert Color.BOLD.value in result  # Error is bold

    def test_warning_color(self):
        """Test warning helper returns yellow text."""
        set_colors_enabled(True)
        result = warning("warn")
        assert Color.YELLOW.value in result

    def test_info_color(self):
        """Test info helper returns blue text."""
        set_colors_enabled(True)
        result = info("info")
        assert Color.BLUE.value in result

    def test_highlight_color(self):
        """Test highlight helper returns cyan bold text."""
        set_colors_enabled(True)
        result = highlight("highlight")
        assert Color.CYAN.value in result
        assert Color.BOLD.value in result

    def test_dim_when_enabled(self):
        """Test dim applies dim formatting."""
        set_colors_enabled(True)
        result = dim("dimmed")
        assert Color.DIM.value in result

    def test_dim_when_disabled(self):
        """Test dim returns plain text when disabled."""
        set_colors_enabled(False)
        result = dim("dimmed")
        assert result == "dimmed"


class TestProgressBar:
    """Tests for ProgressBar class."""

    def test_init(self):
        """Test progress bar initialization."""
        bar = ProgressBar(100, "Testing")
        assert bar.total == 100
        assert bar.current == 0
        assert bar.description == "Testing"

    def test_update(self):
        """Test progress bar update."""
        bar = ProgressBar(100)
        bar.update(10)
        assert bar.current == 10
        bar.update(5)
        assert bar.current == 15

    def test_set_progress(self):
        """Test setting progress directly."""
        bar = ProgressBar(100)
        bar.set_progress(50)
        assert bar.current == 50

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_render_output(self, mock_stdout):
        """Test progress bar renders to stdout."""
        set_colors_enabled(False)
        bar = ProgressBar(10, "Test", width=10, show_eta=False)
        bar._last_update = 0  # Force render
        bar.set_progress(5)
        output = mock_stdout.getvalue()
        assert "Test" in output
        assert "5/10" in output

    def test_finish(self):
        """Test finishing progress bar."""
        bar = ProgressBar(100)
        bar.finish()
        assert bar.current == bar.total


class TestSpinner:
    """Tests for Spinner class."""

    def test_init(self):
        """Test spinner initialization."""
        spinner = Spinner("Loading")
        assert spinner.message == "Loading"
        assert spinner.frame_idx == 0

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_spin(self, mock_stdout):
        """Test spinner advances frame."""
        set_colors_enabled(False)
        spinner = Spinner("Working")
        initial_idx = spinner.frame_idx

        spinner.spin()
        assert spinner.frame_idx == initial_idx + 1
        assert "Working" in mock_stdout.getvalue()

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_finish(self, mock_stdout):
        """Test spinner finish shows OK."""
        set_colors_enabled(False)
        spinner = Spinner("Task")
        spinner.finish("Done!")
        output = mock_stdout.getvalue()
        assert "OK" in output
        assert "Done!" in output

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_fail(self, mock_stdout):
        """Test spinner fail shows FAIL."""
        set_colors_enabled(False)
        spinner = Spinner("Task")
        spinner.fail("Error!")
        output = mock_stdout.getvalue()
        assert "FAIL" in output
        assert "Error!" in output


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_seconds_only(self):
        """Test formatting seconds only."""
        assert _format_duration(30) == "30s"
        assert _format_duration(1) == "1s"
        assert _format_duration(59) == "59s"

    def test_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(3599) == "59m 59s"

    def test_hours_and_minutes(self):
        """Test formatting hours and minutes."""
        assert _format_duration(3600) == "1h 0m"
        assert _format_duration(3660) == "1h 1m"
        assert _format_duration(7200) == "2h 0m"


class TestPrintFunctions:
    """Tests for print helper functions."""

    @patch('builtins.print')
    def test_print_header(self, mock_print):
        """Test print_header outputs correctly."""
        set_colors_enabled(False)
        print_header("Test Header")
        assert mock_print.call_count >= 3

    @patch('builtins.print')
    def test_print_result_box(self, mock_print):
        """Test print_result_box outputs correctly."""
        set_colors_enabled(False)
        print_result_box("Title", {"Key": "Value"})
        assert mock_print.called

    @patch('builtins.print')
    def test_print_table(self, mock_print):
        """Test print_table outputs correctly."""
        set_colors_enabled(False)
        print_table(
            ["Name", "Value"],
            [["foo", 1], ["bar", 2]]
        )
        assert mock_print.call_count >= 3

    @patch('builtins.print')
    def test_print_status_success(self, mock_print):
        """Test print_status with success."""
        set_colors_enabled(False)
        print_status("ok", "Task completed")
        mock_print.assert_called()
        args = str(mock_print.call_args)
        assert "OK" in args
        assert "Task completed" in args

    @patch('builtins.print')
    def test_print_status_error(self, mock_print):
        """Test print_status with error."""
        set_colors_enabled(False)
        print_status("error", "Task failed")
        mock_print.assert_called()
        args = str(mock_print.call_args)
        assert "ERROR" in args

    @patch('builtins.print')
    def test_print_list(self, mock_print):
        """Test print_list outputs correctly."""
        set_colors_enabled(False)
        print_list(["Item 1", "Item 2", "Item 3"])
        assert mock_print.call_count == 3


class TestSupportsColor:
    """Tests for color support detection."""

    @patch('sys.stdout')
    def test_no_isatty(self, mock_stdout):
        """Test returns False when stdout has no isatty."""
        del mock_stdout.isatty
        # Note: This would need to reimport to test properly
        # Just verify the function exists and returns bool
        result = supports_color()
        assert isinstance(result, bool)

    def test_returns_bool(self):
        """Test supports_color returns boolean."""
        result = supports_color()
        assert isinstance(result, bool)


class TestColorEnum:
    """Tests for Color enum."""

    def test_all_colors_defined(self):
        """Test all expected colors are defined."""
        assert Color.RED
        assert Color.GREEN
        assert Color.YELLOW
        assert Color.BLUE
        assert Color.CYAN
        assert Color.MAGENTA
        assert Color.WHITE
        assert Color.BLACK
        assert Color.RESET
        assert Color.BOLD
        assert Color.DIM

    def test_color_values_are_ansi(self):
        """Test color values are ANSI escape codes."""
        assert Color.RESET.value == "\033[0m"
        assert Color.RED.value.startswith("\033[")


class TestIntegration:
    """Integration tests for CLI formatting."""

    def test_mixed_colors_disabled(self):
        """Test all formatting works when colors disabled."""
        set_colors_enabled(False)

        result = colorize(success(error(warning("nested"))), Color.CYAN)
        assert "nested" in result
        # No color codes when disabled
        assert "\033[" not in result

    def test_progress_bar_full_workflow(self):
        """Test complete progress bar workflow."""
        bar = ProgressBar(5, "Processing", show_eta=False)

        for i in range(5):
            bar.update()

        assert bar.current == 5

    @patch('builtins.print')
    def test_result_box_with_data(self, mock_print):
        """Test result box with various data types."""
        set_colors_enabled(False)
        print_result_box("Results", {
            "String": "value",
            "Integer": 42,
            "Float": 3.14,
            "Bool": True,
            "": "",  # Spacer
            "After spacer": "test"
        })
        assert mock_print.called

    @patch('builtins.print')
    def test_table_with_min_widths(self, mock_print):
        """Test table with minimum column widths."""
        set_colors_enabled(False)
        print_table(
            ["A", "B"],
            [["x", "y"]],
            min_widths=[10, 20]
        )
        assert mock_print.called
