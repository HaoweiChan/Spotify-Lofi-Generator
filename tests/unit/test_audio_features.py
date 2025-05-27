#!/usr/bin/env python3
"""
Unit tests for AudioFeatures model.
"""

import pytest
from src.models.audio_features import AudioFeatures

class TestAudioFeatures:
    """Unit tests for AudioFeatures model."""
    
    def test_audio_features_creation_with_all_fields(self):
        """Test creating AudioFeatures with all fields."""
        features = AudioFeatures(
            energy=0.8,
            valence=0.6,
            danceability=0.7,
            acousticness=0.3,
            instrumentalness=0.2,
            tempo=120.0,
            loudness=-8.0,
            speechiness=0.05,
            liveness=0.1,
            key=5,
            mode=1,
            time_signature=4,
            duration_ms=240000
        )
        
        assert features.energy == 0.8
        assert features.valence == 0.6
        assert features.danceability == 0.7
        assert features.acousticness == 0.3
        assert features.instrumentalness == 0.2
        assert features.tempo == 120.0
        assert features.loudness == -8.0
        assert features.speechiness == 0.05
        assert features.liveness == 0.1
        assert features.key == 5
        assert features.mode == 1
        assert features.time_signature == 4
        assert features.duration_ms == 240000
    
    def test_audio_features_creation_with_minimal_fields(self):
        """Test creating AudioFeatures with minimal required fields."""
        features = AudioFeatures(energy=0.5, valence=0.5)
        
        assert features.energy == 0.5
        assert features.valence == 0.5
        # Other fields should be None or have default values
        assert features.tempo is None
        assert features.loudness is None
    
    def test_audio_features_validation_valid_ranges(self):
        """Test that valid ranges are accepted."""
        # Test boundary values
        features = AudioFeatures(
            energy=0.0,  # Min value
            valence=1.0,  # Max value
            tempo=50.0,   # Min tempo
            loudness=-60.0  # Min loudness
        )
        
        assert features.energy == 0.0
        assert features.valence == 1.0
        assert features.tempo == 50.0
        assert features.loudness == -60.0
    
    def test_audio_features_to_dict(self):
        """Test converting AudioFeatures to dictionary."""
        features = AudioFeatures(
            energy=0.8,
            valence=0.6,
            tempo=120.0,
            loudness=-8.0
        )
        
        features_dict = features.to_dict()
        
        assert isinstance(features_dict, dict)
        assert features_dict["energy"] == 0.8
        assert features_dict["valence"] == 0.6
        assert features_dict["tempo"] == 120.0
        assert features_dict["loudness"] == -8.0
    
    def test_audio_features_from_dict(self):
        """Test creating AudioFeatures from dictionary."""
        features_dict = {
            "energy": 0.7,
            "valence": 0.5,
            "danceability": 0.8,
            "tempo": 130.0
        }
        
        features = AudioFeatures.from_dict(features_dict)
        
        assert features.energy == 0.7
        assert features.valence == 0.5
        assert features.danceability == 0.8
        assert features.tempo == 130.0
    
    def test_audio_features_similarity_calculation(self):
        """Test similarity calculation between AudioFeatures."""
        # Create features with all values needed for similarity calculation
        features1 = AudioFeatures(
            energy=0.8, 
            valence=0.6, 
            tempo=120.0,
            danceability=0.7,
            acousticness=0.3,
            instrumentalness=0.2,
            loudness=-10.0
        )
        features2 = AudioFeatures(
            energy=0.7, 
            valence=0.5, 
            tempo=125.0,
            danceability=0.8,
            acousticness=0.4,
            instrumentalness=0.1,
            loudness=-12.0
        )
        
        similarity = features1.similarity(features2)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_audio_features_similarity_identical(self):
        """Test similarity calculation for identical features."""
        # Create features with all values needed for similarity calculation
        features1 = AudioFeatures(
            energy=0.8, 
            valence=0.6, 
            tempo=120.0,
            danceability=0.7,
            acousticness=0.3,
            instrumentalness=0.2,
            loudness=-10.0
        )
        features2 = AudioFeatures(
            energy=0.8, 
            valence=0.6, 
            tempo=120.0,
            danceability=0.7,
            acousticness=0.3,
            instrumentalness=0.2,
            loudness=-10.0
        )
        
        similarity = features1.similarity(features2)
        
        # Should be very close to 1.0 for identical features
        assert similarity > 0.99
    
    def test_audio_features_normalization(self):
        """Test that features are validated but not normalized on creation."""
        # The implementation validates ranges and raises errors, doesn't normalize
        # Test with slightly out-of-range values that should raise errors
        with pytest.raises(ValueError, match="Energy must be between"):
            AudioFeatures(energy=1.5)
        
        with pytest.raises(ValueError, match="Valence must be between"):
            AudioFeatures(valence=-0.5)
        
        with pytest.raises(ValueError, match="Tempo must be between"):
            AudioFeatures(tempo=250.0)
    
    def test_audio_features_string_representation(self):
        """Test string representation of AudioFeatures."""
        features = AudioFeatures(energy=0.8, valence=0.6, tempo=120.0)
        
        str_repr = str(features)
        
        assert isinstance(str_repr, str)
        # Should contain the dataclass name and some values
        assert "AudioFeatures" in str_repr
    
    def test_audio_features_equality(self):
        """Test equality comparison between AudioFeatures."""
        features1 = AudioFeatures(energy=0.8, valence=0.6)
        features2 = AudioFeatures(energy=0.8, valence=0.6)
        features3 = AudioFeatures(energy=0.7, valence=0.6)
        
        assert features1 == features2
        assert features1 != features3
    
    def test_audio_features_validation_error(self):
        """Test that validation errors are raised for invalid values."""
        # Test that out-of-range values raise validation errors
        with pytest.raises(ValueError, match="Energy must be between"):
            AudioFeatures(energy=10.0)
        
        with pytest.raises(ValueError, match="Valence must be between"):
            AudioFeatures(valence=-10.0) 