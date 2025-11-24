"""Dependency Injection Container for centralized dependency management.

This module provides a container that:
- Centralizes all dependency creation
- Makes dependencies explicit and testable
- Allows easy mocking for tests
- Manages service lifecycles
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Type, Callable

from .models import Platform
from ..config.settings import Settings, get_settings
from ..config.paths import get_paths, PathConfig
from ..storage.base import StorageBackend
from ..storage.sqlite import SQLiteStorage
from ..scrapers.base import BaseScraper
from ..scrapers.registry import ScraperRegistry
from ..exporters.base import BaseExporter
from ..exporters.registry import ExporterRegistry
from ..utils.output_paths import OutputPathManager

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency Injection Container.

    Centralizes dependency creation and management for the application.
    Makes dependencies explicit and easily mockable for testing.

    Usage:
        # Production
        container = Container()
        service = container.extraction_service()

        # Testing
        container = Container()
        container.register_storage(MockStorage())
        service = container.extraction_service()  # Uses mock storage
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        paths: Optional[PathConfig] = None
    ):
        """
        Initialize container with configuration.

        Args:
            settings: Application settings (defaults to get_settings())
            paths: Path configuration (defaults to get_paths())
        """
        self._settings = settings
        self._paths = paths

        # Registered overrides (for testing)
        self._storage_override: Optional[StorageBackend] = None
        self._scraper_factory_override: Optional[Callable] = None
        self._exporter_factory_override: Optional[Callable] = None

        # Cached instances (singletons)
        self._storage_instance: Optional[StorageBackend] = None
        self._path_manager_instance: Optional[OutputPathManager] = None

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def paths(self) -> PathConfig:
        """Get path configuration."""
        if self._paths is None:
            self._paths = get_paths()
        return self._paths

    # =========================================================================
    # REGISTRATION (for testing/mocking)
    # =========================================================================

    def register_storage(self, storage: StorageBackend) -> 'Container':
        """
        Register a storage backend override.

        Args:
            storage: Storage backend to use

        Returns:
            Self for chaining
        """
        self._storage_override = storage
        self._storage_instance = None  # Clear cached instance
        return self

    def register_scraper_factory(self, factory: Callable) -> 'Container':
        """
        Register a scraper factory override.

        Args:
            factory: Callable that creates scrapers

        Returns:
            Self for chaining
        """
        self._scraper_factory_override = factory
        return self

    def register_exporter_factory(self, factory: Callable) -> 'Container':
        """
        Register an exporter factory override.

        Args:
            factory: Callable that creates exporters

        Returns:
            Self for chaining
        """
        self._exporter_factory_override = factory
        return self

    # =========================================================================
    # STORAGE
    # =========================================================================

    def storage(self) -> StorageBackend:
        """
        Get storage backend (singleton).

        Returns:
            Storage backend instance
        """
        if self._storage_override:
            return self._storage_override

        if self._storage_instance is None:
            db_path = self.paths.database_path
            self._storage_instance = SQLiteStorage(db_path=str(db_path))
            logger.debug(f"Created SQLite storage at {db_path}")

        return self._storage_instance

    # =========================================================================
    # SCRAPERS
    # =========================================================================

    def scraper_factory(self) -> Callable:
        """
        Get scraper factory function.

        Returns:
            Factory callable
        """
        if self._scraper_factory_override:
            return self._scraper_factory_override

        return ScraperRegistry.get

    def scraper(self, platform: str, config: Optional[Dict[str, Any]] = None) -> BaseScraper:
        """
        Create a scraper for the given platform.

        Args:
            platform: Platform name
            config: Platform-specific configuration

        Returns:
            Scraper instance
        """
        factory = self.scraper_factory()

        # Merge settings with provided config
        merged_config = self._get_platform_config(platform)
        if config:
            merged_config.update(config)

        return factory(platform, merged_config)

    def _get_platform_config(self, platform: str) -> Dict[str, Any]:
        """
        Get configuration for a platform from settings.

        Args:
            platform: Platform name

        Returns:
            Configuration dictionary
        """
        platform_lower = platform.lower()
        platform_settings = getattr(self.settings, platform_lower, None)

        if platform_settings is None:
            return {}

        # Convert Pydantic model to dict
        config = {}

        # Common settings
        if hasattr(platform_settings, 'browser'):
            config['headless'] = platform_settings.browser.headless
            config['user_agent'] = platform_settings.browser.user_agent

        if hasattr(platform_settings, 'proxies') and platform_settings.proxies.enabled:
            config['proxies'] = platform_settings.proxies.urls

        # Platform-specific credentials
        if platform_lower == 'facebook':
            config['email'] = platform_settings.email
            config['password'] = platform_settings.password
            config['cookies_file'] = platform_settings.cookies_file
        elif platform_lower == 'instagram':
            config['username'] = platform_settings.username
            config['password'] = platform_settings.password
            config['session_file'] = platform_settings.session_file
        elif platform_lower == 'twitter':
            config['username'] = platform_settings.username
            config['password'] = platform_settings.password
        elif platform_lower == 'linkedin':
            config['email'] = platform_settings.email
            config['password'] = platform_settings.password

        return config

    # =========================================================================
    # EXPORTERS
    # =========================================================================

    def exporter_factory(self) -> Callable:
        """
        Get exporter factory function.

        Returns:
            Factory callable
        """
        if self._exporter_factory_override:
            return self._exporter_factory_override

        return ExporterRegistry.get

    def exporter(self, format: str) -> BaseExporter:
        """
        Create an exporter for the given format.

        Args:
            format: Export format (json, csv, etc.)

        Returns:
            Exporter instance
        """
        factory = self.exporter_factory()
        return factory(format)

    # =========================================================================
    # PATH MANAGEMENT
    # =========================================================================

    def path_manager(self, base_dir: Optional[str] = None) -> OutputPathManager:
        """
        Get output path manager.

        Args:
            base_dir: Base directory for exports (defaults to paths.exports_dir)

        Returns:
            OutputPathManager instance
        """
        if self._path_manager_instance is None or base_dir:
            exports_dir = base_dir or str(self.paths.exports_dir)
            self._path_manager_instance = OutputPathManager(exports_dir)

        return self._path_manager_instance

    # =========================================================================
    # SERVICES
    # =========================================================================

    def extraction_service(self):
        """
        Create extraction service with all dependencies.

        Returns:
            ExtractionService instance
        """
        # Import here to avoid circular imports
        from ..services.extraction import ExtractionService

        return ExtractionService(
            storage=self.storage(),
            data_dir=str(self.paths.data_dir),
            scraper_factory=self.scraper_factory(),
            exporter_factory=self.exporter_factory(),
            path_manager=self.path_manager()
        )

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def close(self) -> None:
        """Close all resources and clear cached instances."""
        if self._storage_instance:
            # StorageBackend might have a close method
            if hasattr(self._storage_instance, 'close'):
                self._storage_instance.close()
            self._storage_instance = None

        self._path_manager_instance = None
        logger.debug("Container closed")

    def __enter__(self) -> 'Container':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# =========================================================================
# GLOBAL CONTAINER (optional singleton access)
# =========================================================================

_global_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get or create the global container instance.

    Returns:
        Global Container instance
    """
    global _global_container
    if _global_container is None:
        _global_container = Container()
    return _global_container


def reset_container() -> None:
    """
    Reset the global container (useful for testing).
    """
    global _global_container
    if _global_container:
        _global_container.close()
    _global_container = None


def configure_container(
    settings: Optional[Settings] = None,
    paths: Optional[PathConfig] = None
) -> Container:
    """
    Configure and return the global container.

    Args:
        settings: Application settings
        paths: Path configuration

    Returns:
        Configured global Container
    """
    global _global_container
    reset_container()
    _global_container = Container(settings=settings, paths=paths)
    return _global_container
