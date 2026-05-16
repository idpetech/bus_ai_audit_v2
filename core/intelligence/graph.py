"""
Structured intelligence graph - future extensibility for relationship mapping
"""

import logging
from typing import Dict, List, Any, Set
from ..models.intelligence import StructuredIntelligence
from ..models.evidence import EvidenceItem, ContradictionCandidate

logger = logging.getLogger(__name__)


class IntelligenceGraph:
    """
    Graph representation of structured intelligence for future extensibility.
    
    Enables relationship mapping between evidence items, contradictions,
    and company profile elements for advanced querying and analysis.
    """
    
    def __init__(self, intelligence: StructuredIntelligence):
        self.intelligence = intelligence
        self.evidence_graph = self._build_evidence_graph()
        self.contradiction_graph = self._build_contradiction_graph()
    
    def _build_evidence_graph(self) -> Dict[str, Dict[str, Any]]:
        """Build graph of evidence relationships"""
        graph = {}
        
        for evidence in self.intelligence.evidence_items:
            graph[evidence.evidence_id] = {
                "evidence": evidence,
                "category_peers": self._find_category_peers(evidence),
                "source_peers": self._find_source_peers(evidence),
                "confidence_level": evidence.confidence,
                "supports_contradictions": self._find_supported_contradictions(evidence)
            }
        
        return graph
    
    def _build_contradiction_graph(self) -> Dict[str, Dict[str, Any]]:
        """Build graph of contradiction relationships"""
        graph = {}
        
        for contradiction in self.intelligence.contradictions:
            graph[contradiction.contradiction_id] = {
                "contradiction": contradiction,
                "claim_evidence": self.intelligence.get_evidence_by_id(contradiction.claim_evidence_id),
                "reality_evidence": self.intelligence.get_evidence_by_id(contradiction.reality_evidence_id),
                "severity": contradiction.severity,
                "related_constraints": self._find_related_constraints(contradiction)
            }
        
        return graph
    
    def _find_category_peers(self, evidence: EvidenceItem) -> List[str]:
        """Find other evidence items in the same category"""
        return [
            e.evidence_id for e in self.intelligence.evidence_items 
            if e.category == evidence.category and e.evidence_id != evidence.evidence_id
        ]
    
    def _find_source_peers(self, evidence: EvidenceItem) -> List[str]:
        """Find other evidence items from the same source"""
        return [
            e.evidence_id for e in self.intelligence.evidence_items
            if e.source == evidence.source and e.evidence_id != evidence.evidence_id
        ]
    
    def _find_supported_contradictions(self, evidence: EvidenceItem) -> List[str]:
        """Find contradictions this evidence supports"""
        return [
            c.contradiction_id for c in self.intelligence.contradictions
            if evidence.evidence_id in [c.claim_evidence_id, c.reality_evidence_id]
        ]
    
    def _find_related_constraints(self, contradiction: ContradictionCandidate) -> List[str]:
        """Find constraints related to this contradiction"""
        # Future implementation would analyze semantic relationships
        return []
    
    def query_evidence_by_path(self, category: str, source: str = None, confidence: str = None) -> List[EvidenceItem]:
        """Query evidence by category/source/confidence path"""
        results = []
        
        for evidence in self.intelligence.evidence_items:
            if evidence.category.value != category:
                continue
            
            if source and evidence.source.value != source:
                continue
                
            if confidence and evidence.confidence.value != confidence:
                continue
            
            results.append(evidence)
        
        return results
    
    def get_evidence_clusters(self) -> Dict[str, List[str]]:
        """Group evidence into semantic clusters"""
        clusters = {}
        
        for evidence_id, node in self.evidence_graph.items():
            category = node["evidence"].category.value
            if category not in clusters:
                clusters[category] = []
            clusters[category].append(evidence_id)
        
        return clusters
    
    def get_contradiction_impact_map(self) -> Dict[str, List[str]]:
        """Map contradictions to impacted evidence areas"""
        impact_map = {}
        
        for contradiction_id, node in self.contradiction_graph.items():
            claim_evidence = node["claim_evidence"]
            reality_evidence = node["reality_evidence"]
            
            if claim_evidence and reality_evidence:
                affected_categories = [claim_evidence.category.value, reality_evidence.category.value]
                impact_map[contradiction_id] = affected_categories
        
        return impact_map
    
    def to_cypher_queries(self) -> List[str]:
        """Generate Cypher queries for future Neo4j integration"""
        queries = []
        
        # Create evidence nodes
        for evidence in self.intelligence.evidence_items:
            query = f"""
            CREATE (e:Evidence {{
                id: '{evidence.evidence_id}',
                claim: '{evidence.claim.replace("'", "\\'")}',
                category: '{evidence.category.value}',
                source: '{evidence.source.value}',
                confidence: '{evidence.confidence.value}'
            }})
            """
            queries.append(query)
        
        # Create contradiction nodes and relationships
        for contradiction in self.intelligence.contradictions:
            query = f"""
            MATCH (claim:Evidence {{id: '{contradiction.claim_evidence_id}'}})
            MATCH (reality:Evidence {{id: '{contradiction.reality_evidence_id}'}})
            CREATE (c:Contradiction {{
                id: '{contradiction.contradiction_id}',
                explanation: '{contradiction.explanation.replace("'", "\\'")}'
            }})
            CREATE (c)-[:CONTRADICTS]->(claim)
            CREATE (c)-[:SUPPORTED_BY]->(reality)
            """
            queries.append(query)
        
        return queries