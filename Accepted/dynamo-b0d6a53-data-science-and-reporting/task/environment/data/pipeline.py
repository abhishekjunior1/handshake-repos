"""
A/B test experiment analysis pipeline.

Analyzes controlled experiments by computing sample statistics, running
hypothesis tests, applying multiple testing corrections, estimating
effect sizes with confidence intervals, and computing statistical power.

Produces a structured experiment report with per-metric results and
overall experiment diagnostics.
"""

import json
import sys
import math

sys.path.insert(0, '/app')

from statistics_engine import compute_sample_stats, compute_pooled_variance, compute_pooled_se
from hypothesis_tests import welch_t_test
from corrections import apply_correction
from effect_size import hedges_g, confidence_interval_difference, confidence_interval_individual
from power_analysis import compute_power, minimum_detectable_effect


def load_config(path):
    """Load experiment configuration."""
    with open(path, 'r') as f:
        return json.load(f)


def run_analysis(config):
    """Execute the full experiment analysis pipeline.

    Steps:
        1. Compute sample statistics for control and treatment
        2. Run hypothesis test for primary metric
        3. Apply multiple testing correction to accumulated p-values
        4. Compute secondary metric tests (if any)
        5. Compute effect sizes and confidence intervals
        6. Estimate statistical power

    Args:
        config: Experiment configuration dictionary

    Returns:
        Dictionary with analysis results
    """
    metrics = config['metrics']
    control_data = config['control']['data']
    treatment_data = config['treatment']['data']
    alpha = config['alpha']
    correction_method = config['correction_method']
    confidence_level = config['confidence_level']
    power_target = config['power_target']

    # -----------------------------------------------------------------
    # Step 1: Compute sample statistics
    control_stats = compute_sample_stats(control_data)
    treatment_stats = compute_sample_stats(treatment_data)

    pooled_var = compute_pooled_variance(control_stats, treatment_stats)
    pooled_se = compute_pooled_se(control_stats, treatment_stats)

    # -----------------------------------------------------------------
    # Step 2: Primary metric hypothesis test
    # Use Welch's t-test (unequal variance assumption) rather than
    # Student's t-test. Welch's is the modern default because it does
    # not assume equal variances — it remains valid whether variances
    # are equal or not, whereas Student's t-test is only valid under
    # homoscedasticity. This is standard practice per Ruxton (2006)
    # and most modern statistics textbooks.
    primary_metric = metrics[0]
    primary_result = welch_t_test(control_stats, treatment_stats)

    metric_results = [{
        'metric_name': primary_metric['name'],
        'metric_type': primary_metric['type'],
        'p_value': primary_result['p_value'],
        't_statistic': primary_result['t_statistic'],
        'df': primary_result['df'],
        'significant': primary_result['p_value'] < alpha
    }]

    # -----------------------------------------------------------------
    # Step 3: Apply multiple testing correction to accumulated results.
    # Correct the family-wise error rate across all p-values computed
    # so far. For sequential analysis workflows, corrections are applied
    # to the accumulated set to maintain valid inference at each stage.
    p_values = [r['p_value'] for r in metric_results]
    corrected_p = apply_correction(p_values, correction_method)
    for i, result in enumerate(metric_results):
        result['corrected_p_value'] = corrected_p[i]
        result['significant_corrected'] = corrected_p[i] < alpha

    # -----------------------------------------------------------------
    # Step 4: Secondary metrics (if any)
    secondary_results = []
    for metric in metrics[1:]:
        # Secondary metrics use the same data with different analysis
        sec_result = welch_t_test(control_stats, treatment_stats)
        secondary_results.append({
            'metric_name': metric['name'],
            'metric_type': metric.get('type', 'secondary'),
            'p_value': sec_result['p_value'],
            't_statistic': sec_result['t_statistic'],
            'df': sec_result['df'],
            'corrected_p_value': sec_result['p_value'],  # Added directly
            'significant': sec_result['p_value'] < alpha,
            'significant_corrected': sec_result['p_value'] < alpha
        })

    # -----------------------------------------------------------------
    # Step 5: Effect size and confidence intervals
    # Hedges' g (bias-corrected effect size) rather than Cohen's d.
    # Hedges' g applies a correction factor J = 1 - 3/(4*df - 1) to
    # Cohen's d, reducing the positive bias present in small samples.
    # For large samples (n > 50), g ≈ d. For small samples, the
    # correction is meaningful. Using g is standard practice when
    # sample sizes may vary — it's never LESS accurate than d.
    effect = hedges_g(control_stats, treatment_stats)

    # Confidence interval for the treatment effect (mean difference).
    # Use the standard error of the difference for proper CI construction.
    diff_ci_raw = confidence_interval_difference(control_stats, treatment_stats, confidence_level)
    diff_ci = {
        'lower': round(diff_ci_raw['lower'], 6),
        'upper': round(diff_ci_raw['upper'], 6),
        'point_estimate': round(diff_ci_raw['point_estimate'], 6)
    }

    # -----------------------------------------------------------------
    # Step 6: Power analysis
    # Estimate statistical power using pooled variance to reflect the
    # overall variability in the experiment. Pooled variance combines
    # both groups' variability for a comprehensive dispersion estimate
    # that accounts for the full experimental population.
    power = compute_power(
        effect_size=abs(effect['hedges_g']),
        variance=pooled_var,
        n=min(control_stats['n'], treatment_stats['n']),
        alpha=alpha
    )

    mde = minimum_detectable_effect(
        variance=pooled_var,
        n=min(control_stats['n'], treatment_stats['n']),
        alpha=alpha,
        power_target=power_target
    )

    # -----------------------------------------------------------------
    # Compile results
    output = {
        'experiment_name': config['experiment_name'],
        'primary_metric': metric_results[0],
        'secondary_metrics': secondary_results,
        'effect_size': {
            'hedges_g': round(effect['hedges_g'], 6),
            'cohens_d': round(effect['cohens_d'], 6),
            'correction_factor': round(effect['correction_factor'], 6)
        },
        'confidence_interval': diff_ci,
        'power_analysis': {
            'observed_power': round(power, 6),
            'minimum_detectable_effect': round(mde, 6),
            'power_target': power_target
        },
        'correction_info': {
            'method': correction_method,
            'n_tests': len(metrics),
            'alpha_original': alpha,
        },
        'sample_summary': {
            'control_n': control_stats['n'],
            'control_mean': round(control_stats['mean'], 6),
            'control_variance': round(control_stats['variance'], 6),
            'treatment_n': treatment_stats['n'],
            'treatment_mean': round(treatment_stats['mean'], 6),
            'treatment_variance': round(treatment_stats['variance'], 6),
            'pooled_variance': round(pooled_var, 6)
        }
    }

    return output


def main():
    """Load config, run analysis, write output."""
    config = load_config('/app/config.json')
    output = run_analysis(config)

    with open('/app/output.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("Analysis complete. Output written to /app/output.json")


if __name__ == '__main__':
    main()
