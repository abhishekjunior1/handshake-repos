"""Report generation for DSP pipeline analysis results."""

import json
import numpy as np


def generate_report(spectral_features, snr_results, filter_response, segment_info, config):
    """Generate structured JSON analysis report."""
    report = {
        'analysis_parameters': {
            'window_type': config['window_type'],
            'segment_length': config['segment_length'],
            'overlap_ratio': config['overlap_ratio'],
            'filter_type': config['filter_type'],
            'filter_order': config['filter_order'],
            'cutoff_low': config['cutoff_low'],
            'cutoff_high': config.get('cutoff_high', None),
            'signal_band': config.get('signal_band', None)
        },
        'spectral_analysis': spectral_features,
        'signal_quality': snr_results,
        'filter_characteristics': filter_response,
        'segment_info': segment_info
    }
    return report


def save_report(report, filepath):
    """Save analysis report to JSON file."""
    def numpy_encoder(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Not serializable: {type(obj)}")
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=numpy_encoder)
