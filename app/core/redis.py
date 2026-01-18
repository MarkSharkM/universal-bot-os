"""
Redis caching utilities for Universal Bot OS.
Provides caching for translations, partners, bot configs, etc.
"""
import redis
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager with connection pooling."""
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    def connect(self):
        """
        Connect to Redis server.
        Safe to call multiple times - will reuse existing connection.
        """
        if self._connected and self._client:
            return
        
        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            self._connected = True
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Caching disabled.")
            self._connected = False
            self._client = None
    
    def disconnect(self):
        """Disconnect from Redis."""
        if self._pool:
            self._pool.disconnect()
        self._connected = False
        self._client = None
        logger.info("Redis cache disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/error
        """
        if not self.is_connected:
            return None
        
        try:
            value = self._client.get(key)
            if value:
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.warning(f"Redis GET error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            # Serialize to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis SET error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., "translations:*")
        
        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis DELETE_PATTERN error for pattern '{pattern}': {e}")
            return 0
    
    def flush_all(self) -> bool:
        """
        Flush all cache (use with caution!).
        
        Returns:
            True if successful
        """
        if not self.is_connected:
            return False
        
        try:
            self._client.flushdb()
            logger.info("Redis cache flushed")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSH error: {e}")
            return False


# Global cache instance
cache = RedisCache()


def cached(key_prefix: str, ttl: int = 3600):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
    
    Example:
        @cached("translations", ttl=3600)
        def get_translation(key: str, lang: str):
            return db.query(...).first()
    
    Usage:
        # First call - hits database
        translation = get_translation("welcome", "uk")
        
        # Second call - returns from cache
        translation = get_translation("welcome", "uk")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function args
            # Format: prefix:arg1:arg2:kwarg1=value1
            cache_key_parts = [key_prefix]
            cache_key_parts.extend(str(arg) for arg in args)
            cache_key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(cache_key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value
            
            # Cache miss - call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        # Add cache invalidation method
        wrapper.invalidate_cache = lambda *args, **kwargs: cache.delete(
            ":".join([key_prefix] + [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())])
        )
        
        return wrapper
    return decorator


# Initialize cache on import
cache.connect()
