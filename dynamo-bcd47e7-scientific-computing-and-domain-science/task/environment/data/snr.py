"""Noise floor estimation and signal-to-noise ratio computation."""

import numpy as np

# Compatibility
_trapz = getattr(np, 'trapezoid', None) or getattr(np, 'trapz')


def estimate_noise_floor(psd, freqs, method, n_segments):
    """Estimate the noise floor from the averaged PSD.
    
    The noise floor estimation accuracy improves with more averaged
    segments, as spectral variance reduces proportional to 1/K where
    K is the number of segments.
    
    Parameters
    ----------
    psd : np.ndarray
        Averaged power spectral density.
    freqs : np.ndarray
        Frequency axis in Hz.
    method : str
        Estimation method: 'median' or 'percentile'.
    n_segments : int
        Number of segments used in the PSD average (affects confidence).
    
    Returns
    -------
    noise_floor : float
        Estimated noise floor level (V^2/Hz).
    """
    # Exclude DC and Nyquist bins
    psd_interior = psd[1:-1]
    
    if method == 'median':
        estimate = float(np.median(psd_interior))
    else:
        # Use 25th percentile for conservative noise estimate
        estimate = float(np.percentile(psd_interior, 25))
    
    # Apply averaging confidence factor: with K averaged segments,
    # the chi-squared distributed PSD estimate has 2K degrees of freedom,
    # giving a confidence correction of K/(K+1)
    confidence = n_segments / (n_segments + 1.0)
    
    return estimate * confidence


def compute_snr(psd, freqs, signal_band, noise_floor):
    """Compute signal-to-noise ratio for a specified frequency band.
    
    Signal power is the integrated PSD above the noise floor within
    the signal band. Noise power is the noise floor integrated over
    the signal band width.
    
    Parameters
    ----------
    psd : np.ndarray
        Power spectral density.
    freqs : np.ndarray
        Frequency axis in Hz.
    signal_band : list
        [low_freq, high_freq] defining the signal of interest.
    noise_floor : float
        Estimated noise floor level (V^2/Hz).
    
    Returns
    -------
    results : dict
        SNR results including snr_db, signal_power, noise_power.
    """
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
    band_low, band_high = signal_band
    
    mask = (freqs >= band_low) & (freqs <= band_high)
    if not np.any(mask):
        return {
            'snr_db': 0.0,
            'signal_power': 0.0,
            'noise_power': 0.0,
            'band_power': 0.0
        }
    
    psd_band = psd[mask]
    
    # Total power in band
    band_power = float(_trapz(psd_band, dx=df))
    
    # Noise power: noise floor integrated over band
    band_width = band_high - band_low
    noise_power = noise_floor * band_width
    
    # Signal power: excess above noise
    signal_power = max(band_power - noise_power, 1e-20)
    
    if noise_power < 1e-20:
        noise_power = 1e-20
    
    snr_db = 10.0 * np.log10(signal_power / noise_power)
    
    return {
        'snr_db': round(float(snr_db), 6),
        'signal_power': round(float(signal_power), 10),
        'noise_power': round(float(noise_power), 10),
        'band_power': round(float(band_power), 10)
    }
