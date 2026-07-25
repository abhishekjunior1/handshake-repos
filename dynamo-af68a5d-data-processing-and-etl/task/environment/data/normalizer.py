"""
Text normalization module.
Applies Unicode normalization, whitespace collapse, and case folding.
"""

import unicodedata
import re
from typing import Dict, Any


def normalize(text: str) -> str:
    """
    Normalize text through multiple stages.
    
    Pipeline:
    1. Unicode NFKC normalization - converts compatibility characters
       to their canonical equivalents (e.g., ﬁ -> fi, ² -> 2)
    2. Whitespace collapse - replaces runs of whitespace with single space
    3. Case folding - converts all characters to lowercase
    4. Strip leading/trailing whitespace
    
    Args:
        text: Raw input text string.
        
    Returns:
        Normalized text string.
    """
    # Stage 1: Unicode NFKC normalization
    # This decomposes characters then recomposes with compatibility mappings
    # Handles things like: ﬁ->fi, ½->1/2, ²->2, ™->TM
    normalized = unicodedata.normalize('NFKC', text)

    # Stage 2: Whitespace collapse
    # Replace any sequence of whitespace (spaces, tabs, newlines) with single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # Stage 3: Case folding to lowercase
    # Using str.lower() for consistent case-insensitive processing
    normalized = normalized.lower()

    # Stage 4: Strip leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def normalize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize the text field of a document dictionary.
    
    Args:
        document: Document dict with 'text' field.
        
    Returns:
        New document dict with 'normalized_text' added
        and original 'text' preserved as 'raw_text'.
    """
    result = document.copy()
    result['raw_text'] = document['text']
    result['normalized_text'] = normalize(document['text'])
    return result
