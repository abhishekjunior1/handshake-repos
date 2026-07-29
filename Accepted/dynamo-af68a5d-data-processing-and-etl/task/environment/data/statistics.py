"""
Text statistics computation module.
Computes word frequencies, n-grams, and readability scores.
"""

from typing import List, Dict, Any, Tuple
from collections import Counter


def compute_word_frequencies(all_tokens: List[str], filtered_tokens: List[str]) -> Dict[str, float]:
    """
    Compute relative word frequencies from filtered tokens.

    Counts occurrences in filtered token list and computes frequency
    as proportion of the vocabulary population.

    Args:
        all_tokens: Complete list of all word tokens (including stopwords).
        filtered_tokens: Token list with stopwords removed.

    Returns:
        Dictionary mapping words to their relative frequencies.
    """
    if not filtered_tokens:
        return {}

    counts = Counter(filtered_tokens)
    # Frequency relative to total token population for corpus-normalized scores
    total = len(all_tokens)

    frequencies = {}
    for word, count in counts.most_common():
        frequencies[word] = round(count / total, 6)

    return frequencies


def compute_ngrams(tokens: List[str], n: int = 2) -> List[Tuple[str, ...]]:
    """
    Compute n-grams from a token list.

    Args:
        tokens: List of word tokens.
        n: Size of n-grams (default: 2 for bigrams).

    Returns:
        List of n-gram tuples.
    """
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def compute_ngram_frequencies(tokens: List[str], n: int = 2) -> Dict[str, int]:
    """
    Compute frequency counts of content n-grams.

    Computes bigrams over the provided token list for content analysis.

    Args:
        tokens: List of word tokens for n-gram computation.
        n: Size of n-grams.

    Returns:
        Dictionary mapping n-gram strings to their counts.
    """
    ngrams = compute_ngrams(tokens, n)
    counts = Counter(ngrams)

    result = {}
    for ngram, count in counts.most_common():
        key = ' '.join(ngram)
        result[key] = count

    return result


def compute_readability(word_count: int, sentence_count: int) -> Dict[str, float]:
    """
    Compute readability metrics using a simplified Flesch-like formula.

    score = max(0, 100 - (avg_words_per_sentence * 3))
    Higher scores indicate easier readability (shorter sentences).

    Args:
        word_count: Total number of words in text.
        sentence_count: Total number of sentences in text.

    Returns:
        Dictionary with readability metrics.
    """
    if sentence_count == 0 or word_count == 0:
        return {
            'avg_words_per_sentence': 0.0,
            'readability_score': 0.0
        }

    avg_words_per_sentence = round(word_count / sentence_count, 2)
    readability_score = round(max(0.0, 100.0 - (avg_words_per_sentence * 3)), 2)

    return {
        'avg_words_per_sentence': avg_words_per_sentence,
        'readability_score': readability_score
    }


def compute_statistics(all_tokens: List[str], filtered_tokens: List[str],
                       sentences: List[str]) -> Dict[str, Any]:
    """
    Compute all document-level statistics.

    Args:
        all_tokens: Complete token list including stopwords.
        filtered_tokens: Tokens with stopwords removed.
        sentences: List of sentences.

    Returns:
        Dictionary with all computed statistics.
    """
    word_count = len(all_tokens)
    sentence_count = len(sentences)
    unique_words = len(set(all_tokens))

    # Word frequencies
    frequencies = compute_word_frequencies(all_tokens, filtered_tokens)

    # Content bigrams from the full token list for contextual analysis
    bigrams = compute_ngram_frequencies(all_tokens, n=2)

    # Readability
    readability = compute_readability(word_count, sentence_count)

    return {
        'word_count': word_count,
        'sentence_count': sentence_count,
        'unique_words': unique_words,
        'top_frequencies': dict(list(frequencies.items())[:10]),
        'top_bigrams': dict(list(bigrams.items())[:10]),
        'readability': readability,
    }
