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
        try:
            async with LicensingChecker(settings) as licensing_checker:
                print("\n🔍 Checking licensing information...")
                licensed_playlist = await licensing_checker.check_playlist_licensing(playlist)
        except Exception as e:
            print(f"⚠️  Warning: Licensing check failed ({e})")
            print("📝 Note: YouTube API key may not be configured. Generating mock licensing data...")
            
            # Add mock licensing data for demonstration
            from src.models.license_info import LicenseInfo
            for track in playlist.tracks:
                # Create mock license info
                mock_license = LicenseInfo.create_unknown()
                mock_license.source = "mock_data"
                mock_license.confidence_score = 0.1
                track.add_license_info(mock_license)
            
            licensed_playlist = playlist
        
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
                if license_info.get('business_risk_score', 0) > 0.7:
                    high_risk_tracks += 1
        
        print(f"Business Licensed: {licensed_tracks}/{total_tracks} ({licensed_tracks/total_tracks*100:.1f}%)")
        print(f"High Risk Tracks: {high_risk_tracks}/{total_tracks} ({high_risk_tracks/total_tracks*100:.1f}%)")
        
        # Show first few tracks with licensing info
        print(f"\nTrack Licensing Details:")
        print("-" * 60)
        for i, track in enumerate(tracks[:5], 1):
            license_info = track.get('license_info', {})
            business_use = "✅ Yes" if license_info.get('business_use_allowed', False) else "❌ No"
            risk_score = license_info.get('business_risk_score', 0)
            risk_level = "🟢 Low" if risk_score < 0.3 else "🟡 Medium" if risk_score < 0.7 else "🔴 High"
            
            print(f"{i:2d}. {track['name']} - {track['artist']}")
            print(f"    Business Use: {business_use} | Risk: {risk_level} ({risk_score:.2f})")
        
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