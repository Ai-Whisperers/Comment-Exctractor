# Rate Limiting & Quota Management

## Overview

Rate limiting is critical for:
1. Respecting platform API limits
2. Avoiding IP bans
3. Managing third-party service costs
4. Ensuring fair resource allocation

## Platform Rate Limits

### Known Limits

| Platform | Endpoint | Limit | Window | Notes |
|----------|----------|-------|--------|-------|
| Facebook | Posts | 200 | 1 hour | Per access token |
| Facebook | Comments | 200 | 1 hour | Per access token |
| Instagram | Media | 200 | 1 hour | Shared with FB |
| Twitter | Search | 180 | 15 min | Per user auth |
| Twitter | Timeline | 900 | 15 min | App auth |
| LinkedIn | Posts | 100 | 1 day | Per app |
| Apify | API calls | Varies | Per plan | Check dashboard |

### Platform-Specific Headers

```python
# Response headers to monitor

# Facebook
"x-app-usage": {"call_count": 28, "total_time": 56, "total_cputime": 34}
"x-fb-rlafr": "0"  # Rate Limit Application-level Failure Response

# Twitter
"x-rate-limit-limit": "180"
"x-rate-limit-remaining": "175"
"x-rate-limit-reset": "1705316400"

# LinkedIn
"X-Li-Throttle-Limit": "100"
"X-Li-Throttle-Remaining": "95"
```

## Implementation

### Rate Limiter Class

```python
# src/utils/rate_limiter.py

import asyncio
import time
from typing import Dict
from datetime import datetime
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limits = {
            "facebook": {"requests": 200, "window": 3600},
            "instagram": {"requests": 200, "window": 3600},
            "twitter": {"requests": 180, "window": 900},
            "linkedin": {"requests": 100, "window": 86400},
            "apify": {"requests": 1000, "window": 3600}
        }

    async def acquire(self, platform: str, tokens: int = 1) -> bool:
        """
        Acquire rate limit tokens. Returns True if allowed.
        """
        key = f"ratelimit:{platform}"
        limit = self.limits.get(platform, {"requests": 60, "window": 60})

        # Use sliding window counter
        now = time.time()
        window_start = now - limit["window"]

        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Add new entry if allowed
        pipe.zadd(key, {f"{now}:{tokens}": now})

        # Set expiry
        pipe.expire(key, limit["window"])

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit["requests"]:
            # Remove the entry we just added
            await self.redis.zremrangebyscore(key, now, now)
            return False

        return True

    async def wait_if_needed(self, platform: str, tokens: int = 1):
        """
        Wait until rate limit allows request.
        """
        while not await self.acquire(platform, tokens):
            # Get time until oldest entry expires
            key = f"ratelimit:{platform}"
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)

            if oldest:
                wait_time = self.limits[platform]["window"] - (time.time() - oldest[0][1])
                wait_time = max(1, min(wait_time, 60))  # Cap at 60 seconds

                logger.info(f"Rate limited on {platform}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(1)

    async def get_remaining(self, platform: str) -> int:
        """
        Get remaining requests in current window.
        """
        key = f"ratelimit:{platform}"
        limit = self.limits.get(platform, {"requests": 60, "window": 60})

        now = time.time()
        window_start = now - limit["window"]

        # Remove old and count
        await self.redis.zremrangebyscore(key, 0, window_start)
        current = await self.redis.zcard(key)

        return max(0, limit["requests"] - current)

    async def get_reset_time(self, platform: str) -> int:
        """
        Get seconds until rate limit resets.
        """
        key = f"ratelimit:{platform}"

        oldest = await self.redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            reset = self.limits[platform]["window"] - (time.time() - oldest[0][1])
            return int(max(0, reset))

        return 0
```

### Decorator for Rate Limiting

```python
from functools import wraps

def rate_limited(platform: str):
    """Decorator to apply rate limiting to functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Wait for rate limit
            await self.rate_limiter.wait_if_needed(platform)

            try:
                result = await func(self, *args, **kwargs)
                return result

            except RateLimitError as e:
                # Platform returned 429, wait and retry
                await asyncio.sleep(e.retry_after)
                return await wrapper(self, *args, **kwargs)

        return wrapper
    return decorator

# Usage
class FacebookExtractor(BaseExtractor):
    @rate_limited("facebook")
    async def get_posts(self, identifier: str, options: dict):
        # This will automatically wait if rate limited
        return await self._fetch_posts(identifier, options)
```

### Adaptive Rate Limiting

```python
class AdaptiveRateLimiter:
    """
    Adjusts rate limits based on actual API responses.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.base_limits = {
            "facebook": 200,
            "instagram": 200,
            "twitter": 180
        }

    async def update_from_response(self, platform: str, response):
        """Update limits based on response headers."""

        if platform == "twitter":
            remaining = response.headers.get("x-rate-limit-remaining")
            reset = response.headers.get("x-rate-limit-reset")

            if remaining and reset:
                await self.redis.hset(
                    f"adaptive:{platform}",
                    mapping={
                        "remaining": remaining,
                        "reset": reset,
                        "updated": time.time()
                    }
                )

        elif platform == "facebook":
            usage = response.headers.get("x-app-usage")
            if usage:
                data = json.loads(usage)
                # Slow down if approaching limit
                if data.get("call_count", 0) > 80:
                    await self.redis.set(
                        f"adaptive:{platform}:throttle",
                        "1",
                        ex=300  # Throttle for 5 minutes
                    )

    async def should_throttle(self, platform: str) -> bool:
        """Check if we should slow down requests."""
        return await self.redis.exists(f"adaptive:{platform}:throttle")

    async def get_effective_limit(self, platform: str) -> int:
        """Get current effective limit for platform."""
        base = self.base_limits.get(platform, 60)

        if await self.should_throttle(platform):
            return base // 2  # Reduce by half when throttling

        return base
```

