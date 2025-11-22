"""Tests for rate limiting detection and handling."""

import pytest
from unittest.mock import MagicMock, patch
import time

from src.scrapers.shared.rate_limiting import (
    RateLimitDetector,
    RateLimitHandler,
    FacebookRateLimitDetector,
    InstagramRateLimitDetector,
    TwitterRateLimitDetector,
    LinkedInRateLimitDetector,
    get_rate_limit_detector,
    AdaptiveRateLimiter,
    PlatformRateLimitConfig,
    PLATFORM_CONFIGS,
    get_platform_config,
)


class TestFacebookRateLimitDetector:
    """Tests for Facebook rate limit detection."""

    def test_detects_temporarily_blocked(self):
        """Test detection of temporarily blocked message."""
        mock_page = MagicMock()
        mock_page.url = "https://facebook.com/page"
        mock_page.content.return_value = "you're temporarily blocked from doing this"

        detector = FacebookRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_detects_checkpoint_url(self):
        """Test detection of checkpoint URL."""
        mock_page = MagicMock()
        mock_page.url = "https://facebook.com/checkpoint/123"
        mock_page.content.return_value = "normal content"

        detector = FacebookRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_no_rate_limit(self):
        """Test normal page without rate limiting."""
        mock_page = MagicMock()
        mock_page.url = "https://facebook.com/page"
        mock_page.content.return_value = "normal page content"

        detector = FacebookRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is False

    def test_spanish_indicators(self):
        """Test detection of Spanish rate limit messages."""
        mock_page = MagicMock()
        mock_page.url = "https://facebook.com/page"
        mock_page.content.return_value = "estás bloqueado temporalmente"

        detector = FacebookRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_get_indicators(self):
        """Test that indicators list is returned."""
        detector = FacebookRateLimitDetector()
        indicators = detector.get_indicators()

        assert isinstance(indicators, list)
        assert len(indicators) > 0
        assert "temporarily blocked" in indicators


class TestInstagramRateLimitDetector:
    """Tests for Instagram rate limit detection."""

    def test_detects_action_blocked(self):
        """Test detection of action blocked message."""
        mock_page = MagicMock()
        mock_page.url = "https://instagram.com/p/123"
        mock_page.evaluate.return_value = "action blocked please try again"

        detector = InstagramRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_detects_challenge_url(self):
        """Test detection of challenge URL."""
        mock_page = MagicMock()
        mock_page.url = "https://instagram.com/challenge/123"
        mock_page.evaluate.return_value = "verify your account"

        detector = InstagramRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_no_rate_limit(self):
        """Test normal page without rate limiting."""
        mock_page = MagicMock()
        mock_page.url = "https://instagram.com/p/123"
        mock_page.evaluate.return_value = "normal content with comments"

        detector = InstagramRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is False


