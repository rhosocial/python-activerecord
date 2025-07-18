# tests/rhosocial/activerecord_test/relation/test_cache.py
"""Tests for cache module."""

import time

from rhosocial.activerecord.relation.cache import (
    CacheConfig,
    GlobalCacheConfig,
    CacheEntry,
    RelationCache
)


def test_cache_config():
    """Test CacheConfig initialization and defaults."""
    config = CacheConfig()
    assert config.enabled is True
    assert config.ttl == 300
    assert config.max_size == 1000

    custom_config = CacheConfig(enabled=False, ttl=60, max_size=100)
    assert custom_config.enabled is False
    assert custom_config.ttl == 60
    assert custom_config.max_size == 100


def test_global_cache_config():
    """Test GlobalCacheConfig singleton and configuration."""
    config1 = GlobalCacheConfig()
    config2 = GlobalCacheConfig()
    assert config1 is config2

    GlobalCacheConfig.set_config(enabled=False, ttl=60)
    assert config1.config.enabled is False
    assert config1.config.ttl == 60
    assert config2.config.enabled is False
    assert config2.config.ttl == 60


def test_cache_entry():
    """Test CacheEntry creation and expiration."""
    entry = CacheEntry("test", ttl=1)
    assert entry.value == "test"
    assert not entry.is_expired()

    # Test expiration
    time.sleep(1.1)
    assert entry.is_expired()

    # Test no TTL
    entry = CacheEntry("test", ttl=None)
    assert not entry.is_expired()


def test_relation_cache():
    """Test RelationCache operations."""
    cache = RelationCache(CacheConfig(ttl=1))
    cache.relation_name = "test_relation"

    # Test set and get
    instance = object()
    cache.set(instance, "test_value")
    assert cache.get(instance) == "test_value"

    # Test expiration
    time.sleep(1.1)
    assert cache.get(instance) is None

    # Test delete
    cache.set(instance, "test_value")
    cache.delete(instance)
    assert cache.get(instance) is None

    # Test clear
    cache.set(instance, "test_value")
    cache.clear()
    assert cache.get(instance) is None


def test_relation_cache_max_size():
    """Test RelationCache max size handling."""
    cache = RelationCache(CacheConfig(max_size=2))
    cache.relation_name = "test_relation"

    # Add entries up to max size
    instance1 = object()
    instance2 = object()
    instance3 = object()

    cache.set(instance1, "value1")
    cache.set(instance2, "value2")
    assert cache.get(instance1) == "value1"
    assert cache.get(instance2) == "value2"

    # Add one more entry, should clear cache
    cache.set(instance3, "value3")
    assert cache.get(instance1) is None
    assert cache.get(instance2) is None
    assert cache.get(instance3) == "value3"


def test_relation_cache_disabled():
    """Test RelationCache when disabled."""
    cache = RelationCache(CacheConfig(enabled=False))
    cache.relation_name = "test_relation"

    instance = object()
    cache.set(instance, "test_value")
    assert cache.get(instance) is None


def test_concurrent_cache_access():
    """Test thread-safe cache operations."""
    import threading

    cache = RelationCache(CacheConfig(max_size=100))
    cache.relation_name = "test"

    def cache_worker():
        for i in range(100):
            instance = object()
            cache.set(instance, f"value_{i}")
            assert cache.get(instance) == f"value_{i}"

    threads = [
        threading.Thread(target=cache_worker)
        for _ in range(5)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_cache_memory_management():
    """Test cache memory management under load."""
    cache = RelationCache(CacheConfig(max_size=5))
    cache.relation_name = "test"

    # Fill cache beyond max size
    for i in range(10):
        instance = object()
        cache.set(instance, f"value_{i}")

    # Verify cache size is maintained
    assert len(cache._cache) <= 5
