"""
Licensing verification service.
Coordinates YouTube Content ID verification and business use compliance scoring.
"""

import logging
from typing import Dict, Any, List, Optional
from src.models.playlist import Playlist
from src.models.track import Track
from src.models.license_info import LicenseInfo
from src.api.youtube_client import YouTubeClient
from src.utils.cache_manager import CacheManager
from config.settings import Settings

logger = logging.getLogger(__name__)

class LicensingChecker:
    """Service for checking music licensing and business use compliance."""
    
    def __init__(self, settings: Settings):
        """
        Initialize licensing checker.
        
        Args:
            settings: Application settings containing API keys and configuration
        """
        self.settings = settings
        self.cache_manager = CacheManager(settings.REDIS_URL)
        self.youtube_client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.cache_manager.connect()
        if self.settings.YOUTUBE_API_KEY:
            self.youtube_client = YouTubeClient(
                api_key=self.settings.YOUTUBE_API_KEY,
                cache_manager=self.cache_manager
            )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cache_manager.close()
        if self.youtube_client:
            await self.youtube_client.close()
            
    async def check_playlist_licensing(self, playlist: Playlist) -> Playlist:
        """
        Check licensing for all tracks in a playlist.
        
        Args:
            playlist: Playlist object to check
            
        Returns:
            Updated playlist with licensing information
        """
        logger.info(f"Checking licensing for playlist '{playlist.name}' with {len(playlist.tracks)} tracks")
        
        updated_tracks = []
        for track in playlist.tracks:
            try:
                license_info = await self.check_track_licensing(track)
                track.license_info = license_info
                updated_tracks.append(track)
            except Exception as e:
                logger.warning(f"Failed to check licensing for track {track.id}: {e}")
                # Add track with unknown licensing status
                track.license_info = LicenseInfo(
                    track_id=track.id,
                    business_use_allowed=False,
                    risk_level="unknown",
                    risk_factors=["Unable to verify licensing"],
                    recommendation="Manual verification required"
                )
                updated_tracks.append(track)
                
        playlist.tracks = updated_tracks
        playlist.licensing_summary = self._generate_licensing_summary(updated_tracks)
        
        logger.info(f"Licensing check complete. Summary: {playlist.licensing_summary}")
        return playlist
        
    async def check_track_licensing(self, track: Track) -> LicenseInfo:
        """
        Check licensing for a specific track.
        
        Args:
            track: Track object to check
            
        Returns:
            LicenseInfo object with licensing details
        """
        if not self.youtube_client:
            return LicenseInfo(
                track_id=track.id,
                business_use_allowed=False,
                risk_level="unknown",
                risk_factors=["YouTube API not configured"],
                recommendation="Configure YouTube API for licensing verification"
            )
            
        # Search for the track on YouTube
        youtube_videos = await self.youtube_client.search_track_on_youtube(
            artist=", ".join(track.artists),
            title=track.name
        )
        
        if not youtube_videos:
            return LicenseInfo(
                track_id=track.id,
                business_use_allowed=False,
                risk_level="medium",
                risk_factors=["Track not found on YouTube"],
                recommendation="Track may not be widely available - verify licensing independently"
            )
            
        # Analyze the most relevant video (first result)
        primary_video = youtube_videos[0]
        licensing_info = await self.youtube_client.get_licensing_info(primary_video["id"])
        
        # Check additional videos for comprehensive analysis
        additional_risks = []
        if len(youtube_videos) > 1:
            for video in youtube_videos[1:3]:  # Check up to 2 additional videos
                try:
                    additional_info = await self.youtube_client.get_licensing_info(video["id"])
                    if additional_info["risk_level"] == "high":
                        additional_risks.extend(additional_info["risk_factors"])
                except Exception as e:
                    logger.warning(f"Failed to check additional video {video['id']}: {e}")
                    
        # Combine risk factors
        all_risk_factors = licensing_info["risk_factors"] + additional_risks
        
        # Determine overall business use allowance
        business_use_allowed = self._assess_business_use(licensing_info, additional_risks)
        
        # Create comprehensive license info
        license_info = LicenseInfo(
            track_id=track.id,
            youtube_video_id=primary_video["id"],
            youtube_title=primary_video["title"],
            youtube_channel=primary_video["channel_title"],
            business_use_allowed=business_use_allowed,
            risk_level=licensing_info["risk_level"],
            risk_factors=list(set(all_risk_factors)),  # Remove duplicates
            recommendation=licensing_info["business_use_recommendation"],
            embeddable=licensing_info["embeddable"],
            content_id_claims=licensing_info["content_id_claims"],
            additional_notes=self._generate_additional_notes(licensing_info, youtube_videos)
        )
        
        return license_info
        
    def _assess_business_use(
        self, 
        primary_licensing: Dict[str, Any], 
        additional_risks: List[str]
    ) -> bool:
        """Assess whether business use is allowed based on licensing information."""
        # High risk = not allowed
        if primary_licensing["risk_level"] == "high":
            return False
            
        # Medium risk with additional high-risk factors = not allowed
        if primary_licensing["risk_level"] == "medium" and additional_risks:
            return False
            
        # Check for specific blocking factors
        blocking_factors = [
            "not embeddable",
            "official content",
            "copyright restrictions",
            "not public"
        ]
        
        all_factors = primary_licensing["risk_factors"] + additional_risks
        for factor in all_factors:
            if any(blocking in factor.lower() for blocking in blocking_factors):
                return False
                
        return True
        
    def _generate_additional_notes(
        self, 
        licensing_info: Dict[str, Any], 
        youtube_videos: List[Dict[str, Any]]
    ) -> str:
        """Generate additional notes about the licensing assessment."""
        notes = []
        
        # Note about multiple versions
        if len(youtube_videos) > 1:
            notes.append(f"Found {len(youtube_videos)} versions on YouTube")
            
        # Note about video popularity
        primary_video = youtube_videos[0]
        view_count = primary_video.get("view_count", 0)
        if view_count > 1000000:
            notes.append("High-popularity content (>1M views)")
        elif view_count < 10000:
            notes.append("Low-popularity content (<10K views)")
            
        # Note about channel type
        channel = primary_video.get("channel_title", "").lower()
        if any(term in channel for term in ["official", "records", "music", "vevo"]):
            notes.append("Content from official music channel")
            
        # Note about licensing status
        if licensing_info.get("licensed_content"):
            notes.append("Content marked as licensed")
            
        return " | ".join(notes) if notes else "No additional notes"
        
    def _generate_licensing_summary(self, tracks: List[Track]) -> Dict[str, Any]:
        """Generate a summary of licensing status for all tracks."""
        total_tracks = len(tracks)
        if total_tracks == 0:
            return {"total": 0, "safe": 0, "risky": 0, "unknown": 0}
            
        safe_count = 0
        risky_count = 0
        unknown_count = 0
        
        risk_level_counts = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
        common_risk_factors = {}
        
        for track in tracks:
            if track.license_info:
                license_info = track.license_info
                
                # Count by business use allowance
                if license_info.business_use_allowed:
                    safe_count += 1
                elif license_info.risk_level == "unknown":
                    unknown_count += 1
                else:
                    risky_count += 1
                    
                # Count by risk level
                risk_level = license_info.risk_level
                risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
                
                # Count common risk factors
                for factor in license_info.risk_factors:
                    common_risk_factors[factor] = common_risk_factors.get(factor, 0) + 1
            else:
                unknown_count += 1
                
        # Find most common risk factors
        top_risk_factors = sorted(
            common_risk_factors.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        return {
            "total": total_tracks,
            "safe_for_business": safe_count,
            "risky_for_business": risky_count,
            "unknown_status": unknown_count,
            "risk_level_breakdown": risk_level_counts,
            "common_risk_factors": [factor for factor, count in top_risk_factors],
            "business_use_percentage": round((safe_count / total_tracks) * 100, 1) if total_tracks > 0 else 0
        }
        
    async def generate_licensing_report(self, playlist: Playlist) -> Dict[str, Any]:
        """
        Generate a comprehensive licensing report for a playlist.
        
        Args:
            playlist: Playlist with licensing information
            
        Returns:
            Detailed licensing report
        """
        if not playlist.licensing_summary:
            playlist = await self.check_playlist_licensing(playlist)
            
        report = {
            "playlist_name": playlist.name,
            "total_tracks": len(playlist.tracks),
            "generated_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "summary": playlist.licensing_summary,
            "recommendations": self._generate_recommendations(playlist),
            "track_details": []
        }
        
        # Add detailed track information
        for track in playlist.tracks:
            if track.license_info:
                track_detail = {
                    "track_name": track.name,
                    "artist": ", ".join(track.artists),
                    "business_use_allowed": track.license_info.business_use_allowed,
                    "risk_level": track.license_info.risk_level,
                    "risk_factors": track.license_info.risk_factors,
                    "recommendation": track.license_info.recommendation,
                    "youtube_video_id": track.license_info.youtube_video_id,
                    "youtube_title": track.license_info.youtube_title
                }
                report["track_details"].append(track_detail)
                
        return report
        
    def _generate_recommendations(self, playlist: Playlist) -> List[str]:
        """Generate recommendations based on licensing analysis."""
        recommendations = []
        summary = playlist.licensing_summary
        
        if not summary:
            return ["Complete licensing check first"]
            
        business_use_percentage = summary.get("business_use_percentage", 0)
        
        if business_use_percentage >= 80:
            recommendations.append("Playlist is generally safe for business use")
        elif business_use_percentage >= 50:
            recommendations.append("Playlist has moderate licensing risk - review individual tracks")
        else:
            recommendations.append("Playlist has high licensing risk - not recommended for business use")
            
        # Specific recommendations based on common risk factors
        common_factors = summary.get("common_risk_factors", [])
        
        if "official content" in str(common_factors).lower():
            recommendations.append("Consider using cover versions or royalty-free alternatives")
            
        if "not embeddable" in str(common_factors).lower():
            recommendations.append("Some tracks cannot be embedded - verify platform-specific licensing")
            
        if summary.get("unknown_status", 0) > 0:
            recommendations.append("Some tracks require manual licensing verification")
            
        return recommendations 