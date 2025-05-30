#!/usr/bin/env python3
"""
Music Playlist Generator with Licensing Checker
Main CLI entry point for generating playlists based on audio features
and checking business licensing availability.
"""

import sys
import json
import asyncio
import argparse
import subprocess
import os
from datetime import datetime

from config.settings import Settings
from src.services.playlist_generator import PlaylistGenerator
from src.services.licensing_checker import LicensingChecker
from src.services.spotify_playlist_service import SpotifyPlaylistService

def run_tests():
    """Run the test suite."""
    print("🧪 Running Music Playlist Generator Test Suite...")
    print("=" * 60)
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"])
        import pytest
    
    # Run pytest with the tests directory
    test_args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "tests/",  # Test directory
    ]
    
    try:
        # Run the tests
        exit_code = pytest.main(test_args)
        
        if exit_code == 0:
            print("\n✅ All tests passed!")
            print("\n🚀 Your Music Playlist Generator is ready to use!")
            print("\nNext steps:")
            print("1. Set up your .env file with API keys")
            print("2. Run: python main.py --features '{\"energy\": 0.8, \"valence\": 0.6}' --length 5")
        else:
            print(f"\n❌ Some tests failed (exit code: {exit_code})")
            print("Please check the output above for details.")
            
        return exit_code
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def display_playlist_summary(playlist):
    """Display a summary of the generated playlist."""
    print("\n" + "="*60)
    print(f"🎵 Playlist Generated: {playlist['name']}")
    print("="*60)
    print(f"Description: {playlist['description']}")
    print(f"Total Tracks: {len(playlist['tracks'])}")
    print(f"Provider: {playlist['provider'].title()}")
    
    if playlist.get('target_audio_features'):
        features = playlist['target_audio_features']
        print(f"\nTarget Audio Features:")
        for feature, value in features.items():
            if feature in ['energy', 'valence', 'danceability', 'acousticness'] and value is not None:
                print(f"  {feature.title()}: {value:.1f}")
    
    print(f"\nTracks:")
    print("-" * 60)
    for i, track in enumerate(playlist['tracks'][:10], 1):  # Show first 10 tracks
        duration = track.get('duration_formatted', 'Unknown')
        popularity = track.get('popularity', 'N/A')
        album = track.get('album', 'Unknown Album')
        name = track.get('name', 'Unknown Track')
        artist = track.get('artist', 'Unknown Artist')
        
        # Handle None values
        if duration is None:
            duration = 'Unknown'
        if popularity is None:
            popularity = 'N/A'
        if album is None:
            album = 'Unknown Album'
        if name is None:
            name = 'Unknown Track'
        if artist is None:
            artist = 'Unknown Artist'
            
        print(f"{i:2d}. {name} - {artist}")
        print(f"    Album: {album} | Duration: {duration} | Popularity: {popularity}")
    
    if len(playlist['tracks']) > 10:
        print(f"    ... and {len(playlist['tracks']) - 10} more tracks")
    
    print("-" * 60)

def get_output_path(filename=None, provider="spotify"):
    """Generate output path with proper directory structure."""
    # Ensure output directory exists
    output_dir = "output/playlists"
    os.makedirs(output_dir, exist_ok=True)
    
    if filename:
        # If filename provided, use it (but ensure it's in the output directory)
        if not filename.startswith(output_dir):
            filename = os.path.join(output_dir, os.path.basename(filename))
        return filename
    
    # Generate automatic filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{provider}_playlist_{timestamp}.json"
    return os.path.join(output_dir, filename)

