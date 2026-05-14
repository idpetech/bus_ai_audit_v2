"""
Data models for BA Assistant
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


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


@dataclass
class PipelineResults:
    signals: Dict[str, Any]
    diagnosis: str
    hook: str
    audit: str
    close: str