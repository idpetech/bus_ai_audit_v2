"""
Data models for BA Assistant
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class CompanyInputs:
    target_url: str                          # Primary company website URL
    job_posting: Optional[str] = None        # Optional job posting text
    scraped_content: Optional[str] = None    # Scraped company narrative/self-perception
    external_signals: Optional[str] = None  # External signals from search
    company_name: Optional[str] = None       # Extracted company name
    
    @property
    def combined_context(self) -> str:
        """Combine scraped content and external signals for analysis."""
        context_parts = []
        if self.scraped_content:
            context_parts.append(f"Company Self-Perception (from {self.target_url}):\n{self.scraped_content}")
        if self.external_signals:
            context_parts.append(f"External Signals:\n{self.external_signals}")
        if self.job_posting:
            context_parts.append(f"Job Posting:\n{self.job_posting}")
        return "\n\n".join(context_parts)


# Agent stage constants
AGENT_STAGES = [
    "IDLE",
    "RESEARCHING", 
    "ICP_DECISION",
    "AWAITING_CONFIRM",
    "RUNNING_PIPELINE",
    "COMPLETE",
    "DISQUALIFIED"
]


@dataclass
class PipelineResults:
    signals: Dict[str, Any]
    diagnosis: str
    hook: str
    audit: str
    close: str


@dataclass
class ResearchSummary:
    company_name: str
    official_website: str
    funding_stage: str
    funding_amount: str
    headcount_estimate: str
    founded_year: str
    decision_maker_name: str
    decision_maker_title: str
    decision_maker_linkedin: str
    decision_maker_confidence: str
    news_signals: List[str]
    research_sources: List[str]
    research_log: List[str]
    research_duration_seconds: float
    job_signals: str
    scraped_content: str
    # Company disambiguation fields (backward compatible)
    company_description_full: str = ""   # Full scraped description from homepage
    company_description_short: str = ""  # Short 5-word anchor for searches (e.g. "logistics platform")
    # Legacy field (deprecated but kept for compatibility)
    company_description: str = ""        # Maps to company_description_short
    # Acquisition status fields (backward compatible)
    acquisition_status: str = "UNKNOWN"  # "INDEPENDENT" / "ACQUIRED" / "UNKNOWN"  
    parent_company: str = ""             # Empty if independent
    acquisition_year: str = ""           # Empty if not acquired


@dataclass
class ICPResult:
    score: str            # HOT / WARM / COLD
    decision: str         # FIT / DISQUALIFIED
    confidence: str       # HIGH / MEDIUM / LOW
    
    # Clear human-readable explanation
    explanation: str
    
    # Specific disqualifiers if not fit
    disqualifiers: List[str]
    
    # Why it IS a fit if fit
    fit_reasons: List[str]
    
    # Firecrawl cost warning if proceeding
    estimated_credits: int
    
    # Alternative companies if disqualified
    alternatives: List[Dict]
    # Each alternative:
    # {
    #   "company_name": str,
    #   "reason": str,  # why better fit
    #   "search_term": str  # what to search
    # }