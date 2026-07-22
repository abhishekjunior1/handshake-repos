"""Oracle solution - patches bugs in the text processing pipeline."""

import subprocess
import sys


def patch_file(filepath, old_text, new_text):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old_text not in content:
        print(f"WARNING: patch target not found in {filepath}")
        return False
    content = content.replace(old_text, new_text, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    return True


def fix_bug1():
    """Fix Bug 1: Word frequency uses wrong denominator.

    compute_word_frequencies divides by len(all_tokens) which includes
    stopwords, deflating frequencies when stopwords are present.
    Fix: divide by len(filtered_tokens) for correct relative frequency.
    """
    patch_file(
        "/app/statistics.py",
        '    # Frequency relative to total token population for corpus-normalized scores\n'
        '    total = len(all_tokens)',
        '    # Frequency relative to content token population\n'
        '    total = len(filtered_tokens)',
    )


def fix_bug2():
    """Fix Bug 2: Per-document bigrams computed from all tokens including stopwords.

    compute_statistics passes all_tokens to compute_ngram_frequencies, which
    includes stopword pairs in content bigrams. Fix: use filtered_tokens.
    """
    patch_file(
        "/app/statistics.py",
        '    # Content bigrams from the full token list for contextual analysis\n'
        '    bigrams = compute_ngram_frequencies(all_tokens, n=2)',
        '    # Content bigrams from filtered tokens (stopwords excluded)\n'
        '    bigrams = compute_ngram_frequencies(filtered_tokens, n=2)',
    )


def fix_bug3():
    """Fix Bug 3: Corpus-level bigrams use all tokens instead of filtered.

    _compute_corpus_statistics passes all_corpus_tokens to bigram computation,
    including stopwords in corpus-level content analysis. Fix: use filtered.
    """
    patch_file(
        "/app/pipeline.py",
        '    # Corpus-wide bigrams computed from full token context for completeness\n'
        '    corpus_bigrams = statistics.compute_ngram_frequencies(\n'
        '        all_corpus_tokens, n=2\n'
        '    )',
        '    # Corpus-wide bigrams computed from filtered tokens\n'
        '    corpus_bigrams = statistics.compute_ngram_frequencies(\n'
        '        all_corpus_filtered, n=2\n'
        '    )',
    )


if __name__ == "__main__":
    fix_bug1()
    fix_bug2()
    fix_bug3()
    print("All patches applied successfully.")

    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline error: {result.stderr}")
        sys.exit(1)
    print("Pipeline executed successfully.")
