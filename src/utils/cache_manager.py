"""
Cache manager utility for API response caching.
Provides Redis-based caching with TTL support and fallback to in-memory cache.
"""

import json
import logging
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CacheManager:
    """Cache manager with Redis backend and in-memory fallback."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL (optional)
        """
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, tuple] = {}  # key -> (value, expires_at)
        self.max_memory_items = 1000
        
    async def connect(self):
        """Connect to Redis if URL is provided."""
        if self.redis_url:
            try:
                self.redis = redis.from_url(self.redis_url)
                await self.redis.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using memory cache")
                self.redis = None
                
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Try Redis first
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                
        # Fallback to memory cache
        if key in self.memory_cache:
            value, expires_at = self.memory_cache[key]
            if datetime.now() < expires_at:
                return value
            else:
                del self.memory_cache[key]
                
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds."""
        serialized_value = json.dumps(value, default=str)
        
        # Try Redis first
        if self.redis:
            try:
                await self.redis.setex(key, ttl, serialized_value)
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                
        # Fallback to memory cache
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.memory_cache[key] = (value, expires_at)
        
        # Cleanup old entries if memory cache is too large
        if len(self.memory_cache) > self.max_memory_items:
            await self._cleanup_memory_cache()
            
    async def delete(self, key: str):
        """Delete value from cache."""
        # Try Redis first
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                
        # Remove from memory cache
        self.memory_cache.pop(key, None)
        
    async def clear(self):
        """Clear all cache entries."""
        # Clear Redis
        if self.redis:
            try:
                await self.redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
                
        # Clear memory cache
        self.memory_cache.clear()
        
    async def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self.memory_cache.items()
            if now >= expires_at
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
            
        # If still too many items, remove oldest entries
        if len(self.memory_cache) > self.max_memory_items:
            items_to_remove = len(self.memory_cache) - self.max_memory_items + 100
            keys_to_remove = list(self.memory_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.memory_cache[key]
                
    def get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments."""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts) 