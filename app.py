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
from docx import Document
from docx.shared import Inches
from docx.enum.style import WD_STYLE_TYPE
import io

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
  "technical_complexity_signals": [],
  "architecture_keywords": [],
  "data_flow_indicators": [],
  "scaling_evidence": []
}

NO interpretation. NO analysis. ONLY data extraction.""",
            
            "diagnose": """You are a systems architect performing a reality check on AI ambitions.

REQUIRED OUTPUT STRUCTURE:

**What They Think They're Building:**
[Extract their self-perception from job posts, marketing language, and stated goals]

**What They're Actually Building:**
[Based on technical signals - stack, architecture, hiring patterns]

**The Gap:**
[Specific contradictions between perception and technical reality]

**Hidden Bottlenecks:**
- Data architecture constraints they haven't considered
- Technical debt that will block AI implementation
- Operational complexity they're underestimating
- Team capability gaps relative to AI ambitions

**Scaling Failure Points:**
[Specific technical chokepoints that will break at 10x scale]

**AI System Classification:**
- AI-Washed: Marketing AI but building traditional systems
- AI-Assisted: Adding AI features to existing products  
- AI-Native: Core product requires AI to function
- Non-AI: Traditional software with no AI dependency

**Classification Reasoning:**
[Justify classification with specific evidence]

NO BUZZWORDS. Be surgically precise about technical realities.""",
            
            "generate_hook": """You are writing a direct, founder-to-founder message that exposes a tension.

REQUIREMENTS:
- 3-5 sentences maximum
- Identify one contradiction between what they claim and what they're actually building
- Frame as genuine curiosity, not accusation
- Reference specific technical signals from their hiring/stack
- End with a simple, non-sales question

TONE: Technical peer, not consultant. Direct but respectful.

AVOID:
- Any buzzwords (leverage, unlock, transform, scale, optimize)
- Generic AI statements
- Sales language
- Multiple topics

FORMULA:
1. Observe their stated direction
2. Note technical contradiction 
3. Express curiosity about the gap
4. Simple question

Example style: "Noticed you're hiring for X and talking about Y, but your stack suggests Z. Curious how you're thinking about that gap - is there something I'm missing about the architecture?"
""",
            
            "generate_audit": """Generate a mechanism-driven AI Readiness Audit. Focus on what will break, not what sounds good.

# AI Readiness Audit

## Executive Summary
- Current AI Classification: [AI-Washed/AI-Assisted/AI-Native/Non-AI]
- Reality Check Score: X/10 (gap between claims and capability)
- Primary Constraint: [The one thing that will break first]

## System Reality
What they actually built vs what they claim to be building.

## Constraint Analysis
**Data Architecture:** [Specific data flow bottlenecks]
**Compute Infrastructure:** [Actual processing limitations]  
**Team Capabilities:** [Skills gaps that will cause failures]
**Technical Debt:** [Legacy constraints blocking AI implementation]
**Operational Maturity:** [Process gaps at scale]

## Failure Mode Predictions
The top 3 ways their AI ambitions will fail, with specific technical triggers.

