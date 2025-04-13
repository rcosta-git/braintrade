import unittest
from unittest.mock import patch, MagicMock
import time
import numpy as np
import sys
import os
import collections # Import collections

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Modules to test and dependencies
from braintrade_monitor import baseline, data_store, config

class TestBaseline(unittest.TestCase):

    def setUp(self):
        """Initialize data store before each test."""
        # Use small buffers for baseline tests as we control data population
        self.eeg_size = config.EEG_SAMPLING_RATE * (config.EEG_WINDOW_DURATION + 2) # Enough for >1 window
        self.ppg_size = config.PPG_SAMPLING_RATE * (config.PPG_WINDOW_DURATION + 2) # Enough for >1 window
        self.acc_size = 100 # Placeholder
        self.num_eeg = config.NUM_EEG_CHANNELS

        data_store.initialize_data_store(
            eeg_buffer_size=self.eeg_size,
            ppg_buffer_size=self.ppg_size,
            acc_buffer_size=self.acc_size,
            num_eeg_channels=self.num_eeg
        )

    def _populate_data(self, num_seconds):
        """Helper to populate data store with dummy data using public functions."""
        # EEG Data
        eeg_samples_to_add = int(num_seconds * config.EEG_SAMPLING_RATE)
        for i in range(eeg_samples_to_add):
            # Generate a sample for this step
            eeg_sample = [float(i + chan) for chan in range(self.num_eeg)]
            # Add using the public function (timestamp is handled internally)
            data_store.add_eeg_data(eeg_sample)
            # Small sleep to prevent tight loop and allow time to advance slightly
            # if i % 100 == 0: time.sleep(0.0001) # Optional: simulate time passing

        # PPG Data
        ppg_samples_to_add = int(num_seconds * config.PPG_SAMPLING_RATE)
        for i in range(ppg_samples_to_add):
             # Generate a sample for this step (using dummy sensor ID 1)
             ppg_sample = [1, float(i * 0.1), 1]
             # Add using the public function
             data_store.add_ppg_data(ppg_sample)
             # if i % 10 == 0: time.sleep(0.0001) # Optional: simulate time passing

    # Use patch to mock the feature extraction functions during the test
    @patch('braintrade_monitor.feature_extraction.extract_alpha_beta_ratio')
    @patch('braintrade_monitor.feature_extraction.estimate_bpm_from_ppg')
    def test_calculate_baseline_success(self, mock_estimate_bpm, mock_extract_ratio): # Swapped args to match decorator order
        """Test successful baseline calculation with mocked feature extraction."""
        # Configure mocks to return consistent values
        mock_extract_ratio.return_value = (1.5, 0.5)  # Example ratio and theta
        mock_estimate_bpm.return_value = 70.0  # Example HR

        # Populate enough data (must be >= longest window duration used in check, which is PPG)
        populate_duration = 15  # e.g., 15 seconds
        self._populate_data(num_seconds=populate_duration)

        # Populate enough data (must be >= longest window duration used in check, which is PPG)
        # populate_duration = 15 # e.g., 11 seconds
        # self._populate_data(num_seconds=populate_duration)

        # Run baseline calculation (short duration for test speed)
        # The duration here mainly affects the wait time, data is already populated
        success = baseline.calculate_baseline(duration_seconds=15) # Wait only 1s

        self.assertTrue(success, "Baseline calculation should succeed")

        # Verify mocks were called (at least once, actual count depends on windowing)
        mock_extract_ratio.assert_called()
        mock_estimate_bpm.assert_called()

        # Verify stored metrics
        metrics = data_store.get_baseline_metrics()
        self.assertIn('ratio_median', metrics)
        self.assertIn('ratio_std', metrics)
        self.assertIn('hr_median', metrics)
        self.assertIn('hr_std', metrics)
        self.assertAlmostEqual(metrics['ratio_median'], 1.5)
        self.assertAlmostEqual(metrics['hr_median'], 70.0)
        self.assertAlmostEqual(metrics['theta_median'], 0.5)
        self.assertEqual(metrics['ratio_std'], 0.0) # Std should be 0 if mock always returns same value
        self.assertEqual(metrics['hr_std'], 0.0)
        self.assertEqual(metrics['theta_std'], 0.0)

    def test_calculate_baseline_insufficient_eeg(self):
        """Test baseline failure with insufficient EEG data."""
        # Populate only PPG data
        self._populate_data(num_seconds=config.PPG_WINDOW_DURATION + 1)
        # Clear EEG specifically
        with data_store._data_lock:
            data_store._eeg_data_buffers = [collections.deque(maxlen=self.eeg_size) for _ in range(self.num_eeg)]

        success = baseline.calculate_baseline(duration_seconds=1)
        self.assertFalse(success, "Baseline should fail with insufficient EEG data")
        metrics = data_store.get_baseline_metrics()
        self.assertEqual(metrics, {}, "Baseline metrics should not be set on failure")

    def test_calculate_baseline_insufficient_ppg(self):
        """Test baseline failure with insufficient PPG data."""
         # Populate only EEG data
        self._populate_data(num_seconds=config.EEG_WINDOW_DURATION + 1)
         # Clear PPG specifically
        with data_store._data_lock:
            data_store._ppg_data_buffer = collections.deque(maxlen=self.ppg_size)
            # Need to ensure EEG is cleared from the helper's PPG loop run
            data_store._eeg_data_buffers = [collections.deque(maxlen=self.eeg_size) for _ in range(self.num_eeg)]
        # Re-populate EEG
        self._populate_data(num_seconds=config.EEG_WINDOW_DURATION + 1)


        success = baseline.calculate_baseline(duration_seconds=1)
        self.assertFalse(success, "Baseline should fail with insufficient PPG data")
        metrics = data_store.get_baseline_metrics()
        self.assertEqual(metrics, {}, "Baseline metrics should not be set on failure")


    @patch('braintrade_monitor.feature_extraction.extract_alpha_beta_ratio')
    @patch('braintrade_monitor.feature_extraction.estimate_bpm_from_ppg')
    def test_calculate_baseline_nan_features(self, mock_extract_ratio, mock_estimate_bpm): # Swapped args to match decorator order
        """Test baseline failure when feature extraction returns NaN."""
        mock_extract_ratio.return_value = (np.nan, np.nan)
        mock_estimate_bpm.return_value = np.nan

        self._populate_data(num_seconds=max(config.EEG_WINDOW_DURATION, config.PPG_WINDOW_DURATION) + 1)

        success = baseline.calculate_baseline(duration_seconds=1)

        self.assertFalse(success, "Baseline should fail if features are always NaN")
        metrics = data_store.get_baseline_metrics()
        self.assertEqual(metrics, {}, "Baseline metrics should not be set on NaN failure")


if __name__ == '__main__':
    unittest.main()
