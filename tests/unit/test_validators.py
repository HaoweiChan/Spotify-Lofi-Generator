#!/usr/bin/env python3
"""
Unit tests for validators utility module.
"""

import pytest
from src.utils.validators import (
    AudioFeaturesValidator,
    validate_audio_features,
    validate_track_data,
    validate_playlist_data,
    ValidationError
)

class TestAudioFeaturesValidator:
    """Unit tests for AudioFeaturesValidator."""
    
    def test_validate_valid_features(self):
        """Test validation of valid audio features."""
        valid_features = {
            "energy": 0.8,
            "valence": 0.6,
            "danceability": 0.7,
            "acousticness": 0.3,
            "instrumentalness": 0.2,
            "tempo": 120.0,
            "loudness": -8.0
        }
        
        validated = AudioFeaturesValidator.validate(valid_features)
        
        assert validated is not None
        assert validated["energy"] == 0.8
        assert validated["valence"] == 0.6
        assert validated["tempo"] == 120.0
    
    def test_validate_boundary_values(self):
        """Test validation of boundary values."""
        boundary_features = {
            "energy": 0.0,      # Min value
            "valence": 1.0,     # Max value
            "tempo": 50.0,      # Min tempo
            "loudness": -60.0   # Min loudness
        }
        
        validated = AudioFeaturesValidator.validate(boundary_features)
        
        assert validated["energy"] == 0.0
        assert validated["valence"] == 1.0
        assert validated["tempo"] == 50.0
        assert validated["loudness"] == -60.0
    
    def test_validate_invalid_energy(self):
        """Test validation with invalid energy values."""
        # Energy too high
        with pytest.raises(ValidationError, match="energy"):
            AudioFeaturesValidator.validate({"energy": 1.5})
        
        # Energy too low
        with pytest.raises(ValidationError, match="energy"):
            AudioFeaturesValidator.validate({"energy": -0.1})
    
    def test_validate_invalid_valence(self):
        """Test validation with invalid valence values."""
        # Valence too high
        with pytest.raises(ValidationError, match="valence"):
            AudioFeaturesValidator.validate({"valence": 1.2})
        
        # Valence too low
        with pytest.raises(ValidationError, match="valence"):
            AudioFeaturesValidator.validate({"valence": -0.5})
    
    def test_validate_invalid_tempo(self):
        """Test validation with invalid tempo values."""
        # Tempo too high
        with pytest.raises(ValidationError, match="tempo"):
            AudioFeaturesValidator.validate({"tempo": 250.0})
        
        # Tempo too low
        with pytest.raises(ValidationError, match="tempo"):
            AudioFeaturesValidator.validate({"tempo": 30.0})
    
    def test_validate_invalid_loudness(self):
        """Test validation with invalid loudness values."""
        # Loudness too high
        with pytest.raises(ValidationError, match="loudness"):
            AudioFeaturesValidator.validate({"loudness": 5.0})
        
        # Loudness too low
        with pytest.raises(ValidationError, match="loudness"):
            AudioFeaturesValidator.validate({"loudness": -70.0})
    
    def test_validate_empty_features(self):
        """Test validation with empty features."""
        validated = AudioFeaturesValidator.validate({})
        assert validated == {}
    
    def test_validate_partial_features(self):
        """Test validation with partial features."""
        partial_features = {
            "energy": 0.8,
            "tempo": 120.0
        }
        
        validated = AudioFeaturesValidator.validate(partial_features)
        
        assert validated["energy"] == 0.8
        assert validated["tempo"] == 120.0
        assert len(validated) == 2
    
    def test_validate_unknown_features(self):
        """Test validation with unknown feature names."""
        features_with_unknown = {
            "energy": 0.8,
            "unknown_feature": 0.5,  # Should raise error
            "valence": 0.6
        }
        
        # The validator raises an error for unknown features
        with pytest.raises(ValidationError, match="Unknown audio feature"):
            AudioFeaturesValidator.validate(features_with_unknown)

class TestValidateAudioFeatures:
    """Unit tests for validate_audio_features function."""
    
    def test_validate_audio_features_valid(self):
        """Test validate_audio_features with valid input."""
        features = {
            "energy": 0.8,
            "valence": 0.6,
            "tempo": 120.0
        }
        
        # The function returns the validated dict, not a boolean
        result = validate_audio_features(features)
        
        assert isinstance(result, dict)
        assert result["energy"] == 0.8
        assert result["valence"] == 0.6
        assert result["tempo"] == 120.0
    
    def test_validate_audio_features_invalid(self):
        """Test validate_audio_features with invalid input."""
        features = {
            "energy": 2.0,  # Invalid value
            "valence": 0.6
        }
        
        # Should raise ValidationError for invalid values
        with pytest.raises(ValidationError):
            validate_audio_features(features)
    
    def test_validate_audio_features_none(self):
        """Test validate_audio_features with None input."""
        # Should raise ValidationError for None input
        with pytest.raises(ValidationError):
            validate_audio_features(None)
    
    def test_validate_audio_features_not_dict(self):
        """Test validate_audio_features with non-dict input."""
        # Should raise ValidationError for non-dict input
        with pytest.raises(ValidationError):
            validate_audio_features("not a dict")

