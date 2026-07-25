"""Digital filter design and application."""

import numpy as np


def design_filter(filter_type, order, cutoff_low, cutoff_high, sampling_rate):
    """Design an IIR Butterworth filter using bilinear transform with pre-warping."""
    wc_low = 2.0 * sampling_rate * np.tan(np.pi * cutoff_low / sampling_rate)
    
    if filter_type == 'bandpass':
        wc_high = 2.0 * sampling_rate * np.tan(np.pi * cutoff_high / sampling_rate)
        b, a = _butterworth_bandpass(order, wc_low, wc_high, sampling_rate)
    else:
        b, a = _butterworth_lowpass(order, wc_low, sampling_rate)
    
    return b, a


def apply_filtfilt(signal, b, a):
    """Apply zero-phase forward-backward filtering."""
    forward = _apply_filter_forward(signal, b, a)
    backward = _apply_filter_forward(forward[::-1], b, a)
    return backward[::-1]


def compute_filter_response(b, a, sampling_rate, n_points=512):
    """Compute frequency response characteristics."""
    eval_freqs = np.linspace(0, sampling_rate / 2, n_points)
    
    h_mag = np.zeros(n_points)
    for i, f in enumerate(eval_freqs):
        w = 2.0 * np.pi * f / sampling_rate
        z = np.exp(1j * w)
        num = sum(b[k] * z**(-k) for k in range(len(b)))
        den = sum(a[k] * z**(-k) for k in range(len(a)))
        h_mag[i] = abs(num / den) if abs(den) > 1e-15 else 0.0
    
    h_db = 20.0 * np.log10(np.maximum(h_mag, 1e-15))
    
    passband_mask = h_db > -3.0
    passband_ripple = float(np.max(h_db[passband_mask]) - np.min(h_db[passband_mask])) if np.any(passband_mask) else 0.0
    
    stopband_mask = h_db < -3.0
    stopband_attenuation = float(-np.min(h_db[stopband_mask])) if np.any(stopband_mask) else 0.0
    
    above_3db = np.where(h_db >= -3.0)[0]
    bandwidth_3db = float(eval_freqs[above_3db[-1]] - eval_freqs[above_3db[0]]) if len(above_3db) > 0 else 0.0
    
    return {
        'passband_ripple_db': round(passband_ripple, 6),
        'stopband_attenuation_db': round(stopband_attenuation, 6),
        'bandwidth_3db': round(bandwidth_3db, 4),
        'max_gain_db': round(float(np.max(h_db)), 6)
    }


def _apply_filter_forward(signal, b, a):
    """Direct Form II transposed IIR filter (forward only)."""
    n = len(signal)
    nfilt = max(len(b), len(a))
    
    b_padded = np.zeros(nfilt)
    a_padded = np.zeros(nfilt)
    b_padded[:len(b)] = b
    a_padded[:len(a)] = a
    
    if a_padded[0] != 1.0:
        b_padded = b_padded / a_padded[0]
        a_padded = a_padded / a_padded[0]
    
    state = np.zeros(nfilt - 1)
    filtered = np.zeros(n)
    
    for i in range(n):
        filtered[i] = b_padded[0] * signal[i] + state[0]
        for j in range(nfilt - 2):
            state[j] = b_padded[j + 1] * signal[i] - a_padded[j + 1] * filtered[i] + state[j + 1]
        state[nfilt - 2] = b_padded[nfilt - 1] * signal[i] - a_padded[nfilt - 1] * filtered[i]
    
    return filtered


def _butterworth_lowpass(order, wc, sampling_rate):
    """Design Butterworth lowpass via bilinear transform."""
    poles = []
    for k in range(order):
        theta = np.pi * (2 * k + order + 1) / (2 * order)
        poles.append(wc * np.exp(1j * theta))
    
    T = 1.0 / sampling_rate
    digital_poles = [(1.0 + p * T / 2.0) / (1.0 - p * T / 2.0) for p in poles]
    digital_zeros = -np.ones(order)
    
    b, a = _zpk_to_tf(digital_zeros, np.array(digital_poles), 1.0)
    dc_gain = np.sum(b) / np.sum(a)
    b = b / dc_gain
    
    return np.real(b), np.real(a)


def _butterworth_bandpass(order, wc_low, wc_high, sampling_rate):
    """Design Butterworth bandpass via bilinear transform."""
    w0 = np.sqrt(wc_low * wc_high)
    bw = wc_high - wc_low
    
    lp_poles = [np.exp(1j * np.pi * (2 * k + order + 1) / (2 * order)) for k in range(order)]
    
    bp_poles = []
    for p in lp_poles:
        sp = bw * p / 2.0
        bp_poles.append(sp + np.sqrt(sp**2 - w0**2 + 0j))
        bp_poles.append(sp - np.sqrt(sp**2 - w0**2 + 0j))
    
    T = 1.0 / sampling_rate
    digital_poles = [(1.0 + p * T / 2.0) / (1.0 - p * T / 2.0) for p in bp_poles]
    digital_zeros = np.concatenate([np.ones(order), -np.ones(order)])
    
    b, a = _zpk_to_tf(digital_zeros, np.array(digital_poles), 1.0)
    
    w_center = 2 * np.pi * np.sqrt(wc_low * wc_high) / (2.0 * sampling_rate)
    z_center = np.exp(1j * w_center)
    gain = np.abs(np.polyval(b, z_center) / np.polyval(a, z_center))
    if gain > 0:
        b = b / gain
    
    return np.real(b), np.real(a)


def _zpk_to_tf(zeros, poles, gain):
    """Convert zeros-poles-gain to transfer function coefficients."""
    b = gain * np.real(np.poly(zeros))
    a = np.real(np.poly(poles))
    return b, a
