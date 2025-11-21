# Extraction Workflow

## Overview

Detailed workflow for extracting social media data from multiple platforms.

## High-Level Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Request   │────>│   Queue     │────>│   Worker    │
│   (API)     │     │   (Redis)   │     │  (Celery)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┤
                    │                          │
             ┌──────▼──────┐            ┌──────▼──────┐
             │  Platform   │            │  Platform   │
             │  Extractor  │            │  Extractor  │
             │  (Facebook) │            │ (Instagram) │
             └──────┬──────┘            └──────┬──────┘
                    │                          │
                    └────────────┬─────────────┘
                                 │
                          ┌──────▼──────┐
                          │  Normalizer │
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │   Database  │
                          └─────────────┘
```

## Detailed Workflow Steps

### 1. Job Creation

```python
class ExtractionService:
    async def create_job(self, request: ExtractionRequest) -> Job:
        # 1. Validate company exists
        company = await self.company_repo.get(request.company_id)
        if not company:
            raise NotFoundError("Company not found")

        # 2. Validate platforms
        valid_platforms = ["facebook", "instagram", "twitter", "linkedin", "tiktok"]
        for platform in request.platforms:
            if platform not in valid_platforms:
                raise ValidationError(f"Invalid platform: {platform}")

        # 3. Create job record
        job = Job(
            company_id=request.company_id,
            platforms=request.platforms,
            options=request.options,
            status="queued"
        )
        await self.job_repo.save(job)

        # 4. Queue extraction tasks
        for platform in request.platforms:
            await self.queue.enqueue(
                "extract_platform",
                job_id=job.id,
                platform=platform
            )

        return job
```

### 2. Platform Extraction

Each platform runs as a separate task for parallel execution.

```python
@celery.task(bind=True, max_retries=3)
def extract_platform(self, job_id: str, platform: str):
    try:
        # 1. Get job and company info
        job = job_repo.get(job_id)
        company = company_repo.get(job.company_id)
        account = get_social_account(company, platform)

        # 2. Update job status
        update_job_progress(job_id, platform, "running")

        # 3. Get extractor for platform
        extractor = get_extractor(platform)

        # 4. Extract profile
        profile = extractor.get_profile(account.identifier)
        save_profile(account.id, profile)

        # 5. Extract posts
        posts = []
        for post in extractor.get_posts(account.identifier, job.options):
            normalized_post = normalize_post(post, platform)
            post_id = save_post(job_id, normalized_post)
            posts.append((post_id, post))

            # Update progress
            update_job_progress(job_id, platform, posts_count=len(posts))

        # 6. Extract comments for each post
        total_comments = 0
        for post_id, post in posts:
            comments = extractor.get_comments(post.id, job.options)

            for comment in comments:
                # Save author
                author_id = save_author(comment.author, platform)

                # Normalize and save comment
                normalized = normalize_comment(comment, platform, post_id, author_id)
                save_comment(job_id, normalized)
                total_comments += 1

            # Update progress
            update_job_progress(
                job_id, platform,
                comments_count=total_comments
            )

        # 7. Mark platform complete
        update_job_progress(job_id, platform, "completed")

    except RateLimitError as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        update_job_progress(job_id, platform, "failed", error=str(e))
        raise
```

### 3. Extractor Implementation

#### Base Extractor

```python
from abc import ABC, abstractmethod
from typing import Iterator

class BaseExtractor(ABC):
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.session = self._create_session()

    @abstractmethod
    def get_profile(self, identifier: str) -> dict:
        """Get account profile information."""
        pass

    @abstractmethod
    def get_posts(self, identifier: str, options: dict) -> Iterator[dict]:
        """Yield posts from the account."""
        pass

    @abstractmethod
    def get_comments(self, post_id: str, options: dict) -> Iterator[dict]:
        """Yield comments for a post."""
        pass

    def _handle_rate_limit(self, response):
        """Handle rate limiting."""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(f"Rate limited, retry after {retry_after}s")
