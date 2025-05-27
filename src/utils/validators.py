"""
Input validation utilities for audio features and API parameters.
"""

from typing import Dict, Any, List, Optional, Union
import re

class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass

class AudioFeaturesValidator:
    """Validator for audio features input."""
    
    VALID_FEATURES = {
        "energy": (0.0, 1.0),
        "valence": (0.0, 1.0),
        "danceability": (0.0, 1.0),
        "acousticness": (0.0, 1.0),
        "instrumentalness": (0.0, 1.0),
        "liveness": (0.0, 1.0),
        "speechiness": (0.0, 1.0),
        "tempo": (50.0, 200.0),
        "loudness": (-60.0, 0.0),
        "key": (0, 11),
        "mode": (0, 1),
        "time_signature": (3, 7)
    }
    
    @classmethod
    def validate(cls, features: Dict[str, Union[float, int]]) -> Dict[str, float]:
        """
        Validate audio features dictionary.
        
        Args:
            features: Dictionary of audio features
            
        Returns:
            Validated and normalized features dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(features, dict):
            raise ValidationError("Audio features must be a dictionary")
            
        validated = {}
        
        for feature, value in features.items():
            if feature not in cls.VALID_FEATURES:
                raise ValidationError(f"Unknown audio feature: {feature}")
                
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid value for {feature}: must be numeric")
                
            min_val, max_val = cls.VALID_FEATURES[feature]
            if not min_val <= value <= max_val:
                raise ValidationError(
                    f"Invalid value for {feature}: {value} "
                    f"(must be between {min_val} and {max_val})"
                )
                
            validated[feature] = value
            
        return validated

class PlaylistValidator:
    """Validator for playlist generation parameters."""
    
    @classmethod
    def validate_length(cls, length: int) -> int:
        """Validate playlist length."""
        if not isinstance(length, int):
            raise ValidationError("Playlist length must be an integer")
            
        if not 1 <= length <= 100:
            raise ValidationError("Playlist length must be between 1 and 100")
            
        return length
        
    @classmethod
    def validate_provider(cls, provider: str) -> str:
        """Validate music provider."""
        valid_providers = ["spotify", "apple_music"]
        
        if not isinstance(provider, str):
            raise ValidationError("Provider must be a string")
            
        provider = provider.lower()
        if provider not in valid_providers:
            raise ValidationError(f"Invalid provider: {provider}. Valid options: {valid_providers}")
            
        return provider
        
    @classmethod
    def validate_diversity(cls, diversity: float) -> float:
        """Validate diversity parameter."""
        try:
            diversity = float(diversity)
        except (ValueError, TypeError):
            raise ValidationError("Diversity must be a number")
            
        if not 0.0 <= diversity <= 1.0:
            raise ValidationError("Diversity must be between 0.0 and 1.0")
            
        return diversity
        
    @classmethod
    def validate_popularity_range(cls, popularity_range: Optional[tuple]) -> Optional[tuple]:
        """Validate popularity range."""
        if popularity_range is None:
            return None
            
        if not isinstance(popularity_range, (list, tuple)) or len(popularity_range) != 2:
            raise ValidationError("Popularity range must be a tuple/list of two numbers")
            
        try:
            min_pop, max_pop = float(popularity_range[0]), float(popularity_range[1])
        except (ValueError, TypeError):
            raise ValidationError("Popularity range values must be numeric")
            
        if not 0 <= min_pop <= 100 or not 0 <= max_pop <= 100:
            raise ValidationError("Popularity values must be between 0 and 100")
            
        if min_pop > max_pop:
            raise ValidationError("Minimum popularity cannot be greater than maximum")
            
        return (min_pop, max_pop)

class StringValidator:
    """Validator for string inputs."""
    
    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate search query string."""
        if not isinstance(query, str):
            raise ValidationError("Search query must be a string")
            
        query = query.strip()
        if not query:
            raise ValidationError("Search query cannot be empty")
            
        if len(query) > 500:
            raise ValidationError("Search query too long (max 500 characters)")
            
        return query
        
    @classmethod
    def validate_genre(cls, genre: Optional[str]) -> Optional[str]:
        """Validate genre string."""
        if genre is None:
            return None
            
        if not isinstance(genre, str):
            raise ValidationError("Genre must be a string")
            
        genre = genre.strip()
        if not genre:
            return None
            
        # Basic genre validation (alphanumeric, spaces, hyphens)
        if not re.match(r'^[a-zA-Z0-9\s\-]+$', genre):
            raise ValidationError("Genre contains invalid characters")
            
        return genre.lower()
        
    @classmethod
    def validate_mood(cls, mood: Optional[str]) -> Optional[str]:
        """Validate mood string."""
        if mood is None:
            return None
            
        if not isinstance(mood, str):
            raise ValidationError("Mood must be a string")
            
        mood = mood.strip()
        if not mood:
            return None
            
        # Basic mood validation
        if not re.match(r'^[a-zA-Z0-9\s\-]+$', mood):
            raise ValidationError("Mood contains invalid characters")
            
        return mood.lower()

