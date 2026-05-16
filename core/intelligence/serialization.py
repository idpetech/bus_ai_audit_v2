"""
JSON serialization and persistence for structured intelligence
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models.intelligence import StructuredIntelligence

logger = logging.getLogger(__name__)


class IntelligenceSerializer:
    """
    Handles JSON serialization and persistence of structured intelligence.
    
    Supports:
    - JSON-compatible serialization
    - Database persistence preparation
    - Version compatibility
    - Future graph format export
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path("intelligence_cache")
        self.storage_path.mkdir(exist_ok=True)
    
    def serialize_to_json(self, intelligence: StructuredIntelligence) -> str:
        """Serialize structured intelligence to JSON string"""
        try:
            data = intelligence.to_json_compatible()
            
            # Add serialization metadata
            data["_serialization"] = {
                "version": "1.0",
                "serialized_at": datetime.utcnow().isoformat(),
                "format": "structured_intelligence_v1"
            }
            
            return json.dumps(data, indent=2, default=str)
        
        except Exception as e:
            logger.error(f"Failed to serialize intelligence: {e}")
            raise
    
    def deserialize_from_json(self, json_str: str) -> StructuredIntelligence:
        """Deserialize structured intelligence from JSON string"""
        try:
            data = json.loads(json_str)
            
            # Remove serialization metadata
            if "_serialization" in data:
                serialization_info = data.pop("_serialization")
                logger.info(f"Deserializing from format: {serialization_info.get('format', 'unknown')}")
            
            return StructuredIntelligence.from_json_compatible(data)
        
        except Exception as e:
            logger.error(f"Failed to deserialize intelligence: {e}")
            raise
    
    def save_to_file(self, intelligence: StructuredIntelligence, filename: str = None) -> str:
        """Save structured intelligence to JSON file"""
        if not filename:
            filename = f"intelligence_{intelligence.intelligence_id}.json"
        
        file_path = self.storage_path / filename
        
        try:
            json_str = self.serialize_to_json(intelligence)
            
            with open(file_path, 'w') as f:
                f.write(json_str)
            
            logger.info(f"Intelligence saved to {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Failed to save intelligence to file: {e}")
            raise
    
    def load_from_file(self, filename: str) -> StructuredIntelligence:
        """Load structured intelligence from JSON file"""
        file_path = self.storage_path / filename
        
        try:
            with open(file_path, 'r') as f:
                json_str = f.read()
            
            intelligence = self.deserialize_from_json(json_str)
            logger.info(f"Intelligence loaded from {file_path}")
            return intelligence
        
        except Exception as e:
            logger.error(f"Failed to load intelligence from file: {e}")
            raise
    
    def to_database_format(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """
        Convert to database-compatible format for existing SQLite schema.
        
        Maps structured intelligence back to current database fields
        for backward compatibility during migration.
        """
        
        # Convert evidence items to legacy signals format
        legacy_signals = self._convert_evidence_to_legacy_signals(intelligence)
        
        return {
            "website_url": intelligence.company_profile.website_url,
            "company_name": intelligence.company_profile.company_name,
            "signals_json": json.dumps(legacy_signals),
            "structured_intelligence": self.serialize_to_json(intelligence),  # Full intelligence in new field
            "extraction_version": intelligence.extraction_version,
            "evidence_quality_score": intelligence.data_quality_score,
            "overall_confidence": intelligence.overall_confidence.value
        }
    
    def _convert_evidence_to_legacy_signals(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """Convert evidence items back to legacy signals format for compatibility"""
        
        # Group evidence by category
        evidence_by_category = {}
        for item in intelligence.evidence_items:
            category = item.category.value.lower()
            if category not in evidence_by_category:
                evidence_by_category[category] = []
            evidence_by_category[category].append(item.claim)
        
        # Map to legacy format
        legacy_signals = {
            "company_name": intelligence.company_profile.company_name,
            "industry": intelligence.company_profile.industry or "",
            "tech_stack": evidence_by_category.get("tech_stack", []),
            "ai_mentions": evidence_by_category.get("ai_mention", []),
            "architecture_keywords": evidence_by_category.get("architecture", []),
            "data_flow_indicators": evidence_by_category.get("data_flow", []),
            "business_model_signals": evidence_by_category.get("business_model", []),
            "scale_indicators": evidence_by_category.get("scale_indicator", []),
            "hiring_patterns": evidence_by_category.get("hiring_pattern", [])
        }
        
        return legacy_signals
    
    def export_for_chatbot(self, intelligence: StructuredIntelligence) -> Dict[str, Any]:
        """
        Export in format optimized for chatbot querying.
        
        Future enhancement for conversational intelligence access.
        """
        return {
            "company": {
                "name": intelligence.company_profile.company_name,
                "website": intelligence.company_profile.website_url,
                "industry": intelligence.company_profile.industry
            },
            "evidence_summary": {
                "total_items": len(intelligence.evidence_items),
                "high_confidence_items": len(intelligence.get_high_confidence_evidence()),
                "categories_covered": list(intelligence.evidence_coverage.keys())
            },
            "key_findings": {
                "contradictions": [c.explanation for c in intelligence.contradictions],
                "ai_readiness": [ai.ai_classification for ai in intelligence.ai_readiness_indicators],
                "critical_constraints": [c.constraint_type for c in intelligence.constraint_indicators]
            },
            "queryable_evidence": [
                {
                    "id": item.evidence_id,
                    "claim": item.claim,
                    "category": item.category.value,
                    "confidence": item.confidence.value,
                    "source": item.source.value
                }
                for item in intelligence.evidence_items
            ]
        }
    
    def list_cached_intelligence(self) -> List[Dict[str, Any]]:
        """List all cached intelligence files"""
        cached = []
        
        for file_path in self.storage_path.glob("*.json"):
            try:
                # Read basic metadata without full deserialization
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                cached.append({
                    "filename": file_path.name,
                    "intelligence_id": data.get("intelligence_id"),
                    "company_name": data.get("company_profile", {}).get("company_name"),
                    "created_at": data.get("created_at"),
                    "evidence_count": len(data.get("evidence_items", [])),
                    "file_size": file_path.stat().st_size
                })
            
            except Exception as e:
                logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return cached