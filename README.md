# Music Playlist Generator with Licensing Checker

A Python application that generates music playlists using music provider APIs (Spotify, Apple Music, etc.) based on specified audio features and checks licensing availability for business use on platforms like YouTube.

## ✅ Status: Fully Implemented and Tested

All core functionality is working, including Spotify API integration, YouTube licensing verification, audio feature-based playlist generation, web API endpoints, CLI interface, and comprehensive error handling.

## Features

### 🎵 Playlist Generation
- Generate playlists based on audio features (tempo, energy, valence, etc.)
- Support for multiple music providers (Spotify, Apple Music)
- Customizable playlist length and diversity settings
- Genre and mood-based filtering
- Audio feature similarity matching
- Cross-provider audio feature normalization

### 📋 Licensing Verification
- Check YouTube Content ID for business use licensing
- Verify Creative Commons licensing
- Check for copyright claims and monetization restrictions
- Generate licensing reports for business compliance
- Risk assessment for commercial use

### 🎛️ Audio Feature Matching
- Tempo (BPM) matching with tolerance ranges
- Energy level matching (0.0 - 1.0 scale)
- Valence (musical positivity) matching
- Danceability and acousticness filtering
- Key and mode preferences
- Weighted similarity scoring between tracks

### 🔊 Advanced Audio Analysis (Optional)
- File-based audio analysis using librosa
- Audio fingerprinting for similarity matching
- Real-time feature extraction from audio files
- Support for multiple audio formats

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (for cloning the repository)

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Spotify-Lofi-Generator
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp env.example .env
```

Edit `.env` with your API credentials:
```env
# Spotify API (Required)
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# YouTube Data API (Required for licensing checks)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Apple Music API (Optional)
APPLE_MUSIC_KEY_ID=your_apple_music_key_id
APPLE_MUSIC_TEAM_ID=your_apple_music_team_id
APPLE_MUSIC_PRIVATE_KEY=your_apple_music_private_key

# Redis (Optional - will use in-memory cache if not provided)
REDIS_URL=redis://localhost:6379
```

5. **Verify installation**:
```bash
# Run comprehensive setup check
python setup_env.py

# Run the test suite
python main.py test

# Or run tests directly with pytest
pytest tests/ -v
```

## Getting API Keys

### Spotify API (Required)
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Copy Client ID and Client Secret

### YouTube Data API (Required for licensing)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable YouTube Data API v3
3. Create credentials (API Key)

### Apple Music API (Optional)
1. Join [Apple Developer Program](https://developer.apple.com/programs/)
2. Create MusicKit identifier
3. Generate private key

## Usage

### Command Line Interface

Generate a playlist with specific audio features:

```bash
python main.py generate --features '{"energy": 0.8, "valence": 0.6, "tempo": 120}' --length 20 --provider spotify --check-licensing
```

**Command Variations**:
```bash
# Basic playlist generation (auto-saves to output/playlists/)
python main.py generate --features '{"energy": 0.8, "valence": 0.6}' --length 10 --provider spotify

# With licensing check
python main.py generate --features '{"energy": 0.8, "valence": 0.6, "tempo": 120}' --length 20 --provider spotify --check-licensing

# Save to custom filename (still goes to output/playlists/)
python main.py generate --features '{"energy": 0.3, "valence": 0.7}' --length 15 --provider spotify --output "chill_vibes.json"

# Low energy, sad playlist
python main.py generate --features '{"energy": 0.2, "valence": 0.3}' --length 15 --provider spotify --output "sad_playlist.json"

# Apple Music provider
python main.py generate --features '{"energy": 0.8, "valence": 0.6}' --length 20 --provider apple_music

# Complex audio features
python main.py generate --features '{"energy": 0.8, "valence": 0.6, "tempo": 120, "danceability": 0.9, "acousticness": 0.2}' --length 25 --provider spotify --check-licensing

# Run tests
python main.py test

# Check licensing for existing playlist
python main.py check-licensing output/playlists/my_playlist.json

# Check licensing with custom output filename
python main.py check-licensing output/playlists/my_playlist.json --output "my_playlist_licensed.json"
```

**Note**: For backward compatibility, the old command format still works, but the new subcommand format is recommended.

### Licensing Check for Existing Playlists

You can check licensing information for previously generated playlists without regenerating them:

```bash
# Check licensing for an existing playlist
python main.py check-licensing output/playlists/my_playlist.json

