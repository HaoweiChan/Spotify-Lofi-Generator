"""
Spotify User API client implementation.
Provides OAuth 2.0 Authorization Code flow for user authentication and playlist creation.
"""

import base64
import logging
import webbrowser
import urllib.parse
from typing import Dict, Any, List
from datetime import datetime, timedelta

from src.api.spotify_client import SpotifyClient
from src.api.base_client import AuthenticationError

logger = logging.getLogger(__name__)

class SpotifyUserClient(SpotifyClient):
    """Spotify Web API client with OAuth 2.0 Authorization Code flow for user operations."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str,
        redirect_uri: str = "http://localhost:8888/callback",
        cache_manager=None
    ):
        """
        Initialize Spotify user client.
        
        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            redirect_uri: Redirect URI for OAuth flow
            cache_manager: Optional cache manager for API responses
        """
        super().__init__(client_id, client_secret, cache_manager)
        self.redirect_uri = redirect_uri
        self.user_access_token = None
        self.refresh_token = None
        self.user_token_expires_at = None
        self.current_user_id = None
        
    def get_authorization_url(self, scopes: List[str]) -> str:
        """
        Get the authorization URL for user to grant permissions.
        
        Args:
            scopes: List of Spotify scopes to request
            
        Returns:
            Authorization URL for user to visit
        """
        scope_string = " ".join(scopes)
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope_string,
            "show_dialog": "true"  # Always show the authorization dialog
        }
        
        auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
        return auth_url
        
    async def authenticate_user(self, authorization_code: str) -> str:
        """
        Exchange authorization code for access token.
        
        Args:
            authorization_code: Authorization code from callback
            
        Returns:
            User access token
        """
        await self._ensure_session()
        
        # Prepare credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri
        }
        
        try:
            async with self.session.post(self.auth_url, headers=headers, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()
                
                # Store user tokens
                self.user_access_token = token_data["access_token"]
                self.refresh_token = token_data.get("refresh_token")
                
                # Set token expiration
                expires_in = token_data.get("expires_in", 3600)
                self.user_token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                # Get current user info
                await self._get_current_user()
                
                return self.user_access_token
                
        except Exception as e:
            logger.error(f"Spotify user authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate user with Spotify: {e}")
            
    async def refresh_user_token(self) -> str:
        """
        Refresh the user access token using refresh token.
        
        Returns:
            New user access token
        """
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")
            
        await self._ensure_session()
        
        # Prepare credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        try:
            async with self.session.post(self.auth_url, headers=headers, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()
                
                # Update user token
                self.user_access_token = token_data["access_token"]
                if "refresh_token" in token_data:
                    self.refresh_token = token_data["refresh_token"]
                
                # Set token expiration
                expires_in = token_data.get("expires_in", 3600)
                self.user_token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                return self.user_access_token
                
        except Exception as e:
            logger.error(f"Spotify token refresh failed: {e}")
            raise AuthenticationError(f"Failed to refresh Spotify token: {e}")
            
    def _get_user_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for user API requests."""
        if self.user_access_token:
            return {"Authorization": f"Bearer {self.user_access_token}"}
        return {}
        
    async def _ensure_user_token(self):
        """Ensure user token is valid, refresh if necessary."""
        if not self.user_access_token:
            raise AuthenticationError("User not authenticated")
            
        # Check if token needs refresh
        if (self.user_token_expires_at and 
            datetime.now() >= self.user_token_expires_at and 
            self.refresh_token):
            await self.refresh_user_token()
            
    async def _make_user_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with user authentication."""
        await self._ensure_user_token()
        await self._ensure_session()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_user_auth_headers()
        
        # Merge with any additional headers
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers
        
        # Handle JSON data
        if "data" in kwargs and isinstance(kwargs["data"], dict):
            kwargs["json"] = kwargs.pop("data")
            
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"User API request failed: {method} {url} - {e}")
            raise
            
    async def _get_current_user(self) -> Dict[str, Any]:
        """Get current user profile information."""
        user_info = await self._make_user_request("GET", "me")
        self.current_user_id = user_info["id"]
        return user_info
        
    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get current user's profile information.
        
        Returns:
            Dictionary with user profile data
        """
        return await self._make_user_request("GET", "me")
        
    async def create_user_playlist(
        self, 
        name: str, 
        description: str = "",
        public: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new playlist on the current user's account.
        
        Args:
            name: Playlist name
            description: Playlist description
            public: Whether playlist should be public
            
        Returns:
            Dictionary with playlist information
        """
        if not self.current_user_id:
            await self._get_current_user()
            
        data = {
            "name": name,
            "description": description,
            "public": public
        }
        
        result = await self._make_user_request("POST", f"users/{self.current_user_id}/playlists", data=data)
        return result
        
    async def add_tracks_to_user_playlist(self, playlist_id: str, track_uris: List[str]) -> Dict[str, Any]:
        """
        Add tracks to a user's playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            track_uris: List of Spotify track URIs
            
        Returns:
            Dictionary with operation result
        """
        data = {"uris": track_uris}
        result = await self._make_user_request("POST", f"playlists/{playlist_id}/tracks", data=data)
        return result
        
    async def get_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get current user's playlists.
        
        Args:
            limit: Maximum number of playlists to return
            offset: Index offset for pagination
            
        Returns:
            Dictionary with playlists data
        """
        params = {"limit": limit, "offset": offset}
        result = await self._make_user_request("GET", "me/playlists", params=params)
        return result
        
    def start_auth_flow(self, scopes: List[str] = None) -> str:
        """
        Start the authorization flow by opening browser.
        
        Args:
            scopes: List of Spotify scopes to request
            
        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = [
                "playlist-modify-public",
                "playlist-modify-private", 
                "playlist-read-private",
                "user-read-private"
            ]
            
        auth_url = self.get_authorization_url(scopes)
        
        print(f"🎵 Opening Spotify authorization in your browser...")
        print(f"🔗 If it doesn't open automatically, visit: {auth_url}")
        print(f"📋 After authorization, copy the 'code' parameter from the redirect URL")
        
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
            
        return auth_url 