## Contrarian Insights
**What everyone else is telling them:** [Common advice they're getting]
**What's actually true:** [Uncomfortable reality they need to face]
**The bet they're really making:** [What has to be true for them to succeed]

## Mechanism-Based Recommendations
Specific technical interventions, not strategic advice:
- [Concrete system changes with clear outcomes]
- [Process modifications with measurable effects]
- [Architecture decisions with failure prevention]

NO BUZZWORDS. NO "BEST PRACTICES." Focus on what breaks systems and how to prevent it.""",
            
            "generate_close": """Write 2-3 sentences that surface one uncomfortable truth about their approach.

Requirements:
- Reference a specific technical tension from the analysis
- No questions, no CTAs, no next steps
- End with a direct statement about what they're actually building vs what they think they're building

Avoid: consulting language, encouragement, positivity, solutions

Style: Technical peer delivering honest feedback"""
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
        pass
    
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
    
    def _add_content_to_pdf(self, pdf: FPDF, title: str, content: str, company_name: str = None):
        """Add content section to PDF"""
        # Header
        pdf.set_font('Times', 'B', 16)
        pdf.cell(0, 10, f'IDPETECH - BA Assistant: {title}', ln=True, align='C')
        pdf.set_font('Times', '', 10)
        pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True, align='C')
        pdf.ln(5)
        
        # Company name if provided
        if company_name:
            pdf.set_font('Times', 'B', 14)
            pdf.cell(0, 10, f'Company: {company_name}', ln=True)
            pdf.ln(5)
        
        # Content
        pdf.set_font('Times', '', 10)
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
                            pdf.cell(0, 5, current_line.strip(), ln=True)
                        current_line = word + " "
                if current_line:
                    pdf.cell(0, 5, current_line.strip(), ln=True)
            else:
                pdf.cell(0, 5, line, ln=True)
    
    def generate_section_pdf(self, title: str, content: str, company_name: str = None) -> bytes:
        """Generate PDF for individual section"""
        pdf = FPDF()
        pdf.add_page()
        self._add_content_to_pdf(pdf, title, content, company_name)
        return bytes(pdf.output())
    
    def generate_pdf(self, results: PipelineResults, company_name: str) -> bytes:
        """Generate complete PDF report"""
        pdf = FPDF()
        pdf.add_page()
        
        # Header for complete report
        pdf.set_font('Times', 'B', 16)
        pdf.cell(0, 10, 'IDPETECH - BA Assistant: Complete AI Readiness Report', ln=True, align='C')
        pdf.set_font('Times', '', 10)
        pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True, align='C')
        pdf.ln(5)
        
        # Company name
        pdf.set_font('Times', 'B', 14)
        pdf.cell(0, 10, f'Company: {company_name}', ln=True)
        pdf.ln(5)
        
        sections = [
            ("First Engagement Hook", results.hook),
            ("Diagnostic Insight", results.diagnosis),
            ("AI Readiness Audit", results.audit),
            ("Conversation Close", results.close)
        ]
        
        for title, content in sections:
            pdf.set_font('Times', 'B', 12)
            pdf.cell(0, 10, title, ln=True)
            pdf.ln(2)
            
            pdf.set_font('Times', '', 10)
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
                                pdf.cell(0, 5, current_line.strip(), ln=True)
                            current_line = word + " "
                    if current_line:
                        pdf.cell(0, 5, current_line.strip(), ln=True)
                else:
                    pdf.cell(0, 5, line, ln=True)
            pdf.ln(5)
        
        return bytes(pdf.output())

class WordGenerator:
    def __init__(self):
        pass
    
    def _clean_text_for_word(self, text: str) -> str:
        """Clean and prepare text for Word document"""
        # Convert markdown to plain text while preserving structure
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, 'html.parser')
        cleaned = soup.get_text()
        
        # Clean up spacing
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()
    
    def _add_markdown_content(self, doc: Document, content: str):
        """Add markdown content to Word document with proper formatting"""
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # Handle headers
            if line.startswith('# '):
                heading = doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                heading = doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                heading = doc.add_heading(line[4:], level=3)
            elif line.startswith('**') and line.endswith('**'):
                # Bold text
                p = doc.add_paragraph()
                run = p.add_run(line[2:-2])
                run.bold = True
            elif line.startswith('- '):
                # Bullet point
                doc.add_paragraph(line[2:], style='List Bullet')
            else:
                # Regular paragraph
                doc.add_paragraph(line)
            
            i += 1
    
    def generate_section_word(self, title: str, content: str, company_name: str = None) -> bytes:
        """Generate Word document for individual section"""
        doc = Document()
        
        # Add header
        header_p = doc.add_heading(f'IDPETECH - BA Assistant: {title}', level=1)
        
        # Add metadata
        meta_p = doc.add_paragraph()
        meta_p.add_run(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n').italic = True
        if company_name:
            meta_p.add_run(f'Company: {company_name}').italic = True
        
        doc.add_paragraph()  # Space
        
        # Add content
        self._add_markdown_content(doc, content)
        
        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_word(self, results: PipelineResults, company_name: str) -> bytes:
        """Generate complete Word document report"""
        doc = Document()
        
        # Add title
        title = doc.add_heading('IDPETECH - BA Assistant: Complete AI Readiness Report', level=1)
        
        # Add metadata
        meta_p = doc.add_paragraph()
        meta_p.add_run(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n').italic = True
        meta_p.add_run(f'Company: {company_name}').italic = True
        
        doc.add_page_break()
        
        sections = [
            ("First Engagement Hook", results.hook),
            ("Diagnostic Insight", results.diagnosis),
            ("AI Readiness Audit", results.audit),
            ("Conversation Close", results.close)
        ]
        
        for title, content in sections:
            doc.add_heading(title, level=2)
            doc.add_paragraph()  # Space
            self._add_markdown_content(doc, content)
            doc.add_page_break()
        
        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

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
            company_name = results.signals.get('company_name', 'Unknown Company')
            pdf_generator = PDFGenerator()
            word_generator = WordGenerator()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # Helper function for individual downloads
            def create_download_buttons(section_title: str, content: str, file_prefix: str):
                col_md, col_pdf, col_word = st.columns(3)
                
                with col_md:
                    # Individual Markdown download
                    markdown_content = f"""# {section_title}
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Company: {company_name}

{content}
"""
                    st.download_button(
                        label="📄 MD",
                        data=markdown_content,
                        file_name=f"{file_prefix}_{timestamp}.md",
                        mime="text/markdown",
                        key=f"md_{file_prefix}"
                    )
                
                with col_pdf:
                    # Individual PDF download
                    try:
                        pdf_bytes = pdf_generator.generate_section_pdf(section_title, content, company_name)
                        st.download_button(
                            label="📄 PDF",
                            data=pdf_bytes,
                            file_name=f"{file_prefix}_{timestamp}.pdf",
                            mime="application/pdf",
                            key=f"pdf_{file_prefix}"
                        )
                    except Exception as e:
                        st.error(f"PDF generation failed: {str(e)}")
                
                with col_word:
                    # Individual Word download
                    try:
                        word_bytes = word_generator.generate_section_word(section_title, content, company_name)
                        st.download_button(
                            label="📄 DOCX",
                            data=word_bytes,
                            file_name=f"{file_prefix}_{timestamp}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"word_{file_prefix}"
                        )
                    except Exception as e:
                        st.error(f"Word generation failed: {str(e)}")
            
            # Hook Section
            st.subheader("🎯 First Engagement Hook")
            st.info(results.hook)
            create_download_buttons("First Engagement Hook", results.hook, "hook")
            
            st.divider()
            
            # Diagnostic Section
            st.subheader("🔍 Diagnostic Insight")
            st.markdown(results.diagnosis)
            create_download_buttons("Diagnostic Insight", results.diagnosis, "diagnosis")
            
            st.divider()
            
            # Audit Section
            st.subheader("📋 AI Readiness Audit")
            st.markdown(results.audit)
            create_download_buttons("AI Readiness Audit", results.audit, "audit")
            
            st.divider()
            
            # Close Section
            st.subheader("🤝 Conversation Close")
            st.write(results.close)
            create_download_buttons("Conversation Close", results.close, "close")
            
            st.divider()
            
            # Complete Report Download Options
            st.subheader("💾 Complete Report")
            st.caption("Download all sections as a single file")
            
            col_md, col_pdf, col_word = st.columns(3)
            
            with col_md:
                # Complete Markdown download
                complete_markdown = f"""# AI Readiness Audit Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Company: {company_name}

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
                    label="📄 Complete Report (MD)",
                    data=complete_markdown,
                    file_name=f"complete_ai_readiness_report_{timestamp}.md",
                    mime="text/markdown",
                    key="complete_md"
                )
            
            with col_pdf:
                # Complete PDF download
                try:
                    pdf_bytes = pdf_generator.generate_pdf(results, company_name)
                    st.download_button(
                        label="📄 Complete Report (PDF)",
                        data=pdf_bytes,
                        file_name=f"complete_ai_readiness_report_{timestamp}.pdf",
                        mime="application/pdf",
                        key="complete_pdf"
                    )
                except Exception as e:
                    st.error(f"Complete PDF generation failed: {str(e)}")
            
            with col_word:
                # Complete Word download
                try:
                    word_bytes = word_generator.generate_word(results, company_name)
                    st.download_button(
                        label="📄 Complete Report (DOCX)",
                        data=word_bytes,
                        file_name=f"complete_ai_readiness_report_{timestamp}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="complete_word"
                    )
                except Exception as e:
                    st.error(f"Complete Word generation failed: {str(e)}")
        else:
            st.info("👈 Enter company information and click 'Generate' to see the AI readiness analysis.")

if __name__ == "__main__":
    main()