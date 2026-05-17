"""
Unified page components that eliminate duplication across Manual/Agent/Comparison modes
KISS principle: Single source of truth for common functionality
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable, Tuple, List
from enum import Enum

from .config import render_pipeline_config, apply_pipeline_config
from .downloads import create_download_buttons, create_bulk_download_buttons


class PageMode(Enum):
    MANUAL = "manual"
    AGENT = "agent" 
    COMPARISON = "comparison"


def render_unified_header(mode: PageMode, title: str):
    """Unified header for all modes."""
    st.title(title)
    
    # Mode-specific context info
    if mode == PageMode.MANUAL:
        st.markdown("**Direct URL analysis with manual input**")
    elif mode == PageMode.AGENT:
        st.markdown("**Automated company research with agent workflow**") 
    elif mode == PageMode.COMPARISON:
        st.markdown("**Side-by-side pipeline comparison**")


def render_unified_config_panel(
    mode: PageMode,
    apply_callback: Optional[Callable] = None,
    show_comparison_options: bool = False
) -> Dict[str, Any]:
    """
    Unified configuration panel for all modes.
    Eliminates duplication between manual/agent/comparison config sections.
    
    Args:
        mode: The page mode for unique keys
        apply_callback: Optional callback when config is applied
        show_comparison_options: Whether to show comparison-specific options
        
    Returns:
        Dict with config state and changes
    """
    # Unique keys based on mode
    mode_prefix = mode.value
    pipeline_session_key = f"selected_{mode_prefix}_pipeline"
    prompts_session_key = f"selected_{mode_prefix}_prompts"
    apply_button_key = f"{mode_prefix}_apply"
    
    # Render unified config panel
    pipeline_type, prompt_version, config_applied = render_pipeline_config(
        mode_key=mode_prefix,
        pipeline_session_key=pipeline_session_key,
        prompts_session_key=prompts_session_key, 
        apply_button_key=apply_button_key
    )
    
    config_state = {
        'pipeline_type': pipeline_type,
        'prompt_version': prompt_version,
        'config_applied': config_applied,
        'pipeline_session_key': pipeline_session_key,
        'prompts_session_key': prompts_session_key
    }
    
    # Execute callback if config was applied
    if config_applied and apply_callback:
        apply_callback(config_state)
    
    # Comparison-specific options
    if show_comparison_options:
        st.info("💡 **Tip:** Configure different pipeline/prompt combinations to compare results side-by-side")
    
    return config_state


def render_unified_results_section(
    results: Dict[str, Any],
    company_name: str,
    mode: PageMode,
    pdf_generator,
    word_generator,
    show_downloads: bool = True,
    show_comparison: bool = False,
    comparison_results: Optional[Dict[str, Any]] = None,
    edit_signals_callback: Optional[Callable] = None
):
    """
    Unified results display for all modes.
    Eliminates duplication in results rendering across manual/agent/comparison.
    
    Args:
        results: Analysis results dictionary
        company_name: Company name for headers
        mode: Page mode for styling
        pdf_generator: PDF generator instance
        word_generator: Word generator instance  
        show_downloads: Whether to show download buttons
        show_comparison: Whether to show comparison view
        comparison_results: Optional comparison results for side-by-side
    """
    if not results:
        return
    
    # Results sections to display
    sections = [
        ('signals', '📊 Extracted Signals', '🔍'),
        ('diagnosis', '🔬 Strategic Diagnosis', '⚡'),
        ('hook', '🎯 Founder Hook', '💬'),
        ('audit', '📋 AI Readiness Audit', '📊'),
        ('close', '🎯 Strategic Close', '💭')
    ]
    
    if show_comparison and comparison_results:
        # Side-by-side comparison view
        _render_comparison_view(sections, results, comparison_results, company_name, 
                              pdf_generator, word_generator, show_downloads, edit_signals_callback)
    else:
        # Standard single results view
        _render_standard_results(sections, results, company_name, mode,
                               pdf_generator, word_generator, show_downloads, edit_signals_callback)


def _render_standard_results(
    sections: List[Tuple[str, str, str]], 
    results: Dict[str, Any],
    company_name: str,
    mode: PageMode,
    pdf_generator,
    word_generator, 
    show_downloads: bool,
    edit_signals_callback: Optional[Callable] = None
):
    """Render standard single-column results."""
    timestamp = None  # Will be generated in download component
    
    for section_key, section_title, emoji in sections:
        if section_key in results and results[section_key]:
            with st.expander(f"{emoji} {section_title}", expanded=True):
                content = results[section_key]
                
                # Display content based on type
                if section_key == 'signals':
                    _display_signals(
                        content, 
                        show_edit_button=bool(edit_signals_callback),
                        edit_callback=edit_signals_callback,
                        unique_key=f"{mode.value}_signals"
                    )
                else:
                    st.markdown(content)
                
                # Download buttons
                if show_downloads:
                    create_download_buttons(
                        section_title=section_title,
                        content=str(content),
                        file_prefix=f"{mode.value}_{section_key}",
                        company_name=company_name,
                        pdf_generator=pdf_generator,
                        word_generator=word_generator,
                        timestamp=timestamp
                    )
    
    # Bulk download section
    if show_downloads:
        st.divider()
        st.subheader("📄 Complete Analysis Export")
        create_bulk_download_buttons(
            results_data=results,
            company_name=company_name,
            pdf_generator=pdf_generator,
            word_generator=word_generator
        )


def _render_comparison_view(
    sections: List[Tuple[str, str, str]],
    results_a: Dict[str, Any],
    results_b: Dict[str, Any], 
    company_name: str,
    pdf_generator,
    word_generator,
    show_downloads: bool,
    edit_signals_callback: Optional[Callable] = None
):
    """Render side-by-side comparison view."""
    st.subheader("📊 Pipeline Comparison Results")
    
    # Headers
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔬 Structured Pipeline")
    with col2:
        st.markdown("#### ⚡ Legacy Pipeline")
    
    # Section-by-section comparison
    for section_key, section_title, emoji in sections:
        if section_key in results_a or section_key in results_b:
            st.divider()
            st.markdown(f"### {emoji} {section_title}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                content_a = results_a.get(section_key, "No data available")
                if section_key == 'signals':
                    _display_signals(
                        content_a,
                        show_edit_button=bool(edit_signals_callback),
                        edit_callback=edit_signals_callback,
                        unique_key=f"comparison_a_{section_key}"
                    )
                else:
                    st.markdown(content_a)
            
            with col2:
                content_b = results_b.get(section_key, "No data available")
                if section_key == 'signals':
                    _display_signals(
                        content_b,
                        show_edit_button=bool(edit_signals_callback),
                        edit_callback=edit_signals_callback, 
                        unique_key=f"comparison_b_{section_key}"
                    )
                else:
                    st.markdown(content_b)


def _display_signals(signals_data, show_edit_button=True, edit_callback=None, unique_key="signals"):
    """Display signals data in formatted way with optional edit functionality."""
    if isinstance(signals_data, dict):
        # Show signals
        for key, value in signals_data.items():
            if value and value != []:
                st.markdown(f"**{key.replace('_', ' ').title()}:**")
                if isinstance(value, list):
                    for item in value:
                        st.markdown(f"• {item}")
                else:
                    st.markdown(f"• {value}")
                st.markdown("")
        
        # Edit button and form
        if show_edit_button and edit_callback:
            if st.button("✏️ Edit Signals", key=f"edit_{unique_key}"):
                st.session_state[f"{unique_key}_edit_mode"] = True
                st.rerun()
            
            # Show edit form if in edit mode
            if st.session_state.get(f"{unique_key}_edit_mode", False):
                st.markdown("---")
                st.subheader("✏️ Edit Extracted Signals")
                
                with st.form(key=f"edit_signals_form_{unique_key}"):
                    # Convert signals to editable text format
                    signals_text = _signals_to_text(signals_data)
                    
                    edited_signals = st.text_area(
                        "Edit signals (JSON format):",
                        value=signals_text,
                        height=300,
                        help="Edit the extracted signals in JSON format. Changes will trigger re-processing of the analysis."
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        save_clicked = st.form_submit_button("💾 Save & Re-process", type="primary")
                    
                    with col2:
                        cancel_clicked = st.form_submit_button("❌ Cancel")
                
                # Handle form submissions outside the form
                if save_clicked:
                    try:
                        import json
                        # Parse edited signals
                        new_signals = json.loads(edited_signals)
                        
                        # Debug: Check if callback exists
                        if edit_callback is None:
                            st.error("❌ No edit callback provided - cannot re-process")
                        else:
                            st.info("🔄 Processing signal edits...")
                            
                            # Call the edit callback to trigger re-processing
                            edit_callback(new_signals)
                            
                            # Exit edit mode
                            st.session_state[f"{unique_key}_edit_mode"] = False
                            st.success("✅ Signals updated! Re-processing analysis...")
                            st.rerun()
                            
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON format: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Failed to update signals: {str(e)}")
                        # Keep in edit mode on error
                
                if cancel_clicked:
                    st.session_state[f"{unique_key}_edit_mode"] = False
                    st.rerun()
    else:
        st.markdown(str(signals_data))


def _signals_to_text(signals_data):
    """Convert signals data to editable text format."""
    import json
    try:
        return json.dumps(signals_data, indent=2)
    except Exception:
        return str(signals_data)


def render_unified_input_section(
    mode: PageMode,
    input_callback: Callable,
    placeholder_text: str = "",
    button_text: str = "🚀 Start Analysis",
    show_database_browser: bool = True
) -> Dict[str, Any]:
    """
    Unified input section for all modes.
    Handles URL input, company name input, database browsing etc.
    
    Args:
        mode: Page mode for unique keys
        input_callback: Callback function when input is submitted
        placeholder_text: Placeholder for input field
        button_text: Text for action button
        show_database_browser: Whether to show database browser
        
    Returns:
        Dict with input state and values
    """
    input_state = {}
    
    if mode == PageMode.MANUAL:
        # Manual URL input
        url_input = st.text_input(
            "🌐 Company Website URL",
            placeholder=placeholder_text or "https://example.com",
            key=f"{mode.value}_url_input"
        )
        input_state['url'] = url_input
        
        if st.button(button_text, key=f"{mode.value}_analyze", disabled=not url_input):
            input_callback(input_state)
            
    elif mode == PageMode.AGENT:
        # Agent company name input
        company_input = st.text_input(
            "🏢 Company Name",
            placeholder=placeholder_text or "Enter company name for automated research",
            key=f"{mode.value}_company_input"
        )
        input_state['company_name'] = company_input
        
        if st.button(button_text, key=f"{mode.value}_research", disabled=not company_input):
            input_callback(input_state)
    
    # Database browser (if requested)
    if show_database_browser:
        _render_database_browser(mode)
    
    return input_state


def _render_database_browser(mode: PageMode):
    """Render company database browser section."""
    from .database import render_database_browser
    
    if hasattr(st.session_state, 'db_manager') and st.session_state.db_manager:
        render_database_browser(
            db_manager=st.session_state.db_manager,
            key_prefix=f"{mode.value}_db"
        )
    else:
        st.info("Database not initialized")


# Export functions for easy importing
__all__ = [
    'PageMode',
    'render_unified_header', 
    'render_unified_config_panel',
    'render_unified_results_section',
    'render_unified_input_section'
]