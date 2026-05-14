"""
Database operations for BA Assistant
SQLite management for company analysis persistence
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CompanyInputs, PipelineResults

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for company analysis with upsert logic"""
    
    def __init__(self, db_path: str = "company_reality_check.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS company_analysis (
                    website_url TEXT PRIMARY KEY,
                    company_name TEXT,
                    scraped_content TEXT,
                    external_signals TEXT,
                    job_posting TEXT,
                    signals_json TEXT,
                    diagnosis TEXT,
                    hook TEXT,
                    audit TEXT,
                    close_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def upsert_analysis(self, url: str, inputs: 'CompanyInputs', results: 'PipelineResults') -> bool:
        """Insert or update company analysis using proper REPLACE INTO pattern"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use REPLACE INTO for clean upsert (deletes existing row, inserts new)
                conn.execute("""
                    REPLACE INTO company_analysis 
                    (website_url, company_name, scraped_content, external_signals, job_posting,
                     signals_json, diagnosis, hook, audit, close_text, 
                     created_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            COALESCE(
                                (SELECT created_at FROM company_analysis WHERE website_url = ? AND created_at IS NOT NULL), 
                                CURRENT_TIMESTAMP
                            ),
                            CURRENT_TIMESTAMP)
                """, (
                    url, inputs.company_name, inputs.scraped_content, inputs.external_signals,
                    inputs.job_posting, json.dumps(results.signals), results.diagnosis,
                    results.hook, results.audit, results.close, url
                ))
                conn.commit()
                logger.info(f"💾 Clean upsert completed for {url}")
                return True
        except Exception as e:
            logger.error(f"Failed to upsert analysis for {url}: {e}")
            return False
    
    def get_analysis(self, url: str) -> Optional[Tuple['CompanyInputs', 'PipelineResults', datetime]]:
        """Retrieve existing analysis for a URL"""
        try:
            # Import here to avoid circular imports
            from .models import CompanyInputs, PipelineResults
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT company_name, scraped_content, external_signals, job_posting,
                           signals_json, diagnosis, hook, audit, close_text, last_updated
                    FROM company_analysis WHERE website_url = ?
                """, (url,))
                row = cursor.fetchone()
                
                if row:
                    inputs = CompanyInputs(
                        target_url=url,
                        company_name=row[0],
                        scraped_content=row[1],
                        external_signals=row[2],
                        job_posting=row[3]
                    )
                    results = PipelineResults(
                        signals=json.loads(row[4]) if row[4] else {},
                        diagnosis=row[5],
                        hook=row[6],
                        audit=row[7],
                        close=row[8]
                    )
                    last_updated = datetime.fromisoformat(row[9])
                    return inputs, results, last_updated
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve analysis for {url}: {e}")
            return None
    
    def list_companies(self) -> List[Tuple[str, str, datetime]]:
        """List all companies in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT website_url, company_name, last_updated
                    FROM company_analysis
                    ORDER BY last_updated DESC
                """)
                return [(row[0], row[1] or "Unknown", datetime.fromisoformat(row[2])) 
                        for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list companies: {e}")
            return []
    
    def delete_company(self, url: str) -> bool:
        """Delete a company record from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM company_analysis WHERE website_url = ?", (url,))
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"🗑️ Deleted company record for {url}")
                    return True
                else:
                    logger.warning(f"No record found to delete for {url}")
                    return False
        except Exception as e:
            logger.error(f"Failed to delete company record for {url}: {e}")
            return False
    
    def get_context_only(self, url: str) -> Optional[Tuple['CompanyInputs', str]]:
        """Retrieve only context data (inputs) and company name for reprocessing"""
        try:
            # Import here to avoid circular imports
            from .models import CompanyInputs
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT company_name, scraped_content, external_signals, job_posting
                    FROM company_analysis WHERE website_url = ?
                """, (url,))
                row = cursor.fetchone()
                
                if row:
                    inputs = CompanyInputs(
                        target_url=url,
                        company_name=row[0],
                        scraped_content=row[1],
                        external_signals=row[2],
                        job_posting=row[3]
                    )
                    return inputs, row[0] or "Unknown Company"
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve context for {url}: {e}")
            return None