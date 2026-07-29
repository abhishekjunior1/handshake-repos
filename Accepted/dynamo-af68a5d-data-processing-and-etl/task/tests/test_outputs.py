"""Pytest test suite for the text processing pipeline.

Verifies document analysis results against expected output for
word frequencies, content bigrams, and corpus-level statistics.
"""

import json
import os

import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected output from the test fixtures."""
    with open(EXPECTED_OUTPUT_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual output produced by the pipeline."""
    with open(ACTUAL_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produced an output file at the expected path."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), (
        f"Output file not found at {ACTUAL_OUTPUT_PATH}"
    )


def test_output_is_valid_json(actual_output):
    """Verify that the output file contains valid JSON with required structure."""
    assert "document_count" in actual_output, "Output missing 'document_count'"
    assert "documents" in actual_output, "Output missing 'documents'"
    assert "corpus_statistics" in actual_output, "Output missing 'corpus_statistics'"


def test_document_count(actual_output, expected_output):
    """Verify correct number of documents were processed."""
    assert actual_output["document_count"] == expected_output["document_count"], (
        f"Expected {expected_output['document_count']} documents, "
        f"got {actual_output['document_count']}"
    )


def test_word_frequencies_per_document(actual_output, expected_output):
    """Verify per-document word frequencies reflect correct content token proportions.

    Frequencies should be relative to the content vocabulary (stopwords excluded),
    not the total token count including function words.
    """
    for i, (actual_doc, expected_doc) in enumerate(
        zip(actual_output["documents"], expected_output["documents"])
    ):
        actual_freq = actual_doc["statistics"]["top_frequencies"]
        expected_freq = expected_doc["statistics"]["top_frequencies"]
        assert actual_freq == expected_freq, (
            f"Document {i} word frequencies mismatch: "
            f"expected {expected_freq}, got {actual_freq}"
        )


def test_bigrams_per_document(actual_output, expected_output):
    """Verify per-document bigrams contain only content word pairs.

    Content bigrams should be computed from filtered tokens (stopwords removed)
    to reflect meaningful word co-occurrence patterns.
    """
    for i, (actual_doc, expected_doc) in enumerate(
        zip(actual_output["documents"], expected_output["documents"])
    ):
        actual_bi = actual_doc["statistics"]["top_bigrams"]
        expected_bi = expected_doc["statistics"]["top_bigrams"]
        assert actual_bi == expected_bi, (
            f"Document {i} bigrams mismatch: "
            f"expected {expected_bi}, got {actual_bi}"
        )


def test_corpus_bigrams(actual_output, expected_output):
    """Verify corpus-level bigrams reflect content word patterns across all documents.

    Corpus bigrams should aggregate content word co-occurrences, excluding
    stopword pairs that don't represent meaningful topical relationships.
    """
    actual_bi = actual_output["corpus_statistics"]["corpus_bigrams"]
    expected_bi = expected_output["corpus_statistics"]["corpus_bigrams"]
    assert actual_bi == expected_bi, (
        f"Corpus bigrams mismatch: expected {expected_bi}, got {actual_bi}"
    )


def test_corpus_frequencies(actual_output, expected_output):
    """Verify corpus-level word frequency values are correct."""
    actual_freq = actual_output["corpus_statistics"]["corpus_frequencies"]
    expected_freq = expected_output["corpus_statistics"]["corpus_frequencies"]
    assert actual_freq == expected_freq, (
        f"Corpus frequencies mismatch"
    )


def test_readability_scores(actual_output, expected_output):
    """Verify readability scores match expected values."""
    for i, (actual_doc, expected_doc) in enumerate(
        zip(actual_output["documents"], expected_output["documents"])
    ):
        actual_r = actual_doc["statistics"]["readability"]
        expected_r = expected_doc["statistics"]["readability"]
        assert actual_r == expected_r, (
            f"Document {i} readability mismatch: "
            f"expected {expected_r}, got {actual_r}"
        )


def test_document_word_counts(actual_output, expected_output):
    """Verify basic word and sentence counts for each document."""
    for i, (actual_doc, expected_doc) in enumerate(
        zip(actual_output["documents"], expected_output["documents"])
    ):
        actual_s = actual_doc["statistics"]
        expected_s = expected_doc["statistics"]
        assert actual_s["word_count"] == expected_s["word_count"], (
            f"Document {i} word_count mismatch"
        )
        assert actual_s["sentence_count"] == expected_s["sentence_count"], (
            f"Document {i} sentence_count mismatch"
        )