## Quota Management

### Monthly Quota Tracking

```python
class QuotaManager:
    """
    Track and enforce monthly quotas for third-party services.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.quotas = {
            "apify_comments": 100000,  # 100k comments/month
            "apify_api_calls": 10000,
        }

    async def track_usage(self, quota_type: str, amount: int = 1):
        """Track quota usage."""
        month_key = datetime.utcnow().strftime("%Y-%m")
        key = f"quota:{quota_type}:{month_key}"

        current = await self.redis.incrby(key, amount)

        # Set expiry for next month
        await self.redis.expire(key, 86400 * 35)  # 35 days

        # Check if exceeded
        if current > self.quotas.get(quota_type, float('inf')):
            raise QuotaExceededError(
                f"Monthly quota exceeded for {quota_type}"
            )

        return current

    async def get_usage(self, quota_type: str) -> dict:
        """Get current quota usage."""
        month_key = datetime.utcnow().strftime("%Y-%m")
        key = f"quota:{quota_type}:{month_key}"

        current = int(await self.redis.get(key) or 0)
        limit = self.quotas.get(quota_type, 0)

        return {
            "used": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "percentage": (current / limit * 100) if limit > 0 else 0
        }

    async def check_quota(self, quota_type: str, required: int) -> bool:
        """Check if quota is available."""
        usage = await self.get_usage(quota_type)
        return usage["remaining"] >= required

    async def reset_quota(self, quota_type: str):
        """Manually reset quota (admin only)."""
        month_key = datetime.utcnow().strftime("%Y-%m")
        key = f"quota:{quota_type}:{month_key}"
        await self.redis.delete(key)
```

### Cost Tracking

```python
class CostTracker:
    """
    Track API costs for budgeting.
    """

    # Cost per 1000 items
    COSTS = {
        "facebook_comments": 1.50,
        "instagram_comments": 2.30,
        "twitter_comments": 0.20,
        "linkedin_comments": 1.20,
    }

    def __init__(self, redis_client):
        self.redis = redis_client

    async def track_cost(self, operation: str, count: int):
        """Track cost for operation."""
        cost_per_1000 = self.COSTS.get(operation, 0)
        cost = (count / 1000) * cost_per_1000

        month_key = datetime.utcnow().strftime("%Y-%m")

        # Track total cost
        await self.redis.incrbyfloat(
            f"cost:total:{month_key}",
            cost
        )

        # Track by operation
        await self.redis.incrbyfloat(
            f"cost:{operation}:{month_key}",
            cost
        )

        return cost

    async def get_monthly_cost(self) -> dict:
        """Get current month's costs."""
        month_key = datetime.utcnow().strftime("%Y-%m")

        total = float(await self.redis.get(f"cost:total:{month_key}") or 0)

        breakdown = {}
        for operation in self.COSTS:
            cost = float(
                await self.redis.get(f"cost:{operation}:{month_key}") or 0
            )
            if cost > 0:
                breakdown[operation] = round(cost, 2)

        return {
            "total": round(total, 2),
            "breakdown": breakdown,
            "month": month_key
        }
```

## API Rate Limiting

### FastAPI Rate Limiter

```python
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/extractions")
@limiter.limit("5/minute")
async def create_extraction(request: Request, data: ExtractionRequest):
    pass

@app.get("/api/v1/extractions/{job_id}")
@limiter.limit("100/minute")
async def get_extraction(request: Request, job_id: str):
    pass

@app.get("/api/v1/exports/{export_id}/download")
@limiter.limit("10/minute")
async def download_export(request: Request, export_id: str):
    pass
```

### Custom Rate Limiter with Redis

```python
class APIRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed.
        Returns (allowed, headers_dict)
        """
        redis_key = f"api_ratelimit:{key}"

        # Increment counter
        current = await self.redis.incr(redis_key)

        # Set expiry on first request
        if current == 1:
            await self.redis.expire(redis_key, window)

        # Get TTL for reset time
        ttl = await self.redis.ttl(redis_key)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current)),
            "X-RateLimit-Reset": str(int(time.time()) + ttl)
        }

        allowed = current <= limit

        return allowed, headers

# Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Get API key
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    if api_key:
        limiter = APIRateLimiter(redis)
        allowed, headers = await limiter.check(
            key=api_key,
            limit=100,
            window=60
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"},
                headers=headers
            )

        response = await call_next(request)

        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    return await call_next(request)
```

## Monitoring & Alerts

### Rate Limit Metrics

```python
from prometheus_client import Counter, Gauge

rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['platform']
)

quota_usage = Gauge(
    'quota_usage_percent',
    'Quota usage percentage',
    ['quota_type']
)

monthly_cost = Gauge(
    'monthly_cost_dollars',
    'Monthly API costs in dollars'
)
```

### Alerts

```yaml
# alerts.yml

groups:
- name: rate_limiting
  rules:
  - alert: HighRateLimitHits
    expr: rate(rate_limit_hits_total[5m]) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High rate limit hits on {{ $labels.platform }}"

  - alert: QuotaNearLimit
    expr: quota_usage_percent > 80
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Quota usage above 80% for {{ $labels.quota_type }}"

  - alert: MonthlyBudgetExceeded
    expr: monthly_cost_dollars > 200
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Monthly API budget exceeded"
```
