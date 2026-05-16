"""
Core structured intelligence models - the canonical intelligence layer
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .evidence import (
    EvidenceItem, 
    ContradictionCandidate, 
    ModernizationSignal, 
    AIReadinessIndicator,
    ConstraintIndicator,
    ConfidenceLevel
)
from .company import CompanyProfile


class StructuredIntelligence(BaseModel):
    """
    Canonical structured intelligence object - single source of truth
    
    This is the core data structure that all reasoning stages consume.
    It replaces direct access to raw scraped content.
    """
    
    # Meta information
    intelligence_id: str = Field(description="Unique intelligence identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_version: str = Field(default="1.0", description="Version of extraction logic used")
    
    # Company profile (structured facts)
    company_profile: CompanyProfile = Field(description="Structured company information")
    
    # Evidence base (raw facts with traceability) 
    evidence_items: List[EvidenceItem] = Field(description="All extracted evidence items")
    
    # Analysis layers
    contradictions: List[ContradictionCandidate] = Field(description="Identified contradictions")
    modernization_signals: List[ModernizationSignal] = Field(description="Modernization assessment")
    ai_readiness_indicators: List[AIReadinessIndicator] = Field(description="AI readiness assessment")
    constraint_indicators: List[ConstraintIndicator] = Field(description="System constraints")
    
    # Summary assessments (computed from evidence)
    overall_confidence: ConfidenceLevel = Field(description="Overall confidence in intelligence")
    data_quality_score: float = Field(ge=0.0, le=10.0, description="Quality of underlying data")
    evidence_coverage: Dict[str, int] = Field(description="Count of evidence by category")
    
    # Source tracking
    source_urls: List[str] = Field(description="All source URLs used")
    extraction_duration_seconds: float = Field(description="Time taken for extraction")
    
    def get_evidence_by_category(self, category: str) -> List[EvidenceItem]:
        """Get all evidence items of a specific category"""
        return [item for item in self.evidence_items if item.category == category]
    
    def get_evidence_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        """Get specific evidence item by ID"""
        return next((item for item in self.evidence_items if item.evidence_id == evidence_id), None)
    
    def get_high_confidence_evidence(self) -> List[EvidenceItem]:
        """Get only high confidence evidence items"""
        return [item for item in self.evidence_items if item.confidence == ConfidenceLevel.HIGH]
    
    def get_contradictions_by_severity(self, severity: ConfidenceLevel) -> List[ContradictionCandidate]:
        """Get contradictions of specific severity"""
        return [c for c in self.contradictions if c.severity == severity]
    
    def to_reasoning_context(self) -> Dict[str, Any]:
        """
        Convert to context object for reasoning stages.
        
        This replaces the raw scraped content that stages used to receive.
        """
        return {
            "company_profile": self.company_profile.model_dump(),
            "evidence_summary": {
                "total_evidence_items": len(self.evidence_items),
                "high_confidence_items": len(self.get_high_confidence_evidence()),
                "evidence_by_category": self.evidence_coverage
            },
            "key_contradictions": [c.explanation for c in self.get_contradictions_by_severity(ConfidenceLevel.HIGH)],
            "ai_readiness_summary": {
                "indicators": [ai.ai_classification for ai in self.ai_readiness_indicators],
                "average_score": sum(ai.readiness_score for ai in self.ai_readiness_indicators) / len(self.ai_readiness_indicators) if self.ai_readiness_indicators else 0
            },
            "critical_constraints": [c.constraint_type for c in self.constraint_indicators if c.severity == ConfidenceLevel.HIGH],
            "data_quality": {
                "overall_confidence": self.overall_confidence,
                "data_quality_score": self.data_quality_score
            }
        }
    
    def to_json_compatible(self) -> Dict[str, Any]:
        """Convert to JSON-compatible format for persistence"""
        return self.model_dump()
    
    @classmethod
    def from_json_compatible(cls, data: Dict[str, Any]) -> 'StructuredIntelligence':
        """Create from JSON-compatible format"""
        return cls(**data)