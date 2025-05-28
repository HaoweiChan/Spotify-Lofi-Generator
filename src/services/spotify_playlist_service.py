"""
Spotify Playlist Service for creating playlists on user accounts.
Handles user authentication and playlist creation workflow.
"""

import logging
import os
import json
from typing import Dict, Any, List

from config.settings import Settings
from src.api.spotify_user_client import SpotifyUserClient
from src.models.playlist import Playlist

logger = logging.getLogger(__name__)

class SpotifyPlaylistService:
    """Service for creating playlists directly on user's Spotify account."""
    
    def __init__(self, settings: Settings):
        """
        Initialize Spotify playlist service.
        
        Args:
            settings: Application settings containing API keys
        """
        self.settings = settings
        self.client = None
        self.auth_cache_file = os.path.expanduser("~/.spotify_auth_cache.json")
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.settings.SPOTIFY_CLIENT_ID or not self.settings.SPOTIFY_CLIENT_SECRET:
            raise ValueError("Spotify credentials not configured in settings")
            
        self.client = SpotifyUserClient(
            client_id=self.settings.SPOTIFY_CLIENT_ID,
            client_secret=self.settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=self.settings.SPOTIFY_REDIRECT_URI
        )
        
        # Try to load cached authentication
        await self._load_cached_auth()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.close()
            
    async def _load_cached_auth(self):
        """Load cached authentication tokens if available."""
        if os.path.exists(self.auth_cache_file):
            try:
                with open(self.auth_cache_file, 'r') as f:
                    auth_data = json.load(f)
                    
                self.client.user_access_token = auth_data.get("access_token")
                self.client.refresh_token = auth_data.get("refresh_token")
                self.client.current_user_id = auth_data.get("user_id")
                
                # Try to refresh token to ensure it's valid
                if self.client.refresh_token:
                    try:
                        await self.client.refresh_user_token()
                        logger.info("Successfully refreshed cached Spotify token")
                    except Exception as e:
                        logger.warning(f"Failed to refresh cached token: {e}")
                        self._clear_cached_auth()
                        
            except Exception as e:
                logger.warning(f"Failed to load cached auth: {e}")
                self._clear_cached_auth()
                
    def _save_cached_auth(self):
        """Save authentication tokens to cache."""
        if self.client and self.client.user_access_token:
            auth_data = {
                "access_token": self.client.user_access_token,
                "refresh_token": self.client.refresh_token,
                "user_id": self.client.current_user_id
            }
            
            try:
                with open(self.auth_cache_file, 'w') as f:
                    json.dump(auth_data, f)
                logger.info("Saved Spotify authentication to cache")
            except Exception as e:
                logger.warning(f"Failed to save auth cache: {e}")
                
    def _clear_cached_auth(self):
        """Clear cached authentication."""
        if os.path.exists(self.auth_cache_file):
            try:
                os.remove(self.auth_cache_file)
            except Exception as e:
                logger.warning(f"Failed to clear auth cache: {e}")
                
    async def authenticate_user(self, force_reauth: bool = False) -> bool:
        """
        Authenticate user with Spotify.
        
        Args:
            force_reauth: Force re-authentication even if cached tokens exist
            
        Returns:
            True if authentication successful
        """
        if force_reauth:
            self._clear_cached_auth()
            self.client.user_access_token = None
            self.client.refresh_token = None
            self.client.current_user_id = None
            
        # Check if already authenticated
        if self.client.user_access_token and self.client.current_user_id:
            try:
                # Test the token by getting user profile
                await self.client.get_user_profile()
                return True
            except Exception:
                # Token invalid, need to re-authenticate
                pass
                
        # Start authentication flow
        auth_url = self.client.start_auth_flow()
        
        print("\n" + "="*60)
        print("🔐 Spotify Authentication Required")
        print("="*60)
        print("To create playlists on your Spotify account, you need to authorize this app.")
        print(f"🌐 Authorization URL: {auth_url}")
        print("\n📋 Steps:")
        print("1. Click the link above or copy it to your browser")
        print("2. Log in to Spotify and authorize the app")
        print("3. Copy the 'code' parameter from the redirect URL")
        print("4. Paste it below")
        print("\nExample redirect URL:")
        print("http://localhost:8888/callback?code=AQC1234567890...")
        print("                                    ^^^^^^^^^^^^^^^^")
        print("                                    Copy this part")
        print("="*60)
        
        # Get authorization code from user
        auth_code = input("\n🔑 Enter the authorization code: ").strip()
        
        if not auth_code:
            print("❌ No authorization code provided")
            return False
            
        try:
            # Exchange code for tokens
            await self.client.authenticate_user(auth_code)
            
            # Save to cache
            self._save_cached_auth()
            
            # Get user info
            user_info = await self.client.get_user_profile()
            print(f"✅ Successfully authenticated as: {user_info.get('display_name', user_info['id'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
            
    async def create_playlist_on_spotify(
        self, 
        playlist: Playlist,
        public: bool = False,
        overwrite_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Create a playlist directly on user's Spotify account.
        
        Args:
            playlist: Playlist object to create
            public: Whether to make playlist public
            overwrite_existing: Whether to overwrite if playlist with same name exists
            
        Returns:
            Dictionary with created playlist information
        """
        if not self.client.user_access_token:
            raise ValueError("User not authenticated. Call authenticate_user() first.")
            
        # Check for existing playlist with same name
        if not overwrite_existing:
            existing_playlists = await self.client.get_user_playlists()
            for existing in existing_playlists.get("items", []):
                if existing["name"] == playlist.name:
                    print(f"⚠️  Playlist '{playlist.name}' already exists")
                    response = input("Do you want to create anyway with a different name? (y/n): ").strip().lower()
                    if response != 'y':
                        return {"error": "Playlist already exists"}
                    playlist.name = f"{playlist.name} (Copy)"
                    break
                    
        try:
            # Create playlist on Spotify
            spotify_playlist = await self.client.create_user_playlist(
                name=playlist.name,
                description=playlist.description or f"Generated playlist with {len(playlist.tracks)} tracks",
                public=public
            )
            
            print(f"✅ Created playlist '{playlist.name}' on Spotify")
            print(f"🆔 Playlist ID: {spotify_playlist['id']}")
            print(f"🔗 Playlist URL: {spotify_playlist['external_urls']['spotify']}")
            
            # Prepare track URIs
            track_uris = []
            failed_tracks = []
            
            for track in playlist.tracks:
                if track.provider == "spotify" and hasattr(track, 'uri') and track.uri:
                    track_uris.append(track.uri)
                elif track.provider == "spotify" and track.id:
                    track_uris.append(f"spotify:track:{track.id}")
                else:
                    failed_tracks.append(f"{track.name} - {track.artist}")
                    
            if failed_tracks:
                print(f"⚠️  Could not add {len(failed_tracks)} tracks (missing Spotify URIs):")
                for track_name in failed_tracks[:5]:  # Show first 5
                    print(f"   - {track_name}")
                if len(failed_tracks) > 5:
                    print(f"   ... and {len(failed_tracks) - 5} more")
                    
            # Add tracks to playlist in batches (Spotify limit is 100 per request)
            if track_uris:
                batch_size = 100
                added_count = 0
                
                for i in range(0, len(track_uris), batch_size):
                    batch = track_uris[i:i + batch_size]
                    try:
                        await self.client.add_tracks_to_user_playlist(spotify_playlist['id'], batch)
                        added_count += len(batch)
                        print(f"📀 Added {len(batch)} tracks to playlist ({added_count}/{len(track_uris)} total)")
                    except Exception as e:
                        print(f"❌ Failed to add batch of tracks: {e}")
                        
                print(f"🎵 Successfully added {added_count} tracks to '{playlist.name}'")
            else:
                print("⚠️  No valid Spotify tracks found to add")
                
            return {
                "spotify_playlist": spotify_playlist,
                "tracks_added": len(track_uris),
                "tracks_failed": len(failed_tracks),
                "playlist_url": spotify_playlist['external_urls']['spotify']
            }
            
        except Exception as e:
            logger.error(f"Failed to create playlist on Spotify: {e}")
            raise
            
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user's Spotify profile information.
        
        Returns:
            Dictionary with user profile data
        """
        if not self.client.user_access_token:
            raise ValueError("User not authenticated")
            
        return await self.client.get_user_profile()
        
    async def list_user_playlists(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user's existing playlists.
        
        Args:
            limit: Maximum number of playlists to return
            
        Returns:
            List of playlist dictionaries
        """
        if not self.client.user_access_token:
            raise ValueError("User not authenticated")
            
        result = await self.client.get_user_playlists(limit=limit)
        return result.get("items", [])
        
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return (self.client and 
                self.client.user_access_token and 
                self.client.current_user_id is not None) 