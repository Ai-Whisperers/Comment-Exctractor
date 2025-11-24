"""Application settings and configuration."""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.security import SensitiveFilter
from ..core.exceptions import ConfigurationError
from .paths import get_paths

logger = logging.getLogger(__name__)


# Validation constants
MIN_REQUESTS_PER_MINUTE = 1
MAX_REQUESTS_PER_MINUTE = 100
MIN_RETRIES = 0
MAX_RETRIES = 10
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 300


class BrowserSettings(BaseModel):
    """Browser automation settings."""
    headless: bool = False
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=800, ge=480, le=2160)
    timeout_seconds: int = Field(default=30, ge=MIN_TIMEOUT_SECONDS, le=MAX_TIMEOUT_SECONDS)
    user_agent: Optional[str] = None

    @field_validator('user_agent')
    @classmethod
    def validate_user_agent(cls, v: Optional[str]) -> Optional[str]:
        """Validate user agent string."""
        if v is not None and len(v) > 500:
            raise ValueError("User agent string too long (max 500 characters)")
        return v


class ProxySettings(BaseModel):
    """Proxy configuration settings."""
    enabled: bool = False
    urls: List[str] = Field(default_factory=list)  # List of proxy URLs
    rotate_on_error: bool = True

    @field_validator('urls')
    @classmethod
    def validate_proxy_urls(cls, v: List[str]) -> List[str]:
        """Validate proxy URL formats."""
        for url in v:
            if not url.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
                raise ValueError(f"Invalid proxy URL format: {url}. Must start with http://, https://, socks4://, or socks5://")
        return v


