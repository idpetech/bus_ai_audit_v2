"""
Close generation stage - consumes structured intelligence
"""

import logging
from typing import Dict
import openai

from ..models.intelligence import StructuredIntelligence

logger = logging.getLogger(__name__)


class StructuredCloser:
    """
    Refactored close generation that operates ONLY on structured intelligence.
    
    NO access to raw content. Close based on key contradictions and 
    architectural assessment from structured intelligence.
    """
    
    def __init__(self, openai_client: openai.OpenAI, prompts: Dict[str, str]):
        self.client = openai_client
        self.prompts = prompts
    
    def generate_close(self, intelligence: StructuredIntelligence, audit: str) -> str:
        """
        Generate conversation close from structured intelligence.
        
        Replaces old generate_close() that accessed raw signals.
        """
        
        system_prompt = self.prompts.get("generate_close", self._get_default_close_prompt())
        
        # Extract core architectural contradiction
        core_contradiction = self._extract_core_contradiction(intelligence)
        
        # Extract reality gap summary
        reality_gap = self._extract_reality_gap(intelligence)
        
        user_prompt = f"""Create close based on structured intelligence:

COMPANY: {intelligence.company_profile.company_name}

CORE ARCHITECTURAL CONTRADICTION:
{core_contradiction}

REALITY GAP:
{reality_gap}

AUDIT SUMMARY (key points):
{audit[:300]}...

EVIDENCE QUALITY: {intelligence.overall_confidence} confidence, {intelligence.data_quality_score}/10 quality

Focus on the most fundamental gap between perception and technical reality."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            
            close = response.choices[0].message.content
            logger.info("Structured close generated")
            return close
            
        except Exception as e:
            logger.error(f"Close generation failed: {e}")
            return f"Close generation failed: {str(e)}"
    
    def _extract_core_contradiction(self, intelligence: StructuredIntelligence) -> str:
        """Extract the most fundamental architectural contradiction"""
        if not intelligence.contradictions:
            return "No clear contradiction between stated vision and technical implementation."
        
        # Get the most severe contradiction
        contradictions = sorted(intelligence.contradictions, key=lambda x: x.severity.value, reverse=True)
        return contradictions[0].explanation
    
    def _extract_reality_gap(self, intelligence: StructuredIntelligence) -> str:
        """Extract summary of reality vs. perception gap"""
        ai_indicators = intelligence.ai_readiness_indicators
        constraints = intelligence.constraint_indicators
        
        if ai_indicators and constraints:
            ai_classification = ai_indicators[0].ai_classification
            critical_constraints = [c.constraint_type for c in constraints if c.severity.value == "HIGH"]
            
            if critical_constraints:
                return f"Claims {ai_classification} capabilities while facing {', '.join(critical_constraints)} constraints."
        
        return "Gap between technical aspirations and implementation reality."
    
    def _get_default_close_prompt(self) -> str:
        """Default close generation prompt"""
        return """You are a Senior Architect delivering a final technical observation.

Requirements:
- 2-3 sentences maximum
- Surface one core architectural contradiction from structured intelligence
- No questions, no offers, no next steps
- End with direct statement about reality vs. perception

Avoid: consulting language, encouragement, solutions, positive spin

Tone: Peer-level technical honesty. No sugar-coating.

Direct. Final. Architectural truth based on evidence."""