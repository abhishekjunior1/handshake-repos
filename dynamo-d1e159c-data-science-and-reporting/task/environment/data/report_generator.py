"""Report Generator for the EDA pipeline.

Produces structured JSON output with the complete EDA report.
"""

import json
from typing import Dict, List, Any


def generate_report(univariate: Dict[str, Any],
                    outliers: Dict[str, Any],
                    correlations: Dict[str, Any],
                    group_analysis: Dict[str, Any],
                    metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the structured EDA report.

    Args:
        univariate: Per-column descriptive statistics.
        outliers: Outlier detection results.
        correlations: Correlation matrices.
        group_analysis: Group-wise aggregation results.
        metadata: Pipeline configuration and dataset info.

    Returns:
        Complete report dictionary.
    """
    report = {
        'univariate_statistics': univariate,
        'outlier_detection': outliers,
        'correlations': correlations,
        'group_analysis': group_analysis,
        'metadata': metadata
    }
    return report


def write_report(report: Dict[str, Any], output_path: str) -> None:
    """Write report to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write('\n')