def validate_playlist_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a complete playlist generation request.
    
    Args:
        request_data: Dictionary containing request parameters
        
    Returns:
        Validated request data
        
    Raises:
        ValidationError: If validation fails
    """
    validated = {}
    
    # Validate audio features
    if "audio_features" in request_data:
        validated["audio_features"] = AudioFeaturesValidator.validate(
            request_data["audio_features"]
        )
    else:
        raise ValidationError("Audio features are required")
        
    # Validate playlist length
    length = request_data.get("length", 20)
    validated["length"] = PlaylistValidator.validate_length(length)
    
    # Validate provider
    provider = request_data.get("provider", "spotify")
    validated["provider"] = PlaylistValidator.validate_provider(provider)
    
    # Validate diversity
    diversity = request_data.get("diversity", 0.3)
    validated["diversity"] = PlaylistValidator.validate_diversity(diversity)
    
    # Validate popularity range
    popularity_range = request_data.get("popularity_range")
    validated["popularity_range"] = PlaylistValidator.validate_popularity_range(popularity_range)
    
    # Validate genre
    genre = request_data.get("genre")
    validated["genre"] = StringValidator.validate_genre(genre)
    
    # Validate mood
    mood = request_data.get("mood")
    validated["mood"] = StringValidator.validate_mood(mood)
    
    # Validate check_licensing flag
    check_licensing = request_data.get("check_licensing", False)
    if not isinstance(check_licensing, bool):
        raise ValidationError("check_licensing must be a boolean")
    validated["check_licensing"] = check_licensing
    
    return validated


def validate_track_data(track_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate track data dictionary.
    
    Args:
        track_data: Dictionary containing track information
        
    Returns:
        Validated track data
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(track_data, dict):
        raise ValidationError("Track data must be a dictionary")
    
    required_fields = ["id", "name", "artists", "album", "duration_ms"]
    for field in required_fields:
        if field not in track_data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate ID
    if not isinstance(track_data["id"], str) or not track_data["id"].strip():
        raise ValidationError("Track ID must be a non-empty string")
    
    # Validate name
    if not isinstance(track_data["name"], str) or not track_data["name"].strip():
        raise ValidationError("Track name must be a non-empty string")
    
    # Validate artists
    if not isinstance(track_data["artists"], list) or not track_data["artists"]:
        raise ValidationError("Artists must be a non-empty list")
    
    # Validate album
    if not isinstance(track_data["album"], str):
        raise ValidationError("Album must be a string")
    
    # Validate duration
    if not isinstance(track_data["duration_ms"], (int, float)) or track_data["duration_ms"] <= 0:
        raise ValidationError("Duration must be a positive number")
    
    return track_data


def validate_audio_features(features_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate audio features data dictionary.
    
    Args:
        features_data: Dictionary containing audio features
        
    Returns:
        Validated audio features data
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(features_data, dict):
        raise ValidationError("Audio features data must be a dictionary")
    
    # Use the AudioFeaturesValidator for validation
    return AudioFeaturesValidator.validate(features_data)


def validate_playlist_data(playlist_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate playlist data dictionary.
    
    Args:
        playlist_data: Dictionary containing playlist information
        
    Returns:
        Validated playlist data
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(playlist_data, dict):
        raise ValidationError("Playlist data must be a dictionary")
    
    required_fields = ["name", "tracks"]
    for field in required_fields:
        if field not in playlist_data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate name
    if not isinstance(playlist_data["name"], str) or not playlist_data["name"].strip():
        raise ValidationError("Playlist name must be a non-empty string")
    
    # Validate tracks
    if not isinstance(playlist_data["tracks"], list):
        raise ValidationError("Tracks must be a list")
    
    # Validate each track
    for i, track in enumerate(playlist_data["tracks"]):
        try:
            validate_track_data(track)
        except ValidationError as e:
            raise ValidationError(f"Invalid track at index {i}: {e}")
    
    return playlist_data 