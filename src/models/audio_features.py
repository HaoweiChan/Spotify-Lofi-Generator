"""
Audio features data models for music tracks.
Provides standardized representation of audio characteristics across different providers.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

@dataclass
class AudioFeatures:
    """Standardized audio features for a music track."""
    energy: Optional[float] = None       # Musical intensity (0.0-1.0)
    valence: Optional[float] = None      # Musical positivity (0.0-1.0)
    danceability: Optional[float] = None # Rhythm and beat strength (0.0-1.0)
    acousticness: Optional[float] = None # Acoustic vs electronic (0.0-1.0)
    instrumentalness: Optional[float] = None # Vocal vs instrumental (0.0-1.0)
    tempo: Optional[float] = None        # Beats per minute (50-200)
    loudness: Optional[float] = None     # Overall loudness in dB (-60 to 0)
    speechiness: Optional[float] = None  # Speech-like qualities (0.0-1.0)
    liveness: Optional[float] = None     # Live performance detection (0.0-1.0)
    key: Optional[int] = None            # Musical key (0-11)
    mode: Optional[int] = None           # Major (1) or minor (0)
    time_signature: Optional[int] = None # Time signature (3-7)
    duration_ms: Optional[int] = None    # Track duration in milliseconds
    
    def __post_init__(self):
        """Validate and normalize audio features after initialization."""
        self._validate_ranges()
        self._normalize_features()
    
    def _validate_ranges(self):
        """Validate that all features are within expected ranges."""
        if self.energy is not None and not 0.0 <= self.energy <= 1.0:
            raise ValueError(f"Energy must be between 0.0 and 1.0, got {self.energy}")
        if self.valence is not None and not 0.0 <= self.valence <= 1.0:
            raise ValueError(f"Valence must be between 0.0 and 1.0, got {self.valence}")
        if self.danceability is not None and not 0.0 <= self.danceability <= 1.0:
            raise ValueError(f"Danceability must be between 0.0 and 1.0, got {self.danceability}")
        if self.acousticness is not None and not 0.0 <= self.acousticness <= 1.0:
            raise ValueError(f"Acousticness must be between 0.0 and 1.0, got {self.acousticness}")
        if self.instrumentalness is not None and not 0.0 <= self.instrumentalness <= 1.0:
            raise ValueError(f"Instrumentalness must be between 0.0 and 1.0, got {self.instrumentalness}")
        if self.tempo is not None and not 50.0 <= self.tempo <= 200.0:
            raise ValueError(f"Tempo must be between 50.0 and 200.0 BPM, got {self.tempo}")
        if self.loudness is not None and not -60.0 <= self.loudness <= 0.0:
            raise ValueError(f"Loudness must be between -60.0 and 0.0 dB, got {self.loudness}")
        if self.key is not None and not 0 <= self.key <= 11:
            raise ValueError(f"Key must be between 0 and 11, got {self.key}")
        if self.mode is not None and self.mode not in [0, 1]:
            raise ValueError(f"Mode must be 0 or 1, got {self.mode}")
        if self.time_signature is not None and not 3 <= self.time_signature <= 7:
            raise ValueError(f"Time signature must be between 3 and 7, got {self.time_signature}")
    
    def _normalize_features(self):
        """Normalize features to ensure consistency."""
        # Clamp values to valid ranges
        if self.energy is not None:
            self.energy = max(0.0, min(1.0, self.energy))
        if self.valence is not None:
            self.valence = max(0.0, min(1.0, self.valence))
        if self.danceability is not None:
            self.danceability = max(0.0, min(1.0, self.danceability))
        if self.acousticness is not None:
            self.acousticness = max(0.0, min(1.0, self.acousticness))
        if self.instrumentalness is not None:
            self.instrumentalness = max(0.0, min(1.0, self.instrumentalness))
        if self.tempo is not None:
            self.tempo = max(50.0, min(200.0, self.tempo))
        if self.loudness is not None:
            self.loudness = max(-60.0, min(0.0, self.loudness))
        if self.key is not None:
            self.key = max(0, min(11, self.key))
        if self.mode is not None:
            self.mode = max(0, min(1, self.mode))
        if self.time_signature is not None:
            self.time_signature = max(3, min(7, self.time_signature))
    
    def similarity(self, other: 'AudioFeatures', weights: Dict[str, float] = None) -> float:
        """Calculate similarity score between two audio feature sets."""
        if weights is None:
            weights = {
                "energy": 0.2,
                "valence": 0.2,
                "danceability": 0.15,
                "acousticness": 0.15,
                "instrumentalness": 0.1,
                "tempo": 0.1,
                "loudness": 0.1
            }
        
        # Calculate weighted similarity
        total_similarity = 0.0
        total_weight = 0.0
        
        for feature, weight in weights.items():
            if hasattr(self, feature) and hasattr(other, feature):
                self_val = getattr(self, feature)
                other_val = getattr(other, feature)
                
                # Normalize tempo and loudness for comparison
                if feature == "tempo":
                    self_val = (self_val - 50.0) / 150.0  # Normalize to 0-1
                    other_val = (other_val - 50.0) / 150.0
                elif feature == "loudness":
                    self_val = (self_val + 60.0) / 60.0  # Normalize to 0-1
                    other_val = (other_val + 60.0) / 60.0
                
                # Calculate feature similarity (1 - absolute difference)
                feature_similarity = 1.0 - abs(self_val - other_val)
                total_similarity += feature_similarity * weight
                total_weight += weight
        
        return total_similarity / total_weight if total_weight > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "energy": self.energy,
            "valence": self.valence,
            "danceability": self.danceability,
            "acousticness": self.acousticness,
            "instrumentalness": self.instrumentalness,
            "tempo": self.tempo,
            "loudness": self.loudness,
            "speechiness": self.speechiness,
            "liveness": self.liveness
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioFeatures':
        """Create AudioFeatures from dictionary."""
        return cls(
            energy=data.get("energy", 0.5),
            valence=data.get("valence", 0.5),
            danceability=data.get("danceability", 0.5),
            acousticness=data.get("acousticness", 0.5),
            instrumentalness=data.get("instrumentalness", 0.5),
            tempo=data.get("tempo", 120.0),
            loudness=data.get("loudness", -10.0),
            speechiness=data.get("speechiness"),
            liveness=data.get("liveness")
        )

class AudioFeaturesRequest(BaseModel):
    """Pydantic model for API requests with audio features."""
    energy: Optional[float] = Field(None, ge=0.0, le=1.0)
    valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    danceability: Optional[float] = Field(None, ge=0.0, le=1.0)
    acousticness: Optional[float] = Field(None, ge=0.0, le=1.0)
    instrumentalness: Optional[float] = Field(None, ge=0.0, le=1.0)
    tempo: Optional[float] = Field(None, ge=50.0, le=200.0)
    loudness: Optional[float] = Field(None, ge=-60.0, le=0.0)
    speechiness: Optional[float] = Field(None, ge=0.0, le=1.0)
    liveness: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    def to_audio_features(self) -> AudioFeatures:
        """Convert to AudioFeatures dataclass."""
        return AudioFeatures.from_dict(self.dict(exclude_none=True)) 