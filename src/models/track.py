"""
Track data model representing a music track with metadata and audio features.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from .audio_features import AudioFeatures
from .license_info import LicenseInfo

@dataclass
class Track:
    """Represents a music track with metadata and audio features."""
    id: str                              # Unique identifier
    name: str                           # Track name
    artist: str                         # Primary artist name
    artists: List[str]                  # All artists
    album: str                          # Album name
    duration_ms: int                    # Track duration in milliseconds
    popularity: Optional[int] = None    # Popularity score (0-100)
    explicit: bool = False              # Explicit content flag
    preview_url: Optional[str] = None   # Preview audio URL
    external_urls: Dict[str, str] = None # External URLs (Spotify, Apple Music, etc.)
    audio_features: Optional[AudioFeatures] = None  # Audio characteristics
    license_info: Optional[LicenseInfo] = None       # Licensing information
    genres: List[str] = None            # Track genres
    release_date: Optional[str] = None  # Release date
    isrc: Optional[str] = None          # International Standard Recording Code
    provider: str = "unknown"           # Source provider (spotify, apple_music, etc.)
    provider_id: Optional[str] = None   # Provider-specific ID
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.external_urls is None:
            self.external_urls = {}
        if self.genres is None:
            self.genres = []
        if self.artists is None:
            self.artists = [self.artist] if self.artist else []
    
    @property
    def duration_seconds(self) -> float:
        """Get track duration in seconds."""
        return self.duration_ms / 1000.0
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (MM:SS)."""
        total_seconds = int(self.duration_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def display_name(self) -> str:
        """Get display name for the track."""
        return f"{self.name} - {self.artist}"
    
    @property
    def is_licensed_for_business(self) -> bool:
        """Check if track is licensed for business use."""
        if not self.license_info:
            return False
        return self.license_info.business_use_allowed
    
    def similarity_score(self, target_features: AudioFeatures, weights: Dict[str, float] = None) -> float:
        """Calculate similarity score with target audio features."""
        if not self.audio_features:
            return 0.0
        return self.audio_features.similarity(target_features, weights)
    
    def add_license_info(self, license_info: LicenseInfo):
        """Add licensing information to the track."""
        self.license_info = license_info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "artist": self.artist,
            "artists": self.artists,
            "album": self.album,
            "duration_ms": self.duration_ms,
            "duration_formatted": self.duration_formatted,
            "popularity": self.popularity,
            "explicit": self.explicit,
            "preview_url": self.preview_url,
            "external_urls": self.external_urls,
            "audio_features": self.audio_features.to_dict() if self.audio_features else None,
            "license_info": self.license_info.to_dict() if self.license_info else None,
            "genres": self.genres,
            "release_date": self.release_date,
            "isrc": self.isrc,
            "provider": self.provider,
            "provider_id": self.provider_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Create Track from dictionary representation."""
        # Extract and convert nested objects
        audio_features = None
        if data.get("audio_features"):
            audio_features = AudioFeatures.from_dict(data["audio_features"])
        
        license_info = None
        if data.get("license_info"):
            license_info = LicenseInfo.from_dict(data["license_info"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            artist=data["artist"],
            artists=data.get("artists", []),
            album=data["album"],
            duration_ms=data["duration_ms"],
            popularity=data.get("popularity"),
            explicit=data.get("explicit", False),
            preview_url=data.get("preview_url"),
            external_urls=data.get("external_urls", {}),
            audio_features=audio_features,
            license_info=license_info,
            genres=data.get("genres", []),
            release_date=data.get("release_date"),
            isrc=data.get("isrc"),
            provider=data.get("provider", "unknown"),
            provider_id=data.get("provider_id")
        )
    
    @classmethod
    def from_spotify_data(cls, spotify_track: Dict[str, Any], audio_features: Optional[AudioFeatures] = None) -> 'Track':
        """Create Track from Spotify API response."""
        artists = [artist["name"] for artist in spotify_track.get("artists", [])]
        
        return cls(
            id=spotify_track["id"],
            name=spotify_track["name"],
            artist=artists[0] if artists else "Unknown Artist",
            artists=artists,
            album=spotify_track.get("album", {}).get("name", "Unknown Album"),
            duration_ms=spotify_track.get("duration_ms", 0),
            popularity=spotify_track.get("popularity"),
            explicit=spotify_track.get("explicit", False),
            preview_url=spotify_track.get("preview_url"),
            external_urls=spotify_track.get("external_urls", {}),
            audio_features=audio_features,
            release_date=spotify_track.get("album", {}).get("release_date"),
            provider="spotify",
            provider_id=spotify_track["id"]
        )
    
    @classmethod
    def from_apple_music_data(cls, apple_track: Dict[str, Any]) -> 'Track':
        """Create Track from Apple Music API response."""
        attributes = apple_track.get("attributes", {})
        
        return cls(
            id=apple_track["id"],
            name=attributes.get("name", "Unknown Track"),
            artist=attributes.get("artistName", "Unknown Artist"),
            artists=[attributes.get("artistName", "Unknown Artist")],
            album=attributes.get("albumName", "Unknown Album"),
            duration_ms=attributes.get("durationInMillis", 0),
            explicit=attributes.get("contentRating") == "explicit",
            preview_url=attributes.get("previews", [{}])[0].get("url") if attributes.get("previews") else None,
            external_urls={"apple_music": apple_track.get("href", "")},
            genres=attributes.get("genreNames", []),
            release_date=attributes.get("releaseDate"),
            isrc=attributes.get("isrc"),
            provider="apple_music",
            provider_id=apple_track["id"]
        ) 