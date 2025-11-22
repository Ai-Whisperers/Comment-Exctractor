"""Tests for export format customization options."""

import pytest
import json
import csv
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from src.exporters.options import (
    ExportOptions,
    DateFormat,
    CSVQuoting,
    EXPORT_PRESETS,
    get_preset,
)
from src.exporters import (
    JSONExporter,
    CSVExporter,
    JSONLExporter,
    ExporterRegistry,
)
from src.core.models import Comment, Post, Author, Platform, ExportMetadata


# Test fixtures

@pytest.fixture
def sample_author():
    """Create a sample author."""
    return Author(
        platform_id="author123",
        username="testuser",
        display_name="Test User",
        is_verified=True
    )


@pytest.fixture
def sample_comment(sample_author):
    """Create a sample comment."""
    return Comment(
        platform=Platform.INSTAGRAM,
        platform_id="comment123",
        post_id="post456",
        text="This is a test comment with some text content",
        author=sample_author,
        published_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        likes=42,
        replies_count=5,
        parent_id=None
    )


@pytest.fixture
def sample_post():
    """Create a sample post."""
    return Post(
        platform=Platform.INSTAGRAM,
        platform_id="post456",
        account_id="account789",
        url="https://instagram.com/p/123",
        text="This is a test post",
        published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        likes=100,
        comments_count=10,
        shares=5,
        media_type="image"
    )


@pytest.fixture
def sample_metadata():
    """Create sample export metadata."""
    return ExportMetadata(
        client="test_client",
        exported_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        format="json",
        version="1.0"
    )


class TestExportOptionsValidation:
    """Tests for ExportOptions validation."""

    def test_default_options(self):
        """Test default options are valid."""
        options = ExportOptions()
        assert options.date_format == DateFormat.ISO
        assert options.csv_delimiter == ","
        assert options.json_indent == 2

    def test_custom_date_format_requires_format_string(self):
        """Test CUSTOM date format requires format string."""
        with pytest.raises(ValueError, match="custom_date_format required"):
            ExportOptions(date_format=DateFormat.CUSTOM)

    def test_custom_date_format_with_string(self):
        """Test CUSTOM date format with format string works."""
        options = ExportOptions(
            date_format=DateFormat.CUSTOM,
            custom_date_format="%Y-%m-%d"
        )
        assert options.custom_date_format == "%Y-%m-%d"

    def test_csv_delimiter_must_be_single_char(self):
        """Test CSV delimiter must be single character."""
        with pytest.raises(ValueError, match="single character"):
            ExportOptions(csv_delimiter=";;")

    def test_truncate_text_must_be_positive(self):
        """Test truncate_text must be positive."""
        with pytest.raises(ValueError, match="must be positive"):
            ExportOptions(truncate_text=0)

    def test_json_indent_must_be_non_negative(self):
        """Test json_indent must be non-negative."""
        with pytest.raises(ValueError, match="non-negative"):
            ExportOptions(json_indent=-1)


class TestDateFormatting:
    """Tests for date formatting options."""

    def test_iso_format(self):
        """Test ISO date format."""
        options = ExportOptions(date_format=DateFormat.ISO)
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = options.format_date(dt)
        assert "2024-01-15" in result
        assert "10:30:00" in result

    def test_iso_date_format(self):
        """Test ISO date only format."""
        options = ExportOptions(date_format=DateFormat.ISO_DATE)
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = options.format_date(dt)
        assert result == "2024-01-15"

    def test_timestamp_format(self):
        """Test timestamp format."""
        options = ExportOptions(date_format=DateFormat.TIMESTAMP)
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = options.format_date(dt)
        assert result.isdigit()

    def test_human_format(self):
        """Test human-readable format."""
        options = ExportOptions(date_format=DateFormat.HUMAN)
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = options.format_date(dt)
        assert "Jan" in result
        assert "15" in result
        assert "2024" in result

    def test_custom_format(self):
        """Test custom date format."""
        options = ExportOptions(
            date_format=DateFormat.CUSTOM,
            custom_date_format="%d/%m/%Y"
        )
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = options.format_date(dt)
        assert result == "15/01/2024"

    def test_format_none_date(self):
        """Test formatting None date."""
        options = ExportOptions()
        assert options.format_date(None) is None


class TestFieldSelection:
    """Tests for field selection options."""

    def test_include_fields(self):
        """Test including specific fields."""
        options = ExportOptions(include_fields=["id", "text", "likes"])
        available = ["id", "platform", "text", "likes", "author"]
        result = options.get_effective_fields(available)
        assert result == ["id", "text", "likes"]

    def test_exclude_fields(self):
        """Test excluding specific fields."""
        options = ExportOptions(exclude_fields=["author", "parent_id"])
        available = ["id", "text", "author", "parent_id", "likes"]
        result = options.get_effective_fields(available)
        assert "author" not in result
        assert "parent_id" not in result
        assert "id" in result

    def test_include_and_exclude(self):
        """Test both include and exclude."""
        options = ExportOptions(
            include_fields=["id", "text", "author", "likes"],
            exclude_fields=["author"]
        )
        available = ["id", "platform", "text", "author", "likes"]
        result = options.get_effective_fields(available)
        assert "author" not in result
        assert "id" in result
        assert "text" in result

    def test_field_mapping(self):
        """Test field name mapping."""
        options = ExportOptions(field_mapping={
            "id": "comment_id",
            "text": "content"
        })
        assert options.apply_field_mapping("id") == "comment_id"
        assert options.apply_field_mapping("text") == "content"
        assert options.apply_field_mapping("likes") == "likes"


