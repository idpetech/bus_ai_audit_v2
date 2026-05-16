"""
Evidence normalization and deduplication
"""

import logging
from typing import List, Dict, Set
from ..models.evidence import EvidenceItem, ConfidenceLevel

logger = logging.getLogger(__name__)


class EvidenceNormalizer:
    """Normalizes and deduplicates evidence items"""
    
    def __init__(self):
        self.seen_claims: Set[str] = set()
    
    def normalize_evidence(self, evidence_items: List[EvidenceItem]) -> List[EvidenceItem]:
        """
        Normalize and deduplicate evidence items.
        
        - Removes exact duplicates
        - Merges similar claims
        - Standardizes formats
        - Resolves confidence conflicts
        """
        normalized = []
        claim_groups: Dict[str, List[EvidenceItem]] = {}
        
        # Group similar claims
        for item in evidence_items:
            normalized_claim = self._normalize_claim(item.claim)
            
            if normalized_claim in claim_groups:
                claim_groups[normalized_claim].append(item)
            else:
                claim_groups[normalized_claim] = [item]
        
        # Merge groups and resolve conflicts
        for normalized_claim, group in claim_groups.items():
            if len(group) == 1:
                # Single item, just add it
                normalized.append(group[0])
            else:
                # Multiple items, merge them
                merged_item = self._merge_evidence_group(group)
                normalized.append(merged_item)
        
        logger.info(f"Normalized {len(evidence_items)} evidence items to {len(normalized)} unique items")
        return normalized
    
    def _normalize_claim(self, claim: str) -> str:
        """Normalize a claim for grouping"""
        # Remove extra whitespace and normalize case
        normalized = ' '.join(claim.lower().split())
        
        # Remove common variations
        replacements = {
            'utilizes': 'uses',
            'leverages': 'uses', 
            'implements': 'uses',
            'employs': 'uses',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _merge_evidence_group(self, evidence_group: List[EvidenceItem]) -> EvidenceItem:
        """Merge multiple evidence items for the same claim"""
        
        # Use the highest confidence item as base
        base_item = max(evidence_group, key=lambda x: self._confidence_score(x.confidence))
        
        # Merge evidence text from all sources
        all_evidence_text = []
        all_sources = set()
        all_source_urls = set()
        
        for item in evidence_group:
            all_evidence_text.append(item.evidence_text)
            all_sources.add(item.source.value)
            if item.source_url:
                all_source_urls.add(item.source_url)
        
        # Create merged item
        merged_item = EvidenceItem(
            evidence_id=base_item.evidence_id,  # Keep the highest confidence ID
            claim=base_item.claim,
            evidence_text=" | ".join(all_evidence_text),
            category=base_item.category,
            confidence=self._resolve_confidence(evidence_group),
            source=base_item.source,
            source_url=base_item.source_url,
            surrounding_context=base_item.surrounding_context,
            normalization_notes=f"Merged from {len(evidence_group)} sources: {', '.join(all_sources)}"
        )
        
        return merged_item
    
    def _confidence_score(self, confidence: ConfidenceLevel) -> int:
        """Convert confidence to numeric score for comparison"""
        scores = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1
        }
        return scores[confidence]
    
    def _resolve_confidence(self, evidence_group: List[EvidenceItem]) -> ConfidenceLevel:
        """Resolve confidence when merging multiple evidence items"""
        confidences = [item.confidence for item in evidence_group]
        
        # If any are high confidence, result is high
        if ConfidenceLevel.HIGH in confidences:
            return ConfidenceLevel.HIGH
        
        # If majority are medium or higher, result is medium
        medium_or_higher = [c for c in confidences if c in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]]
        if len(medium_or_higher) >= len(evidence_group) / 2:
            return ConfidenceLevel.MEDIUM
        
        # Otherwise low confidence
        return ConfidenceLevel.LOW