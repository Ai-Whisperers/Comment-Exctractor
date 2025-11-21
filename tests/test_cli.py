"""Tests for the CLI module."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

from src.cli.main import (
    create_parser,
    setup_logging,
    print_result_box,
)


class TestCLIParser:
    """Tests for CLI argument parser."""

    def test_create_parser(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None

    def test_parser_has_subcommands(self):
        """Test that parser has all expected subcommands."""
        parser = create_parser()
        # Get subparser actions
        subparsers_actions = [
            action for action in parser._actions
            if action.dest == "command"
        ]
        assert len(subparsers_actions) == 1

    def test_extract_command_parsing(self):
        """Test parsing extract command."""
        parser = create_parser()
        args = parser.parse_args([
            "extract", "test_client", "instagram", "test_account",
            "--max-posts", "50"
        ])

        assert args.command == "extract"
        assert args.client == "test_client"
        assert args.platform == "instagram"
        assert args.account == "test_account"
        assert args.max_posts == 50

    def test_export_command_parsing(self):
        """Test parsing export command."""
        parser = create_parser()
        args = parser.parse_args([
            "export", "test_client",
            "--format", "csv",
            "--output-dir", "/tmp/exports"
        ])

        assert args.command == "export"
        assert args.client == "test_client"
        assert args.format == "csv"
        assert args.output_dir == "/tmp/exports"

    def test_stats_command_parsing(self):
        """Test parsing stats command."""
        parser = create_parser()
        args = parser.parse_args(["stats", "test_client"])

        assert args.command == "stats"
        assert args.client == "test_client"

    def test_profile_command_parsing(self):
        """Test parsing profile command."""
        parser = create_parser()
        args = parser.parse_args([
            "profile", "instagram", "test_account"
        ])

        assert args.command == "profile"
        assert args.platform == "instagram"
        assert args.account == "test_account"

    def test_batch_command_parsing(self):
        """Test parsing batch command."""
        parser = create_parser()
        args = parser.parse_args([
            "batch",
            "--config", "config/test.json",
            "--max-posts", "200"
        ])

        assert args.command == "batch"
        assert args.config == "config/test.json"
        assert args.max_posts == 200

    def test_verbose_flag(self):
        """Test verbose flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["-v", "list-platforms"])

        assert args.verbose is True

    def test_log_level_option(self):
        """Test log level option parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "--log-level", "DEBUG",
            "list-platforms"
        ])

        assert args.log_level == "DEBUG"

    def test_data_dir_option(self):
        """Test data dir option parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "--data-dir", "/custom/data",
            "list-platforms"
        ])

        assert args.data_dir == "/custom/data"


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        import logging
        setup_logging()
        # Should not raise any errors

    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        import logging
        setup_logging(verbose=True)
        # Should set DEBUG level

    def test_setup_logging_with_level(self):
        """Test logging setup with explicit level."""
        import logging
        setup_logging(log_level="WARNING")
        # Should set WARNING level


class TestPrintResultBox:
    """Tests for result box printing."""

    def test_print_result_box(self, capsys):
        """Test printing result box."""
        content = {
            "Key 1": "Value 1",
            "Key 2": "Value 2"
        }
        print_result_box("Test Title", content, width=40)

        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "Key 1: Value 1" in captured.out
        assert "Key 2: Value 2" in captured.out
        assert "=" * 40 in captured.out


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.mark.unit
    def test_list_platforms_command(self, capsys):
        """Test list-platforms command execution."""
        from src.cli.main import cmd_list_platforms

        class MockArgs:
            pass

        cmd_list_platforms(MockArgs())

        captured = capsys.readouterr()
        assert "Available platforms:" in captured.out

    @pytest.mark.unit
    def test_list_formats_command(self, capsys):
        """Test list-formats command execution."""
        from src.cli.main import cmd_list_formats

        class MockArgs:
            pass

        cmd_list_formats(MockArgs())

        captured = capsys.readouterr()
        assert "Available export formats:" in captured.out
