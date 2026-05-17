"""
Download button components for BA Assistant
Extracted from app.py to reduce duplication and improve maintainability
"""

import streamlit as st
from datetime import datetime
from typing import Optional
import re
from core.export import PDFGenerator, WordGenerator


def create_download_buttons(
    section_title: str, 
    content: str, 
    file_prefix: str,
    company_name: str,
    pdf_generator: PDFGenerator,
    word_generator: WordGenerator,
    timestamp: Optional[str] = None
):
    """
    Create a row of download buttons (MD, PDF, DOCX) for a content section.
    
    Args:
        section_title: Display title for the section
        content: The content to be downloaded
        file_prefix: Prefix for generated filenames
        company_name: Company name for document headers
        pdf_generator: Initialized PDF generator instance
        word_generator: Initialized Word generator instance
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
        # Individual PDF download (clean content for PDF compatibility)
        try:
            # Remove emojis and unicode characters that break PDF generation
            clean_title = _clean_content_for_pdf(section_title)
            clean_content = _clean_content_for_pdf(content)
            
            pdf_bytes = pdf_generator.generate_section_pdf(clean_title, clean_content, company_name)
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


def create_bulk_download_buttons(
    results_data: dict,
    company_name: str,
    pdf_generator: PDFGenerator,
    word_generator: WordGenerator
):
    """
    Create bulk download buttons for complete analysis results.
    
    Args:
        results_data: Dict containing all analysis results
        company_name: Company name for document headers  
        pdf_generator: Initialized PDF generator instance
        word_generator: Initialized Word generator instance
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Complete Markdown export
        full_content = _build_complete_markdown(results_data, company_name)
        st.download_button(
            label="📄 Complete MD",
            data=full_content,
            file_name=f"BA_Analysis_{safe_company_name}_{timestamp}.md",
            mime="text/markdown",
            key="bulk_md"
        )
    
    with col2:
        # Complete PDF export
        try:
            # Convert dict to PipelineResults-like object if needed
            if isinstance(results_data, dict):
                # Create a simple object with the required attributes
                class TempResults:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                
                temp_results = TempResults(results_data)
                pdf_bytes = pdf_generator.generate_pdf(temp_results, company_name)
            else:
                pdf_bytes = pdf_generator.generate_pdf(results_data, company_name)
            
            st.download_button(
                label="📄 Complete PDF",
                data=pdf_bytes,
                file_name=f"BA_Analysis_{safe_company_name}_{timestamp}.pdf",
                mime="application/pdf",
                key="bulk_pdf"
            )
        except Exception as e:
            st.error(f"Full PDF generation failed: {str(e)}")
    
    with col3:
        # Complete Word export
        try:
            # Convert dict to PipelineResults-like object if needed
            if isinstance(results_data, dict):
                # Create a simple object with the required attributes
                class TempResults:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                
                temp_results = TempResults(results_data)
                word_bytes = word_generator.generate_word(temp_results, company_name)
            else:
                word_bytes = word_generator.generate_word(results_data, company_name)
            
            st.download_button(
                label="📄 Complete DOCX", 
                data=word_bytes,
                file_name=f"BA_Analysis_{safe_company_name}_{timestamp}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="bulk_word"
            )
        except Exception as e:
            st.error(f"Full Word generation failed: {str(e)}")


def _build_complete_markdown(results_data: dict, company_name: str) -> str:
    """Build complete markdown content from all results sections."""
    sections = []
    
    # Header
    sections.append(f"""# Business Analysis Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Company: {company_name}

---
""")
    
    # Add each section if present
    section_map = {
        'signals': '## Extracted Signals',
        'diagnosis': '## Strategic Diagnosis', 
        'hook': '## Founder Hook',
        'audit': '## AI Readiness Audit',
        'close': '## Strategic Close'
    }
    
    for key, title in section_map.items():
        if key in results_data and results_data[key]:
            sections.append(f"{title}\n\n{results_data[key]}\n\n---\n")
    
    return "\n".join(sections)


def _clean_content_for_pdf(content: str) -> str:
    """
    Clean content for PDF generation by removing problematic characters.
    
    Args:
        content: Original content with potential emojis/unicode
        
    Returns:
        Cleaned content safe for PDF generation
    """
    if not isinstance(content, str):
        content = str(content)
    
    # Remove common emojis that break PDF generation
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", 
        flags=re.UNICODE
    )
    
    # Remove emojis
    content = emoji_pattern.sub('', content)
    
    # Replace common problematic characters
    replacements = {
        '📊': '[CHART]',
        '📋': '[REPORT]', 
        '🎯': '[TARGET]',
        '🔬': '[ANALYSIS]',
        '⚡': '[QUICK]',
        '💬': '[MESSAGE]',
        '💭': '[THOUGHT]',
        '✅': '[CHECK]',
        '❌': '[X]',
        '🔄': '[REFRESH]',
        '🚀': '[ROCKET]',
        '🔍': '[SEARCH]',
        '⚙️': '[SETTINGS]',
        '📄': '[DOCUMENT]',
        '🌐': '[WEB]',
        '🏢': '[BUILDING]',
        '🤖': '[ROBOT]',
        # Add more as needed
    }
    
    for emoji, replacement in replacements.items():
        content = content.replace(emoji, replacement)
    
    # Remove any remaining non-ASCII characters that might cause issues
    # Keep basic punctuation and formatting
    content = re.sub(r'[^\x00-\x7F]+', '', content)
    
    return content