"""
Extraction package - canonical evidence extraction and normalization
"""

from .extractor import StructuredExtractor
from .normalizer import EvidenceNormalizer
from .confidence import ConfidenceScorer

__all__ = [
    "StructuredExtractor",
    "EvidenceNormalizer", 
    "ConfidenceScorer"
]