```

#### Facebook Extractor (Apify)

```python
class FacebookExtractor(BaseExtractor):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.client = ApifyClient(credentials['apify_api_key'])

    def get_profile(self, identifier: str) -> dict:
        run = self.client.actor("apify/facebook-pages-scraper").call(
            run_input={
                "startUrls": [{"url": f"https://facebook.com/{identifier}"}],
                "resultsLimit": 1
            }
        )

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            return {
                "platform_id": item.get("pageId"),
                "name": item.get("name"),
                "followers": item.get("likes"),
                "url": item.get("url"),
                "raw": item
            }

    def get_posts(self, identifier: str, options: dict) -> Iterator[dict]:
        run = self.client.actor("apify/facebook-posts-scraper").call(
            run_input={
                "startUrls": [{"url": f"https://facebook.com/{identifier}"}],
                "resultsLimit": options.get("max_posts_per_platform", 100)
            }
        )

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            yield {
                "platform_id": item.get("postId"),
                "text": item.get("text"),
                "published_at": item.get("time"),
                "likes": item.get("likes"),
                "comments_count": item.get("comments"),
                "shares": item.get("shares"),
                "url": item.get("url"),
                "media_type": self._detect_media_type(item),
                "raw": item
            }

    def get_comments(self, post_id: str, options: dict) -> Iterator[dict]:
        run = self.client.actor("apify/facebook-comments-scraper").call(
            run_input={
                "startUrls": [{"url": f"https://facebook.com/{post_id}"}],
                "resultsLimit": options.get("max_comments_per_post", 500)
            }
        )

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            yield {
                "platform_id": item.get("id"),
                "text": item.get("text"),
                "published_at": item.get("date"),
                "likes": item.get("likesCount", 0),
                "author": {
                    "platform_id": item.get("profileId"),
                    "username": item.get("profileName"),
                    "url": item.get("profileUrl")
                },
                "parent_id": item.get("parentId"),
                "raw": item
            }
```

### 4. Data Normalization

```python
class DataNormalizer:
    def normalize_post(self, raw: dict, platform: str) -> Post:
        return Post(
            platform=platform,
            platform_id=str(raw["platform_id"]),
            text=self._clean_text(raw.get("text", "")),
            media_type=raw.get("media_type", "text"),
            media_urls=raw.get("media_urls", []),
            published_at=self._parse_timestamp(raw.get("published_at")),
            url=raw.get("url"),
            likes=raw.get("likes", 0),
            comments_count=raw.get("comments_count", 0),
            shares=raw.get("shares", 0),
            raw_data=raw.get("raw", {})
        )

    def normalize_comment(
        self,
        raw: dict,
        platform: str,
        post_id: str,
        author_id: str
    ) -> Comment:
        return Comment(
            platform=platform,
            platform_id=str(raw["platform_id"]),
            post_id=post_id,
            author_id=author_id,
            text=self._clean_text(raw["text"]),
            published_at=self._parse_timestamp(raw.get("published_at")),
            likes=raw.get("likes", 0),
            replies_count=raw.get("replies_count", 0),
            parent_id=raw.get("parent_id"),
            is_reply=bool(raw.get("parent_id")),
            raw_data=raw.get("raw", {})
        )

    def normalize_author(self, raw: dict, platform: str) -> Author:
        return Author(
            platform=platform,
            platform_id=str(raw["platform_id"]),
            username=raw.get("username"),
            display_name=raw.get("display_name"),
            profile_url=raw.get("url"),
            is_verified=raw.get("is_verified", False)
        )

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Normalize whitespace
        text = " ".join(text.split())
        # Remove null characters
        text = text.replace("\x00", "")
        return text.strip()

    def _parse_timestamp(self, value) -> datetime:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        # Try multiple formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
```

### 5. Progress Tracking

```python
class JobProgressTracker:
    def __init__(self, redis_client):
        self.redis = redis_client

    def update(self, job_id: str, platform: str, **kwargs):
        key = f"job:{job_id}:progress"

        # Get current progress
        current = self.redis.hget(key, platform)
        if current:
            progress = json.loads(current)
        else:
            progress = {
                "status": "pending",
                "posts_extracted": 0,
                "comments_extracted": 0
            }

        # Update fields
        for k, v in kwargs.items():
            if k == "status":
                progress["status"] = v
            elif k == "posts_count":
                progress["posts_extracted"] = v
            elif k == "comments_count":
                progress["comments_extracted"] = v
            elif k == "error":
                progress["error"] = v

        # Save
        self.redis.hset(key, platform, json.dumps(progress))

        # Check if all platforms complete
        self._check_job_completion(job_id)

    def _check_job_completion(self, job_id: str):
        key = f"job:{job_id}:progress"
        all_progress = self.redis.hgetall(key)

        statuses = [json.loads(v)["status"] for v in all_progress.values()]

        if all(s == "completed" for s in statuses):
            self._mark_job_complete(job_id)
        elif any(s == "failed" for s in statuses):
            self._mark_job_failed(job_id)

    def get_progress(self, job_id: str) -> dict:
        key = f"job:{job_id}:progress"
        raw = self.redis.hgetall(key)

        platforms = {}
        total_posts = 0
        total_comments = 0

        for platform, data in raw.items():
            progress = json.loads(data)
            platforms[platform] = progress
            total_posts += progress.get("posts_extracted", 0)
            total_comments += progress.get("comments_extracted", 0)

        return {
            "platforms": platforms,
            "totals": {
                "posts": total_posts,
                "comments": total_comments
            }
        }
