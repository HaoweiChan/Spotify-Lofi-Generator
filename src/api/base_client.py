"""
Base API client providing common functionality for all music provider clients.
Includes async HTTP client, retry logic, rate limiting, caching, and error handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import backoff
from src.utils.rate_limiter import RateLimiter
from src.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors."""
    pass

class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""
    pass

class AuthenticationError(APIError):
    """Exception raised when authentication fails."""
    pass

class BaseAPIClient(ABC):
    """Base class for all music provider API clients."""
    
    def __init__(self, base_url: str, rate_limit: int, cache_manager: Optional[CacheManager] = None):
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit)
        self.cache_manager = cache_manager
        self.session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            
    @abstractmethod
    async def authenticate(self) -> str:
        """Authenticate with the API and return access token."""
        pass
        
    async def _get_auth_token(self) -> str:
        """Get valid authentication token, refreshing if necessary."""
        if (self._auth_token is None or 
            self._token_expires_at is None or 
            datetime.now() >= self._token_expires_at):
            self._auth_token = await self.authenticate()
            
        return self._auth_token
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers. Override in subclasses."""
        return {}
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and rate limiting."""
        await self._ensure_session()
        await self.rate_limiter.acquire()
        
        # Ensure we have a valid auth token
        await self._get_auth_token()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)
            
        try:
            async with self.session.request(
                method, url, params=params, json=data, headers=request_headers
            ) as response:
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    raise RateLimitError(f"Rate limit exceeded, retry after {retry_after}s")
                    
                if response.status == 401:
                    # Token might be expired, clear it
                    self._auth_token = None
                    self._token_expires_at = None
                    raise AuthenticationError("Authentication failed")
                    
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise APIError(f"Request failed: {e}")
            
    async def _cached_request(
        self, 
        cache_key: str, 
        method: str, 
        endpoint: str, 
        ttl: int = 3600,
        **kwargs
    ) -> Dict[str, Any]:
        """Make request with caching support."""
        if self.cache_manager:
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
                
        result = await self._make_request(method, endpoint, **kwargs)
        
        if self.cache_manager:
            await self.cache_manager.set(cache_key, result, ttl)
            
        return result
        
    @abstractmethod
    async def search_tracks(
        self, 
        query: str, 
        limit: int = 50,
        audio_features: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Search for tracks based on query and optional audio features."""
        pass
        
    @abstractmethod
    async def get_audio_features(self, track_id: str) -> Dict[str, float]:
        """Get audio features for a specific track."""
        pass
        
    @abstractmethod
    async def get_track_info(self, track_id: str) -> Dict[str, Any]:
        """Get detailed information about a track."""
        pass 