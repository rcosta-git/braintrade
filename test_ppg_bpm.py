import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks

def estimate_bpm_from_ppg(ppg_signal, sampling_rate):
    """Estimates BPM from PPG signal using SciPy."""
    if len(ppg_signal) == 0:
        return np.nan

    # 1. Bandpass filter (example: 0.5 - 4 Hz for typical HR range)
    lowcut = 0.5
    highcut = 4.0
    nyquist_rate = sampling_rate / 2.0
    low = lowcut / nyquist_rate
    high = highcut / nyquist_rate
    b, a = butter(3, [low, high], btype='band')
    ppg_filtered = filtfilt(b, a, ppg_signal)

    # 2. Peak detection (adjust parameters as needed)
    peaks, _ = find_peaks(ppg_filtered, height=np.std(ppg_filtered) * 0.5, distance=int(sampling_rate / 5)) # Example: min peak height 0.5 * signal_std, min distance ~120 BPM max HR

    if len(peaks) < 2: # Need at least 2 peaks to calculate IBI
        return np.nan

    # 3. Calculate Inter-Beat Intervals (IBIs) in seconds
    peak_times = peaks / sampling_rate
    ibis = np.diff(peak_times)

    # 4. Convert IBIs to BPM (beats per minute)
    if len(ibis) == 0:
        return np.nan
    bpm = 60.0 / np.mean(ibis)
    return bpm, peaks, ppg_filtered

if __name__ == "__main__":
    # --- Generate Sample PPG Data (Replace with real data or loading later) ---
    fs = 64.0  # Sample rate (Hz) - typical for Muse PPG
    duration = 10  # seconds
    t = np.arange(0, duration, 1/fs)
    heart_rate_bpm = 70.0 # Simulate HR around 70 BPM
    heart_period_samples = int(fs * 60.0 / heart_rate_bpm)
    # Create a pulse-like signal (simplified PPG)
    pulse = np.zeros(len(t))
    peak_indices = np.arange(heart_period_samples/2, len(t), heart_period_samples) # Roughly every period
    pulse[peak_indices.astype(int)] = 1.0
    ppg_signal_clean = np.sin(2*np.pi * 1.1 * t) + pulse # Add some lower freq component + pulses
    noise = np.random.normal(0, 0.2, len(t)) # Add some noise
    ppg_signal = ppg_signal_clean + noise


    # --- Estimate BPM ---
    bpm_estimated, peaks, ppg_filtered = estimate_bpm_from_ppg(ppg_signal, fs)

    # --- Plotting for Visual Check ---
    plt.figure(figsize=(10, 6))
    plt.plot(t, ppg_signal, label='Raw PPG')
    plt.plot(t, ppg_filtered, label='Filtered PPG', alpha=0.7)
    plt.plot(peaks / fs, ppg_filtered[peaks], "x", color='red', label='Detected Peaks')
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(f"PPG Signal with Peak Detection - Estimated BPM: {bpm_estimated:.2f}")
    plt.legend()
    plt.grid(True)
    plt.show()

    print(f"Estimated BPM: {bpm_estimated:.2f}")