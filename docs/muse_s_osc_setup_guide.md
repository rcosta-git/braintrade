# Setup Guide: Connecting to Muse S via OSC using Muse Direct and Python

## Introduction

This guide explains how to set up a connection to a Muse S headband to receive its data within a Python script using the **Open Sound Control (OSC)** protocol, facilitated by the **Muse Direct** mobile application.

**Important Distinction:** This method relies on the Muse Direct app (running on a phone or tablet) to connect to the Muse S via Bluetooth and then stream the data over your local Wi-Fi network via OSC/UDP packets. Your Python script then acts as an **OSC server**, listening for these packets. This is the approach used in the `eeg_visualizer.py` example within this project.

This is different from connecting *directly* to the Muse S from your Python script using Bluetooth and a library like **BrainFlow**. The BrainFlow method bypasses the need for the Muse Direct app as an intermediary for data streaming but requires handling the Bluetooth connection and data acquisition directly in your Python code using the BrainFlow API. This guide focuses *only* on the OSC/Muse Direct method.

## Prerequisites

*   **Hardware:**
    *   Muse S Headband
    *   Smartphone or Tablet (iOS or Android) capable of running Muse Direct
    *   Computer (Mac, Windows, or Linux)
    *   Wi-Fi Network (Both the phone/tablet and the computer must be connected to the same network)
*   **Software:**
    *   **Muse Direct App:** Installed on your smartphone/tablet (available from app stores).
    *   **Python:** Version 3.x installed on your computer.
    *   **python-osc library:** Install using pip: `pip install python-osc`

## Step 1: Configure Muse Direct App

1.  **Install Muse Direct:** Download and install the Muse Direct application from the relevant app store onto your phone or tablet.
2.  **Connect Muse S:** Open Muse Direct and follow its instructions to connect to your Muse S headband via Bluetooth. Ensure the headband is charged and worn correctly.
3.  **Find Computer's IP Address:** You need the *local IP address* of the computer that will run the Python OSC server script. Both devices must be on the same Wi-Fi network.
    *   **macOS:** Go to System Settings > Network > Wi-Fi > Details... > TCP/IP. Look for the IPv4 Address. Or open Terminal and type `ipconfig getifaddr en0` (or `en1` depending on your Wi-Fi interface).
    *   **Windows:** Open Command Prompt (cmd) and type `ipconfig`. Look for the "IPv4 Address" under your active Wi-Fi adapter.
    *   **Linux:** Open a terminal and type `ip addr show` or `ifconfig`. Look for the `inet` address associated with your Wi-Fi interface (e.g., `wlan0`, `wlpXsY`).
4.  **Configure OSC Streaming in Muse Direct:**
    *   In the Muse Direct app, navigate to the streaming settings section.
    *   Enable OSC streaming.
    *   Set the **Target IP Address** to the local IP address of your computer (found in the previous step).
    *   Set the **Target Port**. A common choice is `5001`, but ensure it matches the port your Python script will listen on.
    *   Select the specific data streams you want to send (e.g., EEG, Accelerometer, Band Powers, Gyroscope, Headband Status). The Python script will need handlers for the corresponding OSC addresses. Common addresses include:
        *   `/muse/eeg` or `/eeg`
        *   `/muse/acc` or `/acc`
        *   `/muse/elements/delta_absolute`, `.../theta_absolute`, etc.
        *   `/muse/gyro`
        *   `/muse/elements/horseshoe` or `/hsi`
        *   `/muse/elements/is_good`

## Step 2: Implement Python OSC Server

Your Python script needs to listen for the incoming OSC messages sent by Muse Direct. Here's a basic structure based on `eeg_visualizer.py`:

