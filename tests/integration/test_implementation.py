#!/usr/bin/env python3
"""
Integration tests to verify the implementation works.
Tests basic playlist generation without requiring API keys.
"""

import pytest
import asyncio
from src.services.playlist_generator import PlaylistGenerator
from src.services.licensing_checker import LicensingChecker
from config.settings import Settings

class TestImplementation:
    """Integration tests for the music playlist generator implementation."""
    
    @pytest.mark.asyncio
    async def test_settings_loading(self):
        """Test that settings load successfully."""
        settings = Settings()
        assert settings is not None
        assert hasattr(settings, 'spotify')
        assert hasattr(settings, 'youtube')
        assert hasattr(settings, 'cache')
    
    def test_audio_features_validation(self):
        """Test audio features validation."""
        from src.utils.validators import AudioFeaturesValidator
        
        # Valid features
        valid_features = {
            "energy": 0.8,
            "valence": 0.6,
            "danceability": 0.7,
            "tempo": 120
        }
        validated = AudioFeaturesValidator.validate(valid_features)
        assert validated is not None
        assert validated["energy"] == 0.8
        
        # Invalid features (should raise error)
        with pytest.raises(Exception):
            invalid_features = {"energy": 2.0}  # Out of range
            AudioFeaturesValidator.validate(invalid_features)
    
    def test_data_models(self):
        """Test data models functionality."""
        from src.models.audio_features import AudioFeatures
        from src.models.track import Track
        from src.models.playlist import Playlist
        
        # Create test objects
        audio_features = AudioFeatures(energy=0.8, valence=0.6)
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            audio_features=audio_features,
            provider="spotify"
        )
        playlist = Playlist(
            id="test_playlist_123",
            name="Test Playlist",
            description="A test playlist",
            tracks=[track],
            target_audio_features=audio_features,
            provider="spotify"
        )
        
        assert track.name == "Test Song"
        assert len(playlist.tracks) == 1
        assert playlist.tracks[0].name == "Test Song"
        
        # Test serialization
        playlist_dict = playlist.to_dict()
        assert isinstance(playlist_dict, dict)
        assert playlist_dict["name"] == "Test Playlist"
    
    @pytest.mark.asyncio
    async def test_cache_manager(self):
        """Test cache manager functionality."""
        from src.utils.cache_manager import CacheManager
        
        cache = CacheManager()  # No Redis URL, should use memory cache
        await cache.connect()
        
        # Test basic operations
        await cache.set("test_key", {"test": "value"}, ttl=60)
        result = await cache.get("test_key")
        
        assert result is not None
        assert result.get("test") == "value"
        
        await cache.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiter functionality."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=60)
        
        # Should allow immediate request
        await limiter.acquire()
        assert limiter.available_tokens() >= 0
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initialization without API calls."""
        settings = Settings()
        
        # Test service initialization (without API calls)
        async with PlaylistGenerator(settings) as generator:
            assert generator is not None
            
        async with LicensingChecker(settings) as checker:
            assert checker is not None 