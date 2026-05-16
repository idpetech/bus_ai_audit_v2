"""
Structured intelligence models package
"""

from .evidence import (
    EvidenceItem,
    ContradictionCandidate,
    ModernizationSignal,
    AIReadinessIndicator,
    ConstraintIndicator,
    ConfidenceLevel,
    EvidenceSource,
    EvidenceCategory
)

from .company import (
    CompanyProfile,
    TechnologyStack,
    BusinessModel,
    OperationalSignals,
    PlatformSignals
)

from .intelligence import StructuredIntelligence

# Re-export existing models for compatibility  
# Import directly from the original models.py file to avoid circular imports
import sys
import os
models_path = os.path.join(os.path.dirname(__file__), '..', 'models.py')
spec = __import__('importlib.util').util.spec_from_file_location("original_models", models_path)
original_models = __import__('importlib.util').util.module_from_spec(spec)
spec.loader.exec_module(original_models)

CompanyInputs = original_models.CompanyInputs
PipelineResults = original_models.PipelineResults  
ResearchSummary = original_models.ResearchSummary
ICPResult = original_models.ICPResult
AGENT_STAGES = original_models.AGENT_STAGES

__all__ = [
    # Evidence models
    "EvidenceItem",
    "ContradictionCandidate", 
    "ModernizationSignal",
    "AIReadinessIndicator",
    "ConstraintIndicator",
    "ConfidenceLevel",
    "EvidenceSource",
    "EvidenceCategory",
    
    # Company models
    "CompanyProfile",
    "TechnologyStack", 
    "BusinessModel",
    "OperationalSignals",
    "PlatformSignals",
    
    # Core intelligence
    "StructuredIntelligence",
    
    # Legacy models (for compatibility)
    "CompanyInputs",
    "PipelineResults", 
    "ResearchSummary",
    "ICPResult",
    "AGENT_STAGES"
]