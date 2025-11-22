"""Tests for data exporters."""

import json
import csv
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.models import (
    Platform,
    Post,
    Comment,
    Author,
    ExportMetadata,
)
from src.exporters import (
    BaseExporter,
    JSONExporter,
    CSVExporter,
    JSONLExporter,
    ExporterRegistry,
    ExportOptions,
)
from src.core.exceptions import ConfigurationError


class TestBaseExporter:
    """Tests for BaseExporter abstract class."""

    @pytest.mark.unit
    def test_base_exporter_cannot_instantiate(self):
        """Test that BaseExporter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseExporter()

    @pytest.mark.unit
    def test_json_exporter_inherits_from_base(self):
        """Test that JSONExporter inherits from BaseExporter."""
        assert issubclass(JSONExporter, BaseExporter)

    @pytest.mark.unit
    def test_csv_exporter_inherits_from_base(self):
        """Test that CSVExporter inherits from BaseExporter."""
        assert issubclass(CSVExporter, BaseExporter)

    @pytest.mark.unit
    def test_jsonl_exporter_inherits_from_base(self):
        """Test that JSONLExporter inherits from BaseExporter."""
        assert issubclass(JSONLExporter, BaseExporter)


class TestExporterRegistry:
    """Tests for ExporterRegistry."""

    @pytest.mark.unit
    def test_list_available_formats(self):
        """Test listing available export formats."""
        formats = ExporterRegistry.list_available()

        assert "json" in formats
        assert "csv" in formats
        assert "jsonl" in formats

    @pytest.mark.unit
    def test_get_json_exporter(self):
        """Test getting JSON exporter from registry."""
        exporter = ExporterRegistry.get("json")

        assert isinstance(exporter, JSONExporter)
        assert exporter.format == "json"

    @pytest.mark.unit
    def test_get_csv_exporter(self):
        """Test getting CSV exporter from registry."""
        exporter = ExporterRegistry.get("csv")

        assert isinstance(exporter, CSVExporter)
        assert exporter.format == "csv"

    @pytest.mark.unit
    def test_get_jsonl_exporter(self):
        """Test getting JSONL exporter from registry."""
        exporter = ExporterRegistry.get("jsonl")

        assert isinstance(exporter, JSONLExporter)
        assert exporter.format == "jsonl"

    @pytest.mark.unit
    def test_get_case_insensitive(self):
        """Test that format names are case insensitive."""
        exporter1 = ExporterRegistry.get("JSON")
        exporter2 = ExporterRegistry.get("Json")

        assert isinstance(exporter1, JSONExporter)
        assert isinstance(exporter2, JSONExporter)

    @pytest.mark.unit
    def test_get_unknown_format_raises_error(self):
        """Test that getting unknown format raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            ExporterRegistry.get("unknown_format")

        assert "Unsupported export format" in str(exc_info.value)

    @pytest.mark.unit
    def test_is_available_true(self):
        """Test is_available returns True for known formats."""
        assert ExporterRegistry.is_available("json")
        assert ExporterRegistry.is_available("csv")
        assert ExporterRegistry.is_available("jsonl")

    @pytest.mark.unit
    def test_is_available_false(self):
        """Test is_available returns False for unknown formats."""
        assert not ExporterRegistry.is_available("unknown")
        assert not ExporterRegistry.is_available("xml")


class ExporterTestMixin:
    """Mixin with common test data for exporters."""

    def create_test_post(self) -> Post:
        """Create a test post."""
        return Post(
            platform=Platform.INSTAGRAM,
            platform_id="post_123",
            account_id="test_account",
            url="https://instagram.com/p/test",
            text="Test post content",
            published_at=datetime(2024, 1, 15, 10, 30, 0),
            likes=100,
            comments_count=5,
            shares=10,
            media_type="image",
        )

    def create_test_comment(self) -> Comment:
        """Create a test comment."""
        return Comment(
            platform=Platform.INSTAGRAM,
            platform_id="comment_456",
            post_id="post_123",
            text="This is a test comment",
            author=Author(
                platform_id="author_789",
                username="testuser",
                display_name="Test User",
                is_verified=True,
            ),
            published_at=datetime(2024, 1, 15, 11, 0, 0),
            likes=10,
            replies_count=2,
            parent_id=None,
        )

    def create_test_metadata(self) -> ExportMetadata:
        """Create test export metadata."""
        return ExportMetadata(
            client="test_client",
            exported_at=datetime(2024, 1, 15, 12, 0, 0),
            format="json",
            total_comments=1,
            platforms=["instagram"],
            version="1.0",
        )


