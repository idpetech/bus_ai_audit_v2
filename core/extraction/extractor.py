"""
Canonical extraction engine - single source of truth for structured intelligence
"""

import json
import logging
import hashlib
import time
import uuid
from typing import Dict, Any, List, Optional
import openai

from ..models import (
    StructuredIntelligence, 
    CompanyProfile,
    EvidenceItem,
    ContradictionCandidate,
    ModernizationSignal,
    AIReadinessIndicator,
    ConstraintIndicator,
    TechnologyStack,
    BusinessModel,
    OperationalSignals,
    PlatformSignals,
    ConfidenceLevel,
    EvidenceSource,
    EvidenceCategory,
    CompanyInputs
)
from .normalizer import EvidenceNormalizer
from .confidence import ConfidenceScorer

logger = logging.getLogger(__name__)


class StructuredExtractor:
    """
    Canonical extraction engine that creates single source of truth.
    
    Replaces the old extract_signals() method with comprehensive structured extraction.
    All downstream stages will consume the output of this extractor instead of raw content.
    """
    
    def __init__(self, openai_client: openai.OpenAI, prompts: Dict[str, str]):
        self.client = openai_client
        self.prompts = prompts
        self.normalizer = EvidenceNormalizer()
        self.confidence_scorer = ConfidenceScorer()
    
    def extract_structured_intelligence(self, inputs: CompanyInputs) -> StructuredIntelligence:
        """
        Main extraction method - creates canonical structured intelligence.
        
        This is the ONLY method that should access raw scraped content.
        All other pipeline stages consume the output of this method.
        """
        start_time = time.time()
        intelligence_id = f"intel_{hashlib.md5(inputs.target_url.encode()).hexdigest()[:8]}"
        
        logger.info(f"🔬 Starting canonical extraction for {inputs.company_name}")
        
        # Step 1: Extract raw evidence items
        evidence_items = self._extract_evidence_items(inputs)
        
        # Step 2: Normalize and deduplicate evidence
        normalized_evidence = self.normalizer.normalize_evidence(evidence_items)
        
        # Step 3: Build structured company profile
        company_profile = self._build_company_profile(normalized_evidence, inputs)
        
        # Step 4: Identify contradictions
        contradictions = self._identify_contradictions(normalized_evidence, inputs)
        
        # Step 5: Assess modernization signals
        modernization_signals = self._assess_modernization_signals(normalized_evidence)
        
        # Step 6: Evaluate AI readiness
        ai_readiness_indicators = self._evaluate_ai_readiness(normalized_evidence)
        
        # Step 7: Identify constraints
        constraint_indicators = self._identify_constraints(normalized_evidence)
        
        # Step 8: Score overall confidence and quality
        overall_confidence = self.confidence_scorer.score_overall_confidence(normalized_evidence)
        data_quality_score = self.confidence_scorer.score_data_quality(normalized_evidence)
        evidence_coverage = self._calculate_evidence_coverage(normalized_evidence)
        
        extraction_duration = time.time() - start_time
        
        # Create canonical intelligence object
        structured_intelligence = StructuredIntelligence(
            intelligence_id=intelligence_id,
            company_profile=company_profile,
            evidence_items=normalized_evidence,
            contradictions=contradictions,
            modernization_signals=modernization_signals,
            ai_readiness_indicators=ai_readiness_indicators,
            constraint_indicators=constraint_indicators,
            overall_confidence=overall_confidence,
            data_quality_score=data_quality_score,
            evidence_coverage=evidence_coverage,
            source_urls=self._extract_source_urls(inputs),
            extraction_duration_seconds=extraction_duration
        )
        
        logger.info(f"✅ Canonical extraction complete: {len(normalized_evidence)} evidence items, {len(contradictions)} contradictions")
        return structured_intelligence
    
    def _extract_evidence_items(self, inputs: CompanyInputs) -> List[EvidenceItem]:
        """Extract individual evidence items from all sources"""
        evidence_items = []
        
        # Extract from company website
        if inputs.scraped_content:
            website_evidence = self._extract_from_source(
                inputs.scraped_content,
                EvidenceSource.COMPANY_WEBSITE,
                inputs.target_url
            )
            evidence_items.extend(website_evidence)
        
        # Extract from job postings
        if inputs.job_posting:
            job_evidence = self._extract_from_source(
                inputs.job_posting,
                EvidenceSource.JOB_POSTING,
                None
            )
            evidence_items.extend(job_evidence)
        
        # Extract from external signals
        if inputs.external_signals:
            external_evidence = self._extract_from_source(
                inputs.external_signals,
                EvidenceSource.EXTERNAL_SEARCH,
                None
            )
            evidence_items.extend(external_evidence)
        
        return evidence_items
    
    def _extract_from_source(self, content: str, source: EvidenceSource, source_url: Optional[str]) -> List[EvidenceItem]:
        """Extract evidence items from a specific source"""
        
        system_prompt = """You are a structured evidence extraction engine. Extract individual factual claims from the provided content.

For each factual claim found, output a JSON object with:
{
  "claim": "specific factual statement",
  "evidence_text": "exact text supporting this claim", 
  "category": "TECH_STACK|BUSINESS_MODEL|SCALE_INDICATOR|AI_MENTION|ARCHITECTURE|DATA_FLOW|HIRING_PATTERN|FUNDING|LEADERSHIP|OPERATIONAL",
  "confidence": "HIGH|MEDIUM|LOW",
  "surrounding_context": "text around the evidence for context"
}

Return an array of these objects. Extract ONLY factual claims, not opinions or marketing language.
Focus on technical details, business model facts, team information, and concrete operational signals.

CRITICAL: Do NOT interpret or analyze. ONLY extract explicit factual statements."""

        user_prompt = f"Extract evidence from this {source.value} content:\n\n{content}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            raw_evidence = json.loads(response.choices[0].message.content)
            
            # Convert to EvidenceItem objects
            evidence_items = []
            for item in raw_evidence:
                evidence_item = EvidenceItem(
                    evidence_id=f"ev_{str(uuid.uuid4())[:8]}",
                    claim=item["claim"],
                    evidence_text=item["evidence_text"],
                    category=EvidenceCategory(item["category"]),
                    confidence=ConfidenceLevel(item["confidence"]),
                    source=source,
                    source_url=source_url,
                    surrounding_context=item.get("surrounding_context")
                )
                evidence_items.append(evidence_item)
            
            return evidence_items
            
        except Exception as e:
            logger.error(f"Failed to extract evidence from {source}: {e}")
            return []
    
    def _build_company_profile(self, evidence: List[EvidenceItem], inputs: CompanyInputs) -> CompanyProfile:
        """Build structured company profile from evidence"""
        
        # Extract tech stack evidence
        tech_evidence = [e for e in evidence if e.category == EvidenceCategory.TECH_STACK]
        tech_stack = self._build_tech_stack(tech_evidence)
        
        # Extract business model evidence  
        business_evidence = [e for e in evidence if e.category == EvidenceCategory.BUSINESS_MODEL]
        business_model = self._build_business_model(business_evidence)
        
        # Extract operational signals
        operational_evidence = [e for e in evidence if e.category in [EvidenceCategory.HIRING_PATTERN, EvidenceCategory.FUNDING, EvidenceCategory.OPERATIONAL]]
        operational_signals = self._build_operational_signals(operational_evidence)
        
        # Extract platform signals
        platform_evidence = [e for e in evidence if e.category in [EvidenceCategory.ARCHITECTURE, EvidenceCategory.DATA_FLOW, EvidenceCategory.SCALE_INDICATOR]]
        platform_signals = self._build_platform_signals(platform_evidence)
        
        return CompanyProfile(
            company_name=inputs.company_name or "Unknown",
            website_url=inputs.target_url,
            technology_stack=tech_stack,
            business_model=business_model,
            operational_signals=operational_signals,
            platform_signals=platform_signals,
            source_urls=self._extract_source_urls(inputs)
        )
    
    def _build_tech_stack(self, evidence: List[EvidenceItem]) -> TechnologyStack:
        """Build technology stack from evidence"""
        # Implementation would analyze evidence and extract structured tech stack
        # This is a simplified version
        return TechnologyStack(
            evidence_ids=[e.evidence_id for e in evidence],
            confidence=self.confidence_scorer.score_category_confidence(evidence)
        )
    
    def _build_business_model(self, evidence: List[EvidenceItem]) -> BusinessModel:
        """Build business model from evidence"""
        return BusinessModel(
            model_type="Unknown",  # Would be extracted from evidence
            customer_size="Unknown",  # Required field with default
            evidence_ids=[e.evidence_id for e in evidence],
            confidence=self.confidence_scorer.score_category_confidence(evidence)
        )
    
    def _build_operational_signals(self, evidence: List[EvidenceItem]) -> OperationalSignals:
        """Build operational signals from evidence"""
        return OperationalSignals(
            evidence_ids=[e.evidence_id for e in evidence],
            confidence=self.confidence_scorer.score_category_confidence(evidence)
        )
    
    def _build_platform_signals(self, evidence: List[EvidenceItem]) -> PlatformSignals:
        """Build platform signals from evidence"""
        return PlatformSignals(
            evidence_ids=[e.evidence_id for e in evidence],
            confidence=self.confidence_scorer.score_category_confidence(evidence)
        )
    
    def _identify_contradictions(self, evidence: List[EvidenceItem], inputs: CompanyInputs) -> List[ContradictionCandidate]:
        """Identify contradictions between company claims and external signals"""
        # Implementation would use LLM to identify contradictions
        # This is a placeholder
        return []
    
    def _assess_modernization_signals(self, evidence: List[EvidenceItem]) -> List[ModernizationSignal]:
        """Assess modernization signals from evidence"""
        # Implementation would analyze evidence for modernization indicators
        return []
    
    def _evaluate_ai_readiness(self, evidence: List[EvidenceItem]) -> List[AIReadinessIndicator]:
        """Evaluate AI readiness from evidence"""
        # Implementation would assess AI readiness based on evidence
        return []
    
    def _identify_constraints(self, evidence: List[EvidenceItem]) -> List[ConstraintIndicator]:
        """Identify system constraints from evidence"""
        # Implementation would identify constraints that will limit scaling
        return []
    
    def _calculate_evidence_coverage(self, evidence: List[EvidenceItem]) -> Dict[str, int]:
        """Calculate evidence coverage by category"""
        coverage = {}
        for item in evidence:
            category = item.category.value
            coverage[category] = coverage.get(category, 0) + 1
        return coverage
    
    def _extract_source_urls(self, inputs: CompanyInputs) -> List[str]:
        """Extract all source URLs"""
        urls = [inputs.target_url]
        # Could extract additional URLs from external signals
        return list(set(urls))  # Deduplicate