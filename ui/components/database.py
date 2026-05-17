"""
Database browser component for BA Assistant
Extracted from app.py for reusability across modes
"""

import streamlit as st
import hashlib
from typing import Optional, Callable


def render_database_browser(
    db_manager,
    load_callback: Optional[Callable] = None,
    key_prefix: str = "db"
):
    """
    Render company database browser with load functionality.
    
    Args:
        db_manager: Database manager instance
        load_callback: Optional callback when company is loaded
        key_prefix: Unique key prefix for this browser instance
    """
    with st.expander("📚 Company Database", expanded=False):
        try:
            companies = db_manager.list_companies()
            
            if not companies:
                st.info("No companies in database yet. Analyze companies to build your database.")
                return
            
            st.write(f"**{len(companies)} companies analyzed:**")
            
            # Show latest 10 companies
            for i, (url, name, updated) in enumerate(companies[:10]):
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                
                col_name, col_actions, col_date = st.columns([2.5, 2.5, 1])
                
                with col_name:
                    st.write(f"**{name or 'Unknown Company'}**")
                    st.caption(f"🌐 {url[:50]}{'...' if len(url) > 50 else ''}")
                
                with col_actions:
                    # Create loading buttons
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 0.8])
                    
                    with btn_col1:
                        if st.button(
                            "📄", 
                            key=f"{key_prefix}_context_{url_hash}_{i}",
                            help="Load context only (for reprocessing)"
                        ):
                            _handle_context_load(url, name, db_manager, load_callback)
                    
                    with btn_col2:
                        if st.button(
                            "📊", 
                            key=f"{key_prefix}_results_{url_hash}_{i}",
                            help="Load results only (view analysis)"
                        ):
                            _handle_results_load(url, name, db_manager, load_callback)
                    
                    with btn_col3:
                        if st.button(
                            "🔄", 
                            key=f"{key_prefix}_full_{url_hash}_{i}",
                            help="Load full analysis (context + results)"
                        ):
                            _handle_full_load(url, name, db_manager, load_callback)
                    
                    with btn_col4:
                        if st.button(
                            "🗑️", 
                            key=f"{key_prefix}_delete_{url_hash}_{i}",
                            help="Delete from database"
                        ):
                            _handle_delete(url, name, db_manager, load_callback)
                
                with col_date:
                    st.caption(f"📅 {updated}")
                
                # Add separator
                if i < min(len(companies), 10) - 1:
                    st.markdown("---")
            
            # Show pagination info if needed
            if len(companies) > 10:
                st.caption(f"Showing latest 10 of {len(companies)} companies")
                
        except Exception as e:
            st.error(f"Database browser error: {e}")


def _handle_context_load(url: str, name: str, db_manager, load_callback: Optional[Callable]):
    """Handle loading context only for reprocessing."""
    try:
        context_data = db_manager.get_context_only(url)
        if context_data:
            st.session_state.inputs, _ = context_data
            st.session_state.results = None  # Clear previous results
            st.success(f"✅ Loaded context for {name} - ready for reprocessing")
            
            if load_callback:
                load_callback('context', url, name, context_data)
            
            st.rerun()
        else:
            st.error(f"❌ No context found for {name}")
    except Exception as e:
        st.error(f"❌ Failed to load context: {e}")


def _handle_results_load(url: str, name: str, db_manager, load_callback: Optional[Callable]):
    """Handle loading results only for viewing."""
    try:
        cached_data = db_manager.get_analysis(url)
        if cached_data:
            _, st.session_state.results, _ = cached_data
            st.session_state.inputs = None  # Clear inputs
            st.success(f"✅ Loaded analysis for {name}")
            
            if load_callback:
                load_callback('results', url, name, cached_data)
            
            st.rerun()
        else:
            st.error(f"❌ No analysis found for {name}")
    except Exception as e:
        st.error(f"❌ Failed to load results: {e}")


def _handle_full_load(url: str, name: str, db_manager, load_callback: Optional[Callable]):
    """Handle loading full analysis (context + results)."""
    try:
        cached_data = db_manager.get_analysis(url)
        if cached_data:
            st.session_state.inputs, st.session_state.results, _ = cached_data
            st.success(f"✅ Loaded full analysis for {name}")
            
            if load_callback:
                load_callback('full', url, name, cached_data)
            
            st.rerun()
        else:
            st.error(f"❌ No analysis found for {name}")
    except Exception as e:
        st.error(f"❌ Failed to load full analysis: {e}")


def _handle_delete(url: str, name: str, db_manager, load_callback: Optional[Callable]):
    """Handle deleting company from database."""
    try:
        # Show confirmation
        if st.button(
            f"⚠️ Confirm delete {name}?", 
            key=f"confirm_delete_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        ):
            success = db_manager.delete_company(url)
            if success:
                st.success(f"✅ Deleted {name} from database")
                
                if load_callback:
                    load_callback('delete', url, name, None)
                
                st.rerun()
            else:
                st.error(f"❌ Failed to delete {name}")
    except Exception as e:
        st.error(f"❌ Delete operation failed: {e}")


def render_simple_database_list(db_manager, max_items: int = 5) -> Optional[str]:
    """
    Render a simplified database list for selection.
    
    Args:
        db_manager: Database manager instance
        max_items: Maximum items to show
        
    Returns:
        Selected company URL or None
    """
    try:
        companies = db_manager.list_companies()
        
        if not companies:
            st.info("No companies in database")
            return None
        
        # Create selection options
        options = ["Select a company..."]
        urls = [None]
        
        for url, name, updated in companies[:max_items]:
            display_name = f"{name or 'Unknown'} ({updated})"
            options.append(display_name)
            urls.append(url)
        
        selected_idx = st.selectbox(
            "Previous Analyses",
            range(len(options)),
            format_func=lambda x: options[x],
            key="simple_db_select"
        )
        
        return urls[selected_idx] if selected_idx > 0 else None
        
    except Exception as e:
        st.error(f"Database list error: {e}")
        return None