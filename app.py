import streamlit as st
import openai
import json
import hashlib
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from urllib.parse import urlparse
import requests
import html2text
from fpdf import FPDF
import markdown
from bs4 import BeautifulSoup
import re
from docx import Document
from docx.shared import Inches
from docx.enum.style import WD_STYLE_TYPE
import io
import tiktoken

# Import extracted core components
from core.models import CompanyInputs, PipelineResults, AGENT_STAGES, ResearchSummary, ICPResult
from core.utils import _is_url, sieve_context
from core.database import DatabaseManager
from core.scraping import FirecrawlManager, scrape_website, scrape_page
from core.pipeline import BAAssistant
from core.export import PDFGenerator, WordGenerator
from core.agent import FirecrawlSearchClient, ResearchAgent, ICPScorer, research_to_inputs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def render_manual_panel():
    """Render the manual mode panel (existing functionality)"""
    # Company database browser
    with st.expander("📚 Company Database", expanded=False):
        companies = st.session_state.db_manager.list_companies()
        if companies:
            st.write(f"**{len(companies)} companies analyzed:**")
            for url, name, updated in companies[:10]:  # Show latest 10
                col_name, col_actions, col_date = st.columns([2.5, 2.5, 1])
                with col_name:
                    st.write(f"**{name}**")
                with col_actions:
                    # Create three loading buttons in a single row
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 0.8])
                    
                    with btn_col1:
                        if st.button("📄", key=f"context_{hashlib.md5(url.encode()).hexdigest()[:8]}", help="Load context only (for reprocessing)"):
                            # Load only context for reprocessing
                            context_data = st.session_state.db_manager.get_context_only(url)
                            if context_data:
                                st.session_state.inputs, _ = context_data
                                st.session_state.results = None  # Clear previous results
                                st.success(f"Loaded context for {name} - ready for reprocessing")
                                st.rerun()
                    
                    with btn_col2:
                        if st.button("📊", key=f"results_{hashlib.md5(url.encode()).hexdigest()[:8]}", help="Load results only (view analysis)"):
                            # Load only results for viewing
                            cached_data = st.session_state.db_manager.get_analysis(url)
                            if cached_data:
                                _, st.session_state.results, _ = cached_data
                                st.session_state.inputs = None  # Clear inputs
                                st.success(f"Loaded results for {name}")
                                st.rerun()
                    
                    with btn_col3:
                        if st.button("📂", key=f"full_{hashlib.md5(url.encode()).hexdigest()[:8]}", help="Load complete analysis (context + results)"):
                            # Load complete analysis
                            cached_data = st.session_state.db_manager.get_analysis(url)
                            if cached_data:
                                st.session_state.inputs, st.session_state.results, _ = cached_data
                                st.success(f"Loaded complete analysis for {name}")
                                st.rerun()
                    
                    with btn_col4:
                        if st.button("🗑️", key=f"delete_{hashlib.md5(url.encode()).hexdigest()[:8]}", help="Delete company record"):
                            if st.session_state.db_manager.delete_company(url):
                                st.success(f"Deleted {name}")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete {name}")
                    
                    with col_date:
                        st.caption(updated.strftime("%m/%d"))
            
            # Add comprehensive legend for buttons
            st.caption("**Load Options:** 📄 Context only (reprocess) • 📊 Results only (view) • 📂 Complete analysis • 🗑️ Delete record")
        else:
            st.info("No companies analyzed yet.")
    
    st.divider()
    
    # Primary inputs
    target_url = st.text_input(
        "🌐 Target Company URL",
        placeholder="https://company.com",
        help="Primary company website for automated analysis"
    )
    
    job_posting = st.text_area(
        "💼 Job Posting (Optional)",
        placeholder="Paste job posting text for additional context...",
        height=120,
        help="Optional job posting to enhance technical signal detection"
    )
    
    # Context editing section (shows when context is loaded for reprocessing)
    if 'inputs' in st.session_state and st.session_state.inputs and not st.session_state.get('results'):
        st.divider()
        with st.expander("✏️ Edit Loaded Context", expanded=True):
            st.info("📝 Context loaded from database. You can edit and add additional context before reprocessing.")
            
            # Show/edit scraped content
            if st.session_state.inputs.scraped_content:
                st.subheader("Company Self-Perception")
                edited_scraped = st.text_area(
                    "Company narrative (scraped content):",
                    value=st.session_state.inputs.scraped_content,
                    height=150,
                    key="edit_scraped"
                )
                st.session_state.inputs.scraped_content = edited_scraped
            
            # Show/edit external signals
            if st.session_state.inputs.external_signals:
                st.subheader("External Technical Signals")
                edited_signals = st.text_area(
                    "External signals:",
                    value=st.session_state.inputs.external_signals,
                    height=150,
                    key="edit_signals"
                )
                st.session_state.inputs.external_signals = edited_signals
            
            # Additional context input
            st.subheader("Additional Context")
            additional_context = st.text_area(
                "Add any additional context or insights:",
                placeholder="Add new technical insights, competitor analysis, or other relevant context...",
                height=100,
                key="additional_context"
            )
            
            # Append additional context to job posting if provided
            if additional_context and additional_context.strip():
                if st.session_state.inputs.job_posting:
                    st.session_state.inputs.job_posting = f"{st.session_state.inputs.job_posting}\n\nAdditional Context:\n{additional_context}"
                else:
                    st.session_state.inputs.job_posting = f"Additional Context:\n{additional_context}"
            
            # Override the primary inputs when editing
            if st.session_state.inputs.target_url:
                target_url = st.session_state.inputs.target_url
            if st.session_state.inputs.job_posting:
                job_posting = st.session_state.inputs.job_posting
    
    # Check for cached analysis
    cached_analysis = None
    if target_url:
        cached_analysis = st.session_state.db_manager.get_analysis(target_url)
    
    # Main action buttons
    run_analysis = False
    
    # Handle different loading modes
    if 'inputs' in st.session_state and st.session_state.inputs and not st.session_state.get('results'):
        # Context-only mode (ready for reprocessing)
        st.info("🔄 **Context Loaded for Reprocessing** - Ready to run analysis on existing context")
        if st.button("⚗️ Reprocess with Context", type="primary", help="Run analysis on loaded context (uses API credits)"):
            run_analysis = True
    elif 'results' in st.session_state and st.session_state.results and not st.session_state.get('inputs'):
        # Results-only mode (view only)
        st.info("📊 **Results Loaded for Viewing** - Analysis results displayed below")
        st.caption("💡 To reprocess this analysis, use the 📄 Context button to load context for editing")
    elif cached_analysis:
        col_run, col_refresh = st.columns(2)
        with col_run:
            if st.button("⚗️ Run Fresh Assessment", type="primary", help="Run new technical analysis (uses API credits)"):
                run_analysis = True
        with col_refresh:
            if st.button("📂 Load Cached", help="Load existing analysis from database"):
                st.session_state.inputs, st.session_state.results, last_updated = cached_analysis
                st.success(f"Loaded analysis from {last_updated.strftime('%Y-%m-%d %H:%M')}")
                st.rerun()
    else:
        if st.button("⚗️ Start Architecture Analysis", type="primary", help="Distill + Hunt + Cross-Reference"):
            run_analysis = True

    if run_analysis:
        # Check if we're reprocessing existing context or running fresh analysis
        if 'inputs' in st.session_state and st.session_state.inputs and not st.session_state.get('results'):
            # Context reprocessing mode
            if not target_url:
                st.error("Please provide a target company URL.")
            elif not _is_url(target_url):
                st.error("Please provide a valid URL (must start with http:// or https://)")
            else:
                # Status tracking for context reprocessing
                status_container = st.status("🔄 Reprocessing Context with Senior Architect Analysis...", expanded=True)
                
                try:
                    with status_container:
                        st.write("📝 Using loaded context from database...")
                        st.write("⚗️ Running pipeline on existing context...")
                        st.write("🎯 Generating fresh insights...")
                        
                        # Run pipeline on existing context
                        results = st.session_state.ba_assistant.run_full_pipeline(st.session_state.inputs)
                        st.session_state.results = results
                        
                        # Save updated analysis to database
                        st.session_state.db_manager.upsert_analysis(
                            st.session_state.inputs.target_url, 
                            st.session_state.inputs, 
                            results
                        )
                except Exception as e:
                    status_container.update(
                        label="❌ Context Reprocessing Failed", 
                        state="error", 
                        expanded=True
                    )
                    st.error(f"Context reprocessing failed: {str(e)}")
                    logger.error(f"Context reprocessing failed: {e}")
                    
        else:
            # Fresh analysis mode
            if not target_url:
                st.error("Please provide a target company URL.")
            elif not _is_url(target_url):
                st.error("Please provide a valid URL (must start with http:// or https://)")
            else:
                # Status tracking container with technical process feedback
                status_container = st.status("⚗️ Distilling Architectural Signals...", expanded=True)
                
                try:
                    with status_container:
                        st.write("🔍 Checking local cache for existing analysis...")
                        st.write("⚗️ Initializing credit-efficient scraping protocol...")
                        st.write("🎯 Preparing targeted external signal hunt...")
                        
                        # Run the agentic triangulation loop
                        inputs, results = st.session_state.ba_assistant.run_triangulation(
                            target_url,
                            job_posting,
                            st.session_state.firecrawl_manager,
                            st.session_state.db_manager
                        )
                        
                        st.session_state.inputs = inputs
                        st.session_state.results = results
                        
                    status_container.update(
                        label="✅ Architectural Reality Check Complete!", 
                        state="complete", 
                        expanded=False
                    )
                    st.success(f"🏗️ Technical assessment complete for {inputs.company_name} - contradictions identified!")
                    st.rerun()
                        
                except Exception as e:
                    status_container.update(
                        label="❌ Technical Analysis Failed", 
                        state="error", 
                        expanded=True
                    )
                    st.error(f"Architectural assessment failed: {str(e)}")
                    logger.error(f"Technical analysis pipeline failed: {e}")


