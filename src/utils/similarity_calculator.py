"""
Similarity calculator for audio features and track comparison.
Provides weighted similarity calculations and diversity algorithms.
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.models.audio_features import AudioFeatures
from src.models.track import Track

@dataclass
class AudioFeatureProfile:
    """Representative audio features derived from seed tracks."""
    tempo_range: Tuple[float, float]          # BPM range (min, max)
    energy_range: Tuple[float, float]         # Energy level range
    valence_range: Tuple[float, float]        # Musical positivity range
    danceability_range: Tuple[float, float]   # Danceability range
    acousticness_range: Tuple[float, float]   # Acoustic vs electric
    instrumentalness_range: Tuple[float, float] # Instrumental content
    liveness_range: Tuple[float, float]       # Live performance detection
    speechiness_range: Tuple[float, float]    # Spoken word content
    
    # Categorical features
    preferred_keys: List[int]                 # Musical keys
    preferred_modes: List[int]                # Major/minor modes
    preferred_genres: List[str]               # Genre preferences
    
    # Derived metrics
    average_features: AudioFeatures           # Mean values
    feature_variance: Dict[str, float]        # Variance for each feature

class SimilarityCalculator:
    """Calculate similarity scores between tracks and audio features."""
    
    def __init__(self):
        """Initialize with default feature weights."""
        self.default_weights = {
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
        
        self.numerical_features = [
            "tempo", "energy", "valence", "danceability", 
            "acousticness", "instrumentalness", "liveness", "speechiness"
        ]
        
        self.categorical_features = ["key", "mode"]
    
    def extract_seed_features(self, tracks: List[Track]) -> AudioFeatureProfile:
        """Extract representative audio features from seed tracks."""
        if not tracks:
            raise ValueError("No tracks provided for feature extraction")
        
        # Collect audio features
        features_list = []
        for track in tracks:
            if track.audio_features:
                features_list.append(track.audio_features)
        
        if not features_list:
            raise ValueError("No audio features available for seed tracks")
        
        # Calculate ranges for numerical features
        tempo_values = [f.tempo for f in features_list if f.tempo is not None]
        energy_values = [f.energy for f in features_list if f.energy is not None]
        valence_values = [f.valence for f in features_list if f.valence is not None]
        danceability_values = [f.danceability for f in features_list if f.danceability is not None]
        acousticness_values = [f.acousticness for f in features_list if f.acousticness is not None]
        instrumentalness_values = [f.instrumentalness for f in features_list if f.instrumentalness is not None]
        liveness_values = [f.liveness for f in features_list if f.liveness is not None]
        speechiness_values = [f.speechiness for f in features_list if f.speechiness is not None]
        
        # Calculate ranges with some tolerance
        tempo_range = self._calculate_range(tempo_values, tolerance=0.15)
        energy_range = self._calculate_range(energy_values, tolerance=0.2)
        valence_range = self._calculate_range(valence_values, tolerance=0.2)
        danceability_range = self._calculate_range(danceability_values, tolerance=0.2)
        acousticness_range = self._calculate_range(acousticness_values, tolerance=0.25)
        instrumentalness_range = self._calculate_range(instrumentalness_values, tolerance=0.3)
        liveness_range = self._calculate_range(liveness_values, tolerance=0.3)
        speechiness_range = self._calculate_range(speechiness_values, tolerance=0.3)
        
        # Collect categorical features
        keys = [f.key for f in features_list if f.key is not None]
        modes = [f.mode for f in features_list if f.mode is not None]
        
        preferred_keys = list(set(keys)) if keys else []
        preferred_modes = list(set(modes)) if modes else []
        
        # Collect genres from tracks
        genres = []
        for track in tracks:
            if track.genres:
                genres.extend(track.genres)
        preferred_genres = list(set(genres))
        
        # Calculate average features
        average_features = self._calculate_average_features(features_list)
        
        # Calculate feature variance
        feature_variance = self._calculate_feature_variance(features_list)
        
        return AudioFeatureProfile(
            tempo_range=tempo_range,
            energy_range=energy_range,
            valence_range=valence_range,
            danceability_range=danceability_range,
            acousticness_range=acousticness_range,
            instrumentalness_range=instrumentalness_range,
            liveness_range=liveness_range,
            speechiness_range=speechiness_range,
            preferred_keys=preferred_keys,
            preferred_modes=preferred_modes,
            preferred_genres=preferred_genres,
            average_features=average_features,
            feature_variance=feature_variance
        )
    
    def _calculate_range(self, values: List[float], tolerance: float = 0.2) -> Tuple[float, float]:
        """Calculate range with tolerance for a list of values."""
        if not values:
            return (0.0, 1.0)  # Default range
        
        min_val = min(values)
        max_val = max(values)
        
        # Add tolerance
        range_size = max_val - min_val
        if range_size == 0:
            # All values are the same, add some tolerance
            tolerance_amount = tolerance
        else:
            tolerance_amount = range_size * tolerance
        
        # Expand range
        expanded_min = max(0.0, min_val - tolerance_amount)
        expanded_max = min(1.0, max_val + tolerance_amount)
        
        # Special handling for tempo (different scale)
        if values and values[0] > 10:  # Likely tempo values
            expanded_min = max(50.0, min_val - tolerance_amount * 100)
            expanded_max = min(200.0, max_val + tolerance_amount * 100)
        
        return (expanded_min, expanded_max)
    
    def _calculate_average_features(self, features_list: List[AudioFeatures]) -> AudioFeatures:
        """Calculate average audio features."""
        if not features_list:
            return AudioFeatures()
        
        # Calculate averages for each feature
        tempo_sum = sum(f.tempo for f in features_list if f.tempo is not None)
        tempo_count = sum(1 for f in features_list if f.tempo is not None)
        
        energy_sum = sum(f.energy for f in features_list if f.energy is not None)
        energy_count = sum(1 for f in features_list if f.energy is not None)
        
        valence_sum = sum(f.valence for f in features_list if f.valence is not None)
        valence_count = sum(1 for f in features_list if f.valence is not None)
        
        danceability_sum = sum(f.danceability for f in features_list if f.danceability is not None)
        danceability_count = sum(1 for f in features_list if f.danceability is not None)
        
        acousticness_sum = sum(f.acousticness for f in features_list if f.acousticness is not None)
        acousticness_count = sum(1 for f in features_list if f.acousticness is not None)
        
        instrumentalness_sum = sum(f.instrumentalness for f in features_list if f.instrumentalness is not None)
        instrumentalness_count = sum(1 for f in features_list if f.instrumentalness is not None)
        
        liveness_sum = sum(f.liveness for f in features_list if f.liveness is not None)
        liveness_count = sum(1 for f in features_list if f.liveness is not None)
        
        speechiness_sum = sum(f.speechiness for f in features_list if f.speechiness is not None)
        speechiness_count = sum(1 for f in features_list if f.speechiness is not None)
        
        return AudioFeatures(
            tempo=tempo_sum / tempo_count if tempo_count > 0 else None,
            energy=energy_sum / energy_count if energy_count > 0 else None,
            valence=valence_sum / valence_count if valence_count > 0 else None,
            danceability=danceability_sum / danceability_count if danceability_count > 0 else None,
            acousticness=acousticness_sum / acousticness_count if acousticness_count > 0 else None,
            instrumentalness=instrumentalness_sum / instrumentalness_count if instrumentalness_count > 0 else None,
            liveness=liveness_sum / liveness_count if liveness_count > 0 else None,
            speechiness=speechiness_sum / speechiness_count if speechiness_count > 0 else None
        )
    
    def _calculate_feature_variance(self, features_list: List[AudioFeatures]) -> Dict[str, float]:
        """Calculate variance for each feature."""
        if len(features_list) <= 1:
            return {feature: 0.0 for feature in self.numerical_features}
        
        average_features = self._calculate_average_features(features_list)
        variance = {}
        
        for feature_name in self.numerical_features:
            avg_value = getattr(average_features, feature_name)
            if avg_value is None:
                variance[feature_name] = 0.0
                continue
            
            values = [getattr(f, feature_name) for f in features_list 
                     if getattr(f, feature_name) is not None]
            
            if len(values) <= 1:
                variance[feature_name] = 0.0
            else:
                variance[feature_name] = sum((v - avg_value) ** 2 for v in values) / len(values)
        
        return variance
    
    def calculate_feature_similarity(self, track_features: AudioFeatures, 
                                   target_profile: AudioFeatureProfile,
                                   weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate weighted similarity score (0.0-1.0)."""
        if weights is None:
            weights = self.default_weights
        
        similarity_scores = {}
        
        # Numerical feature similarities
        for feature_name in self.numerical_features:
            track_value = getattr(track_features, feature_name)
            if track_value is None:
                continue
            
            target_range = getattr(target_profile, f"{feature_name}_range")
            
            if self._is_in_range(track_value, target_range):
                # Perfect match if within range
                similarity_scores[feature_name] = 1.0
            else:
                # Calculate distance-based similarity
                distance = self._min_distance_to_range(track_value, target_range)
                # Normalize distance based on feature scale
                if feature_name == "tempo":
                    max_distance = 100.0  # Max reasonable tempo difference
                else:
                    max_distance = 1.0    # For 0-1 scale features
                
                similarity_scores[feature_name] = max(0.0, 1.0 - (distance / max_distance))
        
        # Categorical feature similarities
        if track_features.key is not None:
            similarity_scores['key'] = self._calculate_key_similarity(
                track_features.key, target_profile.preferred_keys
            )
        
        if track_features.mode is not None:
            similarity_scores['mode'] = self._calculate_mode_similarity(
                track_features.mode, target_profile.preferred_modes
            )
        
        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        
        for feature, weight in weights.items():
            if feature in similarity_scores:
                weighted_sum += similarity_scores[feature] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _is_in_range(self, value: float, range_tuple: Tuple[float, float]) -> bool:
        """Check if value is within range."""
        return range_tuple[0] <= value <= range_tuple[1]
    
    def _min_distance_to_range(self, value: float, range_tuple: Tuple[float, float]) -> float:
        """Calculate minimum distance from value to range."""
        min_val, max_val = range_tuple
        if value < min_val:
            return min_val - value
        elif value > max_val:
            return value - max_val
        else:
            return 0.0
    
    def _calculate_key_similarity(self, track_key: int, preferred_keys: List[int]) -> float:
        """Calculate key similarity using circle of fifths."""
        if not preferred_keys:
            return 0.5  # Neutral score
        
        # Circle of fifths distances
        circle_of_fifths = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]
        
        max_similarity = 0.0
        for preferred_key in preferred_keys:
            # Find positions in circle of fifths
            try:
                track_pos = circle_of_fifths.index(track_key)
                preferred_pos = circle_of_fifths.index(preferred_key)
                
                # Calculate distance (considering circular nature)
                distance = min(
                    abs(track_pos - preferred_pos),
                    12 - abs(track_pos - preferred_pos)
                )
                
                # Convert distance to similarity (0 = perfect, 6 = worst)
                similarity = 1.0 - (distance / 6.0)
                max_similarity = max(max_similarity, similarity)
            except ValueError:
                # Key not in circle of fifths, use direct comparison
                similarity = 1.0 if track_key == preferred_key else 0.0
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _calculate_mode_similarity(self, track_mode: int, preferred_modes: List[int]) -> float:
        """Calculate mode similarity."""
        if not preferred_modes:
            return 0.5  # Neutral score
        
        return 1.0 if track_mode in preferred_modes else 0.0
    
    def calculate_genre_similarity(self, track_genres: List[str], 
                                 target_genres: List[str],
                                 genre_hierarchy: Optional[Dict[str, List[str]]] = None) -> float:
        """Calculate genre similarity using hierarchical matching."""
        if not track_genres or not target_genres:
            return 0.5  # Neutral score for missing data
        
        max_similarity = 0.0
        
        for track_genre in track_genres:
            for target_genre in target_genres:
                # Exact match
                if track_genre.lower() == target_genre.lower():
                    max_similarity = max(max_similarity, 1.0)
                # Partial match (substring)
                elif (track_genre.lower() in target_genre.lower() or 
                      target_genre.lower() in track_genre.lower()):
                    max_similarity = max(max_similarity, 0.7)
                # Hierarchical match (if hierarchy provided)
                elif genre_hierarchy and self._is_genre_related(
                    track_genre, target_genre, genre_hierarchy
                ):
                    max_similarity = max(max_similarity, 0.5)
        
        return max_similarity
    
    def _is_genre_related(self, genre1: str, genre2: str, 
                         genre_hierarchy: Dict[str, List[str]]) -> bool:
        """Check if two genres are related in the hierarchy."""
        genre1_lower = genre1.lower()
        genre2_lower = genre2.lower()
        
        for parent, children in genre_hierarchy.items():
            parent_lower = parent.lower()
            children_lower = [child.lower() for child in children]
            
            # Check if both genres are in the same family
            if ((genre1_lower == parent_lower or genre1_lower in children_lower) and
                (genre2_lower == parent_lower or genre2_lower in children_lower)):
                return True
        
        return False
    
    def calculate_euclidean_distance(self, features1: AudioFeatures, 
                                   features2: AudioFeatures,
                                   weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate weighted Euclidean distance between audio features."""
        if weights is None:
            weights = self.default_weights
        
        distance_squared = 0.0
        total_weight = 0.0
        
        for feature_name in self.numerical_features:
            if feature_name not in weights:
                continue
            
            value1 = getattr(features1, feature_name)
            value2 = getattr(features2, feature_name)
            
            if value1 is None or value2 is None:
                continue
            
            # Normalize tempo to 0-1 scale
            if feature_name == "tempo":
                value1 = (value1 - 50.0) / 150.0
                value2 = (value2 - 50.0) / 150.0
            
            weight = weights[feature_name]
            distance_squared += weight * (value1 - value2) ** 2
            total_weight += weight
        
        return math.sqrt(distance_squared / total_weight) if total_weight > 0 else 1.0
    
    def calculate_average_similarity(self, track: Track, selected_tracks: List[Track]) -> float:
        """Calculate average similarity between a track and a list of tracks."""
        if not selected_tracks or not track.audio_features:
            return 0.0
        
        similarities = []
        for selected_track in selected_tracks:
            if selected_track.audio_features:
                # Use inverse of Euclidean distance as similarity
                distance = self.calculate_euclidean_distance(
                    track.audio_features, selected_track.audio_features
                )
                similarity = 1.0 - min(1.0, distance)  # Clamp to [0, 1]
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0 