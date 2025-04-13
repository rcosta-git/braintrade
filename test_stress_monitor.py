import unittest
import numpy as np
import scipy.signal
import mne
from collections import deque
import argparse # Needed for args simulation
from stress_monitor import (
    estimate_bpm_from_ppg, 
    extract_alpha_beta_ratio, 
    update_stress_state, # Import the new function
    PPG_SAMPLING_RATE, 
    EEG_SAMPLING_RATE,
    ALPHA_BAND,
    BETA_BAND,
    EEG_NFFT,
    EPSILON,
    STATE_PERSISTENCE_UPDATES, # Import persistence constant
    # Import other constants needed for args
    PPG_FILTER_LOWCUT,
    PPG_FILTER_HIGHCUT,
    PPG_PEAK_MIN_DIST_FACTOR,
    PPG_PEAK_HEIGHT_FACTOR,
    EEG_FILTER_LOWCUT,
    EEG_FILTER_HIGHCUT,
    RATIO_THRESHOLD,
    HR_THRESHOLD
)
from scipy.integrate import trapezoid 
import logging

# Suppress MNE info logs during testing for cleaner output
mne.set_log_level('WARNING') 
logging.getLogger().setLevel(logging.WARNING) # Suppress our own info logs during tests

# Helper to simulate args object for tests
def create_test_args(
    ratio_threshold=RATIO_THRESHOLD, 
    hr_threshold=HR_THRESHOLD,
    persistence=STATE_PERSISTENCE_UPDATES,
    ppg_filter_low=PPG_FILTER_LOWCUT,
    ppg_filter_high=PPG_FILTER_HIGHCUT,
    ppg_peak_min_dist_factor=PPG_PEAK_MIN_DIST_FACTOR,
    ppg_peak_height_factor=PPG_PEAK_HEIGHT_FACTOR,
    eeg_filter_low=EEG_FILTER_LOWCUT,
    eeg_filter_high=EEG_FILTER_HIGHCUT,
    alpha_band=ALPHA_BAND,
    beta_band=BETA_BAND,
    nfft=EEG_NFFT
    ):
    """Creates a Namespace object simulating parsed command-line arguments."""
    args = argparse.Namespace(
        ratio_threshold=ratio_threshold,
        hr_threshold=hr_threshold,
        persistence=persistence,
        ppg_filter_low=ppg_filter_low,
        ppg_filter_high=ppg_filter_high,
        ppg_peak_min_dist_factor=ppg_peak_min_dist_factor,
        ppg_peak_height_factor=ppg_peak_height_factor,
        eeg_filter_low=eeg_filter_low,
        eeg_filter_high=eeg_filter_high,
        alpha_band=alpha_band,
        beta_band=beta_band,
        nfft=nfft
    )
    return args

