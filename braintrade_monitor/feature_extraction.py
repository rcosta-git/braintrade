import numpy as np
import mne
import logging
from scipy.signal import butter, filtfilt, find_peaks
from scipy.integrate import trapezoid
from mne.time_frequency import psd_array_welch

# Import constants from the config module within the same package
from . import config

def estimate_bpm_from_ppg(ppg_signal, sampling_rate):
    """Estimates BPM from PPG signal using SciPy."""
    if ppg_signal is None or len(ppg_signal) < sampling_rate * 2: # Need at least a few seconds of data
        # logging.warning("Not enough PPG data to estimate BPM.") # Logged in processing loop
        return np.nan

    # 1. Bandpass filter
    nyquist_rate = sampling_rate / 2.0
    low = config.PPG_FILTER_LOWCUT / nyquist_rate
    high = config.PPG_FILTER_HIGHCUT / nyquist_rate
    try:
        # Ensure high > low after dividing by nyquist_rate
        if high <= low:
             logging.error(f"PPG filter high cut ({config.PPG_FILTER_HIGHCUT} Hz) must be greater than low cut ({config.PPG_FILTER_LOWCUT} Hz).")
             return np.nan
        # Ensure filter order is less than signal length
        filter_order = 3
        if len(ppg_signal) <= filter_order:
             logging.warning(f"PPG signal length ({len(ppg_signal)}) too short for filter order ({filter_order}).")
             return np.nan
        b, a = butter(filter_order, [low, high], btype='band')
        ppg_filtered = filtfilt(b, a, ppg_signal)
    except ValueError as e:
        logging.error(f"Error filtering PPG signal in estimate_bpm_from_ppg: {e}")
        return np.nan

    # 2. Peak detection
    min_distance = int(sampling_rate * config.PPG_PEAK_MIN_DIST_FACTOR)
    # Ensure std dev is not zero before calculating height
    ppg_std = np.std(ppg_filtered)
    if ppg_std < config.EPSILON: # Check against epsilon
        # logging.warning("PPG signal standard deviation is near zero, cannot reliably detect peaks.")
        return np.nan
    min_height = ppg_std * config.PPG_PEAK_HEIGHT_FACTOR

    try:
        # Ensure signal is long enough for peak finding distance
        if len(ppg_filtered) < min_distance:
             logging.warning(f"PPG signal length ({len(ppg_filtered)}) too short for peak distance ({min_distance}).")
             return np.nan
        peaks, _ = find_peaks(ppg_filtered, height=min_height, distance=min_distance)
    except ValueError as e:
        logging.error(f"Error finding PPG peaks in estimate_bpm_from_ppg: {e}")
        return np.nan

    if len(peaks) < 2:
        # logging.warning("Not enough peaks found in PPG signal to estimate BPM.")
        return np.nan

    # 3. Calculate Inter-Beat Intervals (IBIs) in seconds
    peak_times = peaks / sampling_rate
    ibis = np.diff(peak_times)

    # Filter unrealistic IBIs (IBIs) - physiological limits
    valid_ibis = ibis[(ibis > 0.3) & (ibis < 2.0)]

    # 4. Convert IBIs to BPM
    if len(valid_ibis) == 0:
        # logging.warning("No valid IBIs found after filtering.")
        return np.nan
    mean_ibi = np.mean(valid_ibis)
    if mean_ibi < config.EPSILON:
        # logging.warning("Mean IBI is near zero, cannot calculate BPM.")
        return np.nan
    bpm = 60.0 / mean_ibi
    return bpm