class TestTwitterRateLimitDetector:
    """Tests for Twitter rate limit detection."""

    def test_detects_rate_limit_exceeded(self):
        """Test detection of rate limit exceeded message."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = "rate limit exceeded"

        detector = TwitterRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_detects_over_capacity(self):
        """Test detection of over capacity message."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = "twitter is over capacity"

        detector = TwitterRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_no_rate_limit(self):
        """Test normal page without rate limiting."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = "normal tweet content"

        detector = TwitterRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is False


class TestLinkedInRateLimitDetector:
    """Tests for LinkedIn rate limit detection."""

    def test_detects_unusual_activity(self):
        """Test detection of unusual activity message."""
        mock_page = MagicMock()
        mock_page.url = "https://linkedin.com/in/user"
        mock_page.evaluate.return_value = "unusual activity detected"

        detector = LinkedInRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True

    def test_detects_authwall_url(self):
        """Test detection of authwall URL."""
        mock_page = MagicMock()
        mock_page.url = "https://linkedin.com/authwall"
        mock_page.evaluate.return_value = "normal content"

        detector = LinkedInRateLimitDetector()
        assert detector.is_rate_limited(mock_page) is True


class TestRateLimitHandler:
    """Tests for rate limit handling."""

    def test_calculate_backoff(self):
        """Test exponential backoff calculation."""
        handler = RateLimitHandler(base_delay=1.0, max_delay=60.0)

        # First attempt should be around base delay
        backoff_0 = handler.calculate_backoff(0)
        assert 0.75 <= backoff_0 <= 1.25  # With jitter

        # Second attempt should be around 2x
        backoff_1 = handler.calculate_backoff(1)
        assert 1.5 <= backoff_1 <= 2.5

        # Fifth attempt should be capped
        backoff_5 = handler.calculate_backoff(5)
        assert backoff_5 <= 60.0 * 1.25  # Max delay with jitter

    def test_should_retry(self):
        """Test retry logic."""
        handler = RateLimitHandler(max_retries=3)

        # Initially should retry
        assert handler.should_retry() is True

        # Simulate errors
        handler._consecutive_errors = 3
        assert handler.should_retry() is False

    def test_reset(self):
        """Test reset functionality."""
        handler = RateLimitHandler()
        handler._consecutive_errors = 5

        handler.reset()
        assert handler._consecutive_errors == 0
        assert handler.should_retry() is True

    @patch('time.sleep')
    def test_wait_with_backoff(self, mock_sleep):
        """Test wait_with_backoff doesn't block tests."""
        handler = RateLimitHandler(base_delay=1.0)
        handler.wait_with_backoff(0)

        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0][0]
        assert 0.75 <= call_args <= 1.25


class TestGetRateLimitDetector:
    """Tests for detector factory function."""

    def test_get_facebook_detector(self):
        """Test getting Facebook detector."""
        detector = get_rate_limit_detector("facebook")
        assert isinstance(detector, FacebookRateLimitDetector)

    def test_get_instagram_detector(self):
        """Test getting Instagram detector."""
        detector = get_rate_limit_detector("instagram")
        assert isinstance(detector, InstagramRateLimitDetector)

    def test_get_twitter_detector(self):
        """Test getting Twitter detector."""
        detector = get_rate_limit_detector("twitter")
        assert isinstance(detector, TwitterRateLimitDetector)

    def test_get_linkedin_detector(self):
        """Test getting LinkedIn detector."""
        detector = get_rate_limit_detector("linkedin")
        assert isinstance(detector, LinkedInRateLimitDetector)

    def test_case_insensitive(self):
        """Test that platform name is case insensitive."""
        detector1 = get_rate_limit_detector("FACEBOOK")
        detector2 = get_rate_limit_detector("Facebook")

        assert isinstance(detector1, FacebookRateLimitDetector)
        assert isinstance(detector2, FacebookRateLimitDetector)

    def test_invalid_platform(self):
        """Test error for invalid platform."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_rate_limit_detector("invalid_platform")


class TestPlatformRateLimitConfig:
    """Tests for PlatformRateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PlatformRateLimitConfig()
        assert config.base_delay_ms == 2000
        assert config.min_delay_ms == 500
        assert config.max_delay_ms == 30000
        assert config.requests_per_minute == 30
        assert config.burst_limit == 5

    def test_custom_config(self):
        """Test custom configuration."""
        config = PlatformRateLimitConfig(
            base_delay_ms=5000,
            requests_per_minute=10
        )
        assert config.base_delay_ms == 5000
        assert config.requests_per_minute == 10

    def test_platform_configs_exist(self):
        """Test that all expected platforms have configs."""
        assert "instagram" in PLATFORM_CONFIGS
        assert "facebook" in PLATFORM_CONFIGS
        assert "twitter" in PLATFORM_CONFIGS
        assert "linkedin" in PLATFORM_CONFIGS
        assert "google" in PLATFORM_CONFIGS

    def test_instagram_is_strict(self):
        """Test Instagram config reflects its strict limits."""
        config = PLATFORM_CONFIGS["instagram"]
        assert config.requests_per_minute == 15
        assert config.cooldown_seconds == 600

    def test_linkedin_is_strict(self):
        """Test LinkedIn config reflects its strict limits."""
        config = PLATFORM_CONFIGS["linkedin"]
        assert config.requests_per_minute == 10
        assert config.burst_limit == 2


