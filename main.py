import argparse
import queue
import threading
import time
import logging
import sys
import uvicorn # For running the API server
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
# Import the API endpoint function
from web_server import get_state as api_get_state

# REMOVED old UI import
# import dashboard_ui

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

    # 4. Initialize Shared State for Web Server
    shared_state = {
        "timestamp": None,
        "system_phase": "Initializing", # Add system phase
        "overall_state": "Initializing",
        "alpha_beta_ratio": None,
        "heart_rate": None,
        "expression_dict": None,
        "movement_metric": None,
        "theta_power": None,
    }
    shared_state_lock = threading.Lock()

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

    # 6. Calculate Baseline
    logging.info("Starting baseline calculation...")
    # Update shared state before baseline
    with shared_state_lock:
        shared_state["system_phase"] = "Calculating Baseline"
        shared_state["timestamp"] = time.time()

    if not baseline.calculate_baseline(args.baseline_duration):
        logging.error("Baseline calculation failed. Exiting.")
        if osc_server_instance:
             osc_server_instance.shutdown() # Attempt clean shutdown
        sys.exit(1) # Exit if baseline fails

    # Update shared state after baseline
    with shared_state_lock:
        shared_state["system_phase"] = "Monitoring"
        shared_state["timestamp"] = time.time()
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
            shared_state, # Pass shared state dict
            shared_state_lock # Pass shared state lock
        ),
        daemon=True, # Daemon thread exits if main thread exits
        name="ProcessingThread"
    )
    processing_thread.start()

    # 8. Setup FastAPI App and API Endpoint
    logging.info("Setting up FastAPI app...")
    app = FastAPI()

    # Configure CORS
    logging.info("Applying CORS middleware...") # Add log before middleware
    origins = [
        "http://localhost:5173", # Default Vite port
        "http://127.0.0.1:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define the endpoint, injecting shared state and lock
    @app.get("/api/state")
    async def main_get_state():
        # This wrapper calls the imported function, passing the state/lock from main's scope
        return await api_get_state(shared_state, shared_state_lock)

    # 9. Start API Server Thread
    logging.info("Starting API server thread...")
    api_server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={'app': app, 'host': '0.0.0.0', 'port': 8000, 'log_level': 'info'},
        daemon=True, # Daemon thread exits if main thread exits
        name="APIServerThread"
    )
    api_server_thread.start()

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

        # API server thread is daemon, should exit automatically, but good practice might involve more graceful shutdown if needed

        logging.info("BrainTrade Monitor shutdown complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()