"""
Web scraping operations for BA Assistant
Firecrawl-based web scraping and search functionality
"""

import logging
from typing import Tuple, Optional, List
from urllib.parse import urlparse
from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)

# Scraping configuration constants
_SCRAPE_TIMEOUT = 12          # seconds per request
_SCRAPE_MAX_CHARS = 40_000    # ~10k tokens; keeps LLM context manageable
_FIRECRAWL_SEARCH_LIMIT = 2   # Hard limit for external signals


def scrape_page(url: str, api_key: str) -> Tuple[bool, str, str]:
    """
    Scrape a single page using Firecrawl API.
    
    Args:
        url: URL to scrape
        api_key: Firecrawl API key
    
    Returns: (success: bool, content: str, title: str)
    """
    try:
        firecrawl = FirecrawlApp(api_key=api_key)
        
        scrape_result = firecrawl.scrape({
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
            "timeout": 25000
        })
        
        if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
            content = scrape_result.markdown
            title = ""
            
            # Extract title from metadata if available
            if hasattr(scrape_result, 'metadata') and scrape_result.metadata:
                if hasattr(scrape_result.metadata, 'title'):
                    title = scrape_result.metadata.title
                elif isinstance(scrape_result.metadata, dict) and scrape_result.metadata.get('title'):
                    title = scrape_result.metadata['title']
            
            if not title:
                title = "Untitled"
                
            return True, content, title
        else:
            return False, "No content returned from Firecrawl", ""
            
    except Exception as e:
        logger.error(f"Firecrawl scraping failed for {url}: {e}")
        return False, f"Scraping error: {str(e)}", ""


def scrape_website(url: str, api_key: str) -> Tuple[bool, str]:
    """
    Fetch a URL and convert its page to clean Markdown using Firecrawl.

    Args:
        url: URL to scrape
        api_key: Firecrawl API key

    Returns (success, content).  On failure, content is a human-readable
    error message rather than a traceback.
    
    Note: This maintains backward compatibility with the original signature
    while using Firecrawl instead of requests + BeautifulSoup.
    """
    try:
        firecrawl = FirecrawlApp(api_key=api_key)
        
        # Use simple scrape for single page (like existing FirecrawlManager)
        logger.info(f"Scraping {url} with Firecrawl")
        scrape_result = firecrawl.scrape(url)
        
        if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
            content = scrape_result.markdown
            
            # Apply character limit like original function
            if len(content) > _SCRAPE_MAX_CHARS:
                content = content[:_SCRAPE_MAX_CHARS] + "\n\n[Content truncated — page too long]"
            
            logger.info(f"Scraped {url}: {len(content)} chars")
            return True, content
        else:
            return False, "No content returned from Firecrawl"
            
    except Exception as e:
        logger.error(f"Firecrawl scraping failed for {url}: {e}")
        return False, f"Scraping error: {str(e)}"


