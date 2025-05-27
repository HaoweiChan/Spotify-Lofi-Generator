"""
Apple Music API Client

Provides integration with Apple Music API for track search, audio features,
and metadata retrieval.
"""

import asyncio
import logging
import jwt
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base_client import BaseAPIClient
from ..models.track import Track
from ..models.audio_features import AudioFeatures
from ..utils.validators import validate_track_data

logger = logging.getLogger(__name__)


class AppleMusicClient(BaseAPIClient):
    """Apple Music API client for track search and audio features."""
    
    def __init__(self, key_id: str, team_id: str, private_key: str, 
                 cache_manager=None, rate_limiter=None):
        """
        Initialize Apple Music client.
        
        Args:
            key_id: Apple Music API key ID
            team_id: Apple Developer team ID
            private_key: Private key content for JWT signing
            cache_manager: Optional cache manager instance
            rate_limiter: Optional rate limiter instance
        """
        super().__init__(
            base_url="https://api.music.apple.com/v1",
            rate_limit=100,  # Apple Music rate limit
            cache_manager=cache_manager
        )
        
        self.key_id = key_id
        self.team_id = team_id
        self.private_key = private_key
        self._token = None
        self._token_expires = None
        
    async def authenticate(self) -> bool:
        """
        Authenticate with Apple Music API using JWT.
        
        Returns:
            True if authentication successful
        """
        try:
            # Generate JWT token
            now = int(time.time())
            payload = {
                'iss': self.team_id,
                'iat': now,
                'exp': now + 3600,  # 1 hour expiration
                'aud': 'appstoreconnect-v1'
            }
            
            headers = {
                'alg': 'ES256',
                'kid': self.key_id
            }
            
            self._token = jwt.encode(
                payload, 
                self.private_key, 
                algorithm='ES256',
                headers=headers
            )
            
            self._token_expires = datetime.now() + timedelta(hours=1)
            
            # Update session headers
            self.session.headers.update({
                'Authorization': f'Bearer {self._token}',
                'Music-User-Token': ''  # Required for user-specific requests
            })
            
            logger.info("Apple Music authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Apple Music authentication failed: {e}")
            return False
    
    async def search_tracks(self, query: str, limit: int = 50, 
                          audio_features: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Search for tracks on Apple Music.
        
        Args:
            query: Search query string
            limit: Maximum number of results (max 25 per request)
            audio_features: Optional audio features for filtering
            
        Returns:
            List of track dictionaries
        """
        try:
            await self._ensure_authenticated()
            
            # Apple Music limits to 25 results per request
            per_request = min(limit, 25)
            all_tracks = []
            offset = 0
            
            while len(all_tracks) < limit:
                remaining = limit - len(all_tracks)
                current_limit = min(per_request, remaining)
                
                params = {
                    'term': query,
                    'types': 'songs',
                    'limit': current_limit,
                    'offset': offset
                }
                
                # Add audio features filtering if provided
                # Note: Apple Music API has limited filtering capabilities
                
                cache_key = f"apple_music_search:{hash(str(params))}"
                
                response = await self._make_request(
                    'GET', 
                    '/catalog/us/search',
                    params=params,
                    cache_key=cache_key,
                    cache_ttl=3600
                )
                
                if not response or 'results' not in response:
                    break
                
                songs = response['results'].get('songs', {}).get('data', [])
                if not songs:
                    break
                
                tracks = []
                for song in songs:
                    track = self._parse_track(song)
                    if track:
                        track_dict = {
                            'id': track.id,
                            'name': track.name,
                            'artists': track.artists,
                            'album': track.album,
                            'duration_ms': track.duration_ms,
                            'popularity': track.popularity,
                            'external_urls': track.external_urls,
                            'genres': track.genres,
                            'release_date': track.release_date,
                            'explicit': track.explicit,
                            'provider': track.provider
                        }
                        if track.audio_features:
                            track_dict['audio_features'] = track.audio_features.to_dict()
                        tracks.append(track_dict)
                all_tracks.extend(tracks)
                
                offset += current_limit
                
                # Break if we got fewer results than requested (end of results)
                if len(songs) < current_limit:
                    break
            
            logger.info(f"Found {len(all_tracks)} tracks for query: {query}")
            return all_tracks[:limit]
            
        except Exception as e:
            logger.error(f"Error searching Apple Music tracks: {e}")
            return []
    
    async def get_track_audio_features(self, track_id: str) -> Optional[AudioFeatures]:
        """
        Get audio features for a track.
        
        Note: Apple Music API doesn't provide detailed audio features like Spotify.
        This method returns basic features that can be inferred from metadata.
        
        Args:
            track_id: Apple Music track ID
            
        Returns:
            AudioFeatures object or None
        """
        try:
            await self._ensure_authenticated()
            
            cache_key = f"apple_music_features:{track_id}"
            
            response = await self._make_request(
                'GET',
                f'/catalog/us/songs/{track_id}',
                cache_key=cache_key,
                cache_ttl=86400  # 24 hours
            )
            
            if not response or 'data' not in response:
                return None
            
            song_data = response['data'][0]
            return self._parse_audio_features(song_data)
            
        except Exception as e:
            logger.error(f"Error getting Apple Music audio features: {e}")
            return None
    
    async def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """
        Get track details by Apple Music ID.
        
        Args:
            track_id: Apple Music track ID
            
        Returns:
            Track object or None
        """
        try:
            await self._ensure_authenticated()
            
            cache_key = f"apple_music_track:{track_id}"
            
            response = await self._make_request(
                'GET',
                f'/catalog/us/songs/{track_id}',
                cache_key=cache_key,
                cache_ttl=86400  # 24 hours
            )
            
            if not response or 'data' not in response:
                return None
            
            song_data = response['data'][0]
            return self._parse_track(song_data)
            
        except Exception as e:
            logger.error(f"Error getting Apple Music track: {e}")
            return None
    
    async def get_recommendations(self, seed_tracks: List[str], 
                                target_features: Optional[AudioFeatures] = None,
                                limit: int = 20) -> List[Track]:
        """
        Get track recommendations based on seed tracks.
        
        Note: Apple Music API has limited recommendation capabilities.
        This method uses related content and genre-based suggestions.
        
        Args:
            seed_tracks: List of Apple Music track IDs
            target_features: Target audio features (limited support)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended tracks
        """
        try:
            await self._ensure_authenticated()
            
            recommendations = []
            
            for track_id in seed_tracks[:5]:  # Limit seed tracks
                # Get related content
                cache_key = f"apple_music_related:{track_id}"
                
                response = await self._make_request(
                    'GET',
                    f'/catalog/us/songs/{track_id}',
                    params={'include': 'albums,artists'},
                    cache_key=cache_key,
                    cache_ttl=3600
                )
                
                if response and 'data' in response:
                    song_data = response['data'][0]
                    
                    # Get artist's other tracks
                    if 'relationships' in song_data and 'artists' in song_data['relationships']:
                        artist_data = song_data['relationships']['artists']['data'][0]
                        artist_id = artist_data['id']
                        
                        artist_tracks = await self._get_artist_tracks(artist_id, limit=5)
                        recommendations.extend(artist_tracks)
                
                if len(recommendations) >= limit:
                    break
            
            # Remove duplicates and seed tracks
            seen_ids = set(seed_tracks)
            unique_recommendations = []
            
            for track in recommendations:
                if track.id not in seen_ids:
                    unique_recommendations.append(track)
                    seen_ids.add(track.id)
                    
                if len(unique_recommendations) >= limit:
                    break
            
            logger.info(f"Generated {len(unique_recommendations)} Apple Music recommendations")
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"Error getting Apple Music recommendations: {e}")
            return []
    
    async def _get_artist_tracks(self, artist_id: str, limit: int = 10) -> List[Track]:
        """Get tracks by artist."""
        try:
            cache_key = f"apple_music_artist_tracks:{artist_id}"
            
            response = await self._make_request(
                'GET',
                f'/catalog/us/artists/{artist_id}/songs',
                params={'limit': limit},
                cache_key=cache_key,
                cache_ttl=3600
            )
            
            if not response or 'data' not in response:
                return []
            
            tracks = [self._parse_track(song) for song in response['data']]
            return [t for t in tracks if t is not None]
            
        except Exception as e:
            logger.error(f"Error getting artist tracks: {e}")
            return []
    
    def _parse_track(self, song_data: Dict[str, Any]) -> Optional[Track]:
        """Parse Apple Music song data into Track object."""
        try:
            attributes = song_data.get('attributes', {})
            
            artist_name = attributes.get('artistName', 'Unknown Artist')
            track_data = {
                'id': song_data['id'],
                'name': attributes.get('name', ''),
                'artist': artist_name,
                'artists': [artist_name],
                'album': attributes.get('albumName', ''),
                'duration_ms': attributes.get('durationInMillis', 0),
                'popularity': self._calculate_popularity(attributes),
                'preview_url': attributes.get('previews', [{}])[0].get('url'),
                'external_urls': {
                    'apple_music': attributes.get('url', '')
                },
                'genres': attributes.get('genreNames', []),
                'release_date': attributes.get('releaseDate', ''),
                'explicit': attributes.get('contentRating') == 'explicit',
                'isrc': attributes.get('isrc'),
                'provider': 'apple_music'
            }
            
            # Add audio features if available
            audio_features = self._parse_audio_features(song_data)
            if audio_features:
                track_data['audio_features'] = audio_features
            
            validate_track_data(track_data)
            return Track(**track_data)
            
        except Exception as e:
            logger.error(f"Error parsing Apple Music track: {e}")
            return None
    
    def _parse_audio_features(self, song_data: Dict[str, Any]) -> Optional[AudioFeatures]:
        """
        Parse basic audio features from Apple Music data.
        
        Note: Apple Music doesn't provide detailed audio features like Spotify.
        This method infers basic features from available metadata.
        """
        try:
            attributes = song_data.get('attributes', {})
            
            # Basic features that can be inferred
            features_data = {
                'duration_ms': attributes.get('durationInMillis', 0),
                'tempo': None,  # Not available in Apple Music API
                'energy': None,  # Not available
                'valence': None,  # Not available
                'danceability': None,  # Not available
                'acousticness': None,  # Not available
                'instrumentalness': None,  # Not available
                'liveness': None,  # Not available
                'speechiness': None,  # Not available
                'loudness': None,  # Not available
                'key': None,  # Not available
                'mode': None,  # Not available
                'time_signature': None  # Not available
            }
            
            # Try to infer some features from genre
            genres = attributes.get('genreNames', [])
            if genres:
                features_data.update(self._infer_features_from_genre(genres[0]))
            
            return AudioFeatures(**features_data)
            
        except Exception as e:
            logger.error(f"Error parsing Apple Music audio features: {e}")
            return None
    
    def _infer_features_from_genre(self, genre: str) -> Dict[str, Optional[float]]:
        """Infer basic audio features from genre."""
        genre_lower = genre.lower()
        
        # Basic genre-based feature inference
        if 'electronic' in genre_lower or 'dance' in genre_lower:
            return {
                'energy': 0.8,
                'danceability': 0.9,
                'valence': 0.7,
                'tempo': 128.0
            }
        elif 'rock' in genre_lower:
            return {
                'energy': 0.9,
                'danceability': 0.6,
                'valence': 0.6,
                'tempo': 120.0
            }
        elif 'classical' in genre_lower:
            return {
                'energy': 0.3,
                'danceability': 0.2,
                'acousticness': 0.9,
                'instrumentalness': 0.8
            }
        elif 'jazz' in genre_lower:
            return {
                'energy': 0.5,
                'danceability': 0.4,
                'acousticness': 0.7,
                'instrumentalness': 0.6
            }
        elif 'hip hop' in genre_lower or 'rap' in genre_lower:
            return {
                'energy': 0.7,
                'danceability': 0.8,
                'speechiness': 0.8,
                'tempo': 100.0
            }
        
        return {}
    
    def _calculate_popularity(self, attributes: Dict[str, Any]) -> int:
        """Calculate popularity score from available metadata."""
        # Apple Music doesn't provide popularity scores
        # Use chart positions or other indicators if available
        return 50  # Default neutral popularity
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid authentication token."""
        if (not self._token or 
            not self._token_expires or 
            datetime.now() >= self._token_expires):
            await self.authenticate()
    
    async def get_audio_features(self, track_id: str) -> Dict[str, float]:
        """Get audio features for a specific track."""
        features = await self.get_track_audio_features(track_id)
        if features:
            return features.to_dict()
        return {}
    
    async def get_track_info(self, track_id: str) -> Dict[str, Any]:
        """Get detailed information about a track."""
        track = await self.get_track_by_id(track_id)
        if track:
            return {
                'id': track.id,
                'name': track.name,
                'artists': track.artists,
                'album': track.album,
                'duration_ms': track.duration_ms,
                'popularity': track.popularity,
                'external_urls': track.external_urls,
                'genres': track.genres,
                'release_date': track.release_date,
                'explicit': track.explicit,
                'provider': track.provider
            }
        return {}

    async def close(self):
        """Close the client session."""
        await super().close()
        self._token = None
        self._token_expires = None 