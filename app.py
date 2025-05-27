"""
FastAPI web application for Music Playlist Generator
Provides REST API endpoints for playlist generation and licensing checks.
"""

from pydantic import BaseModel
from config.settings import Settings
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, Optional, List
from fastapi.middleware.cors import CORSMiddleware

from src.services.licensing_checker import LicensingChecker
from src.services.playlist_generator import PlaylistGenerator

app = FastAPI(
    title="Music Playlist Generator API",
    description="Generate music playlists based on audio features with business licensing checks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings
settings = Settings()

class PlaylistRequest(BaseModel):
    audio_features: Dict[str, float]
    length: int = 20
    provider: str = "spotify"
    check_licensing: bool = False
    genres: Optional[List[str]] = None

@app.get("/")
async def root():
    return {"message": "Music Playlist Generator API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": ["playlist_generator", "licensing_checker"]}

@app.post("/generate-playlist")
async def generate_playlist(request: PlaylistRequest):
    """Generate a playlist based on audio features and optional licensing checks."""
    try:
        async with PlaylistGenerator(settings) as playlist_generator:
            # Generate playlist
            playlist = await playlist_generator.generate_playlist(
                audio_features=request.audio_features,
                length=request.length,
                provider=request.provider,
                genre=request.genres[0] if request.genres else None
            )
            
            # Check licensing if requested
            if request.check_licensing:
                async with LicensingChecker(settings) as licensing_checker:
                    playlist = await licensing_checker.check_playlist_licensing(playlist)
            
            return playlist.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check-licensing")
async def check_track_licensing(track_info: Dict[str, str]):
    """Check licensing information for a specific track."""
    try:
        from src.models.track import Track
        from src.models.audio_features import AudioFeatures
        
        # Create a minimal track object for licensing check
        track = Track(
            id=track_info.get("id", "unknown"),
            name=track_info.get("name", ""),
            artists=[track_info.get("artist", "")],
            album="",
            duration_ms=0,
            audio_features=AudioFeatures(),
            provider="unknown"
        )
        
        async with LicensingChecker(settings) as licensing_checker:
            licensing_info = await licensing_checker.check_track_licensing(track)
            return licensing_info.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers")
async def get_supported_providers():
    """Get list of supported music providers."""
    return {
        "providers": [
            {"id": "spotify", "name": "Spotify", "features": ["audio_features", "search", "playlists"]},
            {"id": "apple_music", "name": "Apple Music", "features": ["search", "metadata"]},
        ]
    }

@app.get("/audio-features/schema")
async def get_audio_features_schema():
    """Get the schema for audio features parameters."""
    return {
        "energy": {"type": "float", "range": [0.0, 1.0], "description": "Musical intensity and power"},
        "valence": {"type": "float", "range": [0.0, 1.0], "description": "Musical positivity"},
        "danceability": {"type": "float", "range": [0.0, 1.0], "description": "Rhythm and beat strength"},
        "acousticness": {"type": "float", "range": [0.0, 1.0], "description": "Acoustic vs electronic"},
        "instrumentalness": {"type": "float", "range": [0.0, 1.0], "description": "Vocal vs instrumental"},
        "tempo": {"type": "float", "range": [50.0, 200.0], "description": "Beats per minute"},
        "loudness": {"type": "float", "range": [-60.0, 0.0], "description": "Overall loudness in dB"}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 