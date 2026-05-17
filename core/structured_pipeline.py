"""
Refactored "Extract Once, Analyze Many" pipeline orchestrator
"""

import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

import openai

# Import from original models.py to avoid circular imports
from .models import CompanyInputs, PipelineResults

from .models.intelligence import StructuredIntelligence
from .extraction import StructuredExtractor
from .reasoning import StructuredDiagnoser, StructuredHookGenerator, StructuredAuditor, StructuredCloser
from .intelligence import IntelligenceSerializer

if TYPE_CHECKING:
    from .database import DatabaseManager

logger = logging.getLogger(__name__)


class StructuredBAAssistant:
    """
    Refactored BA Assistant implementing "Extract Once, Analyze Many" architecture.
    
    CRITICAL CHANGES:
    - Single structured extraction creates canonical intelligence
    - All reasoning stages consume structured intelligence (no raw content access)
    - Evidence traceability throughout pipeline
    - Eliminates token duplication and reasoning drift
    - Maintains backward compatibility with existing interfaces
    """
    
    def __init__(self, api_key: str, prompts: Dict[str, str] = None):
        self.client = openai.OpenAI(api_key=api_key)
        self.prompts = prompts or self._load_prompts()
        
        # Initialize structured pipeline components
        self.extractor = StructuredExtractor(self.client, self.prompts)
        self.diagnoser = StructuredDiagnoser(self.client, self.prompts)
        self.hook_generator = StructuredHookGenerator(self.client, self.prompts)
        self.auditor = StructuredAuditor(self.client, self.prompts)
        self.closer = StructuredCloser(self.client, self.prompts)
        self.serializer = IntelligenceSerializer()
        
        # Cache for structured intelligence
        self.intelligence_cache = {}
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts (reuse existing logic)"""
        # Import existing logic from original pipeline
        from .pipeline import BAAssistant
        temp_assistant = BAAssistant("dummy")
        return temp_assistant._get_default_prompts()
    
    def extract_structured_intelligence(self, inputs: CompanyInputs) -> StructuredIntelligence:
        """
        STEP 1: Extract structured intelligence - single source of truth.
        
        This is the ONLY stage that accesses raw scraped content.
        Returns canonical intelligence that all other stages consume.
        """
        cache_key = self._get_cache_key(inputs)
        
        if cache_key in self.intelligence_cache:
            logger.info("Returning cached structured intelligence")
            return self.intelligence_cache[cache_key]
        
        logger.info("🔬 EXTRACTION: Creating canonical structured intelligence...")
        intelligence = self.extractor.extract_structured_intelligence(inputs)
        
        # Cache the structured intelligence
        self.intelligence_cache[cache_key] = intelligence
        
        logger.info(f"✅ EXTRACTION COMPLETE: {len(intelligence.evidence_items)} evidence items, quality={intelligence.data_quality_score}/10")
        return intelligence
    
    def run_structured_pipeline(self, inputs: CompanyInputs) -> tuple[StructuredIntelligence, PipelineResults]:
        """
        Execute the complete "Extract Once, Analyze Many" pipeline.
        
        Returns both the structured intelligence and traditional pipeline results
        for backward compatibility.
        """
        
        # STEP 1: Extract Once - Create canonical intelligence
        intelligence = self.extract_structured_intelligence(inputs)
        
        # STEP 2: Analyze Many - All stages consume structured intelligence
        
        # Stage 2: Diagnose (no raw content access)
        logger.info("🔄 DIAGNOSIS: Analyzing structured intelligence...")
        diagnosis = self.diagnoser.diagnose(intelligence)
        
        # Wait for TPM management
        logger.info("⏳ TPM management wait...")
        time.sleep(8)
        
        # Stage 3: Generate hook (no raw content access)
        logger.info("🔄 HOOK: Generating from structured intelligence...")
        hook = self.hook_generator.generate_hook(intelligence, diagnosis)
        
        # Stage 4: Generate audit (no raw content access)
        logger.info("🔄 AUDIT: Building from structured intelligence...")
        audit = self.auditor.generate_audit(intelligence, diagnosis)
        
        # Stage 5: Generate close (no raw content access)
        logger.info("🔄 CLOSE: Finalizing from structured intelligence...")
        close = self.closer.generate_close(intelligence, audit)
        
        # Create backward-compatible results
        results = PipelineResults(
            signals=self._convert_intelligence_to_legacy_signals(intelligence),
            diagnosis=diagnosis,
            hook=hook,
            audit=audit,
            close=close
        )
        
        logger.info("✅ STRUCTURED PIPELINE COMPLETE")
        return intelligence, results
    
    def run_full_pipeline(self, inputs: CompanyInputs) -> PipelineResults:
        """
        Backward compatibility method - returns traditional PipelineResults.
        
        Maintains compatibility with existing code while using new architecture.
        """
        intelligence, results = self.run_structured_pipeline(inputs)
        return results
    
    def get_structured_intelligence(self, inputs: CompanyInputs) -> StructuredIntelligence:
        """
        Get structured intelligence for advanced analysis.
        
        New method for accessing canonical intelligence directly.
        """
        return self.extract_structured_intelligence(inputs)
    
    def save_intelligence(self, intelligence: StructuredIntelligence, filename: str = None) -> str:
        """Save structured intelligence to JSON file"""
        return self.serializer.save_to_file(intelligence, filename)
    
    def load_intelligence(self, filename: str) -> StructuredIntelligence:
        """Load structured intelligence from JSON file"""
        return self.serializer.load_from_file(filename)
    
    def get_evidence_summary(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """Get summary of evidence for debugging/analysis"""
        return {
            "total_evidence": len(intelligence.evidence_items),
            "evidence_by_category": intelligence.evidence_coverage,
            "high_confidence_evidence": len(intelligence.get_high_confidence_evidence()),
            "contradictions": len(intelligence.contradictions),
            "data_quality_score": intelligence.data_quality_score,
            "overall_confidence": intelligence.overall_confidence.value
        }
    
    def _get_cache_key(self, inputs: CompanyInputs) -> str:
        """Generate cache key (reuse existing logic)"""
        import hashlib
        combined = f"{inputs.target_url}{inputs.job_posting or ''}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _convert_intelligence_to_legacy_signals(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """Convert structured intelligence to legacy signals format for compatibility"""
        return self.serializer._convert_evidence_to_legacy_signals(intelligence)
    
    # Legacy method compatibility
    def extract_signals(self, inputs: CompanyInputs) -> Dict[str, Any]:
        """Legacy compatibility - extract signals in old format"""
        intelligence = self.extract_structured_intelligence(inputs)
        return self._convert_intelligence_to_legacy_signals(intelligence)
    
    def diagnose(self, signals: Dict[str, Any], inputs: CompanyInputs) -> str:
        """Legacy compatibility - diagnose from signals"""
        # For legacy calls, we need to re-extract intelligence since signals don't contain full context
        intelligence = self.extract_structured_intelligence(inputs)
        return self.diagnoser.diagnose(intelligence)
    
    def generate_hook(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Legacy compatibility - generate hook from signals"""
        logger.warning("Legacy hook generation called - limited context available")
        return "Hook generation requires structured intelligence context for optimal results."
    
    def generate_audit(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Legacy compatibility - generate audit from signals"""
        logger.warning("Legacy audit generation called - limited context available")
        return "Audit generation requires structured intelligence context for optimal results."
    
    def generate_close(self, signals: Dict[str, Any], audit: str) -> str:
        """Legacy compatibility - generate close from signals"""
        logger.warning("Legacy close generation called - limited context available")
        return "Close generation requires structured intelligence context for optimal results."
    
    def save_custom_prompts(self, prompts: Dict[str, str]) -> bool:
        """Save custom prompts as new defaults (legacy compatibility)"""
        try:
            import json
            with open("custom_prompts.json", 'w') as f:
                json.dump(prompts, f, indent=2)
            logger.info("Custom prompts saved to custom_prompts.json")
            return True
        except Exception as e:
            logger.error(f"Could not save custom prompts: {e}")
            return False
    
    def reset_to_factory_defaults(self) -> Dict[str, str]:
        """Reset prompts to factory defaults (legacy compatibility)"""
        return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Get default prompts (reuse existing logic)"""
        # Import existing logic from original pipeline
        from .pipeline import BAAssistant
        temp_assistant = BAAssistant("dummy")
        return temp_assistant._get_default_prompts()