"""Oracle solution - patches the 3 bugs in the NestedConf pipeline and runs it."""

import subprocess


def patch_file(filepath, old, new):
    """Replace exact string in file."""
    with open(filepath, 'r') as f:
        content = f.read()
    assert old in content, f"Patch target not found in {filepath}: {repr(old[:80])}"
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    # Bug 1 Fix: Change resolver mode from 'shallow' to 'full' in pipeline.py
    # Shallow mode only resolves direct references; full mode resolves chained refs
    patch_file(
        '/app/pipeline.py',
        "resolver = NestedConfResolver(document, mode='shallow')",
        "resolver = NestedConfResolver(document, mode='full')"
    )

    # Bug 2 Fix: Correct escape sequence processing order in parser.py
    # Must process \\\\ (literal backslash) BEFORE \\n, \\t, etc.
    # Otherwise \\temp gets \\t matched as tab escape
    patch_file(
        '/app/parser.py',
        """        # Process single-char escapes for efficient pattern matching
        result = result.replace('\\\\n', '\\n')
        result = result.replace('\\\\t', '\\t')
        result = result.replace('\\\\r', '\\r')
        result = result.replace('\\\\"', '"')
        # Process literal backslash last — any remaining double-backslash
        # at this point is a true literal backslash
        result = result.replace('\\\\\\\\', '\\\\')""",
        """        # Process literal backslash first using placeholder to avoid
        # consuming characters needed by subsequent escape patterns
        result = result.replace('\\\\\\\\', '\\x00')
        result = result.replace('\\\\n', '\\n')
        result = result.replace('\\\\t', '\\t')
        result = result.replace('\\\\r', '\\r')
        result = result.replace('\\\\"', '"')
        result = result.replace('\\x00', '\\\\')"""
    )

    # Bug 3 Fix: Use original_name instead of normalized name for output keys
    # Normalized names are lowercase; output should preserve original casing
    patch_file(
        '/app/pipeline.py',
        "section_names = [s.name for s in document.sections]",
        "section_names = [s.original_name for s in document.sections]"
    )

    # Run the fixed pipeline
    subprocess.run(['python3', '/app/pipeline.py'], check=True)


if __name__ == '__main__':
    main()
