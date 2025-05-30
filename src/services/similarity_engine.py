"""
Similarity engine service for finding similar tracks and generating playlists.
Uses audio features from resolved seed tracks to find similar music.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.models.track import Track
from src.models.playlist import Playlist
from src.models.seed_track import ResolvedSeedTrack
from src.utils.similarity_calculator import SimilarityCalculator, AudioFeatureProfile
from src.utils.cache_manager import CacheManager
from src.api.spotify_client import SpotifyClient
from src.api.apple_music_client import AppleMusicClient
from src.api.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)

@dataclass
class DiversitySettings:
    """Settings for playlist diversity algorithms."""
    max_per_artist: int = 2
    feature_diversity_factor: float = 0.3
    era_distribution: Optional[Dict[str, float]] = None
    include_seeds: bool = False
    genre_strict: bool = False
    tempo_tolerance: float = 0.15
    popularity_bias: float = 0.1
    
    def __post_init__(self):
        if self.era_distribution is None:
            self.era_distribution = {
                "2020s": 0.3,
                "2010s": 0.3,
                "2000s": 0.2,
                "1990s": 0.1,
                "older": 0.1
            }

@dataclass
class SimilarityConfig:
    """Configuration for similarity search and playlist generation."""
    target_count_multiplier: int = 3  # Search for 3x target tracks for diversity
    min_similarity_threshold: float = 0.4
    preferred_similarity_threshold: float = 0.6
    search_timeout_seconds: int = 60
    max_concurrent_searches: int = 10
    feature_weights: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.feature_weights is None:
            self.feature_weights = {
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

class SimilarityEngine:
    """Engine for finding similar tracks and generating playlists."""
    
    def __init__(self,
                 spotify_client: Optional[SpotifyClient] = None,
                 apple_music_client: Optional[AppleMusicClient] = None,
                 youtube_client: Optional[YouTubeClient] = None,
                 cache_manager: Optional[CacheManager] = None):
        """Initialize the similarity engine."""
        self.providers = {}
        if spotify_client:
            self.providers["spotify"] = spotify_client
        if apple_music_client:
            self.providers["apple_music"] = apple_music_client
        if youtube_client:
            self.providers["youtube_music"] = youtube_client
        
        self.cache_manager = cache_manager
        self.similarity_calculator = SimilarityCalculator()
        self.config = SimilarityConfig()
        
        if not self.providers:
            raise ValueError("At least one music provider client must be provided")
    
    async def generate_playlist(self,
                              resolved_seed_tracks: List[ResolvedSeedTrack],
                              target_length: int,
                              diversity_settings: Optional[DiversitySettings] = None,
                              config: Optional[SimilarityConfig] = None) -> Playlist:
        """Generate a playlist based on resolved seed tracks."""
        if config:
            self.config = config
        if diversity_settings is None:
            diversity_settings = DiversitySettings()
        
        logger.info(f"Generating playlist from {len(resolved_seed_tracks)} seed tracks, target length: {target_length}")
        
        # Extract seed tracks
        seed_tracks = [rst.resolved_track for rst in resolved_seed_tracks]
        
        # Extract feature profile from seeds
        feature_profile = await self._extract_seed_features(seed_tracks)
        
        # Find similar tracks
        candidate_tracks = await self._find_similar_tracks(
            feature_profile,
            target_length * self.config.target_count_multiplier
        )
        
        # Apply diversity algorithms
        diverse_tracks = self._apply_diversity_algorithms(
            candidate_tracks, diversity_settings, target_length
        )
        
        # Select final tracks
        final_tracks = diverse_tracks[:target_length]
        
        # Optionally include seed tracks
        if diversity_settings.include_seeds:
            final_tracks = seed_tracks + final_tracks
            final_tracks = final_tracks[:target_length]
        
        # Create playlist
        playlist_name = self._generate_playlist_name(seed_tracks)
        playlist = Playlist(
            id=f"seed_playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=playlist_name,
            description=f"Generated from {len(seed_tracks)} seed tracks",
            tracks=final_tracks,
            created_at=datetime.now()
        )
        
        logger.info(f"Generated playlist '{playlist_name}' with {len(final_tracks)} tracks")
        return playlist
    
    async def _extract_seed_features(self, seed_tracks: List[Track]) -> AudioFeatureProfile:
        """Extract audio feature profile from seed tracks."""
        # Ensure all seed tracks have audio features
        tracks_with_features = []
        for track in seed_tracks:
            if not track.audio_features:
                # Try to get audio features from provider
                try:
                    audio_features = await self._get_audio_features(track)
                    if audio_features:
                        track.audio_features = audio_features
                        tracks_with_features.append(track)
                except Exception as e:
                    logger.warning(f"Failed to get audio features for {track.display_name}: {e}")
            else:
                tracks_with_features.append(track)
        
        if not tracks_with_features:
            raise ValueError("No seed tracks have audio features available")
        
        return self.similarity_calculator.extract_seed_features(tracks_with_features)
    
    async def _get_audio_features(self, track: Track) -> Optional[Any]:
        """Get audio features for a track from its provider."""
        try:
            if track.provider == "spotify" and "spotify" in self.providers:
                features_dict = await self.providers["spotify"].get_audio_features(track.id)
                if features_dict:
                    from src.models.audio_features import AudioFeatures
                    return AudioFeatures.from_dict(features_dict)
            # Add other providers as needed
        except Exception as e:
            logger.warning(f"Failed to get audio features for {track.id}: {e}")
        
        return None
    
    def _create_fallback_audio_features(self, track_name: str, artist_name: str, genre_hints: List[str] = None) -> Dict[str, Any]:
        """Create estimated audio features when Spotify features aren't available."""
        import hashlib
        
        # Use track info to create deterministic but varied features
        seed = f"{track_name.lower()}{artist_name.lower()}"
        hash_obj = hashlib.md5(seed.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Base features for lo-fi/chill style (since that's the common case)
        base_features = {
            "tempo": 70.0 + (hash_int % 50),  # 70-120 BPM
            "energy": 0.2 + (hash_int % 100) / 100 * 0.6,  # 0.2-0.8
            "valence": 0.3 + (hash_int % 100) / 100 * 0.4,  # 0.3-0.7 
            "danceability": 0.3 + (hash_int % 100) / 100 * 0.4,  # 0.3-0.7
            "acousticness": 0.4 + (hash_int % 100) / 100 * 0.4,  # 0.4-0.8
            "instrumentalness": 0.3 + (hash_int % 100) / 100 * 0.5,  # 0.3-0.8
            "liveness": 0.1 + (hash_int % 100) / 100 * 0.2,  # 0.1-0.3
            "speechiness": 0.03 + (hash_int % 100) / 100 * 0.1,  # 0.03-0.13
            "key": hash_int % 12,
            "mode": hash_int % 2,
            "loudness": -12.0 + (hash_int % 100) / 100 * 8,  # -12 to -4 dB
            "time_signature": 4
        }
        
        # Adjust based on genre hints or track name analysis
        if genre_hints:
            genres_lower = [g.lower() for g in genre_hints]
            
            if any(word in genres_lower for word in ['electronic', 'edm', 'dance', 'techno']):
                base_features['energy'] = max(0.6, base_features['energy'])
                base_features['danceability'] = max(0.7, base_features['danceability'])
                base_features['tempo'] = max(120, base_features['tempo'])
                
            elif any(word in genres_lower for word in ['jazz', 'blues']):
                base_features['acousticness'] = max(0.6, base_features['acousticness'])
                base_features['instrumentalness'] = max(0.5, base_features['instrumentalness'])
                
            elif any(word in genres_lower for word in ['rock', 'metal']):
                base_features['energy'] = max(0.7, base_features['energy'])
                base_features['loudness'] = max(-8, base_features['loudness'])
                
            elif any(word in genres_lower for word in ['classical', 'ambient']):
                base_features['acousticness'] = max(0.8, base_features['acousticness'])
                base_features['instrumentalness'] = max(0.7, base_features['instrumentalness'])
                base_features['energy'] = min(0.4, base_features['energy'])
        
        # Analyze track name for hints
        track_lower = track_name.lower()
        if any(word in track_lower for word in ['chill', 'relax', 'calm', 'peaceful', 'ambient']):
            base_features['energy'] = min(0.4, base_features['energy'])
            base_features['valence'] = min(0.6, base_features['valence'])
            
        elif any(word in track_lower for word in ['upbeat', 'energetic', 'party', 'dance']):
            base_features['energy'] = max(0.7, base_features['energy'])
            base_features['danceability'] = max(0.7, base_features['danceability'])
            base_features['valence'] = max(0.6, base_features['valence'])
        
        return base_features
    
    async def _find_similar_tracks(self, feature_profile: AudioFeatureProfile, 
                                 target_count: int) -> List[Track]:
        """Search for similar tracks across all providers."""
        logger.debug(f"Searching for {target_count} similar tracks")
        
        # Generate search queries based on features
        search_queries = self._generate_search_queries(feature_profile)
        
        # Search all providers in parallel
        all_candidates = []
        search_tasks = []
        
        for provider_name, client in self.providers.items():
            for query in search_queries[:3]:  # Limit to top 3 queries per provider
                task = self._search_provider_for_similar_tracks(
                    provider_name, client, query, target_count // len(search_queries)
                )
                search_tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*search_tasks, return_exceptions=True),
                timeout=self.config.search_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning("Search timeout while finding similar tracks")
            results = []
        
        # Collect all candidates
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Search task failed: {result}")
                continue
            if result:
                all_candidates.extend(result)
        
        # Remove duplicates
        unique_candidates = self._deduplicate_tracks(all_candidates)
        
        # Score and rank candidates
        scored_tracks = []
        for track in unique_candidates:
            if track.audio_features:
                similarity_score = self.similarity_calculator.calculate_feature_similarity(
                    track.audio_features, feature_profile, self.config.feature_weights
                )
                if similarity_score >= self.config.min_similarity_threshold:
                    track.similarity_score = similarity_score
                    scored_tracks.append(track)
        
        # Sort by similarity score
        scored_tracks.sort(key=lambda x: x.similarity_score, reverse=True)
        
        logger.debug(f"Found {len(scored_tracks)} similar tracks above threshold")
        return scored_tracks[:target_count]
    
    def _generate_search_queries(self, feature_profile: AudioFeatureProfile) -> List[str]:
        """Generate search queries based on audio features."""
        queries = []
        
        # Genre-based queries
        for genre in feature_profile.preferred_genres[:3]:  # Top 3 genres
            queries.append(f"genre:{genre}")
        
        # Mood-based queries
        avg_valence = (feature_profile.valence_range[0] + feature_profile.valence_range[1]) / 2
        avg_energy = (feature_profile.energy_range[0] + feature_profile.energy_range[1]) / 2
        
        if avg_valence > 0.7:
            queries.extend(["happy", "upbeat", "positive"])
        elif avg_valence < 0.3:
            queries.extend(["sad", "melancholy", "dark"])
        else:
            queries.extend(["chill", "mellow"])
        
        if avg_energy > 0.7:
            queries.extend(["energetic", "intense", "powerful"])
        elif avg_energy < 0.3:
            queries.extend(["calm", "peaceful", "ambient"])
        
        # Tempo-based queries
        avg_tempo = (feature_profile.tempo_range[0] + feature_profile.tempo_range[1]) / 2
        if avg_tempo > 140:
            queries.extend(["fast", "uptempo", "dance"])
        elif avg_tempo < 90:
            queries.extend(["slow", "ballad", "downtempo"])
        
        # Remove duplicates and limit
        unique_queries = list(dict.fromkeys(queries))
        return unique_queries[:10]  # Limit to 10 queries
    
    async def _search_provider_for_similar_tracks(self, provider_name: str, client: Any,
                                                query: str, limit: int) -> List[Track]:
        """Search a specific provider for similar tracks."""
        try:
            if provider_name == "spotify":
                results = await client.search_tracks(query, limit=limit)
            elif provider_name == "apple_music":
                results = await client.search_tracks(query, limit=limit)
            elif provider_name == "youtube_music":
                results = await client.search_tracks(query, limit=limit)
            else:
                return []
            
            # Convert to Track objects
            tracks = []
            for result in results:
                try:
                    if provider_name == "spotify":
                        track = Track.from_spotify_data(result)
                    elif provider_name == "apple_music":
                        track = Track.from_apple_music_data(result)
                    else:
                        # Generic conversion
                        track = Track(
                            id=result.get("id", ""),
                            name=result.get("name", ""),
                            artist=result.get("artist", ""),
                            artists=result.get("artists", []),
                            album=result.get("album", ""),
                            duration_ms=result.get("duration_ms", 0),
                            provider=provider_name
                        )
                    
                    # Get audio features if not present
                    if not track.audio_features:
                        audio_features = await self._get_audio_features(track)
                        if audio_features:
                            track.audio_features = audio_features
                        else:
                            # Use fallback audio features when Spotify features aren't available
                            fallback_features = self._create_fallback_audio_features(
                                track.name, 
                                track.artist, 
                                track.genres if hasattr(track, 'genres') else None
                            )
                            from src.models.audio_features import AudioFeatures
                            track.audio_features = AudioFeatures.from_dict(fallback_features)
                    
                    # Always include tracks (now that we have fallback features)
                    tracks.append(track)
                    
                except Exception as e:
                    logger.warning(f"Failed to process track result: {e}")
                    continue
            
            return tracks
            
        except Exception as e:
            logger.error(f"Search failed for {provider_name}: {e}")
            return []
    
    def _deduplicate_tracks(self, tracks: List[Track]) -> List[Track]:
        """Remove duplicate tracks based on name and artist similarity."""
        if not tracks:
            return []
        
        unique_tracks = []
        seen_combinations = set()
        
        for track in tracks:
            # Create a normalized key for deduplication
            from src.utils.track_matcher import TrackMatcher
            matcher = TrackMatcher()
            track_name = matcher.normalize_track_name(track.name)
            artist_name = matcher.normalize_artist_name(track.artist)
            key = f"{track_name}:{artist_name}"
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_tracks.append(track)
        
        return unique_tracks
    
    def _apply_diversity_algorithms(self, tracks: List[Track], 
                                  settings: DiversitySettings,
                                  target_length: int) -> List[Track]:
        """Apply diversity algorithms to track selection."""
        if not tracks:
            return []
        
        # Apply artist diversity
        diverse_tracks = self._apply_artist_diversity(tracks, settings.max_per_artist)
        
        # Apply feature diversity
        diverse_tracks = self._apply_feature_diversity(
            diverse_tracks, settings.feature_diversity_factor
        )
        
        # Apply temporal diversity
        diverse_tracks = self._apply_temporal_diversity(
            diverse_tracks, settings.era_distribution, target_length
        )
        
        return diverse_tracks
    
    def _apply_artist_diversity(self, tracks: List[Track], max_per_artist: int) -> List[Track]:
        """Limit tracks per artist to increase diversity."""
        artist_counts = {}
        diverse_tracks = []
        
        for track in tracks:
            artist_key = track.artist.lower()
            current_count = artist_counts.get(artist_key, 0)
            
            if current_count < max_per_artist:
                diverse_tracks.append(track)
                artist_counts[artist_key] = current_count + 1
        
        return diverse_tracks
    
    def _apply_feature_diversity(self, tracks: List[Track], 
                                diversity_factor: float) -> List[Track]:
        """Apply diversity penalty to avoid feature clustering."""
        if diversity_factor <= 0 or not tracks:
            return tracks
        
        selected_tracks = []
        remaining_tracks = tracks.copy()
        
        # Always include the most similar track
        if remaining_tracks:
            selected_tracks.append(remaining_tracks.pop(0))
        
        while remaining_tracks and len(selected_tracks) < len(tracks):
            best_track = None
            best_score = -1
            
            for track in remaining_tracks:
                # Get base similarity score
                base_score = getattr(track, 'similarity_score', 0.5)
                
                # Calculate similarity to already selected tracks
                avg_similarity = self.similarity_calculator.calculate_average_similarity(
                    track, selected_tracks
                )
                
                # Apply diversity penalty
                diversity_penalty = avg_similarity * diversity_factor
                adjusted_score = base_score - diversity_penalty
                
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_track = track
            
            if best_track:
                selected_tracks.append(best_track)
                remaining_tracks.remove(best_track)
            else:
                break
        
        return selected_tracks
    
    def _apply_temporal_diversity(self, tracks: List[Track], 
                                era_distribution: Dict[str, float],
                                target_length: int) -> List[Track]:
        """Ensure diverse representation across time periods."""
        if not tracks or not era_distribution:
            return tracks
        
        # Group tracks by era
        era_tracks = {}
        for track in tracks:
            era = self._get_track_era(track.release_date)
            if era not in era_tracks:
                era_tracks[era] = []
            era_tracks[era].append(track)
        
        # Select tracks according to distribution
        diverse_tracks = []
        
        for era, ratio in era_distribution.items():
            target_count = int(target_length * ratio)
            if era in era_tracks:
                era_selection = era_tracks[era][:target_count]
                diverse_tracks.extend(era_selection)
        
        # Fill remaining slots with best tracks
        remaining_slots = target_length - len(diverse_tracks)
        if remaining_slots > 0:
            used_tracks = set(track.id for track in diverse_tracks)
            remaining_tracks = [t for t in tracks if t.id not in used_tracks]
            diverse_tracks.extend(remaining_tracks[:remaining_slots])
        
        return diverse_tracks
    
    def _get_track_era(self, release_date: Optional[str]) -> str:
        """Determine the era of a track based on release date."""
        if not release_date:
            return "unknown"
        
        try:
            year = int(release_date[:4])
            if year >= 2020:
                return "2020s"
            elif year >= 2010:
                return "2010s"
            elif year >= 2000:
                return "2000s"
            elif year >= 1990:
                return "1990s"
            else:
                return "older"
        except (ValueError, TypeError):
            return "unknown"
    
    def _generate_playlist_name(self, seed_tracks: List[Track]) -> str:
        """Generate a descriptive name for the playlist."""
        if not seed_tracks:
            return "Generated Playlist"
        
        if len(seed_tracks) == 1:
            return f"Similar to {seed_tracks[0].name}"
        elif len(seed_tracks) <= 3:
            track_names = [track.name for track in seed_tracks]
            return f"Similar to {', '.join(track_names)}"
        else:
            artists = list(set(track.artist for track in seed_tracks))
            if len(artists) <= 3:
                return f"Similar to {', '.join(artists)}"
            else:
                return f"Generated from {len(seed_tracks)} tracks"
    
    def _feature_profile_to_dict(self, profile: AudioFeatureProfile) -> Dict[str, Any]:
        """Convert feature profile to dictionary for serialization."""
        return {
            "tempo_range": profile.tempo_range,
            "energy_range": profile.energy_range,
            "valence_range": profile.valence_range,
            "danceability_range": profile.danceability_range,
            "acousticness_range": profile.acousticness_range,
            "instrumentalness_range": profile.instrumentalness_range,
            "liveness_range": profile.liveness_range,
            "speechiness_range": profile.speechiness_range,
            "preferred_keys": profile.preferred_keys,
            "preferred_modes": profile.preferred_modes,
            "preferred_genres": profile.preferred_genres,
            "average_features": profile.average_features.to_dict() if profile.average_features else None,
            "feature_variance": profile.feature_variance
        } 