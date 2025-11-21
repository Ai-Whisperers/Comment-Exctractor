# Error Handling & Retry Strategies

## Error Classification

### Error Types

```python
# src/utils/exceptions.py

class ExtractorError(Exception):
    """Base exception for extractor errors."""
    pass

class RateLimitError(ExtractorError):
    """Platform rate limit exceeded."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after

class AuthenticationError(ExtractorError):
    """Invalid or expired credentials."""
    pass

class PlatformError(ExtractorError):
    """Platform-specific error (API changed, down, etc.)."""
    pass

class ValidationError(ExtractorError):
    """Invalid input data."""
    pass

class NotFoundError(ExtractorError):
    """Resource not found (account, post, etc.)."""
    pass

class QuotaExceededError(ExtractorError):
    """Monthly/daily quota exceeded."""
    pass

class TemporaryError(ExtractorError):
    """Temporary error, can be retried."""
    pass

class PermanentError(ExtractorError):
    """Permanent error, should not retry."""
    pass
```

### Error Classification Matrix

| Error Type | Retryable | Action |
|------------|-----------|--------|
| RateLimitError | Yes | Wait and retry |
| AuthenticationError | No | Notify admin |
| PlatformError | Maybe | Retry with backoff |
| ValidationError | No | Return error to user |
| NotFoundError | No | Skip resource |
| QuotaExceededError | No | Stop extraction |
| Network timeout | Yes | Retry |
| HTTP 5xx | Yes | Retry with backoff |
| HTTP 4xx | Depends | Check specific code |

## Retry Strategies

### Celery Task Retry

```python
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

app = Celery('extractor')

@app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True
)
def extract_platform(self, job_id: str, platform: str):
    try:
        # Extraction logic
        pass

    except RateLimitError as e:
        # Specific retry delay from API
        raise self.retry(
            exc=e,
            countdown=e.retry_after,
            max_retries=10  # More retries for rate limits
        )

    except TemporaryError as e:
        # Exponential backoff
        raise self.retry(exc=e)

    except PermanentError as e:
        # Don't retry, mark as failed
        mark_job_failed(job_id, platform, str(e))
        raise

    except Exception as e:
        # Unknown error, retry with caution
        if self.request.retries < 3:
            raise self.retry(exc=e)
        else:
            mark_job_failed(job_id, platform, str(e))
            raise
```

### HTTP Request Retry

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import httpx
import logging

logger = logging.getLogger(__name__)

class RetryableHTTPClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def request(self, method: str, url: str, **kwargs):
        response = await self.client.request(method, url, **kwargs)

        # Raise for 5xx errors (will trigger retry)
        if 500 <= response.status_code < 600:
            response.raise_for_status()

        # Rate limit handling
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError("Rate limited", retry_after=retry_after)

        return response

    async def get(self, url: str, **kwargs):
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self.request("POST", url, **kwargs)
```

### Platform-Specific Retry

```python
class FacebookExtractor(BaseExtractor):
    def __init__(self, credentials):
        super().__init__(credentials)
        self.retry_config = {
            "max_retries": 5,
            "base_delay": 60,
            "max_delay": 3600
        }

    async def get_with_retry(self, url: str):
        retries = 0
        last_error = None

        while retries < self.retry_config["max_retries"]:
            try:
                response = await self.client.get(url)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    # Facebook specific rate limit
                    delay = self._calculate_facebook_delay(response)
                    logger.warning(f"Facebook rate limit, waiting {delay}s")
                    await asyncio.sleep(delay)
                    retries += 1
                    continue

                if response.status_code >= 500:
                    raise TemporaryError(f"Facebook server error: {response.status_code}")

                # 4xx errors - don't retry
                raise PlatformError(f"Facebook error: {response.text}")

            except httpx.TimeoutException as e:
                last_error = e
                retries += 1
                delay = min(
                    self.retry_config["base_delay"] * (2 ** retries),
                    self.retry_config["max_delay"]
                )
                await asyncio.sleep(delay)

        raise last_error or TemporaryError("Max retries exceeded")

    def _calculate_facebook_delay(self, response) -> int:
        # Facebook includes rate limit reset info
        error = response.json().get("error", {})
        if "error_user_msg" in error:
            # Parse "Please retry your request later" type messages
            return 300  # 5 minutes default
        return int(response.headers.get("Retry-After", 60))
```

## Circuit Breaker Pattern

```python
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
                return True
            return False

        # HALF_OPEN - allow limited requests
        return True

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failures = 0
        else:
            self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
class PlatformExtractor:
    def __init__(self):
        self.circuit_breakers = {
            "facebook": CircuitBreaker(),
            "instagram": CircuitBreaker(),
            "twitter": CircuitBreaker()
        }

    async def extract(self, platform: str, *args):
        cb = self.circuit_breakers[platform]

        if not cb.can_execute():
            raise PlatformError(f"{platform} circuit breaker is OPEN")

        try:
            result = await self._do_extract(platform, *args)
            cb.record_success()
            return result
        except Exception as e:
            cb.record_failure()
            raise
