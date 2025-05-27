"""
Pytest configuration and shared fixtures for the music playlist generator tests.
"""

import pytest
import asyncio

from src.models.track import Track
from src.models.audio_features import AudioFeatures
from src.models.license_info import LicenseInfo
from config.settings import Settings
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.spotify_client_id = "test_client_id"
    settings.spotify_client_secret = "test_client_secret"
    settings.youtube_api_key = "test_youtube_key"
    settings.audio_features = {
        "similarity_threshold": 0.8,
        "tempo_tolerance": 10.0,
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
    return settings

@pytest.fixture
def sample_audio_features():
    """Sample audio features for testing."""
    return AudioFeatures(
        energy=0.8,
        valence=0.6,
        danceability=0.7,
        acousticness=0.3,
        instrumentalness=0.2,
        tempo=120.0,
        loudness=-8.0
    )

@pytest.fixture
def sample_track():
    """Sample track for testing."""
    return Track(
        id="test_track_123",
        name="Test Song",
        artist="Test Artist",
        artists=["Test Artist"],
        album="Test Album",
        duration_ms=180000,
        popularity=75,
        explicit=False,
        provider="spotify"
    )

@pytest.fixture
def sample_license_info():
    """Sample license info for testing."""
    return LicenseInfo.create_creative_commons(
        attribution_required=True,
        commercial_allowed=True
    )

@pytest.fixture
def mock_spotify_client():
    """Mock Spotify API client."""
    client = AsyncMock()
    client.search_tracks.return_value = []
    client.get_audio_features.return_value = None
    return client

@pytest.fixture
def mock_youtube_client():
    """Mock YouTube API client."""
    client = AsyncMock()
    client.search_video.return_value = None
    client.check_content_id.return_value = False
    return client 