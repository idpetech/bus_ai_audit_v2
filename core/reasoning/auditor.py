"""
Audit generation stage - consumes structured intelligence
"""

import json
import logging
from typing import Dict
import openai

from ..models.intelligence import StructuredIntelligence
from ..models.evidence import ConfidenceLevel

logger = logging.getLogger(__name__)


class StructuredAuditor:
    """
    Refactored audit generation that operates ONLY on structured intelligence.
    
    NO access to raw content. All audit analysis based on evidence items,
    constraints, and AI readiness indicators.
    """
    
    def __init__(self, openai_client: openai.OpenAI, prompts: Dict[str, str]):
        self.client = openai_client
        self.prompts = prompts
    
    def generate_audit(self, intelligence: StructuredIntelligence, diagnosis: str) -> str:
        """
        Generate structured audit report from intelligence.
        
        Replaces old generate_audit() that accessed raw signals.
        """
        
        system_prompt = self.prompts.get("generate_audit", self._get_default_audit_prompt())
        
        # Build structured audit context
        audit_context = self._build_audit_context(intelligence)
        
        user_prompt = f"""Generate AI readiness audit using structured intelligence:

COMPANY PROFILE:
{intelligence.company_profile.model_dump_json(indent=2)}

STRUCTURED AUDIT CONTEXT:
{audit_context}

ARCHITECTURAL DIAGNOSIS:
{diagnosis}

EVIDENCE QUALITY METRICS:
- Total evidence items: {len(intelligence.evidence_items)}
- High confidence: {len(intelligence.get_high_confidence_evidence())}
- Data quality score: {intelligence.data_quality_score}/10
- Overall confidence: {intelligence.overall_confidence}

All assessments must reference specific evidence IDs and confidence levels.
Focus on failure modes and architectural realities."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            
            audit = response.choices[0].message.content
            logger.info("Structured audit generated")
            return audit
            
        except Exception as e:
            logger.error(f"Audit generation failed: {e}")
            return f"Audit generation failed: {str(e)}"
    
    def _build_audit_context(self, intelligence: StructuredIntelligence) -> str:
        """Build comprehensive audit context from structured intelligence"""
        
        context_parts = []
        
        # AI Readiness Summary
        context_parts.append("AI READINESS INDICATORS:")
        if intelligence.ai_readiness_indicators:
            for indicator in intelligence.ai_readiness_indicators:
                context_parts.append(f"• {indicator.ai_classification} (Score: {indicator.readiness_score}/10)")
                context_parts.append(f"  Evidence: {', '.join(indicator.supporting_evidence_ids)}")
                if indicator.blocking_factors:
                    context_parts.append(f"  Blockers: {', '.join(indicator.blocking_factors)}")
        else:
            context_parts.append("• Assessment pending - insufficient evidence")
        
        context_parts.append("")
        
        # Critical Constraints
        context_parts.append("CRITICAL CONSTRAINTS:")
        critical_constraints = [c for c in intelligence.constraint_indicators if c.severity == ConfidenceLevel.HIGH]
        if critical_constraints:
            for constraint in critical_constraints:
                context_parts.append(f"• {constraint.constraint_type}: {constraint.breaking_point}")
                context_parts.append(f"  Failure mode: {constraint.failure_mode_prediction}")
                context_parts.append(f"  Evidence: {', '.join(constraint.supporting_evidence_ids)}")
        else:
            context_parts.append("• No high-severity constraints identified")
        
        context_parts.append("")
        
        # Modernization Status
        context_parts.append("MODERNIZATION SIGNALS:")
        if intelligence.modernization_signals:
            for signal in intelligence.modernization_signals:
                context_parts.append(f"• {signal.modernization_stage}: {signal.ai_readiness_impact}")
                context_parts.append(f"  Technical debt: {', '.join(signal.technical_debt_indicators)}")
                context_parts.append(f"  Evidence: {', '.join(signal.supporting_evidence_ids)}")
        else:
            context_parts.append("• Modernization assessment pending")
        
        context_parts.append("")
        
        # Top Contradictions
        context_parts.append("KEY CONTRADICTIONS:")
        high_severity_contradictions = intelligence.get_contradictions_by_severity(ConfidenceLevel.HIGH)
        if high_severity_contradictions:
            for contradiction in high_severity_contradictions:
                context_parts.append(f"• {contradiction.explanation}")
                context_parts.append(f"  Evidence conflict: {contradiction.claim_evidence_id} vs {contradiction.reality_evidence_id}")
        else:
            context_parts.append("• No high-severity contradictions identified")
        
        return "\n".join(context_parts)
    
    def _get_default_audit_prompt(self) -> str:
        """Default audit generation prompt"""
        return """You are a Senior Principal Architect conducting a technical assessment based on structured intelligence.

# AI Readiness Audit

## Executive Summary
- Current AI Classification: [Based on AI readiness indicators]
- Reality Gap Score: X/10 (evidence quality and contradictions)
- Primary Constraint: [From constraint analysis]

## System Reality  
[Based on structured company profile vs evidence contradictions]

## Architectural Constraint Analysis
**Data Architecture:** [From platform signals and evidence]
**Infrastructure Reality:** [From technology stack analysis]
**Team Technical Debt:** [From operational signals and modernization indicators]  
**Legacy System Constraints:** [From constraint indicators]
**Operational Maturity Gaps:** [From operational signals]

## Failure Mode Predictions
[Based on constraint indicators and their failure mode predictions]

## Contrarian Technical Assessment
**What consultants are telling them:** [Inferred from AI readiness indicators]
**Architectural reality:** [From evidence contradictions]
**The technical bet:** [From constraint analysis]

## Mechanism-Based Interventions
[Concrete recommendations based on specific constraint indicators]

All conclusions must reference evidence IDs. Focus on architectural realities."""