```python
import argparse
import time
import threading
from pythonosc import dispatcher, osc_server
# Add other necessary imports (e.g., collections, numpy for data handling)

# --- Data Storage (Example: Use thread-safe structures) ---
# from collections import deque, defaultdict
# lock = threading.Lock()
# eeg_data = [deque(maxlen=256) for _ in range(4)] # Example for 4 EEG channels
# latest_acc = deque(maxlen=1)
# ---

# --- OSC Message Handlers ---
# Define functions to handle incoming data for each OSC address
# The first argument is the address, subsequent args are the data values

def handle_eeg(address, *args):
    # Example: Process EEG data (args[0]..args[3] for TP9, AF7, AF8, TP10)
    # with lock:
    #     if len(args) >= 4:
    #         for i in range(4):
    #             eeg_data[i].append(float(args[i]))
    print(f"Received EEG: {args}")
    pass # Replace with your actual data processing

def handle_acc(address, *args):
    # Example: Process Accelerometer data
    # with lock:
    #     latest_acc.clear()
    #     latest_acc.append(list(args))
    print(f"Received Accelerometer: {args}")
    pass # Replace with your actual data processing

def handle_default(address, *args):
    # Handler for any OSC address not explicitly mapped
    print(f"Received unhandled OSC message: {address} {args}")
    pass

# --- OSC Server Setup ---
def start_osc_server(ip, port):
    disp = dispatcher.Dispatcher()

    # Map OSC addresses to handler functions
    # Map addresses used by Muse Direct (check its settings or documentation)
    disp.map("/muse/eeg", handle_eeg)
    disp.map("/eeg", handle_eeg) # Map alternative if needed
    disp.map("/muse/acc", handle_acc)
    disp.map("/acc", handle_acc) # Map alternative if needed
    # Add mappings for all other data streams you enabled in Muse Direct
    # e.g., disp.map("/muse/elements/alpha_absolute", handle_band_power)

    # Set a default handler for unmapped messages
    disp.set_default_handler(handle_default)

    # Start the OSC server in a separate thread
    # Use "0.0.0.0" to listen on all available network interfaces on the computer
    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"OSC Server listening on {server.server_address}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type=str, default="0.0.0.0", help='IP address to listen on')
    parser.add_argument('--port', type=int, default=5001, help='UDP port to listen on')
    args = parser.parse_args()

    osc_server_instance, osc_thread = start_osc_server(args.ip, args.port)

    try:
        # Your main application logic here
        # This loop can now access the data stored by the handlers
        while True:
            # Example: Retrieve and print latest accelerometer data
            # with lock:
            #     if latest_acc:
            #         current_acc = latest_acc[0]
            #     else:
            #         current_acc = None
            # if current_acc:
            #     print(f"Latest Acc: {current_acc}")

            print("Main loop running...") # Placeholder
            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down OSC server...")
        osc_server_instance.shutdown()
        # osc_thread.join() # Optional: wait for thread to finish
        print("Server stopped.")

```

**Key points for the Python script:**

*   **IP Address (`--ip`):** Use `0.0.0.0` to make the server listen on all network interfaces of your computer. This is usually the easiest setting.
*   **Port (`--port`):** Must match the **Target Port** set in the Muse Direct app (e.g., `5001`).
*   **Dispatcher Mapping:** You *must* map the exact OSC addresses being sent by Muse Direct to your handler functions. Check the Muse Direct settings or documentation for the correct addresses for the data you selected.
*   **Threading:** Running the OSC server in a separate thread (`ThreadingOSCUDPServer` and `threading.Thread`) prevents it from blocking your main application logic.
*   **Data Handling:** Use thread-safe mechanisms (like `threading.Lock` with `collections.deque` or `queue.Queue`) if your main loop needs to access data written by the OSC handlers concurrently.

## Step 3: Running the Setup

1.  **Start Python Server:** Run your Python OSC server script from the terminal on your computer (e.g., `python your_script_name.py --port 5001`). Note the IP address and port it reports listening on.
2.  **Start Muse Direct Streaming:** Open the Muse Direct app on your phone/tablet, ensure it's connected to the Muse S, and start the OSC stream, making sure the target IP and port match the running Python script.
3.  **Verify Data Reception:** Check the terminal output of your Python script. You should see messages indicating received OSC data if the connection is successful.

## Troubleshooting & Key Points

*   **Same Wi-Fi Network:** Crucial. Both the phone/tablet running Muse Direct and the computer running the Python script *must* be connected to the same Wi-Fi network.
*   **IP Address Accuracy:** Double-check that the Target IP address in Muse Direct exactly matches the local IP address of the computer running the script.
*   **Port Matching:** Ensure the Target Port in Muse Direct matches the port the Python script is listening on.
*   **Firewall:** Your computer's firewall might block incoming UDP packets on the specified port. You may need to create a firewall rule to allow incoming traffic on that UDP port for your Python application or runtime.
*   **OSC Address Mismatch:** If data seems missing, verify that the OSC addresses mapped in your Python script (`disp.map(...)`) exactly match the addresses being sent by Muse Direct for the selected data streams. Use the `handle_default` function to catch unmapped addresses.

## Data Flow Summary

Muse S Headband `--(Bluetooth)-->` Muse Direct App (Phone/Tablet) `--(OSC/UDP over Wi-Fi)-->` Python Script (Computer acting as OSC Server)