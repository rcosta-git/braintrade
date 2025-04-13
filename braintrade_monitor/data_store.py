import threading
import collections
import time
import numpy as np
import logging

# The single lock for all shared data access
_data_lock = threading.Lock()

# Shared data structures (initialized later via initialize_data_store)
_eeg_data_buffers = None
_ppg_data_buffer = None
_acc_data_buffer = None
_baseline_metrics = {}
_last_eeg_timestamp = 0
_last_ppg_timestamp = 0
_last_acc_timestamp = 0
_num_eeg_channels = 4 # Default, can be overridden during init

# --- Initialization ---

def initialize_data_store(eeg_buffer_size, ppg_buffer_size, acc_buffer_size, num_eeg_channels=4):
    """Initializes or resets the shared data structures."""
    global _eeg_data_buffers, _ppg_data_buffer, _acc_data_buffer, _num_eeg_channels
    global _last_eeg_timestamp, _last_ppg_timestamp, _last_acc_timestamp
    logging.info(f"Initializing data store: EEG({num_eeg_channels}ch, size={eeg_buffer_size}), PPG(size={ppg_buffer_size}), ACC(size={acc_buffer_size})")
    with _data_lock:
        _num_eeg_channels = num_eeg_channels
        _eeg_data_buffers = [collections.deque(maxlen=eeg_buffer_size) for _ in range(_num_eeg_channels)]
        _ppg_data_buffer = collections.deque(maxlen=ppg_buffer_size)
        _acc_data_buffer = collections.deque(maxlen=acc_buffer_size)
        _baseline_metrics = {}
        _last_eeg_timestamp = 0
        _last_ppg_timestamp = 0
        _last_acc_timestamp = 0

# --- Data Addition Functions (Called by OSC Handlers) ---

def add_eeg_data(eeg_sample):
    """Adds a new EEG sample tuple (timestamp, value) for each channel."""
    global _last_eeg_timestamp
    ts = time.time()
    with _data_lock:
        # logging.debug(f"Data Store: Attempting to add EEG sample. Buffer exists: {_eeg_data_buffers is not None}, Sample len: {len(eeg_sample)}, Expected channels: {_num_eeg_channels}") # DEBUG LOG - Commented out for less verbosity
        if _eeg_data_buffers is not None and len(eeg_sample) >= _num_eeg_channels:
            try:
                for i in range(_num_eeg_channels):
                    _eeg_data_buffers[i].append((ts, float(eeg_sample[i])))
                _last_eeg_timestamp = ts
            except (ValueError, TypeError, IndexError) as e:
                 logging.error(f"Error processing EEG sample in data_store: {e} - Sample: {eeg_sample}")
        elif _eeg_data_buffers is None:
            logging.warning("EEG data store not initialized, discarding sample.")
        else:
            logging.warning(f"Mismatch EEG channels. Expected {_num_eeg_channels}, got {len(eeg_sample)}. Discarding.")


def add_ppg_data(ppg_sample):
    """Adds a new PPG sample tuple (timestamp, value). Expects (sensor_id, value, sensor_id)."""
    global _last_ppg_timestamp
    ts = time.time()
    with _data_lock:
        if _ppg_data_buffer is not None and len(ppg_sample) >= 2: # Check length
             try:
                 ppg_value = float(ppg_sample[1]) # Extract the middle PPG value
                 _ppg_data_buffer.append((ts, ppg_value))
                 _last_ppg_timestamp = ts
             except (ValueError, TypeError, IndexError) as e:
                 logging.error(f"Error processing PPG sample in data_store: {e} - Sample: {ppg_sample}")
        elif _ppg_data_buffer is None:
             logging.warning("PPG data store not initialized, discarding sample.")
        else:
             logging.warning(f"Incorrect PPG sample format. Expected >= 2 elements, got {len(ppg_sample)}. Discarding.")


def add_acc_data(acc_sample):
    """Adds a new ACC sample tuple (timestamp, (x, y, z))."""
    global _last_acc_timestamp
    ts = time.time()
    with _data_lock:
        if _acc_data_buffer is not None and len(acc_sample) == 3:
            try:
                acc_tuple = tuple(map(float, acc_sample))
                _acc_data_buffer.append((ts, acc_tuple))
                _last_acc_timestamp = ts
            except (ValueError, TypeError) as e:
                logging.error(f"Error processing ACC sample in data_store: {e} - Sample: {acc_sample}")
        elif _acc_data_buffer is None:
             logging.warning("ACC data store not initialized, discarding sample.")
        else:
             logging.warning(f"Incorrect ACC sample format. Expected 3 elements, got {len(acc_sample)}. Discarding.")


# --- Data Retrieval Functions (Called by Processing Loop / Baseline) ---

