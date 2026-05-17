"""
Configuration panel components for BA Assistant
Handles pipeline and prompt selection with duplicate logic extraction
"""

import streamlit as st
from typing import Dict, Any, Tuple


def render_pipeline_config(
    mode_key: str,
    pipeline_session_key: str, 
    prompts_session_key: str,
    apply_button_key: str
) -> Tuple[str, str, bool]:
    """
    Render pipeline configuration panel with pipeline and prompt selection.
    
    Args:
        mode_key: Unique identifier for this config panel
        pipeline_session_key: Session state key for pipeline selection
        prompts_session_key: Session state key for prompts selection  
        apply_button_key: Unique key for apply button
        
    Returns:
        Tuple of (pipeline_type, prompt_version, config_applied)
    """
    st.subheader("⚙️ Pipeline Configuration")
    
    with st.container():
        col_pipeline, col_prompts = st.columns(2)
        
        with col_pipeline:
            pipeline_type = st.selectbox(
                "Pipeline Architecture",
                ["Structured Pipeline", "Legacy Pipeline"],
                key=f"{mode_key}_pipeline_select",
                help="Structured = Extract Once, Analyze Many | Legacy = Original pipeline"
            )
            st.session_state[pipeline_session_key] = pipeline_type
        
        with col_prompts:
            prompt_version = st.selectbox(
                "Prompt Version", 
                ["Legacy Prompts", "Structured Prompts"],
                key=f"{mode_key}_prompts_select",
                help="Legacy = Raw content prompts | Structured = Evidence-based prompts"
            )
            st.session_state[prompts_session_key] = prompt_version
        
        # Apply configuration button
        config_applied = False
        col_update, col_status = st.columns([1, 2])
        
        with col_update:
            config_applied = st.button("🔄 Apply Configuration", key=apply_button_key)
        
        with col_status:
            if config_applied:
                st.success("✅ Configuration applied!")
            else:
                # Show current config status
                pipeline_display = "Structured" if pipeline_type == "Structured Pipeline" else "Legacy"
                prompts_display = "Structured" if prompt_version == "Structured Prompts" else "Legacy"
                st.info(f"Current: {pipeline_display} pipeline + {prompts_display} prompts")
    
    return pipeline_type, prompt_version, config_applied


def apply_pipeline_config(
    pipeline_type: str,
    prompt_version: str,
    load_structured_prompts_func,
    session_prompts: Dict[str, str],
    set_pipeline_info: bool = True
) -> Tuple[Any, Dict[str, str], str]:
    """
    Apply pipeline configuration and return appropriate assistant class and prompts.
    
    Args:
        pipeline_type: "Structured Pipeline" or "Legacy Pipeline"
        prompt_version: "Structured Prompts" or "Legacy Prompts"  
        load_structured_prompts_func: Function to load structured prompts
        session_prompts: Current session prompts
        set_pipeline_info: Whether to set pipeline info in session state
        
    Returns:
        Tuple of (AssistantClass, prompts_dict, pipeline_info_string)
    """
    # Import here to avoid circular imports
    from core.structured_pipeline import StructuredBAAssistant
    from core.pipeline import BAAssistant as LegacyBAAssistant
    
    # Load appropriate prompts
    if prompt_version == "Structured Prompts":
        prompts = load_structured_prompts_func()
    else:
        prompts = session_prompts
    
    # Select appropriate assistant class
    if pipeline_type == "Structured Pipeline":
        AssistantClass = StructuredBAAssistant
        pipeline_info = "🔬 Using Structured Pipeline (Extract Once, Analyze Many)"
    else:
        AssistantClass = LegacyBAAssistant  
        pipeline_info = "⚡ Using Legacy Pipeline (Original)"
    
    # Optionally set session state (avoid side effects when testing)
    if set_pipeline_info:
        st.session_state.pipeline_info = pipeline_info
    
    return AssistantClass, prompts, pipeline_info


def show_pipeline_status():
    """Display current pipeline status if available."""
    if hasattr(st.session_state, 'pipeline_info'):
        st.info(st.session_state.pipeline_info)