def render_agent_panel():
    """Render the agent mode panel with state machine"""
    # Handle pending company from replan buttons
    if st.session_state.pending_company:
        st.session_state.agent_company = st.session_state.pending_company
        st.session_state.pending_company = None
        st.session_state.agent_stage = "RESEARCHING"
        st.rerun()
    
    stage = st.session_state.agent_stage
    
    # Stage: IDLE
    if stage == "IDLE":
        st.subheader("🤖 Agent Research Mode")
        
        company = st.text_input(
            "Company name",
            placeholder="e.g. Fleetline",
            key="agent_company_input"
        )
        
        if st.button("🚀 Research Company"):
            if company.strip():
                st.session_state.agent_company = company.strip()
                st.session_state.agent_stage = "RESEARCHING"
                st.rerun()
        
        # Company database browser for agent mode
        with st.expander("📚 Previously Researched Companies", expanded=False):
            companies = st.session_state.db_manager.list_companies()
            if companies:
                st.write(f"**{len(companies)} companies in database:**")
                for url, name, updated in companies[:10]:  # Show latest 10
                    col_name, col_actions, col_date = st.columns([3, 2, 1])
                    with col_name:
                        st.write(f"**{name}**")
                    with col_actions:
                        # Load button for agent mode - loads into results display
                        if st.button("📂 Load", key=f"agent_load_{hashlib.md5(url.encode()).hexdigest()[:8]}", help="Load analysis for viewing"):
                            cached_data = st.session_state.db_manager.get_analysis(url)
                            if cached_data:
                                st.session_state.inputs, st.session_state.results, _ = cached_data
                                st.success(f"Loaded analysis for {name}")
                                st.rerun()
                    with col_date:
                        st.write(updated.strftime("%m/%d"))
            else:
                st.write("No companies analyzed yet.")
    
    # Stage: RESEARCHING
    elif stage == "RESEARCHING":
        st.subheader(f"🔬 Researching {st.session_state.agent_company}")
        
        with st.spinner(f"Researching {st.session_state.agent_company}..."):
            # Initialize agents
            search_client = FirecrawlSearchClient(st.session_state.firecrawl_manager.firecrawl.api_key)
            agent = ResearchAgent(search_client, st.session_state.ba_assistant.client, st.session_state.prompts)
            scorer = ICPScorer(st.session_state.ba_assistant.client)
            ba = st.session_state.ba_assistant
            
            # Run research
            research = agent.run(st.session_state.agent_company)
            
            # Convert to CompanyInputs for signal extraction
            inputs = research_to_inputs(research)
            signals = ba.extract_signals(inputs)
            
            # Score ICP fit
            icp = scorer.score(st.session_state.agent_company, research, signals)
            
            # Store results and transition
            st.session_state.agent_research = research
            st.session_state.agent_icp = icp
            st.session_state.agent_signals = signals
            
            # Save research data to database immediately after ICP decision
            # This preserves the research work regardless of whether user proceeds
            from core.models import PipelineResults
            inputs = research_to_inputs(research)
            
            # Create empty PipelineResults with pending status
            pending_results = PipelineResults(
                signals={},
                diagnosis="[Analysis Pending - Research Complete]",
                hook="[Analysis Pending - Research Complete]", 
                audit="[Analysis Pending - Research Complete]",
                close="[Analysis Pending - Research Complete]"
            )
            
            st.session_state.db_manager.upsert_analysis(
                inputs.target_url,
                inputs, 
                pending_results
            )
            
            st.session_state.agent_stage = "ICP_DECISION"
            st.rerun()
    
    # Stage: ICP_DECISION
    elif stage == "ICP_DECISION":
        research = st.session_state.agent_research
        icp = st.session_state.agent_icp
        
        st.subheader(f"🎯 ICP Assessment: {research.company_name}")
        
        # Show research summary first
        with st.expander("🔍 What the agent found", expanded=True):
            st.write(f"• **Website:** {research.official_website}")
            st.write(f"• **Funding:** {research.funding_stage} — {research.funding_amount}")
            st.write(f"• **Headcount:** {research.headcount_estimate}")
            st.write(f"• **Decision maker:** {research.decision_maker_name}, {research.decision_maker_title}")
            st.write(f"• **Confidence:** {research.decision_maker_confidence}")
            
            if research.news_signals:
                st.write("• **News signals:**")
                for signal in research.news_signals[:3]:
                    st.write(f"  - {signal}")
            
            if research.research_sources:
                st.write("• **Research sources:**")
                for source in research.research_sources[:5]:
                    st.write(f"  - {source}")
            
            if research.research_log:
                st.write("• **Research log:**")
                for log_entry in research.research_log:
                    st.write(f"  - {log_entry}")
        
        # Show ICP verdict
        if icp.decision == "FIT":
            st.success(f"✅ {icp.score} FIT — {icp.confidence} confidence")
            st.markdown("**Why this company fits:**")
            for reason in icp.fit_reasons:
                st.markdown(f"• {reason}")
            
            st.info(f"Proceeding will use approximately {icp.estimated_credits} Firecrawl credits.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, run full analysis"):
                    st.session_state.agent_stage = "RUNNING_PIPELINE"
                    st.rerun()
            with col2:
                if st.button("⏸ Save for later"):
                    # Could save to prospected_companies table here
                    st.session_state.agent_stage = "IDLE"
                    st.session_state.agent_company = None
                    st.rerun()
        
        else:  # DISQUALIFIED
            st.error("❌ Not funnel-worthy")
            st.markdown("**Why this company doesn't fit:**")
            for d in icp.disqualifiers:
                st.markdown(f"• {d}")
            st.markdown(f"**Explanation:** {icp.explanation}")
            
            if icp.alternatives:
                st.divider()
                st.markdown("**Similar companies that might fit better:**")
                for i, alt in enumerate(icp.alternatives):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{alt['company_name']}** — {alt['reason']}")
                    with col2:
                        # THE FIX FOR THE CLICK BUG - set pending_company in state then rerun
                        if st.button("Try this →", key=f"alt_{i}_{alt['company_name']}"):
                            st.session_state.pending_company = alt['company_name']
                            st.session_state.agent_stage = "IDLE"
                            st.rerun()
            
            st.divider()
            st.markdown("**Still want to proceed?**")
            st.warning(f"⚠️ This company scored {icp.score}. Proceeding will use ~{icp.estimated_credits} Firecrawl credits on a low-fit prospect.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚠️ Proceed anyway"):
                    st.session_state.agent_stage = "RUNNING_PIPELINE"
                    st.rerun()
            with col2:
                if st.button("🔙 Start over"):
                    st.session_state.agent_stage = "IDLE"
                    st.session_state.agent_company = None
                    st.rerun()
    
    # Stage: RUNNING_PIPELINE
    elif stage == "RUNNING_PIPELINE":
        st.subheader("🔄 Running Full Analysis")
        
        with st.spinner("Running full analysis..."):
            ba = st.session_state.ba_assistant
            inputs = research_to_inputs(st.session_state.agent_research)
            results = ba.run_full_pipeline(inputs)
            st.session_state.agent_result = results
            st.session_state.inputs = inputs  # Set for results display
            st.session_state.results = results  # Set for results display
            
            # Save completed analysis to database (overwrites pending status)
            st.session_state.db_manager.upsert_analysis(
                inputs.target_url,
                inputs, 
                results
            )
            
            st.session_state.agent_stage = "COMPLETE"
            st.rerun()
    
    # Stage: COMPLETE
    elif stage == "COMPLETE":
        if st.button("🔙 New company"):
            st.session_state.agent_stage = "IDLE"
            st.session_state.agent_company = None
            st.session_state.agent_result = None
            st.session_state.agent_research = None
            st.session_state.agent_icp = None
            st.rerun()
        
        # Results are displayed in col2 via existing results display logic


