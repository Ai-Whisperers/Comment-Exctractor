# Extraction Workflow

## Overview

This document details the extraction workflow for scraping social media data using Playwright-based browser automation.

## High-Level Flow

```
+-------------+     +-------------+     +-------------+
|   CLI       |---->|  Settings   |---->|  Scraper    |
|  (extract.py)     |  Validation |     |  Registry   |
+-------------+     +-------------+     +------+------+
                                               |
                    +--------------------------+
                    |
             +------v------+
             | Browser     |
             | Manager     |
             | (Playwright)|
             +------+------+
                    |
         +----------+----------+
         |          |          |
    +----v---+ +----v---+ +----v---+
    |Facebook| |Instagram| |Twitter|
    |Scraper | |Scraper | |Scraper |
    | (POM)  | | (POM)  | |        |
    +----+---+ +----+---+ +----+---+
         |          |          |
         +----------+----------+
                    |
             +------v------+
             | Extraction  |
             | Result      |
             | (Post+      |
             |  Comments)  |
             +------+------+
                    |
             +------v------+
             | Storage     |
             | Backend     |
             +------+------+
                    |
        +-----------+-----------+
        |           |           |
   +----v---+  +----v---+  +----v---+
   |  JSON  |  |  CSV   |  | Excel  |
   +--------+  +--------+  +--------+
```

## Detailed Workflow Steps

### 1. CLI Initialization

```python
# extract.py

def main():
    # 1. Parse command-line arguments
    args = parse_arguments()

    # 2. Load settings from environment/.env
    settings = get_settings()
    settings.setup_logging()
    settings.ensure_directories()

    # 3. Validate platform credentials
    for platform in args.platforms:
        warnings = settings.validate_platform_config(platform)
        if warnings:
            for warning in warnings:
                logger.warning(warning)

    # 4. Get platform configuration
    config = settings.get_platform_config(platform)

    # 5. Initialize scraper from registry
    scraper_class = ScraperRegistry.get(platform)
    scraper = scraper_class(config)

    # 6. Run extraction
    with scraper:
        results = list(scraper.get_posts_with_comments(
            account_id=args.account,
            max_posts=args.max_posts
        ))

    # 7. Export results
    save_results(results, args.account, platform, args.format)
```

### 2. Browser Initialization

The `BrowserManager` handles all browser lifecycle management.

```python
class BrowserManager:
    def __init__(self, config: BrowserConfig, platform: str):
        self.config = config
        self.platform = platform
        self._initialize()

    def _initialize(self):
        # Start Playwright
        self._playwright = sync_playwright().start()

        if self.config.profile_dir:
            # Persistent context (preserves cookies)
            self._init_persistent_context()
        else:
            # Standard context with optional storage state
            self._init_standard_context()

    def _init_persistent_context(self):
        """Use persistent browser profile for session preservation."""
        profile_path = Path(self.config.profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        self._context = self._playwright.chromium.launch_persistent_context(
            str(profile_path),
            headless=self.config.headless,
            viewport=self.config.viewport,
            user_agent=self.config.user_agent,
            args=self.config.browser_args,
            proxy={"server": self.config.proxy} if self.config.proxy else None
        )

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

    def _init_standard_context(self):
        """Standard browser with optional storage state."""
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless,
            args=self.config.browser_args,
            proxy={"server": self.config.proxy} if self.config.proxy else None
        )

        context_options = {
            "viewport": self.config.viewport,
            "user_agent": self.config.user_agent,
        }

        # Load existing session if available
        if self.config.storage_state and Path(self.config.storage_state).exists():
            context_options["storage_state"] = self.config.storage_state

        self._context = self._browser.new_context(**context_options)
        self._page = self._context.new_page()
```

### 3. Authentication Flow