```

## Error Recovery

### Checkpoint and Resume

```python
class ExtractionRecovery:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def save_checkpoint(
        self,
        job_id: str,
        platform: str,
        checkpoint_data: dict
    ):
        """Save extraction progress for recovery."""
        key = f"checkpoint:{job_id}:{platform}"
        await self.redis.set(
            key,
            json.dumps({
                "data": checkpoint_data,
                "saved_at": datetime.utcnow().isoformat()
            }),
            ex=86400 * 7  # Keep for 7 days
        )

    async def get_checkpoint(self, job_id: str, platform: str) -> dict:
        """Get checkpoint for resuming extraction."""
        key = f"checkpoint:{job_id}:{platform}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)["data"]
        return None

    async def resume_extraction(self, job_id: str, platform: str):
        """Resume extraction from checkpoint."""
        checkpoint = await self.get_checkpoint(job_id, platform)

        if not checkpoint:
            # Start from beginning
            return await self.start_fresh_extraction(job_id, platform)

        logger.info(f"Resuming {platform} extraction from checkpoint")

        # Resume from last successful point
        extractor = get_extractor(platform)
        return await extractor.extract(
            job_id,
            start_from=checkpoint.get("last_cursor"),
            processed_count=checkpoint.get("processed_count", 0)
        )
```

### Partial Failure Handling

```python
class JobFailureHandler:
    async def handle_platform_failure(
        self,
        job_id: str,
        platform: str,
        error: Exception
    ):
        """Handle failure of a single platform."""

        # 1. Log the error
        logger.error(
            f"Platform {platform} failed for job {job_id}",
            exc_info=error
        )

        # 2. Update platform status
        await self.update_platform_status(
            job_id, platform, "failed", str(error)
        )

        # 3. Check if job should continue
        job = await self.job_repo.get(job_id)
        failed_platforms = await self.get_failed_platforms(job_id)

        if len(failed_platforms) == len(job.platforms):
            # All platforms failed
            await self.mark_job_failed(job_id)
        else:
            # Some platforms succeeded - partial success
            await self.mark_job_partial(job_id)

    async def mark_job_partial(self, job_id: str):
        """Mark job as partially complete."""
        job = await self.job_repo.get(job_id)
        job.status = "partial"
        job.completed_at = datetime.utcnow()

        # Calculate partial stats
        stats = await self.calculate_partial_stats(job_id)
        job.progress = stats

        await self.job_repo.save(job)

        # Notify user
        await self.send_notification(
            job_id,
            "extraction.partial",
            "Some platforms failed, partial data available"
        )
```

## Error Reporting

### Structured Error Logging

```python
import structlog

logger = structlog.get_logger()

class ErrorReporter:
    async def report(
        self,
        error: Exception,
        context: dict
    ):
        """Report error with full context."""

        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "job_id": context.get("job_id"),
            "platform": context.get("platform"),
            "operation": context.get("operation"),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add stack trace for unexpected errors
        if not isinstance(error, ExtractorError):
            error_data["stack_trace"] = traceback.format_exc()

        # Log with context
        logger.error(
            "extraction_error",
            **error_data
        )

        # Send to error tracking (Sentry, etc.)
        if self.sentry_enabled:
            sentry_sdk.capture_exception(
                error,
                extras=error_data
            )

        # Store for analysis
        await self.store_error(error_data)

    async def store_error(self, error_data: dict):
        """Store error for later analysis."""
        await self.redis.lpush(
            "errors:recent",
            json.dumps(error_data)
        )
        # Keep last 1000 errors
        await self.redis.ltrim("errors:recent", 0, 999)
```

### User-Facing Error Messages

```python
ERROR_MESSAGES = {
    "RateLimitError": {
        "code": "RATE_LIMITED",
        "message": "The platform is rate limiting requests. The extraction will automatically retry.",
        "user_action": "Please wait, the system will resume automatically."
    },
    "AuthenticationError": {
        "code": "AUTH_ERROR",
        "message": "Authentication failed for the platform.",
        "user_action": "Please check your API credentials in settings."
    },
    "NotFoundError": {
        "code": "NOT_FOUND",
        "message": "The requested social media account was not found.",
        "user_action": "Please verify the account URL/username."
    },
    "QuotaExceededError": {
        "code": "QUOTA_EXCEEDED",
        "message": "Monthly API quota has been exceeded.",
        "user_action": "Please wait until quota resets or upgrade your plan."
    }
}

def get_user_error(error: Exception) -> dict:
    """Convert internal error to user-friendly message."""
    error_type = type(error).__name__

    if error_type in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_type]

    # Generic error
    return {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred.",
        "user_action": "Please try again or contact support."
    }
```

## Alerting

### Alert Configuration

```python
class AlertManager:
    def __init__(self, config):
        self.thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "job_duration": 3600,  # 1 hour
            "queue_size": 100
        }
        self.channels = config.alert_channels  # slack, email, etc.

    async def check_and_alert(self):
        """Check metrics and send alerts if needed."""

        # Error rate check
        error_rate = await self.calculate_error_rate()
        if error_rate > self.thresholds["error_rate"]:
            await self.send_alert(
                level="warning",
                title="High Error Rate",
                message=f"Error rate is {error_rate:.1%}"
            )

        # Queue size check
        queue_size = await self.get_queue_size()
        if queue_size > self.thresholds["queue_size"]:
            await self.send_alert(
                level="info",
                title="Large Queue",
                message=f"Queue has {queue_size} pending jobs"
            )

    async def send_alert(self, level: str, title: str, message: str):
        for channel in self.channels:
            if channel == "slack":
                await self.send_slack_alert(level, title, message)
            elif channel == "email":
                await self.send_email_alert(level, title, message)
```
