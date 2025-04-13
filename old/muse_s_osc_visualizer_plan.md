# Plan: Modify `eeg_visualizer.py` for Muse S OSC Data Reception and Terminal Visualization

This plan outlines the steps taken to modify the existing `eeg_visualizer.py` script to receive and visualize data streamed from a Muse S device via the Muse mobile app using the Open Sound Control (OSC) protocol over UDP, displaying the output directly in the terminal.

**Final Handled OSC Data & Visualization:**

*   **Raw EEG:** Received via `/eeg` (or `/muse/eeg`). Visualized as downsampled line plots (4 channels in a 2x2 grid) using `plotext`.
*   **Absolute Band Powers:** Extracted from indices 8-12 of the `/muse_metrics` message. Visualized as colored bar charts (Delta, Theta, Alpha, Beta, Gamma) using `plotext`.
*   **Accelerometer:** Received via `/acc` (or `/muse/acc`). Data is stored but not currently visualized.
*   **Other Metrics:** `/muse_metrics`, `/headband_on`, `/hsi`, `/is_good` are received and stored but not currently visualized (except for band powers extracted from `/muse_metrics`).

**Steps Implemented:**

1.  **Add Dependencies:** Added `python-osc` and `plotext` to `requirements.txt`. Dependencies were installed using `pip install -r requirements.txt`.
2.  **Remove BrainFlow Connection:** Removed code related to `BrainFlowInputParams` and `BoardShim` initialization and session management.
3.  **Import Libraries:** Added necessary imports from `python_osc`, `plotext`, `threading`, `collections`, and `numpy`.
4.  **Implement OSC Server:**
    *   Created a `dispatcher` instance.
    *   Defined handler functions (`handle_eeg`, `handle_acc`, `handle_metrics`, `handle_headband_on`, `handle_hsi`, `handle_is_good`, `handle_band_power`, `handle_default`).
    *   Mapped observed OSC addresses (`/eeg`, `/acc`, `/muse_metrics`, etc.) and original Muse Lab addresses (`/muse/eeg`, etc.) to handlers.
    *   Instantiated and started a `ThreadingOSCUDPServer` on IP `0.0.0.0`, port `5001` in a separate thread.
5.  **Adapt Data Handling & Storage:**
    *   Used thread-safe `deque` structures (protected by a `threading.Lock`) for storing:
        *   A history (~1 second) of EEG samples for each of the 4 channels.
        *   The latest values for accelerometer, `/muse_metrics`, headband status, HSI, and 'is good' signals.
        *   Band power values derived from `/muse_metrics` (indices 8-12) or received directly via `/muse/elements/*_absolute`.
    *   Modified the main loop to read the latest data from these shared structures.
6.  **Update Terminal Visualization (using `plotext`):**
    *   Cleared the terminal and plot data on each update cycle.
    *   Displayed downsampled EEG data (plotting every 10th point from the history) as line plots in a 2x2 grid with distinct colors.
    *   Displayed absolute band powers (derived from `/muse_metrics`) as colored horizontal bar charts.
    *   Removed accelerometer and metrics 24/29 display for clarity.
7.  **Cleanup:** Ensured the OSC server thread is properly shut down on `KeyboardInterrupt` (Ctrl+C).

**Conceptual Diagram:**

See [Muse S OSC Flow Diagram](./muse_s_osc_flow_diagram.md) for a visualization of the data flow.