```python
class InstagramScraper(BaseScraper):
    def _ensure_logged_in(self):
        """Ensure user is logged in, performing login if necessary."""
        # Navigate to home page
        self._page.goto("https://instagram.com", wait_until="domcontentloaded")
        self._page.wait_for_timeout(3000)

        # Dismiss popups
        self._profile_page.dismiss_popups()

        # Check current URL for login redirect
        current_url = self._page.url
        if "/accounts/login" in current_url or "/accounts/signup" in current_url:
            logger.info("Need to authenticate")
        elif self._profile_page.is_logged_in():
            # Verify no login form is present
            has_login_form = self._page.evaluate('''
                () => {
                    const hasUsername = !!document.querySelector('input[name="username"]');
                    const hasPassword = !!document.querySelector('input[name="password"]');
                    return hasUsername && hasPassword;
                }
            ''')
            if not has_login_form:
                logger.info("Already logged in")
                return

        # Perform login
        if not self._username or not self._password:
            raise AuthenticationError("Credentials required")

        self._login_page.login(self._username, self._password)

        # Save session for future use
        session_file = self.config.get("session_file")
        if session_file:
            session_path = Path(session_file).with_suffix('.playwright.json')
            self._browser_manager.save_storage_state(str(session_path))
            logger.info(f"Saved session to {session_path}")
```

### 4. Two-Phase Extraction (Instagram/Facebook)

The extraction uses a two-phase approach for efficiency:

#### Phase 1: Collect Post Links

```python
def _scrape_posts(self, account_id: str, since_date, max_posts, known_post_ids):
    """Phase 1: Collect all post links from profile."""

    self._ensure_logged_in()
    self._profile_page.navigate(account_id)

    # Check for private account
    if self._profile_page.is_private():
        raise PrivateAccountError(f"Account is private: {account_id}")

    # Collect post URLs by scrolling grid
    scroll_all = max_posts > 50
    post_links = self._profile_page.get_post_links(
        count=max_posts,
        scroll_all=scroll_all,
        known_post_ids=known_post_ids
    )

    if not post_links:
        logger.warning("No posts found")
        return

    logger.info(f"PHASE 1 COMPLETE | Collected {len(post_links)} post links")

    # Phase 2: Extract each post
    for post_url in post_links:
        yield from self._extract_single_post(post_url, account_id, since_date)
```

#### Phase 2: Extract Each Post

```python
def _extract_single_post(self, post_url, account_id, since_date):
    """Phase 2: Visit each post and extract data."""

    # Navigate with retry
    for attempt in range(3):
        try:
            self._page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_timeout(1500)
            break
        except Exception as e:
            logger.warning(f"Navigation attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                self._page.wait_for_timeout(2000)
    else:
        logger.warning(f"Failed to navigate to {post_url}")
        return

    # Check for rate limiting
    if self._check_rate_limit():
        logger.warning("Rate limit detected")
        self._page.wait_for_timeout(60000)
        if self._check_rate_limit():
            logger.error("Still rate limited, stopping")
            return

    # Extract post data
    post_data = self._post_modal.extract_post_data(account_id)
    post_id = post_data.get("id") or self._post_modal.get_post_id()

    if not post_id:
        logger.warning(f"Could not get post ID from {post_url}")
        return

    # Create Post object
    post = Post(
        platform=self.platform,
        platform_id=post_id,
        account_id=account_id,
        url=post_data["url"],
        text=post_data["caption"],
        published_at=post_data["timestamp"],
        likes=post_data["likes"],
        comments_count=0,
        shares=0,
        media_type=post_data["media_type"],
    )

    # Check date filter
    if since_date and post.published_at and post.published_at < since_date:
        logger.info(f"Post before since_date, stopping")
        return

    # Extract comments
    raw_comments = self._comments_section.extract_comments_for_post(post.platform_id)
    comments = self._create_comment_objects(raw_comments, post.platform_id)
    post.comments_count = len(comments)

    yield ExtractionResult(post=post, comments=comments)

    # Human-like delay
    self._post_modal.human_delay(1000, 2000)
```

### 5. Human-Like Delay System

