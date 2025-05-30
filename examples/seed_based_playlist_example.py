#!/usr/bin/env python3
"""
Example script demonstrating seed-based playlist generation.
This shows how to use user-provided track names and artists to generate similar playlists.
"""

import asyncio
import os
import sys
import json
from typing import List, Dict, Any, Optional

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.seed_track import SeedTrack
from src.models.track import Track
from src.models.audio_features import AudioFeatures
from src.services.seed_track_resolver import SeedTrackResolver, ResolutionConfig
from src.services.similarity_engine import SimilarityEngine, DiversitySettings
from src.utils.cache_manager import CacheManager

class MockSpotifyClient:
    """Mock Spotify client for demonstration purposes."""
    
    def __init__(self, client_id: str, client_secret: str, cache_manager: Optional[CacheManager] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cache_manager = cache_manager
        self._session = None
    
    async def search_tracks(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Mock search that returns realistic track data."""
        # Mock data for demonstration - in Spotify API format
        mock_tracks = [
            {
                "id": "mock_track_1",
                "name": "Bohemian Rhapsody",
                "artists": [{"name": "Queen"}],
                "album": {"name": "A Night at the Opera", "release_date": "1975-10-31"},
                "duration_ms": 355000,
                "popularity": 95,
                "explicit": False,
                "preview_url": None,
                "external_urls": {"spotify": "https://open.spotify.com/track/mock1"},
                "uri": "spotify:track:mock_track_1"
            },
            {
                "id": "mock_track_2", 
                "name": "Hotel California",
                "artists": [{"name": "Eagles"}],
                "album": {"name": "Hotel California", "release_date": "1976-12-08"},
                "duration_ms": 391000,
                "popularity": 90,
                "explicit": False,
                "preview_url": None,
                "external_urls": {"spotify": "https://open.spotify.com/track/mock2"},
                "uri": "spotify:track:mock_track_2"
            },
            {
                "id": "mock_track_3",
                "name": "Stairway to Heaven", 
                "artists": [{"name": "Led Zeppelin"}],
                "album": {"name": "Led Zeppelin IV", "release_date": "1971-11-08"},
                "duration_ms": 482000,
                "popularity": 88,
                "explicit": False,
                "preview_url": None,
                "external_urls": {"spotify": "https://open.spotify.com/track/mock3"},
                "uri": "spotify:track:mock_track_3"
            },
            {
                "id": "mock_track_4",
                "name": "Sweet Child O' Mine",
                "artists": [{"name": "Guns N' Roses"}],
                "album": {"name": "Appetite for Destruction", "release_date": "1987-07-21"},
                "duration_ms": 356000,
                "popularity": 85,
                "explicit": False,
                "preview_url": None,
                "external_urls": {"spotify": "https://open.spotify.com/track/mock4"},
                "uri": "spotify:track:mock_track_4"
            },
            {
                "id": "mock_track_5",
                "name": "Comfortably Numb",
                "artists": [{"name": "Pink Floyd"}],
                "album": {"name": "The Wall", "release_date": "1979-11-30"},
                "duration_ms": 382000,
                "popularity": 87,
                "explicit": False,
                "preview_url": None,
                "external_urls": {"spotify": "https://open.spotify.com/track/mock5"},
                "uri": "spotify:track:mock_track_5"
            }
        ]
        
        # Simple matching logic for demo
        query_lower = query.lower()
        matching_tracks = []
        
        for track in mock_tracks:
            track_name = track["name"].lower()
            artist_names = [artist["name"].lower() for artist in track["artists"]]
            
            if (query_lower in track_name or 
                any(query_lower in artist_name for artist_name in artist_names) or
                any(word in track_name or any(word in artist_name for artist_name in artist_names)
                    for word in query_lower.split())):
                matching_tracks.append(track)
        
        # If no specific matches, return some tracks for similarity search
        if not matching_tracks:
            matching_tracks = mock_tracks[:min(limit, len(mock_tracks))]
        
        return matching_tracks[:limit]
    
    async def get_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Mock audio features for demonstration."""
        # Mock audio features that vary by track
        mock_features = {
            "mock_track_1": {  # Bohemian Rhapsody
                "tempo": 72.0,
                "energy": 0.8,
                "valence": 0.6,
                "danceability": 0.4,
                "acousticness": 0.3,
                "instrumentalness": 0.2,
                "liveness": 0.1,
                "speechiness": 0.1,
                "key": 3,
                "mode": 1
            },
            "mock_track_2": {  # Hotel California
                "tempo": 75.0,
                "energy": 0.7,
                "valence": 0.5,
                "danceability": 0.3,
                "acousticness": 0.4,
                "instrumentalness": 0.3,
                "liveness": 0.1,
                "speechiness": 0.1,
                "key": 7,
                "mode": 0
            },
            "mock_track_3": {  # Stairway to Heaven
                "tempo": 82.0,
                "energy": 0.6,
                "valence": 0.4,
                "danceability": 0.2,
                "acousticness": 0.6,
                "instrumentalness": 0.4,
                "liveness": 0.1,
                "speechiness": 0.1,
                "key": 11,
                "mode": 0
            },
            "mock_track_4": {  # Sweet Child O' Mine
                "tempo": 125.0,
                "energy": 0.9,
                "valence": 0.7,
                "danceability": 0.5,
                "acousticness": 0.1,
                "instrumentalness": 0.1,
                "liveness": 0.2,
                "speechiness": 0.1,
                "key": 2,
                "mode": 1
            },
            "mock_track_5": {  # Comfortably Numb
                "tempo": 63.0,
                "energy": 0.5,
                "valence": 0.3,
                "danceability": 0.2,
                "acousticness": 0.2,
                "instrumentalness": 0.6,
                "liveness": 0.1,
                "speechiness": 0.1,
                "key": 7,
                "mode": 0
            }
        }
        
        return mock_features.get(track_id)
    
    async def close(self):
        """Close any open connections."""
        if self._session:
            await self._session.close()

async def main():
    """Main example function."""
    print("🎵 Seed-Based Playlist Generator Example")
    print("=" * 50)
    
    # Example seed tracks (user-provided, potentially incomplete)
    seed_track_inputs = [
        "Bohemian Rhapsody - Queen",
        "Hotel California by Eagles",
        "Stairway to Heaven: Led Zeppelin", 
        "Sweet Child O' Mine - Guns N' Roses",
        "Comfortably Numb - Pink Floyd"
    ]
    
    print(f"📝 Input seed tracks:")
    for i, track_input in enumerate(seed_track_inputs, 1):
        print(f"  {i}. {track_input}")
    print()
    
    # Create seed track objects
    seed_tracks = []
    for track_input in seed_track_inputs:
        try:
            seed_track = SeedTrack.from_string(track_input)
            seed_tracks.append(seed_track)
            print(f"✅ Parsed: {seed_track.display_name}")
        except Exception as e:
            print(f"❌ Failed to parse '{track_input}': {e}")
    
    print(f"\n🔍 Successfully parsed {len(seed_tracks)} seed tracks")
    print()
    
    # Initialize services
    cache_manager = CacheManager()
    spotify_client = MockSpotifyClient("mock_id", "mock_secret", cache_manager)
    
    try:
        # Initialize resolver and similarity engine
        resolver = SeedTrackResolver(spotify_client=spotify_client, cache_manager=cache_manager)
        similarity_engine = SimilarityEngine(spotify_client=spotify_client, cache_manager=cache_manager)
        
        # Configure resolution settings
        resolution_config = ResolutionConfig(
            confidence_threshold=0.7,
            max_search_results=50,
            fuzzy_threshold=0.6,
            search_timeout_seconds=30
        )
        
        print("🔎 Resolving seed tracks...")
        resolved_tracks = await resolver.resolve_seed_tracks(seed_tracks, resolution_config)
        
        print(f"✅ Successfully resolved {len(resolved_tracks)} out of {len(seed_tracks)} tracks")
        
        # Display resolution results
        for resolved in resolved_tracks:
            confidence_emoji = "🟢" if resolved.is_high_confidence else "🟡" if resolved.is_medium_confidence else "🔴"
            print(f"  {confidence_emoji} {resolved.seed_track.display_name}")
            print(f"     → {resolved.resolved_track.display_name}")
            print(f"     → Confidence: {resolved.confidence_score:.2f} ({resolved.resolution_method})")
        
        # Show resolution statistics
        stats = resolver.get_resolution_stats(resolved_tracks)
        print(f"\n📊 Resolution Statistics:")
        print(f"   Success Rate: {stats['success_rate']:.1%}")
        print(f"   Average Confidence: {stats['average_confidence']:.2f}")
        print(f"   High Confidence: {stats['high_confidence']}")
        print(f"   Medium Confidence: {stats['medium_confidence']}")
        print(f"   Low Confidence: {stats['low_confidence']}")
        
        if resolved_tracks:
            print("\n🎼 Generating similar playlist...")
            
            # Configure diversity settings
            diversity_settings = DiversitySettings(
                max_per_artist=2,
                feature_diversity_factor=0.3,
                include_seeds=False,
                era_distribution={
                    "2020s": 0.2,
                    "2010s": 0.3,
                    "2000s": 0.2,
                    "1990s": 0.15,
                    "older": 0.15
                }
            )
            
            # Set target length
            target_length = 20
            
            # Generate playlist
            playlist = await similarity_engine.generate_playlist(
                resolved_tracks,
                target_length,
                diversity_settings=diversity_settings
            )
            
            print(f"🎵 Generated playlist: '{playlist.name}'")
            print(f"   Description: {playlist.description}")
            print(f"   Tracks: {len(playlist.tracks)}")
            print()
            
            # Display playlist tracks
            print("📋 Playlist tracks:")
            for i, track in enumerate(playlist.tracks, 1):
                duration = track.duration_formatted
                similarity = getattr(track, 'similarity_score', 0.0)
                print(f"  {i:2d}. {track.display_name} ({duration}) - Similarity: {similarity:.2f}")
            
            # Save playlist to file
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'playlists')
            os.makedirs(output_dir, exist_ok=True)
            
            playlist_file = os.path.join(output_dir, f"seed_based_playlist_{playlist.created_at.strftime('%Y%m%d_%H%M%S')}.json")
            
            # Convert playlist to dict for JSON serialization
            playlist_dict = playlist.to_dict()
            
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump(playlist_dict, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n💾 Playlist saved to: {playlist_file}")
            
            # Display generation statistics
            print(f"\n📈 Generation Statistics:")
            print(f"   Final Track Count: {len(playlist.tracks)}")
            print(f"   Target Length: {target_length}")
            print(f"   Playlist Duration: {playlist.total_duration_formatted}")
        else:
            print("\n⚠️  No tracks were resolved. Cannot generate playlist.")
            await simulate_playlist_generation(seed_tracks)
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        await spotify_client.close()
        if hasattr(cache_manager, 'close'):
            await cache_manager.close()

async def simulate_playlist_generation(seed_tracks: List[SeedTrack]):
    """Simulate the playlist generation process without real API calls."""
    print("🎭 Simulating playlist generation process...")
    print()
    
    print("🔎 Simulating seed track resolution...")
    for seed_track in seed_tracks:
        print(f"  🟢 {seed_track.display_name}")
        print(f"     → Found: {seed_track.track_name} by {seed_track.artist_name}")
        print(f"     → Confidence: 0.95 (exact_match)")
    
    print(f"\n✅ Simulated resolution of {len(seed_tracks)} tracks")
    
    print("\n🎼 Simulating similarity search...")
    print("   🔍 Extracting audio features from seed tracks...")
    print("   🔍 Searching for similar tracks...")
    print("   🔍 Applying diversity algorithms...")
    
    print("\n🎵 Simulated playlist generation complete!")
    print("   📋 Generated 20 tracks similar to your seeds")
    print("   🎯 Applied artist diversity (max 2 per artist)")
    print("   🕰️ Applied temporal diversity across eras")
    print("   ⚖️ Balanced similarity vs. diversity")
    
    print("\n💡 To run with real data:")
    print("   1. Set up Spotify API credentials")
    print("   2. Export SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
    print("   3. Implement actual API client classes")
    print("   4. Run this script again")

if __name__ == "__main__":
    asyncio.run(main()) 