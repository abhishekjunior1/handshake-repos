"""PLC Historian Calibration Module.

Applies engineering unit calibration to raw sensor readings from
PLC data historians. Converts raw ADC count values to physical
engineering units using configured calibration parameters.

Calibration Model:
    The standard calibration model uses a polynomial transformation:
    
        eng_value = c[0]*x^n + c[1]*x^(n-1) + ... + c[n-1]*x + c[n]
    
    Where x is the RAW ADC COUNT (integer, typically 0-65535 for 16-bit)
    and c[] are the polynomial coefficients in descending order.

    Common configurations:
    - Linear: [gain, offset] → eng = gain * raw + offset
    - Quadratic: [a, b, c] → eng = a*raw² + b*raw + c

    The input to calibration is ALWAYS the raw ADC integer count,
    NOT a pre-scaled or normalized value. The polynomial coefficients
    are computed during instrument calibration to map the specific
    sensor's raw digital output to engineering units.
"""

from typing import List, Dict, Any


def apply_polynomial(raw_count: int, coefficients: List[float]) -> float:
    """Apply polynomial calibration to a raw ADC count.

    Evaluates the polynomial at the given raw integer count value.
    Uses Horner's method for numerical stability.

    Args:
        raw_count: Raw ADC value (integer, 0-65535 typical).
        coefficients: Polynomial coefficients in descending power order.
                      e.g., [a, b, c] for a*x² + b*x + c

    Returns:
        Engineering unit value (float).
    """
    if not coefficients:
        return float(raw_count)

    result = coefficients[0]
    for coeff in coefficients[1:]:
        result = result * raw_count + coeff

    return result


def calibrate_sample(raw_count: int, cal_config: Dict[str, Any]) -> float:
    """Calibrate a single raw ADC reading using the tag's cal config.

    Dispatches to the appropriate calibration function based on the
    configured calibration type.

    Args:
        raw_count: Raw ADC count value (integer).
        cal_config: Calibration configuration dictionary containing:
            - type: 'polynomial' or 'linear'
            - coefficients: Polynomial coefficients (for 'polynomial')
            - gain: Scale factor (for 'linear')
            - offset: Zero offset (for 'linear')

    Returns:
        Calibrated engineering unit value.
    """
    cal_type = cal_config.get('type', 'linear')

    if cal_type == 'polynomial':
        coefficients = cal_config.get('coefficients', [1.0, 0.0])
        return apply_polynomial(raw_count, coefficients)
    else:
        gain = cal_config.get('gain', 1.0)
        offset = cal_config.get('offset', 0.0)
        return gain * raw_count + offset


def calibrate_batch(samples: List[Dict[str, Any]],
                    cal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply calibration to a batch of samples.

    Reads 'raw_value' from each sample and writes 'value' with
    the calibrated engineering unit result.

    Args:
        samples: List of sample dicts with 'raw_value' field.
        cal_config: Calibration configuration for this tag.

    Returns:
        Samples with 'value' field added (engineering units).
    """
    for sample in samples:
        raw = sample.get('raw_value', 0)
        sample['value'] = round(calibrate_sample(raw, cal_config), 6)

    return samples