```python
class BaseScraper:
    # Delay settings
    min_delay: float = 0.5       # 500ms minimum
    max_delay: float = 1.0       # 1s maximum
    long_pause_interval: int = 20
    long_pause_min: float = 3.0
    long_pause_max: float = 5.0
    very_long_pause_interval: int = 100
    very_long_pause_min: float = 10.0
    very_long_pause_max: float = 20.0

    def _human_delay(self):
        """Apply human-like random delays between requests."""
        self._request_count += 1

        # Very long break every 100 requests (10-20s)
        if self._request_count % self.very_long_pause_interval == 0:
            pause_time = random.uniform(self.very_long_pause_min, self.very_long_pause_max)
            logger.info(f"LONG BREAK | {pause_time/60:.1f}min")
            time.sleep(pause_time)

        # Medium break every 20 requests (3-5s)
        elif self._request_count % self.long_pause_interval == 0:
            pause_time = random.uniform(self.long_pause_min, self.long_pause_max)
            logger.info(f"SHORT BREAK | {pause_time:.1f}s")
            time.sleep(pause_time)

        else:
            # Variable delay based on "mood"
            if random.random() < 0.2:  # 20% quick action
                delay = random.uniform(self.min_delay * 0.5, self.min_delay)
            elif random.random() < 0.1:  # 10% long pause
                delay = random.uniform(self.max_delay, self.max_delay * 1.5)
            else:  # Normal delay
                delay = random.uniform(self.min_delay, self.max_delay)

            time.sleep(delay)

        self._last_request_time = time.time()
```

### 6. Rate Limit Detection

Each platform has specific indicators:

```python
class InstagramRateLimitDetector(RateLimitDetector):
    INDICATORS = [
        "try again later",
        "please wait",
        "action blocked",
        "temporarily blocked",
        "too many requests",
        "we limit how often",
        "suspicious activity",
    ]

    BLOCKED_URLS = [
        "/challenge/",
        "/accounts/suspended",
        "/accounts/consent",
    ]

    def is_rate_limited(self, page: Page) -> bool:
        # Check URL patterns
        current_url = page.url
        for url_pattern in self.BLOCKED_URLS:
            if url_pattern in current_url:
                logger.warning(f"RATE LIMIT | blocked URL: {current_url}")
                return True

        # Check page text
        page_text = page.evaluate("document.body?.innerText || ''").lower()
        for indicator in self.INDICATORS:
            if indicator in page_text:
                logger.warning(f"RATE LIMIT | indicator: {indicator}")
                return True

        return False
```

### 7. Rate Limit Handling

```python
class RateLimitHandler:
    def __init__(self, base_delay=5.0, max_delay=60.0, max_retries=3):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self._consecutive_errors = 0

    def calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = delay * random.uniform(-0.25, 0.25)
        return delay + jitter

    def handle_rate_limit(self, rotate_proxy_callback=None):
        """Handle rate limit with extended wait."""
        self._consecutive_errors += 1

        # Try rotating proxy
        if rotate_proxy_callback:
            rotate_proxy_callback()

        # Calculate wait time
        backoff_time = self.calculate_backoff(self._consecutive_errors)
        extra_wait = random.uniform(60, 180)  # 1-3 minutes extra
        total_wait = backoff_time + extra_wait

        logger.warning(f"RATE LIMIT WAIT | {total_wait/60:.1f}min")
        time.sleep(total_wait)

    def reset(self):
        """Reset after successful operation."""
        self._consecutive_errors = 0
```

### 8. Checkpointing (Resume Support)