class FirecrawlManager:
    """Manages Firecrawl operations for scraping and searching"""
    
    def __init__(self, api_key: str):
        self.firecrawl = FirecrawlApp(api_key=api_key)
    
    def scrape_company_narrative(self, url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Scrape the main company website to extract self-perception narrative.
        Returns (success, content_or_error, company_name)
        OPTIMIZED: Credit-efficient with basic proxy and markdown-only extraction
        """
        try:
            logger.info(f"🔧 Credit-efficient scraping: {url}")
            
            # FIRECRAWL CREDIT OPTIMIZATION: Simple API call with error handling
            try:
                # Start with minimal parameters for compatibility
                scrape_result = self.firecrawl.scrape(url)
            except Exception as e:
                logger.warning(f"Initial scrape failed: {e}")
                # Fallback to very basic scrape
                try:
                    scrape_result = self.firecrawl.scrape(url=url)
                except Exception as e2:
                    logger.error(f"Fallback scrape also failed: {e2}")
                    raise e2
            
            # Check if scrape was successful and extract content
            if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
                content = scrape_result.markdown
                metadata = getattr(scrape_result, 'metadata', {})
                
                # Extract company name from title or URL
                company_name = None
                if hasattr(metadata, 'title') and metadata.title:
                    # Try to extract company name from title
                    title = metadata.title
                    # Remove common suffixes
                    for suffix in [" - Home", " | Home", " - Company", " Inc.", " LLC", " Corp."]:
                        title = title.replace(suffix, "")
                    company_name = title.split(" - ")[0].split(" | ")[0].strip()
                elif isinstance(metadata, dict) and metadata.get("title"):
                    title = metadata["title"]
                    for suffix in [" - Home", " | Home", " - Company", " Inc.", " LLC", " Corp."]:
                        title = title.replace(suffix, "")
                    company_name = title.split(" - ")[0].split(" | ")[0].strip()
                
                if not company_name or len(company_name) > 50:  # Reject overly long/descriptive titles
                    # Fallback to domain name
                    parsed = urlparse(url)
                    company_name = parsed.netloc.replace("www.", "").split(".")[0].title()
                
                logger.info(f"Extracted company name: '{company_name}' from {url}")
                
                logger.info(f"Successfully scraped {len(content)} chars from {url}")
                return True, content, company_name
            else:
                error_msg = f"No content returned from {url}"
                logger.error(f"Firecrawl scraping failed: {error_msg}")
                return False, f"Scraping failed: {error_msg}", None
                
        except Exception as e:
            logger.error(f"Error during Firecrawl scraping: {e}")
            return False, f"Scraping error: {str(e)}", None
    
    def search_external_signals(self, company_name: str, url: str = None) -> Tuple[bool, str]:
        """
        Search for external signals about the company's technical reality.
        Returns (success, aggregated_content_or_error)
        OPTIMIZED: Hard limit to 2 results per query, targeted domain searches
        """
        try:
            logger.info(f"🎯 Targeted external signal hunt: {company_name}")
            
            # Create domain-based name for more targeted searches
            domain_name = None
            if url:
                parsed = urlparse(url)
                domain_name = parsed.netloc.replace("www.", "").split(".")[0]
            
            # AGGRESSIVE CREDIT CONSERVATION: Simplified high-value queries
            search_queries = []
            
            # Prioritize domain name over potentially generic company descriptions
            if domain_name and domain_name.strip():
                search_queries.extend([
                    f'{domain_name} engineering team',
                    f'{domain_name} software developer'
                ])
            
            # Only add company name if it's specific (not a tagline) and different from domain
            elif company_name and len(company_name) < 30:
                search_queries.extend([
                    f'{company_name} engineering team',
                    f'{company_name} software engineer'
                ])
            
            # Fallback to very basic queries if nothing else
            if not search_queries and company_name:
                search_queries.append(company_name)
            
            # HARD LIMIT: Only top 2 queries to minimize credit burn
            search_queries = search_queries[:2]
            logger.info(f"🔥 FAIL FAST: {len(search_queries)} targeted queries: {search_queries}")
            
            all_results = []
            
            for query in search_queries:
                try:
                    logger.info(f"🔍 Searching: {query}")
                    # CREDIT GUARDRAIL: Simple search call with error handling
                    try:
                        search_result = self.firecrawl.search(query)
                        logger.info(f"Search result type: {type(search_result)}")
                        logger.info(f"Search result: {search_result}")
                    except Exception as search_api_error:
                        logger.warning(f"Search API call failed: {search_api_error}")
                        # Try alternative search parameters
                        try:
                            search_result = self.firecrawl.search(query=query)
                        except Exception as e2:
                            logger.warning(f"Alternative search also failed: {e2}")
                            continue
                    
                    # Handle different possible response structures
                    results_found = False
                    
                    # Try different response structure patterns
                    if isinstance(search_result, dict):
                        # Handle dictionary response
                        if 'results' in search_result:
                            results = search_result['results'][:_FIRECRAWL_SEARCH_LIMIT]
                        elif 'data' in search_result:
                            results = search_result['data'][:_FIRECRAWL_SEARCH_LIMIT]
                        else:
                            results = [search_result] if search_result else []
                    elif hasattr(search_result, 'results'):
                        results = search_result.results[:_FIRECRAWL_SEARCH_LIMIT]
                    elif hasattr(search_result, 'web'):
                        results = search_result.web[:_FIRECRAWL_SEARCH_LIMIT]
                    elif isinstance(search_result, list):
                        results = search_result[:_FIRECRAWL_SEARCH_LIMIT]
                    else:
                        logger.warning(f"Unexpected search result structure: {type(search_result)}")
                        continue
                    
                    # Process results
                    for item in results:
                        title = ""
                        content = ""
                        url = ""
                        
                        # Handle different item structures
                        if isinstance(item, dict):
                            title = item.get('title', '') or item.get('name', '')
                            url = item.get('url', '') or item.get('link', '')
                            content = item.get('content', '') or item.get('description', '') or item.get('snippet', '')
                        else:
                            title = getattr(item, 'title', '') or getattr(item, 'name', '')
                            url = getattr(item, 'url', '') or getattr(item, 'link', '')
                            content = getattr(item, 'content', '') or getattr(item, 'description', '') or getattr(item, 'snippet', '')
                        
                        # Create result if we have at least title or URL
                        if title or url:
                            if content and len(content) > 20:
                                result_summary = f"**Source: {title}**\nURL: {url}\nContent: {content[:800]}..."
                            else:
                                result_summary = f"**External Signal: {title}**\nURL: {url}\nFound via search - indicates external mention"
                            all_results.append(result_summary)
                            results_found = True
                    
                    if results_found:
                        logger.info(f"Found {len(results)} external signals for query: {query}")
                    else:
                        logger.warning(f"No results found for query: {query}")
                                
                except Exception as search_error:
                    logger.warning(f"Search query '{query}' failed: {search_error}")
                    continue
            
            if all_results:
                aggregated_content = "\n\n---\n\n".join(all_results)
                logger.info(f"Found {len(all_results)} external signal sources")
                return True, aggregated_content
            else:
                logger.warning(f"No external signals found for {company_name}")
                return False, f"No external signals found for {company_name}"
                
        except Exception as e:
            logger.error(f"Error during external signal search: {e}")
            return False, f"Search error: {str(e)}"
    
    def _scrape_search_result_url(self, url: str) -> Optional[str]:
        """
        Scrape individual search result URLs for actual content.
        Focus on domains that Firecrawl supports well.
        """
        try:
            # Firecrawl-supported domains that are likely to have good content
            scrapable_domains = ['glassdoor.com', 'stackoverflow.com', 'github.com', 'medium.com', 
                               'dev.to', 'hackernoon.com', 'blog.', 'docs.']
            
            # Skip Reddit and other unsupported sites
            unsupported_domains = ['reddit.com', 'facebook.com', 'twitter.com', 'linkedin.com']
            
            if any(domain in url.lower() for domain in unsupported_domains):
                return None
                
            if not any(domain in url.lower() for domain in scrapable_domains):
                return None
            
            # CREDIT-EFFICIENT: Simple scrape for search results
            try:
                scrape_result = self.firecrawl.scrape(url)
            except Exception as e:
                logger.warning(f"Search result scrape failed: {e}")
                return None
            
            if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
                content = scrape_result.markdown.strip()
                if len(content) > 100:  # Only return substantial content
                    return content
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to scrape search result URL {url}: {e}")
            return None