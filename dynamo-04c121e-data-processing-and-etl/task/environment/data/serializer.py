"""Serializer for the NestedConf (.nconf) configuration format.

Converts resolved configuration data into a canonical output representation.
The serializer takes the resolved values and section metadata and produces
a structured dictionary ready for JSON output.

Output format:
  {
    "sections": {
      "SectionName": {
        "key1": "resolved_value1",
        "key2": "resolved_value2"
      }
    },
    "metadata": { ... }
  }

Section names in the output use the ORIGINAL casing from the source file
to preserve the author's intent. This is important for configuration files
where section names may be used as identifiers in downstream systems.
"""

from typing import Dict, List, Any, Optional
from parser import DocumentNode, SectionNode


class SerializerError(Exception):
    """Raised when serialization encounters an error."""
    pass


class NestedConfSerializer:
    """Serializes resolved NestedConf data into canonical output format.

    The serializer accepts a document AST and resolution results, combining
    them into the final output dictionary. Section ordering in the output
    follows the original document order.

    The serializer uses the section_names parameter to determine output keys.
    This should contain the original-cased section names to preserve authoring
    intent in the output format.
    """

    def __init__(self, document: DocumentNode):
        self.document = document

    def serialize(self, resolved_values: Dict[str, Dict[str, str]],
                  section_names: List[str]) -> Dict[str, Any]:
        """Serialize resolved values into the canonical output format.

        Args:
            resolved_values: Mapping of normalized section names to their
                           resolved key-value pairs.
            section_names: List of section names to use as output keys.
                          Should be the original-cased names for proper output.

        Returns:
            Dictionary with 'sections' and 'metadata' keys.
        """
        output = {
            'sections': {},
            'metadata': {}
        }

        # Build output sections using provided section names as keys
        for i, section in enumerate(self.document.sections):
            # Use the provided section name as the output key
            output_key = section_names[i] if i < len(section_names) else section.name
            normalized = section.name

            if normalized in resolved_values:
                output['sections'][output_key] = resolved_values[normalized]
            else:
                # Preserve empty sections in output per format spec
                output['sections'][output_key] = {}

        # Add document metadata
        output['metadata'] = {
            'section_count': len(self.document.sections),
            'total_keys': sum(len(v) for v in resolved_values.values()),
            'has_references': any(
                any('${' in str(val) for val in vals.values())
                for vals in resolved_values.values()
            ),
            'sections_order': section_names
        }

        return output

    def serialize_to_flat(self, resolved_values: Dict[str, Dict[str, str]],
                          section_names: List[str]) -> Dict[str, str]:
        """Serialize to a flat key=value format using dot notation.

        Creates a flat dictionary where keys are section.key format,
        useful for environment variable export or property file generation.

        Args:
            resolved_values: The resolved values by section.
            section_names: Original-cased section names for key prefixes.

        Returns:
            Flat dictionary with dot-notation keys.
        """
        flat = {}

        for i, section in enumerate(self.document.sections):
            prefix = section_names[i] if i < len(section_names) else section.name
            normalized = section.name

            if normalized in resolved_values:
                for key, value in resolved_values[normalized].items():
                    flat[f"{prefix}.{key}"] = value

        return flat
