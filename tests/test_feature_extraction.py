import unittest
import numpy as np
import sys
import os
import random # Import random module

# Add the project root to the Python path to allow importing braintrade_monitor
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from braintrade_monitor import feature_extraction, config

class TestFeatureExtraction(unittest.TestCase):

    def test_estimate_bpm_from_ppg_clean_sine(self):
        """Test BPM estimation with a clean sine wave."""
        sampling_rate = config.PPG_SAMPLING_RATE # 64 Hz
        duration = 10 # seconds
        target_bpm = 75
        target_freq = target_bpm / 60.0
        t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
        ppg_signal = np.sin(2 * np.pi * target_freq * t)

        bpm = feature_extraction.estimate_bpm_from_ppg(ppg_signal, sampling_rate)
        self.assertIsNotNone(bpm, "BPM should not be None for clean signal")
        self.assertFalse(np.isnan(bpm), "BPM should not be NaN for clean signal")
        self.assertAlmostEqual(bpm, target_bpm, delta=1.0, msg="BPM calculation deviates too much") # Allow 1 BPM delta

    def test_estimate_bpm_from_ppg_noisy(self):
        """Test BPM estimation with added noise."""
        sampling_rate = config.PPG_SAMPLING_RATE
        duration = 10
        target_bpm = 65
        target_freq = target_bpm / 60.0
        t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
        ppg_signal = np.sin(2 * np.pi * target_freq * t) + np.random.normal(0, 0.3, size=len(t)) # Add noise

        bpm = feature_extraction.estimate_bpm_from_ppg(ppg_signal, sampling_rate)
        self.assertIsNotNone(bpm)
        self.assertFalse(np.isnan(bpm))
        # Wider delta for noisy signal
        self.assertAlmostEqual(bpm, target_bpm, delta=5.0, msg="BPM calculation deviates too much on noisy signal")

    def test_estimate_bpm_from_ppg_insufficient_data(self):
        """Test BPM estimation with insufficient data length."""
        sampling_rate = config.PPG_SAMPLING_RATE
        ppg_signal = np.random.rand(sampling_rate) # Only 1 second
        bpm = feature_extraction.estimate_bpm_from_ppg(ppg_signal, sampling_rate)
        self.assertTrue(np.isnan(bpm), "BPM should be NaN for insufficient data")

    def test_estimate_bpm_from_ppg_no_peaks(self):
        """Test BPM estimation with flat signal (no peaks)."""
        sampling_rate = config.PPG_SAMPLING_RATE
        duration = 10
        ppg_signal = np.ones(int(sampling_rate * duration)) # Flat signal
        bpm = feature_extraction.estimate_bpm_from_ppg(ppg_signal, sampling_rate)
        self.assertTrue(np.isnan(bpm), "BPM should be NaN for flat signal")

    # --- Alpha/Beta Ratio Tests ---

    def _generate_eeg_signal(self, freqs_amps, duration, sampling_rate, noise_level=0.1):
        """Helper to generate multi-channel EEG with specific frequencies."""
        n_samples = int(duration * sampling_rate)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        eeg_data = np.random.normal(0, noise_level, size=(config.NUM_EEG_CHANNELS, n_samples))
        for chan in range(config.NUM_EEG_CHANNELS):
            for freq, amp in freqs_amps:
                eeg_data[chan, :] += amp * np.sin(2 * np.pi * freq * t + random.uniform(0, np.pi)) # Add phase shift
        return eeg_data

    def test_extract_alpha_beta_ratio_alpha_dominant(self):
        """Test ratio when alpha power is dominant."""
        sampling_rate = config.EEG_SAMPLING_RATE
        duration = config.EEG_WINDOW_DURATION * 2 # Ensure enough data
        # Strong Alpha (10Hz), Weak Beta (20Hz)
        eeg_data = self._generate_eeg_signal([(10, 5), (20, 1)], duration, sampling_rate)
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_data, sampling_rate)
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio))
        self.assertGreater(ratio, 1.0, "Ratio should be > 1 for alpha dominance") # Expect alpha > beta

    def test_extract_alpha_beta_ratio_beta_dominant(self):
        """Test ratio when beta power is dominant."""
        sampling_rate = config.EEG_SAMPLING_RATE
        duration = config.EEG_WINDOW_DURATION * 2
        # Weak Alpha (10Hz), Strong Beta (20Hz)
        eeg_data = self._generate_eeg_signal([(10, 1), (20, 5)], duration, sampling_rate)
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_data, sampling_rate)
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio))
        self.assertLess(ratio, 1.0, "Ratio should be < 1 for beta dominance") # Expect alpha < beta

    def test_extract_alpha_beta_ratio_noisy(self):
        """Test ratio calculation with significant noise."""
        sampling_rate = config.EEG_SAMPLING_RATE
        duration = config.EEG_WINDOW_DURATION * 2
        # Equal Alpha/Beta, high noise
        eeg_data = self._generate_eeg_signal([(10, 2), (20, 2)], duration, sampling_rate, noise_level=5.0)
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_data, sampling_rate)
        self.assertIsNotNone(ratio)
        self.assertFalse(np.isnan(ratio), "Ratio should still be calculable with noise")
        # Cannot assert specific value easily with high noise

    def test_extract_alpha_beta_ratio_insufficient_data(self):
        """Test ratio calculation with insufficient data length."""
        sampling_rate = config.EEG_SAMPLING_RATE
        # Data shorter than NFFT
        eeg_data = np.random.rand(config.NUM_EEG_CHANNELS, config.EEG_NFFT // 2)
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_data, sampling_rate)
        self.assertTrue(np.isnan(ratio), "Ratio should be NaN for insufficient data")

    def test_extract_alpha_beta_ratio_nan_input(self):
        """Test ratio calculation with NaN input data."""
        sampling_rate = config.EEG_SAMPLING_RATE
        duration = config.EEG_WINDOW_DURATION * 2
        eeg_data = np.random.rand(config.NUM_EEG_CHANNELS, int(duration * sampling_rate))
        eeg_data[0, 10:20] = np.nan # Introduce NaNs
        ratio = feature_extraction.extract_alpha_beta_ratio(eeg_data, sampling_rate)
        # MNE filter might handle NaNs, but PSD might return NaN or error
        # Depending on MNE version and exact handling, it might return NaN or raise error
        # For now, let's assert it doesn't crash and returns NaN if calculation fails
        # A more robust test might check specific MNE behavior or mock filter_data
        self.assertTrue(np.isnan(ratio) or isinstance(ratio, float), "Ratio calculation should handle NaNs gracefully (expect NaN or float)")


if __name__ == '__main__':
    unittest.main()