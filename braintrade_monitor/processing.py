import time
import numpy as np
import logging
import collections
import queue # For type hinting
import threading # For Event type hinting

from . import config
from . import data_store
from . import feature_extraction
from . import state_logic
from . import cv_handler
def processing_loop(update_queue: queue.Queue, stop_event: threading.Event):
    """
    Main loop for processing sensor data, calculating features, updating state,
    and sending results to the UI queue. Designed to run in a background thread.

    Args:
        update_queue (queue.Queue): Queue to send display data to the UI.
        stop_event (threading.Event): Event to signal the loop to stop.
    """
    logging.info("Starting real-time processing loop...")

    # Initialize state variables for the loop
    current_official_state = "Initializing"
    # Deque for storing recent tentative states for persistence logic
    tentative_state_history = collections.deque(maxlen=config.STATE_PERSISTENCE_UPDATES)

    while not stop_event.is_set():
        loop_start_time = time.time()
        processing_error = False # Flag to track if errors occurred in this iteration

        try:
            # 1. Get recent data and baseline metrics from data_store
            (time_since_last_eeg, time_since_last_ppg, time_since_last_acc,
             recent_eeg_data, recent_ppg_data, recent_acc_data,
             current_baseline_metrics) = data_store.get_data_for_processing(
                 config.EEG_WINDOW_DURATION, config.PPG_WINDOW_DURATION, 3.0 # Placeholder ACC window
             )

            # 2. Check for stale data
            if time_since_last_eeg > config.STALE_DATA_THRESHOLD or \
               time_since_last_ppg > config.STALE_DATA_THRESHOLD:
                # Update state directly to Stale if it wasn't already
                if current_official_state != "Uncertain (Stale Data)":
                     logging.warning(f"Stale data detected. Last EEG: {time_since_last_eeg:.1f}s, Last PPG: {time_since_last_ppg:.1f}s. Setting state to Uncertain.")
                     current_official_state = "Uncertain (Stale Data)"
                     # Clear history when becoming uncertain due to stale data
                     tentative_state_history.clear()
                # Send stale state to UI
                update_data = {"state": current_official_state, "ratio": np.nan, "hr": np.nan, "expression": "N/A", "movement": "N/A"}

            else:
                # 3. Prepare data for feature extraction
                eeg_data_array = np.array(recent_eeg_data) if recent_eeg_data and all(recent_eeg_data) else None
                ppg_data_array = np.array(recent_ppg_data) if recent_ppg_data else None
                # acc_data_array = np.array(recent_acc_data) if recent_acc_data else None # For later use

                if eeg_data_array is None:
                    logging.debug("Not enough recent EEG data for A/B ratio calculation.")
                if ppg_data_array is None:
                    logging.debug("Not enough recent PPG data for HR calculation.")

                # 4. Calculate features
                # Pass sampling rates from config
                current_ratio = feature_extraction.extract_alpha_beta_ratio(
                    eeg_data_array, config.EEG_SAMPLING_RATE
                ) if eeg_data_array is not None else np.nan

                current_hr = feature_extraction.estimate_bpm_from_ppg(
                    ppg_data_array, config.PPG_SAMPLING_RATE
                ) if ppg_data_array is not None else np.nan

                # Calculate movement metric from recent_acc_data
                current_movement = feature_extraction.get_movement_metric(
                    recent_acc_data
                ) if recent_acc_data is not None else np.nan
                # Get expression from CV thread/process
                current_expression = cv_handler.get_current_expression()

                # 5. Update stress state using persistence logic
                current_official_state = state_logic.update_stress_state(
                    current_ratio, current_hr, current_expression, current_movement,
                    current_baseline_metrics, current_official_state, tentative_state_history
                )

                # Prepare data for UI
                update_data = {
                    "state": current_official_state,
                    "ratio": current_ratio,
                    "hr": current_hr,
                    "expression": current_expression, # Placeholder
                    "movement": current_movement
                }

            # 6. Send data to the UI queue
            try:
                update_queue.put_nowait(update_data)
            except queue.Full:
                logging.warning("UI update queue is full. Skipping update.")
                processing_error = True

        except Exception as e:
            logging.exception(f"Error in processing loop iteration: {e}")
            processing_error = True
            # Attempt to recover or wait before next iteration
            # Don't update UI queue on error

        # 7. Enforce loop timing
        loop_end_time = time.time()
        loop_duration = loop_end_time - loop_start_time
        # Add a small delay even if processing took longer, unless there was an error
        base_sleep = 0.01 if not processing_error else config.UPDATE_INTERVAL
        sleep_duration = max(base_sleep, config.UPDATE_INTERVAL - loop_duration)

        # Use stop_event.wait for sleeping, allows quicker exit if stop is signaled
        stop_event.wait(timeout=sleep_duration)

    logging.info("Processing loop stopped.")

if __name__ == '__main__':
    # Example usage/test (requires other components like data_store initialized)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    q = queue.Queue()
    stop = threading.Event()

    # Need to initialize data store and baseline for a meaningful test
    print("This module is not designed to be run directly without setting up data_store and baseline.")
    # Example: processing_loop(q, stop) # Would likely fail without setup