async def generate_playlist(args):
    """Generate a playlist based on the provided arguments."""
    # Parse audio features
    features = {}
    if args.features:
        try:
            features = json.loads(args.features)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for features")
            return
    
    # Initialize services
    settings = Settings()
    
    try:
        async with PlaylistGenerator(settings) as playlist_generator:
            # Generate playlist
            print(f"Generating playlist with {args.length} tracks using {args.provider}...")
            playlist = await playlist_generator.generate_playlist(
                audio_features=features,
                length=args.length,
                provider=args.provider
            )
            
            # Check licensing if requested
            if args.check_licensing:
                async with LicensingChecker(settings) as licensing_checker:
                    print("Checking licensing information...")
                    playlist = await licensing_checker.check_playlist_licensing(playlist)
            
            # Convert to dict for processing
            playlist_dict = playlist.to_dict()
            
            # Display playlist summary
            display_playlist_summary(playlist_dict)
            
            # Save to file
            output_path = get_output_path(args.output, args.provider)
            with open(output_path, 'w') as f:
                json.dump(playlist_dict, f, indent=2)
            print(f"\n💾 Playlist saved to: {output_path}")
            
            # Show file location
            abs_path = os.path.abspath(output_path)
            print(f"📁 Full path: {abs_path}")
            
    except Exception as e:
        print(f"Error generating playlist: {e}")

async def create_spotify_playlist(args):
    """Create a playlist directly on user's Spotify account."""
    # Load playlist from file
    if not os.path.exists(args.playlist_file):
        print(f"Error: Playlist file '{args.playlist_file}' not found")
        return
    
    try:
        # Load existing playlist
        with open(args.playlist_file, 'r') as f:
            playlist_data = json.load(f)
        
        print(f"🎵 Creating Spotify playlist: {playlist_data.get('name', 'Unknown')}")
        print(f"📁 Source file: {args.playlist_file}")
        print(f"🎵 Tracks: {len(playlist_data.get('tracks', []))}")
        
        # Convert dict back to Playlist object
        from src.models.playlist import Playlist
        from src.models.track import Track
        from src.models.audio_features import AudioFeatures
        
        # Reconstruct playlist object
        tracks = []
        for track_data in playlist_data.get('tracks', []):
            track = Track.from_dict(track_data)
            tracks.append(track)
        
        target_features = None
        if playlist_data.get('target_audio_features'):
            target_features = AudioFeatures.from_dict(playlist_data['target_audio_features'])
        
        playlist = Playlist(
            id=playlist_data['id'],
            name=playlist_data['name'],
            description=playlist_data['description'],
            tracks=tracks,
            target_audio_features=target_features,
            provider=playlist_data['provider']
        )
        
        # Initialize Spotify service
        settings = Settings()
        
        async with SpotifyPlaylistService(settings) as spotify_service:
            # Check for existing token first
            auth_status = settings.get_spotify_auth_requirements()
            authenticated = False
            
            if auth_status["user_token"]:
                print("🔑 Using existing Spotify user access token")
                try:
                    # Test token with a simple API call
                    import spotipy
                    sp = spotipy.Spotify(auth=settings.SPOTIFY_USER_ACCESS_TOKEN)
                    user_info = sp.current_user()
                    print(f"✅ Token valid for: {user_info.get('display_name', user_info['id'])}")
                    authenticated = True
                except Exception as e:
                    print(f"⚠️  Existing token invalid: {e}")
                    print("🔄 Falling back to OAuth authentication...")
            
            if not authenticated:
                # Authenticate user via OAuth
                if not await spotify_service.authenticate_user(force_reauth=args.reauth):
                    print("❌ Authentication failed. Cannot create playlist.")
                    return
            
            # Create playlist on Spotify
            result = await spotify_service.create_playlist_on_spotify(
                playlist=playlist,
                public=args.public,
                overwrite_existing=args.overwrite
            )
            
            if "error" in result:
                print(f"❌ {result['error']}")
                return
            
            print(f"\n🎉 Success! Playlist created on Spotify:")
            print(f"🔗 {result['playlist_url']}")
            print(f"📊 {result['tracks_added']} tracks added")
            if result['tracks_failed'] > 0:
                print(f"⚠️  {result['tracks_failed']} tracks could not be added")
                
    except Exception as e:
        print(f"Error creating Spotify playlist: {e}")

