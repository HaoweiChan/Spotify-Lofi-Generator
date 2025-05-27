"""
Playlist data model representing a collection of tracks with metadata.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
from .track import Track
from .audio_features import AudioFeatures

@dataclass
class Playlist:
    """Represents a music playlist with tracks and metadata."""
    id: str
    name: str
    description: Optional[str] = None
    tracks: List[Track] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_duration_ms: int = 0
    target_audio_features: Optional[AudioFeatures] = None
    provider: str = "unknown"
    public: bool = False
    collaborative: bool = False
    owner: Optional[str] = None
    follower_count: int = 0
    external_urls: Dict[str, str] = None
    image_url: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.tracks is None:
            self.tracks = []
        if self.external_urls is None:
            self.external_urls = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        self._calculate_total_duration()
    
    def _calculate_total_duration(self):
        """Calculate total duration from tracks."""
        self.total_duration_ms = sum(track.duration_ms for track in self.tracks)
    
    @property
    def track_count(self) -> int:
        """Get number of tracks in playlist."""
        return len(self.tracks)
    
    @property
    def total_duration_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.total_duration_ms / 1000.0
    
    @property
    def total_duration_formatted(self) -> str:
        """Get formatted total duration string (HH:MM:SS)."""
        total_seconds = int(self.total_duration_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    @property
    def licensed_track_count(self) -> int:
        """Get number of tracks licensed for business use."""
        return sum(1 for track in self.tracks if track.is_licensed_for_business)
    
    @property
    def licensing_compliance_percentage(self) -> float:
        """Get percentage of tracks that are licensed for business use."""
        if not self.tracks:
            return 0.0
        return (self.licensed_track_count / len(self.tracks)) * 100
    
    @property
    def average_audio_features(self) -> Optional[AudioFeatures]:
        """Calculate average audio features across all tracks."""
        if not self.tracks:
            return None
        
        tracks_with_features = [track for track in self.tracks if track.audio_features]
        if not tracks_with_features:
            return None
        
        # Calculate averages (handle None values)
        def safe_avg(values):
            non_none_values = [v for v in values if v is not None]
            return sum(non_none_values) / len(non_none_values) if non_none_values else None
        
        avg_energy = safe_avg([t.audio_features.energy for t in tracks_with_features])
        avg_valence = safe_avg([t.audio_features.valence for t in tracks_with_features])
        avg_danceability = safe_avg([t.audio_features.danceability for t in tracks_with_features])
        avg_acousticness = safe_avg([t.audio_features.acousticness for t in tracks_with_features])
        avg_instrumentalness = safe_avg([t.audio_features.instrumentalness for t in tracks_with_features])
        avg_tempo = safe_avg([t.audio_features.tempo for t in tracks_with_features])
        avg_loudness = safe_avg([t.audio_features.loudness for t in tracks_with_features])
        
        return AudioFeatures(
            energy=avg_energy,
            valence=avg_valence,
            danceability=avg_danceability,
            acousticness=avg_acousticness,
            instrumentalness=avg_instrumentalness,
            tempo=avg_tempo,
            loudness=avg_loudness
        )
    
    def add_track(self, track: Track):
        """Add a track to the playlist."""
        self.tracks.append(track)
        self.updated_at = datetime.utcnow()
        self._calculate_total_duration()
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the playlist by ID."""
        original_length = len(self.tracks)
        self.tracks = [track for track in self.tracks if track.id != track_id]
        
        if len(self.tracks) < original_length:
            self.updated_at = datetime.utcnow()
            self._calculate_total_duration()
            return True
        return False
    
    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """Get a track by its ID."""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None
    
    def sort_by_similarity(self, target_features: AudioFeatures, weights: Dict[str, float] = None):
        """Sort tracks by similarity to target audio features."""
        def similarity_key(track: Track) -> float:
            if not track.audio_features:
                return 0.0
            return track.similarity_score(target_features, weights)
        
        self.tracks.sort(key=similarity_key, reverse=True)
        self.updated_at = datetime.utcnow()
    
    def filter_licensed_tracks(self) -> 'Playlist':
        """Create a new playlist with only business-licensed tracks."""
        licensed_tracks = [track for track in self.tracks if track.is_licensed_for_business]
        
        return Playlist(
            id=f"{self.id}_licensed",
            name=f"{self.name} (Business Licensed)",
            description=f"Business-licensed tracks from {self.name}",
            tracks=licensed_tracks,
            target_audio_features=self.target_audio_features,
            provider=self.provider
        )
    
    def get_licensing_report(self) -> Dict[str, Any]:
        """Generate a licensing compliance report."""
        total_tracks = len(self.tracks)
        licensed_tracks = self.licensed_track_count
        unlicensed_tracks = total_tracks - licensed_tracks
        
        risk_scores = []
        for track in self.tracks:
            if track.license_info:
                risk_scores.append(track.license_info.calculate_business_risk_score())
        
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 1.0
        
        return {
            "playlist_id": self.id,
            "playlist_name": self.name,
            "total_tracks": total_tracks,
            "licensed_tracks": licensed_tracks,
            "unlicensed_tracks": unlicensed_tracks,
            "compliance_percentage": self.licensing_compliance_percentage,
            "average_risk_score": avg_risk_score,
            "risk_level": "Low" if avg_risk_score < 0.3 else "Medium" if avg_risk_score < 0.7 else "High",
            "recommendations": self._get_licensing_recommendations()
        }
    
    def _get_licensing_recommendations(self) -> List[str]:
        """Get licensing recommendations based on playlist analysis."""
        recommendations = []
        
        compliance_pct = self.licensing_compliance_percentage
        
        if compliance_pct < 50:
            recommendations.append("Consider replacing unlicensed tracks with business-licensed alternatives")
        elif compliance_pct < 80:
            recommendations.append("Review licensing for remaining unlicensed tracks")
        
        if any(track.license_info and track.license_info.attribution_required for track in self.tracks):
            recommendations.append("Ensure proper attribution for Creative Commons licensed tracks")
        
        if any(track.license_info and track.license_info.youtube_content_id for track in self.tracks):
            recommendations.append("Be aware of potential YouTube Content ID claims")
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert playlist to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tracks": [track.to_dict() for track in self.tracks],
            "track_count": self.track_count,
            "total_duration_ms": self.total_duration_ms,
            "total_duration_formatted": self.total_duration_formatted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "target_audio_features": self.target_audio_features.to_dict() if self.target_audio_features else None,
            "average_audio_features": self.average_audio_features.to_dict() if self.average_audio_features else None,
            "provider": self.provider,
            "public": self.public,
            "collaborative": self.collaborative,
            "owner": self.owner,
            "follower_count": self.follower_count,
            "external_urls": self.external_urls,
            "image_url": self.image_url,
            "licensed_track_count": self.licensed_track_count,
            "licensing_compliance_percentage": self.licensing_compliance_percentage,
            "licensing_report": self.get_licensing_report()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        """Create Playlist from dictionary representation."""
        tracks = []
        if data.get("tracks"):
            tracks = [Track.from_dict(track_data) for track_data in data["tracks"]]
        
        target_features = None
        if data.get("target_audio_features"):
            target_features = AudioFeatures.from_dict(data["target_audio_features"])
        
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            tracks=tracks,
            created_at=created_at,
            updated_at=updated_at,
            target_audio_features=target_features,
            provider=data.get("provider", "unknown"),
            public=data.get("public", False),
            collaborative=data.get("collaborative", False),
            owner=data.get("owner"),
            follower_count=data.get("follower_count", 0),
            external_urls=data.get("external_urls", {}),
            image_url=data.get("image_url")
        )

class PlaylistResponse(BaseModel):
    """Pydantic model for API responses with playlist data."""
    id: str
    name: str
    description: Optional[str] = None
    track_count: int
    total_duration_formatted: str
    tracks: List[Dict[str, Any]]
    licensing_compliance_percentage: float
    licensed_track_count: int
    provider: str
    
    @classmethod
    def from_playlist(cls, playlist: Playlist) -> 'PlaylistResponse':
        """Create response model from Playlist object."""
        return cls(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            track_count=playlist.track_count,
            total_duration_formatted=playlist.total_duration_formatted,
            tracks=[track.to_dict() for track in playlist.tracks],
            licensing_compliance_percentage=playlist.licensing_compliance_percentage,
            licensed_track_count=playlist.licensed_track_count,
            provider=playlist.provider
        ) 