# Save licensed version with custom filename
python main.py check-licensing output/playlists/my_playlist.json --output "business_approved_playlist.json"
```

The licensing check will:
- Load the existing playlist from the JSON file
- Check each track's licensing status via YouTube API
- Display a comprehensive licensing summary
- Save an updated playlist file with licensing information
- Show business use recommendations and risk assessments

**Note**: If YouTube API key is not configured, the tool will generate mock licensing data for demonstration purposes.

### Playlist Display

When generating playlists, the application now displays a comprehensive summary including:

- **Playlist Information**: Name, description, total tracks, and provider
- **Target Audio Features**: The requested audio characteristics
- **Track Listing**: First 10 tracks with details (name, artist, album, duration, popularity)
- **File Location**: Automatic saving to `output/playlists/` with timestamp or custom filename

Example output:
```
============================================================
🎵 Playlist Generated: Feel Good Mix
============================================================
Description: Generated playlist based on audio features: | Energy: 0.7 | Valence: 0.8
Total Tracks: 5
Provider: Spotify

Target Audio Features:
  Energy: 0.7
  Valence: 0.8

Tracks:
------------------------------------------------------------
 1. Happy Together - The Turtles
    Album: Happy Together | Duration: 2:56 | Popularity: 78
 2. Happy Face - Treaty Oak Revival
    Album: Happy Face | Duration: 3:22 | Popularity: 74
------------------------------------------------------------

💾 Playlist saved to: output/playlists/spotify_playlist_20250527_211533.json
📁 Full path: /Users/user/project/output/playlists/spotify_playlist_20250527_211533.json
```

### Licensing Check Output

When checking licensing for existing playlists, you'll see a detailed summary:

```
============================================================
📋 Licensing Summary
============================================================
Total Tracks: 7
Business Licensed: 2/7 (28.6%)
High Risk Tracks: 1/7 (14.3%)

Track Licensing Details:
------------------------------------------------------------
 1. Happy Song - Artist Name
    Business Use: ✅ Yes | Risk: 🟢 Low (0.15)
 2. Copyrighted Track - Major Label
    Business Use: ❌ No | Risk: 🔴 High (0.85)
------------------------------------------------------------

💾 Licensed playlist saved to: output/playlists/playlist_licensed.json
```

**Risk Levels:**
- 🟢 **Low Risk (0.0-0.3)**: Generally safe for business use
- 🟡 **Medium Risk (0.3-0.7)**: Review recommended, may require licensing
- 🔴 **High Risk (0.7-1.0)**: Avoid for commercial use, likely copyrighted

### Web API

Start the web server:
```bash
python app.py
```

The API will be available at `http://localhost:8000`

#### API Endpoints

- `POST /generate-playlist` - Generate a playlist
- `POST /check-licensing` - Check licensing for a track
- `GET /providers` - List supported providers
- `GET /audio-features/schema` - Get audio features schema
- `GET /health` - Health check endpoint

#### Example API Request

```bash
curl -X POST "http://localhost:8000/generate-playlist" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_features": {
      "energy": 0.8,
      "valence": 0.6,
      "danceability": 0.7,
      "tempo": 120
    },
    "length": 20,
    "provider": "spotify",
    "check_licensing": true
  }'
```

## Audio Features

The system uses standardized audio features (0.0-1.0 scale):

