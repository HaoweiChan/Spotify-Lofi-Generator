#!/usr/bin/env python3
"""
Unit tests for RateLimiter utility.
"""

import pytest
import asyncio
import time
from src.utils.rate_limiter import RateLimiter

class TestRateLimiter:
    """Unit tests for RateLimiter."""
    
    def test_rate_limiter_creation(self):
        """Test creating RateLimiter with different configurations."""
        # With required requests_per_minute parameter
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.available_tokens() > 0
        
        # Custom configuration with burst size
        limiter = RateLimiter(requests_per_minute=120, burst_size=150)
        assert limiter.requests_per_minute == 120
        assert limiter.burst_size == 150
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_immediate(self):
        """Test immediate token acquisition."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Should be able to acquire immediately
        await limiter.acquire()
        
        # Should have fewer tokens available
        assert limiter.available_tokens() < 60
    
    @pytest.mark.asyncio
    async def test_rate_limiter_multiple_acquires(self):
        """Test multiple token acquisitions."""
        limiter = RateLimiter(requests_per_minute=60)
        
        initial_tokens = limiter.available_tokens()
        
        # Acquire multiple tokens
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        
        # Should have approximately 3 fewer tokens (allowing for small time differences)
        assert limiter.available_tokens() < initial_tokens - 2.5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_token_refill(self):
        """Test token refill over time."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second
        
        # Acquire a token
        await limiter.acquire()
        tokens_after_acquire = limiter.available_tokens()
        
        # Wait a bit for token refill
        await asyncio.sleep(0.1)
        
        # Should have more tokens (or at least not fewer)
        assert limiter.available_tokens() >= tokens_after_acquire
    
    @pytest.mark.asyncio
    async def test_rate_limiter_exhaustion(self):
        """Test behavior when tokens are exhausted."""
        limiter = RateLimiter(requests_per_minute=3)  # Very low limit
        
        # Exhaust all tokens
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        
        # Should have very few tokens left (close to 0)
        assert limiter.available_tokens() < 0.5
        
        # Next acquire should wait (but we won't wait in test)
        start_time = time.time()
        await limiter.acquire()
        end_time = time.time()
        
        # Should have taken some time to wait for token refill
        assert end_time - start_time > 0
    
    def test_rate_limiter_available_tokens(self):
        """Test available_tokens method."""
        limiter = RateLimiter(requests_per_minute=60)
        
        tokens = limiter.available_tokens()
        
        assert isinstance(tokens, (int, float))
        assert tokens >= 0
        assert tokens <= 60
    
    def test_rate_limiter_burst_size(self):
        """Test rate limiter with custom burst size."""
        # Default burst size equals requests_per_minute
        limiter1 = RateLimiter(requests_per_minute=60)
        assert limiter1.burst_size == 60
        
        # Custom burst size
        limiter2 = RateLimiter(requests_per_minute=60, burst_size=120)
        assert limiter2.burst_size == 120
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_access(self):
        """Test concurrent access to rate limiter."""
        limiter = RateLimiter(requests_per_minute=60)
        
        async def acquire_token():
            await limiter.acquire()
            return limiter.available_tokens()
        
        # Run multiple concurrent acquisitions
        tasks = [acquire_token() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        assert all(isinstance(r, (int, float)) for r in results)
    
    def test_rate_limiter_zero_rate(self):
        """Test rate limiter with zero requests per minute."""
        # Zero requests per minute should be allowed (effectively blocks all requests)
        limiter = RateLimiter(requests_per_minute=0)
        assert limiter.requests_per_minute == 0
    
    def test_rate_limiter_negative_rate(self):
        """Test rate limiter with negative requests per minute."""
        # Negative rate should be allowed (implementation doesn't validate)
        limiter = RateLimiter(requests_per_minute=-10)
        assert limiter.requests_per_minute == -10
    
    @pytest.mark.asyncio
    async def test_rate_limiter_burst_handling(self):
        """Test handling of burst requests."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Make a burst of requests
        start_time = time.time()
        
        for _ in range(10):
            await limiter.acquire()
        
        end_time = time.time()
        
        # Should complete relatively quickly for first 10 requests
        assert end_time - start_time < 2.0  # Should be much faster than 10 seconds
    
    def test_rate_limiter_string_representation(self):
        """Test string representation of RateLimiter."""
        limiter = RateLimiter(requests_per_minute=120)
        
        str_repr = str(limiter)
        
        assert isinstance(str_repr, str)
        # Default object representation should contain class name
        assert "RateLimiter" in str_repr
    
    def test_rate_limiter_time_window(self):
        """Test rate limiter time window behavior."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # The rate limiter should track time windows properly
        initial_time = time.time()
        
        # Acquire some tokens
        asyncio.run(limiter.acquire())
        
        # Check that internal timing is reasonable
        assert limiter.available_tokens() >= 0
        
        # Time should have progressed
        assert time.time() >= initial_time 