async def generate_and_create_spotify_playlist(args):
    """Generate a playlist and immediately create it on Spotify."""
    # First generate the playlist
    print("🎵 Generating playlist...")
    
    # Parse audio features
    features = {}
    if args.features:
        try:
            features = json.loads(args.features)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for features")
            return
    
    # Initialize services
    settings = Settings()
    
    try:
        async with PlaylistGenerator(settings) as playlist_generator:
            # Generate playlist
            playlist = await playlist_generator.generate_playlist(
                audio_features=features,
                length=args.length,
                provider=args.provider
            )
            
            # Check licensing if requested
            if args.check_licensing:
                async with LicensingChecker(settings) as licensing_checker:
                    print("Checking licensing information...")
                    playlist = await licensing_checker.check_playlist_licensing(playlist)
            
            # Display playlist summary
            display_playlist_summary(playlist.to_dict())
            
            # Create on Spotify if requested
            if args.provider == "spotify":
                async with SpotifyPlaylistService(settings) as spotify_service:
                    # Check for existing token first
                    auth_status = settings.get_spotify_auth_requirements()
                    authenticated = False
                    
                    if auth_status["user_token"]:
                        print("🔑 Using existing Spotify user access token")
                        try:
                            # Test token with a simple API call
                            import spotipy
                            sp = spotipy.Spotify(auth=settings.SPOTIFY_USER_ACCESS_TOKEN)
                            user_info = sp.current_user()
                            print(f"✅ Token valid for: {user_info.get('display_name', user_info['id'])}")
                            authenticated = True
                        except Exception as e:
                            print(f"⚠️  Existing token invalid: {e}")
                            print("🔄 Falling back to OAuth authentication...")
                    
                    if not authenticated:
                        # Authenticate user via OAuth
                        if not await spotify_service.authenticate_user():
                            print("❌ Authentication failed. Saving playlist to file only.")
                            # Save to file as fallback
                            output_path = get_output_path(args.output, args.provider)
                            with open(output_path, 'w') as f:
                                json.dump(playlist.to_dict(), f, indent=2)
                            print(f"💾 Playlist saved to: {output_path}")
                            return
                    
                    # Create playlist on Spotify
                    result = await spotify_service.create_playlist_on_spotify(
                        playlist=playlist,
                        public=args.public,
                        overwrite_existing=False
                    )
                    
                    if "error" not in result:
                        print(f"\n🎉 Success! Playlist created on Spotify:")
                        print(f"🔗 {result['playlist_url']}")
                        print(f"📊 {result['tracks_added']} tracks added")
                        if result['tracks_failed'] > 0:
                            print(f"⚠️  {result['tracks_failed']} tracks could not be added")
                    else:
                        print(f"❌ {result['error']}")
            else:
                print("ℹ️  Only Spotify playlists can be created directly on your account")
            
            # Also save to file
            output_path = get_output_path(args.output, args.provider)
            with open(output_path, 'w') as f:
                json.dump(playlist.to_dict(), f, indent=2)
            print(f"\n💾 Playlist also saved to: {output_path}")
            
    except Exception as e:
        print(f"Error generating playlist: {e}")