class TestValidateTrackData:
    """Unit tests for validate_track_data function."""
    
    def test_validate_track_data_valid(self):
        """Test validate_track_data with valid track data."""
        track_data = {
            "id": "test123",
            "name": "Test Song",
            "artist": "Test Artist",
            "artists": ["Test Artist"],
            "album": "Test Album",
            "duration_ms": 180000,
            "provider": "spotify"
        }
        
        # The function returns the validated dict, not a boolean
        result = validate_track_data(track_data)
        
        assert isinstance(result, dict)
        assert result["id"] == "test123"
        assert result["name"] == "Test Song"
    
    def test_validate_track_data_missing_required(self):
        """Test validate_track_data with missing required fields."""
        track_data = {
            "id": "test123",
            "name": "Test Song",
            # Missing artist, album, duration_ms, provider
        }
        
        # Should raise ValidationError for missing fields
        with pytest.raises(ValidationError, match="Missing required field"):
            validate_track_data(track_data)
    
    def test_validate_track_data_invalid_duration(self):
        """Test validate_track_data with invalid duration."""
        track_data = {
            "id": "test123",
            "name": "Test Song",
            "artist": "Test Artist",
            "artists": ["Test Artist"],
            "album": "Test Album",
            "duration_ms": -1000,  # Invalid negative duration
            "provider": "spotify"
        }
        
        # Should raise ValidationError for invalid duration
        with pytest.raises(ValidationError, match="Duration must be a positive number"):
            validate_track_data(track_data)
    
    def test_validate_track_data_none(self):
        """Test validate_track_data with None input."""
        # Should raise ValidationError for None input
        with pytest.raises(ValidationError):
            validate_track_data(None)
    
    def test_validate_track_data_not_dict(self):
        """Test validate_track_data with non-dict input."""
        # Should raise ValidationError for non-dict input
        with pytest.raises(ValidationError):
            validate_track_data("not a dict")

class TestValidatePlaylistData:
    """Unit tests for validate_playlist_data function."""
    
    def test_validate_playlist_data_valid(self):
        """Test validate_playlist_data with valid playlist data."""
        playlist_data = {
            "id": "playlist123",
            "name": "Test Playlist",
            "description": "A test playlist",
            "tracks": [],
            "provider": "spotify"
        }
        
        # The function returns the validated dict, not a boolean
        result = validate_playlist_data(playlist_data)
        
        assert isinstance(result, dict)
        assert result["name"] == "Test Playlist"
    
    def test_validate_playlist_data_missing_required(self):
        """Test validate_playlist_data with missing required fields."""
        playlist_data = {
            "id": "playlist123",
            "name": "Test Playlist",
            # Missing tracks and provider
        }
        
        # Should raise ValidationError for missing fields
        with pytest.raises(ValidationError, match="Missing required field"):
            validate_playlist_data(playlist_data)
    
    def test_validate_playlist_data_invalid_tracks(self):
        """Test validate_playlist_data with invalid tracks field."""
        playlist_data = {
            "id": "playlist123",
            "name": "Test Playlist",
            "description": "A test playlist",
            "tracks": "not a list",  # Should be a list
            "provider": "spotify"
        }
        
        # Should raise ValidationError for invalid tracks type
        with pytest.raises(ValidationError, match="Tracks must be a list"):
            validate_playlist_data(playlist_data)
    
    def test_validate_playlist_data_none(self):
        """Test validate_playlist_data with None input."""
        # Should raise ValidationError for None input
        with pytest.raises(ValidationError):
            validate_playlist_data(None)
    
    def test_validate_playlist_data_not_dict(self):
        """Test validate_playlist_data with non-dict input."""
        # Should raise ValidationError for non-dict input
        with pytest.raises(ValidationError):
            validate_playlist_data("not a dict")

class TestValidationEdgeCases:
    """Unit tests for validation edge cases."""
    
    def test_validate_features_with_string_numbers(self):
        """Test validation with string numbers that should be converted."""
        features = {
            "energy": "0.8",    # String that can be converted to float
            "valence": "0.6",
            "tempo": "120"
        }
        
        # The validator converts string numbers to floats
        validated = AudioFeaturesValidator.validate(features)
        assert validated["energy"] == 0.8
        assert validated["valence"] == 0.6
        assert validated["tempo"] == 120.0
        assert isinstance(validated["energy"], float)
    
    def test_validate_features_with_none_values(self):
        """Test validation with None values."""
        features = {
            "energy": 0.8,
            "valence": None,  # None value
            "tempo": 120.0
        }
        
        # Should raise ValidationError for None values
        with pytest.raises(ValidationError, match="must be numeric"):
            AudioFeaturesValidator.validate(features) 