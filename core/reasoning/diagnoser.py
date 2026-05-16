"""
Diagnosis stage - consumes structured intelligence instead of raw content
"""

import json
import logging
from typing import Dict, Any
import openai

from ..models.intelligence import StructuredIntelligence
from ..models.evidence import ConfidenceLevel

logger = logging.getLogger(__name__)


class StructuredDiagnoser:
    """
    Refactored diagnosis stage that operates ONLY on structured intelligence.
    
    NO direct access to raw scraped content. All analysis based on 
    evidence items and structured company profile.
    """
    
    def __init__(self, openai_client: openai.OpenAI, prompts: Dict[str, str]):
        self.client = openai_client
        self.prompts = prompts
    
    def diagnose(self, intelligence: StructuredIntelligence) -> str:
        """
        Generate architectural diagnosis from structured intelligence.
        
        Replaces the old diagnose() method that accessed raw content.
        """
        
        system_prompt = self.prompts.get("diagnose", self._get_default_diagnosis_prompt())
        
        # Convert structured intelligence to reasoning context
        reasoning_context = self._build_reasoning_context(intelligence)
        
        user_prompt = f"""Perform architectural reality check using structured intelligence:

COMPANY PROFILE:
{intelligence.company_profile.model_dump_json(indent=2)}

KEY EVIDENCE SUMMARY:
- Total evidence items: {len(intelligence.evidence_items)}
- High confidence evidence: {len(intelligence.get_high_confidence_evidence())}
- Evidence quality score: {intelligence.data_quality_score}/10

CRITICAL CONTRADICTIONS:
{self._format_contradictions(intelligence)}

AI READINESS ASSESSMENT:
{self._format_ai_readiness(intelligence)}

SYSTEM CONSTRAINTS:
{self._format_constraints(intelligence)}

MODERNIZATION SIGNALS:
{self._format_modernization(intelligence)}

FOCUS: Use the structured evidence to expose gaps between company claims and technical reality.
All conclusions must reference specific evidence items by ID.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            
            diagnosis = response.choices[0].message.content
            logger.info("Structured diagnosis completed")
            return diagnosis
            
        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            return f"Diagnosis failed: {str(e)}"
    
    def _build_reasoning_context(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """Build reasoning context from structured intelligence"""
        return intelligence.to_reasoning_context()
    
    def _format_contradictions(self, intelligence: StructuredIntelligence) -> str:
        """Format contradictions for diagnosis"""
        if not intelligence.contradictions:
            return "No significant contradictions identified."
        
        lines = []
        for contradiction in intelligence.contradictions:
            lines.append(f"• {contradiction.explanation} (Severity: {contradiction.severity})")
            lines.append(f"  Evidence IDs: {contradiction.claim_evidence_id} vs {contradiction.reality_evidence_id}")
        
        return "\n".join(lines)
    
    def _format_ai_readiness(self, intelligence: StructuredIntelligence) -> str:
        """Format AI readiness indicators"""
        if not intelligence.ai_readiness_indicators:
            return "AI readiness assessment pending detailed analysis."
        
        lines = []
        for indicator in intelligence.ai_readiness_indicators:
            lines.append(f"• {indicator.ai_classification} (Score: {indicator.readiness_score}/10)")
            if indicator.blocking_factors:
                lines.append(f"  Blockers: {', '.join(indicator.blocking_factors)}")
        
        return "\n".join(lines)
    
    def _format_constraints(self, intelligence: StructuredIntelligence) -> str:
        """Format system constraints"""
        if not intelligence.constraint_indicators:
            return "System constraint analysis pending."
        
        lines = []
        critical_constraints = [c for c in intelligence.constraint_indicators if c.severity == ConfidenceLevel.HIGH]
        
        for constraint in critical_constraints:
            lines.append(f"• {constraint.constraint_type}: {constraint.breaking_point}")
            lines.append(f"  Failure mode: {constraint.failure_mode_prediction}")
        
        return "\n".join(lines) if lines else "No critical constraints identified."
    
    def _format_modernization(self, intelligence: StructuredIntelligence) -> str:
        """Format modernization signals"""
        if not intelligence.modernization_signals:
            return "Modernization assessment pending."
        
        lines = []
        for signal in intelligence.modernization_signals:
            lines.append(f"• {signal.modernization_stage}: {signal.ai_readiness_impact}")
        
        return "\n".join(lines)
    
    def _get_default_diagnosis_prompt(self) -> str:
        """Default diagnosis prompt for structured intelligence"""
        return """You are a Senior Principal Architect analyzing structured company intelligence.

CRITICAL: All conclusions must reference specific evidence IDs from the structured intelligence.

REQUIRED OUTPUT STRUCTURE:

**What They Think They're Building:**
[Based on company profile and self-perception evidence]

**What They're Actually Building:**  
[Based on external evidence and contradiction analysis]

**The Architectural Gap:**
[Specific contradictions with evidence ID references]

**System Failure Modes:**
[Based on constraint indicators and evidence]

**Breaking Points at 10x Scale:**
[Based on platform signals and constraint analysis]

**AI Implementation Reality:**
[Based on AI readiness indicators - AI-Washed/AI-Assisted/AI-Native/Non-AI]

**Technical Classification Evidence:**
[Reference specific evidence IDs that support your classification]

Be brutally honest. Reference evidence IDs. Focus on architectural reality."""