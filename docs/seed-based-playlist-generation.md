# Seed-Based Playlist Generation

This document describes the seed-based playlist generation feature, which allows users to provide track names and artist names (potentially incomplete or inaccurate) to generate playlists of similar tracks.

## Overview

The seed-based playlist generation system consists of three main components:

1. **Track Resolution**: Resolves user-provided track information to actual tracks using fuzzy matching
2. **Similarity Analysis**: Extracts audio features and finds similar tracks
3. **Playlist Generation**: Applies diversity algorithms to create balanced playlists

## Quick Start

```python
import asyncio
from src.models.seed_track import SeedTrack
from src.services.seed_track_resolver import SeedTrackResolver
from src.services.similarity_engine import SimilarityEngine
from src.api.spotify_client import SpotifyClient

async def generate_playlist():
    # Create seed tracks from user input
    seed_tracks = [
        SeedTrack.from_string("Bohemian Rhapsody - Queen"),
        SeedTrack.from_string("Hotel California by Eagles"),
        SeedTrack("Stairway to Heaven", "Led Zeppelin")
    ]
    
    # Initialize services
    spotify_client = SpotifyClient(client_id, client_secret)
    resolver = SeedTrackResolver(spotify_client=spotify_client)
    similarity_engine = SimilarityEngine(spotify_client=spotify_client)
    
    # Resolve seed tracks
    resolved_tracks = await resolver.resolve_seed_tracks(seed_tracks)
    
    # Generate playlist
    playlist = await similarity_engine.generate_playlist(
        resolved_tracks, 
        target_length=20
    )
    
    return playlist
```

## Input Formats

The system accepts various input formats for seed tracks:

### String Formats

```python
# Format: "Track Name - Artist Name"
SeedTrack.from_string("Bohemian Rhapsody - Queen")

# Format: "Artist Name: Track Name"
SeedTrack.from_string("Queen: Bohemian Rhapsody")

# Format: "Track Name by Artist Name"
SeedTrack.from_string("Bohemian Rhapsody by Queen")
```

### Direct Construction

```python
SeedTrack(
    track_name="Bohemian Rhapsody",
    artist_name="Queen",
    album_name="A Night at the Opera",  # Optional
    year=1975,  # Optional
    confidence_threshold=0.7  # Optional
)
```

### CSV Import

```python
# From CSV row dictionary
csv_row = {
    "track_name": "Bohemian Rhapsody",
    "artist_name": "Queen",
    "album": "A Night at the Opera",
    "year": "1975"
}
seed_track = SeedTrack.from_csv_row(csv_row)
```

## Track Resolution Process

The track resolution process uses a multi-stage approach to handle incomplete or inaccurate input:

### Stage 1: Exact Match
- Searches with original, unmodified input
- Highest confidence threshold (0.95+)

### Stage 2: Normalized Search
- Applies string normalization (lowercase, remove punctuation, etc.)
- High confidence threshold (0.8+)

### Stage 3: Partial Match
- Generates search variations
- Handles partial track names and artist variations
- Medium confidence threshold (0.7+)

### Stage 4: Fuzzy Search
- Broad search with similarity filtering
- Uses phonetic matching and token similarity
- Lower confidence threshold (0.4+)

## Fuzzy Matching Algorithms

### String Normalization
- Unicode normalization (NFD decomposition)
- Remove diacritics and accents
- Handle featuring artists (`feat.`, `ft.`, `featuring`)
- Remove remix indicators (`remix`, `mix`, `version`)
- Remove parenthetical content (`(Official Video)`, `(Remastered)`)

### Similarity Algorithms
- **Levenshtein Distance**: Character-level edit distance
- **Jaro-Winkler**: Better for shorter strings, emphasizes prefixes
- **Token Similarity**: Word-level Jaccard similarity
- **Phonetic Matching**: Soundex-like algorithm for misspellings

### Artist Aliases
The system includes a comprehensive database of artist aliases:

```json
{
  "eminem": ["slim shady", "marshall mathers", "b-rabbit"],
  "jay-z": ["jay z", "shawn carter", "hov"],
  "the beatles": ["beatles", "fab four"]
}
```

## Audio Feature Analysis

### Feature Extraction
The system extracts audio features from resolved seed tracks:

- **Tempo**: Beats per minute (50-200 BPM)
- **Energy**: Musical intensity (0.0-1.0)
- **Valence**: Musical positivity (0.0-1.0)
- **Danceability**: Rhythm and beat strength (0.0-1.0)
- **Acousticness**: Acoustic vs electronic (0.0-1.0)
- **Instrumentalness**: Vocal vs instrumental (0.0-1.0)
- **Liveness**: Live performance detection (0.0-1.0)
- **Speechiness**: Speech-like qualities (0.0-1.0)

### Feature Profile Generation
Creates ranges for each feature with configurable tolerance:

```python
AudioFeatureProfile(
    tempo_range=(120.0, 140.0),
    energy_range=(0.6, 0.9),
    valence_range=(0.4, 0.8),
    # ... other features
    preferred_keys=[0, 7],  # C major, G major
    preferred_modes=[1],    # Major mode
    preferred_genres=["rock", "classic rock"]
)
```

## Similarity Search

### Query Generation
Generates search queries based on audio features:

- **Genre-based**: `genre:rock`, `genre:pop`
- **Mood-based**: `happy`, `sad`, `energetic`, `calm`
- **Tempo-based**: `fast`, `slow`, `uptempo`, `ballad`

### Multi-Provider Search
Searches across multiple music providers in parallel:

- Spotify (weight: 1.0)
- Apple Music (weight: 0.9)
- YouTube Music (weight: 0.7)

### Similarity Scoring
Calculates weighted similarity scores:

```python
DEFAULT_FEATURE_WEIGHTS = {
    "tempo": 0.15,
    "energy": 0.20,
    "valence": 0.15,
    "danceability": 0.15,
    "acousticness": 0.10,
    "instrumentalness": 0.05,
    "liveness": 0.05,
    "speechiness": 0.05,
    "key": 0.05,
    "mode": 0.05
}
```

## Diversity Algorithms

### Artist Diversity
Limits tracks per artist to increase variety:

```python
DiversitySettings(max_per_artist=2)
```

### Feature Diversity
Applies diversity penalty to avoid clustering:

```python
DiversitySettings(feature_diversity_factor=0.3)
```

### Temporal Diversity
Ensures representation across time periods:

```python
DiversitySettings(era_distribution={
    "2020s": 0.3,
    "2010s": 0.3,
    "2000s": 0.2,
    "1990s": 0.1,
    "older": 0.1
})
```

## Configuration Options

### Resolution Configuration

```python
ResolutionConfig(
    confidence_threshold=0.7,
    max_search_results=50,
    fuzzy_threshold=0.6,
    enable_phonetic=True,
    search_timeout_seconds=30,
    max_concurrent_searches=5,
    provider_weights={
        "spotify": 1.0,
        "apple_music": 0.9,
        "youtube_music": 0.7
    }
)
```

### Similarity Configuration

```python
SimilarityConfig(
    target_count_multiplier=3,
    min_similarity_threshold=0.4,
    preferred_similarity_threshold=0.6,
    search_timeout_seconds=60,
    max_concurrent_searches=10,
    feature_weights=DEFAULT_FEATURE_WEIGHTS
)
```

### Diversity Settings

```python
DiversitySettings(
    max_per_artist=2,
    feature_diversity_factor=0.3,
    era_distribution=DEFAULT_ERA_DISTRIBUTION,
    include_seeds=False,
    genre_strict=False,
    tempo_tolerance=0.15,
    popularity_bias=0.1
)
```

## Error Handling

### Common Scenarios
- **No matches found**: Suggests alternative spellings
- **Multiple high-confidence matches**: Presents options to user
- **All low-confidence matches**: Requests manual verification
- **API rate limiting**: Implements exponential backoff
- **Network timeouts**: Retries with different providers

### Graceful Degradation
- Continue with partial results if some tracks fail
- Use cached results when APIs are unavailable
- Provide manual search links as fallback
- Allow users to skip problematic tracks

## Performance Optimization

### Caching Strategy
- Cache resolved tracks to avoid re-resolution
- Cache similarity calculations between tracks
- Cache search results for feature-based queries
- Use Redis for distributed caching

### Parallel Processing
- Parallel provider searches
- Parallel similarity calculations
- Batch audio feature requests
- Async playlist generation pipeline

## Usage Examples

### Basic Usage

```python
# Simple seed-based playlist generation
seed_tracks = [
    SeedTrack.from_string("Bohemian Rhapsody - Queen"),
    SeedTrack.from_string("Hotel California - Eagles")
]

resolver = SeedTrackResolver(spotify_client=spotify_client)
similarity_engine = SimilarityEngine(spotify_client=spotify_client)

resolved_tracks = await resolver.resolve_seed_tracks(seed_tracks)
playlist = await similarity_engine.generate_playlist(resolved_tracks, target_length=20)
```

### Advanced Configuration

```python
# Custom resolution and diversity settings
resolution_config = ResolutionConfig(
    confidence_threshold=0.8,
    fuzzy_threshold=0.7,
    search_timeout_seconds=45
)

diversity_settings = DiversitySettings(
    max_per_artist=1,
    feature_diversity_factor=0.5,
    include_seeds=True,
    era_distribution={
        "2020s": 0.4,
        "2010s": 0.4,
        "2000s": 0.2
    }
)

resolved_tracks = await resolver.resolve_seed_tracks(seed_tracks, resolution_config)
playlist = await similarity_engine.generate_playlist(
    resolved_tracks, 
    target_length=30,
    diversity_settings=diversity_settings
)
```

### Batch Processing

```python
# Process multiple playlists
seed_track_lists = [
    [SeedTrack.from_string("Track1 - Artist1"), ...],
    [SeedTrack.from_string("Track2 - Artist2"), ...],
    # ... more lists
]

playlists = []
for seed_tracks in seed_track_lists:
    resolved_tracks = await resolver.resolve_seed_tracks(seed_tracks)
    playlist = await similarity_engine.generate_playlist(resolved_tracks, target_length=20)
    playlists.append(playlist)
```

## Quality Metrics

### Resolution Quality
- **Success Rate**: Percentage of tracks successfully resolved
- **Average Confidence**: Mean confidence score across resolved tracks
- **Method Distribution**: Breakdown by resolution method used

### Playlist Quality
- **Similarity Distribution**: Range of similarity scores in final playlist
- **Diversity Metrics**: Artist diversity, temporal diversity, feature diversity
- **User Satisfaction**: Feedback-based quality assessment

## Best Practices

### Input Preparation
1. Provide as much information as possible (track name, artist, album, year)
2. Use consistent formatting for batch processing
3. Handle special characters and Unicode properly
4. Validate input before processing

### Configuration Tuning
1. Adjust confidence thresholds based on input quality
2. Tune feature weights for specific genres or use cases
3. Customize diversity settings for target audience
4. Monitor and adjust based on user feedback

### Performance Optimization
1. Use caching for repeated operations
2. Batch API requests when possible
3. Implement proper rate limiting
4. Monitor API usage and costs

### Error Handling
1. Implement comprehensive logging
2. Provide meaningful error messages to users
3. Have fallback strategies for API failures
4. Allow manual intervention for edge cases 