```python
class InstagramScraper:
    def _get_checkpoint_path(self, account_id: str) -> Path:
        checkpoint_dir = Path(self.config.get("data_dir", "data")) / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / f"instagram_{account_id}_checkpoint.json"

    def _load_checkpoint(self, account_id: str) -> Set[str]:
        """Load processed post IDs from checkpoint."""
        checkpoint_path = self._get_checkpoint_path(account_id)
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r') as f:
                    data = json.load(f)
                    processed_ids = set(data.get("processed_post_ids", []))
                    logger.info(f"CHECKPOINT | loaded {len(processed_ids)} processed posts")
                    return processed_ids
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return set()

    def _save_checkpoint(self, account_id: str, processed_post_ids: Set[str]):
        """Save checkpoint for resume capability."""
        checkpoint_path = self._get_checkpoint_path(account_id)
        try:
            data = {
                "account_id": account_id,
                "processed_post_ids": list(processed_post_ids),
                "last_updated": datetime.now().isoformat(),
                "count": len(processed_post_ids)
            }
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
```

### 9. Storage Backend

```python
class StorageBackend(ABC):
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def save_posts(self, posts, account, platform) -> str:
        pass

    @abstractmethod
    def save_comments(self, comments, account, platform) -> str:
        pass

    def save_extraction_result(self, posts, comments, profile, account, platform):
        """Save complete extraction result."""
        results = {}

        if posts:
            results["posts"] = self.save_posts(posts, account, platform)
            logger.info(f"Saved {len(posts)} posts to {results['posts']}")

        if comments:
            results["comments"] = self.save_comments(comments, account, platform)
            logger.info(f"Saved {len(comments)} comments to {results['comments']}")

        if profile:
            results["profile"] = self.save_profile(profile, account, platform)

        return results

    def _generate_filename(self, account, platform, data_type, extension) -> Path:
        """Generate standardized filename with organized directory structure."""
        # Output: {output_dir}/{account}/{platform}/{YYYY-MM}/file.ext
        path_manager = OutputPathManager(str(self.output_dir))
        file_path = path_manager.get_export_path(
            client=account,
            platform=platform,
            data_type=data_type,
            format=extension
        )
        path_manager.ensure_dir(file_path)
        return file_path
```

### 10. Incremental Updates

```python
def save_results_with_merge(results, account, platform, output_dir):
    """Save results with incremental merge into combined.json."""

    combined_path = Path(output_dir) / account / "combined.json"

    # Load existing data
    if combined_path.exists():
        with open(combined_path, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {
            "metadata": {
                "account": account,
                "created_at": datetime.now().isoformat(),
                "platforms": [],
            },
            "extractions": []
        }

    # Create lookup for existing posts
    existing_posts = {
        ext["post"]["platform_id"]: ext
        for ext in existing_data["extractions"]
    }

    # Merge new results
    for result in results:
        post_id = result.post.platform_id

        if post_id in existing_posts:
            # Update existing post with new comments
            existing = existing_posts[post_id]
            existing_comment_ids = {c["platform_id"] for c in existing["comments"]}

            for comment in result.comments:
                if comment.platform_id not in existing_comment_ids:
                    existing["comments"].append(comment_to_dict(comment))
        else:
            # Add new post
            existing_data["extractions"].append({
                "post": post_to_dict(result.post),
                "comments": [comment_to_dict(c) for c in result.comments]
            })

    # Update metadata
    existing_data["metadata"]["last_updated"] = datetime.now().isoformat()
    existing_data["metadata"]["total_posts"] = len(existing_data["extractions"])
    existing_data["metadata"]["total_comments"] = sum(
        len(ext["comments"]) for ext in existing_data["extractions"]
    )

    if platform not in existing_data["metadata"]["platforms"]:
        existing_data["metadata"]["platforms"].append(platform)

    # Save merged data
    with open(combined_path, 'w') as f:
        json.dump(existing_data, f, indent=2, default=str)

    return combined_path
```

## Page Object Model Pattern

### Base Page

```python
class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def human_delay(self, min_ms: int, max_ms: int):
        """Human-like random delay."""
        delay = random.randint(min_ms, max_ms)
        self.page.wait_for_timeout(delay)

    def wait_for_element(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for element to be visible."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def safe_click(self, selector: str) -> bool:
        """Click element if it exists."""
        try:
            element = self.page.query_selector(selector)
            if element:
                element.click()
                return True
        except Exception:
            pass
        return False
```

