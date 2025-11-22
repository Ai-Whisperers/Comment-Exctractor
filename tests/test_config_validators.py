"""Tests for Pydantic configuration validators."""

import pytest
from pydantic import ValidationError

from src.config.settings import (
    BrowserSettings,
    ProxySettings,
    ScraperSettings,
    FacebookSettings,
    InstagramSettings,
    TwitterSettings,
    LinkedInSettings,
    Settings,
    MIN_REQUESTS_PER_MINUTE,
    MAX_REQUESTS_PER_MINUTE,
    MIN_RETRIES,
    MAX_RETRIES,
    MIN_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
)


class TestBrowserSettings:
    """Tests for BrowserSettings validators."""

    def test_default_values(self):
        """Test default browser settings."""
        settings = BrowserSettings()
        assert settings.headless is False
        assert settings.viewport_width == 1280
        assert settings.viewport_height == 800
        assert settings.timeout_seconds == 30
        assert settings.user_agent is None

    def test_viewport_width_bounds(self):
        """Test viewport width validation."""
        # Valid values
        BrowserSettings(viewport_width=320)
        BrowserSettings(viewport_width=3840)

        # Too small
        with pytest.raises(ValidationError) as exc:
            BrowserSettings(viewport_width=100)
        assert "viewport_width" in str(exc.value)

        # Too large
        with pytest.raises(ValidationError) as exc:
            BrowserSettings(viewport_width=5000)
        assert "viewport_width" in str(exc.value)

    def test_viewport_height_bounds(self):
        """Test viewport height validation."""
        # Valid values
        BrowserSettings(viewport_height=480)
        BrowserSettings(viewport_height=2160)

        # Too small
        with pytest.raises(ValidationError) as exc:
            BrowserSettings(viewport_height=100)
        assert "viewport_height" in str(exc.value)

    def test_timeout_bounds(self):
        """Test timeout validation."""
        BrowserSettings(timeout_seconds=MIN_TIMEOUT_SECONDS)
        BrowserSettings(timeout_seconds=MAX_TIMEOUT_SECONDS)

        with pytest.raises(ValidationError):
            BrowserSettings(timeout_seconds=0)

        with pytest.raises(ValidationError):
            BrowserSettings(timeout_seconds=500)

    def test_user_agent_too_long(self):
        """Test user agent length validation."""
        # Valid
        BrowserSettings(user_agent="x" * 500)

        # Too long
        with pytest.raises(ValidationError) as exc:
            BrowserSettings(user_agent="x" * 501)
        assert "too long" in str(exc.value).lower()


class TestProxySettings:
    """Tests for ProxySettings validators."""

    def test_default_values(self):
        """Test default proxy settings."""
        settings = ProxySettings()
        assert settings.enabled is False
        assert settings.urls == []
        assert settings.rotate_on_error is True

    def test_valid_proxy_urls(self):
        """Test valid proxy URL formats."""
        settings = ProxySettings(
            enabled=True,
            urls=[
                "http://proxy.example.com:8080",
                "https://secure.proxy.com:443",
                "socks5://user:pass@socks.proxy.com:1080",
                "socks4://socks4.proxy.com:1080",
            ]
        )
        assert len(settings.urls) == 4

    def test_invalid_proxy_url_format(self):
        """Test invalid proxy URL format validation."""
        with pytest.raises(ValidationError) as exc:
            ProxySettings(urls=["ftp://invalid.proxy.com:21"])
        assert "Invalid proxy URL format" in str(exc.value)

    def test_multiple_invalid_urls(self):
        """Test validation catches first invalid URL."""
        with pytest.raises(ValidationError):
            ProxySettings(urls=[
                "http://valid.proxy.com:8080",
                "invalid://bad.proxy.com:21"
            ])


