"""Spectral analysis: FFT, PSD computation, and Welch averaging."""

import numpy as np

# Compatibility: np.trapezoid (numpy>=2.0) vs np.trapz (numpy<2.0)
_trapz = getattr(np, 'trapezoid', None) or getattr(np, 'trapz')


def compute_segment_psd(segment, window, sampling_rate):
    """Compute one-sided PSD for a single windowed segment.
    
    Parameters
    ----------
    segment : np.ndarray
        Time-domain signal segment (already windowed).
    window : np.ndarray
        Window function used (for normalization).
    sampling_rate : float
        Sampling rate in Hz.
    
    Returns
    -------
    freqs : np.ndarray
        One-sided frequency axis.
    psd : np.ndarray
        One-sided power spectral density (V^2/Hz).
    """
    n = len(segment)
    fft_vals = np.fft.fft(segment)
    
    n_onesided = n // 2 + 1
    spectrum = fft_vals[:n_onesided]
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate)
    
    # Window energy normalization
    window_energy = np.sum(window**2)
    
    # Power spectrum
    power = np.abs(spectrum)**2
    psd = power / (sampling_rate * window_energy)
    
    # One-sided doubling (accounts for negative frequency energy
    # in real-valued signals where X[-f] = conj(X[f]))
    psd[1:-1] *= 2.0
    
    return freqs, psd


def average_psd(psd_segments):
    """Average multiple PSD estimates (Welch's method).
    
    Parameters
    ----------
    psd_segments : list of np.ndarray
        Individual segment PSD estimates.
    
    Returns
    -------
    psd_avg : np.ndarray
        Averaged PSD estimate.
    """
    return np.mean(psd_segments, axis=0)


def compute_spectral_features(freqs, psd):
    """Extract standard spectral features from PSD.
    
    Parameters
    ----------
    freqs : np.ndarray
        Frequency axis in Hz.
    psd : np.ndarray
        Power spectral density.
    
    Returns
    -------
    features : dict
        Spectral descriptors.
    """
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
    total_power = float(_trapz(psd, dx=df))
    
    if total_power > 0:
        centroid = float(_trapz(freqs * psd, dx=df) / total_power)
        variance = float(_trapz((freqs - centroid)**2 * psd, dx=df) / total_power)
        bandwidth = float(np.sqrt(variance))
    else:
        centroid = 0.0
        bandwidth = 0.0
    
    peak_idx = np.argmax(psd)
    peak_frequency = float(freqs[peak_idx])
    peak_power = float(psd[peak_idx])
    
    # Spectral flatness (geometric mean / arithmetic mean in dB)
    psd_pos = psd[psd > 0]
    if len(psd_pos) > 0:
        log_mean = np.mean(np.log(psd_pos))
        geo_mean = np.exp(log_mean)
        arith_mean = np.mean(psd_pos)
        flatness = float(geo_mean / arith_mean) if arith_mean > 0 else 0.0
    else:
        flatness = 0.0
    
    return {
        'total_power': round(total_power, 10),
        'peak_frequency': round(peak_frequency, 6),
        'peak_power': round(peak_power, 10),
        'spectral_centroid': round(centroid, 6),
        'spectral_bandwidth': round(bandwidth, 6),
        'spectral_flatness': round(flatness, 8)
    }


def compute_band_power(freqs, psd, band_low, band_high):
    """Integrate PSD over a frequency band.
    
    Parameters
    ----------
    freqs : np.ndarray
        Frequency axis.
    psd : np.ndarray
        Power spectral density.
    band_low, band_high : float
        Band boundaries in Hz.
    
    Returns
    -------
    power : float
        Integrated power in the band.
    """
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
    mask = (freqs >= band_low) & (freqs <= band_high)
    if np.any(mask):
        return float(_trapz(psd[mask], dx=df))
    return 0.0
