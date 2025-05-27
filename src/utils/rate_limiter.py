"""
Rate limiter utility for managing API request rates.
Implements token bucket algorithm with async support.
"""

import asyncio
import time
from typing import Optional

class RateLimiter:
    """Token bucket rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.tokens = self.burst_size
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            
            # Add tokens based on time passed
            tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return
                
            # Need to wait for tokens
            wait_time = (1 - self.tokens) * (60.0 / self.requests_per_minute)
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.time()
            
    def available_tokens(self) -> float:
        """Get number of available tokens."""
        now = time.time()
        time_passed = now - self.last_update
        tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
        return min(self.burst_size, self.tokens + tokens_to_add) 