class TestScraperSettings:
    """Tests for ScraperSettings validators."""

    def test_default_values(self):
        """Test default scraper settings."""
        settings = ScraperSettings()
        assert settings.enabled is True
        assert settings.requests_per_minute == 30
        assert settings.max_retries == 3
        assert settings.request_timeout == 30

    def test_requests_per_minute_bounds(self):
        """Test requests_per_minute validation."""
        ScraperSettings(requests_per_minute=MIN_REQUESTS_PER_MINUTE)
        ScraperSettings(requests_per_minute=MAX_REQUESTS_PER_MINUTE)

        with pytest.raises(ValidationError):
            ScraperSettings(requests_per_minute=0)

        with pytest.raises(ValidationError):
            ScraperSettings(requests_per_minute=101)

    def test_max_retries_bounds(self):
        """Test max_retries validation."""
        ScraperSettings(max_retries=MIN_RETRIES)
        ScraperSettings(max_retries=MAX_RETRIES)

        with pytest.raises(ValidationError):
            ScraperSettings(max_retries=-1)

        with pytest.raises(ValidationError):
            ScraperSettings(max_retries=11)

    def test_proxy_enabled_without_urls(self):
        """Test validation fails when proxies enabled but no URLs."""
        with pytest.raises(ValidationError) as exc:
            ScraperSettings(
                proxies=ProxySettings(enabled=True, urls=[])
            )
        assert "no proxy URLs configured" in str(exc.value)

    def test_proxy_enabled_with_urls(self):
        """Test valid proxy configuration."""
        settings = ScraperSettings(
            proxies=ProxySettings(
                enabled=True,
                urls=["http://proxy.com:8080"]
            )
        )
        assert settings.proxies.enabled is True


class TestFacebookSettings:
    """Tests for FacebookSettings validators."""

    def test_default_values(self):
        """Test default Facebook settings."""
        settings = FacebookSettings()
        assert settings.email is None
        assert settings.password is None
        assert settings.pages_per_request == 10

    def test_pages_per_request_bounds(self):
        """Test pages_per_request validation."""
        FacebookSettings(pages_per_request=1)
        FacebookSettings(pages_per_request=50)

        with pytest.raises(ValidationError):
            FacebookSettings(pages_per_request=0)

        with pytest.raises(ValidationError):
            FacebookSettings(pages_per_request=51)

    def test_valid_email(self):
        """Test valid email formats."""
        FacebookSettings(email="user@example.com")
        FacebookSettings(email="user.name@subdomain.example.co.uk")

    def test_invalid_email(self):
        """Test invalid email format validation."""
        with pytest.raises(ValidationError) as exc:
            FacebookSettings(email="invalid-email")
        assert "Invalid email format" in str(exc.value)

    def test_email_without_domain(self):
        """Test email without proper domain."""
        with pytest.raises(ValidationError):
            FacebookSettings(email="user@invalid")

    def test_cookies_file_path_traversal(self):
        """Test cookies file path traversal protection."""
        # Valid path
        FacebookSettings(cookies_file="/path/to/cookies.json")

        # Path traversal
        with pytest.raises(ValidationError) as exc:
            FacebookSettings(cookies_file="../../../etc/passwd")
        assert "path traversal" in str(exc.value).lower()


class TestInstagramSettings:
    """Tests for InstagramSettings validators."""

    def test_default_values(self):
        """Test default Instagram settings."""
        settings = InstagramSettings()
        assert settings.username is None
        assert settings.requests_per_minute == 15

    def test_valid_username(self):
        """Test valid Instagram username formats."""
        InstagramSettings(username="user_name")
        InstagramSettings(username="user.name")
        InstagramSettings(username="username123")
        InstagramSettings(username="a" * 30)

    def test_username_too_long(self):
        """Test Instagram username length validation."""
        with pytest.raises(ValidationError) as exc:
            InstagramSettings(username="a" * 31)
        assert "30 characters" in str(exc.value)

    def test_invalid_username_characters(self):
        """Test Instagram username character validation."""
        with pytest.raises(ValidationError) as exc:
            InstagramSettings(username="user@name")
        assert "letters, numbers, underscores, and periods" in str(exc.value)

    def test_username_with_hyphen(self):
        """Test Instagram username rejects hyphens."""
        with pytest.raises(ValidationError):
            InstagramSettings(username="user-name")

    def test_session_file_path_traversal(self):
        """Test session file path traversal protection."""
        with pytest.raises(ValidationError) as exc:
            InstagramSettings(session_file="../../../private/session.json")
        assert "path traversal" in str(exc.value).lower()


