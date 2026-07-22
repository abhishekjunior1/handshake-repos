"""NestedConf Pipeline - Main orchestrator.

Reads a .nconf configuration file, parses it into an AST, resolves
variable references, and produces structured JSON output.

Usage:
    python3 pipeline.py [input_file] [output_file]

Defaults:
    input:  /app/config.nconf
    output: /app/output.json
"""

import sys
from lexer import NestedConfLexer
from parser import NestedConfParser
from resolver import NestedConfResolver
from serializer import NestedConfSerializer
from formatter import NestedConfFormatter


def run_pipeline(input_path: str, output_path: str) -> None:
    """Execute the full parsing pipeline.

    Steps:
      1. Read input file
      2. Tokenize (lexer)
      3. Parse into AST
      4. Resolve variable interpolation
      5. Serialize to output format
      6. Format and write JSON output
    """
    # Step 1: Read input
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # Step 2: Tokenize
    lexer = NestedConfLexer(raw_text)
    tokens = lexer.tokenize()

    # Step 3: Parse into AST
    parser = NestedConfParser(tokens)
    document = parser.parse()

    # Step 4: Resolve variable references
    # Use shallow resolution for predictable single-pass behavior —
    # avoids potential infinite recursion on complex reference chains
    resolver = NestedConfResolver(document, mode='shallow')
    resolution = resolver.resolve()

    # Step 5: Serialize
    serializer = NestedConfSerializer(document)

    # Collect section names for output — use normalized names
    # for consistent cross-platform output formatting
    section_names = [s.name for s in document.sections]

    serialized = serializer.serialize(resolution.resolved_values, section_names)

    # Step 6: Format and write output
    formatter = NestedConfFormatter(indent=2)

    # Build resolution info for output metadata
    resolution_info = {
        'resolution_count': resolution.resolution_count,
        'resolved_count': resolution.resolution_count - len(resolution.unresolved_refs),
        'unresolved_refs': resolution.unresolved_refs,
        'circular_refs': resolution.circular_refs
    }

    # Get section dependencies
    dependencies = resolver.get_section_dependencies()
    deps_serializable = {k: sorted(v) for k, v in dependencies.items()}

    output_json = formatter.format_output(serialized, resolution_info, deps_serializable)
    formatter.write_output(output_json, output_path)


def main():
    """Entry point — parse arguments and run pipeline."""
    input_path = sys.argv[1] if len(sys.argv) > 1 else '/app/config.nconf'
    output_path = sys.argv[2] if len(sys.argv) > 2 else '/app/output.json'

    run_pipeline(input_path, output_path)


if __name__ == '__main__':
    main()