async def spotify_auth(args):
    """Manage Spotify authentication."""
    settings = Settings()
    
    try:
        async with SpotifyPlaylistService(settings) as spotify_service:
            if args.logout:
                # Clear authentication
                spotify_service._clear_cached_auth()
                print("✅ Logged out from Spotify")
                return
            
            if args.status:
                # Check authentication status
                auth_status = settings.get_spotify_auth_requirements()
                
                if auth_status["user_token"]:
                    print("🔑 Found existing Spotify user access token")
                    # Try to use existing token
                    try:
                        # Test the token by making a simple API call
                        import spotipy
                        sp = spotipy.Spotify(auth=settings.SPOTIFY_USER_ACCESS_TOKEN)
                        user_info = sp.current_user()
                        
                        print(f"✅ Token is valid! Authenticated as: {user_info.get('display_name', user_info['id'])}")
                        print(f"🆔 User ID: {user_info['id']}")
                        print(f"👥 Followers: {user_info.get('followers', {}).get('total', 'N/A')}")
                        
                        # Show some playlists
                        playlists_response = sp.current_user_playlists(limit=5)
                        playlists = playlists_response.get('items', [])
                        if playlists:
                            print(f"\n📋 Recent playlists:")
                            for i, playlist in enumerate(playlists[:5], 1):
                                print(f"  {i}. {playlist['name']} ({playlist['tracks']['total']} tracks)")
                        
                        print(f"\n💡 Using existing token from SPOTIFY_USER_ACCESS_TOKEN")
                        return
                        
                    except Exception as e:
                        print(f"❌ Existing token is invalid or expired: {e}")
                        print("💡 Will need to re-authenticate")
                
                # Fall back to checking OAuth-based authentication
                if spotify_service.is_authenticated():
                    try:
                        user_info = await spotify_service.get_user_info()
                        print(f"✅ Authenticated via OAuth as: {user_info.get('display_name', user_info['id'])}")
                        print(f"🆔 User ID: {user_info['id']}")
                        print(f"👥 Followers: {user_info.get('followers', {}).get('total', 'N/A')}")
                        
                        # Show some playlists
                        playlists = await spotify_service.list_user_playlists(limit=5)
                        if playlists:
                            print(f"\n📋 Recent playlists:")
                            for i, playlist in enumerate(playlists[:5], 1):
                                print(f"  {i}. {playlist['name']} ({playlist['tracks']['total']} tracks)")
                    except Exception as e:
                        print(f"❌ OAuth authentication expired or invalid: {e}")
                        print("💡 Run 'python main.py spotify-auth' to re-authenticate")
                else:
                    print("❌ Not authenticated with Spotify")
                    print("💡 Run 'python main.py spotify-auth' to authenticate")
                return
            
            # Check for existing token before starting OAuth
            auth_status = settings.get_spotify_auth_requirements()
            
            if auth_status["user_token"] and not args.reauth:
                print("🔑 Found existing Spotify user access token")
                try:
                    # Test the token
                    import spotipy
                    sp = spotipy.Spotify(auth=settings.SPOTIFY_USER_ACCESS_TOKEN)
                    user_info = sp.current_user()
                    
                    print(f"✅ Token is valid! Already authenticated as: {user_info.get('display_name', user_info['id'])}")
                    print("💡 Use --reauth flag to force re-authentication")
                    print("💡 Use --status to see detailed authentication info")
                    return
                    
                except Exception as e:
                    print(f"⚠️  Existing token is invalid or expired: {e}")
                    print("🔄 Proceeding with OAuth authentication...")
            elif not auth_status["client_credentials"]:
                print("❌ Missing Spotify client credentials")
                print("💡 Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env file")
                return
            
            # Default: authenticate via OAuth
            success = await spotify_service.authenticate_user(force_reauth=args.reauth)
            if success:
                user_info = await spotify_service.get_user_info()
                print(f"\n🎉 Successfully authenticated via OAuth!")
                print(f"👤 Welcome, {user_info.get('display_name', user_info['id'])}!")
                print("💡 You can now create playlists directly on your Spotify account")
                
                # Suggest adding token to .env for future use
                print(f"\n💡 Tip: To skip OAuth in the future, you can save your access token:")
                print(f"   Add this to your .env file:")
                print(f"   SPOTIFY_USER_ACCESS_TOKEN=<your_token>")
            else:
                print("❌ Authentication failed")
                
    except Exception as e:
        print(f"Error with Spotify authentication: {e}")

