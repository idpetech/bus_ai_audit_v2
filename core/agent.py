"""
Agent operations for BA Assistant
Research agent and ICP scoring functionality
"""

import json
import logging
import time
import requests
from typing import Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

import openai
from firecrawl import FirecrawlApp

if TYPE_CHECKING:
    from .models import ResearchSummary, ICPResult, CompanyInputs
    from .scraping import FirecrawlManager

from .scraping import scrape_website

logger = logging.getLogger(__name__)

# Agent configuration
_SEARCH_TIMEOUT = 20          # seconds per search request
_RESEARCH_CREDITS_PER_QUERY = 3  # credits per search query
_ESTIMATED_PIPELINE_CREDITS = 18  # 6 searches × 3 credits each


class FirecrawlSearchClient:
    """Wraps all Firecrawl API calls for agent research"""
    
    def __init__(self, api_key: str):
        self.firecrawl = FirecrawlApp(api_key=api_key)
        self.api_key = api_key
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search using Firecrawl API
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            
        Returns: List of {url, title, content} dicts
        """
        try:
            logger.info(f"🔍 Firecrawl search: {query}")
            
            # Use the existing FirecrawlManager search approach
            search_result = self.firecrawl.search(query)
            
            results = []
            
            # Handle different possible response structures
            if isinstance(search_result, dict):
                if 'results' in search_result:
                    raw_results = search_result['results'][:num_results]
                elif 'data' in search_result:
                    raw_results = search_result['data'][:num_results]
                else:
                    raw_results = [search_result] if search_result else []
            elif hasattr(search_result, 'results'):
                raw_results = search_result.results[:num_results]
            elif hasattr(search_result, 'web'):
                raw_results = search_result.web[:num_results]
            elif isinstance(search_result, list):
                raw_results = search_result[:num_results]
            else:
                logger.warning(f"Unexpected search result structure: {type(search_result)}")
                return []
            
            # Process results into standardized format
            for item in raw_results:
                title = ""
                url = ""
                content = ""
                
                # Handle different item structures
                if isinstance(item, dict):
                    title = item.get('title', '') or item.get('name', '')
                    url = item.get('url', '') or item.get('link', '')
                    content = item.get('content', '') or item.get('description', '') or item.get('snippet', '')
                else:
                    title = getattr(item, 'title', '') or getattr(item, 'name', '')
                    url = getattr(item, 'url', '') or getattr(item, 'link', '')
                    content = getattr(item, 'content', '') or getattr(item, 'description', '') or getattr(item, 'snippet', '')
                
                if title or url:
                    results.append({
                        'url': url,
                        'title': title,
                        'content': content[:800] if content else ""  # Limit content length
                    })
            
            logger.info(f"Found {len(results)} search results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Firecrawl search failed for query '{query}': {e}")
            return []


class ResearchAgent:
    """Six-step company research agent"""
    
    def __init__(self, search_client: FirecrawlSearchClient, openai_client=None, prompts=None):
        self.search_client = search_client
        self.openai_client = openai_client
        self.prompts = prompts or {}
    
    def run(self, company_name: str) -> 'ResearchSummary':
        """
        Execute 6-step research process
        
        Args:
            company_name: Company name to research
            
        Returns: ResearchSummary with all gathered data
        """
        # Import here to avoid circular imports
        from .models import ResearchSummary
        
        start_time = time.time()
        research_log = []
        
        logger.info(f"🔬 Starting research for: {company_name}")
        research_log.append(f"Started research for {company_name}")
        
        # Initialize result fields
        official_website = ""
        funding_stage = "Unknown"
        funding_amount = "Unknown"
        headcount_estimate = "Unknown"
        founded_year = "Unknown"
        decision_maker_name = "Unknown"
        decision_maker_title = "Unknown"
        decision_maker_linkedin = ""
        decision_maker_confidence = "LOW"
        news_signals = []
        research_sources = []
        job_signals = ""
        scraped_content = ""
        
        # Company disambiguation fields
        company_description_full = ""
        company_description_short = ""
        company_description = ""  # Legacy field
        
        # Acquisition status fields
        acquisition_status = "UNKNOWN"
        parent_company = ""
        acquisition_year = ""
        
        # Step 1 — Website discovery
        try:
            logger.info("Step 1: Website discovery")
            query = f"{company_name} official website"
            results = self.search_client.search(query, 5)
            research_sources.extend([r['url'] for r in results if r['url']])
            
            # Pick first result not from LinkedIn, Crunchbase, Twitter, or news sites
            excluded_domains = ['linkedin.com', 'crunchbase.com', 'twitter.com', 'x.com', 'facebook.com', 
                              'news.', 'techcrunch.com', 'venturebeat.com', 'reuters.com', 'bloomberg.com']
            
            for result in results:
                url = result.get('url', '')
                if url and not any(domain in url.lower() for domain in excluded_domains):
                    official_website = url
                    research_log.append(f"Found official website: {url}")
                    break
            
            if not official_website and results:
                official_website = results[0].get('url', '')
                research_log.append(f"Fallback to first result: {official_website}")
            
            # Extract company description from homepage for disambiguation
            if official_website and self.openai_client:
                try:
                    logger.info("Step 1b: Extracting company description for disambiguation")
                    
                    # Find the description from search results
                    for result in results:
                        if result.get('url') == official_website:
                            content = result.get('content', '')
                            if content and len(content) > 100:
                                # Store full scraped content
                                company_description_full = content
                                
                                # Use LLM to extract short search anchor
                                short_anchor_prompt = f"""Extract a SHORT search anchor for this company.

