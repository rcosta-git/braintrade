import time
import numpy as np
import logging
import collections
import queue  # For type hinting
import threading  # For Event type hinting

from . import config
from . import data_store
from . import feature_extraction
from . import state_logic
from .market_data import MarketDataHandler
from . import cv_handler
# Removed import from web_server


def processing_loop(
    update_queue: queue.Queue,
    stop_event: threading.Event,
    shared_state_dict: dict,  # Added shared state dict argument
    shared_state_lock_obj: threading.Lock  # Added shared state lock argument
):
    """
    Main loop for processing sensor data, calculating features, updating state,
    and sending results to the UI queue and shared state dict. Designed to run in a background thread.

    Args:
        update_queue (queue.Queue): Queue to send display data to the (old) UI.
        stop_event (threading.Event): Event to signal the loop to stop.
        shared_state_dict (dict): Dictionary for sharing state with the web server.
        shared_state_lock_obj (threading.Lock): Lock for accessing the shared state dict.
    """
    logging.info("Starting real-time processing loop...")

    # Initialize MarketDataHandler
    market_data_handler = MarketDataHandler()

    # Initialize state variables for the loop
    current_official_state = "Initializing"
    # Deque for storing recent tentative states for persistence logic
    tentative_state_history = collections.deque(maxlen=config.STATE_PERSISTENCE_UPDATES)

    # Get baseline metrics once before starting the loop
    final_baseline_metrics = data_store.get_baseline_metrics()
    if not final_baseline_metrics:
        logging.error("Processing loop: Failed to retrieve baseline metrics before starting. Exiting.")
        return  # Exit if baseline is missing
    logging.info(f"Processing loop: Using baseline metrics: {final_baseline_metrics}")

    try:  # Outer try block to catch early exceptions
        while not stop_event.is_set():
            # logging.debug("***ROO-DEBUG-CHECK*** Processing loop started iteration.")  # Commented out
            loop_start_time = time.time()
            processing_error = False  # Flag to track if errors occurred in this iteration

            try:  # Inner try block for main processing logic
                # 1. Get recent data and baseline metrics from data_store
                # 1. Get recent data from data_store (baseline already fetched)
                (time_since_last_eeg, time_since_last_ppg, time_since_last_acc,
                 recent_eeg_data, recent_ppg_data, recent_acc_data
                 ) = data_store.get_data_for_processing(
                     config.EEG_WINDOW_DURATION, config.PPG_WINDOW_DURATION, 3.0  # Placeholder ACC window
                 )

                # Update market data
                market_data_handler.update_market_data()
                current_trend = market_data_handler.get_trend()
                current_time = time.time()
                # logging.debug("Processing loop: Data retrieved from store.") # Commented out

                # 2. Check for stale data
                if time_since_last_eeg > config.STALE_DATA_THRESHOLD or \
                   time_since_last_ppg > config.STALE_DATA_THRESHOLD:
                    # Update state directly to Stale if it wasn't already
                    if current_official_state != "Uncertain (Stale Data)":
                         logging.warning(f"Stale data detected. Last EEG: {time_since_last_eeg:.1f}s, Last PPG: {time_since_last_ppg:.1f}s. Setting state to Uncertain.")
                         current_official_state = "Uncertain (Stale Data)"
                         # Clear history when becoming uncertain due to stale data
                         tentative_state_history.clear()

                    # Update shared state for web server
                    with shared_state_lock_obj:
                        shared_state_dict["timestamp"] = time.time()
                        shared_state_dict["last_osc_timestamp"] = current_time
                        shared_state_dict["overall_state"] = current_official_state
                        shared_state_dict["alpha_beta_ratio"] = None
                        shared_state_dict["heart_rate"] = None
                        shared_state_dict["expression_dict"] = None
                        shared_state_dict["movement_metric"] = None
                        shared_state_dict["theta_power"] = None
                        shared_state_dict["market_trend"] = current_trend
                        # logging.debug("Shared state updated with STALE status.") # Commented out

                    # Send stale state to UI (existing Tkinter queue)
                    update_data = {"state": current_official_state, "ratio": np.nan, "hr": np.nan, "expression": "N/A", "movement": "N/A"}
                    # logging.debug("Processing loop: Stale data check complete (Data was stale).") # Commented out

                else:
                    # logging.debug("Processing loop: Stale data check complete (Data is fresh).") # Commented out
                    # 3. Prepare data for feature extraction
                    eeg_data_array = np.array(recent_eeg_data) if recent_eeg_data and all(recent_eeg_data) else None
                    ppg_data_array = np.array(recent_ppg_data) if recent_ppg_data else None
                    # acc_data_array = np.array(recent_acc_data) if recent_acc_data else None # For later use
                    # logging.debug("Processing loop: Data prepared for feature extraction.") # Commented out

                    if eeg_data_array is None:
                        # logging.debug("Not enough recent EEG data for A/B ratio calculation.") # Commented out
                        pass # Keep structure
                    if ppg_data_array is None:
                        # logging.debug("Not enough recent PPG data for HR calculation.") # Commented out
                        pass # Keep structure

                    # 4. Calculate features
                    # Pass sampling rates from config
                    current_ratio, current_theta = feature_extraction.extract_alpha_beta_ratio(
                        eeg_data_array, config.EEG_SAMPLING_RATE
                    ) if eeg_data_array is not None else (np.nan, np.nan)
                    # logging.debug(f"Processing loop: Ratio/Theta calculated: {current_ratio}, {current_theta}") # Commented out

                    current_hr = feature_extraction.estimate_bpm_from_ppg(
                        ppg_data_array, config.PPG_SAMPLING_RATE
                    ) if ppg_data_array is not None else np.nan
                    # logging.debug(f"Processing loop: HR calculated: {current_hr}") # Commented out

                    # Calculate movement metric from recent_acc_data
                    current_movement = feature_extraction.get_movement_metric(
                        recent_acc_data
                    ) if recent_acc_data is not None else np.nan
                    # logging.debug(f"Processing loop: Movement calculated: {current_movement}") # Commented out

                    # Get expression from CV thread/process
                    current_expression = cv_handler.get_current_expression()
                    # logging.debug(f"Processing loop: Expression retrieved: {current_expression}") # Commented out

                    # --- Debugging State Logic Inputs ---
                    # Log features first, before checking baseline
                    # logging.debug(f"Features: ratio={current_ratio}, hr={current_hr}, theta={current_theta}, movement={current_movement}, expression={current_expression}") # Commented out

                    # Initialize bounds and flags to defaults
                    ratio_lower_bound, hr_upper_bound, movement_upper_bound, theta_upper_bound = np.nan, np.nan, np.nan, np.nan
                    is_ratio_low, is_hr_high, is_movement_high, is_theta_high = False, False, False, False

                    # Use the baseline fetched before the loop
                    if final_baseline_metrics:
                        # logging.debug(f"***ROO-DEBUG-CHECK*** Baseline Metrics: {final_baseline_metrics}") # Commented out

                        # Safely get baseline values, defaulting to NaN
                        # Safely get baseline values from the pre-fetched dictionary
                        ratio_median = final_baseline_metrics.get('ratio_median', np.nan)
                        ratio_std = final_baseline_metrics.get('ratio_std', np.nan)
                        hr_median = final_baseline_metrics.get('hr_median', np.nan)
                        hr_std = final_baseline_metrics.get('hr_std', np.nan)
                        movement_median = final_baseline_metrics.get('movement_median', np.nan)
                        movement_std = final_baseline_metrics.get('movement_std', np.nan)
                        theta_median = final_baseline_metrics.get('theta_median', np.nan)
                        theta_std = final_baseline_metrics.get('theta_std', np.nan)

                        # Calculate flags, checking for NaN bounds
                        is_ratio_low = current_ratio < ratio_lower_bound if not np.isnan(current_ratio) and not np.isnan(ratio_lower_bound) else False
                        is_hr_high = current_hr > hr_upper_bound if not np.isnan(current_hr) and not np.isnan(hr_upper_bound) else False
                        is_movement_high = current_movement > movement_upper_bound if not np.isnan(current_movement) and not np.isnan(movement_upper_bound) else False
                        is_theta_high = current_theta > theta_upper_bound if not np.isnan(current_theta) and not np.isnan(theta_upper_bound) else False

                        # logging.debug(f"Flags: is_ratio_low={is_ratio_low}, is_hr_high={is_hr_high}, is_movement_high={is_movement_high}, is_theta_high={is_theta_high}, expression={current_expression}") # Commented out
                    else:
                        # logging.debug("Baseline metrics not yet available for flag calculation.") # Commented out
                        pass # Keep structure
                    # --- End Debugging State Logic Inputs ---

                    # 5. Update stress state using persistence logic
                    # Pass shared_state_dict which contains both baseline metrics and market_trend
                    new_state, suggested_position, confidence_level = state_logic.update_stress_state(current_ratio, current_hr, current_expression, current_movement, current_theta,
                        shared_state_dict, current_official_state, tentative_state_history) # Removed current_trend, passed shared_state_dict
                    current_official_state = new_state # Update the loop's state variable for the next iteration's persistence check
                    # logging.debug(f"Processing loop: State updated: {current_official_state}") # Commented out - state is logged below

                    # Store suggestion data
                    data_store.set_suggestion_data(suggested_position, confidence_level)

                    # --- Update Shared State for Web Server ---
                    current_time = time.time()  # Use a consistent timestamp
                    with shared_state_lock_obj:
                        shared_state_dict["timestamp"] = current_time
                        shared_state_dict["overall_state"] = new_state # Use the state returned by state_logic
                        shared_state_dict["suggested_position"] = suggested_position
                        shared_state_dict["confidence_level"] = confidence_level
                        shared_state_dict["alpha_beta_ratio"] = current_ratio if not np.isnan(current_ratio) else None
                        shared_state_dict["heart_rate"] = current_hr if not np.isnan(current_hr) else None
                        shared_state_dict["expression_dict"] = current_expression if current_expression != "N/A" else None
                        shared_state_dict["movement_metric"] = current_movement if not np.isnan(current_movement) else None
                        shared_state_dict["theta_power"] = current_theta if not np.isnan(current_theta) else None
                        shared_state_dict["market_trend"] = current_trend
                        shared_state_dict["last_osc_timestamp"] = current_time # Add timestamp update for fresh data
                        # Add more detailed log
                        log_data = {k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in shared_state_dict.items()}
                        logging.debug(f"Processing Loop Update: {log_data}") # Changed to DEBUG
                    # --- End Update Shared State ---
                    logging.info("Processing loop iteration completed and shared state updated.") # Add INFO log here

                    # Prepare data for UI (existing Tkinter queue)
                    update_data = {
                        "state": current_official_state,
                        "ratio": current_ratio,
                        "hr": current_hr,
                        "expression": current_expression,
                        "movement": current_movement,
                        "theta": current_theta
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

    except Exception as e:
        logging.exception(f"***ROO-DEBUG-CHECK*** Unhandled exception in processing_loop: {e}")
    finally:
        logging.info("Processing loop stopped.")


if __name__ == '__main__':
    # Example usage/test (requires other components like data_store initialized)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    q = queue.Queue()
    stop = threading.Event()

    # Need to initialize data store and baseline for a meaningful test
    print("This module is not designed to be run directly without setting up data_store and baseline.")
    # Example: processing_loop(q, stop) # Would likely fail without setup