"""
Entity extraction module using regex-based pattern matching.
Extracts emails, dates, and currency amounts from text.
All patterns are designed to work on lowercase normalized text.
"""

import re
from typing import List, Dict, Any


# Email pattern - matches standard email format in lowercase text
EMAIL_PATTERN = re.compile(
    r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
)

# Date patterns - various formats, designed for lowercase text
DATE_PATTERNS = [
    # "march 15, 2024" or "january 1, 2023"
    re.compile(r'(?:january|february|march|april|may|june|july|august|'
               r'september|october|november|december)\s+\d{1,2},?\s+\d{4}'),
    # "15 march 2024"
    re.compile(r'\d{1,2}\s+(?:january|february|march|april|may|june|july|august|'
               r'september|october|november|december)\s+\d{4}'),
    # "2024-03-15" ISO format
    re.compile(r'\d{4}-\d{2}-\d{2}'),
    # "03/15/2024" or "15/03/2024"
    re.compile(r'\d{1,2}/\d{1,2}/\d{4}'),
]

# Currency pattern - matches $X,XXX.XX format
CURRENCY_PATTERN = re.compile(
    r'(?:\$|€|£)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
)


def extract(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text using regex patterns.
    
    Extracts:
    - Email addresses
    - Dates in various formats
    - Currency/monetary amounts
    
    Note: Patterns are designed for lowercase normalized text input.
    
    Args:
        text: Input text to extract entities from.
        
    Returns:
        List of entity dicts with 'type', 'value', and 'position' keys.
    """
    entities = []

    # Extract emails
    for match in EMAIL_PATTERN.finditer(text):
        entities.append({
            'type': 'email',
            'value': match.group(),
            'position': match.start()
        })

    # Extract dates
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            entities.append({
                'type': 'date',
                'value': match.group(),
                'position': match.start()
            })

    # Extract currency amounts
    for match in CURRENCY_PATTERN.finditer(text):
        entities.append({
            'type': 'currency',
            'value': match.group(),
            'position': match.start()
        })

    # Sort by position for consistent output
    entities.sort(key=lambda e: e['position'])

    return entities
