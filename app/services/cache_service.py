"""
CACHE SERVICE - Redis-based caching for frequently accessed data

This service provides caching functionality to improve performance
by reducing database queries and expensive computations.
"""

import json
import hashlib
from typing import Optional, Any, Dict, List
from functools import wraps
import redis
from app.utils import get_logger, Constants

logger = get_logger(__name__)

class CacheService:
    """Service class for caching operations."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis (graceful fallback if not available)."""
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis cache is available."""
        return self.redis_client is not None
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self.is_available():
            return False
        
        try:
            serialized_value = json.dumps(value)
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.is_available():
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def cache_prompt_evaluation(self, prompt_text: str, response_text: Optional[str], result: Dict[str, Any]) -> bool:
        """Cache prompt evaluation results."""
        key = self._generate_key("eval", prompt_text, response_text or "")
        return self.set(key, result, ttl=1800)  # 30 minutes
    
    def get_cached_evaluation(self, prompt_text: str, response_text: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get cached prompt evaluation results."""
        key = self._generate_key("eval", prompt_text, response_text or "")
        return self.get(key)
    
    def cache_analytics_report(self, window_days: int, result: Dict[str, Any]) -> bool:
        """Cache analytics report results."""
        key = self._generate_key("report", window_days)
        return self.set(key, result, ttl=900)  # 15 minutes
    
    def get_cached_report(self, window_days: int) -> Optional[Dict[str, Any]]:
        """Get cached analytics report."""
        key = self._generate_key("report", window_days)
        return self.get(key)
    
    def invalidate_prompt_cache(self, prompt_id: int):
        """Invalidate all cache entries related to a prompt."""
        if not self.is_available():
            return
        
        try:
            # This is a simple approach - in production you might want
            # more sophisticated cache invalidation patterns
            pattern = f"*prompt_{prompt_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

# Global cache instance
cache_service = CacheService()

def cached(ttl: int = 3600, key_prefix: str = "default"):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache_service.is_available():
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = cache_service._generate_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator
