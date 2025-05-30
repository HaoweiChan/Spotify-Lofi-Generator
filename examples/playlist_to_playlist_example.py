#!/usr/bin/env python3
"""
Example script for playlist-to-playlist generation.
Takes an existing playlist from user's Spotify account and generates a similar playlist.
"""

import asyncio
import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any, Optional

# Reduce spotipy error logging for expected 403 errors
logging.getLogger('spotipy.client').setLevel(logging.CRITICAL)

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.seed_track import SeedTrack, ResolvedSeedTrack
from src.models.track import Track
from src.models.audio_features import AudioFeatures
from src.services.seed_track_resolver import SeedTrackResolver, ResolutionConfig
from src.services.similarity_engine import SimilarityEngine, DiversitySettings
from src.utils.cache_manager import CacheManager
from config.settings import Settings

# Try to import spotipy for real Spotify API
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from dotenv import load_dotenv
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    print("⚠️  spotipy not available. Install with: pip install spotipy python-dotenv")

class TokenBasedSpotifyClient:
    """Spotify client using existing user access token (no OAuth required)."""
    
    def __init__(self, access_token: str, cache_manager: Optional[CacheManager] = None):
        if not SPOTIPY_AVAILABLE:
            raise ImportError("spotipy not available. Install with: pip install spotipy python-dotenv")
        
        self.cache_manager = cache_manager
        self.access_token = access_token
        
        try:
            # Create Spotify client with existing token
            self.sp = spotipy.Spotify(auth=access_token)
            
            # Test the connection
            user = self.sp.current_user()
            print(f"🔑 Connected to Spotify using existing token as: {user['display_name']} (@{user['id']})")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect with existing token: {e}")
    
    async def search_user_playlists(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search user's playlists by name."""
        try:
            # Get all user playlists
            playlists_response = self.sp.current_user_playlists(limit=50)
            all_playlists = playlists_response['items']
            
            # Handle pagination to get all playlists
            while playlists_response['next']:
                playlists_response = self.sp.next(playlists_response)
                all_playlists.extend(playlists_response['items'])
            
            # Filter by query if provided
            if query:
                query_lower = query.lower()
                matching_playlists = []
                
                for playlist in all_playlists:
                    if playlist is None:  # Skip None playlists
                        continue
                    
                    playlist_name = playlist.get('name', '').lower()
                    playlist_desc = playlist.get('description', '').lower() if playlist.get('description') else ''
                    
                    if query_lower in playlist_name or query_lower in playlist_desc:
                        matching_playlists.append(playlist)
            else:
                matching_playlists = [p for p in all_playlists if p is not None]
            
            return matching_playlists[:limit]
            
        except Exception as e:
            print(f"❌ Error searching playlists: {e}")
            return []
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tracks from a specific playlist."""
        try:
            # Get playlist tracks with pagination
            tracks_response = self.sp.playlist_tracks(playlist_id, limit=50)
            all_tracks = tracks_response['items']
            
            # Handle pagination
            while tracks_response['next'] and len(all_tracks) < limit:
                tracks_response = self.sp.next(tracks_response)
                all_tracks.extend(tracks_response['items'])
            
            # Filter out None tracks and local tracks
            valid_tracks = []
            for item in all_tracks:
                if item is None or item.get('track') is None:
                    continue
                
                track = item['track']
                # Skip local tracks (they don't have Spotify IDs)
                if track.get('id') is None or track.get('is_local', False):
                    continue
                
                valid_tracks.append(item)
            
            return valid_tracks[:limit]
            
        except Exception as e:
            print(f"❌ Error getting playlist tracks: {e}")
            return []
    
    async def search_tracks(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for tracks."""
        try:
            # Search for tracks using Spotify API
            results = self.sp.search(q=query, type='track', limit=min(limit, 50))
            return results['tracks']['items']
            
        except Exception as e:
            print(f"❌ Error searching tracks: {e}")
            return []
    
    async def get_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get audio features for a track."""
        try:
            # Get audio features from Spotify
            features_list = self.sp.audio_features([track_id])
            
            if features_list and features_list[0]:
                return features_list[0]
            else:
                return None
                
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403:
                # This is common - audio features may not be available or app lacks permissions
                # Don't log this as an error since we have fallback handling
                return None
            else:
                print(f"❌ Spotify API error for {track_id}: {e}")
                return None
        except Exception as e:
            # Only log unexpected errors
            if "403" not in str(e):
                print(f"❌ Error getting audio features for {track_id}: {e}")
            return None
    
    async def close(self):
        """Close any open connections."""
        pass  # spotipy doesn't require explicit cleanup

class RealSpotifyClient:
    """Real Spotify client with user authentication."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        if not SPOTIPY_AVAILABLE:
            raise ImportError("spotipy not available. Install with: pip install spotipy python-dotenv")
        
        load_dotenv()
        
        self.cache_manager = cache_manager
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8080/callback')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment")
        
        # Set up OAuth with required scopes
        self.scope = "playlist-read-private playlist-read-collaborative user-library-read"
        
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache"
            ))
            
            # Test the connection
            user = self.sp.current_user()
            print(f"🔑 Connected to Spotify as: {user['display_name']} (@{user['id']})")
            
        except Exception as e:
            raise ConnectionError(f"Failed to authenticate with Spotify: {e}")
    
    async def search_user_playlists(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search user's playlists by name."""
        try:
            # Get all user playlists
            playlists_response = self.sp.current_user_playlists(limit=50)
            all_playlists = playlists_response['items']
            
            # Handle pagination to get all playlists
            while playlists_response['next']:
                playlists_response = self.sp.next(playlists_response)
                all_playlists.extend(playlists_response['items'])
            
            # Filter by query if provided
            if query:
                query_lower = query.lower()
                matching_playlists = []
                
                for playlist in all_playlists:
                    if playlist is None:  # Skip None playlists
                        continue
                    
                    playlist_name = playlist.get('name', '').lower()
                    playlist_desc = playlist.get('description', '').lower() if playlist.get('description') else ''
                    
                    if query_lower in playlist_name or query_lower in playlist_desc:
                        matching_playlists.append(playlist)
            else:
                matching_playlists = [p for p in all_playlists if p is not None]
            
            return matching_playlists[:limit]
            
        except Exception as e:
            print(f"❌ Error searching playlists: {e}")
            return []
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tracks from a specific playlist."""
        try:
            # Get playlist tracks with pagination
            tracks_response = self.sp.playlist_tracks(playlist_id, limit=50)
            all_tracks = tracks_response['items']
            
            # Handle pagination
            while tracks_response['next'] and len(all_tracks) < limit:
                tracks_response = self.sp.next(tracks_response)
                all_tracks.extend(tracks_response['items'])
            
            # Filter out None tracks and local tracks
            valid_tracks = []
            for item in all_tracks:
                if item is None or item.get('track') is None:
                    continue
                
                track = item['track']
                # Skip local tracks (they don't have Spotify IDs)
                if track.get('id') is None or track.get('is_local', False):
                    continue
                
                valid_tracks.append(item)
            
            return valid_tracks[:limit]
            
        except Exception as e:
            print(f"❌ Error getting playlist tracks: {e}")
            return []
    
    async def search_tracks(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for tracks."""
        try:
            # Search for tracks using Spotify API
            results = self.sp.search(q=query, type='track', limit=min(limit, 50))
            return results['tracks']['items']
            
        except Exception as e:
            print(f"❌ Error searching tracks: {e}")
            return []
    
    async def get_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get audio features for a track."""
        try:
            # Get audio features from Spotify
            features_list = self.sp.audio_features([track_id])
            
            if features_list and features_list[0]:
                return features_list[0]
            else:
                return None
                
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403:
                # This is common - audio features may not be available or app lacks permissions
                # Don't log this as an error since we have fallback handling
                return None
            else:
                print(f"❌ Spotify API error for {track_id}: {e}")
                return None
        except Exception as e:
            # Only log unexpected errors
            if "403" not in str(e):
                print(f"❌ Error getting audio features for {track_id}: {e}")
            return None
    
    async def close(self):
        """Close any open connections."""
        pass  # spotipy doesn't require explicit cleanup

class MockSpotifyUserClient:
    """Mock Spotify client with user authentication for demonstration."""
    
    def __init__(self, client_id: str, client_secret: str, cache_manager: Optional[CacheManager] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cache_manager = cache_manager
        self._session = None
        self.user_access_token = "mock_user_token"  # In real implementation, get via OAuth
    
    async def search_user_playlists(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search user's playlists by name."""
        # Mock user playlists
        mock_playlists = [
            {
                "id": "playlist_1",
                "name": "My Chill Vibes",
                "description": "Relaxing tracks for studying",
                "tracks": {"total": 25},
                "owner": {"id": "user123"},
                "public": False,
                "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_1"}
            },
            {
                "id": "playlist_2", 
                "name": "Rock Classics",
                "description": "Best rock songs of all time",
                "tracks": {"total": 30},
                "owner": {"id": "user123"},
                "public": True,
                "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_2"}
            },
            {
                "id": "playlist_3",
                "name": "Workout Mix",
                "description": "High energy tracks for the gym",
                "tracks": {"total": 40},
                "owner": {"id": "user123"},
                "public": False,
                "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_3"}
            },
            {
                "id": "playlist_4",
                "name": "Jazz Essentials",
                "description": "Classic and modern jazz",
                "tracks": {"total": 50},
                "owner": {"id": "user123"},
                "public": True,
                "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_4"}
            }
        ]
        
        # Filter by query
        query_lower = query.lower()
        matching_playlists = []
        
        for playlist in mock_playlists:
            if not query or query_lower in playlist["name"].lower() or query_lower in playlist.get("description", "").lower():
                matching_playlists.append(playlist)
        
        return matching_playlists[:limit]
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tracks from a specific playlist."""
        # Mock playlist tracks based on playlist ID
        if playlist_id == "playlist_1":  # Chill Vibes
            return [
                {
                    "track": {
                        "id": "chill_1",
                        "name": "Weightless",
                        "artists": [{"name": "Marconi Union"}],
                        "album": {"name": "Weightless", "release_date": "2011-08-01"},
                        "duration_ms": 485000,
                        "popularity": 60,
                        "explicit": False,
                        "external_urls": {"spotify": "https://open.spotify.com/track/chill_1"},
                        "uri": "spotify:track:chill_1"
                    }
                },
                {
                    "track": {
                        "id": "chill_2",
                        "name": "Gymnopédie No. 1",
                        "artists": [{"name": "Erik Satie"}],
                        "album": {"name": "Classical Essentials", "release_date": "1888-01-01"},
                        "duration_ms": 210000,
                        "popularity": 75,
                        "explicit": False,
                        "external_urls": {"spotify": "https://open.spotify.com/track/chill_2"},
                        "uri": "spotify:track:chill_2"
                    }
                },
                {
                    "track": {
                        "id": "chill_3",
                        "name": "Clair de Lune",
                        "artists": [{"name": "Claude Debussy"}],
                        "album": {"name": "Suite Bergamasque", "release_date": "1905-01-01"},
                        "duration_ms": 300000,
                        "popularity": 80,
                        "explicit": False,
                        "external_urls": {"spotify": "https://open.spotify.com/track/chill_3"},
                        "uri": "spotify:track:chill_3"
                    }
                }
            ]
        elif playlist_id == "playlist_2":  # Rock Classics
            return [
                {
                    "track": {
                        "id": "rock_1",
                        "name": "Stairway to Heaven",
                        "artists": [{"name": "Led Zeppelin"}],
                        "album": {"name": "Led Zeppelin IV", "release_date": "1971-11-08"},
                        "duration_ms": 482000,
                        "popularity": 88,
                        "explicit": False,
                        "external_urls": {"spotify": "https://open.spotify.com/track/rock_1"},
                        "uri": "spotify:track:rock_1"
                    }
                },
                {
                    "track": {
                        "id": "rock_2",
                        "name": "Bohemian Rhapsody",
                        "artists": [{"name": "Queen"}],
                        "album": {"name": "A Night at the Opera", "release_date": "1975-10-31"},
                        "duration_ms": 355000,
                        "popularity": 95,
                        "explicit": False,
                        "external_urls": {"spotify": "https://open.spotify.com/track/rock_2"},
                        "uri": "spotify:track:rock_2"
                    }
                }
            ]
        else:
            return []
    
    async def search_tracks(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for tracks (reuse from previous example)."""
        # Similar tracks for demonstration
        mock_tracks = [
            {
                "id": "similar_1",
                "name": "Aqueous Transmission",
                "artists": [{"name": "Incubus"}],
                "album": {"name": "Morning View", "release_date": "2001-10-23"},
                "duration_ms": 450000,
                "popularity": 70,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/similar_1"},
                "uri": "spotify:track:similar_1"
            },
            {
                "id": "similar_2",
                "name": "Svefn-g-englar",
                "artists": [{"name": "Sigur Rós"}],
                "album": {"name": "Ágætis byrjun", "release_date": "1999-06-12"},
                "duration_ms": 620000,
                "popularity": 65,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/similar_2"},
                "uri": "spotify:track:similar_2"
            },
            {
                "id": "similar_3",
                "name": "Porcelain",
                "artists": [{"name": "Moby"}],
                "album": {"name": "Play", "release_date": "1999-05-17"},
                "duration_ms": 240000,
                "popularity": 75,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/similar_3"},
                "uri": "spotify:track:similar_3"
            },
            {
                "id": "similar_4",
                "name": "Intro",
                "artists": [{"name": "The xx"}],
                "album": {"name": "xx", "release_date": "2009-08-14"},
                "duration_ms": 135000,
                "popularity": 78,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/similar_4"},
                "uri": "spotify:track:similar_4"
            },
            {
                "id": "similar_5",
                "name": "Teardrop",
                "artists": [{"name": "Massive Attack"}],
                "album": {"name": "Mezzanine", "release_date": "1998-04-20"},
                "duration_ms": 330000,
                "popularity": 80,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/similar_5"},
                "uri": "spotify:track:similar_5"
            }
        ]
        
        return mock_tracks[:limit]
    
    async def get_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get audio features for a track."""
        # Mock audio features based on track type
        chill_features = {
            "tempo": 65.0,
            "energy": 0.3,
            "valence": 0.4,
            "danceability": 0.2,
            "acousticness": 0.8,
            "instrumentalness": 0.9,
            "liveness": 0.1,
            "speechiness": 0.05,
            "key": 2,
            "mode": 0
        }
        
        rock_features = {
            "tempo": 120.0,
            "energy": 0.9,
            "valence": 0.7,
            "danceability": 0.6,
            "acousticness": 0.1,
            "instrumentalness": 0.2,
            "liveness": 0.2,
            "speechiness": 0.1,
            "key": 7,
            "mode": 1
        }
        
        similar_features = {
            "tempo": 70.0,
            "energy": 0.4,
            "valence": 0.3,
            "danceability": 0.3,
            "acousticness": 0.6,
            "instrumentalness": 0.7,
            "liveness": 0.1,
            "speechiness": 0.05,
            "key": 5,
            "mode": 0
        }
        
        if track_id.startswith("chill_"):
            return chill_features
        elif track_id.startswith("rock_"):
            return rock_features
        elif track_id.startswith("similar_"):
            return similar_features
        else:
            return chill_features  # Default
    
    async def close(self):
        """Close any open connections."""
        if self._session:
            await self._session.close()

def create_fallback_audio_features(track_name: str, artist_name: str, genre_hints: List[str] = None) -> Dict[str, Any]:
    """Create estimated audio features when Spotify features aren't available."""
    import hashlib
    
    # Use track info to create deterministic but varied features
    seed = f"{track_name.lower()}{artist_name.lower()}"
    hash_obj = hashlib.md5(seed.encode())
    hash_int = int(hash_obj.hexdigest()[:8], 16)
    
    # Base features for lo-fi/chill style (since that's the common case)
    base_features = {
        "tempo": 70.0 + (hash_int % 50),  # 70-120 BPM
        "energy": 0.2 + (hash_int % 100) / 100 * 0.6,  # 0.2-0.8
        "valence": 0.3 + (hash_int % 100) / 100 * 0.4,  # 0.3-0.7 
        "danceability": 0.3 + (hash_int % 100) / 100 * 0.4,  # 0.3-0.7
        "acousticness": 0.4 + (hash_int % 100) / 100 * 0.4,  # 0.4-0.8
        "instrumentalness": 0.3 + (hash_int % 100) / 100 * 0.5,  # 0.3-0.8
        "liveness": 0.1 + (hash_int % 100) / 100 * 0.2,  # 0.1-0.3
        "speechiness": 0.03 + (hash_int % 100) / 100 * 0.1,  # 0.03-0.13
        "key": hash_int % 12,
        "mode": hash_int % 2,
        "loudness": -12.0 + (hash_int % 100) / 100 * 8,  # -12 to -4 dB
        "time_signature": 4
    }
    
    # Adjust based on genre hints or track name analysis
    if genre_hints:
        genres_lower = [g.lower() for g in genre_hints]
        
        if any(word in genres_lower for word in ['electronic', 'edm', 'dance', 'techno']):
            base_features['energy'] = max(0.6, base_features['energy'])
            base_features['danceability'] = max(0.7, base_features['danceability'])
            base_features['tempo'] = max(120, base_features['tempo'])
            
        elif any(word in genres_lower for word in ['jazz', 'blues']):
            base_features['acousticness'] = max(0.6, base_features['acousticness'])
            base_features['instrumentalness'] = max(0.5, base_features['instrumentalness'])
            
        elif any(word in genres_lower for word in ['rock', 'metal']):
            base_features['energy'] = max(0.7, base_features['energy'])
            base_features['loudness'] = max(-8, base_features['loudness'])
            
        elif any(word in genres_lower for word in ['classical', 'ambient']):
            base_features['acousticness'] = max(0.8, base_features['acousticness'])
            base_features['instrumentalness'] = max(0.7, base_features['instrumentalness'])
            base_features['energy'] = min(0.4, base_features['energy'])
    
    # Analyze track name for hints
    track_lower = track_name.lower()
    if any(word in track_lower for word in ['chill', 'relax', 'calm', 'peaceful', 'ambient']):
        base_features['energy'] = min(0.4, base_features['energy'])
        base_features['valence'] = min(0.6, base_features['valence'])
        
    elif any(word in track_lower for word in ['upbeat', 'energetic', 'party', 'dance']):
        base_features['energy'] = max(0.7, base_features['energy'])
        base_features['danceability'] = max(0.7, base_features['danceability'])
        base_features['valence'] = max(0.6, base_features['valence'])
    
    return base_features

async def main():
    """Main example function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate playlists based on existing playlists")
    parser.add_argument("--playlist", "-p", default="Chill Vibes", help="Playlist name to use as seeds")
    parser.add_argument("--length", "-l", type=int, help="Target length for new playlist")
    parser.add_argument("--non-interactive", action="store_true", help="Run without user input prompts")
    args = parser.parse_args()
    
    print("🎵 Playlist-to-Playlist Generator")
    print("=" * 50)
    
    # Get playlist name from command line or user input
    if args.non_interactive:
        playlist_name = args.playlist
        print(f"Using playlist: '{playlist_name}' (non-interactive mode)")
    else:
        try:
            user_input = input(f"Enter the name of your playlist to use as seeds [default: {args.playlist}]: ").strip()
            playlist_name = user_input if user_input else args.playlist
        except (EOFError, KeyboardInterrupt):
            playlist_name = args.playlist
            print(f"Using default playlist: '{playlist_name}'")
    
    print(f"\n🔍 Searching for playlist: '{playlist_name}'")
    
    # Initialize settings to check for existing token
    settings = Settings()
    
    # Initialize services with real or mock Spotify client
    cache_manager = CacheManager()
    
    # Check authentication requirements
    auth_status = settings.get_spotify_auth_requirements()
    spotify_client = None
    use_real_api = False
    
    if SPOTIPY_AVAILABLE:
        try:
            if auth_status["user_token"]:
                # Use existing access token
                print("🔑 Found existing Spotify user access token")
                spotify_client = TokenBasedSpotifyClient(
                    settings.SPOTIFY_USER_ACCESS_TOKEN, 
                    cache_manager
                )
                use_real_api = True
                print("🔑 Using existing user token")
            elif auth_status["client_credentials"]:
                # Fall back to OAuth flow
                print("🔄 No user token found, attempting OAuth flow...")
                spotify_client = RealSpotifyClient(cache_manager)
                use_real_api = True
                print("🔑 Using OAuth authentication")
            else:
                print("⚠️  Spotify credentials not found in environment")
                raise ValueError("No credentials")
        except Exception as e:
            print(f"⚠️  Failed to initialize Spotify client: {e}")
            print("🎭 Falling back to mock client")
    
    # Fall back to mock client if real API not available
    if spotify_client is None:
        spotify_client = MockSpotifyUserClient("mock_id", "mock_secret", cache_manager)
        use_real_api = False
        if not SPOTIPY_AVAILABLE:
            print("🎭 Using mock Spotify client (install spotipy for real API)")
        else:
            print("🎭 Using mock Spotify client")
    
    try:
        # Search for user's playlists
        playlists = await spotify_client.search_user_playlists(playlist_name)
        
        if not playlists:
            print(f"❌ No playlists found matching '{playlist_name}'")
            print("\n📋 Available playlists:")
            all_playlists = await spotify_client.search_user_playlists("")
            for i, playlist in enumerate(all_playlists, 1):
                if use_real_api:
                    track_count = playlist['tracks']['total'] if playlist.get('tracks') else 'Unknown'
                    owner = playlist['owner']['display_name'] if playlist.get('owner', {}).get('display_name') else playlist.get('owner', {}).get('id', 'Unknown')
                    print(f"  {i}. {playlist['name']} ({track_count} tracks) by {owner}")
                else:
                    print(f"  {i}. {playlist['name']} ({playlist['tracks']['total']} tracks)")
            return
        
        # Select the first matching playlist
        selected_playlist = playlists[0]
        print(f"✅ Found playlist: '{selected_playlist['name']}'")
        print(f"   Description: {selected_playlist.get('description', 'No description')}")
        
        if use_real_api:
            track_count = selected_playlist['tracks']['total'] if selected_playlist.get('tracks') else 'Unknown'
            owner = selected_playlist['owner']['display_name'] if selected_playlist.get('owner', {}).get('display_name') else selected_playlist.get('owner', {}).get('id', 'Unknown')
            print(f"   Tracks: {track_count}")
            print(f"   Owner: {owner}")
            print(f"   Public: {'Yes' if selected_playlist.get('public') else 'No'}")
            if selected_playlist.get('external_urls', {}).get('spotify'):
                print(f"   URL: {selected_playlist['external_urls']['spotify']}")
        else:
            print(f"   Tracks: {selected_playlist['tracks']['total']}")
            print(f"   Owner: {selected_playlist['owner']['id']}")
        print()
        
        # Get tracks from the playlist
        print("📀 Downloading tracks from playlist...")
        playlist_tracks = await spotify_client.get_playlist_tracks(selected_playlist['id'])
        
        if not playlist_tracks:
            print("❌ No tracks found in playlist")
            return
        
        print(f"✅ Found {len(playlist_tracks)} tracks")
        
        # Convert playlist tracks to Track objects and get audio features
        seed_tracks_resolved = []
        print("\n🎼 Processing tracks and extracting audio features...")
        
        for i, item in enumerate(playlist_tracks, 1):
            track_data = item['track']
            
            # Skip tracks without proper data (podcasts, local files, etc.)
            if not track_data.get('name') or not track_data.get('artists') or not track_data['artists']:
                print(f"  {i}. Skipping: {track_data.get('name', 'Unknown')} - No artist information")
                continue
            
            # Skip if first artist has no name
            first_artist = track_data['artists'][0]
            if not first_artist.get('name'):
                print(f"  {i}. Skipping: {track_data.get('name', 'Unknown')} - No artist name")
                continue
            
            print(f"  {i}. {track_data['name']} - {first_artist['name']}")
            
            try:
                # Create Track object
                track = Track.from_spotify_data(track_data)
                
                # Get audio features
                audio_features_dict = await spotify_client.get_audio_features(track.id)
                if audio_features_dict:
                    track.audio_features = AudioFeatures.from_dict(audio_features_dict)
                    print(f"       ✅ Got audio features from Spotify")
                else:
                    # Use fallback audio features
                    print(f"       🔄 Using estimated audio features")
                    fallback_features = create_fallback_audio_features(
                        track.name, 
                        track.artist, 
                        track.genres if hasattr(track, 'genres') else None
                    )
                    track.audio_features = AudioFeatures.from_dict(fallback_features)
                
                # Create a ResolvedSeedTrack (since we already have the resolved track)
                seed_track = SeedTrack(
                    track_name=track.name,
                    artist_name=track.artist
                )
                
                resolved_seed = ResolvedSeedTrack(
                    seed_track=seed_track,
                    resolved_track=track,
                    confidence_score=1.0,  # Perfect confidence since it's from user's playlist
                    resolution_method="playlist_extraction"
                )
                
                seed_tracks_resolved.append(resolved_seed)
                
            except Exception as e:
                print(f"       ❌ Error processing track: {e}")
                continue
        
        if not seed_tracks_resolved:
            print("\n❌ No tracks with audio features found in playlist")
            print("   This may be due to:")
            print("   - The playlist contains mostly podcasts or local files")
            print("   - Spotify API permissions don't include audio features access")
            print("   - The tracks are not available in your region")
            return
        
        print(f"\n✅ Successfully processed {len(seed_tracks_resolved)} seed tracks")
        
        # Initialize similarity engine
        similarity_engine = SimilarityEngine(spotify_client=spotify_client, cache_manager=cache_manager)
        
        # Configure diversity settings
        diversity_settings = DiversitySettings(
            max_per_artist=3,  # Allow more per artist since we're building from existing playlist
            feature_diversity_factor=0.2,  # Less diversity to stay closer to original vibe
            include_seeds=False,  # Don't include original tracks
            era_distribution={
                "2020s": 0.2,
                "2010s": 0.3,
                "2000s": 0.3,
                "1990s": 0.1,
                "older": 0.1
            }
        )
        
        # Set target length
        default_length = len(seed_tracks_resolved) * 2
        if args.length:
            target_length = args.length
        elif args.non_interactive:
            target_length = default_length
        else:
            try:
                user_input = input(f"\nHow many tracks for the new playlist? [default: {default_length}]: ").strip()
                target_length = int(user_input) if user_input else default_length
            except (EOFError, KeyboardInterrupt, ValueError):
                target_length = default_length
                print(f"Using default length: {target_length}")
        
        print(f"\n🎼 Generating similar playlist with {target_length} tracks...")
        
        # Generate playlist
        playlist = await similarity_engine.generate_playlist(
            seed_tracks_resolved,
            target_length,
            diversity_settings=diversity_settings
        )
        
        # Update playlist name to reflect source
        playlist.name = f"Similar to '{selected_playlist['name']}'"
        playlist.description = f"Generated from {len(seed_tracks_resolved)} tracks in '{selected_playlist['name']}'"
        
        print(f"🎵 Generated playlist: '{playlist.name}'")
        print(f"   Description: {playlist.description}")
        print(f"   Tracks: {len(playlist.tracks)}")
        print(f"   Duration: {playlist.total_duration_formatted}")
        print()
        
        # Display playlist tracks
        print("📋 Generated playlist tracks:")
        for i, track in enumerate(playlist.tracks, 1):
            duration = track.duration_formatted
            similarity = getattr(track, 'similarity_score', 0.0)
            print(f"  {i:2d}. {track.display_name} ({duration}) - Similarity: {similarity:.2f}")
        
        # Save playlist to file
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'playlists')
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = "".join(c for c in selected_playlist['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        playlist_file = os.path.join(output_dir, f"similar_to_{safe_name.replace(' ', '_').lower()}_{playlist.created_at.strftime('%Y%m%d_%H%M%S')}.json")
        
        # Convert playlist to dict for JSON serialization
        playlist_dict = playlist.to_dict()
        
        # Add source playlist metadata
        playlist_dict['source_playlist'] = {
            'id': selected_playlist['id'],
            'name': selected_playlist['name'],
            'description': selected_playlist.get('description'),
            'track_count': selected_playlist['tracks']['total'],
            'seed_tracks_used': len(seed_tracks_resolved)
        }
        
        with open(playlist_file, 'w', encoding='utf-8') as f:
            json.dump(playlist_dict, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Playlist saved to: {playlist_file}")
        
        # Display generation statistics
        print(f"\n📈 Generation Statistics:")
        print(f"   Source Playlist: '{selected_playlist['name']}'")
        print(f"   Seed Tracks Used: {len(seed_tracks_resolved)}")
        print(f"   Generated Tracks: {len(playlist.tracks)}")
        print(f"   Target Length: {target_length}")
        print(f"   Final Duration: {playlist.total_duration_formatted}")
        
        # Show audio feature profile
        avg_features = playlist.average_audio_features
        if avg_features:
            print(f"\n🎛️  Average Audio Features:")
            print(f"   Energy: {avg_features.energy:.2f}")
            print(f"   Valence: {avg_features.valence:.2f}")
            print(f"   Danceability: {avg_features.danceability:.2f}")
            print(f"   Tempo: {avg_features.tempo:.0f} BPM")
            print(f"   Acousticness: {avg_features.acousticness:.2f}")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Review the generated playlist")
        if use_real_api:
            print(f"   2. The playlist was generated from your actual Spotify data")
            print(f"   3. You can import the JSON file to create the playlist on Spotify")
            print(f"   4. Customize generation parameters for better results")
        else:
            print(f"   2. Set up real Spotify API credentials for actual usage:")
            print(f"      - Get credentials from https://developer.spotify.com/dashboard")
            print(f"      - Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file")
            print(f"      - Install spotipy: pip install spotipy python-dotenv")
            print(f"   3. Use the saved JSON file to create the playlist on Spotify")
        
        print(f"\n💻 To use with real Spotify API:")
        print(f"   1. Create a Spotify app at https://developer.spotify.com/dashboard")
        print(f"   2. Set environment variables:")
        print(f"      export SPOTIFY_CLIENT_ID='your_client_id'")
        print(f"      export SPOTIFY_CLIENT_SECRET='your_client_secret'")
        print(f"   3. Install dependencies: pip install spotipy python-dotenv")
        print(f"   4. Run this script again")
        print(f"")
        print(f"   Alternative - Use existing access token:")
        print(f"   1. Get your access token from Spotify Web Console or existing app")
        print(f"   2. Set: export SPOTIFY_USER_ACCESS_TOKEN='your_token'")
        print(f"   3. This skips OAuth and uses the token directly")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        await spotify_client.close()
        if hasattr(cache_manager, 'close'):
            await cache_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 