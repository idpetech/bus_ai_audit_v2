"""
Hook generation stage - consumes structured intelligence
"""

import json
import logging
from typing import Dict
import openai

from ..models.intelligence import StructuredIntelligence

logger = logging.getLogger(__name__)


class StructuredHookGenerator:
    """
    Refactored hook generation that operates ONLY on structured intelligence.
    
    NO access to raw content. All hook generation based on evidence items,
    contradictions, and structured diagnosis.
    """
    
    def __init__(self, openai_client: openai.OpenAI, prompts: Dict[str, str]):
        self.client = openai_client
        self.prompts = prompts
    
    def generate_hook(self, intelligence: StructuredIntelligence, diagnosis: str) -> str:
        """
        Generate founder-facing hook from structured intelligence.
        
        Replaces old generate_hook() that accessed raw signals.
        """
        
        system_prompt = self.prompts.get("generate_hook", self._get_default_hook_prompt())
        
        # Extract key contradiction for hook
        key_contradiction = self._identify_key_contradiction(intelligence)
        
        # Extract technical tension
        technical_tension = self._extract_technical_tension(intelligence)
        
        user_prompt = f"""Create hook message based on structured intelligence:

COMPANY: {intelligence.company_profile.company_name}

KEY TECHNICAL CONTRADICTION:
{key_contradiction}

TECHNICAL TENSION:
{technical_tension}

DIAGNOSIS SUMMARY:
{diagnosis[:500]}...

EVIDENCE QUALITY: {intelligence.data_quality_score}/10 ({intelligence.overall_confidence})

Focus on the most compelling architectural contradiction with specific technical details."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            
            hook = response.choices[0].message.content
            logger.info("Structured hook generated")
            return hook
            
        except Exception as e:
            logger.error(f"Hook generation failed: {e}")
            return f"Hook generation failed: {str(e)}"
    
    def _identify_key_contradiction(self, intelligence: StructuredIntelligence) -> str:
        """Identify the most compelling contradiction for the hook"""
        if not intelligence.contradictions:
            return "No direct contradictions identified between claims and technical reality."
        
        # Get the highest severity contradiction
        contradictions = sorted(intelligence.contradictions, key=lambda x: x.severity.value, reverse=True)
        top_contradiction = contradictions[0]
        
        return f"{top_contradiction.explanation} (Evidence: {top_contradiction.claim_evidence_id} vs {top_contradiction.reality_evidence_id})"
    
    def _extract_technical_tension(self, intelligence: StructuredIntelligence) -> str:
        """Extract technical tension between stack and claims"""
        tech_stack = intelligence.company_profile.technology_stack
        ai_indicators = intelligence.ai_readiness_indicators
        
        if ai_indicators:
            ai_classification = ai_indicators[0].ai_classification
            return f"Claims {ai_classification} capabilities while technical evidence suggests different reality."
        
        return "Technical implementation appears misaligned with stated capabilities."
    
    def _get_default_hook_prompt(self) -> str:
        """Default hook generation prompt"""
        return """You are a Senior Principal Architect reaching out peer-to-peer.

REQUIREMENTS:
- 2-4 sentences maximum
- Lead with specific technical contradiction from structured intelligence
- Frame as architectural curiosity, not accusation  
- Reference concrete evidence (not generic observations)
- End with direct technical question

TONE: Senior technical peer. Skeptical but respectful.

AVOID:
- Introductions ("I noticed", "Hi", "Hope you're well")
- Buzzwords (scale, optimize, leverage, unlock, transform)
- Generic AI statements
- Sales language

FORMULA:
[Specific technical observation] + [Evidence-based contradiction] + [Direct question]

Start immediately with the technical tension. No preamble."""