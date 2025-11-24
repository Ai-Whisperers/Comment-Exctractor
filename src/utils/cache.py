"""Caching utilities for improved performance.

Provides in-memory and file-based caching for:
- Query results
- Extracted data
- Session state
"""

import hashlib
import json
import logging
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with metadata."""
    value: T
    created_at: float
    expires_at: Optional[float] = None
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MemoryCache(Generic[T]):
    """
    Thread-safe in-memory cache with TTL support.

    Usage:
        cache = MemoryCache[str](default_ttl=300)  # 5 minute TTL

        # Set and get
        cache.set("key", "value")
        value = cache.get("key")

        # With custom TTL
        cache.set("temp", "data", ttl=60)  # 1 minute

        # Delete
        cache.delete("key")

        # Clear all
        cache.clear()
    """

    def __init__(
        self,
        default_ttl: Optional[int] = None,
        max_size: int = 1000,
    ):
        """
        Initialize memory cache.

        Args:
            default_ttl: Default time-to-live in seconds (None = no expiry)
            max_size: Maximum number of entries
        """
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return default

            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                return default

            entry.hits += 1
            self._stats["hits"] += 1
            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_oldest()

            # Calculate expiry
            actual_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + actual_ttl if actual_ttl else None

            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
            )

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    def size(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            **self._stats,
            "size": len(self._cache),
            "hit_rate": (
                self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])
                if (self._stats["hits"] + self._stats["misses"]) > 0
                else 0
            ),
        }

    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU-style)."""
        if not self._cache:
            return

        # Find entry with fewest hits (or oldest if tied)
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hits, self._cache[k].created_at)
        )

        del self._cache[oldest_key]
        self._stats["evictions"] += 1

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired:
                del self._cache[key]
            return len(expired)


class FileCache(Generic[T]):
    """
    File-based cache for persistent storage.

    Stores cached data as pickle files on disk.

    Usage:
        cache = FileCache[dict]("./cache")

        cache.set("data", {"key": "value"})
        data = cache.get("data")
    """

    def __init__(
        self,
        cache_dir: str,
        default_ttl: Optional[int] = None,
    ):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default TTL in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = default_ttl

    def _key_to_path(self, key: str) -> Path:
        """Convert key to file path."""
        # Hash key for safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get value from file cache."""
        path = self._key_to_path(key)

        if not path.exists():
            return default

        try:
            with open(path, 'rb') as f:
                entry: CacheEntry[T] = pickle.load(f)

            if entry.is_expired():
                path.unlink()
                return default

            return entry.value

        except Exception as e:
            logger.warning(f"Failed to read cache file {path}: {e}")
            return default

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in file cache."""
        path = self._key_to_path(key)

        actual_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + actual_ttl if actual_ttl else None

        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
        )

        try:
            with open(path, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.error(f"Failed to write cache file {path}: {e}")

    def delete(self, key: str) -> bool:
        """Delete entry from file cache."""
        path = self._key_to_path(key)

        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> None:
        """Clear all cache files."""
        for path in self.cache_dir.glob("*.cache"):
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")

    def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        removed = 0

        for path in self.cache_dir.glob("*.cache"):
            try:
                with open(path, 'rb') as f:
                    entry = pickle.load(f)

                if entry.is_expired():
                    path.unlink()
                    removed += 1

            except Exception:
                # Remove corrupt files
                path.unlink()
                removed += 1

        return removed


# =============================================================================
# DECORATOR FOR FUNCTION CACHING
# =============================================================================

def cached(
    ttl: Optional[int] = 300,
    key_prefix: str = "",
    cache: Optional[MemoryCache] = None,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache: Cache instance to use (creates one if not provided)

    Usage:
        @cached(ttl=60)
        def expensive_query(client_id):
            return database.query(client_id)
    """
    _cache = cache or MemoryCache(default_ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Check cache
            result = _cache.get(key)
            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl)

            return result

        # Expose cache for testing/clearing
        wrapper.cache = _cache
        wrapper.clear_cache = _cache.clear

        return wrapper

    return decorator


# =============================================================================
# QUERY RESULT CACHE
# =============================================================================

class QueryCache:
    """
    Specialized cache for database query results.

    Provides automatic cache invalidation based on client/platform.

    Usage:
        cache = QueryCache()

        # Cache a query
        result = cache.get_or_set(
            "comments",
            client="acme",
            platform="facebook",
            fetcher=lambda: storage.get_comments("acme", "facebook")
        )

        # Invalidate when data changes
        cache.invalidate(client="acme", platform="facebook")
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize query cache.

        Args:
            ttl: Default TTL for cached queries
        """
        self._cache = MemoryCache(default_ttl=ttl, max_size=500)

    def _make_key(
        self,
        query_type: str,
        client: Optional[str] = None,
        platform: Optional[str] = None,
        **kwargs
    ) -> str:
        """Build cache key from query parameters."""
        parts = [query_type]
        if client:
            parts.append(f"client={client}")
        if platform:
            parts.append(f"platform={platform}")
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")
        return ":".join(parts)

    def get_or_set(
        self,
        query_type: str,
        fetcher: Callable[[], T],
        client: Optional[str] = None,
        platform: Optional[str] = None,
        ttl: Optional[int] = None,
        **kwargs
    ) -> T:
        """
        Get cached query result or fetch and cache it.

        Args:
            query_type: Type of query (e.g., "comments", "posts")
            fetcher: Function to call if not cached
            client: Client name for key
            platform: Platform for key
            ttl: Custom TTL
            **kwargs: Additional key parameters

        Returns:
            Query result
        """
        key = self._make_key(query_type, client, platform, **kwargs)

        result = self._cache.get(key)
        if result is not None:
            logger.debug(f"Cache hit: {key}")
            return result

        logger.debug(f"Cache miss: {key}")
        result = fetcher()
        self._cache.set(key, result, ttl)

        return result

    def invalidate(
        self,
        query_type: Optional[str] = None,
        client: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> int:
        """
        Invalidate cached queries matching criteria.

        Args:
            query_type: Query type to invalidate (None = all types)
            client: Client to invalidate (None = all clients)
            platform: Platform to invalidate (None = all platforms)

        Returns:
            Number of entries invalidated
        """
        # Build pattern to match
        patterns = []
        if query_type:
            patterns.append(query_type)
        if client:
            patterns.append(f"client={client}")
        if platform:
            patterns.append(f"platform={platform}")

        # Find and delete matching entries
        count = 0
        with self._cache._lock:
            keys_to_delete = []
            for key in self._cache._cache:
                if all(p in key for p in patterns):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache._cache[key]
                count += 1

        if count > 0:
            logger.debug(f"Invalidated {count} cache entries")

        return count

    def clear(self) -> None:
        """Clear all cached queries."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats()


# =============================================================================
# GLOBAL CACHE INSTANCES
# =============================================================================

_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get or create global query cache."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache(ttl=300)
    return _query_cache


def reset_query_cache() -> None:
    """Reset global query cache."""
    global _query_cache
    if _query_cache:
        _query_cache.clear()
    _query_cache = None
