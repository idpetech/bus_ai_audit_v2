#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import BAAssistant
import openai

# Test ICP gate with some sample companies
def test_icp_gate():
    assistant = BAAssistant(openai.OpenAI(api_key="test"))
    
    # Test cases
    test_cases = [
        {
            "name": "Linear",
            "signals": {
                "company_name": "Linear",
                "industry": "Project Management",
                "stage": "Growth",
                "funding_stage": "Series B",
                "headcount_estimate": "50-100",
                "tech_stack": ["React", "TypeScript"],
                "business_model_signals": ["SaaS", "B2B"]
            }
        },
        {
            "name": "BaseCamp", 
            "signals": {
                "company_name": "BaseCamp",
                "industry": "Project Management Software", 
                "stage": "Established",
                "funding_stage": "Unknown",
                "headcount_estimate": "Unknown",
                "tech_stack": [],
                "business_model_signals": ["SaaS"]
            }
        },
        {
            "name": "StartupCo",
            "signals": {
                "company_name": "StartupCo",
                "industry": "AI Tools", 
                "stage": "Early",
                "funding_stage": "Seed",
                "headcount_estimate": "10-20",
                "tech_stack": ["Python", "AI/ML"],
                "business_model_signals": ["SaaS", "API"]
            }
        }
    ]
    
    for case in test_cases:
        qualified, reason = assistant.icp_gate(case["signals"], case["name"])
        print(f"\n{case['name']}:")
        print(f"  Qualified: {qualified}")
        print(f"  Reason: {reason}")
        print(f"  Signals: {case['signals']}")

if __name__ == "__main__":
    test_icp_gate()