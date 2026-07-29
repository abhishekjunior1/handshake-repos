"""
Report generator module.
Formats processed documents and corpus statistics into the output JSON.
"""

import json
from typing import List, Dict, Any


def generate_report(processed_docs: List[Dict[str, Any]],
                    corpus_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the final analysis report.

    Args:
        processed_docs: List of processed document results.
        corpus_stats: Corpus-level aggregate statistics.

    Returns:
        Report dictionary ready for JSON serialization.
    """
    documents = []
    for doc in processed_docs:
        doc_entry = {
            'id': doc['id'],
            'title': doc['title'],
            'entities': doc['entities'],
            'statistics': doc['statistics'],
        }
        documents.append(doc_entry)

    return {
        'document_count': len(documents),
        'documents': documents,
        'corpus_statistics': corpus_stats,
    }


def write_report(report: Dict[str, Any], output_path: str) -> None:
    """
    Write the report to a JSON file.

    Args:
        report: Report dictionary.
        output_path: Path to write the output file.
    """
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
