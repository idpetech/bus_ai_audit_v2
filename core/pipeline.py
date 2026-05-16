"""
AI reasoning pipeline for BA Assistant
Multi-stage analysis and triangulation engine
"""

import hashlib
import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

import openai

if TYPE_CHECKING:
    from .models import CompanyInputs, PipelineResults
    from .scraping import FirecrawlManager
    from .database import DatabaseManager

from .utils import sieve_context

logger = logging.getLogger(__name__)

# Pipeline configuration
_PIPELINE_DELAY = 12          # Seconds between pipeline stages for TPM management


class BAAssistant:
    def __init__(self, api_key: str, prompts: Dict[str, str] = None):
        self.client = openai.OpenAI(api_key=api_key)
        self.cache = {}
        self.prompts = prompts or self._load_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Default system prompts for each stage"""
        return {
            "extract_signals": """You are a signal extraction engine. Extract ONLY structured data from company inputs.

Return valid JSON with these fields:
{
  "company_name": "",
  "industry": "",
  "stage": "",
  "tech_stack": [],
  "role_being_hired": "",
  "role_seniority": "",
  "specific_skills_required": [],
  "business_model_signals": [],
  "scale_indicators": [],
  "ai_mentions": [],
  "technical_complexity_signals": [],
  "architecture_keywords": [],
  "data_flow_indicators": [],
  "scaling_evidence": []
}

NO interpretation. NO analysis. ONLY data extraction.""",
            
            "diagnose": """You are a Senior Principal Architect with 35+ years building distributed systems. You've seen every architectural failure mode and can spot BS from orbit.

CRITICAL: Use triangulated data to expose the gap between marketing narratives and engineering reality.

REQUIRED OUTPUT STRUCTURE:

**What They Think They're Building:**
[Extract from company narrative - their vision, marketing claims, stated technical goals]

**What They're Actually Building:**
[Based on external signals - actual tech stack, hiring patterns, engineering challenges, reviews]

**The Architectural Gap:**
[Specific technical contradictions between claimed capabilities and engineering reality]

**System Failure Modes:**
- Data flow bottlenecks that will break at scale
- Technical debt blocking AI implementation pathways
- Operational complexity gaps they're blind to
- Team capability mismatches vs. stated technical ambitions

**Breaking Points at 10x Scale:**
[Specific architectural chokepoints that will fail based on external signals]

**AI Implementation Reality:**
- AI-Washed: Pure marketing play, traditional CRUD underneath
- AI-Assisted: Bolting AI onto existing architectures
- AI-Native: Core business logic requires AI to function
- Non-AI: Traditional software, no meaningful AI dependency

**Technical Classification Evidence:**
[Justify with concrete evidence from external signals vs. company claims]

Be brutally honest. No sugar-coating. Focus on what breaks systems.""",
            
            "generate_hook": """You are a Senior Principal Architect reaching out peer-to-peer. No introduction. No fluff. Start with a direct architectural observation.

REQUIREMENTS:
- 2-4 sentences maximum
- Lead with specific technical contradiction (hiring vs. claims vs. stack)
- Frame as architectural curiosity, not accusation
- Reference concrete external signals (not generic observations)
- End with direct technical question

TONE: Senior technical peer. Skeptical but respectful.

AVOID:
- Any introduction ("I noticed", "Hi", "Hope you're well")
- Buzzwords (scale, optimize, leverage, unlock, transform)
- Generic AI statements
- Sales language or multiple topics

FORMULA:
[Technical observation] + [Specific contradiction] + [Direct question]

Example: "Your team is hiring Node.js engineers while positioning as an AI-first company, but I don't see ML infrastructure in the stack. What's the actual data flow architecture you're building?"

Start immediately with the technical tension. No preamble.
""",
            
            "generate_audit": """You are a Senior Principal Architect conducting a brutal technical assessment. Focus on failure modes and architectural realities.

# AI Readiness Audit

## Executive Summary
- Current AI Classification: [AI-Washed/AI-Assisted/AI-Native/Non-AI]
- Reality Gap Score: X/10 (claims vs. actual technical capability)
- Primary Constraint: [The one architectural bottleneck that will break first]

## System Reality
What they actually built vs what they claim to be building.

## Architectural Constraint Analysis
**Data Architecture:** [Specific data flow bottlenecks and pipeline limitations]
**Infrastructure Reality:** [Actual processing constraints vs. AI requirements]  
**Team Technical Debt:** [Skills gaps that will cause implementation failures]
**Legacy System Constraints:** [Technical debt blocking AI integration pathways]
**Operational Maturity Gaps:** [Process/tooling failures at scale]

## Failure Mode Predictions
Top 3 ways their AI implementation will break, with specific technical triggers.

