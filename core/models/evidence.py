"""
Evidence and fact models for structured intelligence
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ConfidenceLevel(str, Enum):
    """Confidence levels for evidence items"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM" 
    LOW = "LOW"


class EvidenceSource(str, Enum):
    """Sources of evidence"""
    COMPANY_WEBSITE = "COMPANY_WEBSITE"
    JOB_POSTING = "JOB_POSTING"
    EXTERNAL_SEARCH = "EXTERNAL_SEARCH"
    NEWS_ARTICLE = "NEWS_ARTICLE"
    LINKEDIN = "LINKEDIN"
    CRUNCHBASE = "CRUNCHBASE"
    GLASSDOOR = "GLASSDOOR"
    GITHUB = "GITHUB"


class EvidenceCategory(str, Enum):
    """Categories of evidence"""
    TECH_STACK = "TECH_STACK"
    BUSINESS_MODEL = "BUSINESS_MODEL"
    SCALE_INDICATOR = "SCALE_INDICATOR" 
    AI_MENTION = "AI_MENTION"
    ARCHITECTURE = "ARCHITECTURE"
    DATA_FLOW = "DATA_FLOW"
    HIRING_PATTERN = "HIRING_PATTERN"
    FUNDING = "FUNDING"
    LEADERSHIP = "LEADERSHIP"
    OPERATIONAL = "OPERATIONAL"


class EvidenceItem(BaseModel):
    """Single piece of extracted evidence with full traceability"""
    
    # Unique identifier
    evidence_id: str = Field(description="Unique evidence identifier")
    
    # Core content
    claim: str = Field(description="The factual claim being made")
    evidence_text: str = Field(description="Original text supporting this claim")
    
    # Classification
    category: EvidenceCategory = Field(description="Category of evidence")
    confidence: ConfidenceLevel = Field(description="Confidence in this evidence")
    
    # Traceability
    source: EvidenceSource = Field(description="Where this evidence came from")
    source_url: Optional[str] = Field(default=None, description="Specific URL if available")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    surrounding_context: Optional[str] = Field(default=None, description="Text around the evidence")
    normalization_notes: Optional[str] = Field(default=None, description="Any normalization applied")


class ContradictionCandidate(BaseModel):
    """Potential contradiction between evidence items"""
    
    contradiction_id: str = Field(description="Unique contradiction identifier")
    
    # Evidence in conflict
    claim_evidence_id: str = Field(description="Evidence ID for company claim")
    reality_evidence_id: str = Field(description="Evidence ID for contradicting reality")
    
    # Analysis
    contradiction_type: str = Field(description="Type of contradiction (e.g., 'tech_stack_mismatch')")
    severity: ConfidenceLevel = Field(description="How severe is this contradiction")
    explanation: str = Field(description="Human-readable explanation of the contradiction")


class ModernizationSignal(BaseModel):
    """Signal indicating modernization efforts or technical debt"""
    
    signal_id: str = Field(description="Unique signal identifier")
    signal_type: str = Field(description="Type of modernization signal")
    
    # Evidence
    supporting_evidence_ids: List[str] = Field(description="Evidence items supporting this signal")
    
    # Assessment
    modernization_stage: str = Field(description="Where they are in modernization (legacy/transitioning/modern)")
    technical_debt_indicators: List[str] = Field(description="Specific technical debt signals")
    ai_readiness_impact: str = Field(description="How this affects AI implementation readiness")


class AIReadinessIndicator(BaseModel):
    """Indicator of AI implementation readiness"""
    
    indicator_id: str = Field(description="Unique indicator identifier")
    readiness_type: str = Field(description="Type of readiness indicator")
    
    # Classification
    ai_classification: str = Field(description="AI-Washed/AI-Assisted/AI-Native/Non-AI")
    readiness_score: float = Field(ge=0.0, le=10.0, description="Readiness score 0-10")
    
    # Evidence
    supporting_evidence_ids: List[str] = Field(description="Evidence items supporting this assessment")
    blocking_factors: List[str] = Field(description="Factors blocking AI implementation")
    enablers: List[str] = Field(description="Factors enabling AI implementation")


class ConstraintIndicator(BaseModel):
    """System constraint that will impact scaling"""
    
    constraint_id: str = Field(description="Unique constraint identifier")
    constraint_type: str = Field(description="Type of constraint (data/infrastructure/team/legacy)")
    
    # Impact
    severity: ConfidenceLevel = Field(description="How severe is this constraint")
    breaking_point: str = Field(description="When/how this constraint will cause failure")
    
    # Evidence
    supporting_evidence_ids: List[str] = Field(description="Evidence items supporting this constraint")
    failure_mode_prediction: str = Field(description="Specific prediction of how this will break")