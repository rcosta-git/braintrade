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
    # ACC data is now processed

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
    thetas = [] # Initialize thetas list
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
        ratio, theta = feature_extraction.extract_alpha_beta_ratio(eeg_window, config.EEG_SAMPLING_RATE)
        if not np.isnan(ratio) and not np.isnan(theta):
            ratios.append(ratio)
            thetas.append(theta) # Append theta here

    # PPG HR Calculation
    for i in range(0, len(ppg_baseline_data) - ppg_window_samples + 1, step_samples_ppg):
        ppg_window = ppg_baseline_data[i:i+ppg_window_samples]
        # Pass sampling rate directly from config
        hr = feature_extraction.estimate_bpm_from_ppg(ppg_window, config.PPG_SAMPLING_RATE)
        if not np.isnan(hr):
            hrs.append(hr)

    # ACC Movement Calculation
    movements = []
    # Define ACC window and step based on assumed sampling rate (e.g., 50Hz) and duration
    # TODO: Get ACC sampling rate from config or data source if possible
    acc_sampling_rate = 50 # Assume 50Hz for now
    acc_window_duration = 3 # seconds, match processing loop expectation
    acc_window_samples = int(acc_sampling_rate * acc_window_duration)
    step_samples_acc = int(acc_sampling_rate * config.UPDATE_INTERVAL)

    if len(acc_baseline_data) >= acc_window_samples:
        for i in range(0, len(acc_baseline_data) - acc_window_samples + 1, step_samples_acc):
            acc_window = acc_baseline_data[i:i+acc_window_samples]
            # Pass sampling rate directly from config (or assumed value)
            movement = feature_extraction.get_movement_metric(acc_window)
            if not np.isnan(movement):
                movements.append(movement)
                # logging.debug(f"Baseline movement sample {len(movements)}: {movement:.4f}") # Commented out
    else:
        logging.warning(f"Insufficient ACC data for baseline movement calculation. Collected: {len(acc_baseline_data)}, Required: {acc_window_samples}")

    # --- Store Results ---
    # --- Store Results ---
    # Check if enough samples were collected for *all* metrics needed
    if not ratios or not hrs or not thetas or not movements:
        logging.error(f"Error: Not enough valid feature samples calculated during baseline. "
                      f"Ratios: {len(ratios)}, HRs: {len(hrs)}, Thetas: {len(thetas)}, Movements: {len(movements)}")
        # Store whatever was calculated, but return False
        calculated_metrics = {
            'ratio_median': np.median(ratios) if ratios else np.nan,
            'ratio_std': np.std(ratios) if ratios else np.nan,
            'hr_median': np.median(hrs) if hrs else np.nan,
            'hr_std': np.std(hrs) if hrs else np.nan,
            'theta_median': np.median(thetas) if thetas else np.nan,
            'theta_std': np.std(thetas) if thetas else np.nan,
            'movement_median': np.median(movements) if movements else np.nan,
            'movement_std': np.std(movements) if movements else np.nan
        }
        data_store.set_baseline_metrics(calculated_metrics) # Store partial/NaN results
        return False

# Remove the redundant second EEG loop
    # All metrics have sufficient samples, calculate and store final values
    calculated_metrics = {
        'ratio_median': np.median(ratios),
        'ratio_std': np.std(ratios),
        'hr_median': np.median(hrs),
        'hr_std': np.std(hrs),
        'theta_median': np.median(thetas),
        'theta_std': np.std(thetas),
        'movement_median': np.median(movements),
        'movement_std': np.std(movements)
    }

    # Store the final, valid baseline metrics
    data_store.set_baseline_metrics(calculated_metrics)

    logging.info("-" * 30)
    logging.info("Baseline Calculation Complete:")
    logging.info(f"  Baseline A/B Ratio: {calculated_metrics['ratio_median']:.2f} +/- {calculated_metrics['ratio_std']:.2f} ({len(ratios)} samples)")
    logging.info(f"  Baseline HR: {calculated_metrics['hr_median']:.1f} +/- {calculated_metrics['hr_std']:.1f} BPM ({len(hrs)} samples)")
    logging.info(f"  Baseline Theta Power: {calculated_metrics.get('theta_median', np.nan):.2f} +/- {calculated_metrics.get('theta_std', np.nan):.2f} ({len(thetas)} samples)")
    logging.info(f"  Baseline Movement: {calculated_metrics.get('movement_median', np.nan):.4f} +/- {calculated_metrics.get('movement_std', np.nan):.4f} ({len(movements)} samples)")
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