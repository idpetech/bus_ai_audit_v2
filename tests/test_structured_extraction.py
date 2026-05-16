"""
Unit tests for structured extraction engine
"""

import pytest
import json
from unittest.mock import Mock, MagicMock

from core.models import CompanyInputs
from core.models.intelligence import StructuredIntelligence
from core.models.evidence import EvidenceItem, ConfidenceLevel, EvidenceSource, EvidenceCategory
from core.extraction import StructuredExtractor


class TestStructuredExtractor:
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing"""
        client = Mock()
        
        # Mock response for evidence extraction
        mock_response = Mock()
        mock_response.choices[0].message.content = json.dumps([
            {
                "claim": "Uses React for frontend development",
                "evidence_text": "Built with React and modern JavaScript",
                "category": "TECH_STACK",
                "confidence": "HIGH",
                "surrounding_context": "Technology stack section"
            },
            {
                "claim": "Processes 1000+ orders daily",
                "evidence_text": "We handle over 1000 orders per day",
                "category": "SCALE_INDICATOR", 
                "confidence": "MEDIUM",
                "surrounding_context": "Company metrics section"
            }
        ])
        
        client.chat.completions.create.return_value = mock_response
        return client
    
    @pytest.fixture
    def test_inputs(self):
        """Test company inputs"""
        return CompanyInputs(
            target_url="https://testcompany.com",
            company_name="Test Company",
            scraped_content="Test scraped content about React and 1000 orders",
            external_signals="External signal about company growth",
            job_posting="Hiring React developers"
        )
    
    @pytest.fixture
    def extractor(self, mock_openai_client):
        """Create extractor with mocked client"""
        prompts = {"extract_signals": "Test prompt"}
        return StructuredExtractor(mock_openai_client, prompts)
    
    def test_extract_structured_intelligence(self, extractor, test_inputs):
        """Test basic structured intelligence extraction"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        # Verify intelligence object structure
        assert isinstance(intelligence, StructuredIntelligence)
        assert intelligence.intelligence_id.startswith("intel_")
        assert intelligence.company_profile.company_name == "Test Company"
        assert intelligence.company_profile.website_url == "https://testcompany.com"
        
        # Verify evidence extraction
        assert len(intelligence.evidence_items) > 0
        
        # Check evidence quality
        assert intelligence.overall_confidence in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
        assert 0 <= intelligence.data_quality_score <= 10
    
    def test_evidence_item_structure(self, extractor, test_inputs):
        """Test evidence item structure and fields"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        for evidence in intelligence.evidence_items:
            # Verify required fields
            assert evidence.evidence_id.startswith("ev_")
            assert len(evidence.claim) > 0
            assert len(evidence.evidence_text) > 0
            assert evidence.category in EvidenceCategory
            assert evidence.confidence in ConfidenceLevel
            assert evidence.source in EvidenceSource
            
            # Verify timestamps
            assert evidence.extracted_at is not None
    
    def test_evidence_categorization(self, extractor, test_inputs):
        """Test evidence is properly categorized"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        # Should have evidence in multiple categories
        categories = [item.category for item in intelligence.evidence_items]
        assert EvidenceCategory.TECH_STACK in categories
        assert EvidenceCategory.SCALE_INDICATOR in categories
    
    def test_evidence_source_tracking(self, extractor, test_inputs):
        """Test evidence source tracking"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        sources = [item.source for item in intelligence.evidence_items]
        
        # Should extract from multiple sources
        assert EvidenceSource.COMPANY_WEBSITE in sources
        assert EvidenceSource.JOB_POSTING in sources
        assert EvidenceSource.EXTERNAL_SEARCH in sources
    
    def test_evidence_confidence_scoring(self, extractor, test_inputs):
        """Test evidence confidence scoring"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        # Should have mix of confidence levels
        confidences = [item.confidence for item in intelligence.evidence_items]
        assert len(set(confidences)) >= 1  # At least one confidence level
        
        # High confidence evidence should have supporting details
        high_conf_items = intelligence.get_high_confidence_evidence()
        if high_conf_items:
            assert all(len(item.evidence_text) > 10 for item in high_conf_items)
    
    def test_company_profile_construction(self, extractor, test_inputs):
        """Test company profile construction from evidence"""
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        profile = intelligence.company_profile
        
        # Basic company information
        assert profile.company_name == "Test Company"
        assert profile.website_url == "https://testcompany.com"
        
        # Technology stack should reference evidence
        assert len(profile.technology_stack.evidence_ids) > 0
        
        # Business model should reference evidence
        assert len(profile.business_model.evidence_ids) > 0
    
    def test_error_handling(self, test_inputs):
        """Test error handling in extraction"""
        # Mock client that fails
        failing_client = Mock()
        failing_client.chat.completions.create.side_effect = Exception("API Error")
        
        extractor = StructuredExtractor(failing_client, {})
        
        # Should handle errors gracefully
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        # Should still return intelligence object
        assert isinstance(intelligence, StructuredIntelligence)
        
        # But with empty evidence
        assert len(intelligence.evidence_items) == 0
    
    def test_caching_behavior(self, extractor, test_inputs):
        """Test extraction caching"""
        # First extraction
        intelligence1 = extractor.extract_structured_intelligence(test_inputs)
        
        # Second extraction with same inputs
        intelligence2 = extractor.extract_structured_intelligence(test_inputs)
        
        # Should be identical (from cache)
        assert intelligence1.intelligence_id == intelligence2.intelligence_id
    
    def test_evidence_normalization(self, extractor, test_inputs):
        """Test evidence normalization and deduplication"""
        # Mock client to return duplicate evidence
        extractor.client.chat.completions.create.return_value.choices[0].message.content = json.dumps([
            {
                "claim": "Uses React framework",
                "evidence_text": "Built with React",
                "category": "TECH_STACK",
                "confidence": "HIGH",
                "surrounding_context": "Tech section"
            },
            {
                "claim": "Uses React framework",  # Duplicate
                "evidence_text": "React-based application",
                "category": "TECH_STACK",
                "confidence": "MEDIUM",
                "surrounding_context": "Different section"
            }
        ])
        
        intelligence = extractor.extract_structured_intelligence(test_inputs)
        
        # Should deduplicate similar claims
        react_claims = [
            item for item in intelligence.evidence_items 
            if "react" in item.claim.lower()
        ]
        
        # Should merge duplicates
        assert len(react_claims) <= 2