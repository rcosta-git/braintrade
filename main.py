import argparse
import queue
import threading
import time
import logging
import sys
import multiprocessing
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# Import the API endpoint function from web_server
from web_server import get_state as api_get_state
# REMOVED: shared_state_module import

# REMOVED old UI import
# import dashboard_ui

# Function to run the API server in a separate process
def run_api_server(shared_dict, shared_lock):
    app = FastAPI()

    # Configure CORS
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080", # Added from previous debugging
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define the endpoint, using the passed managed dict/lock
    @app.get("/api/state")
    async def main_get_state():
        # Pass the managed objects to the imported function
        return await api_get_state(shared_dict, shared_lock)

    # Run Uvicorn
    # Note: log_level='info' might be noisy, consider 'warning'
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')


def main():
    # 1. Setup Logging
    logging_setup.setup_logging()
    logging.debug("***ROO-DEBUG-CHECK*** Logging configured in main.") # Added debug check
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

    # 4. Initialize Shared State using multiprocessing Manager
    manager = multiprocessing.Manager()
    shared_manager_dict = manager.dict({
        "timestamp": time.time(),
        "system_phase": "Initializing",
        "overall_state": "Initializing",
        "alpha_beta_ratio": None,
        "heart_rate": None,
        "expression_dict": None,
        "movement_metric": None,
        "theta_power": None,
        "last_osc_timestamp": None,
        "suggested_position": None,
        "confidence_level": None,
        "market_trend": None,
    })
    shared_manager_lock = manager.Lock()
    logging.info("Multiprocessing managed state initialized.")

    # Initialize old UI Queue (might still be used by processing loop temporarily)
    update_queue = queue.Queue(maxsize=100)

    # 5. Start OSC Server Thread
    logging.info(f"Starting OSC server on {args.osc_ip}:{args.osc_port}...")
    osc_server_instance, osc_thread = osc_handler.start_osc_server(args.osc_ip, args.osc_port)
    if osc_server_instance is None or not osc_thread.is_alive():
        logging.error("Failed to start OSC server. Exiting.")
        sys.exit(1) # Exit if server fails

    # Give OSC server a moment to start receiving data
    # logging.info("Waiting briefly for OSC data to start arriving...")
    # time.sleep(1.0) # REMOVED delay - suspecting issue here or in OSC thread startup

    # 5.5 Start API Server Process using multiprocessing (Moved BEFORE baseline)
    logging.info("Starting API server process...")
    api_server_process = multiprocessing.Process(
        target=run_api_server,
        args=(shared_manager_dict, shared_manager_lock),
        daemon=True, # Daemon process exits if main process exits
        name="APIServerProcess"
    )
    api_server_process.start()
    # Give API server a moment to initialize
    time.sleep(2.0) # Add a small delay to ensure API server starts before baseline

    # 6. Calculate Baseline
    logging.info("Starting baseline calculation...")
    # Update shared state before baseline
    with shared_manager_lock:
        shared_manager_dict["system_phase"] = "Calculating Baseline"
        shared_manager_dict["timestamp"] = time.time()

    if not baseline.calculate_baseline(args.baseline_duration):
        logging.error("Baseline calculation failed. Exiting.")
        if osc_server_instance:
             osc_server_instance.shutdown() # Attempt clean shutdown
        sys.exit(1) # Exit if baseline fails

    # Update shared state after baseline
    with shared_manager_lock:
        shared_manager_dict["system_phase"] = "Monitoring"
        shared_manager_dict["timestamp"] = time.time()
    logging.info("Baseline calculation successful. Starting monitoring.")

    # 7. Start Computer Vision Thread
    logging.info("Starting computer vision processing...")
    cv_handler.start_cv_processing()

    # 9. Start Processing Thread
    logging.info("Starting data processing thread...")
    stop_processing_event = threading.Event()
    processing_thread = threading.Thread(
        target=processing.processing_loop,
        args=(
            update_queue,
            stop_processing_event,
            shared_manager_dict, # Pass managed dict
            shared_manager_lock # Pass managed lock
        ),
        daemon=True, # Daemon thread exits if main thread exits
        name="ProcessingThread"
    )
    processing_thread.start()

    # REMOVED: API Server start (moved before baseline)

    # 10. Keep Main Thread Alive & Handle Shutdown
    logging.info("Application started. Press Ctrl+C to stop.")
    try:
        while True:
            # Keep main thread alive, threads are doing the work
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Ctrl+C detected. Initiating shutdown sequence...")
    finally:
        # --- Cleanup ---
        logging.info("Signaling processing thread to stop...")
        stop_processing_event.set()

        # Shutdown OSC server
        logging.info("Shutting down OSC server...")
        if osc_server_instance:
            osc_server_instance.shutdown()
            if osc_thread and osc_thread.is_alive():
                 osc_thread.join(timeout=2.0)
                 if osc_thread.is_alive():
                      logging.warning("OSC server thread did not exit cleanly.")

        # Wait for processing thread
        logging.info("Waiting for processing thread to stop...")
        if processing_thread and processing_thread.is_alive():
             processing_thread.join(timeout=2.0)
             if processing_thread.is_alive():
                  logging.warning("Processing thread did not exit cleanly.")

        # Terminate API server process
        logging.info("Terminating API server process...")
        if api_server_process and api_server_process.is_alive():
            api_server_process.terminate() # Send SIGTERM
            api_server_process.join(timeout=2.0) # Wait briefly
            if api_server_process.is_alive():
                 logging.warning("API server process did not terminate cleanly.")
                 # Consider api_server_process.kill() if needed

        logging.info("BrainTrade Monitor shutdown complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()