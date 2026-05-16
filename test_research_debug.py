#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import openai
from app import ResearchAgent

def test_research():
    client = openai.OpenAI(api_key="fake-key")
    agent = ResearchAgent(client, None, None, 10)  # 10 second timeout
    
    # Test with a known tech company
    try:
        print("Testing research for: Linear")
        inputs, summary = agent.research_company("Linear")
        
        print(f"\nCompany: {summary.company_name}")
        print(f"Website: {summary.official_website}")
        print(f"Industry: {summary.industry}")
        print(f"Stage: {summary.company_stage}")
        print(f"Funding: {summary.funding_stage}")
        print(f"Headcount: {summary.headcount_estimate}")
        print(f"Founded: {summary.founded_year}")
        print(f"News signals: {len(summary.news_signals)}")
        
        print("\nResearch Log:")
        for log in agent.research_log:
            print(f"  {log}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_research()