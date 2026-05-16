"""
Unit tests for structured reasoning stages
"""

import pytest
from unittest.mock import Mock

from core.models.intelligence import StructuredIntelligence
from core.models.company import CompanyProfile, TechnologyStack
from core.models.evidence import (
    EvidenceItem, ContradictionCandidate, AIReadinessIndicator,
    ConfidenceLevel, EvidenceSource, EvidenceCategory
)
from core.reasoning import StructuredDiagnoser, StructuredHookGenerator, StructuredAuditor, StructuredCloser


class TestStructuredReasoning:
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing"""
        client = Mock()
        
        # Mock responses for different stages
        mock_response = Mock()
        mock_response.choices[0].message.content = "Test response from LLM"
        client.chat.completions.create.return_value = mock_response
        
        return client
    
    @pytest.fixture
    def test_intelligence(self):
        """Create test structured intelligence"""
        evidence_items = [
            EvidenceItem(
                evidence_id="ev_001",
                claim="Uses React for frontend",
                evidence_text="Built with React framework",
                category=EvidenceCategory.TECH_STACK,
                confidence=ConfidenceLevel.HIGH,
                source=EvidenceSource.COMPANY_WEBSITE,
                source_url="https://test.com"
            ),
            EvidenceItem(
                evidence_id="ev_002", 
                claim="Claims AI-powered features",
                evidence_text="AI-driven analytics platform",
                category=EvidenceCategory.AI_MENTION,
                confidence=ConfidenceLevel.MEDIUM,
                source=EvidenceSource.COMPANY_WEBSITE
            ),
            EvidenceItem(
                evidence_id="ev_003",
                claim="No ML engineers on team",
                evidence_text="LinkedIn shows no ML roles",
                category=EvidenceCategory.HIRING_PATTERN,
                confidence=ConfidenceLevel.HIGH,
                source=EvidenceSource.EXTERNAL_SEARCH
            )
        ]
        
        contradictions = [
            ContradictionCandidate(
                contradiction_id="contra_001",
                claim_evidence_id="ev_002",
                reality_evidence_id="ev_003",
                contradiction_type="ai_capability_mismatch",
                severity=ConfidenceLevel.HIGH,
                explanation="Claims AI features but no ML expertise on team"
            )
        ]
        
        ai_readiness = [
            AIReadinessIndicator(
                indicator_id="ai_001",
                readiness_type="capability_assessment",
                ai_classification="AI-Assisted",
                readiness_score=4.5,
                supporting_evidence_ids=["ev_002", "ev_003"],
                blocking_factors=["No ML team"],
                enablers=["Modern tech stack"]
            )
        ]
        
        company_profile = CompanyProfile(
            company_name="Test Company",
            website_url="https://test.com",
            technology_stack=TechnologyStack(
                programming_languages=["JavaScript"],
                frameworks=["React"],
                evidence_ids=["ev_001"],
                confidence=ConfidenceLevel.HIGH
            )
        )
        
        return StructuredIntelligence(
            intelligence_id="intel_test",
            company_profile=company_profile,
            evidence_items=evidence_items,
            contradictions=contradictions,
            ai_readiness_indicators=ai_readiness,
            overall_confidence=ConfidenceLevel.MEDIUM,
            data_quality_score=7.5,
            evidence_coverage={"TECH_STACK": 1, "AI_MENTION": 1, "HIRING_PATTERN": 1},
            source_urls=["https://test.com"],
            extraction_duration_seconds=30.0
        )
    
    def test_structured_diagnoser(self, mock_openai_client, test_intelligence):
        """Test structured diagnoser operates on intelligence"""
        diagnoser = StructuredDiagnoser(mock_openai_client, {})
        
        diagnosis = diagnoser.diagnose(test_intelligence)
        
        # Should return diagnosis
        assert isinstance(diagnosis, str)
        assert len(diagnosis) > 0
        
        # Should have called OpenAI with structured context
        assert mock_openai_client.chat.completions.create.called
        
        # Verify the prompt includes structured intelligence
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        # Should reference evidence IDs and structured data
        assert "ev_" in user_prompt  # Evidence ID format
        assert "Test Company" in user_prompt
        assert "CONTRADICTIONS" in user_prompt
    
    def test_diagnoser_references_evidence(self, mock_openai_client, test_intelligence):
        """Test diagnoser includes evidence references"""
        diagnoser = StructuredDiagnoser(mock_openai_client, {})
        
        diagnosis = diagnoser.diagnose(test_intelligence)
        
        # Check that prompt includes contradiction details
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        # Should include contradiction explanation
        assert "Claims AI features but no ML expertise" in user_prompt
        # Should include evidence IDs
        assert "ev_002" in user_prompt and "ev_003" in user_prompt
    
    def test_structured_hook_generator(self, mock_openai_client, test_intelligence):
        """Test structured hook generator"""
        hook_generator = StructuredHookGenerator(mock_openai_client, {})
        
        hook = hook_generator.generate_hook(test_intelligence, "Test diagnosis")
        
        assert isinstance(hook, str)
        assert mock_openai_client.chat.completions.create.called
        
        # Check prompt includes contradiction
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        assert "TECHNICAL CONTRADICTION" in user_prompt
        assert "Test Company" in user_prompt
    
    def test_structured_auditor(self, mock_openai_client, test_intelligence):
        """Test structured auditor"""
        auditor = StructuredAuditor(mock_openai_client, {})
        
        audit = auditor.generate_audit(test_intelligence, "Test diagnosis")
        
        assert isinstance(audit, str)
        assert mock_openai_client.chat.completions.create.called
        
        # Check prompt includes AI readiness
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        assert "AI READINESS INDICATORS" in user_prompt
        assert "AI-Assisted" in user_prompt
        assert "4.5/10" in user_prompt
    
    def test_structured_closer(self, mock_openai_client, test_intelligence):
        """Test structured closer"""
        closer = StructuredCloser(mock_openai_client, {})
        
        close = closer.generate_close(test_intelligence, "Test audit")
        
        assert isinstance(close, str)
        assert mock_openai_client.chat.completions.create.called
        
        # Check prompt includes core contradiction
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        assert "CORE ARCHITECTURAL CONTRADICTION" in user_prompt
        assert "Test Company" in user_prompt
    
    def test_no_raw_content_access(self, mock_openai_client, test_intelligence):
        """Test that reasoning stages don't access raw content"""
        stages = [
            StructuredDiagnoser(mock_openai_client, {}),
            StructuredHookGenerator(mock_openai_client, {}),
            StructuredAuditor(mock_openai_client, {}), 
            StructuredCloser(mock_openai_client, {})
        ]
        
        # Run all stages
        diagnoser = stages[0]
        hook_generator = stages[1]
        auditor = stages[2]
        closer = stages[3]
        
        diagnosis = diagnoser.diagnose(test_intelligence)
        hook = hook_generator.generate_hook(test_intelligence, diagnosis)
        audit = auditor.generate_audit(test_intelligence, diagnosis)
        close = closer.generate_close(test_intelligence, audit)
        
        # Verify none of the prompts contain raw scraped content
        all_calls = mock_openai_client.chat.completions.create.call_args_list
        
        for call in all_calls:
            user_prompt = call[1]["messages"][1]["content"]
            
            # Should NOT contain raw content patterns
            assert "scraped_content" not in user_prompt.lower()
            assert "raw content" not in user_prompt.lower()
            
            # Should contain structured intelligence patterns
            assert any(pattern in user_prompt for pattern in [
                "COMPANY PROFILE",
                "EVIDENCE",
                "CONTRADICTIONS", 
                "structured intelligence"
            ])
    
    def test_evidence_traceability(self, mock_openai_client, test_intelligence):
        """Test evidence traceability through reasoning"""
        diagnoser = StructuredDiagnoser(mock_openai_client, {})
        
        # Mock response with evidence references
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = \
            "Based on evidence ev_002 and ev_003, there is a contradiction..."
        
        diagnosis = diagnoser.diagnose(test_intelligence)
        
        # Response should reference evidence IDs
        assert "ev_002" in diagnosis
        assert "ev_003" in diagnosis
    
    def test_confidence_propagation(self, mock_openai_client, test_intelligence):
        """Test confidence levels are propagated through reasoning"""
        auditor = StructuredAuditor(mock_openai_client, {})
        
        audit = auditor.generate_audit(test_intelligence, "Test diagnosis")
        
        # Check that confidence information is included in prompt
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        # Should include confidence metrics
        assert "7.5/10" in user_prompt  # data_quality_score
        assert "MEDIUM" in user_prompt  # overall_confidence
    
    def test_empty_intelligence_handling(self, mock_openai_client):
        """Test handling of intelligence with no evidence"""
        empty_intelligence = StructuredIntelligence(
            intelligence_id="empty_test",
            company_profile=CompanyProfile(
                company_name="Empty Company",
                website_url="https://empty.com"
            ),
            evidence_items=[],
            contradictions=[],
            overall_confidence=ConfidenceLevel.LOW,
            data_quality_score=1.0,
            evidence_coverage={},
            source_urls=["https://empty.com"],
            extraction_duration_seconds=5.0
        )
        
        diagnoser = StructuredDiagnoser(mock_openai_client, {})
        
        # Should handle empty evidence gracefully
        diagnosis = diagnoser.diagnose(empty_intelligence)
        assert isinstance(diagnosis, str)
        
        # Prompt should indicate limited evidence
        call_args = mock_openai_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        
        assert "Total evidence items: 0" in user_prompt