"""
Caching and performance optimization for NRIS.

This module provides caching mechanisms to improve performance of
frequently accessed data and computationally expensive operations.

Features:
- In-memory LRU cache for fast access
- Database-backed cache for persistence across sessions
- Automatic cache invalidation
- Query result caching

Usage:
    from nris.cache import Cache, cached

    # Use decorator for function caching
    @cached(ttl=300)  # 5 minutes
    def get_analytics_summary():
        # Expensive computation
        return compute_summary()

    # Manual cache operations
    cache = Cache()
    cache.set('key', 'value', ttl=600)
    value = cache.get('key')
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Generic, Union
from collections import OrderedDict
import threading

from .config import DB_FILE

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LRUCache(Generic[T]):
    """Thread-safe in-memory LRU cache.

    Args:
        maxsize: Maximum number of items to store.
        ttl: Default time-to-live in seconds (0 = no expiration).

    Example:
        cache = LRUCache[Dict](maxsize=100, ttl=300)
        cache.set('stats', {'total': 100})
        data = cache.get('stats')
    """

    def __init__(self, maxsize: int = 128, ttl: int = 0):
        self.maxsize = maxsize
        self.default_ttl = ttl
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._lock = threading.RLock()

    def _is_expired(self, entry: tuple) -> bool:
        """Check if cache entry has expired."""
        _, expires_at = entry
        if expires_at is None:
            return False
        return time.time() > expires_at

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get value from cache.

        Args:
            key: Cache key.
            default: Value to return if key not found.

        Returns:
            Cached value or default.
        """
        with self._lock:
            if key not in self._cache:
                return default

            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry[0]

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if None).
        """
        with self._lock:
            actual_ttl = ttl if ttl is not None else self.default_ttl
            expires_at = time.time() + actual_ttl if actual_ttl > 0 else None

            # Remove oldest if at capacity
            while len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)

            self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if key was deleted, False if not found.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if self._is_expired(v)
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        with self._lock:
            return {
                'size': len(self._cache),
                'maxsize': self.maxsize,
                'default_ttl': self.default_ttl
            }


class DatabaseCache:
    """Persistent database-backed cache.

    Stores cache entries in SQLite for persistence across sessions.
    Useful for expensive computations that don't change frequently.

    Args:
        db_path: Path to database file.
        table_name: Name of cache table.

    Example:
        cache = DatabaseCache()
        cache.set('analytics_2024', data, ttl=3600)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        table_name: str = "_analytics_cache"
    ):
        self.db_path = db_path or DB_FILE
        self.table_name = table_name
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def _ensure_table(self) -> None:
        """Create cache table if it doesn't exist."""
        try:
            conn = self._get_connection()
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires
                ON {self.table_name}(expires_at)
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Could not create cache table: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from database cache.

        Args:
            key: Cache key.
            default: Default value if not found or expired.

        Returns:
            Cached value or default.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                f"SELECT cache_value, expires_at FROM {self.table_name} WHERE cache_key = ?",
                (key,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return default

            value_json, expires_at = row

            # Check expiration
            if expires_at:
                if datetime.fromisoformat(expires_at) < datetime.now():
                    self.delete(key)
                    return default

            return json.loads(value_json)

        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.debug(f"Cache get error for {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in database cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON serializable).
            ttl: Time-to-live in seconds.

        Returns:
            True if successful, False otherwise.
        """
        try:
            conn = self._get_connection()
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            value_json = json.dumps(value)

            conn.execute(
                f"""INSERT OR REPLACE INTO {self.table_name}
                    (cache_key, cache_value, created_at, expires_at)
                    VALUES (?, ?, ?, ?)""",
                (key, value_json, datetime.now().isoformat(), expires_at)
            )
            conn.commit()
            conn.close()
            return True

        except (sqlite3.Error, TypeError) as e:
            logger.debug(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                f"DELETE FROM {self.table_name} WHERE cache_key = ?",
                (key,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except sqlite3.Error:
            return False

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(f"DELETE FROM {self.table_name}")
            count = cursor.rowcount
            conn.commit()
            conn.close()
            return count
        except sqlite3.Error:
            return 0

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                f"DELETE FROM {self.table_name} WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            count = cursor.rowcount
            conn.commit()
            conn.close()
            return count
        except sqlite3.Error:
            return 0


class Cache:
    """Unified cache interface with memory and database backends.

    Provides a two-tier caching system:
    - L1: Fast in-memory LRU cache
    - L2: Persistent database cache (optional)

    Args:
        memory_maxsize: Max items in memory cache.
        memory_ttl: Default TTL for memory cache.
        use_db_cache: Whether to use database cache as L2.
        db_path: Path to database for L2 cache.

    Example:
        cache = Cache(memory_maxsize=256, memory_ttl=60)

        # Store in both tiers
        cache.set('stats', data, ttl=300, persist=True)

        # Get from fastest available tier
        data = cache.get('stats')
    """

    def __init__(
        self,
        memory_maxsize: int = 128,
        memory_ttl: int = 300,
        use_db_cache: bool = True,
        db_path: Optional[str] = None
    ):
        self.memory = LRUCache(maxsize=memory_maxsize, ttl=memory_ttl)
        self.db_cache = DatabaseCache(db_path) if use_db_cache else None

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache (memory first, then database).

        Args:
            key: Cache key.
            default: Default value if not found.

        Returns:
            Cached value or default.
        """
        # Try memory cache first (L1)
        value = self.memory.get(key)
        if value is not None:
            return value

        # Try database cache (L2)
        if self.db_cache:
            value = self.db_cache.get(key)
            if value is not None:
                # Promote to L1
                self.memory.set(key, value)
                return value

        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        persist: bool = False
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
            persist: Also store in database cache.
        """
        self.memory.set(key, value, ttl)

        if persist and self.db_cache:
            self.db_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete from all cache tiers.

        Args:
            key: Cache key.

        Returns:
            True if deleted from any tier.
        """
        memory_deleted = self.memory.delete(key)
        db_deleted = self.db_cache.delete(key) if self.db_cache else False
        return memory_deleted or db_deleted

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern.

        Args:
            pattern: Key prefix to match.

        Returns:
            Number of keys invalidated.
        """
        # Note: This is a simple prefix match
        count = 0

        # Memory cache - need to iterate
        with self.memory._lock:
            keys_to_delete = [
                k for k in self.memory._cache.keys()
                if k.startswith(pattern)
            ]
            for key in keys_to_delete:
                del self.memory._cache[key]
                count += 1

        # Database cache
        if self.db_cache:
            try:
                conn = self.db_cache._get_connection()
                cursor = conn.execute(
                    f"DELETE FROM {self.db_cache.table_name} WHERE cache_key LIKE ?",
                    (f"{pattern}%",)
                )
                count += cursor.rowcount
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass

        return count

    def clear(self) -> int:
        """Clear all caches.

        Returns:
            Total number of entries cleared.
        """
        count = self.memory.clear()
        if self.db_cache:
            count += self.db_cache.clear()
        return count

    def cleanup(self) -> int:
        """Remove expired entries from all tiers.

        Returns:
            Total number of entries removed.
        """
        count = self.memory.cleanup_expired()
        if self.db_cache:
            count += self.db_cache.cleanup_expired()
        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with stats from all tiers.
        """
        return {
            'memory': self.memory.stats(),
            'database_enabled': self.db_cache is not None
        }


# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get the global cache instance.

    Returns:
        Global Cache instance.
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    persist: bool = False
) -> Callable:
    """Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds.
        key_prefix: Prefix for cache key.
        persist: Store in database cache.

    Returns:
        Decorator function.

    Example:
        @cached(ttl=600, key_prefix='analytics')
        def compute_statistics(date_range: str) -> Dict:
            # Expensive computation
            return stats
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            cache = get_cache()
            result = cache.get(cache_key)

            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result

            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl, persist=persist)

            return result

        # Add method to invalidate this function's cache
        wrapper.invalidate = lambda: get_cache().invalidate_pattern(  # type: ignore
            key_prefix or func.__name__
        )

        return wrapper
    return decorator


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """Simple memoization decorator using functools.lru_cache.

    For functions that are called many times with the same arguments
    within a single session. No TTL, clears on process restart.

    Args:
        func: Function to memoize.

    Returns:
        Memoized function.

    Example:
        @memoize
        def expensive_computation(n: int) -> int:
            return sum(range(n))
    """
    return lru_cache(maxsize=128)(func)
