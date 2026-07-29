"""
Text tokenization module.
Splits text into sentences and words, with stopword filtering.
"""

import re
from typing import List, Dict, Any


# Common English stopwords
STOPWORDS = frozenset([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'and', 'but', 'or',
    'nor', 'not', 'so', 'yet', 'both', 'either', 'neither', 'each',
    'every', 'all', 'any', 'few', 'more', 'most', 'other', 'some',
    'such', 'no', 'only', 'own', 'same', 'than', 'too', 'very',
    'just', 'because', 'if', 'when', 'where', 'how', 'what', 'which',
    'who', 'whom', 'this', 'that', 'these', 'those', 'it', 'its',
    'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'our', 'their', 'about', 'up', 'out',
    'then', 'there', 'here', 'also', 'over', 'under', 'again',
])

# Known abbreviations that should not trigger sentence breaks
ABBREVIATIONS = frozenset([
    'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'st',
    'inc', 'ltd', 'corp', 'co', 'dept', 'univ',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'vs', 'etc', 'approx', 'est', 'vol', 'ref', 'fig',
    'u', 'e', 'i',  # for U.S., e.g., i.e.
])


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using period-based boundary detection.

    Handles sentence boundaries by splitting on '. ' (period + space)
    patterns, then rejoining fragments that were split at abbreviations.
    This post-hoc correction approach handles most common abbreviation
    patterns found in English technical text.

    Args:
        text: Normalized text string.

    Returns:
        List of sentence strings.
    """
    if not text.strip():
        return []

    # Split on period followed by space and uppercase or end
    # Use a simple split on '. ' first, then rejoin abbreviations
    raw_fragments = re.split(r'\.\s+', text)

    # Post-hoc abbreviation correction: rejoin fragments split at abbreviations
    sentences = []
    current = raw_fragments[0] if raw_fragments else ''

    for i in range(1, len(raw_fragments)):
        # Check if previous fragment ends with an abbreviation
        last_word = current.rsplit(None, 1)[-1] if current else ''
        last_word_clean = re.sub(r'[^a-z]', '', last_word.lower())

        if last_word_clean in ABBREVIATIONS:
            # Rejoin: the split was at an abbreviation
            current = current + '. ' + raw_fragments[i]
        else:
            sentences.append(current.strip())
            current = raw_fragments[i]

    if current.strip():
        sentences.append(current.strip())

    # Remove empty sentences
    sentences = [s for s in sentences if s.strip()]
    return sentences


def tokenize_words(text: str) -> List[str]:
    """
    Tokenize text into individual word tokens.

    Keeps hyphenated compound words as single tokens (e.g., "data-driven"
    remains one token) for proper compound term analysis.

    Args:
        text: Text string to tokenize.

    Returns:
        List of word tokens.
    """
    # Match word characters including hyphens within words
    tokens = re.findall(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', text.lower())
    # Filter out single-character tokens except common ones
    tokens = [t for t in tokens if len(t) > 1 or t in ('a', 'i')]
    return tokens


def remove_stopwords(tokens: List[str]) -> List[str]:
    """
    Remove common English stopwords from token list.

    Args:
        tokens: List of word tokens.

    Returns:
        Filtered token list without stopwords.
    """
    return [t for t in tokens if t not in STOPWORDS]


def tokenize(text: str) -> Dict[str, Any]:
    """
    Full tokenization pipeline: sentences, words, and stopword removal.

    Args:
        text: Normalized text to tokenize.

    Returns:
        Dictionary with 'sentences', 'tokens', and 'tokens_without_stopwords'.
    """
    sentences = split_sentences(text)
    all_tokens = tokenize_words(text)
    filtered_tokens = remove_stopwords(all_tokens)

    return {
        'sentences': sentences,
        'tokens': all_tokens,
        'tokens_without_stopwords': filtered_tokens,
    }