class TestTextProcessing:
    """Tests for text processing options."""

    def test_truncate_text(self):
        """Test text truncation."""
        options = ExportOptions(truncate_text=20)
        long_text = "This is a very long text that should be truncated"
        result = options.truncate_text_field(long_text)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_short_text(self):
        """Test truncation doesn't affect short text."""
        options = ExportOptions(truncate_text=50)
        short_text = "Short text"
        result = options.truncate_text_field(short_text)
        assert result == short_text

    def test_truncate_none(self):
        """Test truncation handles None."""
        options = ExportOptions(truncate_text=20)
        assert options.truncate_text_field(None) is None

    def test_filter_empty_fields(self):
        """Test filtering empty fields."""
        options = ExportOptions(include_empty_fields=False)
        data = {
            "id": "123",
            "text": "",
            "likes": 0,
            "parent_id": None,
            "tags": []
        }
        result = options.filter_empty_fields(data)
        assert "id" in result
        assert "likes" in result
        assert "text" not in result
        assert "parent_id" not in result
        assert "tags" not in result


class TestJSONExporterWithOptions:
    """Tests for JSON exporter with options."""

    def test_json_no_metadata(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export without metadata."""
        options = ExportOptions(json_include_metadata=False)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        # Should be a list, not a dict with metadata
        assert isinstance(data, list)
        assert len(data) == 1

    def test_json_with_stats(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export with statistics."""
        options = ExportOptions(include_export_stats=True)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert "stats" in data["metadata"]
        assert "avg_likes" in data["metadata"]["stats"]

    def test_json_custom_indent(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export with custom indentation."""
        options = ExportOptions(json_indent=4)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            content = f.read()

        # Check for 4-space indentation
        assert "    " in content

    def test_json_no_indent(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export without indentation."""
        options = ExportOptions(json_indent=None)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            content = f.read()

        # Should be single line (or minimal whitespace)
        assert content.count("\n") <= 1

    def test_json_sorted_keys(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export with sorted keys."""
        options = ExportOptions(json_sort_keys=True)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        # Keys in comments should be sorted
        comment_keys = list(data["comments"][0].keys())
        assert comment_keys == sorted(comment_keys)

    def test_json_flatten_author(self, sample_comment, sample_metadata, tmp_path):
        """Test JSON export with flattened author."""
        options = ExportOptions(flatten_author=True)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        comment = data["comments"][0]
        assert "author" not in comment
        assert "author_username" in comment


class TestCSVExporterWithOptions:
    """Tests for CSV exporter with options."""

    def test_csv_custom_delimiter(self, sample_comment, sample_metadata, tmp_path):
        """Test CSV export with custom delimiter."""
        options = ExportOptions(csv_delimiter=";", flatten_author=True)
        exporter = CSVExporter(options)
        output_path = str(tmp_path / "test.csv")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            content = f.read()

        assert ";" in content
        # Fewer commas since we're using semicolon
        assert content.count(";") > content.count(",")

    def test_csv_no_header(self, sample_comment, sample_metadata, tmp_path):
        """Test CSV export without header."""
        options = ExportOptions(csv_include_header=False, flatten_author=True)
        exporter = CSVExporter(options)
        output_path = str(tmp_path / "test.csv")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            lines = f.readlines()

        # Should have only data row, no header
        assert len(lines) == 1

    def test_csv_quote_all(self, sample_comment, sample_metadata, tmp_path):
        """Test CSV export with all fields quoted."""
        options = ExportOptions(csv_quoting=CSVQuoting.ALL, flatten_author=True)
        exporter = CSVExporter(options)
        output_path = str(tmp_path / "test.csv")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            content = f.read()

        # All fields should be quoted
        assert content.count('"') > 10

    def test_csv_field_selection(self, sample_comment, sample_metadata, tmp_path):
        """Test CSV export with field selection."""
        options = ExportOptions(
            include_fields=["id", "text", "likes"],
            flatten_author=True
        )
        exporter = CSVExporter(options)
        output_path = str(tmp_path / "test.csv")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should only have selected fields
        assert set(rows[0].keys()) == {"id", "text", "likes"}


class TestJSONLExporterWithOptions:
    """Tests for JSONL exporter with options."""

    def test_jsonl_no_metadata_line(self, sample_comment, sample_metadata, tmp_path):
        """Test JSONL export without metadata line."""
        options = ExportOptions(jsonl_include_metadata_line=False)
        exporter = JSONLExporter(options)
        output_path = str(tmp_path / "test.jsonl")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            lines = f.readlines()

        # Should have only data line(s)
        assert len(lines) == 1
        first_line = json.loads(lines[0])
        assert "client" not in first_line

    def test_jsonl_no_type_field(self, sample_comment, sample_metadata, tmp_path):
        """Test JSONL export without type field."""
        options = ExportOptions(jsonl_include_type_field=False)
        exporter = JSONLExporter(options)
        output_path = str(tmp_path / "test.jsonl")

        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            lines = f.readlines()

        # Skip metadata line
        data_line = json.loads(lines[1])
        assert "type" not in data_line


class TestPresets:
    """Tests for export presets."""

    def test_get_minimal_preset(self):
        """Test getting minimal preset."""
        options = get_preset("minimal")
        assert options.include_fields is not None
        assert options.json_include_metadata is False

    def test_get_analytics_preset(self):
        """Test getting analytics preset."""
        options = get_preset("analytics")
        assert options.date_format == DateFormat.TIMESTAMP
        assert options.include_export_stats is True

    def test_get_readable_preset(self):
        """Test getting readable preset."""
        options = get_preset("readable")
        assert options.date_format == DateFormat.HUMAN
        assert options.json_indent == 4

    def test_get_streaming_preset(self):
        """Test getting streaming preset."""
        options = get_preset("streaming")
        assert options.json_indent is None
        assert options.jsonl_include_metadata_line is False

    def test_get_excel_friendly_preset(self):
        """Test getting excel_friendly preset."""
        options = get_preset("excel_friendly")
        assert options.csv_quoting == CSVQuoting.ALL

    def test_unknown_preset_raises(self):
        """Test unknown preset raises error."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent")

    def test_preset_returns_copy(self):
        """Test preset returns a copy, not reference."""
        options1 = get_preset("minimal")
        options2 = get_preset("minimal")
        options1.json_indent = 10
        assert options2.json_indent != 10


class TestRegistryWithOptions:
    """Tests for registry with options support."""

    def test_get_exporter_with_options(self):
        """Test getting exporter with options."""
        options = ExportOptions(json_indent=4)
        exporter = ExporterRegistry.get("json", options)
        assert exporter.options.json_indent == 4

    def test_get_exporter_default_options(self):
        """Test getting exporter with default options."""
        exporter = ExporterRegistry.get("csv")
        assert exporter.options is not None
        assert exporter.options.csv_delimiter == ","


class TestIntegration:
    """Integration tests for export options."""

    def test_full_workflow_json(self, sample_comment, sample_metadata, tmp_path):
        """Test full JSON export workflow with options."""
        options = ExportOptions(
            date_format=DateFormat.ISO_DATE,
            include_fields=["id", "text", "published_at", "likes"],
            field_mapping={"id": "comment_id"},
            json_indent=2,
            include_export_stats=True
        )

        exporter = ExporterRegistry.get("json", options)
        output_path = str(tmp_path / "test.json")
        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        comment = data["comments"][0]
        assert "comment_id" in comment
        assert "id" not in comment
        assert comment["published_at"] == "2024-01-15"
        assert "stats" in data["metadata"]

    def test_full_workflow_csv(self, sample_comment, sample_metadata, tmp_path):
        """Test full CSV export workflow with options."""
        options = ExportOptions(
            csv_delimiter="\t",
            date_format=DateFormat.ISO_DATE,
            truncate_text=30,
            flatten_author=True
        )

        exporter = ExporterRegistry.get("csv", options)
        output_path = str(tmp_path / "test.csv")
        exporter.export([sample_comment], sample_metadata, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "\t" in content
        assert "2024-01-15" in content

    def test_multiple_comments(self, sample_author, sample_metadata, tmp_path):
        """Test export with multiple comments."""
        comments = [
            Comment(
                platform=Platform.INSTAGRAM,
                platform_id=f"comment{i}",
                post_id="post1",
                text=f"Comment {i}",
                author=sample_author,
                published_at=datetime(2024, 1, i, 10, 0, 0, tzinfo=timezone.utc),
                likes=i * 10,
                replies_count=0
            )
            for i in range(1, 6)
        ]

        options = ExportOptions(include_export_stats=True)
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")
        exporter.export(comments, sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert len(data["comments"]) == 5
        assert data["metadata"]["stats"]["avg_likes"] == 30  # (10+20+30+40+50)/5

    def test_empty_comments_list(self, sample_metadata, tmp_path):
        """Test export with empty comments list."""
        options = ExportOptions()
        exporter = JSONExporter(options)
        output_path = str(tmp_path / "test.json")
        exporter.export([], sample_metadata, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert data["comments"] == []
        assert data["metadata"]["total_comments"] == 0
