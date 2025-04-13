import time
import numpy as np
import logging

from . import config
from . import data_store
from . import feature_extraction

def calculate_baseline(duration_seconds):
    """
    Collects data for a specified duration, calculates baseline feature statistics
    (median and std dev for HR and Alpha/Beta Ratio), and stores them in the data_store.

    Args:
        duration_seconds (int): The duration in seconds to collect baseline data.

    Returns:
        bool: True if baseline calculation was successful, False otherwise.
    """
    logging.info(f"Starting baseline calculation for {duration_seconds} seconds... Please relax.")
    baseline_start_time = time.time()

    # Data collection happens passively via the OSC handlers updating the data_store.
    # We just need to wait for the specified duration.
    while time.time() - baseline_start_time < duration_seconds:
        # Log progress periodically
        elapsed = time.time() - baseline_start_time
        logging.info(f"Baseline collection progress: {elapsed:.1f} / {duration_seconds}s")
        # Sleep for a short interval to avoid busy-waiting, but allow interruption
        time.sleep(min(1.0, duration_seconds - elapsed + 0.1)) # Sleep 1s or remaining time

    logging.info("Baseline data collection finished. Processing data...")

    # Retrieve all collected data from the data store
    eeg_baseline_data, ppg_baseline_data, acc_baseline_data = data_store.get_all_data_for_baseline()
    # We ignore acc_baseline_data for now

    # --- Data Validation ---
    min_eeg_samples = int(config.EEG_SAMPLING_RATE * config.EEG_WINDOW_DURATION)
    min_ppg_samples = int(config.PPG_SAMPLING_RATE * config.PPG_WINDOW_DURATION)

    #if eeg_baseline_data.shape[1] < min_eeg_samples:
    #    logging.error(f"Error: Insufficient EEG data collected for baseline. "
    #                  f"Required: {min_eeg_samples}, Collected: {eeg_baseline_data.shape[1]}")
    #    return False
    #if len(ppg_baseline_data) < min_ppg_samples:
    #    logging.error(f"Error: Insufficient PPG data collected for baseline. "
    #                  f"Required: {min_ppg_samples}, Collected: {len(ppg_baseline_data)}")
    #    return False
    
    #if len(acc_baseline_data) < 1:
    #    logging.error(f"Error: Insufficient ACC data collected for baseline.")
    #    return False

    logging.info(f"Processing baseline data. EEG shape: {eeg_baseline_data.shape}, PPG length: {len(ppg_baseline_data)}")

    # --- Feature Calculation over Sliding Windows ---
    ratios = []
    hrs = []
    eeg_window_samples = int(config.EEG_SAMPLING_RATE * config.EEG_WINDOW_DURATION)
    ppg_window_samples = int(config.PPG_SAMPLING_RATE * config.PPG_WINDOW_DURATION)
    # Use a step size related to the update interval for consistency
    step_samples_eeg = int(config.EEG_SAMPLING_RATE * config.UPDATE_INTERVAL)
    step_samples_ppg = int(config.PPG_SAMPLING_RATE * config.UPDATE_INTERVAL)

    logging.info("Calculating baseline stats using sliding windows...")
    # EEG Ratio Calculation
    for i in range(0, eeg_baseline_data.shape[1] - eeg_window_samples + 1, step_samples_eeg):
        eeg_window = eeg_baseline_data[:, i:i+eeg_window_samples]
        # Pass sampling rate directly from config
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_window, config.EEG_SAMPLING_RATE)
        if not np.isnan(ratio):
            ratios.append(ratio)

    # PPG HR Calculation
    for i in range(0, len(ppg_baseline_data) - ppg_window_samples + 1, step_samples_ppg):
        ppg_window = ppg_baseline_data[i:i+ppg_window_samples]
        # Pass sampling rate directly from config
        hr = feature_extraction.estimate_bpm_from_ppg(ppg_window, config.PPG_SAMPLING_RATE)
        if not np.isnan(hr):
            hrs.append(hr)

    # --- Store Results ---
    if not ratios or not hrs:
        logging.error(f"Error: No valid feature samples calculated during baseline processing. "
                      f"Ratios calculated: {len(ratios)}, HRs calculated: {len(hrs)}")
        return False

    calculated_metrics = {
        'ratio_median': np.median(ratios),
        'ratio_std': np.std(ratios),
        'hr_median': np.median(hrs),
        'hr_std': np.std(hrs),
        'movement_median': np.nan, # Placeholder
        'movement_std': np.nan # Placeholder
    }

    data_store.set_baseline_metrics(calculated_metrics)

    logging.info("-" * 30)
    logging.info("Baseline Calculation Complete:")
    logging.info(f"  Baseline A/B Ratio: {calculated_metrics['ratio_median']:.2f} +/- {calculated_metrics['ratio_std']:.2f} ({len(ratios)} samples)")
    logging.info(f"  Baseline HR: {calculated_metrics['hr_median']:.1f} +/- {calculated_metrics['hr_std']:.1f} BPM ({len(hrs)} samples)")
    logging.info("-" * 30)
    return True

if __name__ == '__main__':
    # Example usage/test (requires OSC server running and sending data)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Initialize data store with placeholder sizes
    data_store.initialize_data_store(eeg_buffer_size=20000, ppg_buffer_size=10000, acc_buffer_size=10000)
    print("Starting baseline calculation test (requires data stream)...")
    # Simulate waiting for some data first in a real scenario
    time.sleep(5) # Wait 5s for some data to potentially arrive
    success = calculate_baseline(duration_seconds=15) # Short baseline for testing
    if success:
        print("Baseline test completed successfully.")
        print("Stored Metrics:", data_store.get_baseline_metrics())
    else:
        print("Baseline test failed.")