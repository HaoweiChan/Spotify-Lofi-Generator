"""
Track matching utilities for fuzzy string matching and track resolution.
Handles incomplete or inaccurate user-provided track information.
"""

import re
import unicodedata
from typing import List, Dict, Tuple, Optional, Set
from difflib import SequenceMatcher
import json
import os
from dataclasses import dataclass

@dataclass
class MatchResult:
    """Result of a track matching operation."""
    similarity_score: float
    normalized_track: str
    normalized_artist: str
    match_details: Dict[str, float]

class TrackMatcher:
    """Fuzzy matching utilities for track names and artists."""
    
    def __init__(self):
        """Initialize the track matcher with artist aliases."""
        self.artist_aliases = self._load_artist_aliases()
        self.common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
        }
        self.featuring_patterns = [
            r'\bfeat\.?\s+',
            r'\bft\.?\s+',
            r'\bfeaturing\s+',
            r'\bwith\s+',
            r'\bvs\.?\s+',
            r'\b&\s+'
        ]
        self.remix_patterns = [
            r'\(.*remix.*\)',
            r'\(.*mix.*\)',
            r'\(.*version.*\)',
            r'\(.*edit.*\)',
            r'\bremaster.*',
            r'\bremix\b',
            r'\bmix\b'
        ]
        self.parenthetical_patterns = [
            r'\(official.*\)',
            r'\(music.*video\)',
            r'\(lyric.*video\)',
            r'\(audio.*\)',
            r'\(live.*\)',
            r'\(acoustic.*\)',
            r'\(explicit.*\)',
            r'\(clean.*\)'
        ]
    
    def _load_artist_aliases(self) -> Dict[str, List[str]]:
        """Load artist aliases from JSON file."""
        try:
            aliases_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'artist_aliases.json')
            if os.path.exists(aliases_path):
                with open(aliases_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Default aliases if file doesn't exist
        return {
            "eminem": ["slim shady", "marshall mathers", "b-rabbit"],
            "jay-z": ["jay z", "shawn carter", "hov", "jay z"],
            "the beatles": ["beatles", "fab four"],
            "beyonce": ["beyoncé", "destiny's child"],
            "justin timberlake": ["nsync", "*nsync"],
            "lady gaga": ["stefani germanotta"],
            "kanye west": ["ye", "yeezy"],
            "taylor swift": ["t swift"],
            "bruno mars": ["peter hernandez"],
            "the weeknd": ["weeknd", "abel tesfaye"]
        }
    
    def normalize_string(self, text: str) -> str:
        """Apply basic string normalization."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def normalize_track_name(self, track_name: str) -> str:
        """Apply music-specific normalization to track names."""
        if not track_name:
            return ""
        
        # Start with basic normalization
        normalized = self.normalize_string(track_name)
        
        # Remove parenthetical content
        for pattern in self.parenthetical_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove remix indicators
        for pattern in self.remix_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Handle featuring artists
        for pattern in self.featuring_patterns:
            normalized = re.sub(pattern + r'.*$', '', normalized, flags=re.IGNORECASE)
        
        # Remove punctuation except apostrophes in contractions
        normalized = re.sub(r'[^\w\s\']', ' ', normalized)
        
        # Handle contractions
        normalized = re.sub(r"'s\b", '', normalized)  # Remove possessive 's
        normalized = re.sub(r"'t\b", 'nt', normalized)  # can't -> cant
        normalized = re.sub(r"'re\b", 're', normalized)  # you're -> youre
        normalized = re.sub(r"'ll\b", 'll', normalized)  # you'll -> youll
        normalized = re.sub(r"'ve\b", 've', normalized)  # you've -> youve
        normalized = re.sub(r"'d\b", 'd', normalized)   # you'd -> youd
        
        # Remove common prefixes
        normalized = re.sub(r'^(the|a|an)\s+', '', normalized)
        
        # Clean up whitespace
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        return normalized
    
    def normalize_artist_name(self, artist_name: str) -> str:
        """Apply music-specific normalization to artist names."""
        if not artist_name:
            return ""
        
        # Start with basic normalization
        normalized = self.normalize_string(artist_name)
        
        # Handle featuring artists - extract main artist
        for pattern in self.featuring_patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                normalized = normalized[:match.start()].strip()
                break
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(the|a|an)\s+', '', normalized)
        normalized = re.sub(r'\s+(band|group|orchestra|ensemble)$', '', normalized)
        
        # Handle ampersands
        normalized = re.sub(r'\s*&\s*', ' and ', normalized)
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Clean up whitespace
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        return normalized
    
    def extract_featuring_artists(self, text: str) -> Tuple[str, List[str]]:
        """Extract main artist and featuring artists from text."""
        main_artist = text
        featuring_artists = []
        
        for pattern in self.featuring_patterns:
            match = re.search(pattern + r'(.+)$', text, flags=re.IGNORECASE)
            if match:
                main_artist = text[:match.start()].strip()
                featuring_text = match.group(1).strip()
                
                # Split featuring artists by common separators
                featuring_artists = re.split(r'[,&]|\sand\s', featuring_text)
                featuring_artists = [artist.strip() for artist in featuring_artists if artist.strip()]
                break
        
        return main_artist, featuring_artists
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate normalized Levenshtein similarity (0.0-1.0)."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        distance = self.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len)
    
    def jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        # Use SequenceMatcher as approximation for Jaro-Winkler
        return SequenceMatcher(None, s1, s2).ratio()
    
    def token_similarity(self, s1: str, s2: str) -> float:
        """Calculate token-based similarity using Jaccard index."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        
        # Remove common words that don't add meaning
        tokens1 = tokens1 - self.common_words
        tokens2 = tokens2 - self.common_words
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
    
    def phonetic_similarity(self, s1: str, s2: str) -> float:
        """Calculate phonetic similarity using simple Soundex-like algorithm."""
        def soundex_simple(text: str) -> str:
            """Simple Soundex-like algorithm."""
            if not text:
                return ""
            
            # Keep first letter
            result = text[0].upper()
            
            # Replace consonants with numbers
            replacements = {
                'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3',
                'L': '4', 'MN': '5', 'R': '6'
            }
            
            for i, char in enumerate(text[1:], 1):
                char = char.upper()
                for group, digit in replacements.items():
                    if char in group:
                        result += digit
                        break
            
            # Remove duplicates and vowels
            result = re.sub(r'(.)\1+', r'\1', result)
            result = re.sub(r'[AEIOUY]', '', result[1:])
            result = text[0].upper() + result
            
            # Pad or truncate to 4 characters
            return (result + '0000')[:4]
        
        soundex1 = soundex_simple(s1)
        soundex2 = soundex_simple(s2)
        
        return 1.0 if soundex1 == soundex2 else 0.0
    
    def calculate_similarity(self, track1: str, artist1: str, track2: str, artist2: str) -> MatchResult:
        """Calculate comprehensive similarity between two track/artist pairs."""
        # Normalize inputs
        norm_track1 = self.normalize_track_name(track1)
        norm_artist1 = self.normalize_artist_name(artist1)
        norm_track2 = self.normalize_track_name(track2)
        norm_artist2 = self.normalize_artist_name(artist2)
        
        # Calculate track name similarities
        track_levenshtein = self.levenshtein_similarity(norm_track1, norm_track2)
        track_jaro = self.jaro_winkler_similarity(norm_track1, norm_track2)
        track_token = self.token_similarity(norm_track1, norm_track2)
        track_phonetic = self.phonetic_similarity(norm_track1, norm_track2)
        
        # Calculate artist name similarities
        artist_levenshtein = self.levenshtein_similarity(norm_artist1, norm_artist2)
        artist_jaro = self.jaro_winkler_similarity(norm_artist1, norm_artist2)
        artist_token = self.token_similarity(norm_artist1, norm_artist2)
        artist_phonetic = self.phonetic_similarity(norm_artist1, norm_artist2)
        
        # Check artist aliases
        artist_alias_bonus = 0.0
        if self._check_artist_aliases(norm_artist1, norm_artist2):
            artist_alias_bonus = 0.2
        
        # Weighted combination of similarities
        track_similarity = (
            track_levenshtein * 0.4 +
            track_jaro * 0.3 +
            track_token * 0.2 +
            track_phonetic * 0.1
        )
        
        artist_similarity = (
            artist_levenshtein * 0.4 +
            artist_jaro * 0.3 +
            artist_token * 0.2 +
            artist_phonetic * 0.1 +
            artist_alias_bonus
        )
        
        # Overall similarity (track: 60%, artist: 40%)
        overall_similarity = track_similarity * 0.6 + artist_similarity * 0.4
        
        match_details = {
            "track_levenshtein": track_levenshtein,
            "track_jaro": track_jaro,
            "track_token": track_token,
            "track_phonetic": track_phonetic,
            "track_similarity": track_similarity,
            "artist_levenshtein": artist_levenshtein,
            "artist_jaro": artist_jaro,
            "artist_token": artist_token,
            "artist_phonetic": artist_phonetic,
            "artist_alias_bonus": artist_alias_bonus,
            "artist_similarity": artist_similarity
        }
        
        return MatchResult(
            similarity_score=overall_similarity,
            normalized_track=norm_track2,
            normalized_artist=norm_artist2,
            match_details=match_details
        )
    
    def _check_artist_aliases(self, artist1: str, artist2: str) -> bool:
        """Check if two artists are aliases of each other."""
        artist1_lower = artist1.lower()
        artist2_lower = artist2.lower()
        
        # Check direct aliases
        for main_artist, aliases in self.artist_aliases.items():
            main_lower = main_artist.lower()
            aliases_lower = [alias.lower() for alias in aliases]
            
            # Check if both artists are in the same alias group
            if ((artist1_lower == main_lower or artist1_lower in aliases_lower) and
                (artist2_lower == main_lower or artist2_lower in aliases_lower)):
                return True
        
        return False
    
    def generate_search_variations(self, track_name: str, artist_name: str) -> List[str]:
        """Generate search query variations for partial matching."""
        variations = []
        
        # Original query
        original = f"{track_name} {artist_name}"
        variations.append(original)
        
        # Normalized versions
        norm_track = self.normalize_track_name(track_name)
        norm_artist = self.normalize_artist_name(artist_name)
        if norm_track and norm_artist:
            variations.append(f"{norm_track} {norm_artist}")
        
        # Individual components
        if track_name:
            variations.append(track_name)
        if artist_name:
            variations.append(artist_name)
        if norm_track:
            variations.append(norm_track)
        if norm_artist:
            variations.append(norm_artist)
        
        # Partial track names (for long titles)
        track_words = track_name.split()
        if len(track_words) > 2:
            # First few words
            variations.append(f"{' '.join(track_words[:2])} {artist_name}")
            variations.append(f"{' '.join(track_words[:3])} {artist_name}")
        
        # Artist variations
        main_artist, featuring = self.extract_featuring_artists(artist_name)
        if main_artist != artist_name:
            variations.append(f"{track_name} {main_artist}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in variations:
            if variation and variation not in seen:
                seen.add(variation)
                unique_variations.append(variation)
        
        return unique_variations
    
    def filter_by_similarity(self, candidates: List[Dict], target_track: str, target_artist: str, 
                           min_similarity: float = 0.6) -> List[Tuple[Dict, float]]:
        """Filter candidates by similarity threshold and return with scores."""
        results = []
        
        for candidate in candidates:
            # Extract track and artist from candidate
            candidate_track = candidate.get('name', '')
            candidate_artist = candidate.get('artist', '')
            if isinstance(candidate.get('artists'), list) and candidate['artists']:
                candidate_artist = candidate['artists'][0]
            
            # Calculate similarity
            match_result = self.calculate_similarity(
                target_track, target_artist,
                candidate_track, candidate_artist
            )
            
            # Filter by threshold
            if match_result.similarity_score >= min_similarity:
                results.append((candidate, match_result.similarity_score))
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results 