```

### 6. Job Completion

```python
class JobCompletionHandler:
    async def handle_completion(self, job_id: str):
        # 1. Update job status
        job = await self.job_repo.get(job_id)
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        await self.job_repo.save(job)

        # 2. Calculate final statistics
        stats = await self.calculate_stats(job_id)
        job.progress = stats
        await self.job_repo.save(job)

        # 3. Send webhook notification
        if job.company.webhook_url:
            await self.send_webhook(
                job.company.webhook_url,
                {
                    "event": "extraction.completed",
                    "job_id": job_id,
                    "stats": stats
                }
            )

        # 4. Cleanup temporary data
        await self.cleanup_temp_data(job_id)

    async def calculate_stats(self, job_id: str) -> dict:
        return await self.db.execute("""
            SELECT
                COUNT(DISTINCT p.id) as total_posts,
                COUNT(DISTINCT c.id) as total_comments,
                COUNT(DISTINCT c.author_id) as unique_authors
            FROM extraction_jobs j
            LEFT JOIN posts p ON j.id = p.job_id
            LEFT JOIN comments c ON j.id = c.job_id
            WHERE j.id = $1
        """, job_id)
```

## Concurrency Model

### Parallel Platform Extraction

```python
# Each platform runs in its own Celery task
# Tasks run in parallel on different workers

@celery.task
def orchestrate_extraction(job_id: str, platforms: list):
    # Create group of tasks
    tasks = group([
        extract_platform.s(job_id, platform)
        for platform in platforms
    ])

    # Execute in parallel
    result = tasks.apply_async()

    # Wait for completion
    result.get()
```

### Rate Limit Coordination

```python
class RateLimitCoordinator:
    """Coordinate rate limits across workers using Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def acquire(self, platform: str, timeout: int = 30) -> bool:
        """Acquire rate limit slot."""
        key = f"ratelimit:{platform}"
        limit = self.get_limit(platform)

        # Use Redis INCR with TTL
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, 60)  # Reset every minute

        if current > limit:
            return False

        return True

    def get_limit(self, platform: str) -> int:
        limits = {
            "facebook": 30,  # 30 requests/minute
            "instagram": 30,
            "twitter": 60,
            "linkedin": 30
        }
        return limits.get(platform, 30)
```

## Error Recovery

### Checkpoint System

```python
class ExtractionCheckpoint:
    """Save progress for resumable extraction."""

    def save(self, job_id: str, platform: str, checkpoint: dict):
        key = f"checkpoint:{job_id}:{platform}"
        self.redis.set(key, json.dumps(checkpoint), ex=86400)  # 24h TTL

    def load(self, job_id: str, platform: str) -> dict:
        key = f"checkpoint:{job_id}:{platform}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def clear(self, job_id: str, platform: str):
        key = f"checkpoint:{job_id}:{platform}"
        self.redis.delete(key)

# Usage in extractor
def extract_posts(self, identifier: str, options: dict, job_id: str):
    # Check for checkpoint
    checkpoint = self.checkpoint.load(job_id, self.platform)
    last_cursor = checkpoint.get("cursor") if checkpoint else None

    for post in self.paginate_posts(identifier, cursor=last_cursor):
        yield post

        # Save checkpoint periodically
        if post.get("cursor"):
            self.checkpoint.save(job_id, self.platform, {
                "cursor": post["cursor"],
                "posts_processed": post.get("index", 0)
            })
```

## Monitoring

### Metrics to Track

```python
# Using Prometheus metrics

extraction_duration = Histogram(
    'extraction_duration_seconds',
    'Time spent on extraction',
    ['platform']
)

comments_extracted = Counter(
    'comments_extracted_total',
    'Total comments extracted',
    ['platform']
)

extraction_errors = Counter(
    'extraction_errors_total',
    'Total extraction errors',
    ['platform', 'error_type']
)

# Usage
with extraction_duration.labels(platform="facebook").time():
    extract_platform(job_id, "facebook")

comments_extracted.labels(platform="facebook").inc(100)
```
