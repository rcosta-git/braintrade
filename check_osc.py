import argparse
import time
from pythonosc import dispatcher, osc_server
import threading

def print_message(address, *args):
    """Prints any received OSC message."""
    print(f"Received OSC: Address={address}, Arguments={args}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type=str, default="0.0.0.0", 
                        help='IP address to listen on (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5001, 
                        help='UDP port to listen on (default: 5001)')
    args = parser.parse_args()

    # Setup dispatcher to catch all messages
    disp = dispatcher.Dispatcher()
    # Use set_default_handler to print any message regardless of address
    disp.set_default_handler(print_message) 

    # Start the OSC server in a separate thread
    server = osc_server.ThreadingOSCUDPServer((args.ip, args.port), disp)
    print(f"OSC Listener started on {server.server_address}")
    print("Waiting for OSC messages... Press Ctrl+C to stop.")
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Keep the main thread alive while the server runs in the background
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping OSC listener...")
        server.shutdown()
        print("Listener stopped.")

if __name__ == "__main__":
    main()