class ScraperSettings(BaseModel):
    """Settings for a specific scraper."""
    enabled: bool = True
    requests_per_minute: int = Field(default=30, ge=MIN_REQUESTS_PER_MINUTE, le=MAX_REQUESTS_PER_MINUTE)
    max_retries: int = Field(default=3, ge=MIN_RETRIES, le=MAX_RETRIES)
    proxies: ProxySettings = Field(default_factory=ProxySettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    request_timeout: int = Field(default=30, ge=MIN_TIMEOUT_SECONDS, le=MAX_TIMEOUT_SECONDS)

    @model_validator(mode='after')
    def validate_scraper_settings(self) -> 'ScraperSettings':
        """Cross-validate scraper settings."""
        # Proxy validation: if proxies enabled, must have at least one URL
        if self.proxies.enabled and len(self.proxies.urls) == 0:
            raise ValueError("Proxies are enabled but no proxy URLs configured")
        return self


class FacebookSettings(ScraperSettings):
    """Facebook-specific settings."""
    email: Optional[str] = None
    password: Optional[str] = None
    cookies_file: Optional[str] = None
    pages_per_request: int = Field(default=10, ge=1, le=50)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v is not None and v != "":
            if '@' not in v or '.' not in v.split('@')[-1]:
                raise ValueError("Invalid email format")
        return v

    @field_validator('cookies_file')
    @classmethod
    def validate_cookies_file(cls, v: Optional[str]) -> Optional[str]:
        """Validate cookies file path has no traversal."""
        if v is not None and '..' in v:
            raise ValueError("Cookies file path cannot contain path traversal '..'")
        return v

    @model_validator(mode='after')
    def validate_facebook_auth(self) -> 'FacebookSettings':
        """Validate Facebook authentication configuration."""
        if self.enabled:
            has_creds = self.email and self.password
            has_cookies = self.cookies_file is not None
            # It's okay if neither are set - will use browser profile
        return self


class InstagramSettings(ScraperSettings):
    """Instagram-specific settings."""
    username: Optional[str] = None
    password: Optional[str] = None
    session_file: Optional[str] = None
    requests_per_minute: int = Field(default=15, ge=MIN_REQUESTS_PER_MINUTE, le=MAX_REQUESTS_PER_MINUTE)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate Instagram username format."""
        if v is not None and v != "":
            # Instagram usernames: alphanumeric, underscores, periods, max 30 chars
            if len(v) > 30:
                raise ValueError("Instagram username cannot exceed 30 characters")
            import re
            if not re.match(r'^[a-zA-Z0-9_.]+$', v):
                raise ValueError("Instagram username can only contain letters, numbers, underscores, and periods")
        return v

    @field_validator('session_file')
    @classmethod
    def validate_session_file(cls, v: Optional[str]) -> Optional[str]:
        """Validate session file path has no traversal."""
        if v is not None and '..' in v:
            raise ValueError("Session file path cannot contain path traversal '..'")
        return v


class TwitterSettings(ScraperSettings):
    """Twitter-specific settings."""
    username: Optional[str] = None
    password: Optional[str] = None
    # Google OAuth credentials (alternative to Twitter credentials)
    google_email: Optional[str] = None
    google_password: Optional[str] = None
    use_google_auth: bool = False
    requests_per_minute: int = Field(default=20, ge=MIN_REQUESTS_PER_MINUTE, le=MAX_REQUESTS_PER_MINUTE)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate Twitter username format."""
        if v is not None and v != "":
            # Twitter handles: max 15 chars
            if len(v) > 15:
                raise ValueError("Twitter username cannot exceed 15 characters")
        return v

    @field_validator('google_email')
    @classmethod
    def validate_google_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation for Google account."""
        if v is not None and v != "":
            if '@' not in v or '.' not in v.split('@')[-1]:
                raise ValueError("Invalid Google email format")
        return v


class LinkedInSettings(ScraperSettings):
    """LinkedIn-specific settings."""
    email: Optional[str] = None
    password: Optional[str] = None
    requests_per_minute: int = Field(default=10, ge=MIN_REQUESTS_PER_MINUTE, le=MAX_REQUESTS_PER_MINUTE)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v is not None and v != "":
            if '@' not in v or '.' not in v.split('@')[-1]:
                raise ValueError("Invalid email format")
        return v




class Settings(BaseSettings):
    """Main application settings."""

    # General
    app_name: str = "Comment Extractor"
    debug: bool = False
    log_level: str = "INFO"

    # Paths - now use centralized path config
    @property
    def _path_config(self):
        return get_paths()

    data_dir: str = "data"
    exports_dir: str = "data/exports"
    logs_dir: str = "logs"

    # Database
    database_path: str = "data/extractor.db"

    def get_database_path(self) -> str:
        """Get database path from centralized config."""
        return str(self._path_config.database_path)

    def get_exports_dir(self) -> str:
        """Get exports directory from centralized config."""
        return str(self._path_config.exports_dir)

    # Extraction defaults
    default_max_posts: int = 100
    default_export_format: str = "json"

    # Platform settings
    facebook: FacebookSettings = Field(default_factory=FacebookSettings)
    instagram: InstagramSettings = Field(default_factory=InstagramSettings)
    twitter: TwitterSettings = Field(default_factory=TwitterSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",  # Allow extra fields (e.g., future platforms like Twitter)
    )

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator('default_export_format')
    @classmethod
    def validate_export_format(cls, v: str) -> str:
        """Validate export format."""
        valid_formats = {'json', 'csv', 'excel'}
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid export format: {v}. Must be one of: {', '.join(valid_formats)}")
        return v.lower()

    @field_validator('default_max_posts')
    @classmethod
    def validate_max_posts(cls, v: int) -> int:
        """Validate max posts."""
        if v < 1:
            raise ValueError("default_max_posts must be at least 1")
        if v > 10000:
            raise ValueError("default_max_posts cannot exceed 10000")
        return v

    @field_validator('data_dir', 'exports_dir', 'logs_dir', 'database_path')
    @classmethod
    def validate_paths(cls, v: str) -> str:
        """Validate paths don't contain traversal."""
        if '..' in v:
            raise ValueError(f"Path cannot contain path traversal '..': {v}")
        return v

    @model_validator(mode='after')
    def validate_settings(self) -> 'Settings':
        """Cross-validate all settings."""
        # Ensure exports_dir is under data_dir or a valid path
        exports_path = Path(self.exports_dir)
        data_path = Path(self.data_dir)

        # Ensure database_path ends with .db
        if not self.database_path.endswith('.db'):
            logger.warning(f"Database path '{self.database_path}' should end with .db extension")

        return self

    def validate_platform_config(self, platform: str) -> List[str]:
        """
        Validate configuration for a specific platform.

        Args:
            platform: Platform name

        Returns:
            List of validation warnings (empty if all good)
        """
        warnings: List[str] = []
        platform_lower = platform.lower()

        if platform_lower == "instagram":
            if not self.instagram.enabled:
                warnings.append("Instagram is disabled")
            elif not self.instagram.username or not self.instagram.password:
                warnings.append("Instagram credentials not configured. Set EXTRACTOR_INSTAGRAM__USERNAME and EXTRACTOR_INSTAGRAM__PASSWORD in .env")

        elif platform_lower == "facebook":
            if not self.facebook.enabled:
                warnings.append("Facebook is disabled")
            elif not self.facebook.email or not self.facebook.password:
                warnings.append("Facebook credentials not configured. Set EXTRACTOR_FACEBOOK__EMAIL and EXTRACTOR_FACEBOOK__PASSWORD in .env")

        elif platform_lower == "twitter":
            if not self.twitter.enabled:
                warnings.append("Twitter is disabled")
            elif not self.twitter.username or not self.twitter.password:
                warnings.append("Twitter credentials not configured. Set EXTRACTOR_TWITTER__USERNAME and EXTRACTOR_TWITTER__PASSWORD in .env")

        elif platform_lower == "linkedin":
            if not self.linkedin.enabled:
                warnings.append("LinkedIn is disabled")
            elif not self.linkedin.email or not self.linkedin.password:
                warnings.append("LinkedIn credentials not configured. Set EXTRACTOR_LINKEDIN__EMAIL and EXTRACTOR_LINKEDIN__PASSWORD in .env")

        return warnings

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.data_dir, self.exports_dir, self.logs_dir]:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")

    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validate all settings and return any warnings/errors.

        Returns:
            Dictionary with platform names as keys and list of warnings as values
        """
        results: Dict[str, List[str]] = {}

        for platform in ['instagram', 'facebook', 'twitter', 'linkedin']:
            warnings = self.validate_platform_config(platform)
            if warnings:
                results[platform] = warnings

        return results

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """
        Get configuration for a specific platform.

        Args:
            platform: Platform name

        Returns:
            Platform configuration dictionary
        """
        platform_lower = platform.lower()

        paths = get_paths()

        if platform_lower == "facebook":
            # Check for browser profile override (for parallel execution)
            browser_profile = os.environ.get(
                "BROWSER_PROFILE_OVERRIDE",
                str(paths.browser_profile_path("facebook"))
            )
            config = {
                "cookies": self.facebook.cookies_file,
                "pages": self.facebook.pages_per_request,
                "email": self.facebook.email,
                "password": self.facebook.password,
                "browser_profile": browser_profile,
                "headless": False,
            }
            # Add proxies if enabled
            if self.facebook.proxies.enabled:
                config["proxies"] = self.facebook.proxies.urls
            return config
        elif platform_lower == "instagram":
            config = {
                "username": self.instagram.username,
                "password": self.instagram.password,
                "session_file": self.instagram.session_file,
            }
            # Add proxies if enabled
            if self.instagram.proxies.enabled:
                config["proxies"] = self.instagram.proxies.urls
            return config

        elif platform_lower == "twitter":
            config = {
                "credentials": {
                    "username": self.twitter.username,
                    "password": self.twitter.password,
                },
                "google_auth": {
                    "enabled": self.twitter.use_google_auth,
                    "email": self.twitter.google_email,
                    "password": self.twitter.google_password,
                },
                "browser": {
                    "headless": False,
                    "profile_dir": str(paths.browser_profile_path("twitter")),
                }
            }
            if self.twitter.proxies.enabled:
                config["proxies"] = self.twitter.proxies.urls
            return config

        elif platform_lower == "linkedin":
            config = {
                "credentials": {
                    "email": self.linkedin.email,
                    "password": self.linkedin.password,
                },
                "browser": {
                    "headless": False,
                    "profile_dir": str(paths.browser_profile_path("linkedin")),
                }
            }
            if self.linkedin.proxies.enabled:
                config["proxies"] = self.linkedin.proxies.urls
            return config

        return {}

    def setup_logging(self):
        """Configure logging based on settings."""
        log_dir = Path(self.logs_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Detailed format for file logging
        file_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | "
            "%(funcName)s | %(message)s"
        )

        # Concise format for console
        console_format = "%(asctime)s | %(levelname)-8s | %(message)s"

        # Create formatters
        file_formatter = logging.Formatter(
            file_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_formatter = logging.Formatter(
            console_format,
            datefmt="%H:%M:%S"
        )

        # Configure handlers
        file_handler = logging.FileHandler(log_dir / "extractor.log")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_handler.addFilter(SensitiveFilter())  # Mask sensitive data

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, self.log_level.upper()))
        console_handler.addFilter(SensitiveFilter())  # Mask sensitive data

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to allow all messages through
        root_logger.handlers = []  # Clear existing handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Reduce noise from third-party libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

        logger.info(f"Logging initialized: console={self.log_level}, file=DEBUG")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()


# Example .env file content
ENV_EXAMPLE = """
# Comment Extractor Configuration

