import unittest
from unittest.mock import patch, MagicMock, call
import time
import numpy as np
import queue
import threading
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Module to test
from braintrade_monitor import processing, config

# Mock the dependencies that processing_loop uses
@patch('braintrade_monitor.processing.state_logic')
@patch('braintrade_monitor.processing.feature_extraction')
@patch('braintrade_monitor.processing.data_store')
class TestProcessingLoop(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        self.update_queue = queue.Queue(maxsize=10)
        self.stop_event = threading.Event()

    def tearDown(self):
        """Ensure stop event is set after each test to clean up potential threads."""
        self.stop_event.set() # Ensure event is set even if test fails before join

    def test_normal_processing_flow(self, mock_data_store, mock_feature_extraction, mock_state_logic):
        """Test one iteration of the loop with valid data."""
        # --- Mock Setup ---
        mock_baseline = {'ratio_median': 1.5, 'hr_median': 70.0}
        mock_eeg_data = [[1.0] * 100] * config.NUM_EEG_CHANNELS
        mock_ppg_data = [1.0] * 100
        mock_acc_data = [(1,1,1)] * 50

        # Define side effect to return data then stop
        def get_data_side_effect(*args, **kwargs):
            # Return value for the first call
            return_value = (0.1, 0.1, 0.1, mock_eeg_data, mock_ppg_data, mock_acc_data, mock_baseline)
            # Set stop event after returning
            self.stop_event.set()
            return return_value

        mock_data_store.get_data_for_processing.side_effect = get_data_side_effect
        mock_feature_extraction.extract_alpha_beta_ratio.return_value = 1.8
        mock_feature_extraction.estimate_bpm_from_ppg.return_value = 65.0
        mock_state_logic.update_stress_state.return_value = "Calm"

        # --- Run Test ---
        test_thread = threading.Thread(target=processing.processing_loop, args=(self.update_queue, self.stop_event))
        test_thread.start()
        test_thread.join(timeout=2) # Wait for thread to finish (should be quick now)

        # --- Assertions ---
        self.assertTrue(self.stop_event.is_set(), "Stop event should be set by side effect")
        mock_data_store.get_data_for_processing.assert_called_once()
        mock_feature_extraction.extract_alpha_beta_ratio.assert_called_once()
        mock_feature_extraction.estimate_bpm_from_ppg.assert_called_once()
        mock_state_logic.update_stress_state.assert_called_once()

        self.assertFalse(self.update_queue.empty(), "Update queue should not be empty")
        update_data = self.update_queue.get_nowait()
        self.assertEqual(update_data["state"], "Calm")
        # ... other assertions ...

    def test_stale_data_handling(self, mock_data_store, mock_feature_extraction, mock_state_logic):
        """Test loop behavior when data is stale."""
        # Define side effect
        def get_data_side_effect(*args, **kwargs):
            return_value = (config.STALE_DATA_THRESHOLD + 1, 0.1, 0.1, None, None, None, {})
            self.stop_event.set()
            return return_value

        mock_data_store.get_data_for_processing.side_effect = get_data_side_effect

        # --- Run Test ---
        test_thread = threading.Thread(target=processing.processing_loop, args=(self.update_queue, self.stop_event))
        test_thread.start()
        test_thread.join(timeout=2)

        # --- Assertions ---
        self.assertTrue(self.stop_event.is_set())
        mock_data_store.get_data_for_processing.assert_called_once()
        mock_feature_extraction.extract_alpha_beta_ratio.assert_not_called()
        mock_feature_extraction.estimate_bpm_from_ppg.assert_not_called()
        mock_state_logic.update_stress_state.assert_not_called()

        self.assertFalse(self.update_queue.empty())
        update_data = self.update_queue.get_nowait()
        self.assertEqual(update_data["state"], "Uncertain (Stale Data)")
        # ... other assertions ...

    def test_nan_feature_handling(self, mock_data_store, mock_feature_extraction, mock_state_logic):
        """Test loop behavior when feature extraction returns NaN."""
        # Define side effect for data store
        def get_data_side_effect(*args, **kwargs):
             return_value = (0.1, 0.1, 0.1, [[1.0]*100]*config.NUM_EEG_CHANNELS, [1.0]*100, [(1,1,1)]*50, {'ratio_median': 1.5, 'hr_median': 70.0})
             self.stop_event.set()
             return return_value
        mock_data_store.get_data_for_processing.side_effect = get_data_side_effect

        mock_feature_extraction.extract_alpha_beta_ratio.return_value = np.nan
        mock_feature_extraction.estimate_bpm_from_ppg.return_value = 65.0
        mock_state_logic.update_stress_state.return_value = "Uncertain (NaN)"

        # --- Run Test ---
        test_thread = threading.Thread(target=processing.processing_loop, args=(self.update_queue, self.stop_event))
        test_thread.start()
        test_thread.join(timeout=2)

        # --- Assertions ---
        self.assertTrue(self.stop_event.is_set())
        mock_data_store.get_data_for_processing.assert_called_once()
        mock_feature_extraction.extract_alpha_beta_ratio.assert_called_once()
        mock_feature_extraction.estimate_bpm_from_ppg.assert_called_once()
        mock_state_logic.update_stress_state.assert_called_once()

        self.assertFalse(self.update_queue.empty())
        update_data = self.update_queue.get_nowait()
        self.assertEqual(update_data["state"], "Uncertain (NaN)")
        # ... other assertions ...


    # Remove class-level patch decorator
    def test_full_queue_handling(self, mock_data_store, mock_feature_extraction, mock_state_logic): # Remove mock_put_nowait arg
        """Test loop behavior when the UI queue is full."""
        # Pre-fill the queue
        for i in range(self.update_queue.maxsize):
            self.update_queue.put_nowait(f"dummy_{i}")

        # Define side effect for data store
        def get_data_side_effect(*args, **kwargs):
             return_value = (0.1, 0.1, 0.1, [[1.0]*100]*config.NUM_EEG_CHANNELS, [1.0]*100, [(1,1,1)]*50, {})
             # Don't set stop event here, let the queue exception happen
             return return_value
        mock_data_store.get_data_for_processing.side_effect = get_data_side_effect

        mock_feature_extraction.extract_alpha_beta_ratio.return_value = 1.8
        mock_feature_extraction.estimate_bpm_from_ppg.return_value = 65.0
        mock_state_logic.update_stress_state.return_value = "Calm"

        # Define side effect for the instance mock
        def queue_full_side_effect(*args, **kwargs):
            self.stop_event.set() # Stop the loop when queue is full
            raise queue.Full

        # Patch the instance method using 'with' and capture the mock
        with patch.object(self.update_queue, 'put_nowait', side_effect=queue_full_side_effect) as mock_put_instance:
            # --- Run Test ---
            test_thread = threading.Thread(target=processing.processing_loop, args=(self.update_queue, self.stop_event))
            test_thread.start()
            test_thread.join(timeout=2) # Wait for thread to finish

            # --- Assertions ---
            self.assertTrue(self.stop_event.is_set(), "Stop event should be set by queue full side effect")
            mock_data_store.get_data_for_processing.assert_called_once()
            mock_feature_extraction.extract_alpha_beta_ratio.assert_called_once()
            mock_state_logic.update_stress_state.assert_called_once()
            mock_put_instance.assert_called_once() # Assert on the instance mock


if __name__ == '__main__':
    unittest.main()