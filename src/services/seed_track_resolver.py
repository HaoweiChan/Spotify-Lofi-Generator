"""
Seed track resolver service for resolving user-provided track information.
Handles incomplete or inaccurate track names and artist names through fuzzy matching.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from src.models.seed_track import SeedTrack, ResolvedSeedTrack
from src.models.track import Track
from src.utils.track_matcher import TrackMatcher, MatchResult
from src.utils.cache_manager import CacheManager
from src.api.spotify_client import SpotifyClient
from src.api.apple_music_client import AppleMusicClient
from src.api.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)

@dataclass
class ResolutionConfig:
    """Configuration for track resolution process."""
    confidence_threshold: float = 0.7
    max_search_results: int = 50
    fuzzy_threshold: float = 0.6
    enable_phonetic: bool = True
    search_timeout_seconds: int = 30
    max_concurrent_searches: int = 5
    provider_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.provider_weights is None:
            self.provider_weights = {
                "spotify": 1.0,
                "apple_music": 0.9,
                "youtube_music": 0.7
            }

class SeedTrackResolver:
    """Service for resolving seed tracks to actual track data."""
    
    def __init__(self, 
                 spotify_client: Optional[SpotifyClient] = None,
                 apple_music_client: Optional[AppleMusicClient] = None,
                 youtube_client: Optional[YouTubeClient] = None,
                 cache_manager: Optional[CacheManager] = None):
        """Initialize the seed track resolver."""
        self.providers = {}
        if spotify_client:
            self.providers["spotify"] = spotify_client
        if apple_music_client:
            self.providers["apple_music"] = apple_music_client
        if youtube_client:
            self.providers["youtube_music"] = youtube_client
        
        self.cache_manager = cache_manager
        self.track_matcher = TrackMatcher()
        self.config = ResolutionConfig()
        
        if not self.providers:
            raise ValueError("At least one music provider client must be provided")
    
    async def resolve_seed_tracks(self, 
                                seed_tracks: List[SeedTrack],
                                config: Optional[ResolutionConfig] = None) -> List[ResolvedSeedTrack]:
        """Resolve a list of seed tracks to actual track data."""
        if config:
            self.config = config
        
        logger.info(f"Starting resolution of {len(seed_tracks)} seed tracks")
        
        # Process tracks in batches to respect rate limits
        batch_size = self.config.max_concurrent_searches
        resolved_tracks = []
        
        for i in range(0, len(seed_tracks), batch_size):
            batch = seed_tracks[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._resolve_single_track(seed_track) for seed_track in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error resolving track: {result}")
                    continue
                if result:
                    resolved_tracks.append(result)
        
        logger.info(f"Successfully resolved {len(resolved_tracks)} out of {len(seed_tracks)} tracks")
        return resolved_tracks
    
    async def _resolve_single_track(self, seed_track: SeedTrack) -> Optional[ResolvedSeedTrack]:
        """Resolve a single seed track through multi-stage search."""
        logger.debug(f"Resolving track: {seed_track.display_name}")
        
        # Check cache first
        if self.cache_manager:
            cache_key = f"resolved_track:{seed_track.track_name}:{seed_track.artist_name}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Found cached resolution for {seed_track.display_name}")
                return ResolvedSeedTrack.from_dict(cached_result)
        
        # Stage 1: Exact match
        result = await self._exact_search(seed_track)
        if result and result.confidence_score >= seed_track.confidence_threshold:
            await self._cache_result(seed_track, result)
            return result
        
        # Stage 2: Normalized search
        result = await self._normalized_search(seed_track)
        if result and result.confidence_score >= seed_track.confidence_threshold:
            await self._cache_result(seed_track, result)
            return result
        
        # Stage 3: Partial match
        result = await self._partial_search(seed_track)
        if result and result.confidence_score >= seed_track.confidence_threshold:
            await self._cache_result(seed_track, result)
            return result
        
        # Stage 4: Fuzzy search
        result = await self._fuzzy_search(seed_track)
        if result:
            await self._cache_result(seed_track, result)
            return result
        
        logger.warning(f"Could not resolve track: {seed_track.display_name}")
        return None
    
    async def _exact_search(self, seed_track: SeedTrack) -> Optional[ResolvedSeedTrack]:
        """Stage 1: Search with original, unmodified input."""
        query = seed_track.search_query
        candidates = await self._search_all_providers(query, limit=10)
        
        return await self._find_best_match(
            seed_track, candidates, "exact_match", min_similarity=0.95
        )
    
    async def _normalized_search(self, seed_track: SeedTrack) -> Optional[ResolvedSeedTrack]:
        """Stage 2: Search with normalized strings."""
        norm_track = self.track_matcher.normalize_track_name(seed_track.track_name)
        norm_artist = self.track_matcher.normalize_artist_name(seed_track.artist_name)
        
        if not norm_track or not norm_artist:
            return None
        
        query = f"{norm_track} {norm_artist}"
        candidates = await self._search_all_providers(query, limit=20)
        
        return await self._find_best_match(
            seed_track, candidates, "normalized_search", min_similarity=0.8
        )
    
    async def _partial_search(self, seed_track: SeedTrack) -> Optional[ResolvedSeedTrack]:
        """Stage 3: Search with partial strings and variations."""
        variations = self.track_matcher.generate_search_variations(
            seed_track.track_name, seed_track.artist_name
        )
        
        all_candidates = []
        for variation in variations[:5]:  # Limit to top 5 variations
            candidates = await self._search_all_providers(variation, limit=15)
            all_candidates.extend(candidates)
        
        # Remove duplicates
        unique_candidates = self._deduplicate_tracks(all_candidates)
        
        return await self._find_best_match(
            seed_track, unique_candidates, "partial_search", min_similarity=0.7
        )
    
    async def _fuzzy_search(self, seed_track: SeedTrack) -> Optional[ResolvedSeedTrack]:
        """Stage 4: Broad search with similarity filtering."""
        # Search with individual terms
        track_candidates = await self._search_all_providers(seed_track.track_name, limit=25)
        artist_candidates = await self._search_all_providers(seed_track.artist_name, limit=25)
        
        all_candidates = track_candidates + artist_candidates
        unique_candidates = self._deduplicate_tracks(all_candidates)
        
        # Filter by similarity threshold
        filtered_candidates = self.track_matcher.filter_by_similarity(
            unique_candidates,
            seed_track.track_name,
            seed_track.artist_name,
            min_similarity=self.config.fuzzy_threshold
        )
        
        # Convert to track objects and find best match
        candidate_tracks = []
        for candidate_dict, similarity_score in filtered_candidates:
            try:
                track = self._dict_to_track(candidate_dict)
                candidate_tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to convert candidate to track: {e}")
                continue
        
        return await self._find_best_match(
            seed_track, candidate_tracks, "fuzzy_search", min_similarity=0.4
        )
    
    async def _search_all_providers(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search all available providers in parallel."""
        search_tasks = []
        
        for provider_name, client in self.providers.items():
            task = self._search_provider(provider_name, client, query, limit)
            search_tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*search_tasks, return_exceptions=True),
                timeout=self.config.search_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Search timeout for query: {query}")
            return []
        
        all_tracks = []
        for provider_name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Search failed for {provider_name}: {result}")
                continue
            
            # Apply provider weight
            weight = self.config.provider_weights.get(provider_name, 1.0)
            for track in result:
                track["provider_weight"] = weight
                all_tracks.append(track)
        
        return all_tracks
    
    async def _search_provider(self, provider_name: str, client: Any, 
                             query: str, limit: int) -> List[Dict[str, Any]]:
        """Search a specific provider."""
        try:
            if provider_name == "spotify":
                results = await client.search_tracks(query, limit=limit)
            elif provider_name == "apple_music":
                results = await client.search_tracks(query, limit=limit)
            elif provider_name == "youtube_music":
                results = await client.search_tracks(query, limit=limit)
            else:
                logger.warning(f"Unknown provider: {provider_name}")
                return []
            
            # Add provider info to each result
            for result in results:
                result["provider"] = provider_name
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed for {provider_name}: {e}")
            return []
    
    async def _find_best_match(self, seed_track: SeedTrack, candidates: List[Any],
                             method: str, min_similarity: float = 0.6) -> Optional[ResolvedSeedTrack]:
        """Find the best matching track from candidates."""
        if not candidates:
            return None
        
        best_match = None
        best_score = 0.0
        alternative_matches = []
        
        for candidate in candidates:
            # Convert to track if it's a dict
            if isinstance(candidate, dict):
                try:
                    track = self._dict_to_track(candidate)
                except Exception as e:
                    logger.warning(f"Failed to convert candidate to track: {e}")
                    continue
            else:
                track = candidate
            
            # Calculate similarity
            match_result = self.track_matcher.calculate_similarity(
                seed_track.track_name, seed_track.artist_name,
                track.name, track.artist
            )
            
            # Apply provider weight if available
            provider_weight = getattr(candidate, 'provider_weight', 1.0) if hasattr(candidate, 'provider_weight') else 1.0
            if isinstance(candidate, dict):
                provider_weight = candidate.get('provider_weight', 1.0)
            
            adjusted_score = min(1.0, match_result.similarity_score * provider_weight)  # Clamp to 1.0
            
            if adjusted_score >= min_similarity:
                if adjusted_score > best_score:
                    if best_match:
                        alternative_matches.append(best_match)
                    best_match = track
                    best_score = adjusted_score
                else:
                    alternative_matches.append(track)
        
        if best_match:
            return ResolvedSeedTrack(
                seed_track=seed_track,
                resolved_track=best_match,
                confidence_score=best_score,
                resolution_method=method,
                alternative_matches=alternative_matches[:5]  # Limit alternatives
            )
        
        return None
    
    def _dict_to_track(self, track_dict: Dict[str, Any]) -> Track:
        """Convert a track dictionary to a Track object."""
        provider = track_dict.get("provider", "unknown")
        
        if provider == "spotify":
            return Track.from_spotify_data(track_dict)
        elif provider == "apple_music":
            return Track.from_apple_music_data(track_dict)
        else:
            # Generic conversion
            return Track(
                id=track_dict.get("id", ""),
                name=track_dict.get("name", ""),
                artist=track_dict.get("artist", ""),
                artists=track_dict.get("artists", []),
                album=track_dict.get("album", ""),
                duration_ms=track_dict.get("duration_ms", 0),
                popularity=track_dict.get("popularity"),
                explicit=track_dict.get("explicit", False),
                preview_url=track_dict.get("preview_url"),
                external_urls=track_dict.get("external_urls", {}),
                genres=track_dict.get("genres", []),
                release_date=track_dict.get("release_date"),
                provider=provider
            )
    
    def _deduplicate_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tracks based on name and artist similarity."""
        if not tracks:
            return []
        
        unique_tracks = []
        seen_combinations = set()
        
        for track in tracks:
            # Create a normalized key for deduplication
            track_name = self.track_matcher.normalize_track_name(track.get("name", ""))
            
            # Handle different artist field formats
            artist_name = ""
            if "artist" in track:
                artist_name = track["artist"]
            elif "artists" in track and track["artists"]:
                if isinstance(track["artists"][0], dict):
                    # Spotify format: [{"name": "Artist"}]
                    artist_name = track["artists"][0].get("name", "")
                else:
                    # Simple format: ["Artist"]
                    artist_name = track["artists"][0]
            
            artist_name = self.track_matcher.normalize_artist_name(artist_name)
            key = f"{track_name}:{artist_name}"
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_tracks.append(track)
        
        return unique_tracks
    
    async def _cache_result(self, seed_track: SeedTrack, result: ResolvedSeedTrack):
        """Cache the resolution result."""
        if self.cache_manager:
            cache_key = f"resolved_track:{seed_track.track_name}:{seed_track.artist_name}"
            await self.cache_manager.set(cache_key, result.to_dict(), ttl=86400)  # 24 hours
    
    def get_resolution_stats(self, resolved_tracks: List[ResolvedSeedTrack]) -> Dict[str, Any]:
        """Get statistics about the resolution process."""
        if not resolved_tracks:
            return {
                "total": 0, 
                "success_rate": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "average_confidence": 0.0,
                "methods": {},
                "providers": {}
            }
        
        total = len(resolved_tracks)
        high_confidence = sum(1 for t in resolved_tracks if t.is_high_confidence)
        medium_confidence = sum(1 for t in resolved_tracks if t.is_medium_confidence)
        low_confidence = sum(1 for t in resolved_tracks if t.is_low_confidence)
        
        methods = {}
        providers = {}
        
        for track in resolved_tracks:
            # Count resolution methods
            method = track.resolution_method
            methods[method] = methods.get(method, 0) + 1
            
            # Count providers
            provider = track.resolved_track.provider
            providers[provider] = providers.get(provider, 0) + 1
        
        avg_confidence = sum(t.confidence_score for t in resolved_tracks) / total
        
        return {
            "total": total,
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence,
            "average_confidence": avg_confidence,
            "success_rate": total / total if total > 0 else 0.0,
            "methods": methods,
            "providers": providers
        } 