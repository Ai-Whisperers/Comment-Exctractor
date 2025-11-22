"""Registry for data exporters."""

import logging
from typing import Dict, Type, List, Optional

from .base import BaseExporter
from .json_exporter import JSONExporter
from .csv_exporter import CSVExporter
from .jsonl_exporter import JSONLExporter
from .options import ExportOptions
from ..core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ExporterRegistry:
    """Registry for managing data exporters."""

    _exporters: Dict[str, Type[BaseExporter]] = {
        "json": JSONExporter,
        "csv": CSVExporter,
        "jsonl": JSONLExporter,
    }

    @classmethod
    def register(cls, format_name: str, exporter_class: Type[BaseExporter]) -> None:
        """
        Register an exporter for a format.

        Args:
            format_name: Format name (e.g., "json", "csv")
            exporter_class: Exporter class to register
        """
        cls._exporters[format_name.lower()] = exporter_class
        logger.debug(f"Registered exporter for {format_name}: {exporter_class.__name__}")

    @classmethod
    def get(cls, format_name: str, options: Optional[ExportOptions] = None) -> BaseExporter:
        """
        Get an exporter instance for a format.

        Args:
            format_name: Format name
            options: Export customization options

        Returns:
            Exporter instance

        Raises:
            ConfigurationError: If format is not supported
        """
        format_lower = format_name.lower()

        if format_lower not in cls._exporters:
            available = ", ".join(cls._exporters.keys())
            raise ConfigurationError(
                f"Unsupported export format: {format_name}. Available: {available}",
                setting="format"
            )

        exporter_class = cls._exporters[format_lower]
        return exporter_class(options=options)

    @classmethod
    def list_available(cls) -> List[str]:
        """
        List available export formats.

        Returns:
            List of format names
        """
        return list(cls._exporters.keys())

    @classmethod
    def is_available(cls, format_name: str) -> bool:
        """
        Check if a format is available.

        Args:
            format_name: Format name

        Returns:
            True if format is available
        """
        return format_name.lower() in cls._exporters