def extract_alpha_beta_ratio(eeg_data, sampling_rate):
    """Calculates Alpha/Beta ratio from EEG data."""
    if eeg_data is None:
        return np.nan

    bands = {'Alpha': config.ALPHA_BAND, 'Beta': config.BETA_BAND}
    # Expecting numpy array already
    if not isinstance(eeg_data, np.ndarray) or eeg_data.ndim != 2:
         logging.error(f"Invalid EEG data format: Expected 2D numpy array, got {type(eeg_data)}")
         return np.nan

    n_channels, n_times = eeg_data.shape

    if n_channels != config.NUM_EEG_CHANNELS:
         logging.warning(f"EEG data has {n_channels} channels, expected {config.NUM_EEG_CHANNELS}. Check data source.")
         # Proceeding, but this might indicate an issue.

    if n_times < config.EEG_NFFT: # Check if signal is long enough for FFT
        # logging.warning(f"EEG segment too short ({n_times} samples) for FFT (needs {config.EEG_NFFT}), skipping ratio calculation.")
        return np.nan

    # Filter EEG data first
    try:
        iir_params = dict(order=4, ftype='butter')
        # MNE's filter_data handles padding and potential issues internally
        eeg_filtered = mne.filter.filter_data(eeg_data, sfreq=sampling_rate,
                                              l_freq=config.EEG_FILTER_LOWCUT, h_freq=config.EEG_FILTER_HIGHCUT,
                                              method='iir', iir_params=iir_params, verbose=False,
                                              pad='reflect_limited', # Common padding method
                                              picks=None # Default: filter all channels in the array
                                              )
    except ValueError as e:
        # This might catch cases where filtering is impossible (e.g., all NaN data)
        logging.error(f"Error filtering EEG data in extract_alpha_beta_ratio: {e}")
        return np.nan

    band_powers = {}
    for band_name, (fmin, fmax) in bands.items():
        band_powers[band_name] = np.zeros(n_channels)

    for j in range(n_channels):
        channel_data = eeg_filtered[j, :]
        n_times_ch = len(channel_data)
        # Ensure n_fft is not greater than the channel data length after potential filtering artifacts
        n_fft = min(n_times_ch, config.EEG_NFFT)
        if n_fft == 0:
            # logging.warning(f"Warning: Empty EEG segment for channel {j} after filtering, skipping.")
            band_powers['Alpha'][j] = np.nan # Ensure NaN if skipped
            band_powers['Beta'][j] = np.nan
            continue # Skip this channel if empty

        try:
            # Ensure n_per_seg is not greater than channel data length
            n_per_seg = min(n_fft, n_times_ch)
            if n_per_seg == 0: # Double check after min()
                 band_powers['Alpha'][j] = np.nan
                 band_powers['Beta'][j] = np.nan
                 continue

            psd, freqs = psd_array_welch(channel_data, sfreq=sampling_rate,
                                         fmin=config.EEG_FILTER_LOWCUT, # Calculate PSD over full filtered range
                                         fmax=config.EEG_FILTER_HIGHCUT,
                                         n_fft=n_fft, n_per_seg=n_per_seg, verbose=False,
                                         average='mean', # Explicitly average Welch segments
                                         )
            # Calculate power per band using trapezoidal integration
            for band_name, (fmin, fmax) in bands.items():
                 freq_res = freqs[1] - freqs[0] # Frequency resolution
                 idx_band = np.logical_and(freqs >= fmin, freqs <= fmax)
                 if np.sum(idx_band) > 0:
                     # Integrate PSD over the band frequencies
                     band_powers[band_name][j] = trapezoid(psd[idx_band], dx=freq_res)
                 else:
                     band_powers[band_name][j] = 0 # Assign 0 if no components in band
                     # logging.warning(f"No PSD components found for band {band_name} in channel {j}.")

        except ValueError as e:
            logging.error(f"Error calculating PSD for channel {j} in extract_alpha_beta_ratio: {e}")
            # Assign NaN if PSD fails for a channel
            for band_name in bands:
                band_powers[band_name][j] = np.nan

    # Average power across channels, handle potential NaNs
    # Use nanmean which ignores NaNs
    alpha_power = np.nanmean(band_powers['Alpha'])
    beta_power = np.nanmean(band_powers['Beta'])

    # Check for invalid results after averaging
    if np.isnan(alpha_power) or np.isnan(beta_power) or beta_power < config.EPSILON:
        # logging.warning(f"Warning: Invalid average alpha ({alpha_power}) or beta ({beta_power}) power, returning NaN")
        return np.nan

    alpha_beta_ratio = alpha_power / beta_power
    return alpha_beta_ratio