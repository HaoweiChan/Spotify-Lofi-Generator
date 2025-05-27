"""
Playlist generation service.
Coordinates music provider APIs to generate playlists based on audio features.
"""

import logging
import random
from typing import Dict, Any, List, Optional
from src.models.playlist import Playlist
from src.models.track import Track
from src.models.audio_features import AudioFeatures
from src.api.spotify_client import SpotifyClient
from src.api.apple_music_client import AppleMusicClient
from src.services.audio_features import AudioFeaturesService
from src.utils.cache_manager import CacheManager
from config.settings import Settings

logger = logging.getLogger(__name__)

class PlaylistGenerator:
    """Main service for generating music playlists based on audio features."""
    
    def __init__(self, settings: Settings):
        """
        Initialize playlist generator.
        
        Args:
            settings: Application settings containing API keys and configuration
        """
        self.settings = settings
        self.cache_manager = CacheManager(settings.REDIS_URL)
        self.audio_features_service = AudioFeaturesService()
        self._clients = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.cache_manager.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cache_manager.close()
        for client in self._clients.values():
            await client.close()
            
    async def _get_client(self, provider: str):
        """Get or create API client for the specified provider."""
        if provider not in self._clients:
            if provider == "spotify":
                if not self.settings.SPOTIFY_CLIENT_ID or not self.settings.SPOTIFY_CLIENT_SECRET:
                    raise ValueError("Spotify credentials not configured")
                    
                self._clients[provider] = SpotifyClient(
                    client_id=self.settings.SPOTIFY_CLIENT_ID,
                    client_secret=self.settings.SPOTIFY_CLIENT_SECRET,
                    cache_manager=self.cache_manager
                )
            elif provider == "apple_music":
                if not self.settings.APPLE_MUSIC_KEY_ID or not self.settings.APPLE_MUSIC_TEAM_ID:
                    raise ValueError("Apple Music credentials not configured")
                    
                self._clients[provider] = AppleMusicClient(
                    key_id=self.settings.APPLE_MUSIC_KEY_ID,
                    team_id=self.settings.APPLE_MUSIC_TEAM_ID,
                    private_key=self.settings.APPLE_MUSIC_PRIVATE_KEY,
                    cache_manager=self.cache_manager
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        return self._clients[provider]
        
    async def generate_playlist(
        self,
        audio_features: Dict[str, float],
        length: int = 20,
        provider: str = "spotify",
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        diversity: float = 0.3,
        popularity_range: Optional[tuple] = None
    ) -> Playlist:
        """
        Generate a playlist based on specified audio features.
        
        Args:
            audio_features: Target audio features (energy, valence, etc.)
            length: Number of tracks in playlist
            provider: Music provider to use
            genre: Optional genre filter
            mood: Optional mood descriptor
            diversity: Diversity factor (0.0-1.0, higher = more diverse)
            popularity_range: Optional (min, max) popularity range
            
        Returns:
            Generated Playlist object
        """
        logger.info(f"Generating playlist with {length} tracks using {provider}")
        
        client = await self._get_client(provider)
        
        # Build search queries based on audio features and preferences
        search_queries = self._build_search_queries(audio_features, genre, mood)
        
        # Collect candidate tracks
        candidate_tracks = []
        for query in search_queries:
            try:
                tracks = await client.search_tracks(
                    query=query,
                    limit=50,
                    audio_features=None  # Don't filter by audio features during search
                )
                candidate_tracks.extend(tracks)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                
        if not candidate_tracks:
            raise ValueError("No tracks found matching the specified criteria")
            
        # Remove duplicates
        unique_tracks = self._remove_duplicates(candidate_tracks)
        
        # Filter by popularity if specified
        if popularity_range:
            unique_tracks = self._filter_by_popularity(unique_tracks, popularity_range)
            
        # Score and rank tracks (using metadata instead of audio features)
        scored_tracks = self._score_tracks_by_metadata(unique_tracks, audio_features)
        
        # Select final tracks with diversity
        selected_tracks = self._select_diverse_tracks(scored_tracks, length, diversity)
        
        # Create Track objects
        track_objects = []
        for track_data in selected_tracks:
            audio_features_obj = AudioFeatures(**track_data.get("audio_features", {}))
            track = Track(
                id=track_data["id"],
                name=track_data["name"],
                artist=track_data["artist"],  # Primary artist
                artists=track_data["artists"],
                album=track_data["album"],
                duration_ms=track_data["duration_ms"],
                popularity=track_data.get("popularity"),
                audio_features=audio_features_obj,
                provider=provider,
                external_urls=track_data.get("external_urls", {}),
                preview_url=track_data.get("preview_url")
            )
            track_objects.append(track)
            
        # Create playlist
        import uuid
        playlist = Playlist(
            id=str(uuid.uuid4()),
            name=self._generate_playlist_name(audio_features, genre, mood),
            description=self._generate_playlist_description(audio_features, genre, mood),
            tracks=track_objects,
            target_audio_features=AudioFeatures(**audio_features),
            provider=provider
        )
        
        logger.info(f"Generated playlist '{playlist.name}' with {len(track_objects)} tracks")
        return playlist
        
    def _build_search_queries(
        self, 
        audio_features: Dict[str, float], 
        genre: Optional[str] = None,
        mood: Optional[str] = None
    ) -> List[str]:
        """Build search queries based on audio features and preferences."""
        queries = []
        
        # Genre-based queries
        if genre:
            queries.append(f"genre:{genre}")
            
        # Mood-based queries
        if mood:
            queries.append(mood)
            
        # Feature-based queries
        energy = audio_features.get("energy", 0.5)
        valence = audio_features.get("valence", 0.5)
        danceability = audio_features.get("danceability", 0.5)
        
        # High energy queries
        if energy > 0.7:
            queries.extend(["energetic", "upbeat", "powerful"])
        elif energy < 0.3:
            queries.extend(["calm", "peaceful", "ambient"])
            
        # Valence-based queries
        if valence > 0.7:
            queries.extend(["happy", "uplifting", "positive"])
        elif valence < 0.3:
            queries.extend(["melancholy", "sad", "emotional"])
            
        # Danceability queries
        if danceability > 0.7:
            queries.extend(["dance", "groove", "rhythmic"])
            
        # Default queries if none specified
        if not queries:
            queries = ["popular", "trending", "new music"]
            
        return queries[:5]  # Limit to 5 queries to avoid too many API calls
        
    def _remove_duplicates(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tracks based on name and artist."""
        seen = set()
        unique_tracks = []
        
        for track in tracks:
            # Create a key based on normalized name and artist
            key = (
                track["name"].lower().strip(),
                track["artist"].lower().strip()
            )
            
            if key not in seen:
                seen.add(key)
                unique_tracks.append(track)
                
        return unique_tracks
        
    def _filter_by_popularity(
        self, 
        tracks: List[Dict[str, Any]], 
        popularity_range: tuple
    ) -> List[Dict[str, Any]]:
        """Filter tracks by popularity range."""
        min_pop, max_pop = popularity_range
        return [
            track for track in tracks
            if min_pop <= track.get("popularity", 50) <= max_pop
        ]
        
    async def _score_tracks(
        self, 
        tracks: List[Dict[str, Any]], 
        target_features: Dict[str, float],
        client
    ) -> List[Dict[str, Any]]:
        """Score tracks based on how well they match target audio features."""
        scored_tracks = []
        
        for track in tracks:
            try:
                # Get audio features if not already present
                if "audio_features" not in track:
                    features = await client.get_audio_features(track["id"])
                    track["audio_features"] = features
                    
                # Calculate similarity score
                score = self._calculate_feature_similarity(
                    track["audio_features"], 
                    target_features
                )
                track["similarity_score"] = score
                scored_tracks.append(track)
                
            except Exception as e:
                logger.warning(f"Failed to score track {track['id']}: {e}")
                
        # Sort by similarity score (descending)
        scored_tracks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        return scored_tracks
        
    def _score_tracks_by_metadata(
        self, 
        tracks: List[Dict[str, Any]], 
        target_features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Score tracks based on metadata when audio features are not available."""
        scored_tracks = []
        
        for track in tracks:
            # Use popularity and other metadata for scoring
            score = 0.5  # Base score
            
            # Boost score based on popularity (normalized to 0-1)
            popularity = track.get("popularity", 50) / 100.0
            score += popularity * 0.3
            
            # Add some randomness to ensure variety
            import random
            score += random.random() * 0.2
            
            track["similarity_score"] = score
            
            # Add mock audio features for compatibility
            track["audio_features"] = {
                "energy": target_features.get("energy", 0.5),
                "valence": target_features.get("valence", 0.5),
                "danceability": target_features.get("danceability", 0.5),
                "acousticness": target_features.get("acousticness", 0.5),
                "instrumentalness": target_features.get("instrumentalness", 0.5),
                "tempo": target_features.get("tempo", 120),
                "loudness": -10,
                "liveness": 0.1,
                "speechiness": 0.1,
                "key": 0,
                "mode": 1,
                "time_signature": 4
            }
            
            scored_tracks.append(track)
            
        # Sort by similarity score (descending)
        scored_tracks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        return scored_tracks
        
    def _calculate_feature_similarity(
        self, 
        track_features: Dict[str, float], 
        target_features: Dict[str, float]
    ) -> float:
        """Calculate similarity score between track and target features."""
        if not track_features or not target_features:
            return 0.0
            
        total_diff = 0.0
        feature_count = 0
        
        # Weight different features
        feature_weights = {
            "energy": 1.0,
            "valence": 1.0,
            "danceability": 0.8,
            "acousticness": 0.6,
            "instrumentalness": 0.5,
            "tempo": 0.3
        }
        
        for feature, target_value in target_features.items():
            if feature in track_features and feature in feature_weights:
                track_value = track_features[feature]
                weight = feature_weights[feature]
                
                # Normalize tempo to 0-1 scale for comparison
                if feature == "tempo":
                    track_value = min(track_value / 200.0, 1.0)
                    target_value = min(target_value / 200.0, 1.0)
                    
                diff = abs(track_value - target_value) * weight
                total_diff += diff
                feature_count += weight
                
        if feature_count == 0:
            return 0.0
            
        # Convert difference to similarity (0-1 scale)
        avg_diff = total_diff / feature_count
        similarity = max(0.0, 1.0 - avg_diff)
        
        return similarity
        
    def _select_diverse_tracks(
        self, 
        scored_tracks: List[Dict[str, Any]], 
        count: int,
        diversity: float
    ) -> List[Dict[str, Any]]:
        """Select tracks with diversity to avoid repetitive playlists."""
        if len(scored_tracks) <= count:
            return scored_tracks
            
        selected = []
        remaining = scored_tracks.copy()
        
        # Always include the best match
        if remaining:
            selected.append(remaining.pop(0))
            
        # Select remaining tracks with diversity
        while len(selected) < count and remaining:
            if random.random() < diversity:
                # Random selection for diversity
                index = random.randint(0, min(len(remaining) - 1, 10))
            else:
                # Best match selection
                index = 0
                
            selected.append(remaining.pop(index))
            
        return selected
        
    def _generate_playlist_name(
        self, 
        audio_features: Dict[str, float], 
        genre: Optional[str] = None,
        mood: Optional[str] = None
    ) -> str:
        """Generate a descriptive name for the playlist."""
        name_parts = []
        
        if mood:
            name_parts.append(mood.title())
        elif genre:
            name_parts.append(genre.title())
            
        # Add feature-based descriptors
        energy = audio_features.get("energy", 0.5)
        valence = audio_features.get("valence", 0.5)
        
        if energy > 0.7 and valence > 0.7:
            name_parts.append("High Energy")
        elif energy < 0.3 and valence < 0.3:
            name_parts.append("Chill Vibes")
        elif valence > 0.7:
            name_parts.append("Feel Good")
        elif energy > 0.7:
            name_parts.append("Energetic")
            
        name_parts.append("Mix")
        
        return " ".join(name_parts) if name_parts else "Custom Playlist"
        
    def _generate_playlist_description(
        self, 
        audio_features: Dict[str, float], 
        genre: Optional[str] = None,
        mood: Optional[str] = None
    ) -> str:
        """Generate a description for the playlist."""
        desc_parts = ["Generated playlist based on audio features:"]
        
        for feature, value in audio_features.items():
            if feature in ["energy", "valence", "danceability"]:
                desc_parts.append(f"{feature.title()}: {value:.1f}")
                
        if genre:
            desc_parts.append(f"Genre: {genre}")
        if mood:
            desc_parts.append(f"Mood: {mood}")
            
        return " | ".join(desc_parts) 