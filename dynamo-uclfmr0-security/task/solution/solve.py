#!/usr/bin/env python3
"""
Solution for the Security Compliance Hardening Scanner Pipeline.
Patches 3 bugs:
1. pipeline.py: Use resolve_inherited_rules (walks ancestor chain) instead of get_rules_for_profile (direct only)
2. pipeline.py: Pass waived_results to scoring/formatting instead of raw_results (computed-but-unused fix)
3. exception_matcher.py: Use fnmatch glob matching instead of exact string comparison
"""

import os

TASK_DIR = "/app"


def patch_file(filepath, old_str, new_str):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old_str not in content:
        raise ValueError(f"Patch target not found in {filepath}: {repr(old_str[:80])}")
    content = content.replace(old_str, new_str, 1)
    with open(filepath, 'w') as f:
        f.write(content)


def fix_bug1_inheritance():
    """Fix Bug 1: Use resolve_inherited_rules to walk full ancestor chain."""
    filepath = os.path.join(TASK_DIR, "pipeline.py")
    old = """            applicable_rules = get_rules_for_profile(rules, profile_id)"""
    new = """            applicable_rules = resolve_inherited_rules(rules, profiles, profile_id)"""
    patch_file(filepath, old, new)


def fix_bug2_waived_results():
    """Fix Bug 2: Pass waived_results to scoring and formatting instead of raw_results."""
    filepath = os.path.join(TASK_DIR, "pipeline.py")

    # Fix scoring: use waived_results
    old = """    # Step 7: Compute scores and analytics
    scores = compute_compliance_scores(raw_results, all_applicable_rules)
    severity_dist = compute_severity_distribution(raw_results, all_applicable_rules)
    risk_score = compute_risk_score(raw_results, all_applicable_rules)
    critical_findings = get_critical_findings(raw_results, all_applicable_rules)"""
    new = """    # Step 7: Compute scores and analytics
    scores = compute_compliance_scores(waived_results, all_applicable_rules)
    severity_dist = compute_severity_distribution(waived_results, all_applicable_rules)
    risk_score = compute_risk_score(waived_results, all_applicable_rules)
    critical_findings = get_critical_findings(waived_results, all_applicable_rules)"""
    patch_file(filepath, old, new)

    # Fix report formatting: use waived_results
    old = """        assessment_results=raw_results,"""
    new = """        assessment_results=waived_results,"""
    patch_file(filepath, old, new)


def fix_bug3_glob_matching():
    """Fix Bug 3: Use glob pattern matching instead of exact string comparison."""
    filepath = os.path.join(TASK_DIR, "exception_matcher.py")

    # Add fnmatch import
    old = '''"""
Exception and waiver matcher for compliance assessment.
Matches waiver definitions against resources to determine exemptions.
"""'''
    new = '''"""
Exception and waiver matcher for compliance assessment.
Matches waiver definitions against resources to determine exemptions.
"""

import fnmatch'''
    patch_file(filepath, old, new)

    # Replace exact match with glob matching
    old = """    return resource_id == pattern"""
    new = """    return fnmatch.fnmatch(resource_id, pattern)"""
    patch_file(filepath, old, new)


def main():
    """Apply all patches and run the pipeline."""
    fix_bug1_inheritance()
    fix_bug2_waived_results()
    fix_bug3_glob_matching()

    # Run the pipeline to generate output
    import subprocess
    subprocess.run(["python3", os.path.join(TASK_DIR, "pipeline.py")], cwd=TASK_DIR, check=True)


if __name__ == "__main__":
    main()
