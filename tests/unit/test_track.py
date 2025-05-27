#!/usr/bin/env python3
"""
Unit tests for Track model.
"""

import pytest
from src.models.track import Track
from src.models.audio_features import AudioFeatures
from src.models.license_info import LicenseInfo

class TestTrack:
    """Unit tests for Track model."""
    
    def test_track_creation_minimal(self):
        """Test creating Track with minimal required fields."""
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        assert track.id == "test123"
        assert track.name == "Test Song"
        assert track.artist == "Test Artist"
        assert track.artists == ["Test Artist"]
        assert track.album == "Test Album"
        assert track.duration_ms == 180000
        assert track.provider == "spotify"
    
    def test_track_creation_with_audio_features(self):
        """Test creating Track with audio features."""
        audio_features = AudioFeatures(energy=0.8, valence=0.6, tempo=120.0)
        
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
        
        assert track.audio_features == audio_features
        assert track.audio_features.energy == 0.8
    
    def test_track_creation_with_license_info(self):
        """Test creating Track with license information."""
        license_info = LicenseInfo.create_creative_commons(
            attribution_required=True,
            commercial_allowed=True
        )
        
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            license_info=license_info,
            provider="spotify"
        )
        
        assert track.license_info == license_info
        assert track.license_info.commercial_use_allowed is True
    
    def test_track_duration_formatted(self):
        """Test formatted duration property."""
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,  # 3 minutes
            provider="spotify"
        )
        
        assert track.duration_formatted == "3:00"
        
        # Test different durations
        track.duration_ms = 245000  # 4:05
        assert track.duration_formatted == "4:05"
        
        track.duration_ms = 65000   # 1:05
        assert track.duration_formatted == "1:05"
    
    def test_track_to_dict(self):
        """Test converting Track to dictionary."""
        audio_features = AudioFeatures(energy=0.8, valence=0.6)
        
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            popularity=75,
            explicit=False,
            audio_features=audio_features,
            provider="spotify"
        )
        
        track_dict = track.to_dict()
        
        assert isinstance(track_dict, dict)
        assert track_dict["id"] == "test123"
        assert track_dict["name"] == "Test Song"
        assert track_dict["artist"] == "Test Artist"
        assert track_dict["popularity"] == 75
        assert track_dict["explicit"] is False
        assert "audio_features" in track_dict
    
    def test_track_from_dict(self):
        """Test creating Track from dictionary."""
        track_dict = {
            "id": "test123",
            "name": "Test Song",
            "artist": "Test Artist",
            "artists": ["Test Artist"],
            "album": "Test Album",
            "duration_ms": 180000,
            "popularity": 80,
            "provider": "spotify"
        }
        
        track = Track.from_dict(track_dict)
        
        assert track.id == "test123"
        assert track.name == "Test Song"
        assert track.popularity == 80
        assert track.provider == "spotify"
    
    def test_track_equality(self):
        """Test equality comparison between tracks."""
        track1 = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        track2 = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        track3 = Track(
            id="test456",
            name="Different Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        assert track1 == track2
        assert track1 != track3
    
    def test_track_string_representation(self):
        """Test string representation of Track."""
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        str_repr = str(track)
        
        assert isinstance(str_repr, str)
        assert "Track" in str_repr
        assert "test123" in str_repr
    
    def test_track_multiple_artists(self):
        """Test track with multiple artists."""
        track = Track(
            id="test123",
            name="Collaboration Song",
            artist="Artist 1",
            artists=["Artist 1", "Artist 2", "Artist 3"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        assert track.artist == "Artist 1"  # Primary artist
        assert len(track.artists) == 3
        assert "Artist 2" in track.artists
        assert "Artist 3" in track.artists
    
    def test_track_display_name(self):
        """Test track display name property."""
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        assert track.display_name == "Test Song - Test Artist"
    
    def test_track_is_licensed_for_business(self):
        """Test business licensing check."""
        # Track without license info
        track = Track(
            id="test123",
            name="Test Song",
            artist="Test Artist",
            artists=["Test Artist"],
            album="Test Album",
            duration_ms=180000,
            provider="spotify"
        )
        
        assert track.is_licensed_for_business is False
        
        # Track with license info allowing business use
        license_info = LicenseInfo.create_creative_commons(
            attribution_required=True,
            commercial_allowed=True
        )
        track.add_license_info(license_info)
        
        assert track.is_licensed_for_business is True
    
    def test_track_similarity_score(self):
        """Test similarity score calculation."""
        # Create audio features with all required values for similarity calculation
        audio_features = AudioFeatures(
            energy=0.8, 
            valence=0.6, 
            tempo=120.0,
            danceability=0.7,
            acousticness=0.3,
            instrumentalness=0.2,
            loudness=-10.0
        )
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
        
        # Create target features with all required values
        target_features = AudioFeatures(
            energy=0.7, 
            valence=0.5, 
            tempo=125.0,
            danceability=0.8,
            acousticness=0.4,
            instrumentalness=0.1,
            loudness=-12.0
        )
        similarity = track.similarity_score(target_features)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_track_from_spotify_data(self):
        """Test creating track from Spotify API data."""
        spotify_data = {
            "id": "spotify123",
            "name": "Spotify Song",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "album": {"name": "Spotify Album"},
            "duration_ms": 200000,
            "popularity": 80,
            "explicit": True,
            "preview_url": "https://preview.url",
            "external_urls": {"spotify": "https://spotify.url"}
        }
        
        track = Track.from_spotify_data(spotify_data)
        
        assert track.id == "spotify123"
        assert track.name == "Spotify Song"
        assert track.artist == "Artist 1"
        assert track.artists == ["Artist 1", "Artist 2"]
        assert track.album == "Spotify Album"
        assert track.duration_ms == 200000
        assert track.popularity == 80
        assert track.explicit is True
        assert track.provider == "spotify" 