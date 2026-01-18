"""
Unit tests for cache module.
"""

import time
import pytest
from unittest.mock import patch

from nris.cache import (
    LRUCache,
    DatabaseCache,
    Cache,
    get_cache,
    cached,
    memoize,
)


class TestLRUCache:
    """Test cases for in-memory LRU cache."""

    def test_set_and_get(self):
        """Should store and retrieve values."""
        cache = LRUCache[str]()
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

    def test_get_missing_key(self):
        """Should return None for missing keys."""
        cache = LRUCache[str]()
        assert cache.get('nonexistent') is None

    def test_get_with_default(self):
        """Should return default for missing keys."""
        cache = LRUCache[str]()
        assert cache.get('missing', default='default') == 'default'

    def test_ttl_expiration(self):
        """Should expire entries after TTL."""
        cache = LRUCache[str](ttl=1)  # 1 second TTL
        cache.set('key', 'value')

        assert cache.get('key') == 'value'
        time.sleep(1.1)
        assert cache.get('key') is None

    def test_custom_ttl_per_key(self):
        """Should respect per-key TTL."""
        cache = LRUCache[str](ttl=10)  # Default 10 seconds
        cache.set('short', 'value', ttl=1)  # Override to 1 second
        cache.set('long', 'value')  # Uses default

        time.sleep(1.1)
        assert cache.get('short') is None
        assert cache.get('long') == 'value'

    def test_lru_eviction(self):
        """Should evict least recently used when at capacity."""
        cache = LRUCache[str](maxsize=3)
        cache.set('a', '1')
        cache.set('b', '2')
        cache.set('c', '3')

        # Access 'a' to make it recently used
        cache.get('a')

        # Add new item, should evict 'b' (least recently used)
        cache.set('d', '4')

        assert cache.get('a') == '1'
        assert cache.get('b') is None  # Evicted
        assert cache.get('c') == '3'
        assert cache.get('d') == '4'

    def test_delete(self):
        """Should delete keys."""
        cache = LRUCache[str]()
        cache.set('key', 'value')
        assert cache.delete('key') is True
        assert cache.get('key') is None
        assert cache.delete('nonexistent') is False

    def test_clear(self):
        """Should clear all entries."""
        cache = LRUCache[str]()
        cache.set('a', '1')
        cache.set('b', '2')

        count = cache.clear()
        assert count == 2
        assert cache.get('a') is None
        assert cache.get('b') is None

    def test_cleanup_expired(self):
        """Should remove expired entries."""
        cache = LRUCache[str]()
        cache.set('expired', 'value', ttl=1)
        cache.set('valid', 'value', ttl=60)

        time.sleep(1.1)
        removed = cache.cleanup_expired()

        assert removed == 1
        assert cache.get('expired') is None
        assert cache.get('valid') == 'value'

    def test_stats(self):
        """Should return cache statistics."""
        cache = LRUCache[str](maxsize=100, ttl=300)
        cache.set('a', '1')
        cache.set('b', '2')

        stats = cache.stats()
        assert stats['size'] == 2
        assert stats['maxsize'] == 100
        assert stats['default_ttl'] == 300


class TestDatabaseCache:
    """Test cases for database-backed cache."""

    @pytest.fixture
    def db_cache(self, tmp_path):
        """Create a database cache with temp database."""
        db_file = tmp_path / "test_cache.db"
        return DatabaseCache(str(db_file))

    def test_set_and_get(self, db_cache):
        """Should store and retrieve values."""
        db_cache.set('key', {'data': 'value'})
        assert db_cache.get('key') == {'data': 'value'}

    def test_get_missing(self, db_cache):
        """Should return default for missing keys."""
        assert db_cache.get('missing') is None
        assert db_cache.get('missing', default='def') == 'def'

    def test_ttl_expiration(self, db_cache):
        """Should expire entries after TTL."""
        db_cache.set('key', 'value', ttl=1)
        assert db_cache.get('key') == 'value'

        time.sleep(1.1)
        assert db_cache.get('key') is None

    def test_delete(self, db_cache):
        """Should delete keys."""
        db_cache.set('key', 'value')
        assert db_cache.delete('key') is True
        assert db_cache.get('key') is None

    def test_clear(self, db_cache):
        """Should clear all entries."""
        db_cache.set('a', 1)
        db_cache.set('b', 2)

        count = db_cache.clear()
        assert count == 2
        assert db_cache.get('a') is None

    def test_cleanup_expired(self, db_cache):
        """Should remove expired entries."""
        db_cache.set('expired', 'value', ttl=1)
        db_cache.set('valid', 'value', ttl=60)

        time.sleep(1.1)
        removed = db_cache.cleanup_expired()

        assert removed == 1

    def test_json_serialization(self, db_cache):
        """Should handle complex JSON-serializable values."""
        data = {
            'list': [1, 2, 3],
            'nested': {'a': 1, 'b': 2},
            'string': 'test',
            'number': 42.5,
            'boolean': True,
            'null': None
        }
        db_cache.set('complex', data)
        retrieved = db_cache.get('complex')
        assert retrieved == data