class TestTwitterSettings:
    """Tests for TwitterSettings validators."""

    def test_default_values(self):
        """Test default Twitter settings."""
        settings = TwitterSettings()
        assert settings.username is None
        assert settings.requests_per_minute == 20

    def test_valid_username(self):
        """Test valid Twitter username."""
        TwitterSettings(username="user")
        TwitterSettings(username="a" * 15)

    def test_username_too_long(self):
        """Test Twitter username length validation."""
        with pytest.raises(ValidationError) as exc:
            TwitterSettings(username="a" * 16)
        assert "15 characters" in str(exc.value)


class TestLinkedInSettings:
    """Tests for LinkedInSettings validators."""

    def test_default_values(self):
        """Test default LinkedIn settings."""
        settings = LinkedInSettings()
        assert settings.email is None
        assert settings.requests_per_minute == 10

    def test_valid_email(self):
        """Test valid email formats."""
        LinkedInSettings(email="user@company.com")

    def test_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValidationError):
            LinkedInSettings(email="not-an-email")


class TestSettingsValidators:
    """Tests for main Settings validators."""

    def test_default_values(self):
        """Test default Settings values."""
        settings = Settings()
        assert settings.app_name == "Comment Extractor"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_valid_log_levels(self):
        """Test valid log level values."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            settings = Settings(log_level=level)
            assert settings.log_level == level

    def test_invalid_log_level(self):
        """Test invalid log level validation."""
        with pytest.raises(ValidationError) as exc:
            Settings(log_level="INVALID")
        assert "Invalid log level" in str(exc.value)

    def test_log_level_case_insensitive(self):
        """Test log level is case insensitive and normalized."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

    def test_valid_export_formats(self):
        """Test valid export format values."""
        for fmt in ['json', 'csv', 'excel']:
            settings = Settings(default_export_format=fmt)
            assert settings.default_export_format == fmt

    def test_invalid_export_format(self):
        """Test invalid export format validation."""
        with pytest.raises(ValidationError) as exc:
            Settings(default_export_format="xml")
        assert "Invalid export format" in str(exc.value)

    def test_export_format_case_insensitive(self):
        """Test export format is case insensitive and normalized."""
        settings = Settings(default_export_format="JSON")
        assert settings.default_export_format == "json"

    def test_max_posts_bounds(self):
        """Test default_max_posts validation."""
        Settings(default_max_posts=1)
        Settings(default_max_posts=10000)

        with pytest.raises(ValidationError) as exc:
            Settings(default_max_posts=0)
        assert "at least 1" in str(exc.value)

        with pytest.raises(ValidationError) as exc:
            Settings(default_max_posts=10001)
        assert "exceed 10000" in str(exc.value)

    def test_path_traversal_in_data_dir(self):
        """Test data_dir path traversal protection."""
        with pytest.raises(ValidationError) as exc:
            Settings(data_dir="../../../etc")
        assert "path traversal" in str(exc.value).lower()

    def test_path_traversal_in_exports_dir(self):
        """Test exports_dir path traversal protection."""
        with pytest.raises(ValidationError) as exc:
            Settings(exports_dir="../../../tmp")
        assert "path traversal" in str(exc.value).lower()

    def test_path_traversal_in_logs_dir(self):
        """Test logs_dir path traversal protection."""
        with pytest.raises(ValidationError) as exc:
            Settings(logs_dir="../../../var/log")
        assert "path traversal" in str(exc.value).lower()

    def test_path_traversal_in_database_path(self):
        """Test database_path path traversal protection."""
        with pytest.raises(ValidationError) as exc:
            Settings(database_path="../../../data/extractor.db")
        assert "path traversal" in str(exc.value).lower()


