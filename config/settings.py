"""
Application settings and configuration management.
Handles environment variables, API configurations, and application defaults.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class APIConfig:
    """Configuration for external API services."""
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 100

@dataclass
class CacheConfig:
    """Configuration for caching system."""
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600  # 1 hour
    track_ttl: int = 86400   # 24 hours
    features_ttl: int = 604800  # 7 days

class Settings:
    """Main application settings."""
    
    def __init__(self):
        # Spotify API Configuration
        self.spotify = APIConfig(
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=100
        )
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        
        # Apple Music API Configuration
        self.apple_music = APIConfig(
            base_url="https://api.music.apple.com/v1",
            rate_limit_per_minute=1000
        )
        self.APPLE_MUSIC_KEY_ID = os.getenv("APPLE_MUSIC_KEY_ID")
        self.APPLE_MUSIC_TEAM_ID = os.getenv("APPLE_MUSIC_TEAM_ID")
        self.APPLE_MUSIC_PRIVATE_KEY = os.getenv("APPLE_MUSIC_PRIVATE_KEY")
        
        # YouTube Data API Configuration
        self.youtube = APIConfig(
            base_url="https://www.googleapis.com/youtube/v3",
            rate_limit_per_minute=10000
        )
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
        
        # Cache Configuration
        self.cache = CacheConfig(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        self.REDIS_URL = os.getenv("REDIS_URL")
        
        # Audio Features Configuration
        self.audio_features = {
            "similarity_threshold": 0.8,
            "tempo_tolerance": 10.0,  # BPM tolerance
            "feature_weights": {
                "energy": 0.2,
                "valence": 0.2,
                "danceability": 0.15,
                "acousticness": 0.15,
                "instrumentalness": 0.1,
                "tempo": 0.1,
                "loudness": 0.1
            }
        }
        
        # Playlist Generation Settings
        self.playlist = {
            "max_length": 100,
            "min_length": 5,
            "diversity_factor": 0.3,  # 0.0 = no diversity, 1.0 = max diversity
            "popularity_weight": 0.1
        }
        
        # Licensing Check Settings
        self.licensing = {
            "check_timeout": 30,
            "batch_size": 10,
            "confidence_threshold": 0.7
        }
        
        # Database Configuration (optional)
        self.database_url = os.getenv("DATABASE_URL")
        
        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def validate(self, require_youtube: bool = False) -> bool:
        """Validate that required configuration is present."""
        required_vars = []
        
        if not self.SPOTIFY_CLIENT_ID:
            required_vars.append("SPOTIFY_CLIENT_ID")
        if not self.SPOTIFY_CLIENT_SECRET:
            required_vars.append("SPOTIFY_CLIENT_SECRET")
        if require_youtube and not self.YOUTUBE_API_KEY:
            required_vars.append("YOUTUBE_API_KEY")
        
        if required_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")
        
        return True
    
    def get_provider_config(self, provider: str) -> APIConfig:
        """Get configuration for a specific music provider."""
        provider_configs = {
            "spotify": self.spotify,
            "apple_music": self.apple_music,
            "youtube": self.youtube
        }
        
        if provider not in provider_configs:
            raise ValueError(f"Unknown provider: {provider}")
        
        return provider_configs[provider] 