Company name: {company_name}
Website content: {content[:1000]}...

Return EXACTLY 3-5 words maximum describing their core business category.
Examples: "logistics platform", "fleet software", "truck parts", "recruiting platform"

Must be very short for search queries. No articles, no marketing terms.

Short anchor:"""

                                response = self.openai_client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[{"role": "user", "content": short_anchor_prompt}],
                                    temperature=0.1,
                                    max_tokens=20
                                )
                                
                                company_description_short = response.choices[0].message.content.strip()
                                company_description = company_description_short  # For backward compatibility
                                
                                research_log.append(f"Company anchor: {company_description_short}")
                                research_log.append(f"Full description length: {len(company_description_full)} chars")
                                break
                                
                except Exception as desc_error:
                    logger.error(f"Description extraction failed: {desc_error}")
                    research_log.append(f"Description extraction failed: {str(desc_error)}")
                
        except Exception as e:
            research_log.append(f"Step 1 failed: {str(e)}")
            logger.error(f"Step 1 failed: {e}")
        
        # Step 2 — Funding intelligence
        try:
            logger.info("Step 2: Funding intelligence")
            query = f"{company_name} funding raised series investors crunchbase 2024 2025"
            results = self.search_client.search(query, 3)
            research_sources.extend([r['url'] for r in results if r['url']])
            
            # Extract funding information from content
            for result in results:
                content = result.get('content', '').lower()
                if any(term in content for term in ['series', 'funding', 'raised', 'million', 'billion']):
                    # Simple extraction logic
                    if 'series a' in content:
                        funding_stage = "Series A"
                    elif 'series b' in content:
                        funding_stage = "Series B"
                    elif 'series c' in content:
                        funding_stage = "Series C"
                    elif 'series d' in content:
                        funding_stage = "Series D"
                    elif 'seed' in content:
                        funding_stage = "Seed"
                    
                    # Extract amount if present
                    if '$' in content:
                        words = content.split()
                        for i, word in enumerate(words):
                            if '$' in word and i < len(words) - 1:
                                amount = word + " " + words[i+1]
                                funding_amount = amount
                                break
                    
                    break
            
            research_log.append(f"Funding research: {funding_stage} - {funding_amount}")
                
        except Exception as e:
            research_log.append(f"Step 2 failed: {str(e)}")
            logger.error(f"Step 2 failed: {e}")
        
        # Step 2b — Acquisition detection (LLM-verified)
        try:
            logger.info("Step 2b: Acquisition detection (LLM-verified)")
            # Include company description for disambiguation
            search_results_content = []
            
            # Try search with short company description first
            if company_description_short:
                query = f"{company_name} {company_description_short} acquired merger parent company 2022 2023 2024 2025"
                research_log.append(f"Acquisition search with short context: {company_description_short}")
                results = self.search_client.search(query, 3)
                research_sources.extend([r['url'] for r in results if r['url']])
                
                # Prepare search results
                for i, result in enumerate(results):
                    content = result.get('content', '')
                    title = result.get('title', '')
                    url = result.get('url', '')
                    if content or title:
                        search_results_content.append(f"Result {i+1}:\nURL: {url}\nTitle: {title}\nContent: {content[:500]}...")
                
                # If no results with description, try fallback search
                if not search_results_content:
                    research_log.append("No results with description context - trying fallback search")
                    query = f"{company_name} acquired merger parent company subsidiary 2022 2023 2024 2025"
                    results = self.search_client.search(query, 3)
                    research_sources.extend([r['url'] for r in results if r['url']])
                    
                    for i, result in enumerate(results):
                        content = result.get('content', '')
                        title = result.get('title', '')
                        url = result.get('url', '')
                        if content or title:
                            search_results_content.append(f"Result {i+1}:\nURL: {url}\nTitle: {title}\nContent: {content[:500]}...")
            else:
                # No description available - use basic search
                query = f"{company_name} acquired merger parent company subsidiary 2022 2023 2024 2025"
                research_log.append("Acquisition search without description context")
                results = self.search_client.search(query, 3)
                research_sources.extend([r['url'] for r in results if r['url']])
                
                for i, result in enumerate(results):
                    content = result.get('content', '')
                    title = result.get('title', '')
                    url = result.get('url', '')
                    if content or title:
                        search_results_content.append(f"Result {i+1}:\nURL: {url}\nTitle: {title}\nContent: {content[:500]}...")
            
            if search_results_content and self.openai_client:
                # Use LLM to verify acquisition with configurable prompt
                search_results_text = "\n\n".join(search_results_content)
                
                # Get acquisition verification prompt from config
                acquisition_prompt = self.prompts.get("verify_acquisition", 
                    "You are verifying company acquisitions. Return JSON with acquired, acquirer_name, acquisition_year, confidence, evidence fields.")
                
                user_prompt = f"""We are researching {company_name}.