class TestGetPlatformConfig:
    """Tests for get_platform_config function."""

    def test_get_known_platform(self):
        """Test getting config for known platform."""
        config = get_platform_config("instagram")
        assert config.requests_per_minute == 15

    def test_get_unknown_platform(self):
        """Test getting default config for unknown platform."""
        config = get_platform_config("unknown")
        assert config.base_delay_ms == 2000  # Default value

    def test_case_insensitive(self):
        """Test platform name is case insensitive."""
        config1 = get_platform_config("INSTAGRAM")
        config2 = get_platform_config("Instagram")
        assert config1.requests_per_minute == config2.requests_per_minute


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter class."""

    def test_init_with_platform(self):
        """Test initialization with platform name."""
        limiter = AdaptiveRateLimiter("instagram")
        assert limiter.platform == "instagram"
        assert limiter._current_delay_ms == PLATFORM_CONFIGS["instagram"].base_delay_ms

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        custom_config = PlatformRateLimitConfig(base_delay_ms=1000)
        limiter = AdaptiveRateLimiter("test", config=custom_config)
        assert limiter._current_delay_ms == 1000

    def test_current_delay_seconds(self):
        """Test current_delay_seconds property."""
        limiter = AdaptiveRateLimiter("facebook")
        expected = PLATFORM_CONFIGS["facebook"].base_delay_ms / 1000
        assert limiter.current_delay_seconds == expected

    def test_stats(self):
        """Test stats property returns correct data."""
        limiter = AdaptiveRateLimiter("instagram")
        stats = limiter.stats

        assert stats["platform"] == "instagram"
        assert stats["total_requests"] == 0
        assert stats["total_rate_limits"] == 0
        assert stats["consecutive_successes"] == 0

    def test_record_success(self):
        """Test recording successful requests."""
        limiter = AdaptiveRateLimiter("instagram")
        initial_delay = limiter._current_delay_ms

        limiter.record_success()
        assert limiter._consecutive_successes == 1
        assert limiter._consecutive_errors == 0

    def test_record_success_decreases_delay(self):
        """Test that enough successes decrease delay."""
        config = PlatformRateLimitConfig(
            base_delay_ms=2000,
            min_delay_ms=500,
            success_threshold=3,
            decrease_factor=0.8
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        # Record enough successes to trigger decrease
        for _ in range(3):
            limiter.record_success()

        # Delay should have decreased
        expected = int(2000 * 0.8)
        assert limiter._current_delay_ms == expected

    def test_record_success_respects_min_delay(self):
        """Test that delay doesn't go below minimum."""
        config = PlatformRateLimitConfig(
            base_delay_ms=600,
            min_delay_ms=500,
            success_threshold=3,
            decrease_factor=0.5
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        for _ in range(3):
            limiter.record_success()

        # Should not go below min
        assert limiter._current_delay_ms >= config.min_delay_ms

    def test_record_rate_limit(self):
        """Test recording rate limit increases delay."""
        config = PlatformRateLimitConfig(
            base_delay_ms=2000,
            increase_factor=1.5
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        limiter.record_rate_limit()

        assert limiter._consecutive_errors == 1
        assert limiter._consecutive_successes == 0
        assert limiter._total_rate_limits == 1
        expected_delay = int(2000 * 1.5)
        assert limiter._current_delay_ms == expected_delay

    def test_record_rate_limit_respects_max_delay(self):
        """Test that delay doesn't exceed maximum."""
        config = PlatformRateLimitConfig(
            base_delay_ms=20000,
            max_delay_ms=30000,
            increase_factor=2.0
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        limiter.record_rate_limit()

        # Should not exceed max
        assert limiter._current_delay_ms <= config.max_delay_ms

    def test_record_error(self):
        """Test recording non-rate-limit errors."""
        limiter = AdaptiveRateLimiter("instagram")

        limiter.record_error()
        assert limiter._consecutive_errors == 1

    def test_should_continue(self):
        """Test should_continue based on consecutive errors."""
        config = PlatformRateLimitConfig(max_consecutive_errors=3)
        limiter = AdaptiveRateLimiter("test", config=config)

        assert limiter.should_continue() is True

        # Simulate errors
        limiter._consecutive_errors = 3
        assert limiter.should_continue() is False

    def test_reset(self):
        """Test reset restores initial state."""
        limiter = AdaptiveRateLimiter("instagram")

        # Modify state
        limiter._current_delay_ms = 10000
        limiter._consecutive_errors = 5
        limiter._consecutive_successes = 10
        limiter._request_times = [1, 2, 3]

        limiter.reset()

        assert limiter._current_delay_ms == PLATFORM_CONFIGS["instagram"].base_delay_ms
        assert limiter._consecutive_errors == 0
        assert limiter._consecutive_successes == 0
        assert len(limiter._request_times) == 0

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_basic(self, mock_time, mock_sleep):
        """Test basic wait functionality."""
        mock_time.return_value = 1000.0

        config = PlatformRateLimitConfig(base_delay_ms=1000)
        limiter = AdaptiveRateLimiter("test", config=config)

        delay = limiter.wait()

        # Should have slept
        mock_sleep.assert_called()
        # Should have recorded request
        assert limiter._total_requests == 1
        assert len(limiter._request_times) == 1

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_tracks_requests(self, mock_time, mock_sleep):
        """Test that wait tracks multiple requests."""
        mock_time.return_value = 1000.0

        config = PlatformRateLimitConfig(base_delay_ms=100)
        limiter = AdaptiveRateLimiter("test", config=config)

        limiter.wait()
        limiter.wait()
        limiter.wait()

        assert limiter._total_requests == 3
        assert len(limiter._request_times) == 3

    def test_clean_old_requests(self):
        """Test cleaning of old request times."""
        limiter = AdaptiveRateLimiter("instagram")

        # Add old requests
        old_time = time.time() - 120  # 2 minutes ago
        limiter._request_times = [old_time, old_time + 10]

        # Clean should remove them
        limiter._clean_old_requests()
        assert len(limiter._request_times) == 0

    def test_cooldown_tracking(self):
        """Test cooldown period tracking."""
        config = PlatformRateLimitConfig(cooldown_seconds=10)
        limiter = AdaptiveRateLimiter("test", config=config)

        # Initially not in cooldown
        assert limiter._is_in_cooldown() is False

        # Record rate limit
        limiter.record_rate_limit()

        # Now in cooldown
        assert limiter._is_in_cooldown() is True
        assert limiter._get_cooldown_remaining() > 0


class TestAdaptiveRateLimiterIntegration:
    """Integration tests for AdaptiveRateLimiter."""

    def test_adaptive_behavior_sequence(self):
        """Test a realistic sequence of operations."""
        config = PlatformRateLimitConfig(
            base_delay_ms=1000,
            min_delay_ms=500,
            max_delay_ms=10000,
            success_threshold=5,
            increase_factor=2.0,
            decrease_factor=0.8
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        # Initial state
        assert limiter._current_delay_ms == 1000

        # Hit rate limit
        limiter.record_rate_limit()
        assert limiter._current_delay_ms == 2000

        # Recover with successes
        for _ in range(5):
            limiter.record_success()

        # Should decrease
        assert limiter._current_delay_ms < 2000

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        limiter = AdaptiveRateLimiter("instagram")

        limiter.record_success()
        limiter.record_success()
        limiter.record_rate_limit()
        limiter.record_success()

        stats = limiter.stats
        assert stats["total_rate_limits"] == 1
        assert stats["consecutive_successes"] == 1
        assert stats["consecutive_errors"] == 0

    def test_multiple_rate_limits_increase_delay(self):
        """Test that multiple rate limits compound delay increase."""
        config = PlatformRateLimitConfig(
            base_delay_ms=1000,
            max_delay_ms=100000,
            increase_factor=2.0
        )
        limiter = AdaptiveRateLimiter("test", config=config)

        limiter.record_rate_limit()
        delay1 = limiter._current_delay_ms
        assert delay1 == 2000

        limiter.record_rate_limit()
        delay2 = limiter._current_delay_ms
        assert delay2 == 4000

        limiter.record_rate_limit()
        delay3 = limiter._current_delay_ms
        assert delay3 == 8000
