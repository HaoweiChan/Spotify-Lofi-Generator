"""
License information data model for tracking business use permissions and copyright status.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class LicenseType(Enum):
    """Types of licenses for music tracks."""
    UNKNOWN = "unknown"
    COPYRIGHT = "copyright"
    CREATIVE_COMMONS = "creative_commons"
    PUBLIC_DOMAIN = "public_domain"
    ROYALTY_FREE = "royalty_free"
    SYNC_LICENSE = "sync_license"

class BusinessUseStatus(Enum):
    """Business use permission status."""
    UNKNOWN = "unknown"
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    REQUIRES_LICENSE = "requires_license"

@dataclass
class LicenseInfo:
    """Licensing information for a music track."""
    license_type: LicenseType = LicenseType.UNKNOWN
    business_use_status: BusinessUseStatus = BusinessUseStatus.UNKNOWN
    copyright_holder: Optional[str] = None
    license_url: Optional[str] = None
    attribution_required: bool = False
    commercial_use_allowed: bool = False
    modification_allowed: bool = False
    distribution_allowed: bool = False
    youtube_content_id: Optional[bool] = None  # True if Content ID claimed
    copyright_claims: List[str] = None
    monetization_allowed: bool = False
    sync_rights_available: bool = False
    mechanical_rights_available: bool = False
    performance_rights_available: bool = False
    confidence_score: float = 0.0  # 0.0-1.0 confidence in licensing info
    last_checked: Optional[datetime] = None
    source: str = "unknown"  # Source of licensing information
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.copyright_claims is None:
            self.copyright_claims = []
        if self.last_checked is None:
            self.last_checked = datetime.utcnow()
    
    @property
    def business_use_allowed(self) -> bool:
        """Check if track is allowed for business use."""
        return (
            self.business_use_status == BusinessUseStatus.ALLOWED or
            (self.commercial_use_allowed and not self.youtube_content_id)
        )
    
    @property
    def requires_attribution(self) -> bool:
        """Check if attribution is required for use."""
        return self.attribution_required
    
    @property
    def has_copyright_claims(self) -> bool:
        """Check if track has any copyright claims."""
        return bool(self.copyright_claims) or self.youtube_content_id is True
    
    @property
    def licensing_summary(self) -> str:
        """Get a human-readable summary of licensing status."""
        if self.business_use_status == BusinessUseStatus.ALLOWED:
            return "✅ Business use allowed"
        elif self.business_use_status == BusinessUseStatus.RESTRICTED:
            return "⚠️ Business use restricted"
        elif self.business_use_status == BusinessUseStatus.PROHIBITED:
            return "❌ Business use prohibited"
        elif self.business_use_status == BusinessUseStatus.REQUIRES_LICENSE:
            return "📄 License required for business use"
        else:
            return "❓ Licensing status unknown"
    
    def update_youtube_status(self, content_id_claimed: bool, monetization_allowed: bool = False):
        """Update YouTube-specific licensing information."""
        self.youtube_content_id = content_id_claimed
        self.monetization_allowed = monetization_allowed
        self.last_checked = datetime.utcnow()
        
        # Update business use status based on YouTube info
        if content_id_claimed and not monetization_allowed:
            self.business_use_status = BusinessUseStatus.RESTRICTED
        elif not content_id_claimed:
            # No Content ID claim might indicate more permissive licensing
            if self.business_use_status == BusinessUseStatus.UNKNOWN:
                self.business_use_status = BusinessUseStatus.ALLOWED
    
    def add_copyright_claim(self, claim_info: str):
        """Add a copyright claim to the track."""
        if claim_info not in self.copyright_claims:
            self.copyright_claims.append(claim_info)
            self.last_checked = datetime.utcnow()
    
    def calculate_business_risk_score(self) -> float:
        """Calculate risk score for business use (0.0 = low risk, 1.0 = high risk)."""
        risk_score = 0.0
        
        # Base risk from business use status
        if self.business_use_status == BusinessUseStatus.PROHIBITED:
            risk_score += 0.8
        elif self.business_use_status == BusinessUseStatus.RESTRICTED:
            risk_score += 0.6
        elif self.business_use_status == BusinessUseStatus.REQUIRES_LICENSE:
            risk_score += 0.4
        elif self.business_use_status == BusinessUseStatus.UNKNOWN:
            risk_score += 0.3
        
        # Additional risk factors
        if self.youtube_content_id:
            risk_score += 0.2
        if self.copyright_claims:
            risk_score += 0.1 * len(self.copyright_claims)
        if not self.commercial_use_allowed:
            risk_score += 0.1
        
        # Reduce risk for positive indicators
        if self.license_type == LicenseType.CREATIVE_COMMONS:
            risk_score -= 0.2
        elif self.license_type == LicenseType.PUBLIC_DOMAIN:
            risk_score -= 0.4
        elif self.license_type == LicenseType.ROYALTY_FREE:
            risk_score -= 0.3
        
        # Factor in confidence score
        risk_score *= (1.0 - self.confidence_score * 0.2)
        
        return max(0.0, min(1.0, risk_score))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "license_type": self.license_type.value,
            "business_use_status": self.business_use_status.value,
            "copyright_holder": self.copyright_holder,
            "license_url": self.license_url,
            "attribution_required": self.attribution_required,
            "commercial_use_allowed": self.commercial_use_allowed,
            "modification_allowed": self.modification_allowed,
            "distribution_allowed": self.distribution_allowed,
            "youtube_content_id": self.youtube_content_id,
            "copyright_claims": self.copyright_claims,
            "monetization_allowed": self.monetization_allowed,
            "sync_rights_available": self.sync_rights_available,
            "mechanical_rights_available": self.mechanical_rights_available,
            "performance_rights_available": self.performance_rights_available,
            "confidence_score": self.confidence_score,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "source": self.source,
            "notes": self.notes,
            "business_use_allowed": self.business_use_allowed,
            "licensing_summary": self.licensing_summary,
            "business_risk_score": self.calculate_business_risk_score()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseInfo':
        """Create LicenseInfo from dictionary representation."""
        last_checked = None
        if data.get("last_checked"):
            last_checked = datetime.fromisoformat(data["last_checked"])
        
        return cls(
            license_type=LicenseType(data.get("license_type", "unknown")),
            business_use_status=BusinessUseStatus(data.get("business_use_status", "unknown")),
            copyright_holder=data.get("copyright_holder"),
            license_url=data.get("license_url"),
            attribution_required=data.get("attribution_required", False),
            commercial_use_allowed=data.get("commercial_use_allowed", False),
            modification_allowed=data.get("modification_allowed", False),
            distribution_allowed=data.get("distribution_allowed", False),
            youtube_content_id=data.get("youtube_content_id"),
            copyright_claims=data.get("copyright_claims", []),
            monetization_allowed=data.get("monetization_allowed", False),
            sync_rights_available=data.get("sync_rights_available", False),
            mechanical_rights_available=data.get("mechanical_rights_available", False),
            performance_rights_available=data.get("performance_rights_available", False),
            confidence_score=data.get("confidence_score", 0.0),
            last_checked=last_checked,
            source=data.get("source", "unknown"),
            notes=data.get("notes")
        )
    
    @classmethod
    def create_unknown(cls) -> 'LicenseInfo':
        """Create a LicenseInfo instance with unknown status."""
        return cls(
            license_type=LicenseType.UNKNOWN,
            business_use_status=BusinessUseStatus.UNKNOWN,
            confidence_score=0.0,
            source="unknown"
        )
    
    @classmethod
    def create_creative_commons(cls, attribution_required: bool = True, commercial_allowed: bool = True) -> 'LicenseInfo':
        """Create a Creative Commons license info."""
        return cls(
            license_type=LicenseType.CREATIVE_COMMONS,
            business_use_status=BusinessUseStatus.ALLOWED if commercial_allowed else BusinessUseStatus.RESTRICTED,
            attribution_required=attribution_required,
            commercial_use_allowed=commercial_allowed,
            modification_allowed=True,
            distribution_allowed=True,
            confidence_score=0.9,
            source="creative_commons"
        ) 