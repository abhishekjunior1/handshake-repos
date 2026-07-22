A digital signal processing pipeline at `/app/pipeline.py` performs Welch-method spectral analysis on sampled signals. It uses modules `/app/signal_loader.py`, `/app/windowing.py`, `/app/spectral.py`, `/app/filtering.py`, `/app/snr.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/signal_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current signal data but has bugs that cause incorrect results on other input configurations. Find and fix the bugs so the pipeline handles all valid inputs correctly.

The input contains a time-domain signal, sampling rate, and configuration specifying window type, segment length, overlap ratio, filter parameters, noise estimation method, and signal band. The pipeline segments the signal with overlap, applies windowing per segment, computes per-segment PSD, averages them (Welch's method), designs and applies a Butterworth filter, estimates noise floor, computes SNR, and extracts spectral features.

Do not rewrite from scratch — preserve the existing module structure, the one-sided PSD doubling convention, the bilinear pre-warping in filter design, the coherent gain amplitude correction for power measurement, and the overlap-dependent processing gain normalization. The fixed pipeline will be tested on a different signal configuration than the one at `/app/signal_data.json`.

Output: `/app/output.json` — JSON with sections: `analysis_parameters` (config echo), `spectral_analysis` (total_power, peak_frequency, peak_power, spectral_centroid, spectral_bandwidth, spectral_flatness), `signal_quality` (snr_db, signal_power, noise_power, band_power, effective_band_power), `filter_characteristics` (passband_ripple_db, stopband_attenuation_db, bandwidth_3db, max_gain_db), and `segment_info` (n_segments, segment_length, overlap_ratio, window_coherent_gain, total_signal_length).
