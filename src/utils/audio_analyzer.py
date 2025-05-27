"""
Audio Analyzer Utility

Provides audio feature extraction from files, tempo detection and analysis,
key and mode detection, and audio similarity comparison.
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("librosa not available - audio analysis features will be limited")

try:
    import essentia
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
except ImportError:
    ESSENTIA_AVAILABLE = False
    logging.warning("essentia not available - advanced audio analysis features will be limited")

from ..models.audio_features import AudioFeatures

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """Utility for audio feature extraction and analysis."""
    
    def __init__(self, sample_rate: int = 22050):
        """
        Initialize audio analyzer.
        
        Args:
            sample_rate: Target sample rate for analysis
        """
        self.sample_rate = sample_rate
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required audio analysis libraries are available."""
        if not LIBROSA_AVAILABLE and not ESSENTIA_AVAILABLE:
            logger.warning("No audio analysis libraries available. Install librosa or essentia for full functionality.")
    
    async def analyze_audio_file(self, file_path: str) -> Optional[AudioFeatures]:
        """
        Analyze audio file and extract features.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            AudioFeatures object or None if analysis fails
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found: {file_path}")
                return None
            
            # Use librosa if available, otherwise fallback to basic analysis
            if LIBROSA_AVAILABLE:
                return await self._analyze_with_librosa(file_path)
            elif ESSENTIA_AVAILABLE:
                return await self._analyze_with_essentia(file_path)
            else:
                logger.error("No audio analysis library available")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing audio file {file_path}: {e}")
            return None
    
    async def _analyze_with_librosa(self, file_path: str) -> Optional[AudioFeatures]:
        """Analyze audio using librosa library."""
        try:
            # Load audio file
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            
            # Extract features
            features = {}
            
            # Tempo detection
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = float(tempo)
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            features['spectral_centroid'] = float(np.mean(spectral_centroids))
            
            # Zero crossing rate (indicator of speech/music)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            features['zero_crossing_rate'] = float(np.mean(zcr))
            
            # MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            features['mfccs'] = [float(np.mean(mfcc)) for mfcc in mfccs]
            
            # Chroma features (key detection)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            features['chroma'] = [float(np.mean(c)) for c in chroma]
            
            # Estimate key from chroma
            key = self._estimate_key_from_chroma(chroma)
            features['key'] = key
            
            # RMS energy
            rms = librosa.feature.rms(y=y)[0]
            features['rms_energy'] = float(np.mean(rms))
            
            # Spectral rolloff
            rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            features['spectral_rolloff'] = float(np.mean(rolloff))
            
            # Convert to AudioFeatures format
            return self._convert_to_audio_features(features, len(y), sr)
            
        except Exception as e:
            logger.error(f"Error in librosa analysis: {e}")
            return None
    
    async def _analyze_with_essentia(self, file_path: str) -> Optional[AudioFeatures]:
        """Analyze audio using essentia library."""
        try:
            # Load audio
            loader = es.MonoLoader(filename=file_path, sampleRate=self.sample_rate)
            audio = loader()
            
            features = {}
            
            # Tempo detection
            rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
            bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)
            features['tempo'] = float(bpm)
            
            # Key detection
            key_extractor = es.KeyExtractor()
            key, scale, strength = key_extractor(audio)
            features['key'] = self._convert_key_to_number(key)
            features['mode'] = 1 if scale == 'major' else 0
            
            # Spectral features
            spectrum = es.Spectrum()
            spectral_centroid = es.SpectralCentroidTime()
            
            # Process in frames
            frame_size = 2048
            hop_size = 1024
            
            centroids = []
            for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size):
                spec = spectrum(frame)
                centroid = spectral_centroid(spec)
                centroids.append(centroid)
            
            features['spectral_centroid'] = float(np.mean(centroids))
            
            # Energy and dynamics
            energy = es.Energy()
            rms_energies = []
            
            for frame in es.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size):
                rms_energies.append(energy(frame))
            
            features['rms_energy'] = float(np.mean(rms_energies))
            
            # Convert to AudioFeatures format
            return self._convert_to_audio_features(features, len(audio), self.sample_rate)
            
        except Exception as e:
            logger.error(f"Error in essentia analysis: {e}")
            return None
    
    def _convert_to_audio_features(self, features: Dict[str, Any], 
                                 audio_length: int, sample_rate: int) -> AudioFeatures:
        """Convert extracted features to AudioFeatures object."""
        duration_ms = int((audio_length / sample_rate) * 1000)
        
        # Map extracted features to AudioFeatures format
        audio_features = AudioFeatures(
            tempo=features.get('tempo'),
            energy=self._normalize_energy(features.get('rms_energy')),
            valence=self._estimate_valence(features),
            danceability=self._estimate_danceability(features),
            acousticness=self._estimate_acousticness(features),
            instrumentalness=self._estimate_instrumentalness(features),
            liveness=self._estimate_liveness(features),
            speechiness=self._estimate_speechiness(features),
            loudness=self._calculate_loudness(features.get('rms_energy')),
            key=features.get('key'),
            mode=features.get('mode'),
            time_signature=self._estimate_time_signature(features),
            duration_ms=duration_ms
        )
        
        return audio_features
    
    def _estimate_key_from_chroma(self, chroma: np.ndarray) -> Optional[int]:
        """Estimate musical key from chroma features."""
        try:
            # Average chroma across time
            chroma_mean = np.mean(chroma, axis=1)
            
            # Find the dominant pitch class
            key = int(np.argmax(chroma_mean))
            return key
            
        except Exception as e:
            logger.error(f"Error estimating key from chroma: {e}")
            return None
    
    def _convert_key_to_number(self, key_string: str) -> Optional[int]:
        """Convert key string to number (0-11)."""
        key_map = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
            'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
        }
        return key_map.get(key_string)
    
    def _normalize_energy(self, rms_energy: Optional[float]) -> Optional[float]:
        """Normalize RMS energy to 0-1 scale."""
        if rms_energy is None:
            return None
        
        # Simple normalization (could be improved with training data)
        normalized = min(1.0, max(0.0, rms_energy * 10))
        return normalized
    
    def _estimate_valence(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate valence (musical positivity) from features."""
        try:
            # Simple heuristic based on tempo and spectral features
            tempo = features.get('tempo', 120)
            spectral_centroid = features.get('spectral_centroid', 1000)
            
            # Higher tempo and brighter timbre suggest higher valence
            tempo_factor = min(1.0, tempo / 140)  # Normalize around 140 BPM
            brightness_factor = min(1.0, spectral_centroid / 2000)  # Normalize
            
            valence = (tempo_factor + brightness_factor) / 2
            return max(0.0, min(1.0, valence))
            
        except Exception:
            return None
    
    def _estimate_danceability(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate danceability from features."""
        try:
            tempo = features.get('tempo', 120)
            rms_energy = features.get('rms_energy', 0.1)
            
            # Optimal dance tempo range
            if 90 <= tempo <= 140:
                tempo_score = 1.0
            elif 70 <= tempo <= 160:
                tempo_score = 0.7
            else:
                tempo_score = 0.3
            
            energy_score = min(1.0, rms_energy * 5)
            
            danceability = (tempo_score + energy_score) / 2
            return max(0.0, min(1.0, danceability))
            
        except Exception:
            return None
    
    def _estimate_acousticness(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate acousticness from features."""
        try:
            spectral_centroid = features.get('spectral_centroid', 1000)
            spectral_rolloff = features.get('spectral_rolloff', 2000)
            
            # Lower spectral features suggest more acoustic content
            centroid_score = max(0.0, 1.0 - (spectral_centroid / 3000))
            rolloff_score = max(0.0, 1.0 - (spectral_rolloff / 5000))
            
            acousticness = (centroid_score + rolloff_score) / 2
            return max(0.0, min(1.0, acousticness))
            
        except Exception:
            return None
    
    def _estimate_instrumentalness(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate instrumentalness from features."""
        try:
            # Use zero crossing rate and spectral features
            zcr = features.get('zero_crossing_rate', 0.1)
            
            # Lower ZCR suggests less vocal content
            instrumentalness = max(0.0, 1.0 - (zcr * 10))
            return max(0.0, min(1.0, instrumentalness))
            
        except Exception:
            return None
    
    def _estimate_liveness(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate liveness from features."""
        # This is difficult to estimate without training data
        # Return a neutral value
        return 0.1
    
    def _estimate_speechiness(self, features: Dict[str, Any]) -> Optional[float]:
        """Estimate speechiness from features."""
        try:
            zcr = features.get('zero_crossing_rate', 0.1)
            spectral_centroid = features.get('spectral_centroid', 1000)
            
            # Higher ZCR and certain spectral characteristics suggest speech
            zcr_score = min(1.0, zcr * 5)
            
            # Speech typically has specific spectral characteristics
            if 1000 <= spectral_centroid <= 3000:
                spectral_score = 0.7
            else:
                spectral_score = 0.3
            
            speechiness = (zcr_score + spectral_score) / 2
            return max(0.0, min(1.0, speechiness))
            
        except Exception:
            return None
    
    def _calculate_loudness(self, rms_energy: Optional[float]) -> Optional[float]:
        """Calculate loudness in dB from RMS energy."""
        if rms_energy is None or rms_energy <= 0:
            return None
        
        try:
            # Convert RMS to dB (approximate)
            loudness_db = 20 * np.log10(rms_energy)
            return float(loudness_db)
            
        except Exception:
            return None
    
    def _estimate_time_signature(self, features: Dict[str, Any]) -> Optional[int]:
        """Estimate time signature from features."""
        # This requires beat tracking analysis
        # Return common 4/4 as default
        return 4
    
    async def compare_audio_similarity(self, file1: str, file2: str) -> Optional[float]:
        """
        Compare similarity between two audio files.
        
        Args:
            file1: Path to first audio file
            file2: Path to second audio file
            
        Returns:
            Similarity score (0.0 to 1.0) or None if comparison fails
        """
        try:
            features1 = await self.analyze_audio_file(file1)
            features2 = await self.analyze_audio_file(file2)
            
            if not features1 or not features2:
                return None
            
            # Calculate similarity based on multiple features
            similarities = []
            
            # Tempo similarity
            if features1.tempo and features2.tempo:
                tempo_diff = abs(features1.tempo - features2.tempo)
                tempo_sim = max(0.0, 1.0 - (tempo_diff / 50))  # 50 BPM tolerance
                similarities.append(tempo_sim)
            
            # Key similarity
            if features1.key is not None and features2.key is not None:
                key_diff = min(abs(features1.key - features2.key), 
                             12 - abs(features1.key - features2.key))
                key_sim = max(0.0, 1.0 - (key_diff / 6))
                similarities.append(key_sim)
            
            # Energy similarity
            if features1.energy and features2.energy:
                energy_sim = 1.0 - abs(features1.energy - features2.energy)
                similarities.append(energy_sim)
            
            # Overall similarity
            if similarities:
                return sum(similarities) / len(similarities)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error comparing audio similarity: {e}")
            return None
    
    async def extract_audio_fingerprint(self, file_path: str) -> Optional[List[float]]:
        """
        Extract audio fingerprint for similarity matching.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Audio fingerprint as list of floats or None
        """
        try:
            if not LIBROSA_AVAILABLE:
                logger.warning("librosa required for audio fingerprinting")
                return None
            
            # Load audio
            y, sr = librosa.load(file_path, sr=self.sample_rate, duration=30)  # First 30 seconds
            
            # Extract MFCC features as fingerprint
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            
            # Average across time to get fixed-size fingerprint
            fingerprint = np.mean(mfccs, axis=1).tolist()
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error extracting audio fingerprint: {e}")
            return None
    
    def calculate_fingerprint_similarity(self, fingerprint1: List[float], 
                                       fingerprint2: List[float]) -> float:
        """
        Calculate similarity between two audio fingerprints.
        
        Args:
            fingerprint1: First audio fingerprint
            fingerprint2: Second audio fingerprint
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            if len(fingerprint1) != len(fingerprint2):
                return 0.0
            
            # Calculate cosine similarity
            fp1 = np.array(fingerprint1)
            fp2 = np.array(fingerprint2)
            
            dot_product = np.dot(fp1, fp2)
            norm1 = np.linalg.norm(fp1)
            norm2 = np.linalg.norm(fp2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Convert to 0-1 range (cosine similarity is -1 to 1)
            return (similarity + 1) / 2
            
        except Exception as e:
            logger.error(f"Error calculating fingerprint similarity: {e}")
            return 0.0 