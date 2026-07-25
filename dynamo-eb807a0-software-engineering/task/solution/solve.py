#!/usr/bin/env python3
"""
Solution: patches the three bugs in the type inference pipeline and runs it.
"""

import subprocess
import sys


def patch_file(filepath, old_string, new_string):
    """Replace old_string with new_string in filepath."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old_string not in content:
        print(f"ERROR: Could not find patch target in {filepath}")
        print(f"  Looking for: {repr(old_string[:80])}")
        sys.exit(1)
    content = content.replace(old_string, new_string, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Patched {filepath}")


def main():
    # Bug 1 (pipeline.py): Apply substitution to binding types before reporting
    patch_file(
        "/app/pipeline.py",
        "final_bindings[name] = binding_type",
        "final_bindings[name] = apply_substitution(substitution, binding_type)"
    )

    # Bug 2 (unifier.py): Don't apply existing substitution to new bindings
    patch_file(
        "/app/unifier.py",
        "composed[var_name] = apply_substitution(existing, var_type)",
        "composed[var_name] = var_type"
    )

    # Bug 3 (constraint_generator.py): Fix swapped arrow direction in function application
    patch_file(
        "/app/constraint_generator.py",
        "self.constraints.append((func_type, TypeArrow(result_type, arg_type)))",
        "self.constraints.append((func_type, TypeArrow(arg_type, result_type)))"
    )

    # Run the pipeline
    result = subprocess.run(
        ["python3", "/app/pipeline.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)
    print("Pipeline executed successfully")


if __name__ == "__main__":
    main()
