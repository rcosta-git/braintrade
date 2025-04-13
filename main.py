import argparse
import queue
import threading
import time
import logging
import sys

# Import modules from the package
from braintrade_monitor import (
    config,
    logging_setup,
    data_store,
    osc_handler,
    baseline,
    processing,
    cv_handler
)
# Import the UI module (assuming it's at the top level for now)
import dashboard_ui

def main():
    # 1. Setup Logging
    logging_setup.setup_logging()
    logging.info("BrainTrade Monitor starting...")

    # 2. Argument Parsing (using defaults from config, but allowing overrides)
    parser = argparse.ArgumentParser(description='BrainTrade Real-time Stress Monitor')
    # OSC Args
    parser.add_argument('--osc-ip', type=str, default="0.0.0.0", help='OSC server IP address')
    parser.add_argument('--osc-port', type=int, default=5001, help='OSC server port')
    # Timing Args
    parser.add_argument('--baseline-duration', type=int, default=config.BASELINE_DURATION,
                        help='Duration of baseline calculation (seconds)')
    # Add other arguments if needed to override config values (e.g., thresholds)
    parser.add_argument('--acc-buffer-size', type=int, default=500, help='Size of the accelerometer data buffer')
    # parser.add_argument('--ratio-threshold', type=float, default=config.RATIO_THRESHOLD, ...)

    args = parser.parse_args()
    logging.info(f"Arguments parsed: {args}")

    # 3. Initialize Data Store (Calculate buffer sizes based on config/args)
    # Add some buffer beyond baseline duration
    buffer_safety_margin = 15 # seconds
    eeg_buffer_size = int(config.EEG_SAMPLING_RATE * (args.baseline_duration + buffer_safety_margin))
    ppg_buffer_size = int(config.PPG_SAMPLING_RATE * (args.baseline_duration + buffer_safety_margin))
    # acc_buffer_size = int(50 * (args.baseline_duration + buffer_safety_margin)) # Assuming 50Hz for ACC buffer size
    data_store.initialize_data_store(
        eeg_buffer_size=eeg_buffer_size,
        ppg_buffer_size=ppg_buffer_size,
        acc_buffer_size=args.acc_buffer_size,
        num_eeg_channels=config.NUM_EEG_CHANNELS
    )

    # 4. Initialize UI Queue
    update_queue = queue.Queue(maxsize=100) # Add maxsize to prevent unbounded growth

    # 5. Start OSC Server Thread
    logging.info(f"Starting OSC server on {args.osc_ip}:{args.osc_port}...")
    osc_server_instance, osc_thread = osc_handler.start_osc_server(args.osc_ip, args.osc_port)
    if osc_server_instance is None or not osc_thread.is_alive():
        logging.error("Failed to start OSC server. Exiting.")
        sys.exit(1) # Exit if server fails

    # 6. Calculate Baseline
    logging.info("Starting baseline calculation with ACC...")
    if not baseline.calculate_baseline(args.baseline_duration):
        logging.error("Baseline calculation failed. Exiting.")
        osc_server_instance.shutdown() # Attempt clean shutdown
        sys.exit(1) # Exit if baseline fails
    logging.info("Baseline calculation successful.")

    # 7. Start Computer Vision Thread
    logging.info("Starting computer vision processing...")
    cv_handler.start_cv_processing()

    # 9. Start Processing Thread
    logging.info("Starting data processing thread...")
    stop_processing_event = threading.Event()
    processing_thread = threading.Thread(
        target=processing.processing_loop,
        args=(update_queue, stop_processing_event), # Pass stop event
        daemon=True, # Daemon thread exits if main thread exits
        name="ProcessingThread"
    )
    processing_thread.start()

    # 8. Start UI on the Main Thread (this blocks until UI window is closed)
    logging.info("Starting UI on main thread...")
    ui_crashed = False
    try:
        # Pass the queue to the UI starter function
        dashboard_ui.start_ui(update_queue)
        # If start_ui returns normally, it means the UI window was closed by the user
        logging.info("UI window closed by user.")
    except Exception as e:
        logging.exception(f"UI encountered an error: {e}")
        ui_crashed = True
    finally:
        # --- Cleanup ---
        logging.info("Initiating shutdown sequence...")

        # Signal the processing thread to stop
        logging.info("Signaling processing thread to stop...")
        stop_processing_event.set()

        # Shutdown OSC server
        logging.info("Shutting down OSC server...")
        if osc_server_instance:
            osc_server_instance.shutdown() # Request shutdown
            # Wait briefly for the OSC server thread to exit
            if osc_thread and osc_thread.is_alive():
                 osc_thread.join(timeout=2.0)
                 if osc_thread.is_alive():
                      logging.warning("OSC server thread did not exit cleanly.")

        # Wait briefly for the processing thread to exit
        logging.info("Waiting for processing thread to stop...")
        if processing_thread and processing_thread.is_alive():
             processing_thread.join(timeout=2.0) # Wait max 2 seconds
             if processing_thread.is_alive():
                  logging.warning("Processing thread did not exit cleanly.")

        logging.info("BrainTrade Monitor shutdown complete.")
        # Exit with error code if UI crashed
        sys.exit(1 if ui_crashed else 0)


if __name__ == "__main__":
    main()