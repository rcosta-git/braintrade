# BrainTrade - Mental State Monitor

This project aims to build a system using a Muse S headset (and potentially other inputs like computer vision) to monitor the mental state of a day trader in real-time. The goal is to detect suboptimal states (e.g., stress, fatigue, distraction) and provide feedback to help mitigate poor trading decisions.

This project is being developed incrementally as part of a hackathon.

## Approach

The system uses a multi-phase approach, starting with basic physiological indicators and progressively adding more complex features and analysis:

*   **Phase 1:** Simple Stress Meter (EEG Alpha/Beta Ratio + Estimated Heart Rate from PPG)
*   **Phase 2:** Enhanced Dashboard (Adds Computer Vision for Facial Expression + Accelerometer for Movement)
*   **Phase 3:** Focus/Fatigue Detection (Adds EEG Theta + Blink Detection)
*   **Phase 4:** Advanced Indicators (Explores HRV - Stretch Goal)
*   **Phase 5:** Web UI Migration (Future Enhancement)

See `docs/braintrade_monitor_plan.md` for the overall roadmap and individual `docs/phaseX_*.md` files for detailed plans.

## Current Status (Phase 2 In Progress)

Phase 1 is now complete. The core logic for the stress monitor is now refactored into the `braintrade_monitor` Python package. The main script is now `main.py`. The system performs real-time stress monitoring based on EEG Alpha/Beta ratio and PPG-derived heart rate, and displays a basic `tkinter` UI. Unit tests have been added for core modules.

*   **Modular Codebase:** Core logic refactored into the `braintrade_monitor` package for better organization and maintainability.
*   **Unit Tests:** Unit tests added for `feature_extraction`, `state_logic`, `data_store`, and `baseline` modules, ensuring core functionality is robust.
*   **Resolved Hanging Issue:** The issue causing the script to hang during baseline calculation has been resolved.
*   **Console Logging:** Logging is configured to output to both file and console, with configurable levels.
*   **OSC Data Reception:** Confirmed reception of EEG (`/eeg`) and PPG (`/ppg`) data from Muse Direct via OSC.
*   **Core Logic ( `braintrade_monitor` package):** Implements OSC data handling, baseline calculation, feature extraction, and state logic.
*   **UI Dashboard (`dashboard_ui.py`):** Basic `tkinter` UI displays state, A/B Ratio, and HR.

## Setup

1.  **Hardware:**
    *   Muse S Headband
    *   Smartphone/Tablet with Muse Direct app installed.
    *   Computer (Mac/Windows/Linux) with Python 3.x and Wi-Fi.
    *   Webcam (for Phase 2+)
    *   Ensure computer and phone/tablet are on the **same Wi-Fi network** for OSC.
2.  **Software:**
    *   Clone this repository.
    *   Install Python 3.x if you haven't already.
    *   It's recommended to use a virtual environment:
        ```bash
        python3 -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   Install required Python packages:
        ```bash
        pip install -r requirements.txt
        ```
3.  **Muse Direct Configuration (for OSC):**
    *   Connect Muse S to Muse Direct via Bluetooth.
    *   Find your computer's local IP address.
    *   In Muse Direct Streaming settings:
        *   Enable OSC Streaming.
        *   Set **Target IP Address** to your computer's IP.
        *   Set **Target Port** to `5001` (or match the port used in scripts).
        *   Enable streaming for `/eeg` and `/ppg`. (Also enable `/acc` for Phase 2+).

## Running the Scripts

### 1. Check OSC Connection (Optional but Recommended)

*   Start streaming from Muse Direct.
*   Run the checker script:
    ```bash
    python3 check_osc.py
    ```
*   You should see OSC messages printed if the connection is working. Press Ctrl+C to stop.

### 2. Run the Monitor (`main.py`)

*   Start streaming from Muse Direct.
*   Run the monitor script:
    ```bash
    python3 main.py
    ```
*   The script will first run the baseline calculation (default 60s). Please relax during this time.
*   After baseline calculation, it will enter the real-time monitoring loop and display a UI window.
*   Observe the console output and the UI for state information. Press Ctrl+C to stop the script and close the UI window.

### 3. Run with Shorter Baseline (for testing)

*   To speed up testing, you can use a shorter baseline duration:
    ```bash
    python3 main.py --baseline-duration 10 
    ```

### 4. PPG BPM Test (`test_ppg_bpm.py`)

*   A utility script to test the PPG-to-BPM estimation logic using simulated data.
    ```bash
    python3 test_ppg_bpm.py
    ```

### 5. Run Unit Tests

*   To run the unit tests, use the command:
    ```bash
    python3 -m unittest discover tests
    ```
    *   Ensure you are in the project root directory when running this command.
    *   All tests in the `tests/` directory will be discovered and run.

## Project Structure

```
braintrade_monitor/  # Python package containing core logic
├── __init__.py
├── config.py        # Configuration constants
├── data_store.py    # Manages shared data buffers and thread safety
├── feature_extraction.py # Feature extraction functions (EEG ratio, BPM)
├── osc_handler.py   # OSC server setup and message handlers
├── baseline.py      # Baseline calculation logic
├── processing.py    # Main real-time data processing loop
├── state_logic.py   # Stress state determination logic
dashboard_ui.py      # Tkinter UI implementation
main.py              # Main application script (entry point)
check_osc.py         # OSC connection checker script
send_synthetic_osc.py # Script to send synthetic OSC data for testing
tests/               # Unit tests directory
├── test_feature_extraction.py
├── test_state_logic.py
├── test_data_store.py
├── test_baseline.py
├── test_processing.py
docs/                # Documentation files
logs/                # Log files
old/                 # Old/archived files
training_data/       # Training data (if any)
requirements.txt     # Python dependencies
README.md            # This file
CHANGELOG.md         # Changelog
.gitignore           # Git ignore file
```


## Documentation

*   `docs/braintrade_monitor_plan.md`: Overall project roadmap and Phase 2 plan/progress.
*   `docs/phase1_stress_meter_plan.md`: Detailed plan for Phase 1.
*   `docs/phase2_dashboard_plan.md`: Detailed plan for Phase 2.
*   `docs/phase3_focus_guardian_plan.md`: Detailed plan for Phase 3.
*   `docs/phase4_advanced_indicators_plan.md`: Detailed plan for Phase 4 (Stretch Goal).
*   `docs/phase5_web_ui_plan.md`: Detailed plan for Phase 5 (Future Enhancement).
*   `docs/muse_s_osc_setup_guide.md`: Guide for setting up Muse Direct and OSC.

(Note: Motor imagery related files have been moved to the `old/` directory).