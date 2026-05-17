#!/usr/bin/env python3
"""
Direct test of structured extraction to see logging output
"""

import logging
import json
import sys
import os

# Set up detailed logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Import after logging setup
from core.models import CompanyInputs
from core.structured_pipeline import StructuredBAAssistant

def test_fresh_air_extraction():
    """Test extraction on Fresh Air Heating & Cooling data from database"""
    
    print("🔧 Setting up test...")
    
    # Get API key - try multiple sources
    api_key = None
    
    # Try environment variable
    api_key = os.environ.get('OPENAI_API_KEY')
    
    # Try streamlit secrets if available
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except:
            pass
    
    # Manual input as fallback
    if not api_key:
        api_key = input("Enter OpenAI API Key: ").strip()
    
    if not api_key:
        print("❌ No API key available")
        return
    
    print("✅ API key obtained")
    
    # Create test inputs using actual Fresh Air data
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
    
    print(f"📝 Test inputs created:")
    print(f"   Company: {inputs.company_name}")
    print(f"   URL: {inputs.target_url}")
    print(f"   Content length: {len(inputs.scraped_content)} chars")
    print(f"   External signals: {len(inputs.external_signals)} chars")
    
    # Initialize structured assistant
    print("\n🤖 Initializing StructuredBAAssistant...")
    assistant = StructuredBAAssistant(api_key)
    
    # Test extraction only (not full pipeline)
    print("\n🔍 Testing structured intelligence extraction...")
    try:
        intelligence = assistant.extract_structured_intelligence(inputs)
        
        print(f"\n✅ Extraction completed!")
        print(f"   Intelligence ID: {intelligence.intelligence_id}")
        print(f"   Evidence items: {len(intelligence.evidence_items)}")
        print(f"   Data quality score: {intelligence.data_quality_score}")
        print(f"   Overall confidence: {intelligence.overall_confidence}")
        
        # Show evidence details
        if intelligence.evidence_items:
            print(f"\n📋 Evidence items:")
            for i, item in enumerate(intelligence.evidence_items):
                print(f"   {i+1}. {item.claim} [{item.category.value}] ({item.confidence.value})")
        else:
            print(f"\n❌ NO EVIDENCE ITEMS EXTRACTED!")
            
        # Convert to legacy signals format to see what would be saved
        legacy_signals = assistant._convert_intelligence_to_legacy_signals(intelligence)
        print(f"\n📊 Legacy signals format:")
        print(f"   Keys: {list(legacy_signals.keys())}")
        non_empty = {k: v for k, v in legacy_signals.items() if v and v != [] and v != ""}
        print(f"   Non-empty fields: {len(non_empty)}")
        if non_empty:
            for key, value in non_empty.items():
                print(f"     {key}: {value}")
        else:
            print(f"   ⚠️  ALL LEGACY SIGNALS WOULD BE EMPTY!")
            
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    test_fresh_air_extraction()