class TestValidatePlatformConfig:
    """Tests for validate_platform_config method."""

    def test_instagram_without_credentials(self):
        """Test Instagram validation without credentials."""
        # Explicitly set empty credentials to override any env vars
        settings = Settings(
            instagram=InstagramSettings(
                username=None,
                password=None
            )
        )
        warnings = settings.validate_platform_config("instagram")
        assert len(warnings) == 1
        assert "credentials not configured" in warnings[0]

    def test_instagram_with_credentials(self):
        """Test Instagram validation with credentials."""
        settings = Settings(
            instagram=InstagramSettings(
                username="testuser",
                password="testpass"
            )
        )
        warnings = settings.validate_platform_config("instagram")
        assert len(warnings) == 0

    def test_instagram_disabled(self):
        """Test Instagram validation when disabled."""
        settings = Settings(
            instagram=InstagramSettings(enabled=False)
        )
        warnings = settings.validate_platform_config("instagram")
        assert len(warnings) == 1
        assert "disabled" in warnings[0]

    def test_facebook_without_credentials(self):
        """Test Facebook validation without credentials."""
        # Explicitly set empty credentials to override any env vars
        settings = Settings(
            facebook=FacebookSettings(
                email=None,
                password=None
            )
        )
        warnings = settings.validate_platform_config("facebook")
        assert len(warnings) == 1
        assert "credentials not configured" in warnings[0]

    def test_validate_all_with_no_credentials(self):
        """Test validate_all returns warnings for platforms without credentials."""
        # Create settings with explicitly empty credentials
        settings = Settings(
            instagram=InstagramSettings(username=None, password=None),
            facebook=FacebookSettings(email=None, password=None),
            twitter=TwitterSettings(username=None, password=None),
            linkedin=LinkedInSettings(email=None, password=None)
        )
        results = settings.validate_all()

        # All platforms should have warnings (no credentials)
        assert "instagram" in results
        assert "facebook" in results
        assert "twitter" in results
        assert "linkedin" in results

    def test_validate_all_with_all_credentials(self):
        """Test validate_all returns no warnings when all configured."""
        settings = Settings(
            instagram=InstagramSettings(username="user", password="pass"),
            facebook=FacebookSettings(email="user@test.com", password="pass"),
            twitter=TwitterSettings(username="user", password="pass"),
            linkedin=LinkedInSettings(email="user@test.com", password="pass")
        )
        results = settings.validate_all()
        assert len(results) == 0


class TestCrossFieldValidation:
    """Tests for cross-field validation scenarios."""

    def test_scraper_settings_with_full_config(self):
        """Test fully configured scraper settings."""
        settings = ScraperSettings(
            enabled=True,
            requests_per_minute=50,
            max_retries=5,
            request_timeout=60,
            browser=BrowserSettings(
                headless=True,
                viewport_width=1920,
                viewport_height=1080,
                timeout_seconds=45
            ),
            proxies=ProxySettings(
                enabled=True,
                urls=["http://proxy1.com:8080", "http://proxy2.com:8080"]
            )
        )
        assert settings.requests_per_minute == 50
        assert settings.browser.headless is True
        assert len(settings.proxies.urls) == 2

    def test_nested_model_validation(self):
        """Test that nested model validation works correctly."""
        # Invalid browser settings should fail
        with pytest.raises(ValidationError):
            ScraperSettings(
                browser=BrowserSettings(viewport_width=10)  # Too small
            )

    def test_settings_with_platform_configs(self):
        """Test Settings with all platform configurations."""
        settings = Settings(
            instagram=InstagramSettings(
                username="testuser",
                password="testpass",
                requests_per_minute=10
            ),
            facebook=FacebookSettings(
                email="test@example.com",
                password="testpass",
                pages_per_request=20
            ),
            twitter=TwitterSettings(
                username="twitteruser",
                password="testpass"
            ),
            linkedin=LinkedInSettings(
                email="linkedin@company.com",
                password="testpass"
            )
        )

        # Validate all should pass
        results = settings.validate_all()
        assert len(results) == 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_username_is_allowed(self):
        """Test that empty string username is allowed."""
        # Empty string should be allowed (not validated)
        settings = InstagramSettings(username="")
        assert settings.username == ""

    def test_none_values_are_allowed(self):
        """Test that None values are allowed for optional fields."""
        settings = FacebookSettings(email=None, password=None)
        assert settings.email is None
        assert settings.password is None

    def test_zero_retries_allowed(self):
        """Test that zero retries is a valid configuration."""
        settings = ScraperSettings(max_retries=0)
        assert settings.max_retries == 0

    def test_minimum_values(self):
        """Test all minimum values are valid."""
        settings = ScraperSettings(
            requests_per_minute=1,
            max_retries=0,
            request_timeout=1
        )
        assert settings.requests_per_minute == 1
        assert settings.max_retries == 0
        assert settings.request_timeout == 1

    def test_maximum_values(self):
        """Test all maximum values are valid."""
        settings = ScraperSettings(
            requests_per_minute=100,
            max_retries=10,
            request_timeout=300
        )
        assert settings.requests_per_minute == 100
        assert settings.max_retries == 10
        assert settings.request_timeout == 300