## Contrarian Technical Assessment
**What consultants are telling them:** [Standard advice they're receiving]
**Architectural reality:** [Uncomfortable technical truths they're avoiding]
**The technical bet:** [What must be architecturally true for success]

## Mechanism-Based Interventions
Concrete technical changes, not strategy:
- [Specific architectural modifications with failure prevention]
- [Data flow optimizations with measurable outcomes]
- [Infrastructure decisions that prevent known failure modes]

No buzzwords. No "best practices." Focus on what breaks distributed systems.""",
            
            "generate_close": """You are a Senior Architect delivering a final technical observation. Cut through the noise.

Requirements:
- 2-3 sentences maximum
- Surface one core architectural contradiction
- No questions, no offers, no next steps
- End with direct statement: what they're building vs. what they think they're building

Avoid: consulting language, encouragement, solutions, positive spin

Tone: Peer-level technical honesty. No sugar-coating.

Example: "Your AI roadmap assumes clean data flows, but your hiring suggests you're still fighting legacy ETL pipelines. You're building a data cleanup operation, not an AI product."

Direct. Final. Architectural truth.""",
            
            "verify_acquisition": """You are verifying whether a SPECIFIC company has been acquired. Be conservative — only confirm an acquisition if you find explicit clear evidence about THIS specific company, not any other company with a similar name.

Return JSON only:
{
  "acquired": true|false,
  "acquirer_name": "",
  "acquisition_year": "",
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence": "exact phrase that confirms this"
}

CRITICAL DISAMBIGUATION RULES:
- acquired = true ONLY if results explicitly state THIS SPECIFIC COMPANY was purchased/acquired/merged
- If the acquisition evidence refers to a DIFFERENT company with a similar name, return acquired: false
- Company description and website must match the acquisition target
- A 'citation' in text is NOT an acquisition
- A 'partner' is NOT an acquisition  
- If unsure about company identity, return acquired: false
- acquirer_name must be a real company name
- acquisition_year must be a 4-digit year
- If either is missing, return acquired: false"""
        }
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts from custom file if exists, otherwise use defaults"""
        custom_prompts_file = "custom_prompts.json"
        if os.path.exists(custom_prompts_file):
            try:
                with open(custom_prompts_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load custom prompts: {e}")
        return self._get_default_prompts()
    
    def save_custom_prompts(self, prompts: Dict[str, str]) -> bool:
        """Save custom prompts as new defaults"""
        try:
            with open("custom_prompts.json", 'w') as f:
                json.dump(prompts, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Could not save custom prompts: {e}")
            return False
    
    def reset_to_factory_defaults(self) -> Dict[str, str]:
        """Reset to factory defaults and remove custom file"""
        try:
            if os.path.exists("custom_prompts.json"):
                os.remove("custom_prompts.json")
        except Exception as e:
            logger.warning(f"Could not remove custom prompts file: {e}")
        return self._get_default_prompts()
    
    def _make_llm_call(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o", max_retries: int = 3, stage: str = "unknown") -> str:
        """Reusable LLM wrapper with retry handling and TPM management"""
        
        # SIGNAL SIEVE: Apply context truncation to stay under TPM limits
        from .utils import MAX_CONTEXT_TOKENS
        sieved_prompt = sieve_context(user_prompt, MAX_CONTEXT_TOKENS)
        
        # TEMPERATURE CONTROL: Technical precision for critical stages
        temp = 0.4 if stage in ["diagnose", "generate_hook"] else 0.7
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🤖 {stage.upper()}: Making LLM call (temp={temp})")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": sieved_prompt}
                    ],
                    temperature=temp
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)
    
    def _get_cache_key(self, inputs: 'CompanyInputs') -> str:
        """Generate cache key from inputs"""
        combined = f"{inputs.target_url}{inputs.job_posting or ''}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, stripping markdown code fences if present."""
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)
        return json.loads(stripped)

    def extract_signals(self, inputs: 'CompanyInputs') -> Dict[str, Any]:
        """Stage 1: Extract structured signals without interpretation"""
        system_prompt = self.prompts["extract_signals"]

        user_prompt = f"""Extract signals from triangulated company data:

Target URL: {inputs.target_url}
Company: {inputs.company_name or 'Unknown'}

{inputs.combined_context}"""

        response = self._make_llm_call(system_prompt, user_prompt, stage="extract_signals")
        logger.info(f"Signals extracted: {response[:200]}...")

        try:
            return self._extract_json(response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse signals", "raw_response": response}
    
    def diagnose(self, signals: Dict[str, Any], inputs: 'CompanyInputs') -> str:
        """Stage 2: Agentic reality check using triangulated data"""
        system_prompt = self.prompts["diagnose"]

        user_prompt = f"""Perform reality check on company using triangulated intelligence:

Company: {inputs.company_name or 'Unknown'}
URL: {inputs.target_url}

EXTRACTED SIGNALS: {json.dumps(signals, indent=2)}

TRIANGULATED DATA:
{inputs.combined_context}

FOCUS: Use external signals to challenge company self-perception. Expose contradictions between what they claim vs what external sources reveal about their technical reality."""

        response = self._make_llm_call(system_prompt, user_prompt, max_retries=3, stage="diagnose")
        logger.info(f"Agentic diagnosis completed: {response[:200]}...")
        return response
    
    def generate_hook(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Stage 3: Generate founder-facing outbound hook"""
        system_prompt = self.prompts["generate_hook"]

        user_prompt = f"""Create hook message based on:

Signals: {json.dumps(signals, indent=2)}
Diagnosis: {diagnosis}"""

        response = self._make_llm_call(system_prompt, user_prompt, stage="generate_hook")
        logger.info("Hook generated")
        return response
    
    def generate_audit(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Stage 4: Generate structured audit report"""
        system_prompt = self.prompts["generate_audit"]

        user_prompt = f"""Generate audit for:

Signals: {json.dumps(signals, indent=2)}
Diagnosis: {diagnosis}"""

        response = self._make_llm_call(system_prompt, user_prompt, stage="generate_audit")
        logger.info("Audit generated")
        return response
    
    def generate_close(self, signals: Dict[str, Any], audit: str) -> str:
        """Stage 5: Generate conversation close with soft CTA"""
        system_prompt = self.prompts["generate_close"]

        user_prompt = f"""Create close based on:

Company Signals: {json.dumps(signals, indent=2)}
Audit Summary: {audit[:500]}..."""

        response = self._make_llm_call(system_prompt, user_prompt, stage="generate_close")
        logger.info("Close generated")
        return response
    
    def run_full_pipeline(self, inputs: 'CompanyInputs') -> 'PipelineResults':
        """Execute complete 5-stage pipeline"""
        # Import here to avoid circular imports
        from .models import PipelineResults
        
        cache_key = self._get_cache_key(inputs)
        
        if cache_key in self.cache:
            logger.info("Returning cached results")
            return self.cache[cache_key]
        
        # Stage 1: Extract signals
        logger.info(f"🔄 Stage 1/5: Extracting structured signals...")
        signals = self.extract_signals(inputs)
        
        # WAIT & PULSE: TPM rate limiting between extract and diagnose
        logger.info(f"⏳ Waiting {_PIPELINE_DELAY}s for TPM bucket refill...")
        time.sleep(_PIPELINE_DELAY)
        
        # Stage 2: Diagnose
        logger.info(f"🔄 Stage 2/5: Running agentic diagnosis...")
        diagnosis = self.diagnose(signals, inputs)
        
        # Stage 3: Generate hook
        logger.info(f"🔄 Stage 3/5: Generating founder hook...")
        hook = self.generate_hook(signals, diagnosis)
        
        # Stage 4: Generate audit
        logger.info(f"🔄 Stage 4/5: Building audit report...")
        audit = self.generate_audit(signals, diagnosis)
        
        # Stage 5: Generate close
        logger.info(f"🔄 Stage 5/5: Finalizing conversation close...")
        close = self.generate_close(signals, audit)
        
        results = PipelineResults(
            signals=signals,
            diagnosis=diagnosis,
            hook=hook,
            audit=audit,
            close=close
        )
        
        # Cache results
        self.cache[cache_key] = results
        logger.info("Pipeline completed and cached")
        
        return results
    
    def run_triangulation(self, url: str, job_posting: Optional[str] = None, 
                         firecrawl_manager: 'FirecrawlManager' = None, 
                         db_manager: 'DatabaseManager' = None) -> Tuple['CompanyInputs', 'PipelineResults']:
        """
        Agentic Triangulation Loop: Automated reality check engine
        
        Step 1 (Scrape): Extract company's self-perception narrative
        Step 2 (Search): Hunt for external signals about technical reality  
        Step 3 (Cross-Reference): Feed both into diagnosis for contradiction analysis
        
        Returns: (CompanyInputs with triangulated data, PipelineResults)
        """
        # Import here to avoid circular imports
        from .models import CompanyInputs
        
        logger.info(f"🤖 Starting agentic triangulation for {url}")
        
        # Step 1: Scrape company narrative (self-perception)
        logger.info("⚗️ Step 1: Distilling company self-perception narrative...")
        scrape_success, scraped_content, company_name = firecrawl_manager.scrape_company_narrative(url)
        
        if not scrape_success:
            logger.error(f"Failed to scrape {url}: {scraped_content}")
            raise Exception(f"Scraping failed: {scraped_content}")
        
        # Step 2: Search for external signals (technical reality)
        logger.info("🔍 Step 2: Hunting for external technical contradiction signals...")
        search_success, external_signals = firecrawl_manager.search_external_signals(company_name, url)
        
        if not search_success:
            logger.warning(f"No external signals found: {external_signals}")
            external_signals = "No external signals found. Analysis will be based solely on company narrative."
        
        # Step 3: Cross-reference both sources for reality check
        logger.info("⚖️ Step 3: Verifying tech-stack contradictions vs. company claims...")
        
        # Create enriched inputs with triangulated data
        inputs = CompanyInputs(
            target_url=url,
            job_posting=job_posting,
            scraped_content=scraped_content,
            external_signals=external_signals,
            company_name=company_name
        )
        
        # Run the analysis pipeline with triangulated data
        results = self.run_full_pipeline(inputs)
        
        # Persist to database if manager provided
        if db_manager:
            db_manager.upsert_analysis(url, inputs, results)
            logger.info(f"💾 Analysis persisted to database for {url}")
        
        logger.info(f"🎯 Triangulation complete for {company_name}")
        return inputs, results