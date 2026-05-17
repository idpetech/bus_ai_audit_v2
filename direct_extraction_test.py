#!/usr/bin/env python3
"""
Direct test of extraction logic with manual API key input
"""

import logging
import json
import sys
import openai

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from core.models import CompanyInputs, EvidenceCategory, EvidenceSource, ConfidenceLevel
from core.extraction.extractor import StructuredExtractor

def test_extraction_directly():
    """Test the extraction process directly"""
    
    print("=== DIRECT EXTRACTION TEST ===")
    
    # Get API key
    api_key = input("Enter OpenAI API Key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("Skipping API test - no key provided")
        return
    
    client = openai.OpenAI(api_key=api_key)
    prompts = {}  # Empty prompts dict for this test
    
    extractor = StructuredExtractor(client, prompts)
    
    # Create test inputs
    inputs = CompanyInputs(
        target_url="https://www.freshaircorp.com/our-company-2/",
        company_name="Fresh Air Heating & Cooling", 
        scraped_content="""Fresh Air Heating & Cooling has been serving the Greater Cincinnati area since 2008. We are a full-service HVAC company that specializes in heating, cooling, and air quality solutions for both residential and commercial customers.

Our Services:
- HVAC Installation & Replacement  
- Heating & Cooling Repair
- Air Quality Solutions
- 24/7 Emergency Service
- Maintenance Plans

We are fully licensed and insured, and our certified technicians are trained on all major brands of HVAC equipment including Carrier, Trane, Lennox, and more.

Contact us today for a free estimate on any HVAC service!""",
        external_signals="Fresh Air Heating & Cooling - HVAC services Cincinnati area. Licensed and insured. Emergency service available.",
        job_posting=None
    )
    
    print(f"Input prepared - content: {len(inputs.scraped_content)} chars")
    
    # Test the extraction
    try:
        print("\n🔬 Starting extraction...")
        intelligence = extractor.extract_structured_intelligence(inputs)
        
        print(f"✅ Extraction completed!")
        print(f"Evidence items: {len(intelligence.evidence_items)}")
        print(f"Data quality: {intelligence.data_quality_score}")
        print(f"Confidence: {intelligence.overall_confidence}")
        
        if intelligence.evidence_items:
            print("\nEvidence found:")
            for i, item in enumerate(intelligence.evidence_items):
                print(f"  {i+1}. [{item.category.value}] {item.claim} ({item.confidence.value})")
        else:
            print("❌ NO EVIDENCE ITEMS FOUND")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction_directly()