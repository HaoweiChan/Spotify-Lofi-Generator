"""
YouTube Data API client implementation.
Provides video search, metadata retrieval, and copyright claim detection.
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from src.api.base_client import BaseAPIClient, AuthenticationError
from src.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class YouTubeClient(BaseAPIClient):
    """YouTube Data API v3 client for licensing verification."""
    
    def __init__(self, api_key: str, cache_manager: Optional[CacheManager] = None):
        """
        Initialize YouTube client.
        
        Args:
            api_key: YouTube Data API key
            cache_manager: Optional cache manager for API responses
        """
        super().__init__(
            base_url="https://www.googleapis.com/youtube/v3",
            rate_limit=10000,  # 10,000 units per day (very conservative rate)
            cache_manager=cache_manager
        )
        self.api_key = api_key
        
    async def authenticate(self) -> str:
        """YouTube API uses API key authentication, no token needed."""
        return self.api_key
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """YouTube API doesn't use headers for auth, uses query params."""
        return {}
        
    async def search_videos(
        self, 
        query: str, 
        max_results: int = 25,
        order: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-50)
            order: Sort order (relevance, date, rating, viewCount, title)
            
        Returns:
            List of video dictionaries with metadata
        """
        cache_key = self.cache_manager.get_cache_key("youtube_search", query, max_results) if self.cache_manager else None
        
        params = {
            "part": "snippet,statistics",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
            "key": self.api_key
        }
        
        if cache_key:
            result = await self._cached_request(cache_key, "GET", "search", ttl=3600, params=params)
        else:
            result = await self._make_request("GET", "search", params=params)
            
        videos = []
        for item in result.get("items", []):
            video_data = self._normalize_video_data(item)
            videos.append(video_data)
            
        return videos
        
    async def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video details including licensing info
        """
        cache_key = self.cache_manager.get_cache_key("youtube_video", video_id) if self.cache_manager else None
        
        params = {
            "part": "snippet,statistics,status,contentDetails",
            "id": video_id,
            "key": self.api_key
        }
        
        if cache_key:
            result = await self._cached_request(
                cache_key, "GET", "videos", ttl=86400, params=params  # 24 hours
            )
        else:
            result = await self._make_request("GET", "videos", params=params)
            
        if not result.get("items"):
            return {}
            
        return self._normalize_video_data(result["items"][0], detailed=True)
        
    async def search_track_on_youtube(
        self, 
        artist: str, 
        title: str,
        additional_terms: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for a specific track on YouTube.
        
        Args:
            artist: Artist name
            title: Track title
            additional_terms: Additional search terms
            
        Returns:
            List of matching videos with licensing information
        """
        # Construct search query
        query_parts = [artist, title]
        if additional_terms:
            query_parts.append(additional_terms)
            
        query = " ".join(query_parts)
        
        videos = await self.search_videos(query, max_results=10)
        
        # Get detailed info for each video to check licensing
        detailed_videos = []
        for video in videos:
            try:
                details = await self.get_video_details(video["id"])
                if details:
                    detailed_videos.append(details)
            except Exception as e:
                logger.warning(f"Failed to get details for video {video['id']}: {e}")
                
        return detailed_videos
        
    async def check_content_id_claims(self, video_id: str) -> Dict[str, Any]:
        """
        Check for Content ID claims on a video.
        Note: This requires special API access and may not be available for all applications.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with Content ID claim information
        """
        # This would require YouTube Partner API access
        # For now, we'll return basic licensing info from video details
        video_details = await self.get_video_details(video_id)
        
        return {
            "video_id": video_id,
            "has_claims": False,  # Would need Partner API to determine
            "license": video_details.get("license", "unknown"),
            "embeddable": video_details.get("embeddable", True),
            "public_stats_viewable": video_details.get("public_stats_viewable", True),
            "made_for_kids": video_details.get("made_for_kids", False)
        }
        
    def _normalize_video_data(self, video_data: Dict[str, Any], detailed: bool = False) -> Dict[str, Any]:
        """Normalize YouTube video data to standard format."""
        snippet = video_data.get("snippet", {})
        statistics = video_data.get("statistics", {})
        status = video_data.get("status", {}) if detailed else {}
        content_details = video_data.get("contentDetails", {}) if detailed else {}
        
        result = {
            "id": video_data.get("id", {}).get("videoId") or video_data.get("id"),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "comment_count": int(statistics.get("commentCount", 0)),
            "provider": "youtube"
        }
        
        if detailed:
            result.update({
                "duration": content_details.get("duration", ""),
                "license": content_details.get("licensedContent", False),
                "embeddable": status.get("embeddable", True),
                "public_stats_viewable": status.get("publicStatsViewable", True),
                "made_for_kids": status.get("madeForKids", False),
                "upload_status": status.get("uploadStatus", ""),
                "privacy_status": status.get("privacyStatus", ""),
                "category_id": snippet.get("categoryId", ""),
                "tags": snippet.get("tags", [])
            })
            
        return result
        
    async def get_licensing_info(self, video_id: str) -> Dict[str, Any]:
        """
        Get comprehensive licensing information for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with licensing assessment
        """
        video_details = await self.get_video_details(video_id)
        content_id_info = await self.check_content_id_claims(video_id)
        
        # Assess business use risk
        risk_factors = []
        risk_score = 0.0
        
        # Check privacy status
        if video_details.get("privacy_status") != "public":
            risk_factors.append("Video is not public")
            risk_score += 0.3
            
        # Check if embeddable
        if not video_details.get("embeddable", True):
            risk_factors.append("Video is not embeddable")
            risk_score += 0.2
            
        # Check if made for kids (COPPA restrictions)
        if video_details.get("made_for_kids", False):
            risk_factors.append("Video is marked as made for kids")
            risk_score += 0.1
            
        # Check for potential copyright issues based on title/description
        title_lower = video_details.get("title", "").lower()
        if any(term in title_lower for term in ["official", "music video", "album"]):
            risk_factors.append("Likely official content with potential copyright restrictions")
            risk_score += 0.4
            
        # Determine overall risk level
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
            
        return {
            "video_id": video_id,
            "title": video_details.get("title", ""),
            "channel": video_details.get("channel_title", ""),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "embeddable": video_details.get("embeddable", True),
            "public_stats_viewable": video_details.get("public_stats_viewable", True),
            "privacy_status": video_details.get("privacy_status", ""),
            "made_for_kids": video_details.get("made_for_kids", False),
            "licensed_content": video_details.get("license", False),
            "content_id_claims": content_id_info.get("has_claims", False),
            "business_use_recommendation": self._get_business_use_recommendation(risk_level, risk_factors)
        }
        
    def _get_business_use_recommendation(self, risk_level: str, risk_factors: List[str]) -> str:
        """Get business use recommendation based on risk assessment."""
        if risk_level == "high":
            return "Not recommended for business use without explicit licensing"
        elif risk_level == "medium":
            return "Use with caution - consider seeking additional licensing"
        else:
            return "Generally safe for business use, but verify licensing terms"
            
    # Abstract method implementations (not used for YouTube)
    async def search_tracks(self, query: str, limit: int = 50, audio_features: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Not applicable for YouTube - use search_videos instead."""
        return await self.search_videos(query, limit)
        
    async def get_audio_features(self, track_id: str) -> Dict[str, float]:
        """Not applicable for YouTube - returns empty dict."""
        return {}
        
    async def get_track_info(self, track_id: str) -> Dict[str, Any]:
        """Get video info instead of track info."""
        return await self.get_video_details(track_id) 