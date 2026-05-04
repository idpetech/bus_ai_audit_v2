import streamlit as st
import openai
import json
import hashlib
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from fpdf import FPDF
import markdown
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CompanyInputs:
    linkedin_url: str
    website: str
    job_posting: str

@dataclass
class PipelineResults:
    signals: Dict[str, Any]
    diagnosis: str
    hook: str
    audit: str
    close: str

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
  "technical_complexity_signals": []
}

NO interpretation. NO analysis. ONLY data extraction.""",
            
            "diagnose": """You are a senior systems architect diagnosing AI readiness.

Determine:
1. What the company THINKS it is building vs what it ACTUALLY is building
2. Hidden technical bottlenecks they haven't considered
3. Specific failure modes in their current approach
4. AI maturity classification: Opportunistic | Experimental | Scaling | Native

Be opinionated. Identify blind spots. Focus on mechanisms, not descriptions.
Avoid buzzwords: leverage, unlock, synergy, transformation.

Output 3-4 paragraphs of sharp diagnostic insight.""",
            
            "generate_hook": """You are writing a 5-8 line outbound message to a founder.

Requirements:
- Must contain a tension point or insight they haven't considered
- Founder-facing (not HR or recruiters)
- Specific to their situation
- No generic AI statements
- Must create curiosity without being salesy

Format as a LinkedIn message or email.""",
            
            "generate_audit": """Generate a comprehensive AI Readiness Audit in markdown format.

Structure:
# AI Readiness Audit

## Executive Summary
Brief overview and readiness score (1-10)

## Current State Analysis
What they're building and how

## Readiness Scores
- Data Infrastructure: X/10
- Technical Architecture: X/10  
- Team Capabilities: X/10
- Product-Market Fit: X/10
- AI Integration Maturity: X/10

## Opportunity Map
Specific areas where AI can add value

## Critical Bottlenecks
Technical and organizational constraints

## Recommendations
Prioritized action items with timeframes

## Next Steps
Concrete 30/60/90 day plan

Be specific. Include actual technical recommendations, not generic advice.""",
            
            "generate_close": """Write a brief consultative close (2-3 paragraphs).

Include:
- Short reflection on their situation
- One thoughtful question about their approach
- Optional soft call-to-action (not pushy)

