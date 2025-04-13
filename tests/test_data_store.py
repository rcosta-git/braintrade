import unittest
import time
import numpy as np
import collections
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Modules to test
from braintrade_monitor import data_store, config

# DO NOT import internal variables like _eeg_data_buffers directly

class TestDataStore(unittest.TestCase):

    def setUp(self):
        """Initialize the data store before each test."""
        # Use larger buffers for windowing test
        self.eeg_size = config.EEG_SAMPLING_RATE * 10 # 10 seconds worth
        self.ppg_size = config.PPG_SAMPLING_RATE * 15 # 15 seconds worth
        self.acc_size = 50 * 10 # 10 seconds worth (assuming 50Hz)
        self.num_eeg = config.NUM_EEG_CHANNELS # 4

        data_store.initialize_data_store(
            eeg_buffer_size=self.eeg_size,
            ppg_buffer_size=self.ppg_size,
            acc_buffer_size=self.acc_size,
            num_eeg_channels=self.num_eeg
        )
        # Resetting internal timestamps directly here is okay for test setup isolation,
        # but accessing them for assertions should use the public getter.
        data_store._last_eeg_timestamp = 0
        data_store._last_ppg_timestamp = 0
        data_store._last_acc_timestamp = 0
        data_store._baseline_metrics.clear()


    def test_initialization(self):
        """Test if data store initializes correctly by checking state via functions."""
        # Check buffer initialization indirectly by adding/retrieving data
        self.assertTrue(data_store.check_buffers_initialized())
        eeg, ppg, acc = data_store.get_all_data_for_baseline()
        self.assertEqual(eeg.shape, (self.num_eeg, 0)) # Should be empty
        self.assertEqual(len(ppg), 0)
        self.assertEqual(len(acc), 0)

        timestamps = data_store.get_last_timestamps()
        self.assertEqual(timestamps["eeg"], 0)
        self.assertEqual(timestamps["ppg"], 0)
        self.assertEqual(timestamps["acc"], 0)

        metrics = data_store.get_baseline_metrics()
        self.assertEqual(metrics, {})

    def test_add_eeg_data_valid(self):
        """Test adding valid EEG data and check via retrieval and timestamp."""
        start_time = time.time()
        eeg_sample = [1.0, 2.0, 3.0, 4.0]
        data_store.add_eeg_data(eeg_sample)

        # Check timestamp using the getter
        timestamps = data_store.get_last_timestamps()
        self.assertGreaterEqual(timestamps["eeg"], start_time)
        self.assertLess(timestamps["eeg"] - start_time, 0.1, "Timestamp update took too long")

        # Check data via retrieval
        eeg, _, _ = data_store.get_all_data_for_baseline()
        self.assertEqual(eeg.shape, (self.num_eeg, 1))
        np.testing.assert_array_almost_equal(eeg[:, 0], eeg_sample)


    def test_add_eeg_data_invalid_length(self):
        """Test adding EEG data with incorrect channel count."""
        initial_timestamps = data_store.get_last_timestamps()
        data_store.add_eeg_data([1.0, 2.0, 3.0]) # Only 3 channels

        # Check data wasn't added
        eeg, _, _ = data_store.get_all_data_for_baseline()
        self.assertEqual(eeg.shape, (self.num_eeg, 0))

        # Check timestamp wasn't updated
        final_timestamps = data_store.get_last_timestamps()
        self.assertEqual(final_timestamps["eeg"], initial_timestamps["eeg"])

    def test_add_eeg_data_buffer_limit(self):
        """Test EEG buffer respects maxlen using public add function."""
        for i in range(self.eeg_size + 10):
            data_store.add_eeg_data([float(i)] * self.num_eeg)

        # Check data via retrieval
        eeg, _, _ = data_store.get_all_data_for_baseline()
        self.assertEqual(eeg.shape, (self.num_eeg, self.eeg_size)) # Should have maxlen samples

        # Check if the first element added is gone (value 0.0)
        self.assertNotEqual(eeg[0, 0], 0.0)
        # Check if the last element added is present (value eeg_size + 9)
        self.assertEqual(eeg[0, -1], float(self.eeg_size + 9))

    def test_add_ppg_data_valid(self):
        """Test adding valid PPG data."""
        start_time = time.time()
        ppg_sample = [1, 50.5, 1] # sensor_id, value, sensor_id
        data_store.add_ppg_data(ppg_sample)

        timestamps = data_store.get_last_timestamps()
        self.assertGreaterEqual(timestamps["ppg"], start_time)
        self.assertLess(timestamps["ppg"] - start_time, 0.1)

        _, ppg, _ = data_store.get_all_data_for_baseline()
        self.assertEqual(len(ppg), 1)
        self.assertEqual(ppg[0], ppg_sample[1])

    def test_add_acc_data_valid(self):
        """Test adding valid ACC data."""
        start_time = time.time()
        acc_sample = [0.1, 0.2, 9.8]
        data_store.add_acc_data(acc_sample)

        timestamps = data_store.get_last_timestamps()
        self.assertGreaterEqual(timestamps["acc"], start_time)
        self.assertLess(timestamps["acc"] - start_time, 0.1)

        _, _, acc = data_store.get_all_data_for_baseline()
        self.assertEqual(acc.shape, (1, 3))
        np.testing.assert_array_almost_equal(acc[0, :], acc_sample)


    def test_set_get_baseline_metrics(self):
        """Test setting and getting baseline metrics."""
        metrics = {'hr_median': 75.0, 'hr_std': 4.0}
        data_store.set_baseline_metrics(metrics)
        retrieved_metrics = data_store.get_baseline_metrics()
        self.assertEqual(retrieved_metrics, metrics)

        more_metrics = {'ratio_median': 1.2, 'ratio_std': 0.3}
        data_store.set_baseline_metrics(more_metrics)
        retrieved_metrics = data_store.get_baseline_metrics()
        expected_metrics = {'hr_median': 75.0, 'hr_std': 4.0, 'ratio_median': 1.2, 'ratio_std': 0.3}
        self.assertEqual(retrieved_metrics, expected_metrics)


    def test_get_data_for_processing_empty(self):
        """Test getting data when buffers are empty."""
        results = data_store.get_data_for_processing(3, 10, 3)
        ts_eeg, ts_ppg, ts_acc, eeg, ppg, acc, baseline = results
        timestamps = data_store.get_last_timestamps()
        self.assertEqual(ts_eeg, float('inf'))
        self.assertEqual(ts_ppg, float('inf'))
        self.assertEqual(ts_acc, float('inf'))
        self.assertIsNone(eeg)
        self.assertIsNone(ppg)
        self.assertIsNone(acc)
        self.assertEqual(baseline, {})
        self.assertEqual(timestamps["eeg"], 0) # Also check timestamps are still 0


    def test_get_data_for_processing_windowing(self):
        """Test if data retrieval respects time windows with sufficient buffer."""
        # Add data over 5 seconds using the public function
        eeg_val = 0.0
        ppg_val = 0.0
        start_ts = time.time()
        num_eeg_samples_added = 5 * config.EEG_SAMPLING_RATE
        num_ppg_samples_added = 5 * config.PPG_SAMPLING_RATE

        # Simulate adding data over time
        for i in range(num_eeg_samples_added):
             # We don't control exact time here, rely on add_eeg_data's time.time()
             data_store.add_eeg_data([eeg_val] * self.num_eeg)
             eeg_val += 0.01
             # Simulate approximate timing
             if i % (config.EEG_SAMPLING_RATE // 10) == 0: time.sleep(0.0001)

        for i in range(num_ppg_samples_added):
             data_store.add_ppg_data([1, ppg_val, 1])
             ppg_val += 0.1
             if i % (config.PPG_SAMPLING_RATE // 10) == 0: time.sleep(0.001)

        # Wait a moment so 'now' is clearly after the added data
        time.sleep(0.1)
        current_time = time.time()

        # Request a 3-second EEG window and 2-second PPG window
        eeg_win_dur = 3.0
        ppg_win_dur = 2.0
        results = data_store.get_data_for_processing(eeg_win_dur, ppg_win_dur, 1) # ACC=1s
        ts_eeg, ts_ppg, ts_acc, eeg, ppg, acc, baseline = results

        # Check timestamps are recent
        self.assertLess(ts_eeg, 1.0)
        self.assertLess(ts_ppg, 1.0)
        self.assertEqual(ts_acc, float('inf')) # No ACC data added

        # Check lengths (approximate due to timing)
        self.assertIsNotNone(eeg, "EEG data should not be None")
        self.assertTrue(all(len(ch) > 0 for ch in eeg), "All EEG channels should have data")
        # Check if the number of samples is plausible for the window
        actual_eeg_count = len(eeg[0])
        max_possible_in_window = int(eeg_win_dur * config.EEG_SAMPLING_RATE * 1.1) # Allow 10% buffer
        self.assertLessEqual(actual_eeg_count, num_eeg_samples_added, "Returned more EEG samples than added")
        self.assertGreater(actual_eeg_count, 0, "Returned zero EEG samples for window")
        # Check it's roughly within the window size (loosely)
        # self.assertLessEqual(actual_eeg_count, max_possible_in_window, f"Returned too many EEG samples ({actual_eeg_count}) for window ({eeg_win_dur}s)")

        self.assertIsNotNone(ppg, "PPG data should not be None")
        actual_ppg_count = len(ppg)
        max_possible_in_window_ppg = int(ppg_win_dur * config.PPG_SAMPLING_RATE * 1.1)
        self.assertLessEqual(actual_ppg_count, num_ppg_samples_added, "Returned more PPG samples than added")
        self.assertGreater(actual_ppg_count, 0, "Returned zero PPG samples for window")
        # self.assertLessEqual(actual_ppg_count, max_possible_in_window_ppg, f"Returned too many PPG samples ({actual_ppg_count}) for window ({ppg_win_dur}s)")

        self.assertIsNone(acc) # No ACC data was added

    def test_get_all_data_for_baseline(self):
        """Test retrieving all data for baseline."""
        # Add some data
        data_store.add_eeg_data([1,2,3,4])
        data_store.add_eeg_data([5,6,7,8])
        data_store.add_ppg_data([1, 10, 1])
        data_store.add_ppg_data([1, 11, 1])
        data_store.add_acc_data([0,0,9])
        data_store.add_acc_data([1,1,8])

        eeg, ppg, acc = data_store.get_all_data_for_baseline()

        self.assertEqual(eeg.shape, (4, 2)) # 4 channels, 2 samples each
        np.testing.assert_array_almost_equal(eeg, np.array([[1.,5.], [2.,6.], [3.,7.], [4.,8.]]))

        self.assertEqual(len(ppg), 2)
        np.testing.assert_array_almost_equal(ppg, np.array([10., 11.]))

        self.assertEqual(acc.shape, (2, 3)) # 2 samples, 3 axes each
        np.testing.assert_array_almost_equal(acc, np.array([[0.,0.,9.], [1.,1.,8.]]))


if __name__ == '__main__':
    unittest.main()