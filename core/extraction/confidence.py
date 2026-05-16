"""
Confidence scoring for evidence and intelligence
"""

import logging
from typing import List
from ..models.evidence import EvidenceItem, ConfidenceLevel

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Scores confidence levels for evidence and overall intelligence"""
    
    def score_overall_confidence(self, evidence_items: List[EvidenceItem]) -> ConfidenceLevel:
        """Score overall confidence in the intelligence"""
        if not evidence_items:
            return ConfidenceLevel.LOW
        
        # Calculate confidence distribution
        confidence_counts = {
            ConfidenceLevel.HIGH: 0,
            ConfidenceLevel.MEDIUM: 0,
            ConfidenceLevel.LOW: 0
        }
        
        for item in evidence_items:
            confidence_counts[item.confidence] += 1
        
        total = len(evidence_items)
        high_ratio = confidence_counts[ConfidenceLevel.HIGH] / total
        medium_ratio = confidence_counts[ConfidenceLevel.MEDIUM] / total
        
        # Scoring rules
        if high_ratio >= 0.6:
            return ConfidenceLevel.HIGH
        elif high_ratio + medium_ratio >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def score_data_quality(self, evidence_items: List[EvidenceItem]) -> float:
        """Score data quality on 0-10 scale"""
        if not evidence_items:
            return 0.0
        
        # Factors that affect data quality
        total_items = len(evidence_items)
        
        # Source diversity (more sources = better quality)
        unique_sources = len(set(item.source for item in evidence_items))
        source_diversity_score = min(unique_sources / 3.0, 1.0) * 2.0  # Max 2 points
        
        # Evidence completeness (more evidence text = better)
        avg_evidence_length = sum(len(item.evidence_text) for item in evidence_items) / total_items
        completeness_score = min(avg_evidence_length / 100.0, 1.0) * 2.0  # Max 2 points
        
        # Confidence distribution
        high_conf_ratio = len([item for item in evidence_items if item.confidence == ConfidenceLevel.HIGH]) / total_items
        confidence_score = high_conf_ratio * 3.0  # Max 3 points
        
        # Category coverage (more categories = better)
        unique_categories = len(set(item.category for item in evidence_items))
        category_score = min(unique_categories / 5.0, 1.0) * 3.0  # Max 3 points
        
        total_score = source_diversity_score + completeness_score + confidence_score + category_score
        return min(total_score, 10.0)
    
    def score_category_confidence(self, evidence_items: List[EvidenceItem]) -> ConfidenceLevel:
        """Score confidence for a specific category of evidence"""
        return self.score_overall_confidence(evidence_items)