class TestPPGEstimation(unittest.TestCase):

    def setUp(self):
        """Create default args for PPG tests."""
        self.args = create_test_args()

    def test_estimate_bpm_from_ppg_basic(self):
        """Test BPM estimation with a clean simulated PPG signal."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 10  # seconds
        bpm_target = 75
        
        # Simulate a relatively clean PPG-like signal
        time_vec = np.linspace(0, duration, int(duration * sampling_rate), endpoint=False)
        heart_rate_hz = bpm_target / 60.0
        # Create a base sine wave at the heart rate frequency
        ppg_signal = np.sin(2 * np.pi * heart_rate_hz * time_vec)
        # Add some higher frequency noise
        noise = np.random.normal(0, 0.1, ppg_signal.shape)
        ppg_signal += noise
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        
        self.assertIsNotNone(estimated_bpm, "BPM estimation returned None")
        self.assertFalse(np.isnan(estimated_bpm), "BPM estimation returned NaN")
        # Allow for some tolerance in the estimation
        self.assertAlmostEqual(estimated_bpm, bpm_target, delta=5, 
                               msg=f"Estimated BPM ({estimated_bpm:.1f}) differs significantly from target ({bpm_target})")

    def test_estimate_bpm_low_hr(self):
        """Test BPM estimation with a lower heart rate."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 15 # Longer duration for lower HR
        bpm_target = 50
        
        time_vec = np.linspace(0, duration, int(duration * sampling_rate), endpoint=False)
        heart_rate_hz = bpm_target / 60.0
        ppg_signal = np.sin(2 * np.pi * heart_rate_hz * time_vec) + np.random.normal(0, 0.1, int(duration*sampling_rate))
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        
        self.assertIsNotNone(estimated_bpm)
        self.assertFalse(np.isnan(estimated_bpm))
        self.assertAlmostEqual(estimated_bpm, bpm_target, delta=5,
                               msg=f"Estimated BPM ({estimated_bpm:.1f}) differs significantly from target ({bpm_target})")

    def test_estimate_bpm_high_hr(self):
        """Test BPM estimation with a higher heart rate."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 10 
        bpm_target = 120
        
        time_vec = np.linspace(0, duration, int(duration * sampling_rate), endpoint=False)
        heart_rate_hz = bpm_target / 60.0
        ppg_signal = np.sin(2 * np.pi * heart_rate_hz * time_vec) + np.random.normal(0, 0.1, int(duration*sampling_rate))
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        
        self.assertIsNotNone(estimated_bpm)
        self.assertFalse(np.isnan(estimated_bpm))
        self.assertAlmostEqual(estimated_bpm, bpm_target, delta=10, # Higher tolerance for higher HR
                               msg=f"Estimated BPM ({estimated_bpm:.1f}) differs significantly from target ({bpm_target})")

    def test_estimate_bpm_noisy(self):
        """Test BPM estimation with a noisier signal."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 10
        bpm_target = 80
        
        time_vec = np.linspace(0, duration, int(duration * sampling_rate), endpoint=False)
        heart_rate_hz = bpm_target / 60.0
        ppg_signal = np.sin(2 * np.pi * heart_rate_hz * time_vec) + np.random.normal(0, 0.5, int(duration*sampling_rate)) # Increased noise
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        
        self.assertIsNotNone(estimated_bpm)
        self.assertFalse(np.isnan(estimated_bpm))
        self.assertAlmostEqual(estimated_bpm, bpm_target, delta=10, # Allow more tolerance for noise
                               msg=f"Estimated BPM ({estimated_bpm:.1f}) differs significantly from target ({bpm_target})")

    def test_estimate_bpm_too_short(self):
        """Test with insufficient data length."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 1 # seconds - less than 2s needed
        ppg_signal = np.random.rand(int(duration * sampling_rate))
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        self.assertTrue(np.isnan(estimated_bpm), "Expected NaN for short signal")

    def test_estimate_bpm_no_peaks(self):
        """Test with a signal likely to have no clear peaks (e.g., flat line)."""
        sampling_rate = PPG_SAMPLING_RATE
        duration = 10
        ppg_signal = np.ones(int(duration * sampling_rate)) * 0.5 # Flat signal
        
        estimated_bpm = estimate_bpm_from_ppg(ppg_signal, sampling_rate, self.args) # Pass args
        self.assertTrue(np.isnan(estimated_bpm), "Expected NaN for signal with no peaks")

class TestEEGRatio(unittest.TestCase):

    def setUp(self):
        """Create default args for EEG tests."""
        self.args = create_test_args()

    def _generate_eeg_signal(self, duration, sampling_rate, freqs_powers):
        """Helper to generate multi-channel EEG with specific frequency components."""
        n_channels = 4
        n_times = int(duration * sampling_rate)
        time_vec = np.linspace(0, duration, n_times, endpoint=False)
        eeg_data = np.zeros((n_channels, n_times))
        
        for freq, power, channel_indices in freqs_powers:
            for ch_idx in channel_indices:
                if ch_idx < n_channels:
                    # Use power related to amplitude squared
                    amplitude = np.sqrt(2 * power) # Approximate relationship for sine wave
                    eeg_data[ch_idx, :] += amplitude * np.sin(2 * np.pi * freq * time_vec + np.random.rand() * 2 * np.pi)
        
        # Add some background noise
        eeg_data += np.random.normal(0, 0.1, eeg_data.shape) 
        return eeg_data

    def test_alpha_dominant(self):
        """Test with signal primarily in the alpha band."""
        sampling_rate = EEG_SAMPLING_RATE
        duration = 5 # seconds
        alpha_freq = (ALPHA_BAND[0] + ALPHA_BAND[1]) / 2
        beta_freq = (BETA_BAND[0] + BETA_BAND[1]) / 2
        
        # Strong alpha power, weak beta power
        freqs_powers = [
            (alpha_freq, 1.0, [0, 1, 2, 3]), # Alpha on all channels
            (beta_freq, 0.1, [0, 1, 2, 3])   # Beta on all channels
        ]
        eeg_data = self._generate_eeg_signal(duration, sampling_rate, freqs_powers)
        
        ratio = extract_alpha_beta_ratio(eeg_data, sampling_rate, self.args) # Pass args
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio))
        self.assertGreater(ratio, 1.5, f"Expected alpha-dominant ratio (>1.5), got {ratio:.2f}") 

    def test_beta_dominant(self):
        """Test with signal primarily in the beta band."""
        sampling_rate = EEG_SAMPLING_RATE
        duration = 5 # seconds
        alpha_freq = (ALPHA_BAND[0] + ALPHA_BAND[1]) / 2
        beta_freq = (BETA_BAND[0] + BETA_BAND[1]) / 2
        
        # Weak alpha power, strong beta power
        freqs_powers = [
            (alpha_freq, 0.1, [0, 1, 2, 3]), # Alpha on all channels
            (beta_freq, 1.0, [0, 1, 2, 3])   # Beta on all channels
        ]
        eeg_data = self._generate_eeg_signal(duration, sampling_rate, freqs_powers)
        
        ratio = extract_alpha_beta_ratio(eeg_data, sampling_rate, self.args) # Pass args
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio))
        self.assertLess(ratio, 0.7, f"Expected beta-dominant ratio (<0.7), got {ratio:.2f}") 

    def test_mixed_signal(self):
        """Test with roughly equal power in alpha and beta bands."""
        sampling_rate = EEG_SAMPLING_RATE
        duration = 5 # seconds
        alpha_freq = (ALPHA_BAND[0] + ALPHA_BAND[1]) / 2
        beta_freq = (BETA_BAND[0] + BETA_BAND[1]) / 2
        
        freqs_powers = [
            (alpha_freq, 0.5, [0, 1, 2, 3]), 
            (beta_freq, 0.5, [0, 1, 2, 3])   
        ]
        eeg_data = self._generate_eeg_signal(duration, sampling_rate, freqs_powers)
        
        ratio = extract_alpha_beta_ratio(eeg_data, sampling_rate, self.args) # Pass args
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio))
        # Adjust delta based on observed results if needed, PSD estimation isn't perfect
        self.assertAlmostEqual(ratio, 1.0, delta=0.6, msg=f"Expected ratio near 1.0, got {ratio:.2f}")

    def test_no_beta_power(self):
        """Test case where beta power is essentially zero (expect large ratio)."""
        sampling_rate = EEG_SAMPLING_RATE
        duration = 5
        alpha_freq = (ALPHA_BAND[0] + ALPHA_BAND[1]) / 2
        
        freqs_powers = [(alpha_freq, 1.0, [0, 1, 2, 3])] # Only alpha
        eeg_data = self._generate_eeg_signal(duration, sampling_rate, freqs_powers)
        
        ratio = extract_alpha_beta_ratio(eeg_data, sampling_rate, self.args) # Pass args
        # Expect a large ratio, not NaN, due to noise floor/leakage in beta band
        self.assertIsNotNone(ratio, "Ratio should not be None")
        self.assertFalse(np.isnan(ratio), f"Ratio should not be NaN, got {ratio}")
        self.assertGreater(ratio, 100, f"Expected very large ratio when beta power is near zero, got {ratio:.2f}")

    def test_eeg_too_short_for_fft(self):
        """Test with EEG data too short for the default FFT window."""
        sampling_rate = EEG_SAMPLING_RATE
        duration = 0.5 # Less than n_fft/sampling_rate (256/256 = 1s)
        n_times = int(duration * sampling_rate)
        eeg_data = np.random.rand(4, n_times)

        ratio = extract_alpha_beta_ratio(eeg_data, sampling_rate, self.args) # Pass args
        self.assertTrue(np.isnan(ratio), "Expected NaN for EEG signal too short for FFT")

class TestStateLogic(unittest.TestCase):

    def setUp(self):
        """Set up baseline metrics and args for state logic tests."""
        self.baseline_metrics = {
            'ratio_median': 1.0,
            'ratio_std': 0.2,
            'hr_median': 70.0,
            'hr_std': 5.0
        }
        # Use the updated helper function
        self.args = create_test_args(ratio_threshold=1.5, hr_threshold=1.5, persistence=STATE_PERSISTENCE_UPDATES) 
        self.initial_state = "Initializing"
        # Use the persistence value from args for the deque maxlen
        self.history = deque(maxlen=self.args.persistence) 

    def test_initial_state_calm(self):
        """Test that state remains Calm if inputs are within baseline."""
        current_state = self.initial_state
        # Simulate multiple updates within baseline
        for _ in range(self.args.persistence): # Use args.persistence
             current_state = update_stress_state(1.0, 70.0, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Calm")

    def test_transition_to_warning_low_ratio(self):
        """Test transition to Warning due to low ratio."""
        current_state = "Calm"
        ratio_low = self.baseline_metrics['ratio_median'] - self.args.ratio_threshold * self.baseline_metrics['ratio_std'] - 0.1
        # Simulate not enough updates
        for _ in range(self.args.persistence - 1): # Use args.persistence
             current_state = update_stress_state(ratio_low, 70.0, self.baseline_metrics, current_state, self.history, self.args)
             self.assertEqual(current_state, "Calm", "State should not change before persistence")
        # Final update to trigger change
        current_state = update_stress_state(ratio_low, 70.0, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Warning")

    def test_transition_to_warning_high_hr(self):
        """Test transition to Warning due to high HR."""
        current_state = "Calm"
        hr_high = self.baseline_metrics['hr_median'] + self.args.hr_threshold * self.baseline_metrics['hr_std'] + 1.0
        for _ in range(self.args.persistence - 1): # Use args.persistence
             current_state = update_stress_state(1.0, hr_high, self.baseline_metrics, current_state, self.history, self.args)
             self.assertEqual(current_state, "Calm", "State should not change before persistence")
        current_state = update_stress_state(1.0, hr_high, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Warning")

    def test_transition_to_stress(self):
        """Test transition to Stress due to low ratio and high HR."""
        current_state = "Calm"
        ratio_low = self.baseline_metrics['ratio_median'] - self.args.ratio_threshold * self.baseline_metrics['ratio_std'] - 0.1
        hr_high = self.baseline_metrics['hr_median'] + self.args.hr_threshold * self.baseline_metrics['hr_std'] + 1.0
        for _ in range(self.args.persistence - 1): # Use args.persistence
             current_state = update_stress_state(ratio_low, hr_high, self.baseline_metrics, current_state, self.history, self.args)
             self.assertEqual(current_state, "Calm", "State should not change before persistence")
        current_state = update_stress_state(ratio_low, hr_high, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Stress")

    def test_transition_back_to_calm(self):
        """Test transition from Stress back to Calm."""
        current_state = "Stress" # Start in Stress
        # Fill history with Stress state
        for _ in range(self.args.persistence): # Use args.persistence
            self.history.append("Stress") 
            
        # Simulate return to normal values
        for _ in range(self.args.persistence - 1): # Use args.persistence
             current_state = update_stress_state(1.0, 70.0, self.baseline_metrics, current_state, self.history, self.args)
             self.assertEqual(current_state, "Stress", "State should not change back before persistence")
        current_state = update_stress_state(1.0, 70.0, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Calm")

    def test_state_with_nan_input(self):
        """Test that state remains unchanged with NaN inputs."""
        current_state = "Calm"
        for _ in range(self.args.persistence): # Use args.persistence
            self.history.append("Calm") 
            
        # Update with NaN ratio
        new_state = update_stress_state(np.nan, 70.0, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(new_state, "Calm", "State should not change on NaN ratio")
        self.assertEqual(self.history[-1], "Uncertain (NaN)") # Tentative state should be uncertain

        # Update with NaN HR
        new_state = update_stress_state(1.0, np.nan, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(new_state, "Calm", "State should not change on NaN HR")
        self.assertEqual(self.history[-1], "Uncertain (NaN)") # Tentative state should be uncertain
        
        # Check persistence to Uncertain (NaN)
        current_state = "Calm"
        self.history.clear()
        for _ in range(self.args.persistence): # Use args.persistence
             current_state = update_stress_state(np.nan, np.nan, self.baseline_metrics, current_state, self.history, self.args)
        self.assertEqual(current_state, "Uncertain (NaN)")


if __name__ == '__main__':
    unittest.main()