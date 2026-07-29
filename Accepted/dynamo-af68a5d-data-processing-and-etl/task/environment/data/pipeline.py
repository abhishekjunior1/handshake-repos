"""
Text processing pipeline orchestrator.
Loads documents and runs them through normalization, tokenization,
entity extraction, and statistical analysis.
"""

import sys
import os

import data_loader
import normalizer
import tokenizer
import entity_extractor
import statistics
import report_generator


def process_document(document):
    """
    Process a single document through all pipeline stages.

    Args:
        document: Document dict with 'text', 'id', 'title' fields.

    Returns:
        Processed document dict with all computed results.
    """
    raw_text = document['text']
    result = {
        'id': document['id'],
        'title': document['title']
    }

    # Stage 1: Text normalization
    normalized_text = normalizer.normalize(raw_text)

    # Stage 2: Entity extraction on normalized text
    entities = entity_extractor.extract(normalized_text)
    result['entities'] = entities

    # Stage 3: Tokenization
    token_result = tokenizer.tokenize(normalized_text)
    sentences = token_result['sentences']
    all_tokens = token_result['tokens']
    filtered_tokens = token_result['tokens_without_stopwords']

    result['sentences'] = sentences
    result['tokens'] = all_tokens
    result['filtered_tokens'] = filtered_tokens

    # Stage 4: Statistics computation
    stats = statistics.compute_statistics(
        all_tokens, filtered_tokens, sentences
    )
    result['statistics'] = stats

    return result


def run_pipeline(input_path, output_path):
    """
    Run the complete text processing pipeline.

    Args:
        input_path: Path to input documents JSON file.
        output_path: Path to write the output JSON file.
    """
    documents = data_loader.load_documents(input_path)

    processed = []
    for doc in documents:
        result = process_document(doc)
        processed.append(result)

    # Compute corpus-level statistics across all documents
    corpus_stats = _compute_corpus_statistics(processed)

    report = report_generator.generate_report(processed, corpus_stats)
    report_generator.write_report(report, output_path)


def _compute_corpus_statistics(processed_docs):
    """Compute corpus-level aggregate statistics across all documents."""
    all_corpus_tokens = []
    all_corpus_filtered = []
    total_sentences = 0

    for doc in processed_docs:
        all_corpus_tokens.extend(doc['tokens'])
        all_corpus_filtered.extend(doc['filtered_tokens'])
        total_sentences += len(doc['sentences'])

    # Corpus-wide frequency: count in filtered, denominator from filtered
    corpus_frequencies = statistics.compute_word_frequencies(
        all_corpus_filtered, all_corpus_filtered
    )

    # Corpus-wide bigrams computed from full token context for completeness
    corpus_bigrams = statistics.compute_ngram_frequencies(
        all_corpus_tokens, n=2
    )

    # Corpus readability
    corpus_readability = statistics.compute_readability(
        len(all_corpus_tokens), total_sentences
    )

    return {
        'total_documents': len(processed_docs),
        'total_tokens': len(all_corpus_tokens),
        'total_unique_tokens': len(set(all_corpus_tokens)),
        'corpus_frequencies': dict(list(corpus_frequencies.items())[:20]),
        'corpus_bigrams': dict(list(corpus_bigrams.items())[:15]),
        'corpus_readability': corpus_readability,
    }


if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'documents.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'output.json'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(input_file):
        input_file = os.path.join(script_dir, input_file)
    if not os.path.isabs(output_file):
        output_file = os.path.join(script_dir, output_file)

    run_pipeline(input_file, output_file)