This company is: {company_description_short}
Their website is: {official_website}
Business description: {company_description_full[:500] if company_description_full else 'Not available'}...

Does THIS specific company — not any other company with a similar name — have clear evidence of being acquired?

Search results:
{search_results_text}

If the acquisition evidence refers to a DIFFERENT company with a similar name, return acquired: false.

{acquisition_prompt}"""

                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1
                    )
                    
                    llm_response = response.choices[0].message.content.strip()
                    
                    # Parse JSON response
                    import json
                    import re
                    
                    # Extract JSON from response (strip markdown code fences if present)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = llm_response
                    
                    verification = json.loads(json_str)
                    
                    # Only set ACQUIRED if high confidence and complete data
                    if (verification.get('acquired', False) and 
                        verification.get('confidence') in ['HIGH', 'MEDIUM'] and
                        verification.get('acquirer_name') and 
                        verification.get('acquisition_year')):
                        
                        acquisition_status = "ACQUIRED"
                        parent_company = verification['acquirer_name']
                        acquisition_year = verification['acquisition_year']
                        
                        research_log.append(f"LLM confirmed acquisition: {parent_company} ({acquisition_year})")
                        research_log.append(f"Evidence: {verification.get('evidence', '')}")
                    else:
                        acquisition_status = "UNKNOWN"
                        research_log.append("LLM found no clear acquisition evidence")
                        
                except Exception as llm_error:
                    logger.error(f"LLM verification failed: {llm_error}")
                    acquisition_status = "UNKNOWN"
                    research_log.append(f"LLM verification failed: {str(llm_error)}")
            else:
                # Fallback to UNKNOWN if no LLM client or no results
                acquisition_status = "UNKNOWN"
                research_log.append("No search results or LLM client - acquisition status unknown")
            
            research_log.append(f"Final acquisition status: {acquisition_status}")
                
        except Exception as e:
            research_log.append(f"Step 2b failed: {str(e)}")
            logger.error(f"Step 2b failed: {e}")
            acquisition_status = "UNKNOWN"
        
        # Step 3 — News signals
        try:
            logger.info("Step 3: News signals")
            query = f"{company_name} AI technology hiring news 2024 2025"
            results = self.search_client.search(query, 3)
            research_sources.extend([r['url'] for r in results if r['url']])
            
            for result in results:
                title = result.get('title', '')
                content = result.get('content', '')
                if title and len(title) > 10:
                    news_signals.append(title[:200])
                elif content and len(content) > 20:
                    news_signals.append(content[:200])
            
            research_log.append(f"Found {len(news_signals)} news signals")
                
        except Exception as e:
            research_log.append(f"Step 3 failed: {str(e)}")
            logger.error(f"Step 3 failed: {e}")
        
        # Step 4 — Leadership signals
        try:
            logger.info("Step 4: Leadership signals")
            query = f"{company_name} CTO VP Engineering Head Engineering linkedin"
            results = self.search_client.search(query, 3)
            research_sources.extend([r['url'] for r in results if r['url']])
            
            # Extract leadership information from snippets only
            for result in results:
                content = result.get('content', '') + " " + result.get('title', '')
                content_lower = content.lower()
                
                # Look for titles and names in the same snippet
                titles = ['cto', 'chief technology officer', 'vp engineering', 'head of engineering', 'engineering manager']
                for title in titles:
                    if title in content_lower:
                        decision_maker_title = title.upper()
                        decision_maker_confidence = "HIGH" if 'linkedin' in content_lower else "MEDIUM"
                        
                        # Try to extract name (simple approach - look for capitalized words near title)
                        words = content.split()
                        for i, word in enumerate(words):
                            if title.split()[0] in word.lower():
                                # Look for names in surrounding words
                                for j in range(max(0, i-3), min(len(words), i+4)):
                                    if words[j].istitle() and len(words[j]) > 2 and not any(x in words[j].lower() for x in ['the', 'and', 'for', 'with']):
                                        decision_maker_name = words[j]
                                        break
                                break
                        break
                
                # Look for LinkedIn URLs (but don't fetch them directly)
                if 'linkedin.com/in/' in content:
                    linkedin_start = content.find('linkedin.com/in/')
                    if linkedin_start > 0:
                        linkedin_end = content.find(' ', linkedin_start)
                        if linkedin_end == -1:
                            linkedin_end = len(content)
                        decision_maker_linkedin = content[linkedin_start:linkedin_end]
                        break
            
            research_log.append(f"Leadership: {decision_maker_name} - {decision_maker_title} ({decision_maker_confidence})")
                
        except Exception as e:
            research_log.append(f"Step 4 failed: {str(e)}")
            logger.error(f"Step 4 failed: {e}")
        
        # Step 5 — Job signals
        try:
            logger.info("Step 5: Job signals")
            query = f"{company_name} software engineer developer AI jobs hiring"
            results = self.search_client.search(query, 3)
            research_sources.extend([r['url'] for r in results if r['url']])
            
            # Extract most relevant technical job text
            for result in results:
                content = result.get('content', '')
                if any(term in content.lower() for term in ['engineer', 'developer', 'python', 'javascript', 'react', 'node', 'ai', 'ml']):
                    job_signals = content[:500]  # Take first relevant job posting
                    break
            
            research_log.append(f"Job signals: {len(job_signals)} chars extracted")
                
        except Exception as e:
            research_log.append(f"Step 5 failed: {str(e)}")
            logger.error(f"Step 5 failed: {e}")
        
        # Step 6 — Deep website scrape
        try:
            logger.info("Step 6: Deep website scrape")
            if official_website:
                success, content = scrape_website(official_website, self.search_client.api_key)
                if success:
                    scraped_content = content
                    research_log.append(f"Scraped {len(content)} chars from website")
                else:
                    research_log.append(f"Website scrape failed: {content}")
            else:
                research_log.append("Step 6 skipped: No website found")
                
        except Exception as e:
            research_log.append(f"Step 6 failed: {str(e)}")
            logger.error(f"Step 6 failed: {e}")
        
        duration = time.time() - start_time
        research_log.append(f"Research completed in {duration:.1f}s")
        
        return ResearchSummary(
            company_name=company_name,
            official_website=official_website,
            funding_stage=funding_stage,
            funding_amount=funding_amount,
            headcount_estimate=headcount_estimate,
            founded_year=founded_year,
            decision_maker_name=decision_maker_name,
            decision_maker_title=decision_maker_title,
            decision_maker_linkedin=decision_maker_linkedin,
            decision_maker_confidence=decision_maker_confidence,
            news_signals=news_signals,
            research_sources=list(set(research_sources)),  # Remove duplicates
            research_log=research_log,
            research_duration_seconds=duration,
            job_signals=job_signals,
            scraped_content=scraped_content,
            # Company disambiguation fields
            company_description_full=company_description_full,
            company_description_short=company_description_short,
            company_description=company_description,  # Legacy field
            # Acquisition status fields
            acquisition_status=acquisition_status,
            parent_company=parent_company,
            acquisition_year=acquisition_year
        )


class ICPScorer:
    """Two-pass ICP scoring system"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
    
    def score(self, company_name: str, research: 'ResearchSummary', signals: Dict) -> 'ICPResult':
        """
        Score company using two-pass system: hard disqualifiers then positive scoring
        
        Args:
            company_name: Company name
            research: Research summary
            signals: Extracted signals from pipeline
            
        Returns: ICPResult with scoring decision
        """
        # Import here to avoid circular imports
        from .models import ICPResult
        
        logger.info(f"🎯 Scoring ICP fit for {company_name}")
        
        disqualifiers = []
        fit_reasons = []
        explanation = ""
        
        # Pass 1 — Hard disqualifiers (instant COLD)
        
        # Check acquisition status (first priority) - only disqualify with complete data
        if (research.acquisition_status == "ACQUIRED" and 
            research.parent_company and 
            research.acquisition_year):
            return ICPResult(
                score="COLD",
                decision="DISQUALIFIED",
                confidence="HIGH",
                explanation=f"{company_name} was acquired by {research.parent_company} in {research.acquisition_year}. No longer an independent company. Technical decisions are made at the parent company level.",
                disqualifiers=[
                    f"Acquired by {research.parent_company} in {research.acquisition_year}",
                    "Not an independent decision maker",
                    "Parent company has own technical leadership structure"
                ],
                fit_reasons=[],
                estimated_credits=0,
                alternatives=[]
            )
        
        # Check funding stage
        funding_stage = research.funding_stage.lower()
        if any(stage in funding_stage for stage in ['series c', 'series d', 'series e']):
            disqualifiers.append(f"Late-stage funding: {research.funding_stage}")
        
        # Check headcount (if we had proper data - using placeholder logic)
        try:
            # Simple heuristic from signals or news content
            combined_content = " ".join(research.news_signals).lower()
            if any(phrase in combined_content for phrase in ['500 employees', '1000 employees', 'large team', 'enterprise scale']):
                disqualifiers.append("Large headcount indicated in news signals")
        except:
            pass
        
        # Check if CTO is present with high confidence
        if (research.decision_maker_title.lower() in ['cto', 'chief technology officer'] and 
            research.decision_maker_confidence == 'HIGH'):
            disqualifiers.append(f"CTO identified: {research.decision_maker_name} - {research.decision_maker_title}")
        
        # Check if AI-native product company
        ai_signals = signals.get('ai_mentions', [])
        tech_stack = signals.get('tech_stack', [])
        if (len(ai_signals) > 3 and 
            any(term in ' '.join(ai_signals).lower() for term in ['ai-first', 'ai-native', 'machine learning core', 'ai platform'])):
            disqualifiers.append("AI-native product company detected from signals")
        
        # If hard disqualifiers found, return COLD immediately
        if disqualifiers:
            # Generate explanation
            explanation = f"Company disqualified due to: {', '.join(disqualifiers)}. "
            if research.funding_stage != "Unknown":
                explanation += f"Funding evidence: {research.funding_stage} - {research.funding_amount}. "
            if research.decision_maker_name != "Unknown":
                explanation += f"Leadership: {research.decision_maker_name} confirmed as {research.decision_maker_title}. "
            
            # Generate alternatives using LLM
            alternatives = self._generate_alternatives(company_name, disqualifiers)
            
            return ICPResult(
                score="COLD",
                decision="DISQUALIFIED", 
                confidence="HIGH",
                explanation=explanation,
                disqualifiers=disqualifiers,
                fit_reasons=[],
                estimated_credits=_ESTIMATED_PIPELINE_CREDITS,
                alternatives=alternatives
            )
        
        # Pass 2 — Positive scoring (HOT/WARM)
        score = 0
        
        # +2 if funding stage is seed or series a
        if any(stage in funding_stage for stage in ['seed', 'series a']):
            score += 2
            fit_reasons.append(f"Good funding stage: {research.funding_stage}")
        
        # +2 if headcount 10-100 (placeholder logic)
        if not any(phrase in ' '.join(research.news_signals).lower() for phrase in ['large team', 'enterprise', '500+', '1000+']):
            score += 2
            fit_reasons.append("No large headcount signals detected")
        
        # +2 if no CTO signal found
        if research.decision_maker_title.lower() not in ['cto', 'chief technology officer']:
            score += 2
            fit_reasons.append("No CTO identified in leadership")
        
        # +1 if tech hiring signals present
        if research.job_signals and len(research.job_signals) > 100:
            score += 1
            fit_reasons.append("Active technical hiring detected")
        
        # +1 if recent funding (2024-2025)
        if any(year in research.funding_amount for year in ['2024', '2025']):
            score += 1
            fit_reasons.append("Recent funding activity")
        
        # +1 if industry in preferred list (placeholder)
        industry = signals.get('industry', '').lower()
        preferred_industries = ['saas', 'fintech', 'healthtech', 'edtech', 'logistics', 'commerce']
        if any(pref in industry for pref in preferred_industries):
            score += 1
            fit_reasons.append(f"Preferred industry: {industry}")
        
        # Determine final score
        if score >= 7:
            final_score = "HOT"
            decision = "FIT"
            confidence = "HIGH"
        elif score >= 4:
            final_score = "WARM" 
            decision = "FIT"
            confidence = "MEDIUM"
        else:
            final_score = "COLD"
            decision = "DISQUALIFIED"
            confidence = "LOW"
            # Generate alternatives for low-scoring companies
            alternatives = self._generate_alternatives(company_name, [f"Low ICP score: {score}/9"])
        
        explanation = f"ICP Score: {score}/9. " + " ".join(fit_reasons)
        
        return ICPResult(
            score=final_score,
            decision=decision,
            confidence=confidence, 
            explanation=explanation,
            disqualifiers=disqualifiers,
            fit_reasons=fit_reasons,
            estimated_credits=_ESTIMATED_PIPELINE_CREDITS,
            alternatives=alternatives if decision == "DISQUALIFIED" else []
        )
    
    def _generate_alternatives(self, company_name: str, disqualifiers: List[str]) -> List[Dict]:
        """Generate alternative companies using LLM"""
        try:
            system_prompt = """You are a company research assistant. Generate alternative companies that would be a better ICP fit."""
            
            user_prompt = f"""Given {company_name} is disqualified because {', '.join(disqualifiers)}, suggest 3 alternative companies or company types in the same industry that would fit this ICP:
- 10-100 employees
- Seed to Series B funding
- No CTO on staff
- Not AI-native product companies

Return JSON only:
{{
  "alternatives": [
    {{
      "company_name": "string",
      "reason": "string", 
      "search_term": "string"
    }}
  ]
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            parsed = json.loads(result)
            return parsed.get('alternatives', [])
            
        except Exception as e:
            logger.error(f"Failed to generate alternatives: {e}")
            return [
                {
                    "company_name": "Similar SaaS Companies",
                    "reason": "Look for companies in same industry with smaller teams",
                    "search_term": f"small SaaS companies like {company_name}"
                },
                {
                    "company_name": "Early Stage Competitors", 
                    "reason": "Find seed/Series A companies in similar space",
                    "search_term": f"seed series a {company_name} competitors"
                }
            ]


def research_to_inputs(research: 'ResearchSummary') -> 'CompanyInputs':
    """
    Convert ResearchSummary into CompanyInputs for the existing pipeline.
    """
    from .models import CompanyInputs
    
    return CompanyInputs(
        target_url=research.official_website or f"https://linkedin.com/company/{research.company_name}",
        job_posting=research.job_signals or "",
        scraped_content=research.scraped_content or None,
        external_signals="\n".join(research.news_signals) if research.news_signals else None,
        company_name=research.company_name
    )