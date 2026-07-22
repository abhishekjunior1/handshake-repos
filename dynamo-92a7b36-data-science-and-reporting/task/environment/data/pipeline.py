"""Meta-analysis pipeline entry point.

Orchestrates the complete random-effects meta-analysis workflow:
1. Load and validate study-level data
2. Compute heterogeneity statistics
3. Estimate random-effects pooled effects
4. Run publication bias diagnostics
5. Perform subgroup analyses
6. Generate structured JSON output

Usage:
    python pipeline.py [--input PATH] [--output PATH]
"""

import argparse
import json
import os
import sys
from typing import Any

from data_loader import load_meta_data
from heterogeneity import estimate_heterogeneity
from random_effects import run_random_effects_analysis
from egger_test import run_egger_test
from report_generator import generate_report, write_report


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the pipeline.

    Returns:
        Namespace with input and output file paths.
    """
    parser = argparse.ArgumentParser(
        description="Random-effects meta-analysis pipeline"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="/app/meta_data.json",
        help="Path to input JSON data file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/app/output.json",
        help="Path for output JSON report",
    )
    return parser.parse_args()


def validate_environment(input_path: str) -> None:
    """Validate that required files and environment are available.

    Args:
        input_path: Path to the input data file.

    Raises:
        SystemExit: If critical requirements are not met.
    """
    if not os.path.isfile(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)


def log_analysis_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary of the analysis to stdout.

    Args:
        report: Complete analysis report dictionary.
    """
    print("=" * 60)
    print(f"Meta-Analysis: {report['analysis_name']}")
    print(f"Effect Measure: {report['effect_measure']}")
    print(f"Number of Studies: {report['num_studies']}")
    print("=" * 60)

    overall = report["overall_analysis"]
    re = overall["random_effects"]
    fe = overall["fixed_effect"]
    het = overall["heterogeneity"]

    print("\n--- Fixed-Effect Model ---")
    print(f"  Pooled Estimate: {fe['pooled_estimate']:.4f}")
    print(f"  95% CI: [{fe['ci_lower']:.4f}, {fe['ci_upper']:.4f}]")

    print("\n--- Random-Effects Model ---")
    print(f"  Pooled Estimate: {re['pooled_estimate']:.4f}")
    print(f"  95% CI: [{re['ci_lower']:.4f}, {re['ci_upper']:.4f}]")
    print(f"  95% PI: [{re['prediction_interval_lower']:.4f}, {re['prediction_interval_upper']:.4f}]")

    print("\n--- Heterogeneity ---")
    print(f"  Q({het['df']}) = {het['Q']:.4f}, p = {het['p_value']:.4f}")
    print(f"  I² = {het['I_squared']:.2f}%")
    print(f"  tau² = {het['tau_squared']:.6f}")

    pub_bias = report["publication_bias"]
    print("\n--- Publication Bias (Egger's Test) ---")
    print(f"  Intercept: {pub_bias['intercept']:.4f} (p = {pub_bias['p_intercept']:.4f})")
    print(f"  Bias Detected: {'Yes' if pub_bias['bias_detected'] else 'No'}")

    print("\n--- Subgroup Analyses ---")
    for sg in report["subgroup_analyses"]:
        print(f"  [{sg['subgroup']}] k={sg['num_studies']}", end="")
        if sg["analysis"] is not None:
            sg_re = sg["analysis"]["random_effects"]
            print(f"  Pooled: {sg_re['pooled_estimate']:.4f} "
                  f"[{sg_re['ci_lower']:.4f}, {sg_re['ci_upper']:.4f}]")
        else:
            print(f"  {sg.get('note', 'N/A')}")

    print("\n" + "=" * 60)


def run_pipeline(input_path: str, output_path: str) -> dict[str, Any]:
    """Execute the complete meta-analysis pipeline.

    Args:
        input_path: Path to input JSON data.
        output_path: Path for output JSON report.

    Returns:
        Complete analysis report dictionary.
    """
    validate_environment(input_path)
    data = load_meta_data(input_path)
    report = generate_report(data)
    write_report(report, output_path)
    log_analysis_summary(report)
    print(f"\nReport written to: {output_path}")
    return report


def main() -> None:
    """Main entry point for the meta-analysis pipeline."""
    args = parse_arguments()
    try:
        run_pipeline(args.input, args.output)
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