async def check_licensing(args):
    """Check licensing for an existing playlist file."""
    if not os.path.exists(args.playlist_file):
        print(f"Error: Playlist file '{args.playlist_file}' not found")
        return
    
    try:
        # Load existing playlist
        with open(args.playlist_file, 'r') as f:
            playlist_data = json.load(f)
        
        print(f"🔍 Checking licensing for playlist: {playlist_data.get('name', 'Unknown')}")
        print(f"📁 File: {args.playlist_file}")
        print(f"🎵 Tracks: {len(playlist_data.get('tracks', []))}")
        
        # Initialize services
        settings = Settings()
        
        # Convert dict back to Playlist object
        from src.models.playlist import Playlist
        from src.models.track import Track
        from src.models.audio_features import AudioFeatures
        
        # Reconstruct playlist object
        tracks = []
        for track_data in playlist_data.get('tracks', []):
            audio_features = None
            if track_data.get('audio_features'):
                audio_features = AudioFeatures.from_dict(track_data['audio_features'])
            
            track = Track.from_dict(track_data)
            tracks.append(track)
        
        target_features = None
        if playlist_data.get('target_audio_features'):
            target_features = AudioFeatures.from_dict(playlist_data['target_audio_features'])
        
        playlist = Playlist(
            id=playlist_data['id'],
            name=playlist_data['name'],
            description=playlist_data['description'],
            tracks=tracks,
            target_audio_features=target_features,
            provider=playlist_data['provider']
        )
        
        # Check licensing
        youtube_key = settings.YOUTUBE_API_KEY
        if not youtube_key or youtube_key.strip() in ["your_youtube_api_key_here", "your_youtube_api_key"]:
            print("❌ Error: YouTube API key not configured")
            print("📝 Licensing check requires YOUTUBE_API_KEY in .env file")
            print("🔧 Get your API key from: https://console.cloud.google.com/")
            print("💡 Replace 'your_youtube_api_key_here' with your actual API key")
            print(f"🔍 Current value: '{youtube_key}'")
            return
        
        try:
            async with LicensingChecker(settings) as licensing_checker:
                print("\n🔍 Checking licensing information...")
                licensed_playlist = await licensing_checker.check_playlist_licensing(playlist)
        except Exception as e:
            print(f"❌ Error: Licensing check failed: {e}")
            return
        
        # Display licensing results
        display_licensing_summary(licensed_playlist.to_dict())
        
        # Save updated playlist with licensing info
        if args.output:
            output_path = get_output_path(args.output, playlist_data['provider'])
        else:
            # Generate new filename with licensing suffix
            base_name = os.path.splitext(os.path.basename(args.playlist_file))[0]
            output_path = get_output_path(f"{base_name}_licensed.json", playlist_data['provider'])
        
        with open(output_path, 'w') as f:
            json.dump(licensed_playlist.to_dict(), f, indent=2)
        
        print(f"\n💾 Licensed playlist saved to: {output_path}")
        print(f"📁 Full path: {os.path.abspath(output_path)}")
        
    except Exception as e:
        print(f"Error checking licensing: {e}")