### Profile Page Example

```python
class ProfilePage(BasePage):
    def navigate(self, username: str):
        """Navigate to user profile."""
        url = f"https://instagram.com/{username}/"
        self.page.goto(url, wait_until="domcontentloaded")
        self.human_delay(2000, 3000)

    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        # Look for profile menu or avatar
        indicators = [
            'svg[aria-label="Home"]',
            'a[href*="/direct/inbox/"]',
            'nav a[href*="/accounts/activity/"]'
        ]
        for selector in indicators:
            if self.page.query_selector(selector):
                return True
        return False

    def is_private(self) -> bool:
        """Check if account is private."""
        return "This Account is Private" in self.page.content()

    def get_followers_count(self) -> int:
        """Extract followers count."""
        try:
            selector = 'a[href*="/followers/"] span'
            element = self.page.query_selector(selector)
            if element:
                text = element.inner_text()
                return self._parse_count(text)
        except Exception:
            pass
        return 0

    def get_post_links(self, count: int, scroll_all: bool, known_post_ids: set) -> List[str]:
        """Collect post URLs from grid."""
        links = []
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50

        while len(links) < count and scroll_attempts < max_scroll_attempts:
            # Get all post links on page
            post_elements = self.page.query_selector_all('a[href*="/p/"]')

            for element in post_elements:
                href = element.get_attribute('href')
                if href and "/p/" in href:
                    # Extract post ID
                    post_id = href.split("/p/")[1].rstrip("/")

                    # Skip if already known
                    if post_id in known_post_ids:
                        continue

                    full_url = f"https://instagram.com{href}"
                    if full_url not in links:
                        links.append(full_url)

            # Check if we found new posts
            if len(links) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = len(links)

            # Scroll down
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.human_delay(1500, 2500)

        return links[:count]
```

## Error Recovery

### Retry with Exponential Backoff

```python
def _navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
    """Navigate with retry and rate limit detection."""

    for attempt in range(max_retries):
        try:
            self._page.goto(url, wait_until="domcontentloaded")
            self._page.wait_for_timeout(1500)

            # Check for rate limiting
            if self._check_rate_limit():
                if attempt < max_retries - 1:
                    self._wait_with_backoff(attempt)
                    continue
                else:
                    raise RateLimitError("Rate limited")

            return True

        except RateLimitError:
            raise
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                self._wait_with_backoff(attempt)

    return False

def _wait_with_backoff(self, attempt: int):
    """Wait with exponential backoff plus jitter."""
    delay = min(2.0 * (2 ** attempt), 60.0)
    jitter = delay * random.uniform(-0.25, 0.25)
    actual_delay = delay + jitter
    logger.info(f"RETRY | waiting {actual_delay:.1f}s before attempt {attempt + 2}")
    time.sleep(actual_delay)
```

### Session Expiry Handling

```python
def _handle_session_expiry(self, account_id: str):
    """Handle session expiry by re-logging in."""
    logger.info("SESSION | forcing re-login")

    if self._username and self._password:
        self._login_page.login(self._username, self._password)

        # Save new session
        session_file = self.config.get("session_file")
        if session_file:
            session_path = Path(session_file).with_suffix('.playwright.json')
            self._browser_manager.save_storage_state(str(session_path))

        # Navigate back to profile
        self._profile_page.navigate(account_id)
    else:
        raise AuthenticationError("Session expired and no credentials available")
```

## Monitoring & Logging

### Log Format

```python
# File: Detailed format
"%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s"

# Console: Concise format
"%(asctime)s | %(levelname)-8s | %(message)s"
```

### Key Log Messages