Keep it conversational and consultative."""
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
    
    def _make_llm_call(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o", max_retries: int = 3) -> str:
        """Reusable LLM wrapper with retry handling"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)
    
    def _get_cache_key(self, inputs: CompanyInputs) -> str:
        """Generate cache key from inputs"""
        combined = f"{inputs.linkedin_url}{inputs.website}{inputs.job_posting}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def extract_signals(self, inputs: CompanyInputs) -> Dict[str, Any]:
        """Stage 1: Extract structured signals without interpretation"""
        system_prompt = self.prompts["extract_signals"]

        user_prompt = f"""Extract signals from:

LinkedIn/Company: {inputs.linkedin_url}
Website/Summary: {inputs.website}
Job Posting: {inputs.job_posting}"""

        response = self._make_llm_call(system_prompt, user_prompt)
        logger.info(f"Signals extracted: {response[:200]}...")
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {"error": "Failed to parse signals", "raw_response": response}
    
    def diagnose(self, signals: Dict[str, Any], inputs: CompanyInputs) -> str:
        """Stage 2: Strategic diagnostic reasoning"""
        system_prompt = self.prompts["diagnose"]

        user_prompt = f"""Diagnose this company:

Extracted Signals: {json.dumps(signals, indent=2)}

Original Context:
LinkedIn/Company: {inputs.linkedin_url}
Website: {inputs.website}
Job Posting: {inputs.job_posting}"""

        response = self._make_llm_call(system_prompt, user_prompt)
        logger.info(f"Diagnosis completed: {response[:200]}...")
        return response
    
    def generate_hook(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Stage 3: Generate founder-facing outbound hook"""
        system_prompt = self.prompts["generate_hook"]

        user_prompt = f"""Create hook message based on:

Signals: {json.dumps(signals, indent=2)}
Diagnosis: {diagnosis}"""

        response = self._make_llm_call(system_prompt, user_prompt)
        logger.info("Hook generated")
        return response
    
    def generate_audit(self, signals: Dict[str, Any], diagnosis: str) -> str:
        """Stage 4: Generate structured audit report"""
        system_prompt = self.prompts["generate_audit"]

        user_prompt = f"""Generate audit for:

Signals: {json.dumps(signals, indent=2)}
Diagnosis: {diagnosis}"""

        response = self._make_llm_call(system_prompt, user_prompt)
        logger.info("Audit generated")
        return response
    
    def generate_close(self, signals: Dict[str, Any], audit: str) -> str:
        """Stage 5: Generate conversation close with soft CTA"""
        system_prompt = self.prompts["generate_close"]

        user_prompt = f"""Create close based on:

Company Signals: {json.dumps(signals, indent=2)}
Audit Summary: {audit[:500]}..."""

        response = self._make_llm_call(system_prompt, user_prompt)
        logger.info("Close generated")
        return response
    
    def run_full_pipeline(self, inputs: CompanyInputs) -> PipelineResults:
        """Execute complete 5-stage pipeline"""
        cache_key = self._get_cache_key(inputs)
        
        if cache_key in self.cache:
            logger.info("Returning cached results")
            return self.cache[cache_key]
        
        # Stage 1: Extract signals
        signals = self.extract_signals(inputs)
        
        # Stage 2: Diagnose
        diagnosis = self.diagnose(signals, inputs)
        
        # Stage 3: Generate hook
        hook = self.generate_hook(signals, diagnosis)
        
        # Stage 4: Generate audit
        audit = self.generate_audit(signals, diagnosis)
        
        # Stage 5: Generate close
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

class PDFGenerator:
    def __init__(self):
        self.pdf = FPDF()
        self.pdf.add_page()
        # Use Times font which has better Unicode support
        self.pdf.set_font('Times', 'B', 16)
    
    def _clean_text(self, text: str) -> str:
        """Remove markdown and clean text for PDF"""
        # Convert markdown to HTML then extract text
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, 'html.parser')
        cleaned = soup.get_text()
        # Remove extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        # Replace problematic characters
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(''', "'").replace(''', "'")
        cleaned = cleaned.replace('–', '-').replace('—', '-')
        cleaned = cleaned.replace('…', '...')
        # Remove any remaining non-ASCII characters
        cleaned = ''.join(char if ord(char) < 128 else '?' for char in cleaned)
        return cleaned.strip()
    
    def generate_pdf(self, results: PipelineResults, company_name: str) -> bytes:
        """Generate PDF report"""
        # Header
        self.pdf.cell(0, 10, 'IDPETECH - BA Assistant AI Readiness Audit', ln=True, align='C')
        self.pdf.set_font('Times', '', 10)
        self.pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True, align='C')
        self.pdf.ln(5)
        
        # Company name
        self.pdf.set_font('Times', 'B', 14)
        self.pdf.cell(0, 10, f'Company: {company_name}', ln=True)
        self.pdf.ln(5)
        
        sections = [
            ("First Engagement Hook", results.hook),
            ("Diagnostic Insight", results.diagnosis),
            ("AI Readiness Audit", results.audit),
            ("Conversation Close", results.close)
        ]
        
        for title, content in sections:
            self.pdf.set_font('Times', 'B', 12)
            self.pdf.cell(0, 10, title, ln=True)
            self.pdf.ln(2)
            
            self.pdf.set_font('Times', '', 10)
            cleaned_content = self._clean_text(content)
            
            # Split long text into lines
            lines = cleaned_content.split('\n')
            for line in lines:
                if len(line) > 80:
                    # Wrap long lines
                    words = line.split(' ')
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 80:
                            current_line += word + " "
                        else:
                            if current_line:
                                self.pdf.cell(0, 5, current_line.strip(), ln=True)
                            current_line = word + " "
                    if current_line:
                        self.pdf.cell(0, 5, current_line.strip(), ln=True)
                else:
                    self.pdf.cell(0, 5, line, ln=True)
            self.pdf.ln(5)
        
        return bytes(self.pdf.output())

def main():
    st.set_page_config(
        page_title="IDPETECH · BA Assistant (AI Readiness Audit Engine)",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 IDPETECH · BA Assistant")
    st.subheader("AI Readiness Audit Engine")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'prompts' not in st.session_state:
        ba_temp = BAAssistant("temp")
        st.session_state.prompts = ba_temp._load_prompts()
    if 'ba_assistant' not in st.session_state:
        api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("OpenAI API Key", type="password")
        if api_key:
            st.session_state.ba_assistant = BAAssistant(api_key, st.session_state.prompts)
    
    # Layout: Left panel for inputs, Right panel for outputs
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📋 Company Inputs")
        
        linkedin_url = st.text_area(
            "LinkedIn URL or Company Description",
            placeholder="Enter LinkedIn company URL or describe the company...",
            height=100
        )
        
        website = st.text_area(
            "Website or Company Summary", 
            placeholder="Enter website URL or company summary...",
            height=100
        )
        
        job_posting = st.text_area(
            "Job Posting Text",
            placeholder="Paste the job posting content...",
            height=150
        )
        
        if st.button("🚀 Generate AI Readiness Audit", type="primary"):
            if not all([linkedin_url, website, job_posting]):
                st.error("Please fill in all three input fields.")
            elif 'ba_assistant' not in st.session_state:
                st.error("Please provide OpenAI API key.")
            else:
                with st.spinner("Running AI reasoning pipeline..."):
                    try:
                        inputs = CompanyInputs(linkedin_url, website, job_posting)
                        st.session_state.results = st.session_state.ba_assistant.run_full_pipeline(inputs)
                        st.success("Analysis complete!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        st.divider()
        
        # Prompt Management Section
        with st.expander("⚙️ Prompt Management", expanded=False):
            st.write("**Edit the system prompts used in each stage:**")
            
            prompt_tabs = st.tabs(["Extract", "Diagnose", "Hook", "Audit", "Close"])
            
            with prompt_tabs[0]:
                st.session_state.prompts["extract_signals"] = st.text_area(
                    "Signal Extraction Prompt",
                    value=st.session_state.prompts["extract_signals"],
                    height=200,
                    key="prompt_extract"
                )
            
            with prompt_tabs[1]:
                st.session_state.prompts["diagnose"] = st.text_area(
                    "Diagnostic Prompt",
                    value=st.session_state.prompts["diagnose"],
                    height=200,
                    key="prompt_diagnose"
                )
            
            with prompt_tabs[2]:
                st.session_state.prompts["generate_hook"] = st.text_area(
                    "Hook Generation Prompt",
                    value=st.session_state.prompts["generate_hook"],
                    height=200,
                    key="prompt_hook"
                )
            
            with prompt_tabs[3]:
                st.session_state.prompts["generate_audit"] = st.text_area(
                    "Audit Generation Prompt",
                    value=st.session_state.prompts["generate_audit"],
                    height=200,
                    key="prompt_audit"
                )
            
            with prompt_tabs[4]:
                st.session_state.prompts["generate_close"] = st.text_area(
                    "Close Generation Prompt",
                    value=st.session_state.prompts["generate_close"],
                    height=200,
                    key="prompt_close"
                )
            
            col_reset, col_update, col_save = st.columns(3)
            
            with col_reset:
                if st.button("🔄 Factory Reset"):
                    if 'ba_assistant' in st.session_state:
                        st.session_state.prompts = st.session_state.ba_assistant.reset_to_factory_defaults()
                        st.rerun()
            
            with col_update:
                if st.button("💾 Update Assistant"):
                    if 'ba_assistant' in st.session_state:
                        api_key = st.secrets.get("OPENAI_API_KEY")
                        st.session_state.ba_assistant = BAAssistant(api_key, st.session_state.prompts)
                        st.success("Assistant updated with new prompts!")
            
            with col_save:
                if st.button("⭐ Save as Defaults"):
                    if 'ba_assistant' in st.session_state:
                        if st.session_state.ba_assistant.save_custom_prompts(st.session_state.prompts):
                            st.success("Prompts saved as new defaults!")
                        else:
                            st.error("Failed to save prompts")
            
            st.info("💡 **Tip:** Edit prompts above, click 'Update Assistant', then 'Save as Defaults' to make your changes permanent for future sessions.")
    
    with col2:
        st.header("📊 Analysis Results")
        
        if st.session_state.results:
            results = st.session_state.results
            
            # Hook - Highlighted box
            st.subheader("🎯 First Engagement Hook")
            st.info(results.hook)
            
            # Diagnostic - Expandable
            with st.expander("🔍 Diagnostic Insight", expanded=True):
                st.write(results.diagnosis)
            
            # Audit - Main content
            st.subheader("📋 AI Readiness Audit")
            st.markdown(results.audit)
            
            # Close section
            st.subheader("🤝 Conversation Close")
            st.write(results.close)
            
            # Download options
            st.subheader("💾 Export Options")
            
            col_md, col_pdf = st.columns(2)
            
            with col_md:
                # Markdown download
                markdown_content = f"""# AI Readiness Audit Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## First Engagement Hook
{results.hook}

## Diagnostic Insight  
{results.diagnosis}

## AI Readiness Audit
{results.audit}

## Conversation Close
{results.close}
"""
                st.download_button(
                    label="📄 Download as Markdown",
                    data=markdown_content,
                    file_name=f"ai_readiness_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown"
                )
            
            with col_pdf:
                # PDF download
                try:
                    company_name = results.signals.get('company_name', 'Unknown Company')
                    pdf_generator = PDFGenerator()
                    pdf_bytes = pdf_generator.generate_pdf(results, company_name)
                    st.download_button(
                        label="📄 Download as PDF",
                        data=pdf_bytes,
                        file_name=f"ai_readiness_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {str(e)}")
        else:
            st.info("👈 Enter company information and click 'Generate' to see the AI readiness analysis.")

if __name__ == "__main__":
    main()