class TestJSONExporter(ExporterTestMixin):
    """Tests for JSONExporter."""

    @pytest.mark.unit
    def test_export_comments(self):
        """Test exporting comments to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONExporter()
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.json"
            result = exporter.export(comments, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "comments" in data
            assert len(data["comments"]) == 1
            assert data["comments"][0]["id"] == "comment_456"
            assert data["comments"][0]["text"] == "This is a test comment"

    @pytest.mark.unit
    def test_export_posts(self):
        """Test exporting posts to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONExporter()
            posts = [self.create_test_post()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "posts.json"
            result = exporter.export_posts(posts, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "posts" in data
            assert len(data["posts"]) == 1
            assert data["posts"][0]["id"] == "post_123"
            assert data["posts"][0]["likes"] == 100

    @pytest.mark.unit
    def test_export_creates_directories(self):
        """Test that export creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONExporter()
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "nested" / "dir" / "comments.json"
            exporter.export(comments, metadata, str(output_path))

            assert output_path.exists()

    @pytest.mark.unit
    def test_export_metadata_format(self):
        """Test that metadata is correctly formatted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONExporter()
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.json"
            exporter.export(comments, metadata, str(output_path))

            with open(output_path) as f:
                data = json.load(f)

            assert data["metadata"]["client"] == "test_client"
            assert data["metadata"]["version"] == "1.0"
            assert "exported_at" in data["metadata"]


class TestCSVExporter(ExporterTestMixin):
    """Tests for CSVExporter."""

    @pytest.mark.unit
    def test_export_comments(self):
        """Test exporting comments to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use flatten_author=True for CSV backward compatibility
            options = ExportOptions(flatten_author=True)
            exporter = CSVExporter(options)
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.csv"
            result = exporter.export(comments, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["id"] == "comment_456"
            assert rows[0]["text"] == "This is a test comment"
            assert rows[0]["author_username"] == "testuser"

    @pytest.mark.unit
    def test_export_posts(self):
        """Test exporting posts to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = CSVExporter()
            posts = [self.create_test_post()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "posts.csv"
            result = exporter.export_posts(posts, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["id"] == "post_123"
            assert rows[0]["likes"] == "100"

    @pytest.mark.unit
    def test_csv_has_correct_headers(self):
        """Test that CSV has all expected headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use flatten_author=True for CSV backward compatibility
            options = ExportOptions(flatten_author=True)
            exporter = CSVExporter(options)
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.csv"
            exporter.export(comments, metadata, str(output_path))

            with open(output_path, newline="") as f:
                reader = csv.reader(f)
                headers = next(reader)

            expected_headers = [
                "id", "platform", "post_id", "text",
                "author_id", "author_username", "author_display_name",
                "author_is_verified", "published_at", "likes",
                "replies_count", "parent_id"
            ]
            assert headers == expected_headers


class TestJSONLExporter(ExporterTestMixin):
    """Tests for JSONLExporter."""

    @pytest.mark.unit
    def test_export_comments(self):
        """Test exporting comments to JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONLExporter()
            comments = [self.create_test_comment()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.jsonl"
            result = exporter.export(comments, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path) as f:
                lines = f.readlines()

            assert len(lines) == 2  # metadata + 1 comment

            # First line is metadata
            meta = json.loads(lines[0])
            assert meta["type"] == "metadata"
            assert meta["client"] == "test_client"

            # Second line is comment
            comment_data = json.loads(lines[1])
            assert comment_data["type"] == "comment"
            assert comment_data["id"] == "comment_456"

    @pytest.mark.unit
    def test_export_posts(self):
        """Test exporting posts to JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONLExporter()
            posts = [self.create_test_post()]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "posts.jsonl"
            result = exporter.export_posts(posts, metadata, str(output_path))

            assert result == str(output_path)
            assert output_path.exists()

            with open(output_path) as f:
                lines = f.readlines()

            assert len(lines) == 2  # metadata + 1 post

            # Second line is post
            post_data = json.loads(lines[1])
            assert post_data["type"] == "post"
            assert post_data["id"] == "post_123"

    @pytest.mark.unit
    def test_jsonl_format_is_valid(self):
        """Test that each line is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONLExporter()
            comments = [self.create_test_comment() for _ in range(3)]
            metadata = self.create_test_metadata()

            output_path = Path(tmpdir) / "comments.jsonl"
            exporter.export(comments, metadata, str(output_path))

            with open(output_path) as f:
                for line in f:
                    # Should not raise
                    data = json.loads(line)
                    assert isinstance(data, dict)

    @pytest.mark.unit
    def test_export_multiple_comments(self):
        """Test exporting multiple comments to JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONLExporter()

            comments = []
            for i in range(5):
                comment = self.create_test_comment()
                comment.platform_id = f"comment_{i}"
                comments.append(comment)

            metadata = self.create_test_metadata()
            metadata.total_comments = 5

            output_path = Path(tmpdir) / "comments.jsonl"
            exporter.export(comments, metadata, str(output_path))

            with open(output_path) as f:
                lines = f.readlines()

            assert len(lines) == 6  # 1 metadata + 5 comments
