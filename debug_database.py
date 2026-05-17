#!/usr/bin/env python3
"""
Debug script to check database contents for Fresh Air Heating & Cooling
"""

import sqlite3
import json

def check_database():
    """Check what's in the database for Fresh Air Heating & Cooling"""
    
    db_path = "company_reality_check.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find Fresh Air Heating & Cooling entries
        cursor.execute("""
            SELECT website_url, company_name, signals_json, created_at, scraped_content, external_signals
            FROM company_analysis 
            WHERE company_name LIKE '%Fresh Air%' 
            ORDER BY created_at DESC
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ No Fresh Air Heating & Cooling entries found")
        else:
            for i, (url, name, signals_json, created_at, scraped_content, external_signals) in enumerate(results):
                print(f"\n=== Entry {i+1} ===")
                print(f"Company: {name}")
                print(f"URL: {url}")
                print(f"Created: {created_at}")
                print(f"Scraped content length: {len(scraped_content) if scraped_content else 0} chars")
                print(f"External signals length: {len(external_signals) if external_signals else 0} chars")
                
                try:
                    signals = json.loads(signals_json) if signals_json else {}
                    print(f"Signals keys: {list(signals.keys())}")
                    
                    # Check if empty
                    non_empty_fields = {k: v for k, v in signals.items() if v and v != [] and v != ""}
                    print(f"Non-empty fields: {len(non_empty_fields)}")
                    
                    if non_empty_fields:
                        for key, value in non_empty_fields.items():
                            if isinstance(value, list) and len(value) > 3:
                                print(f"  {key}: {value[:3]}... ({len(value)} items)")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print("  ⚠️  ALL SIGNALS ARE EMPTY!")
                        print(f"  Raw signals_json: {signals_json}")
                        
                except Exception as e:
                    print(f"  ❌ Error parsing signals JSON: {e}")
                    print(f"  Raw signals_json: {signals_json[:200]}...")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_database()