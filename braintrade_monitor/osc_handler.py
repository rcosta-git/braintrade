import logging
import threading
from pythonosc import dispatcher, osc_server

# Import data store functions from within the package
from . import data_store
from . import config # May need config for NUM_EEG_CHANNELS if not passed

# --- OSC Message Handlers ---
# These functions are called by the dispatcher when an OSC message arrives.
# They use functions from data_store to add the received data.

def handle_eeg(address, *args):
    """Handles incoming /eeg OSC messages."""
    # logging.debug(f"OSC Handler: Received /eeg message with {len(args)} args.") # DEBUG LOG - Commented out for less verbosity
    # No need for global or lock here, data_store handles it
    # logging.debug(f"Received EEG: {args}") # Optional debug
    data_store.add_eeg_data(args)

def handle_ppg(address, *args):
    """Handles incoming /ppg OSC messages."""
    # logging.debug(f"Received PPG: {args}") # Optional debug
    data_store.add_ppg_data(args)

def handle_acc(address, *args):
    """Handles incoming /acc OSC messages."""
    # logging.debug(f"Received ACC: {args}") # Optional debug
    data_store.add_acc_data(args)

def handle_default(address, *args):
    """Handles any other incoming OSC messages."""
    # Log unexpected messages at INFO level to ensure visibility
    logging.info(f"Received unhandled OSC message - Address: {address}, Arguments: {args}")
    # pass # No longer needed as logging performs an action

# --- OSC Server Setup ---

def _server_thread_target(server):
    """Target function for the OSC server thread with error logging."""
    # This is intended to run in a background thread.
    try:
        logging.info(f"OSC server thread started on {server.server_address}.")
        server.serve_forever()
    except Exception as e:
        # Log exceptions that occur during serve_forever
        logging.exception(f"OSC Server thread encountered an error: {e}")
    finally:
        # Log when the server thread is stopping
        logging.info("OSC Server thread exiting.")

def start_osc_server(ip="0.0.0.0", port=5001):
    """
    Sets up and starts the OSC server in a background thread.

    Args:
        ip (str): The IP address to listen on.
        port (int): The port to listen on.

    Returns:
        tuple: (osc_server.ThreadingOSCUDPServer instance, threading.Thread instance) or (None, None) on failure.
    """
    disp = dispatcher.Dispatcher()

    # Map OSC addresses to handler functions
    disp.map("/eeg", handle_eeg)
    disp.map("/ppg", handle_ppg)
    disp.map("/acc", handle_acc)
    # You can add more mappings here for other OSC messages if needed
    # e.g., disp.map("/muse/elements/jaw_clench", handle_jaw_clench)

    disp.set_default_handler(handle_default) # Catch-all for unmapped addresses

    try:
        # Create the OSC server instance
        server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
        logging.info(f"OSC Server configured to listen on {server.server_address}")

        # Create and start the server thread
        # Pass the server instance to the target function
        thread = threading.Thread(target=_server_thread_target, args=(server,), daemon=True, name="OSCServerThread")
        thread.start()

        # Return the server and thread instances so they can be managed (e.g., shutdown)
        return server, thread
    except OSError as e:
        # Log specific errors related to binding the socket (e.g., address already in use)
        logging.error(f"Failed to start OSC server on {ip}:{port} - {e}")
        return None, None
    except Exception as e:
        # Log any other unexpected errors during setup
        logging.exception(f"An unexpected error occurred during OSC server setup: {e}")
        return None, None

# Example usage (for testing this module directly, if needed)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    # Need to initialize data store for handlers to work
    # This requires buffer sizes, which might come from config or args in a real scenario
    # Using placeholder sizes for testing
    data_store.initialize_data_store(eeg_buffer_size=1000, ppg_buffer_size=500, acc_buffer_size=500)

    server, thread = start_osc_server()
    if server:
        print("OSC Server started for testing. Press Ctrl+C to exit.")
        try:
            # Keep the main thread alive, otherwise daemon threads exit
            while thread.is_alive():
                thread.join(timeout=1.0)
        except KeyboardInterrupt:
            print("Shutting down OSC server...")
            server.shutdown()
            print("Server shut down.")
    else:
        print("Failed to start OSC server for testing.")