"""Export format customization options."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from enum import Enum


class DateFormat(Enum):
    """Supported date formats for export."""
    ISO = "iso"  # 2024-01-15T10:30:00+00:00
    ISO_DATE = "iso_date"  # 2024-01-15
    TIMESTAMP = "timestamp"  # 1705312200
    HUMAN = "human"  # Jan 15, 2024 10:30 AM
    CUSTOM = "custom"  # User-defined strftime format


class CSVQuoting(Enum):
    """CSV quoting styles."""
    MINIMAL = 0  # csv.QUOTE_MINIMAL
    ALL = 1  # csv.QUOTE_ALL
    NONNUMERIC = 2  # csv.QUOTE_NONNUMERIC
    NONE = 3  # csv.QUOTE_NONE


@dataclass
class ExportOptions:
    """
    Customization options for data export.

    Provides control over field selection, formatting, and output structure.
    """

    # Field selection
    include_fields: Optional[List[str]] = None  # None = all fields
    exclude_fields: Optional[List[str]] = None
    field_mapping: Optional[Dict[str, str]] = None  # Rename fields

    # Date formatting
    date_format: DateFormat = DateFormat.ISO
    custom_date_format: Optional[str] = None  # For DateFormat.CUSTOM
    timezone: Optional[str] = None  # e.g., "UTC", "America/New_York"

    # CSV options
    csv_delimiter: str = ","
    csv_quoting: CSVQuoting = CSVQuoting.MINIMAL
    csv_include_header: bool = True
    csv_line_terminator: str = "\n"

    # JSON options
    json_indent: Optional[int] = 2
    json_sort_keys: bool = False
    json_ensure_ascii: bool = False
    json_include_metadata: bool = True

    # JSONL options
    jsonl_include_metadata_line: bool = True
    jsonl_include_type_field: bool = True

    # Content options
    include_empty_fields: bool = True
    truncate_text: Optional[int] = None  # Max characters for text fields
    flatten_author: bool = False  # Flatten nested author object

    # Output options
    include_metadata: bool = True
    include_export_stats: bool = False

    def __post_init__(self):
        """Validate options after initialization."""
        if self.date_format == DateFormat.CUSTOM and not self.custom_date_format:
            raise ValueError("custom_date_format required when date_format is CUSTOM")

        if self.csv_delimiter and len(self.csv_delimiter) != 1:
            raise ValueError("CSV delimiter must be a single character")

        if self.truncate_text is not None and self.truncate_text < 1:
            raise ValueError("truncate_text must be positive")

        if self.json_indent is not None and self.json_indent < 0:
            raise ValueError("json_indent must be non-negative")

    def get_effective_fields(self, available_fields: List[str]) -> List[str]:
        """
        Calculate effective field list based on include/exclude rules.

        Args:
            available_fields: All available field names

        Returns:
            List of field names to include
        """
        # Start with all fields or included fields
        if self.include_fields:
            fields = [f for f in self.include_fields if f in available_fields]
        else:
            fields = list(available_fields)

        # Apply exclusions
        if self.exclude_fields:
            fields = [f for f in fields if f not in self.exclude_fields]

        return fields

    def apply_field_mapping(self, field_name: str) -> str:
        """
        Apply field name mapping/renaming.

        Args:
            field_name: Original field name

        Returns:
            Mapped field name (or original if no mapping)
        """
        if self.field_mapping and field_name in self.field_mapping:
            return self.field_mapping[field_name]
        return field_name

    def format_date(self, dt) -> Optional[str]:
        """
        Format a datetime according to options.

        Args:
            dt: datetime object or None

        Returns:
            Formatted date string or None
        """
        if dt is None:
            return None

        # Apply timezone if specified
        if self.timezone:
            try:
                from datetime import timezone as tz
                import zoneinfo
                target_tz = zoneinfo.ZoneInfo(self.timezone)
                dt = dt.astimezone(target_tz)
            except (ImportError, KeyError):
                # zoneinfo not available or invalid timezone
                pass

        if self.date_format == DateFormat.ISO:
            return dt.isoformat()
        elif self.date_format == DateFormat.ISO_DATE:
            return dt.date().isoformat()
        elif self.date_format == DateFormat.TIMESTAMP:
            return str(int(dt.timestamp()))
        elif self.date_format == DateFormat.HUMAN:
            return dt.strftime("%b %d, %Y %I:%M %p")
        elif self.date_format == DateFormat.CUSTOM:
            return dt.strftime(self.custom_date_format)
        else:
            return dt.isoformat()

    def truncate_text_field(self, text: Optional[str]) -> Optional[str]:
        """
        Truncate text field if configured.

        Args:
            text: Text to potentially truncate

        Returns:
            Truncated text or original
        """
        if text is None:
            return None

        if self.truncate_text and len(text) > self.truncate_text:
            return text[:self.truncate_text - 3] + "..."

        return text

    def filter_empty_fields(self, data: dict) -> dict:
        """
        Filter out empty fields if configured.

        Args:
            data: Dictionary with field data

        Returns:
            Filtered dictionary
        """
        if self.include_empty_fields:
            return data

        return {
            k: v for k, v in data.items()
            if v is not None and v != "" and v != []
        }


# Preset export options for common use cases

EXPORT_PRESETS: Dict[str, ExportOptions] = {
    "minimal": ExportOptions(
        include_fields=["id", "platform", "text", "author_username", "published_at", "likes"],
        flatten_author=True,
        json_include_metadata=False,
        json_indent=None,
    ),
    "analytics": ExportOptions(
        date_format=DateFormat.TIMESTAMP,
        flatten_author=True,
        include_export_stats=True,
        json_sort_keys=True,
    ),
    "readable": ExportOptions(
        date_format=DateFormat.HUMAN,
        json_indent=4,
        include_export_stats=True,
    ),
    "streaming": ExportOptions(
        json_indent=None,
        jsonl_include_metadata_line=False,
        include_empty_fields=False,
    ),
    "excel_friendly": ExportOptions(
        csv_delimiter=",",
        csv_quoting=CSVQuoting.ALL,
        date_format=DateFormat.ISO_DATE,
        flatten_author=True,
    ),
}


def get_preset(name: str) -> ExportOptions:
    """
    Get a preset export options configuration.

    Args:
        name: Preset name

    Returns:
        ExportOptions instance

    Raises:
        ValueError: If preset not found
    """
    if name not in EXPORT_PRESETS:
        available = ", ".join(EXPORT_PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")

    # Return a copy to prevent modification of preset
    import copy
    return copy.deepcopy(EXPORT_PRESETS[name])
