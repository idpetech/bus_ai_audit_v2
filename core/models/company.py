"""
Company profile models for structured intelligence
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

from .evidence import EvidenceItem, ConfidenceLevel


class TechnologyStack(BaseModel):
    """Structured representation of company's technology stack"""
    
    # Languages and frameworks
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)
    
    # AI/ML specific
    ai_ml_tools: List[str] = Field(default_factory=list)
    data_platforms: List[str] = Field(default_factory=list)
    
    # Evidence traceability
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence supporting each tech choice")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)


class BusinessModel(BaseModel):
    """Structured representation of business model"""
    
    # Core model
    model_type: str = Field(description="SaaS/Marketplace/E-commerce/etc")
    revenue_streams: List[str] = Field(default_factory=list)
    target_customers: List[str] = Field(default_factory=list)
    
    # Scale indicators
    customer_size: str = Field(description="Enterprise/SMB/Consumer/etc")
    transaction_volume_signals: List[str] = Field(default_factory=list)
    
    # Evidence traceability
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)


class OperationalSignals(BaseModel):
    """Signals about operational maturity and capabilities"""
    
    # Team signals
    headcount_estimate: Optional[str] = None
    engineering_team_size: Optional[str] = None
    hiring_velocity: List[str] = Field(default_factory=list)
    
    # Process maturity
    development_practices: List[str] = Field(default_factory=list)
    operational_maturity_signals: List[str] = Field(default_factory=list)
    
    # Funding and growth
    funding_stage: Optional[str] = None
    funding_amount: Optional[str] = None
    growth_indicators: List[str] = Field(default_factory=list)
    
    # Evidence traceability
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)


class PlatformSignals(BaseModel):
    """Technical platform and architecture signals"""
    
    # Architecture patterns
    architecture_keywords: List[str] = Field(default_factory=list)
    system_complexity_indicators: List[str] = Field(default_factory=list)
    data_flow_patterns: List[str] = Field(default_factory=list)
    
    # Scaling evidence
    performance_signals: List[str] = Field(default_factory=list)
    scalability_indicators: List[str] = Field(default_factory=list)
    
    # Integration patterns
    api_strategy: List[str] = Field(default_factory=list)
    third_party_integrations: List[str] = Field(default_factory=list)
    
    # Evidence traceability
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)


class CompanyProfile(BaseModel):
    """Complete structured company profile"""
    
    # Basic information
    company_name: str = Field(description="Official company name")
    website_url: str = Field(description="Primary website URL")
    industry: Optional[str] = None
    founded_year: Optional[str] = None
    
    # Structured components
    technology_stack: TechnologyStack = Field(default_factory=TechnologyStack)
    business_model: BusinessModel = Field(default_factory=BusinessModel)
    operational_signals: OperationalSignals = Field(default_factory=OperationalSignals)
    platform_signals: PlatformSignals = Field(default_factory=PlatformSignals)
    
    # Leadership and decision makers
    decision_makers: List[Dict] = Field(default_factory=list)
    key_personnel: List[Dict] = Field(default_factory=list)
    
    # Meta information
    profile_created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    profile_confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    
    # Raw source data (for debugging)
    source_urls: List[str] = Field(default_factory=list)
    extraction_notes: Optional[str] = None