class TestCache:
    """Test cases for unified Cache class."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache with temp database."""
        db_file = tmp_path / "test_cache.db"
        return Cache(
            memory_maxsize=10,
            memory_ttl=60,
            use_db_cache=True,
            db_path=str(db_file)
        )

    def test_memory_cache_first(self, cache):
        """Should use memory cache for fast access."""
        cache.set('key', 'value')
        assert cache.get('key') == 'value'

    def test_persist_to_database(self, cache):
        """Should persist to database when requested."""
        cache.set('persistent', 'data', persist=True)

        # Clear memory cache
        cache.memory.clear()

        # Should still get from database
        assert cache.get('persistent') == 'data'

    def test_promote_to_memory(self, cache):
        """Should promote database values to memory."""
        # Put directly in database
        cache.db_cache.set('db_only', 'value', ttl=300)

        # Get should promote to memory
        cache.get('db_only')

        # Should now be in memory
        assert cache.memory.get('db_only') == 'value'

    def test_delete_from_all_tiers(self, cache):
        """Should delete from both tiers."""
        cache.set('key', 'value', persist=True)
        cache.delete('key')

        assert cache.memory.get('key') is None
        assert cache.db_cache.get('key') is None

    def test_invalidate_pattern(self, cache):
        """Should invalidate keys matching pattern."""
        cache.set('stats_2024_01', 'data1', persist=True)
        cache.set('stats_2024_02', 'data2', persist=True)
        cache.set('other_key', 'data3', persist=True)

        count = cache.invalidate_pattern('stats_')

        assert count >= 2
        assert cache.get('stats_2024_01') is None
        assert cache.get('other_key') == 'data3'

    def test_clear_all_tiers(self, cache):
        """Should clear both memory and database cache."""
        cache.set('mem', 'value')
        cache.set('db', 'value', persist=True)

        count = cache.clear()
        assert count >= 2

    def test_cleanup(self, cache):
        """Should cleanup expired from both tiers."""
        cache.memory.set('expired', 'value', ttl=1)
        cache.db_cache.set('also_expired', 'value', ttl=1)

        time.sleep(1.1)
        removed = cache.cleanup()

        assert removed >= 2

    def test_stats(self, cache):
        """Should return stats from all tiers."""
        cache.set('a', '1')
        cache.set('b', '2')

        stats = cache.stats()
        assert 'memory' in stats
        assert 'database_enabled' in stats
        assert stats['database_enabled'] is True


class TestCachedDecorator:
    """Test cases for @cached decorator."""

    def test_caches_result(self):
        """Should cache function results."""
        call_count = 0

        @cached(ttl=60)
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute
        result1 = expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_func(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    def test_different_args_different_cache(self):
        """Should cache separately for different arguments."""
        @cached(ttl=60)
        def func(x):
            return x * 2

        assert func(1) == 2
        assert func(2) == 4

    def test_invalidate_method(self):
        """Should have invalidate method."""
        @cached(ttl=60, key_prefix='test_func')
        def func():
            return 'value'

        func()  # Cache the result
        func.invalidate()  # Clear cache

        # Next call should re-execute
        # (Would need to track call count to verify)

    def test_key_prefix(self):
        """Should use key prefix for cache key."""
        @cached(ttl=60, key_prefix='custom_prefix')
        def func():
            return 'value'

        func()  # This should work without error


class TestMemoize:
    """Test cases for @memoize decorator."""

    def test_memoizes_result(self):
        """Should memoize function results."""
        call_count = 0

        @memoize
        def fib(n):
            nonlocal call_count
            call_count += 1
            if n < 2:
                return n
            return fib(n - 1) + fib(n - 2)

        result = fib(10)
        assert result == 55
        # Without memoization, fib(10) would make many more calls
        assert call_count <= 11  # At most n+1 calls