# General
EXTRACTOR_DEBUG=false
EXTRACTOR_LOG_LEVEL=INFO

# Paths
EXTRACTOR_DATA_DIR=data
EXTRACTOR_EXPORTS_DIR=data/exports

# Database
EXTRACTOR_DATABASE_PATH=data/extractor.db

# Extraction defaults
EXTRACTOR_DEFAULT_MAX_POSTS=100
EXTRACTOR_DEFAULT_EXPORT_FORMAT=json

# Facebook settings (Playwright-based)
EXTRACTOR_FACEBOOK__ENABLED=true
EXTRACTOR_FACEBOOK__EMAIL=
EXTRACTOR_FACEBOOK__PASSWORD=
EXTRACTOR_FACEBOOK__COOKIES_FILE=
EXTRACTOR_FACEBOOK__PAGES_PER_REQUEST=10
EXTRACTOR_FACEBOOK__REQUESTS_PER_MINUTE=20

# Instagram settings (Playwright-based)
EXTRACTOR_INSTAGRAM__ENABLED=true
EXTRACTOR_INSTAGRAM__USERNAME=
EXTRACTOR_INSTAGRAM__PASSWORD=
EXTRACTOR_INSTAGRAM__SESSION_FILE=
EXTRACTOR_INSTAGRAM__REQUESTS_PER_MINUTE=5

# Proxy Configuration (Optional - for IP rotation)
# Format: protocol://user:pass@host:port or protocol://host:port
# EXTRACTOR_INSTAGRAM__PROXIES__ENABLED=true
# EXTRACTOR_INSTAGRAM__PROXIES__URLS=["http://proxy1:8080","http://proxy2:8080"]
# EXTRACTOR_FACEBOOK__PROXIES__ENABLED=true
# EXTRACTOR_FACEBOOK__PROXIES__URLS=["http://proxy1:8080"]
"""