def display_licensing_summary(playlist):
    """Display licensing information summary."""
    print("\n" + "="*60)
    print("📋 Licensing Summary")
    print("="*60)
    
    tracks = playlist.get('tracks', [])
    total_tracks = len(tracks)
    licensed_tracks = 0
    high_risk_tracks = 0
    
    print(f"Total Tracks: {total_tracks}")
    
    if total_tracks > 0:
        for track in tracks:
            license_info = track.get('license_info')
            if license_info:
                if license_info.get('business_use_allowed', False):
                    licensed_tracks += 1
                risk_score = license_info.get('business_risk_score', float('nan'))
                if risk_score == risk_score and risk_score > 0.7:  # Check for NaN and high risk
                    high_risk_tracks += 1
        
        print(f"Business Licensed: {licensed_tracks}/{total_tracks} ({licensed_tracks/total_tracks*100:.1f}%)")
        print(f"High Risk Tracks: {high_risk_tracks}/{total_tracks} ({high_risk_tracks/total_tracks*100:.1f}%)")
        
        # Show first few tracks with licensing info
        print(f"\nTrack Licensing Details:")
        print("-" * 60)
        for i, track in enumerate(tracks[:5], 1):
            license_info = track.get('license_info', {})
            business_use = "✅ Yes" if license_info.get('business_use_allowed', False) else "❌ No"
            risk_score = license_info.get('business_risk_score', float('nan'))
            
            if risk_score != risk_score:  # Check for NaN
                risk_level = "❓ Unknown"
                risk_display = "N/A"
            else:
                risk_level = "🟢 Low" if risk_score < 0.3 else "🟡 Medium" if risk_score < 0.7 else "🔴 High"
                risk_display = f"{risk_score:.2f}"
            
            print(f"{i:2d}. {track['name']} - {track['artist']}")
            print(f"    Business Use: {business_use} | Risk: {risk_level} ({risk_display})")
        
        if len(tracks) > 5:
            print(f"    ... and {len(tracks) - 5} more tracks")
        print("-" * 60)

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Music Playlist Generator with Licensing Checker')
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate playlist command
    generate_parser = subparsers.add_parser('generate', help='Generate a music playlist')
    generate_parser.add_argument('--features', type=str, help='JSON string of audio features')
    generate_parser.add_argument('--length', type=int, default=20, help='Playlist length (default: 20)')
    generate_parser.add_argument('--provider', type=str, default='spotify', choices=['spotify', 'apple_music'], help='Music provider')
    generate_parser.add_argument('--check-licensing', action='store_true', dest='check_licensing', help='Check business licensing')
    generate_parser.add_argument('--output', type=str, help='Output file path')
    
    # Generate and create on Spotify command
    create_parser = subparsers.add_parser('create-spotify', help='Generate playlist and create directly on Spotify')
    create_parser.add_argument('--features', type=str, help='JSON string of audio features')
    create_parser.add_argument('--length', type=int, default=20, help='Playlist length (default: 20)')
    create_parser.add_argument('--provider', type=str, default='spotify', choices=['spotify'], help='Music provider (Spotify only)')
    create_parser.add_argument('--check-licensing', action='store_true', dest='check_licensing', help='Check business licensing')
    create_parser.add_argument('--output', type=str, help='Output file path for backup')
    create_parser.add_argument('--public', action='store_true', help='Make playlist public')
    
    # Upload existing playlist to Spotify command
    upload_parser = subparsers.add_parser('upload-spotify', help='Upload existing playlist file to Spotify')
    upload_parser.add_argument('playlist_file', type=str, help='Path to playlist JSON file')
    upload_parser.add_argument('--public', action='store_true', help='Make playlist public')
    upload_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing playlist with same name')
    upload_parser.add_argument('--reauth', action='store_true', help='Force re-authentication')
    
    # Spotify authentication command
    auth_parser = subparsers.add_parser('spotify-auth', help='Manage Spotify authentication')
    auth_parser.add_argument('--status', action='store_true', help='Check authentication status')
    auth_parser.add_argument('--logout', action='store_true', help='Logout from Spotify')
    auth_parser.add_argument('--reauth', action='store_true', help='Force re-authentication')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run the test suite')
    
    # Check licensing command
    licensing_parser = subparsers.add_parser('check-licensing', help='Check licensing for existing playlist')
    licensing_parser.add_argument('playlist_file', type=str, help='Path to playlist JSON file')
    licensing_parser.add_argument('--output', type=str, help='Output file path for licensed playlist')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'generate':
        asyncio.run(generate_playlist(args))
    elif args.command == 'create-spotify':
        asyncio.run(generate_and_create_spotify_playlist(args))
    elif args.command == 'upload-spotify':
        asyncio.run(create_spotify_playlist(args))
    elif args.command == 'spotify-auth':
        asyncio.run(spotify_auth(args))
    elif args.command == 'test':
        exit_code = run_tests()
        sys.exit(exit_code)
    elif args.command == 'check-licensing':
        asyncio.run(check_licensing(args))
    else:
        # Default behavior for backward compatibility
        if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
            parser.print_help()
        else:
            # Assume generate command for backward compatibility
            args.command = 'generate'
            asyncio.run(generate_playlist(args))

if __name__ == "__main__":
    main() 