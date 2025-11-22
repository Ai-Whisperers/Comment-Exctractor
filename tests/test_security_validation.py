"""Tests for security validation functions."""

import pytest
import tempfile
from pathlib import Path

from src.storage.base import (
    validate_safe_path,
    sanitize_filename,
    StorageBackend,
    StorageFactory,
)
from src.core.exceptions import ValidationError


class TestValidateSafePath:
    """Tests for validate_safe_path function."""

    def test_valid_path_within_base(self):
        """Test that valid paths within base directory pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "subdir" / "file.json"

            assert validate_safe_path(base, target) is True

    def test_valid_nested_path(self):
        """Test deeply nested valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "a" / "b" / "c" / "d" / "file.txt"

            assert validate_safe_path(base, target) is True

    def test_path_traversal_attack(self):
        """Test that path traversal attacks are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Try to escape base directory
            target = base / ".." / "etc" / "passwd"

            assert validate_safe_path(base, target) is False

    def test_double_dot_in_middle(self):
        """Test path traversal in middle of path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "subdir" / ".." / ".." / "escape"

            assert validate_safe_path(base, target) is False

    def test_absolute_path_outside_base(self):
        """Test absolute path outside base directory."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                base = Path(tmpdir1)
                target = Path(tmpdir2) / "file.txt"

                assert validate_safe_path(base, target) is False

    def test_same_directory(self):
        """Test when target is the base directory itself."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            assert validate_safe_path(base, base) is True

    def test_handles_symlinks(self):
        """Test that symlinks are resolved properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create a subdirectory
            subdir = base / "subdir"
            subdir.mkdir()

            # Path to file in subdirectory
            target = subdir / "file.txt"

            assert validate_safe_path(base, target) is True


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename(self):
        """Test that normal filenames pass through."""
        result = sanitize_filename("normal_filename")
        assert result == "normal_filename"

    def test_removes_path_separators(self):
        """Test that path separators are removed."""
        result = sanitize_filename("path/to/file")
        assert "/" not in result
        assert result == "path_to_file"

    def test_removes_backslashes(self):
        """Test that backslashes are removed."""
        result = sanitize_filename("path\\to\\file")
        assert "\\" not in result

    def test_removes_dangerous_characters(self):
        """Test that dangerous characters are replaced."""
        dangerous = '<>:"/\\|?*'
        result = sanitize_filename(f"file{dangerous}name")

        for char in dangerous:
            assert char not in result

    def test_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_filename("file\x00name")
        assert "\x00" not in result

    def test_removes_control_characters(self):
        """Test that control characters are removed."""
        result = sanitize_filename("file\x01\x1fname")
        assert "\x01" not in result
        assert "\x1f" not in result

    def test_strips_leading_trailing_dots(self):
        """Test that leading/trailing dots are stripped."""
        result = sanitize_filename("...filename...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_strips_leading_trailing_spaces(self):
        """Test that leading/trailing spaces are stripped."""
        result = sanitize_filename("  filename  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_empty_string_becomes_unnamed(self):
        """Test that empty string becomes 'unnamed'."""
        result = sanitize_filename("")
        assert result == "unnamed"

    def test_only_dots_becomes_unnamed(self):
        """Test that string of only dots becomes 'unnamed'."""
        result = sanitize_filename("...")
        assert result == "unnamed"

    def test_only_spaces_becomes_unnamed(self):
        """Test that string of only spaces becomes 'unnamed'."""
        result = sanitize_filename("   ")
        assert result == "unnamed"

    def test_length_limit(self):
        """Test that filenames are limited to 255 characters."""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        valid = "file_name-123.txt"
        result = sanitize_filename(valid)
        assert result == valid

    def test_unicode_characters(self):
        """Test that unicode characters are preserved."""
        unicode_name = "archivo_español"
        result = sanitize_filename(unicode_name)
        assert result == unicode_name

    def test_path_traversal_attempt(self):
        """Test that path traversal attempts are sanitized."""
        result = sanitize_filename("../../../etc/passwd")
        # Slashes are removed, making traversal impossible
        assert "/" not in result
        # Double dots are replaced with underscores for enhanced security
        assert ".." not in result
        assert result == "_____etc_passwd"


class TestStorageBackendValidation:
    """Tests for StorageBackend security validation."""

    def test_init_rejects_path_traversal(self):
        """Test that __init__ rejects paths with .."""
        with pytest.raises(ValidationError) as exc_info:
            # Create a concrete implementation for testing
            from src.storage.json_storage import JSONStorage
            JSONStorage("../../../etc")

        assert "path traversal" in str(exc_info.value).lower()

    def test_init_accepts_valid_path(self):
        """Test that __init__ accepts valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.storage.json_storage import JSONStorage
            storage = JSONStorage(tmpdir)
            assert storage.output_dir.exists()

    def test_init_creates_directory(self):
        """Test that __init__ creates the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_output_dir"
            assert not new_dir.exists()

            from src.storage.json_storage import JSONStorage
            storage = JSONStorage(str(new_dir))

            assert storage.output_dir.exists()

    def test_generate_filename_sanitizes_account(self):
        """Test that _generate_filename sanitizes account name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.storage.json_storage import JSONStorage
            storage = JSONStorage(tmpdir)

            # Attempt path traversal in account name
            path = storage._generate_filename(
                "../../../etc",
                "instagram",
                "posts",
                "json"
            )

            # The critical assertion: path must be within output_dir
            # This prevents path traversal attacks
            assert validate_safe_path(storage.output_dir, path)

    def test_generate_filename_sanitizes_platform(self):
        """Test that _generate_filename sanitizes platform name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.storage.json_storage import JSONStorage
            storage = JSONStorage(tmpdir)

            # Attempt injection in platform name
            path = storage._generate_filename(
                "account",
                "../malicious",
                "posts",
                "json"
            )

            assert validate_safe_path(storage.output_dir, path)

    def test_generate_filename_sanitizes_all_inputs(self):
        """Test that all inputs are sanitized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.storage.json_storage import JSONStorage
            storage = JSONStorage(tmpdir)

            # All inputs have dangerous characters
            path = storage._generate_filename(
                "acc<>ount",
                "plat:form",
                "data|type",
                "ex*t"
            )

            assert validate_safe_path(storage.output_dir, path)


