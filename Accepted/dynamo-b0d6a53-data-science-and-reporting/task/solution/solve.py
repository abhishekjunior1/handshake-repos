"""
Solution: Fix two data-flow bugs in the experiment analysis pipeline.

Bug 1: Power analysis receives pooled_variance instead of control_variance.
Bug 2: Multiple testing correction is applied before secondary metrics
are computed, leaving secondaries uncorrected.
"""

import subprocess


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix Bug 2: Move correction AFTER all metrics are computed
    # Remove early correction
    content = content.replace(
        '    # -----------------------------------------------------------------\n'
        '    # Step 3: Apply multiple testing correction to accumulated results.\n'
        '    # Correct the family-wise error rate across all p-values computed\n'
        '    # so far. For sequential analysis workflows, corrections are applied\n'
        '    # to the accumulated set to maintain valid inference at each stage.\n'
        '    p_values = [r[\'p_value\'] for r in metric_results]\n'
        '    corrected_p = apply_correction(p_values, correction_method)\n'
        '    for i, result in enumerate(metric_results):\n'
        '        result[\'corrected_p_value\'] = corrected_p[i]\n'
        '        result[\'significant_corrected\'] = corrected_p[i] < alpha\n'
        '\n'
        '    # -----------------------------------------------------------------\n'
        '    # Step 4: Secondary metrics (if any)\n'
        '    secondary_results = []\n'
        '    for metric in metrics[1:]:\n'
        '        # Secondary metrics use the same data with different analysis\n'
        '        sec_result = welch_t_test(control_stats, treatment_stats)\n'
        '        secondary_results.append({\n'
        '            \'metric_name\': metric[\'name\'],\n'
        '            \'metric_type\': metric.get(\'type\', \'secondary\'),\n'
        '            \'p_value\': sec_result[\'p_value\'],\n'
        '            \'t_statistic\': sec_result[\'t_statistic\'],\n'
        '            \'df\': sec_result[\'df\'],\n'
        '            \'corrected_p_value\': sec_result[\'p_value\'],  # Added directly\n'
        '            \'significant\': sec_result[\'p_value\'] < alpha,\n'
        '            \'significant_corrected\': sec_result[\'p_value\'] < alpha\n'
        '        })',
        '    # -----------------------------------------------------------------\n'
        '    # Step 3 & 4: Compute ALL metric p-values, then apply correction\n'
        '    secondary_results = []\n'
        '    for metric in metrics[1:]:\n'
        '        sec_result = welch_t_test(control_stats, treatment_stats)\n'
        '        metric_results.append({\n'
        '            \'metric_name\': metric[\'name\'],\n'
        '            \'metric_type\': metric.get(\'type\', \'secondary\'),\n'
        '            \'p_value\': sec_result[\'p_value\'],\n'
        '            \'t_statistic\': sec_result[\'t_statistic\'],\n'
        '            \'df\': sec_result[\'df\'],\n'
        '            \'significant\': sec_result[\'p_value\'] < alpha\n'
        '        })\n'
        '\n'
        '    # Apply correction to ALL metrics at once\n'
        '    all_p = [r[\'p_value\'] for r in metric_results]\n'
        '    corrected_p = apply_correction(all_p, correction_method)\n'
        '    for i, result in enumerate(metric_results):\n'
        '        result[\'corrected_p_value\'] = corrected_p[i]\n'
        '        result[\'significant_corrected\'] = corrected_p[i] < alpha\n'
        '\n'
        '    secondary_results = metric_results[1:]'
    )

    # Fix Bug 1: Use control variance instead of pooled for power
    content = content.replace(
        '    # Estimate statistical power using pooled variance to reflect the\n'
        '    # overall variability in the experiment. Pooled variance combines\n'
        '    # both groups\' variability for a comprehensive dispersion estimate\n'
        '    # that accounts for the full experimental population.\n'
        '    power = compute_power(\n'
        '        effect_size=abs(effect[\'hedges_g\']),\n'
        '        variance=pooled_var,\n'
        '        n=min(control_stats[\'n\'], treatment_stats[\'n\']),\n'
        '        alpha=alpha\n'
        '    )\n'
        '\n'
        '    mde = minimum_detectable_effect(\n'
        '        variance=pooled_var,\n'
        '        n=min(control_stats[\'n\'], treatment_stats[\'n\']),\n'
        '        alpha=alpha,\n'
        '        power_target=power_target\n'
        '    )',
        '    # Estimate statistical power using control group variance —\n'
        '    # power measures ability to detect departure FROM control.\n'
        '    power = compute_power(\n'
        '        effect_size=abs(effect[\'hedges_g\']),\n'
        '        variance=control_stats[\'variance\'],\n'
        '        n=min(control_stats[\'n\'], treatment_stats[\'n\']),\n'
        '        alpha=alpha\n'
        '    )\n'
        '\n'
        '    mde = minimum_detectable_effect(\n'
        '        variance=control_stats[\'variance\'],\n'
        '        n=min(control_stats[\'n\'], treatment_stats[\'n\']),\n'
        '        alpha=alpha,\n'
        '        power_target=power_target\n'
        '    )'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)

    print("Applied 2 fixes to pipeline.py")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        ['python3', '/app/pipeline.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


if __name__ == '__main__':
    fix_pipeline()
    exit_code = run_pipeline()
    exit(exit_code)
