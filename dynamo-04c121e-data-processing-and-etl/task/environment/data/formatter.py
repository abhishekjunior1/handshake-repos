"""Formatter for the NestedConf (.nconf) configuration format.

Generates the final JSON output with the parsed configuration tree,
resolution metadata, and validation summaries. Handles output encoding
and formatting for consistent, deterministic output.
"""

import json
from typing import Dict, List, Any, Optional
from parser import DocumentNode


class FormatterError(Exception):
    """Raised when output formatting encounters an error."""
    pass


class NestedConfFormatter:
    """Formats serialized configuration data into final JSON output.

    Takes the serialized output from the serializer along with additional
    metadata (resolution stats, dependency info) and produces the final
    JSON string suitable for writing to disk.

    Output structure:
      {
        "config": { sections dict from serializer },
        "resolution_info": {
          "total_references": N,
          "resolved_count": N,
          "unresolved": [...],
          "circular": [...]
        },
        "document_info": {
          "section_count": N,
          "total_keys": N,
          "dependencies": { section -> [deps] }
        }
      }
    """

    def __init__(self, indent: int = 2):
        self.indent = indent

    def format_output(self, serialized: Dict[str, Any],
                      resolution_info: Dict[str, Any],
                      dependencies: Dict[str, List[str]]) -> str:
        """Format the final output as a JSON string.

        Args:
            serialized: Output from the serializer (sections + metadata).
            resolution_info: Statistics about reference resolution.
            dependencies: Section dependency graph.

        Returns:
            Formatted JSON string.
        """
        output = {
            'config': serialized['sections'],
            'resolution_info': {
                'total_references': resolution_info.get('resolution_count', 0),
                'resolved_count': resolution_info.get('resolved_count', 0),
                'unresolved': resolution_info.get('unresolved_refs', []),
                'circular': resolution_info.get('circular_refs', [])
            },
            'document_info': {
                'section_count': serialized['metadata']['section_count'],
                'total_keys': serialized['metadata']['total_keys'],
                'has_references': serialized['metadata']['has_references'],
                'sections_order': serialized['metadata']['sections_order'],
                'dependencies': {
                    k: sorted(v) for k, v in dependencies.items()
                }
            }
        }

        return json.dumps(output, indent=self.indent, sort_keys=False,
                          ensure_ascii=False)

    def format_summary(self, serialized: Dict[str, Any],
                       resolution_info: Dict[str, Any]) -> str:
        """Format a human-readable summary of the parsing results.

        Useful for debugging and validation. Returns a multi-line string
        describing the document structure and resolution status.
        """
        lines = []
        lines.append(f"Document Summary:")
        lines.append(f"  Sections: {serialized['metadata']['section_count']}")
        lines.append(f"  Total keys: {serialized['metadata']['total_keys']}")
        lines.append(f"  References resolved: {resolution_info.get('resolved_count', 0)}")

        if resolution_info.get('unresolved_refs'):
            lines.append(f"  Unresolved: {', '.join(resolution_info['unresolved_refs'])}")
        if resolution_info.get('circular_refs'):
            lines.append(f"  Circular: {', '.join(resolution_info['circular_refs'])}")

        return '\n'.join(lines)

    def write_output(self, output_json: str, output_path: str):
        """Write formatted JSON to the specified file path.

        Args:
            output_json: The formatted JSON string.
            output_path: Absolute path to write the output file.

        Raises:
            FormatterError: If writing fails.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_json)
                f.write('\n')  # Trailing newline for POSIX compliance
        except OSError as e:
            raise FormatterError(f"Failed to write output: {e}")