- **Energy**: Musical intensity and power
- **Valence**: Musical positivity/happiness  
- **Danceability**: Rhythm and beat strength
- **Acousticness**: Acoustic vs electronic content
- **Instrumentalness**: Vocal vs instrumental content
- **Tempo**: Beats per minute (50-200 BPM)
- **Loudness**: Overall loudness in dB (-60 to 0)
- **Key**: Musical key (0-11, C=0, C#=1, etc.)
- **Mode**: Major (1) or Minor (0)

## Architecture

### Core Components

- **API Clients** (`src/api/`): Spotify, Apple Music, and YouTube integrations
- **Services** (`src/services/`): Playlist generation, licensing verification, audio analysis
- **Models** (`src/models/`): Data structures for tracks, playlists, and audio features
- **Utilities** (`src/utils/`): Caching, rate limiting, validation, and audio analysis

### Key Features

- **Async/Await Support**: Non-blocking API calls for better performance
- **Caching & Rate Limiting**: Redis-based caching with automatic fallback
- **Cross-Provider Normalization**: Standardized audio features across providers
- **Comprehensive Error Handling**: Graceful degradation and retry logic
- **Extensible Design**: Easy to add new music providers

## Project Structure

```
├── main.py                     # CLI entry point with test runner
├── app.py                      # Web API entry point
├── setup_env.py               # Environment verification script
├── output/                     # Generated files and results
│   ├── playlists/             # Generated playlist JSON files
│   ├── reports/               # Licensing and analysis reports
│   └── cache/                 # Cached API responses (optional)
├── config/
│   ├── settings.py            # Application configuration
│   └── api_keys.py            # API key management
├── src/
│   ├── models/                # Data models
│   │   ├── track.py          # Track model
│   │   ├── playlist.py       # Playlist model
│   │   ├── audio_features.py # Audio features model
│   │   └── license_info.py   # License information model
│   ├── api/                   # API clients
│   │   ├── base_client.py    # Base API client
│   │   ├── spotify_client.py # Spotify integration
│   │   ├── apple_music_client.py # Apple Music integration
│   │   └── youtube_client.py # YouTube integration
│   ├── services/              # Business logic
│   │   ├── playlist_generator.py # Main playlist generation
│   │   ├── licensing_checker.py  # Licensing verification
│   │   └── audio_features.py     # Audio analysis service
│   └── utils/                 # Utilities
│       ├── audio_analyzer.py # File-based audio analysis
│       ├── cache_manager.py  # Caching utilities
│       ├── rate_limiter.py   # Rate limiting
│       └── validators.py     # Input validation
├── tests/                     # Test suite
│   ├── conftest.py           # Pytest configuration and fixtures
│   ├── integration/          # Integration tests
│   │   ├── test_implementation.py # Core functionality tests
│   │   └── test_cli_interface.py  # CLI interface tests
│   └── unit/                 # Unit tests
│       ├── test_audio_features.py # AudioFeatures model tests
│       ├── test_track.py     # Track model tests
│       ├── test_validators.py # Validation utility tests
│       └── test_rate_limiter.py # Rate limiter utility tests
├── requirements.txt           # Python dependencies
├── env.example               # Environment variables template
└── README.md                 # This file
```

## Troubleshooting

### Common Issues

**Import Errors**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Authentication Errors**:
- Verify API credentials in `.env` file
- Check Spotify app configuration

**Redis Connection Errors**:
- Redis is optional - app uses memory caching as fallback
- Install Redis: `brew install redis` (macOS) or `sudo apt-get install redis-server` (Ubuntu)

**Audio Analysis Issues**:
- librosa should work out of the box
- essentia is optional and complex to install

### API Rate Limits

- **Spotify**: 100 requests per minute
- **Apple Music**: 1000 requests per minute  
- **YouTube**: 10,000 requests per minute

The application includes built-in rate limiting and caching to stay within these limits.

## Licensing Compliance

The system provides comprehensive licensing analysis:

- **Business Use Status**: Clear indication of commercial use permissions
- **Risk Assessment**: Calculated risk scores for business use
- **Compliance Reports**: Detailed licensing reports for playlists
- **Recommendations**: Actionable suggestions for licensing compliance

### Risk Levels

- **Low Risk (0.0-0.3)**: Generally safe for business use
- **Medium Risk (0.3-0.7)**: Review recommended
- **High Risk (0.7-1.0)**: Avoid for commercial use

## Development

### Running Tests

```bash
# Run the complete test suite
python main.py test

# Run tests with pytest directly
pytest tests/ -v

# Run specific test categories
pytest tests/integration/ -v  # Integration tests only
pytest tests/unit/ -v         # Unit tests only
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Adding New Music Providers

1. Create a new client in `src/api/` inheriting from `BaseClient`
2. Implement required methods for authentication and track search
3. Add provider configuration to `settings.py`
4. Update the playlist generator service
5. Add tests for the new provider

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool provides licensing information for educational and informational purposes only. Always consult with legal professionals for commercial use decisions. The accuracy of licensing information cannot be guaranteed.