def get_data_for_processing(eeg_window_duration, ppg_window_duration, acc_window_duration):
    """Retrieves recent data windows and timestamps for the processing loop."""
    now = time.time()
    eeg_window_start_time = now - eeg_window_duration
    ppg_window_start_time = now - ppg_window_duration
    acc_window_start_time = now - acc_window_duration

    logging.debug("get_data_for_processing: Attempting to acquire lock...")
    with _data_lock:
        logging.debug("get_data_for_processing: Lock acquired.")
        # Make copies under the lock to minimize lock holding time
        time_since_last_eeg = now - _last_eeg_timestamp if _last_eeg_timestamp > 0 else float('inf')
        time_since_last_ppg = now - _last_ppg_timestamp if _last_ppg_timestamp > 0 else float('inf')
        time_since_last_acc = now - _last_acc_timestamp if _last_acc_timestamp > 0 else float('inf')

        if _eeg_data_buffers:
            # Ensure list comprehension handles potential empty buffers gracefully
            recent_eeg_data = [
                [item[1] for item in buf if item[0] >= eeg_window_start_time]
                for buf in _eeg_data_buffers
            ]
            # Check if all channels have data after filtering by time
            if not all(recent_eeg_data): recent_eeg_data = None
        else:
            recent_eeg_data = None

        if _ppg_data_buffer:
            recent_ppg_data = [item[1] for item in _ppg_data_buffer if item[0] >= ppg_window_start_time]
            if not recent_ppg_data: recent_ppg_data = None # Ensure None if empty after filtering
        else:
            recent_ppg_data = None

        if _acc_data_buffer:
             recent_acc_data = [item[1] for item in _acc_data_buffer if item[0] >= acc_window_start_time]
             if not recent_acc_data: recent_acc_data = None # Ensure None if empty after filtering
        else:
             recent_acc_data = None

        # Copy baseline metrics
        current_baseline_metrics = _baseline_metrics.copy()
        logging.debug(f"get_data_for_processing: EEG bufs exist={_eeg_data_buffers is not None}, PPG buf exists={_ppg_data_buffer is not None}, ACC buf exists={_acc_data_buffer is not None}")
        logging.debug(f"get_data_for_processing: Baseline metrics copied: {current_baseline_metrics}")

    # Log lengths before returning
    logging.debug(f"get_data_for_processing: Returning EEG len={len(recent_eeg_data[0]) if recent_eeg_data else 'None'}, PPG len={len(recent_ppg_data) if recent_ppg_data else 'None'}, ACC len={len(recent_acc_data) if recent_acc_data else 'None'}")

    # Return copies of data and timestamps
    return (time_since_last_eeg, time_since_last_ppg, time_since_last_acc,
            recent_eeg_data, recent_ppg_data, recent_acc_data, # Note: recent_eeg_data is list of lists here
            current_baseline_metrics)
    logging.debug("get_data_for_processing: Lock released.")

def get_all_data_for_baseline():
    """Retrieves all currently buffered data (values only) for baseline calculation."""
    with _data_lock:
        if _eeg_data_buffers:
             eeg_baseline_data = np.array([ [item[1] for item in buf] for buf in _eeg_data_buffers])
        else:
             eeg_baseline_data = np.array([[] for _ in range(_num_eeg_channels)]) # Empty array with correct channel dim

        if _ppg_data_buffer:
             ppg_baseline_data = np.array([item[1] for item in _ppg_data_buffer])
        else:
             ppg_baseline_data = np.array([])

        if _acc_data_buffer: # Add ACC retrieval for baseline if needed later
             acc_baseline_data = np.array([item[1] for item in _acc_data_buffer])
        else:
             acc_baseline_data = np.array([])

    return eeg_baseline_data, ppg_baseline_data, acc_baseline_data


# --- Baseline Metrics Functions ---

def set_baseline_metrics(metrics_dict):
    """Updates the stored baseline metrics."""
    with _data_lock:
        _baseline_metrics.update(metrics_dict)
        logging.info(f"Data Store: Baseline metrics updated: {metrics_dict}")

def get_baseline_metrics():
    """Returns a copy of the current baseline metrics."""
    with _data_lock:
        return _baseline_metrics.copy()

# --- Utility ---
def check_buffers_initialized():
    """Checks if data buffers have been initialized."""
    with _data_lock:
        return _eeg_data_buffers is not None and _ppg_data_buffer is not None and _acc_data_buffer is not None

# --- Timestamp Getters ---
def get_last_timestamps():
    """Returns the last received timestamps for all data types."""
    with _data_lock:
        return {
            "eeg": _last_eeg_timestamp,
            "ppg": _last_ppg_timestamp,
            "acc": _last_acc_timestamp
        }