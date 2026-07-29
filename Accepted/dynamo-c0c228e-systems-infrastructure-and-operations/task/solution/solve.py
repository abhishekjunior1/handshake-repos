#!/usr/bin/env python3
"""Fix 3 bugs in the Shell Environment Profile Compiler."""
import os
TASK_DIR = "/app"

def patch_file(filepath, old_str, new_str):
    with open(filepath, 'r') as f:
        content = f.read()
    if old_str not in content:
        raise ValueError(f"Patch target not found in {filepath}")
    content = content.replace(old_str, new_str, 1)
    with open(filepath, 'w') as f:
        f.write(content)

def fix_bug1():
    """Fix multiline joining: use actual newline instead of literal \\n."""
    fp = os.path.join(TASK_DIR, "file_parser.py")
    patch_file(fp,
        '            full_value = "\\\\n".join(value_parts)\n            variables[var_name] = {\n                "value": full_value,\n                "quote_style": "double",',
        '            full_value = "\\n".join(value_parts)\n            variables[var_name] = {\n                "value": full_value,\n                "quote_style": "double",')
    patch_file(fp,
        '            full_value = "\\\\n".join(value_parts)\n            variables[var_name] = {\n                "value": full_value,\n                "quote_style": "single",',
        '            full_value = "\\n".join(value_parts)\n            variables[var_name] = {\n                "value": full_value,\n                "quote_style": "single",')

def fix_bug2():
    """Fix interpolation: resolve against full state, not incremental partial state."""
    fp = os.path.join(TASK_DIR, "interpolation_engine.py")
    patch_file(fp,
        '''    resolved = {}

    for var_name in variables:
        value = variables[var_name]
        # Resolve against current partial state (only previously resolved vars)
        expanded = _expand_value(value, resolved)
        resolved[var_name] = expanded

    return resolved''',
        '''    resolved = {}

    # First pass: expand against full variable map for complete resolution
    for var_name in variables:
        value = variables[var_name]
        expanded = _expand_value(value, variables)
        resolved[var_name] = expanded

    # Iterate until stable (resolve transitive references)
    for _ in range(10):
        changed = False
        for var_name in list(resolved.keys()):
            new_val = _expand_value(resolved[var_name], resolved)
            if new_val != resolved[var_name]:
                resolved[var_name] = new_val
                changed = True
        if not changed:
            break

    return resolved''')

def fix_bug3():
    """Fix quote stripping: remove only one enclosing pair, not all boundary quotes."""
    fp = os.path.join(TASK_DIR, "quote_handler.py")
    patch_file(fp,
        '''    # Double-quoted values: strip double-quote characters from boundaries
    if value.startswith('"'):
        return value.strip('"')

    # Single-quoted values: strip single-quote characters from boundaries
    if value.startswith("'"):
        return value.strip("'")''',
        '''    # Double-quoted values: remove exactly one enclosing pair
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]

    # Single-quoted values: remove exactly one enclosing pair
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1]''')

def main():
    fix_bug1()
    fix_bug2()
    fix_bug3()
    import subprocess
    subprocess.run(["python3", os.path.join(TASK_DIR, "pipeline.py")], cwd=TASK_DIR, check=True)

if __name__ == "__main__":
    main()
