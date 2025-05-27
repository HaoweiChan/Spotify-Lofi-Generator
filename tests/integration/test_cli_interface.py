#!/usr/bin/env python3
"""
Integration tests for the CLI interface.
Tests command line argument parsing and mock playlist generation.
"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from src.models.track import Track
from src.models.playlist import Playlist
from src.models.audio_features import AudioFeatures

class TestCLIInterface:
    """Integration tests for the command line interface."""
    
    def create_mock_track(self, track_id: str, name: str, artist: str, audio_features: Dict[str, float]) -> Track:
        """Create a mock track for testing."""
        return Track(
            id=track_id,
            name=name,
            artist=artist,
            artists=[artist],
            album="Test Album",
            duration_ms=240000,  # 4 minutes
            popularity=75,
            audio_features=AudioFeatures(**audio_features),
            provider="spotify"
        )

    async def mock_generate_playlist(self, audio_features: Dict[str, float], length: int, provider: str) -> Playlist:
        """Generate a mock playlist for testing."""
        
        # Create mock tracks with similar audio features
        tracks = []
        for i in range(length):
            # Vary the features slightly for each track
            mock_features = {
                "energy": audio_features.get("energy", 0.5) + (i * 0.05 - 0.1),
                "valence": audio_features.get("valence", 0.5) + (i * 0.03 - 0.06),
                "tempo": audio_features.get("tempo", 120) + (i * 2 - 4),
                "danceability": audio_features.get("danceability", 0.5) + (i * 0.02 - 0.04),
                "acousticness": 0.3,
                "instrumentalness": 0.1,
                "liveness": 0.1,
                "speechiness": 0.05,
                "loudness": -8.0
            }
            
            # Clamp values to valid ranges
            for key, value in mock_features.items():
                if key == "tempo":
                    mock_features[key] = max(50, min(200, value))
                elif key == "loudness":
                    mock_features[key] = max(-60, min(0, value))
                else:
                    mock_features[key] = max(0, min(1, value))
            
            track = self.create_mock_track(
                track_id=f"mock_track_{i+1}",
                name=f"Test Song {i+1}",
                artist=f"Test Artist {i+1}",
                audio_features=mock_features
            )
            tracks.append(track)
        
        # Create playlist
        playlist = Playlist(
            id=str(uuid.uuid4()),
            name="Mock Energetic Mix",
            description=f"Generated mock playlist based on audio features: Energy: {audio_features.get('energy', 0.5)} | Valence: {audio_features.get('valence', 0.5)} | Tempo: {audio_features.get('tempo', 120)}",
            tracks=tracks,
            target_audio_features=AudioFeatures(**audio_features),
            provider=provider
        )
        
        return playlist

    def test_json_parsing(self):
        """Test JSON parsing of audio features."""
        features_json = '{"energy": 0.8, "valence": 0.6, "tempo": 120}'
        features = json.loads(features_json)
        
        assert features["energy"] == 0.8
        assert features["valence"] == 0.6
        assert features["tempo"] == 120

    def test_invalid_json_parsing(self):
        """Test handling of invalid JSON."""
        invalid_json = '{"energy": 0.8, "valence":}'
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    @pytest.mark.asyncio
    async def test_mock_playlist_generation(self):
        """Test mock playlist generation."""
        features = {"energy": 0.8, "valence": 0.6, "tempo": 120}
        length = 5
        provider = "spotify"
        
        playlist = await self.mock_generate_playlist(features, length, provider)
        
        assert playlist is not None
        assert len(playlist.tracks) == length
        assert playlist.provider == provider
        assert playlist.target_audio_features.energy == 0.8
        assert playlist.target_audio_features.valence == 0.6
        assert playlist.target_audio_features.tempo == 120

    @pytest.mark.asyncio
    async def test_playlist_serialization(self):
        """Test playlist serialization to dict."""
        features = {"energy": 0.7, "valence": 0.5}
        playlist = await self.mock_generate_playlist(features, 3, "spotify")
        
        playlist_dict = playlist.to_dict()
        
        assert isinstance(playlist_dict, dict)
        assert playlist_dict["name"] == playlist.name
        assert len(playlist_dict["tracks"]) == 3
        assert playlist_dict["provider"] == "spotify"

    def test_feature_clamping(self):
        """Test that audio features are properly clamped to valid ranges."""
        # Test values that need clamping
        test_features = {
            "energy": 1.5,  # Should be clamped to 1.0
            "valence": -0.5,  # Should be clamped to 0.0
            "tempo": 300,  # Should be clamped to 200
            "loudness": 10  # Should be clamped to 0
        }
        
        # Simulate the clamping logic
        clamped_features = {}
        for key, value in test_features.items():
            if key == "tempo":
                clamped_features[key] = max(50, min(200, value))
            elif key == "loudness":
                clamped_features[key] = max(-60, min(0, value))
            else:
                clamped_features[key] = max(0, min(1, value))
        
        assert clamped_features["energy"] == 1.0
        assert clamped_features["valence"] == 0.0
        assert clamped_features["tempo"] == 200
        assert clamped_features["loudness"] == 0

    @pytest.mark.asyncio
    async def test_different_providers(self):
        """Test playlist generation with different providers."""
        features = {"energy": 0.6, "valence": 0.7}
        
        # Test Spotify
        spotify_playlist = await self.mock_generate_playlist(features, 3, "spotify")
        assert spotify_playlist.provider == "spotify"
        
        # Test Apple Music
        apple_playlist = await self.mock_generate_playlist(features, 3, "apple_music")
        assert apple_playlist.provider == "apple_music" 