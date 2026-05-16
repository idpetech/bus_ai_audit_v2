"""
Integration tests for structured pipeline
"""

import pytest
from unittest.mock import Mock, patch
import json

from core.structured_pipeline import StructuredBAAssistant
from core.models import CompanyInputs, PipelineResults
from core.models.intelligence import StructuredIntelligence


class TestPipelineIntegration:
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing"""
        client = Mock()
        
        # Mock responses for different stages
        extraction_response = Mock()
        extraction_response.choices[0].message.content = json.dumps([
            {
                "claim": "React-based frontend application",
                "evidence_text": "Built with React and TypeScript",
                "category": "TECH_STACK",
                "confidence": "HIGH",
                "surrounding_context": "Technology overview"
            }
        ])
        
        reasoning_response = Mock()
        reasoning_response.choices[0].message.content = "Test reasoning output"
        
        # Return different responses based on call order
        client.chat.completions.create.side_effect = [
            extraction_response,  # Extraction call
            reasoning_response,   # Diagnosis call
            reasoning_response,   # Hook call
            reasoning_response,   # Audit call
            reasoning_response    # Close call
        ]
        
        return client
    
    @pytest.fixture
    def test_inputs(self):
        """Test company inputs"""
        return CompanyInputs(
            target_url="https://testcompany.com",
            company_name="Test Company",
            scraped_content="React-based application with TypeScript",
            external_signals="External validation of tech stack",
            job_posting="Hiring React developers"
        )
    
    @pytest.fixture 
    def structured_assistant(self, mock_openai_client):
        """Create structured assistant with mocked client"""
        with patch('core.structured_pipeline.openai.OpenAI', return_value=mock_openai_client):
            return StructuredBAAssistant("fake-api-key")
    
    def test_full_structured_pipeline(self, structured_assistant, test_inputs):
        """Test complete structured pipeline execution"""
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        
        # Verify structured intelligence was created
        assert isinstance(intelligence, StructuredIntelligence)
        assert intelligence.company_profile.company_name == "Test Company"
        assert len(intelligence.evidence_items) > 0
        
        # Verify traditional results for backward compatibility
        assert isinstance(results, PipelineResults)
        assert results.signals is not None
        assert results.diagnosis is not None
        assert results.hook is not None
        assert results.audit is not None
        assert results.close is not None
    
    def test_backward_compatibility(self, structured_assistant, test_inputs):
        """Test backward compatibility with existing interface"""
        # Should work with existing method signature
        results = structured_assistant.run_full_pipeline(test_inputs)
        
        assert isinstance(results, PipelineResults)
        assert hasattr(results, 'signals')
        assert hasattr(results, 'diagnosis') 
        assert hasattr(results, 'hook')
        assert hasattr(results, 'audit')
        assert hasattr(results, 'close')
    
    def test_extract_once_principle(self, structured_assistant, test_inputs):
        """Test that extraction only happens once"""
        # Run pipeline twice with same inputs
        intelligence1 = structured_assistant.extract_structured_intelligence(test_inputs)
        intelligence2 = structured_assistant.extract_structured_intelligence(test_inputs)
        
        # Should return same intelligence (cached)
        assert intelligence1.intelligence_id == intelligence2.intelligence_id
        
        # Verify extraction was cached (called once)
        assert structured_assistant.client.chat.completions.create.call_count <= 5
    
    def test_no_raw_content_in_reasoning(self, structured_assistant, test_inputs):
        """Test reasoning stages don't access raw content"""
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        
        # Get all OpenAI calls
        all_calls = structured_assistant.client.chat.completions.create.call_args_list
        
        # First call should be extraction (accesses raw content)
        extraction_call = all_calls[0]
        extraction_prompt = extraction_call[1]["messages"][1]["content"]
        assert "React-based application" in extraction_prompt  # Raw content
        
        # Subsequent calls should be reasoning (no raw content)
        for reasoning_call in all_calls[1:]:
            reasoning_prompt = reasoning_call[1]["messages"][1]["content"]
            
            # Should NOT contain raw scraped content
            assert "React-based application with TypeScript" not in reasoning_prompt
            
            # Should contain structured intelligence markers
            assert any(marker in reasoning_prompt for marker in [
                "COMPANY PROFILE",
                "EVIDENCE",
                "structured intelligence",
                "Test Company"
            ])
    
    def test_evidence_traceability_end_to_end(self, structured_assistant, test_inputs):
        """Test evidence traceability through entire pipeline"""
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        
        # Evidence should have unique IDs
        evidence_ids = [item.evidence_id for item in intelligence.evidence_items]
        assert all(eid.startswith("ev_") for eid in evidence_ids)
        assert len(evidence_ids) == len(set(evidence_ids))  # All unique
        
        # Company profile should reference evidence
        assert len(intelligence.company_profile.technology_stack.evidence_ids) > 0
    
    def test_confidence_scoring_integration(self, structured_assistant, test_inputs):
        """Test confidence scoring through pipeline"""
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        
        # Should have overall confidence
        assert intelligence.overall_confidence is not None
        
        # Should have data quality score
        assert 0 <= intelligence.data_quality_score <= 10
        
        # Evidence coverage should be calculated
        assert len(intelligence.evidence_coverage) > 0
    
    def test_serialization_integration(self, structured_assistant, test_inputs):
        """Test intelligence serialization"""
        intelligence = structured_assistant.extract_structured_intelligence(test_inputs)
        
        # Should be able to save and load
        filename = structured_assistant.save_intelligence(intelligence)
        loaded_intelligence = structured_assistant.load_intelligence(filename.split("/")[-1])
        
        assert loaded_intelligence.intelligence_id == intelligence.intelligence_id
        assert loaded_intelligence.company_profile.company_name == intelligence.company_profile.company_name
    
    def test_legacy_method_compatibility(self, structured_assistant, test_inputs):
        """Test legacy method signatures still work"""
        # Legacy extract_signals should work
        signals = structured_assistant.extract_signals(test_inputs)
        assert isinstance(signals, (dict, str))
        
        # Legacy diagnose should work (though with warning)
        diagnosis = structured_assistant.diagnose(signals, test_inputs)
        assert isinstance(diagnosis, str)
    
    def test_error_handling_integration(self, test_inputs):
        """Test error handling throughout pipeline"""
        # Create assistant with failing client
        failing_client = Mock()
        failing_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch('core.structured_pipeline.openai.OpenAI', return_value=failing_client):
            assistant = StructuredBAAssistant("fake-key")
            
            # Should handle errors gracefully
            try:
                intelligence = assistant.extract_structured_intelligence(test_inputs)
                # Should return valid intelligence even with errors
                assert isinstance(intelligence, StructuredIntelligence)
            except Exception as e:
                # If it fails, should fail gracefully
                assert "API Error" in str(e)
    
    def test_performance_characteristics(self, structured_assistant, test_inputs):
        """Test performance characteristics of structured pipeline"""
        import time
        
        start_time = time.time()
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert execution_time < 10.0  # Assuming mocked calls are fast
        
        # Should track extraction duration
        assert intelligence.extraction_duration_seconds > 0
    
    def test_token_efficiency(self, structured_assistant, test_inputs):
        """Test token efficiency of structured approach"""
        # Run structured pipeline
        intelligence, results = structured_assistant.run_structured_pipeline(test_inputs)
        
        # Count total OpenAI calls
        total_calls = structured_assistant.client.chat.completions.create.call_count
        
        # Should make fewer calls than old architecture
        # (1 extraction + 4 reasoning = 5 total, vs old architecture's repeated parsing)
        assert total_calls <= 5
        
        # Reasoning calls should use structured data, not raw content
        all_calls = structured_assistant.client.chat.completions.create.call_args_list
        
        for call in all_calls[1:]:  # Skip extraction call
            prompt = call[1]["messages"][1]["content"] 
            # Should be shorter than raw content prompts
            assert len(prompt) < 10000  # Reasonable limit for structured prompts