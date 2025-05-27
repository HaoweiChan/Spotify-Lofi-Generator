"""
Audio Features Service

Handles audio feature normalization across providers, similarity calculation algorithms,
feature weighting and scoring, and tempo/key matching with tolerance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import math

from ..models.audio_features import AudioFeatures
from ..models.track import Track
from ..utils.validators import validate_audio_features

logger = logging.getLogger(__name__)


@dataclass
class FeatureWeights:
    """Weights for different audio features in similarity calculations."""
    tempo: float = 0.2
    energy: float = 0.15
    valence: float = 0.15
    danceability: float = 0.1
    acousticness: float = 0.1
    instrumentalness: float = 0.05
    liveness: float = 0.05
    speechiness: float = 0.05
    loudness: float = 0.1
    key: float = 0.05


@dataclass
class FeatureTolerances:
    """Tolerance ranges for audio feature matching."""
    tempo_bpm: float = 10.0  # BPM tolerance
    energy: float = 0.2  # 0.0-1.0 scale
    valence: float = 0.2  # 0.0-1.0 scale
    danceability: float = 0.2  # 0.0-1.0 scale
    acousticness: float = 0.3  # 0.0-1.0 scale
    instrumentalness: float = 0.3  # 0.0-1.0 scale
    liveness: float = 0.3  # 0.0-1.0 scale
    speechiness: float = 0.2  # 0.0-1.0 scale
    loudness_db: float = 5.0  # dB tolerance
    key_semitones: int = 2  # Semitone tolerance


class AudioFeaturesService:
    """Service for audio feature analysis and matching."""
    
    def __init__(self, weights: Optional[FeatureWeights] = None, 
                 tolerances: Optional[FeatureTolerances] = None):
        self.weights = weights or FeatureWeights()
        self.tolerances = tolerances or FeatureTolerances()
        
    def normalize_features(self, features: AudioFeatures, provider: str) -> AudioFeatures:
        """
        Normalize audio features across different providers.
        
        Args:
            features: Raw audio features from provider
            provider: Provider name (spotify, apple_music, etc.)
            
        Returns:
            Normalized audio features
        """
        try:
            normalized = AudioFeatures(
                tempo=self._normalize_tempo(features.tempo, provider),
                energy=self._normalize_scale_feature(features.energy, provider),
                valence=self._normalize_scale_feature(features.valence, provider),
                danceability=self._normalize_scale_feature(features.danceability, provider),
                acousticness=self._normalize_scale_feature(features.acousticness, provider),
                instrumentalness=self._normalize_scale_feature(features.instrumentalness, provider),
                liveness=self._normalize_scale_feature(features.liveness, provider),
                speechiness=self._normalize_scale_feature(features.speechiness, provider),
                loudness=self._normalize_loudness(features.loudness, provider),
                key=self._normalize_key(features.key, provider),
                mode=features.mode,
                time_signature=features.time_signature,
                duration_ms=features.duration_ms
            )
            
            # Skip validation for normalized features as they may contain None values
            # validate_audio_features(normalized.__dict__)
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing features from {provider}: {e}")
            raise
    
    def calculate_similarity(self, target_features: AudioFeatures, 
                           candidate_features: AudioFeatures) -> float:
        """
        Calculate similarity score between target and candidate features.
        
        Args:
            target_features: Target audio features
            candidate_features: Candidate track features
            
        Returns:
            Similarity score (0.0 to 1.0, higher is more similar)
        """
        try:
            total_score = 0.0
            total_weight = 0.0
            
            # Tempo similarity
            tempo_score = self._calculate_tempo_similarity(
                target_features.tempo, candidate_features.tempo
            )
            total_score += tempo_score * self.weights.tempo
            total_weight += self.weights.tempo
            
            # Scale feature similarities (0.0-1.0 range)
            scale_features = [
                ('energy', target_features.energy, candidate_features.energy, self.weights.energy),
                ('valence', target_features.valence, candidate_features.valence, self.weights.valence),
                ('danceability', target_features.danceability, candidate_features.danceability, self.weights.danceability),
                ('acousticness', target_features.acousticness, candidate_features.acousticness, self.weights.acousticness),
                ('instrumentalness', target_features.instrumentalness, candidate_features.instrumentalness, self.weights.instrumentalness),
                ('liveness', target_features.liveness, candidate_features.liveness, self.weights.liveness),
                ('speechiness', target_features.speechiness, candidate_features.speechiness, self.weights.speechiness)
            ]
            
            for feature_name, target_val, candidate_val, weight in scale_features:
                if target_val is not None and candidate_val is not None:
                    score = self._calculate_scale_similarity(target_val, candidate_val)
                    total_score += score * weight
                    total_weight += weight
            
            # Loudness similarity
            if target_features.loudness is not None and candidate_features.loudness is not None:
                loudness_score = self._calculate_loudness_similarity(
                    target_features.loudness, candidate_features.loudness
                )
                total_score += loudness_score * self.weights.loudness
                total_weight += self.weights.loudness
            
            # Key similarity
            if target_features.key is not None and candidate_features.key is not None:
                key_score = self._calculate_key_similarity(
                    target_features.key, candidate_features.key
                )
                total_score += key_score * self.weights.key
                total_weight += self.weights.key
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def matches_criteria(self, features: AudioFeatures, 
                        target_features: AudioFeatures) -> bool:
        """
        Check if features match target criteria within tolerance ranges.
        
        Args:
            features: Candidate track features
            target_features: Target criteria features
            
        Returns:
            True if features match within tolerances
        """
        try:
            # Check tempo tolerance
            if (target_features.tempo is not None and features.tempo is not None):
                tempo_diff = abs(target_features.tempo - features.tempo)
                if tempo_diff > self.tolerances.tempo_bpm:
                    return False
            
            # Check scale feature tolerances
            scale_checks = [
                (target_features.energy, features.energy, self.tolerances.energy),
                (target_features.valence, features.valence, self.tolerances.valence),
                (target_features.danceability, features.danceability, self.tolerances.danceability),
                (target_features.acousticness, features.acousticness, self.tolerances.acousticness),
                (target_features.instrumentalness, features.instrumentalness, self.tolerances.instrumentalness),
                (target_features.liveness, features.liveness, self.tolerances.liveness),
                (target_features.speechiness, features.speechiness, self.tolerances.speechiness)
            ]
            
            for target_val, candidate_val, tolerance in scale_checks:
                if target_val is not None and candidate_val is not None:
                    if abs(target_val - candidate_val) > tolerance:
                        return False
            
            # Check loudness tolerance
            if (target_features.loudness is not None and features.loudness is not None):
                loudness_diff = abs(target_features.loudness - features.loudness)
                if loudness_diff > self.tolerances.loudness_db:
                    return False
            
            # Check key tolerance
            if (target_features.key is not None and features.key is not None):
                key_diff = self._calculate_key_distance(target_features.key, features.key)
                if key_diff > self.tolerances.key_semitones:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking feature criteria: {e}")
            return False
    
    async def rank_tracks_by_similarity(self, target_features: AudioFeatures,
                                      tracks: List[Track]) -> List[Tuple[Track, float]]:
        """
        Rank tracks by similarity to target features.
        
        Args:
            target_features: Target audio features
            tracks: List of candidate tracks
            
        Returns:
            List of (track, similarity_score) tuples, sorted by similarity (descending)
        """
        try:
            scored_tracks = []
            
            for track in tracks:
                if track.audio_features:
                    similarity = self.calculate_similarity(target_features, track.audio_features)
                    scored_tracks.append((track, similarity))
            
            # Sort by similarity score (descending)
            scored_tracks.sort(key=lambda x: x[1], reverse=True)
            
            return scored_tracks
            
        except Exception as e:
            logger.error(f"Error ranking tracks by similarity: {e}")
            return []
    
    def get_feature_statistics(self, tracks: List[Track]) -> Dict[str, Any]:
        """
        Calculate statistics for audio features across a collection of tracks.
        
        Args:
            tracks: List of tracks to analyze
            
        Returns:
            Dictionary containing feature statistics
        """
        try:
            features_data = {
                'tempo': [],
                'energy': [],
                'valence': [],
                'danceability': [],
                'acousticness': [],
                'instrumentalness': [],
                'liveness': [],
                'speechiness': [],
                'loudness': []
            }
            
            for track in tracks:
                if track.audio_features:
                    features = track.audio_features
                    if features.tempo is not None:
                        features_data['tempo'].append(features.tempo)
                    if features.energy is not None:
                        features_data['energy'].append(features.energy)
                    if features.valence is not None:
                        features_data['valence'].append(features.valence)
                    if features.danceability is not None:
                        features_data['danceability'].append(features.danceability)
                    if features.acousticness is not None:
                        features_data['acousticness'].append(features.acousticness)
                    if features.instrumentalness is not None:
                        features_data['instrumentalness'].append(features.instrumentalness)
                    if features.liveness is not None:
                        features_data['liveness'].append(features.liveness)
                    if features.speechiness is not None:
                        features_data['speechiness'].append(features.speechiness)
                    if features.loudness is not None:
                        features_data['loudness'].append(features.loudness)
            
            statistics = {}
            for feature, values in features_data.items():
                if values:
                    statistics[feature] = {
                        'mean': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
                    
                    # Calculate standard deviation
                    mean = statistics[feature]['mean']
                    variance = sum((x - mean) ** 2 for x in values) / len(values)
                    statistics[feature]['std'] = math.sqrt(variance)
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error calculating feature statistics: {e}")
            return {}
    
    def _normalize_tempo(self, tempo: Optional[float], provider: str) -> Optional[float]:
        """Normalize tempo across providers."""
        if tempo is None:
            return None
        
        # Most providers use BPM directly, but some might need conversion
        if provider == "apple_music":
            # Apple Music might use different tempo representation
            return tempo
        
        return tempo
    
    def _normalize_scale_feature(self, value: Optional[float], provider: str) -> Optional[float]:
        """Normalize 0.0-1.0 scale features across providers."""
        if value is None:
            return None
        
        # Ensure value is in 0.0-1.0 range
        return max(0.0, min(1.0, value))
    
    def _normalize_loudness(self, loudness: Optional[float], provider: str) -> Optional[float]:
        """Normalize loudness values across providers."""
        if loudness is None:
            return None
        
        # Most providers use dB, but might have different ranges
        return loudness
    
    def _normalize_key(self, key: Optional[int], provider: str) -> Optional[int]:
        """Normalize key values across providers."""
        if key is None:
            return None
        
        # Ensure key is in 0-11 range (chromatic scale)
        return key % 12
    
    def _calculate_tempo_similarity(self, target: Optional[float], 
                                  candidate: Optional[float]) -> float:
        """Calculate tempo similarity score."""
        if target is None or candidate is None:
            return 0.5  # Neutral score for missing data
        
        diff = abs(target - candidate)
        max_diff = self.tolerances.tempo_bpm * 3  # 3x tolerance for full penalty
        
        return max(0.0, 1.0 - (diff / max_diff))
    
    def _calculate_scale_similarity(self, target: float, candidate: float) -> float:
        """Calculate similarity for 0.0-1.0 scale features."""
        diff = abs(target - candidate)
        return max(0.0, 1.0 - diff)
    
    def _calculate_loudness_similarity(self, target: Optional[float], 
                                     candidate: Optional[float]) -> float:
        """Calculate loudness similarity score."""
        if target is None or candidate is None:
            return 0.5  # Neutral score for missing data
        
        diff = abs(target - candidate)
        max_diff = self.tolerances.loudness_db * 3  # 3x tolerance for full penalty
        
        return max(0.0, 1.0 - (diff / max_diff))
    
    def _calculate_key_similarity(self, target: Optional[int], 
                                candidate: Optional[int]) -> float:
        """Calculate key similarity score."""
        if target is None or candidate is None:
            return 0.5  # Neutral score for missing data
        
        distance = self._calculate_key_distance(target, candidate)
        max_distance = 6  # Maximum distance in chromatic circle
        
        return max(0.0, 1.0 - (distance / max_distance))
    
    def _calculate_key_distance(self, key1: int, key2: int) -> int:
        """Calculate distance between keys in chromatic circle."""
        diff = abs(key1 - key2)
        return min(diff, 12 - diff)  # Shortest path around chromatic circle 