def main():
    st.set_page_config(
        page_title="IDPETECH · Architectural Reality Check Engine",
        page_icon="⚗️",
        layout="wide"
    )
    
    st.title("⚗️ IDPETECH · Architectural Reality Check Engine")
    st.subheader("Senior Principal Architect · AI Claims vs Technical Reality Assessment")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'inputs' not in st.session_state:
        st.session_state.inputs = None
    if 'prompts' not in st.session_state:
        ba_temp = BAAssistant("temp")
        st.session_state.prompts = ba_temp._load_prompts()
    
    # Agent mode session state
    st.session_state.setdefault("agent_stage", "IDLE")
    st.session_state.setdefault("agent_company", None)
    st.session_state.setdefault("agent_research", None)  # ResearchSummary
    st.session_state.setdefault("agent_icp", None)       # ICPResult
    st.session_state.setdefault("agent_result", None)    # PipelineResults
    st.session_state.setdefault("pending_company", None) # replan selection
    
    # Initialize managers
    openai_api_key = st.secrets.get("OPENAI_API_KEY") or st.sidebar.text_input("OpenAI API Key", type="password")
    firecrawl_api_key = st.secrets.get("FIRECRAWL_API_KEY") or st.sidebar.text_input("Firecrawl API Key", type="password")
    
    if not openai_api_key:
        st.warning("Please provide OpenAI API key to continue.")
        return
    if not firecrawl_api_key:
        st.warning("Please provide Firecrawl API key to continue.")
        return
    
    # Initialize managers
    if 'ba_assistant' not in st.session_state:
        st.session_state.ba_assistant = BAAssistant(openai_api_key, st.session_state.prompts)
    if 'firecrawl_manager' not in st.session_state:
        st.session_state.firecrawl_manager = FirecrawlManager(firecrawl_api_key)
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    
    # Layout: Left panel for inputs, Right panel for outputs
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("⚗️ Architectural Assessment")
        
        # Mode selector
        mode = st.radio(
            "Mode",
            ["Manual", "🤖 Agent"],
            horizontal=True,
            key="mode_selector"
        )
        
        if mode == "Manual":
            render_manual_panel()
            
            # Prompt Management Section (only in manual mode)
            st.divider()
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
        
        elif mode == "🤖 Agent":
            render_agent_panel()

    with col2:
        st.header("⚗️ Architectural Reality Check Results")
        
        if st.session_state.results and st.session_state.inputs:
            results = st.session_state.results
            inputs = st.session_state.inputs
            company_name = inputs.company_name or results.signals.get('company_name', 'Unknown Company')
            pdf_generator = PDFGenerator()
            word_generator = WordGenerator()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # Show triangulation summary (expanded by default to show the evidence)
            with st.expander("🔍 Triangulation Evidence", expanded=True):
                if inputs.scraped_content:
                    st.subheader("📄 Company Self-Perception")
                    st.caption("Extraction Method: Firecrawl API (cloud rendered)")
                    st.markdown(inputs.scraped_content[:500] + "..." if len(inputs.scraped_content) > 500 else inputs.scraped_content)
                
                if inputs.job_posting:
                    st.subheader("💼 Job Posting Signals")
                    st.info(f"Role: {inputs.job_posting}")
                    st.caption("Job posting requirements are integrated into the technical analysis")
                
                if inputs.external_signals and "No external signals found" not in inputs.external_signals:
                    st.subheader("🔍 External Technical Signals")
                    # Count the number of signal sources
                    signal_count = len(inputs.external_signals.split("---")) if "---" in inputs.external_signals else 1
                    st.info(f"Found {signal_count} external signal sources")
                    # Show all external signals (not truncated)
                    st.markdown(inputs.external_signals)
                else:
                    st.warning("⚠️ No external signals found - analysis based on company narrative only")
            
            st.divider()
            
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
            st.info("👈 Enter a target company URL and click 'Start Architecture Analysis' to begin technical assessment.")
            
            # Show what the technical assessment will do
            st.markdown("""
            **⚗️ The Senior Architect Assessment Engine will:**
            
            1. **⚗️ Distill** company self-perception from website (credit-efficient scraping)
            2. **🔍 Hunt** for external technical contradiction signals (2-query limit)
            3. **⚖️ Verify** tech-stack contradictions vs. marketing claims
            4. **🏗️ Generate** brutal technical assessment focusing on architectural failure modes
            
            *Results cached for instant retrieval. Zero exposure outreach ready.*
            """)

if __name__ == "__main__":
    main()