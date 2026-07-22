"""
Data loader module for the text processing pipeline.
Loads JSON documents containing text content and metadata.
"""

import json
import sys
from typing import List, Dict, Any


def load_documents(filepath: str) -> List[Dict[str, Any]]:
    """
    Load documents from a JSON file.
    
    Each document should have at minimum a 'text' field.
    Optional fields: 'id', 'title', 'author', 'tags'.
    
    Args:
        filepath: Path to the JSON file containing documents.
        
    Returns:
        List of document dictionaries with validated structure.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: Document file must contain a JSON array", file=sys.stderr)
        sys.exit(1)

    documents = []
    for idx, doc in enumerate(data):
        if not isinstance(doc, dict):
            print(f"Warning: Skipping non-dict entry at index {idx}", file=sys.stderr)
            continue
        if 'text' not in doc:
            print(f"Warning: Skipping document at index {idx} (no 'text' field)", file=sys.stderr)
            continue

        validated = {
            'id': doc.get('id', f'doc_{idx}'),
            'title': doc.get('title', f'Document {idx}'),
            'author': doc.get('author', 'unknown'),
            'tags': doc.get('tags', []),
            'text': doc['text']
        }
        documents.append(validated)

    if not documents:
        print("Error: No valid documents found", file=sys.stderr)
        sys.exit(1)

    return documents
