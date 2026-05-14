"""
Utility functions for BA Assistant
"""

import logging
import tiktoken
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Constants
MAX_CONTEXT_TOKENS = 18_000  # TPM guardrail for OpenAI Tier 1


def _is_url(text: str) -> bool:
    """Return True if text looks like an http/https URL."""
    try:
        p = urlparse(text.strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def sieve_context(text: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """
    Token sieve to guarantee we stay under OpenAI TPM limits.
    Truncates input text to fit within token budget while preserving structure.
    CRITICAL: Prevents TPM overruns on Tier 1 (30k TPM limit)
    """
    try:
        # Use tiktoken for accurate token counting (gpt-4 encoding)
        encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate to max_tokens and decode back
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        
        # Add truncation notice
        truncated_text += "\n\n[Context truncated to stay within TPM limits]"
        logger.warning(f"Context sieved: {len(tokens)} -> {max_tokens} tokens")
        
        return truncated_text
        
    except Exception as e:
        logger.warning(f"Token sieving failed, using character fallback: {e}")
        # Fallback to character-based truncation (rough estimate: 4 chars = 1 token)
        char_limit = max_tokens * 4
        if len(text) > char_limit:
            return text[:char_limit] + "\n\n[Context truncated]"
        return text