"""API clients for music providers and external services."""

from .base_client import BaseAPIClient
from .spotify_client import SpotifyClient
from .spotify_user_client import SpotifyUserClient
from .apple_music_client import AppleMusicClient
from .youtube_client import YouTubeClient

__all__ = [
    'BaseAPIClient',
    'SpotifyClient',
    'SpotifyUserClient',
    'AppleMusicClient',
    'YouTubeClient'
] 