```python
# Extraction lifecycle
"EXTRACTION START | account={account_id} | platform={platform} | max_posts={max_posts}"
"EXTRACTION COMPLETE | posts={posts} | comments={comments} | duration={duration}s"

# Phase tracking
"PHASE 1 COMPLETE | Collected {count} post links"
"PHASE 2 COMPLETE | posts={posts} | skipped={skipped}"

# Rate limiting
"RATE LIMIT | indicator detected: {indicator}"
"RATE LIMIT WAIT | total={total}min | backoff={backoff}s"

# Delays
"LONG BREAK | duration={duration}min | reason=anti_detection"
"SHORT BREAK | duration={duration}s"

# Session management
"SESSION | already logged in"
"SESSION | performing login"
"SESSION | saved Playwright session to {path}"

# Browser lifecycle
"BROWSER INIT | platform={platform} | headless={headless}"
"BROWSER SHUTDOWN | platform={platform}"
```

### Session Statistics

```python
def get_session_stats(self) -> Dict[str, Any]:
    """Get statistics about the current scraping session."""
    elapsed = time.time() - self._session_start
    return {
        "requests": self._request_count,
        "elapsed_minutes": elapsed / 60,
        "requests_per_minute": self._request_count / (elapsed / 60) if elapsed > 0 else 0,
        "consecutive_errors": self._consecutive_errors,
        "current_user_agent": self._current_user_agent[:50] + "...",
        "using_proxy": self._current_proxy is not None,
    }
```

## Output Files

### Directory Structure

```
data/exports/{account}/{platform}/{YYYY-MM}/
+-- {account}_{platform}_posts_{timestamp}.json
+-- {account}_{platform}_comments_{timestamp}.json
+-- combined.json
```

### Example Output

```json
// combined.json
{
  "metadata": {
    "account": "personalpy",
    "last_updated": "2024-11-21T18:51:00Z",
    "created_at": "2024-11-20T19:00:00Z",
    "total_posts": 150,
    "total_comments": 5000,
    "platforms": ["instagram", "facebook"]
  },
  "extractions": [
    {
      "post": {
        "platform": "instagram",
        "platform_id": "ig_12345",
        "account_id": "personalpy",
        "url": "https://instagram.com/p/...",
        "text": "Post caption",
        "published_at": "2024-11-15T10:30:00Z",
        "likes": 450,
        "comments_count": 25,
        "shares": 0,
        "media_type": "image"
      },
      "comments": [
        {
          "platform": "instagram",
          "platform_id": "ig_comment_987",
          "post_id": "ig_12345",
          "text": "Great post!",
          "author": {
            "platform_id": "ig_user_555",
            "username": "john_doe",
            "display_name": "John Doe",
            "is_verified": false
          },
          "published_at": "2024-11-15T11:00:00Z",
          "likes": 5,
          "parent_id": null,
          "replies_count": 1
        }
      ]
    }
  ]
}
```

## Performance Considerations

### Extraction Speed

| Platform  | Posts/Min | With Comments |
|-----------|-----------|---------------|
| Instagram | 3-5       | 2-3           |
| Facebook  | 4-6       | 3-4           |
| Twitter   | 5-8       | 4-5           |

### Memory Usage

- Results are yielded (not stored in memory)
- Incremental file merging
- Browser profile can grow large (clear periodically)

### Network Optimization

- Persistent browser profiles (no repeated login)
- Session state preservation
- Connection reuse via Playwright

## Quiet Hours Support

```python
def is_good_time_to_scrape(self) -> bool:
    """Check if current time is reasonable for browsing."""
    current_hour = datetime.now().hour

    # Avoid heavy scraping during 2 AM - 6 AM
    if 2 <= current_hour < 6:
        return False

    return True

def wait_for_good_time(self):
    """Wait until a reasonable time to resume."""
    while not self.is_good_time_to_scrape():
        now = datetime.now()
        wait_until = now.replace(hour=6, minute=0, second=0)
        if wait_until <= now:
            wait_until = wait_until.replace(day=now.day + 1)

        wait_seconds = (wait_until - now).total_seconds()
        logger.info(f"QUIET HOURS PAUSE | resume_at=06:00 | wait={wait_seconds/3600:.1f}h")
        time.sleep(min(wait_seconds, 3600))  # Check every hour
```