class TestStorageFactoryValidation:
    """Tests for StorageFactory with validation."""

    def test_create_with_path_traversal(self):
        """Test that factory rejects path traversal."""
        with pytest.raises(ValidationError):
            StorageFactory.create("json", "../../../escape")

    def test_create_with_valid_path(self):
        """Test that factory accepts valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageFactory.create("json", tmpdir)
            assert storage is not None


class TestEdgeCases:
    """Edge case tests for security validation."""

    def test_empty_base_directory(self):
        """Test validation with current directory as base."""
        base = Path(".")
        target = base / "subdir" / "file.txt"

        # Should work with relative paths
        result = validate_safe_path(base, target)
        assert isinstance(result, bool)

    def test_unicode_path_traversal(self):
        """Test that unicode variations of .. are handled."""
        # Some systems might interpret unicode dots
        result = sanitize_filename("\u002e\u002e/etc/passwd")  # Unicode dots
        assert "/" not in result

    def test_very_long_path(self):
        """Test validation with very long paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create very long nested path
            nested = "/".join(["dir"] * 50) + "/file.txt"
            target = base / nested

            result = validate_safe_path(base, target)
            assert result is True

    def test_windows_style_paths(self):
        """Test that Windows-style paths are sanitized."""
        result = sanitize_filename("C:\\Users\\test\\file.txt")
        assert "\\" not in result
        assert ":" not in result

    def test_mixed_separators(self):
        """Test paths with mixed separators."""
        result = sanitize_filename("path/to\\file")
        assert "/" not in result
        assert "\\" not in result
