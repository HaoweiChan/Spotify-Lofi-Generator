"""
Spotify Web API client implementation.
Provides OAuth 2.0 authentication, track search, audio features, and playlist management.
"""

import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.api.base_client import BaseAPIClient, AuthenticationError
from src.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class SpotifyClient(BaseAPIClient):
    """Spotify Web API client with OAuth 2.0 Client Credentials flow."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize Spotify client.
        
        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            cache_manager: Optional cache manager for API responses
        """
        super().__init__(
            base_url="https://api.spotify.com/v1",
            rate_limit=100,  # 100 requests per minute
            cache_manager=cache_manager
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = "https://accounts.spotify.com/api/token"
        
    async def authenticate(self) -> str:
        """Authenticate using OAuth 2.0 Client Credentials flow."""
        await self._ensure_session()
        
        # Prepare credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"grant_type": "client_credentials"}
        
        try:
            async with self.session.post(self.auth_url, headers=headers, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()
                
                # Set token expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                return token_data["access_token"]
                
        except Exception as e:
            logger.error(f"Spotify authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate with Spotify: {e}")
            
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if self._auth_token:
            return {"Authorization": f"Bearer {self._auth_token}"}
        return {}
        
    async def search_tracks(
        self, 
        query: str, 
        limit: int = 50,
        audio_features: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for tracks on Spotify.
        
        Args:
            query: Search query string
            limit: Maximum number of results (1-50)
            audio_features: Optional audio features for filtering
            
        Returns:
            List of track dictionaries with normalized data
        """
        cache_key = self.cache_manager.get_cache_key("spotify_search", query, limit) if self.cache_manager else None
        
        params = {
            "q": query,
            "type": "track",
            "limit": min(limit, 50),
            "market": "US"
        }
        
        if cache_key:
            result = await self._cached_request(cache_key, "GET", "search", ttl=86400, params=params)
        else:
            result = await self._make_request("GET", "search", params=params)
            
        tracks = []
        for item in result.get("tracks", {}).get("items", []):
            track_data = self._normalize_track_data(item)
            
            # Get audio features if filtering is requested
            if audio_features:
                try:
                    features = await self.get_audio_features(track_data["id"])
                    if self._matches_audio_features(features, audio_features):
                        track_data["audio_features"] = features
                        tracks.append(track_data)
                except Exception as e:
                    logger.warning(f"Failed to get audio features for {track_data['id']}: {e}")
            else:
                tracks.append(track_data)
                
        return tracks
        
    async def get_audio_features(self, track_id: str) -> Dict[str, float]:
        """
        Get audio features for a specific track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Dictionary of normalized audio features (0.0-1.0 scale)
        """
        cache_key = self.cache_manager.get_cache_key("spotify_features", track_id) if self.cache_manager else None
        
        if cache_key:
            result = await self._cached_request(
                cache_key, "GET", f"audio-features/{track_id}", ttl=604800  # 7 days
            )
        else:
            result = await self._make_request("GET", f"audio-features/{track_id}")
            
        if not result:
            return {}
            
        return self._normalize_audio_features(result)
        
    async def get_track_info(self, track_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Dictionary with track information
        """
        cache_key = self.cache_manager.get_cache_key("spotify_track", track_id) if self.cache_manager else None
        
        if cache_key:
            result = await self._cached_request(
                cache_key, "GET", f"tracks/{track_id}", ttl=86400  # 24 hours
            )
        else:
            result = await self._make_request("GET", f"tracks/{track_id}")
            
        return self._normalize_track_data(result)
        
    async def create_playlist(
        self, 
        user_id: str, 
        name: str, 
        description: str = "",
        public: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new playlist.
        
        Args:
            user_id: Spotify user ID
            name: Playlist name
            description: Playlist description
            public: Whether playlist should be public
            
        Returns:
            Dictionary with playlist information
        """
        data = {
            "name": name,
            "description": description,
            "public": public
        }
        
        result = await self._make_request("POST", f"users/{user_id}/playlists", data=data)
        return result
        
    async def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> Dict[str, Any]:
        """
        Add tracks to a playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            track_uris: List of Spotify track URIs
            
        Returns:
            Dictionary with operation result
        """
        data = {"uris": track_uris}
        result = await self._make_request("POST", f"playlists/{playlist_id}/tracks", data=data)
        return result
        
    def _normalize_track_data(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Spotify track data to standard format."""
        artists = [artist["name"] for artist in track_data.get("artists", [])]
        
        return {
            "id": track_data["id"],
            "name": track_data["name"],
            "artists": artists,
            "artist": ", ".join(artists),
            "album": track_data.get("album", {}).get("name", ""),
            "duration_ms": track_data.get("duration_ms", 0),
            "popularity": track_data.get("popularity", 0),
            "external_urls": track_data.get("external_urls", {}),
            "preview_url": track_data.get("preview_url"),
            "uri": track_data["uri"],
            "provider": "spotify"
        }
        
    def _normalize_audio_features(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Normalize Spotify audio features to 0.0-1.0 scale."""
        return {
            "energy": float(features.get("energy", 0.5)),
            "valence": float(features.get("valence", 0.5)),
            "danceability": float(features.get("danceability", 0.5)),
            "acousticness": float(features.get("acousticness", 0.5)),
            "instrumentalness": float(features.get("instrumentalness", 0.5)),
            "liveness": float(features.get("liveness", 0.5)),
            "speechiness": float(features.get("speechiness", 0.5)),
            "tempo": float(features.get("tempo", 120)),
            "loudness": float(features.get("loudness", -10)),
            "key": int(features.get("key", 0)),
            "mode": int(features.get("mode", 1)),
            "time_signature": int(features.get("time_signature", 4))
        }
        
    def _matches_audio_features(
        self, 
        track_features: Dict[str, float], 
        target_features: Dict[str, float],
        tolerance: float = 0.2
    ) -> bool:
        """Check if track features match target features within tolerance."""
        for feature, target_value in target_features.items():
            if feature in track_features:
                track_value = track_features[feature]
                
                # Special handling for tempo (BPM)
                if feature == "tempo":
                    if abs(track_value - target_value) > target_value * tolerance:
                        return False
                # Standard 0.0-1.0 scale features
                elif abs(track_value - target_value) > tolerance:
                    return False
                    
        return True 