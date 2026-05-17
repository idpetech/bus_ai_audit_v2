#!/usr/bin/env python3
"""
Debug script for structured extraction failures
"""

import os
import json
import logging
import openai
import streamlit as st
from core.models import CompanyInputs, EvidenceCategory, EvidenceSource, ConfidenceLevel

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_extraction():
    """Test the extraction process with verbose logging"""
    
    # Get API key from environment or streamlit secrets
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        try:
            # If running in Streamlit context, use secrets
            api_key = st.secrets.get("OPENAI_API_KEY")
        except:
            # If no Streamlit context, prompt for manual input
            api_key = input("Enter OpenAI API Key: ").strip()
    
    if not api_key:
        print("❌ No API key available")
        return
    
    client = openai.OpenAI(api_key=api_key)
    
    # Test with Fresh Air Heating & Cooling content (simplified)
    test_content = """Fresh Air Heating & Cooling provides HVAC services including heating, cooling, and air quality solutions. We serve residential and commercial customers with 24/7 emergency service. Our certified technicians install and repair all major brands of HVAC equipment."""
    
    system_prompt = """You are a structured evidence extraction engine. Extract individual factual claims from the provided content.

For each factual claim found, output a JSON object with:
{
  "claim": "specific factual statement",
  "evidence_text": "exact text supporting this claim", 
  "category": "TECH_STACK|BUSINESS_MODEL|SCALE_INDICATOR|AI_MENTION|ARCHITECTURE|DATA_FLOW|HIRING_PATTERN|FUNDING|LEADERSHIP|OPERATIONAL",
  "confidence": "HIGH|MEDIUM|LOW",
  "surrounding_context": "text around the evidence for context"
}

Return an array of these objects. Extract ONLY factual claims, not opinions or marketing language.
Focus on technical details, business model facts, team information, and concrete operational signals.

CRITICAL: Do NOT interpret or analyze. ONLY extract explicit factual statements."""
    
    user_prompt = f"Extract evidence from this COMPANY_WEBSITE content:\n\n{test_content}"
    
    print("🔍 Testing OpenAI API call...")
    print(f"System prompt length: {len(system_prompt)} chars")
    print(f"User prompt length: {len(user_prompt)} chars")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        print("✅ OpenAI API call successful")
        raw_response = response.choices[0].message.content
        print(f"Raw response: {raw_response}")
        
        # Test JSON parsing
        try:
            raw_evidence = json.loads(raw_response)
            print(f"✅ JSON parsing successful, got {len(raw_evidence)} items")
            
            # Test evidence item creation
            for i, item in enumerate(raw_evidence):
                print(f"\nItem {i+1}:")
                print(f"  claim: {item.get('claim', 'MISSING')}")
                print(f"  category: {item.get('category', 'MISSING')}")
                print(f"  confidence: {item.get('confidence', 'MISSING')}")
                
                # Test enum validation
                try:
                    category = EvidenceCategory(item["category"])
                    print(f"  ✅ Category enum: {category}")
                except Exception as e:
                    print(f"  ❌ Category enum error: {e}")
                
                try:
                    confidence = ConfidenceLevel(item["confidence"])
                    print(f"  ✅ Confidence enum: {confidence}")
                except Exception as e:
                    print(f"  ❌ Confidence enum error: {e}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response was: {raw_response}")
            
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")

if __name__ == "__main__":
    test_extraction()