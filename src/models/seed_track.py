"""
Seed track data model representing user-provided track information.
Used for track resolution and similarity-based playlist generation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class SeedTrack:
    """Represents user-provided track information for playlist generation."""
    track_name: str                      # User-provided track name
    artist_name: str                     # User-provided artist name
    album_name: Optional[str] = None     # Optional album name
    year: Optional[int] = None           # Optional release year
    confidence_threshold: float = 0.7    # Minimum confidence for auto-selection
    
    def __post_init__(self):
        """Validate and clean input after initialization."""
        self.track_name = self._clean_string(self.track_name)
        self.artist_name = self._clean_string(self.artist_name)
        if self.album_name:
            self.album_name = self._clean_string(self.album_name)
        
        # Validate confidence threshold
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(f"Confidence threshold must be between 0.0 and 1.0, got {self.confidence_threshold}")
        
        # Validate year if provided
        if self.year is not None:
            current_year = datetime.now().year
            if not 1900 <= self.year <= current_year + 1:
                raise ValueError(f"Year must be between 1900 and {current_year + 1}, got {self.year}")
    
    def _clean_string(self, text: str) -> str:
        """Clean and normalize input strings."""
        if not text:
            raise ValueError("Track name and artist name cannot be empty")
        
        # Remove extra whitespace and normalize
        cleaned = " ".join(text.strip().split())
        return cleaned
    
    @property
    def display_name(self) -> str:
        """Get display name for the seed track."""
        return f"{self.track_name} - {self.artist_name}"
    
    @property
    def search_query(self) -> str:
        """Get basic search query string."""
        query = f"{self.track_name} {self.artist_name}"
        if self.album_name:
            query += f" {self.album_name}"
        return query
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "track_name": self.track_name,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "year": self.year,
            "confidence_threshold": self.confidence_threshold,
            "display_name": self.display_name,
            "search_query": self.search_query
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SeedTrack':
        """Create SeedTrack from dictionary representation."""
        return cls(
            track_name=data["track_name"],
            artist_name=data["artist_name"],
            album_name=data.get("album_name"),
            year=data.get("year"),
            confidence_threshold=data.get("confidence_threshold", 0.7)
        )
    
    @classmethod
    def from_string(cls, input_string: str, confidence_threshold: float = 0.7) -> 'SeedTrack':
        """Create SeedTrack from various string formats."""
        # Handle different input formats
        if " - " in input_string:
            # Format: "Track Name - Artist Name"
            parts = input_string.split(" - ", 1)
            track_name = parts[0].strip()
            artist_name = parts[1].strip()
        elif ": " in input_string:
            # Format: "Artist Name: Track Name"
            parts = input_string.split(": ", 1)
            artist_name = parts[0].strip()
            track_name = parts[1].strip()
        elif " by " in input_string.lower():
            # Format: "Track Name by Artist Name"
            parts = input_string.lower().split(" by ", 1)
            track_name = parts[0].strip()
            artist_name = parts[1].strip()
        else:
            # Assume the entire string is the track name
            track_name = input_string.strip()
            artist_name = "Unknown Artist"
        
        return cls(
            track_name=track_name,
            artist_name=artist_name,
            confidence_threshold=confidence_threshold
        )
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'SeedTrack':
        """Create SeedTrack from CSV row data."""
        # Handle various CSV column names
        track_name = (
            row.get("track_name") or 
            row.get("track") or 
            row.get("song") or 
            row.get("title") or
            ""
        ).strip()
        
        artist_name = (
            row.get("artist_name") or 
            row.get("artist") or 
            row.get("performer") or
            ""
        ).strip()
        
        album_name = (
            row.get("album_name") or 
            row.get("album") or
            None
        )
        if album_name:
            album_name = album_name.strip() or None
        
        year = row.get("year") or row.get("release_year")
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None
        
        confidence_threshold = row.get("confidence_threshold")
        if confidence_threshold:
            try:
                confidence_threshold = float(confidence_threshold)
            except (ValueError, TypeError):
                confidence_threshold = 0.7
        else:
            confidence_threshold = 0.7
        
        return cls(
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            year=year,
            confidence_threshold=confidence_threshold
        )

@dataclass
class ResolvedSeedTrack:
    """Represents a seed track that has been resolved to an actual track."""
    seed_track: SeedTrack                # Original seed track
    resolved_track: 'Track'              # Resolved track from provider
    confidence_score: float              # Confidence in the match (0.0-1.0)
    resolution_method: str               # Method used for resolution
    alternative_matches: List['Track'] = None  # Other potential matches
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.alternative_matches is None:
            self.alternative_matches = []
        
        # Validate confidence score
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {self.confidence_score}")
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high confidence match."""
        return self.confidence_score >= 0.8
    
    @property
    def is_medium_confidence(self) -> bool:
        """Check if this is a medium confidence match."""
        return 0.6 <= self.confidence_score < 0.8
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if this is a low confidence match."""
        return 0.4 <= self.confidence_score < 0.6
    
    @property
    def needs_user_confirmation(self) -> bool:
        """Check if this match needs user confirmation."""
        return self.confidence_score < self.seed_track.confidence_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "seed_track": self.seed_track.to_dict(),
            "resolved_track": self.resolved_track.to_dict(),
            "confidence_score": self.confidence_score,
            "resolution_method": self.resolution_method,
            "is_high_confidence": self.is_high_confidence,
            "is_medium_confidence": self.is_medium_confidence,
            "is_low_confidence": self.is_low_confidence,
            "needs_user_confirmation": self.needs_user_confirmation,
            "alternative_matches": [track.to_dict() for track in self.alternative_matches]
        } 