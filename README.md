# VibeEngine
### *AI-Powered Music Playlist Generator with Business Licensing*

<div align="center">

![VibeEngine Hero](assets/images/vibeengine-hero.png)

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)

**Create perfect playlists using AI-driven audio feature matching**  
*Generate vibes, not just music*

[Quick Start](#quick-start) • [Features](#features) • [API Docs](#api-reference) • [Examples](#examples)

</div>

---

## What is VibeEngine?

VibeEngine is an intelligent music curation platform that goes beyond simple playlist generation. Using advanced audio feature analysis and AI-powered matching algorithms, it creates perfectly curated playlists based on **mood**, **energy**, **tempo**, and **musical characteristics**.

**Perfect for:**
- **Content Creators** - Get business-licensed music for videos
- **Businesses** - Commercial-safe background music
- **Music Lovers** - Discover new tracks that match your vibe
- **Developers** - Integrate smart playlist generation

## Features

### **Smart Playlist Generation**
- **AI-Powered Matching** - Advanced audio feature analysis
- **Vibe Control** - Fine-tune energy, mood, tempo, and danceability
- **Multi-Provider** - Spotify, Apple Music support
- **Direct Integration** - Create playlists directly on your Spotify account

### **Business Licensing Verification**
- **Commercial Compliance** - YouTube Content ID verification
- **Risk Assessment** - Intelligent licensing risk scoring
- **Detailed Reports** - Comprehensive licensing analysis
- **Business-Safe** - Perfect for commercial projects

### **Advanced Audio Features**
```
Energy      ████████░░ 0.8    Valence     ██████░░░░ 0.6
Tempo       ███████░░░ 120    Dance       █████████░ 0.9
Acoustic    ██░░░░░░░░ 0.2    Instrum.    ████░░░░░░ 0.4
```

### **Developer-Friendly**
- **REST API** - Full web API with OpenAPI docs
- **Async/Await** - High-performance async operations
- **Smart Caching** - Redis-powered with intelligent fallbacks
- **Type Safety** - Full type hints and validation

## Quick Start

### Installation
```bash
git clone https://github.com/yourusername/VibeEngine.git
cd VibeEngine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
cp env.example .env
# Edit .env with your API keys
```

### Generate Your First Playlist
```bash
# Generate an energetic, happy playlist
python main.py create-spotify --features '{"energy": 0.8, "valence": 0.7}' --length 25

# Create a chill, relaxing vibe
python main.py create-spotify --features '{"energy": 0.3, "valence": 0.6}' --length 20
```

## Examples

### Morning Energy Boost
```bash
python main.py create-spotify \
  --features '{"energy": 0.9, "valence": 0.8, "tempo": 130}' \
  --length 20
```

### Late Night Study Session
```bash
python main.py generate \
  --features '{"energy": 0.2, "valence": 0.4, "acousticness": 0.8}' \
  --length 30 --output "focus_session.json"
```

### Business-Licensed Playlist
```bash
python main.py create-spotify \
  --features '{"energy": 0.6, "valence": 0.7}' \
  --check-licensing --length 25
```

## Audio Feature Guide

| Feature | Range | Description | Examples |
|---------|-------|-------------|----------|
| **Energy** | 0.0-1.0 | Musical intensity | 0.9 = Rock, 0.2 = Ambient |
| **Valence** | 0.0-1.0 | Musical positivity | 0.9 = Happy, 0.1 = Sad |
| **Tempo** | 50-200 | Beats per minute | 120 = Pop, 80 = Ballad |
| **Danceability** | 0.0-1.0 | Rhythm strength | 0.9 = EDM, 0.3 = Classical |
| **Acousticness** | 0.0-1.0 | Acoustic vs Electronic | 0.9 = Folk, 0.1 = Techno |

## API Keys Setup

<details>
<summary><strong>Spotify API (Required)</strong></summary>

1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create new app
3. Add `http://localhost:8888/callback` to Redirect URIs
4. Copy Client ID & Secret to `.env`

**Detailed setup:** [SPOTIFY_SETUP.md](SPOTIFY_SETUP.md)
</details>

<details>
<summary><strong>YouTube API (For Licensing)</strong></summary>

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable YouTube Data API v3
3. Create API Key
4. Add to `.env` file
</details>

## Web API

Start the API server:
```bash
python app.py
```

### Example API Call
```bash
curl -X POST "http://localhost:8000/generate-playlist" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_features": {"energy": 0.8, "valence": 0.6},
    "length": 20,
    "provider": "spotify"
  }'
```

## Licensing Intelligence

VibeEngine provides sophisticated licensing analysis:

```
============================================================
Licensing Summary
============================================================
Total Tracks: 25
Business Licensed: 18/25 (72%)
Medium Risk: 5/25 (20%)
High Risk: 2/25 (8%)

Recommendation: 72% tracks are safe for commercial use
```

**Risk Levels:**
- **Low Risk (0.0-0.3)** - Safe for business use
- **Medium Risk (0.3-0.7)** - Review recommended  
- **High Risk (0.7-1.0)** - Avoid for commercial use

## Architecture

```
VibeEngine
├── Core Engine
│   ├── Audio Feature Analysis
│   ├── Similarity Matching
│   └── Playlist Generation
├── API Integrations
│   ├── Spotify Client
│   ├── Apple Music Client
│   └── YouTube Licensing
├── Licensing Engine
│   ├── Risk Assessment
│   ├── Content ID Verification
│   └── Compliance Reports
└── Interfaces
    ├── CLI Commands
    ├── REST API
    └── Web Dashboard
```

## Testing

```bash
# Run complete test suite
python main.py test

# Run specific tests
pytest tests/integration/ -v
pytest tests/unit/ -v
```

## Roadmap

- [ ] Web Dashboard UI
- [ ] ML-Based Recommendation Engine
- [ ] Mobile App
- [ ] Playlist Sharing Platform

## Disclaimer

VibeEngine provides licensing information for educational purposes. Always consult legal professionals for commercial use decisions. Licensing accuracy cannot be guaranteed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
