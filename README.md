# BrainTrade - Mental State Monitor

This project aims to build a system using a Muse S headset (and potentially other inputs like computer vision) to monitor the mental state of a day trader in real-time. The goal is to detect suboptimal states (e.g., stress, fatigue, distraction) and provide feedback to help mitigate poor trading decisions.

This project is being developed incrementally.

## Approach

The system uses a multi-phase approach, starting with basic physiological indicators and progressively adding more complex features and analysis:

*   **Phase 1:** Simple Stress Meter (EEG Alpha/Beta Ratio + Estimated Heart Rate from PPG)
*   **Phase 2:** Enhanced Dashboard (Adds Computer Vision for Facial Expression + Accelerometer for Movement)
*   **Phase 3:** Focus/Fatigue Detection (Adds EEG Theta + Blink Detection)
*   **Phase 4:** Advanced Indicators (Explores HRV - Stretch Goal)
*   **Phase 5:** Web UI Migration (Future Enhancement)

See `docs/braintrade_monitor_plan.md` for the overall roadmap and individual `docs/phaseX_*.md` files for detailed plans.

## Current Status (Web UI Integration Complete)

Phase 2 is complete. Phase 3 (Focus/Fatigue) is partially implemented. A new web-based UI (React/TypeScript/Vite) located in the `web/` directory has been successfully integrated, replacing the previous Tkinter UI. A FastAPI backend (`web_server.py`) serves data from the `braintrade_monitor` package to the web frontend.

Key accomplishments:
*   Successfully integrated a React/TypeScript web UI.
*   Implemented a FastAPI backend to serve data to the web UI.
*   Implemented a heuristic trade suggestion with confidence level.
*   Added live BTC price display.
*   Improved handling of BCI connection status and data availability.

Ongoing:
*   Troubleshooting occasional issues with data flow and UI updates.

## Setup

1.  **Hardware:**
    *   Muse S Headband
    *   Smartphone/Tablet with Muse Direct app installed.
    *   Computer (Mac/Windows/Linux) with Python 3.x and Wi-Fi.
    *   Webcam (for Phase 2 - basic facial expression)
    *   Ensure computer and phone/tablet are on the **same Wi-Fi network** for OSC.
2.  **Software:**
    *   Clone this repository.
    *   Install Python 3.x if you haven't already.
    *   It's recommended to use a virtual environment:
        ```bash
        python3 -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   Install required Python packages (in project root):
        ```bash
        pip install -r requirements.txt
        ```
    *   Install required Node.js packages for the web UI (in `web/` directory):
        ```bash
        cd web
        npm install  # or yarn install, or bun install
        cd ..
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

### 2. Run the Backend Monitor (`main.py`)

*   This script runs the core data processing and state logic, and now also hosts the API server.
*   Start streaming from Muse Direct.
*   In your first terminal (project root), run the monitor script:
    ```bash
    python3 main.py
    ```
*   The script will first run the baseline calculation (default 60s). Please relax during this time.
*   After baseline calculation, it will enter the real-time monitoring loop. It no longer displays its own UI window directly. Press Ctrl+C to stop.

### 3. Run the Web UI Frontend

*   This serves the web application dashboard.
*   In a second terminal, navigate to the `web/` directory and start the development server:
    ```bash
    cd web
    npm run dev  # or yarn dev, or bun run dev
    ```
*   Open your web browser and navigate to the address shown (usually `http://localhost:5173`).
*   You should see the dashboard updating with data from the backend.

### 4. Run Monitor with Shorter Baseline (for testing)

*   To speed up testing the backend, you can use a shorter baseline duration when running `main.py`:
    ```bash
    # In the first terminal (instead of the command in step 2)
    python3 main.py --baseline-duration 10
    ```

### 5. PPG BPM Test (`test_ppg_bpm.py`)

*   A utility script to test the PPG-to-BPM estimation logic using simulated data.
    ```bash
    python3 test_ppg_bpm.py
    ```

### 6. Run Unit Tests

*   To run the Python unit tests, use the command from the project root:
    ```bash
    python3 -m unittest discover tests
    ```
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
web_server.py        # FastAPI server to bridge backend and web UI
dashboard_ui.py      # Old Tkinter UI implementation (being replaced)
main.py              # Main application script (entry point)
check_osc.py         # OSC connection checker script
send_synthetic_osc.py # Script to send synthetic OSC data for testing
web/                 # Web UI Frontend (React/TypeScript/Vite)
├── public/          # Static assets
├── src/             # Frontend source code
├── package.json     # Node.js dependencies
└── ...              # Other frontend config files (vite, tailwind, etc.)
tests/               # Unit tests directory
├── test_feature_extraction.py
├── test_state_logic.py
├── test_data_store.py
├── test_baseline.py
├── test_processing.py
├── test_cv_handler.py # Assuming this exists or will be added
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

*   `docs/braintrade_monitor_plan.md`: Overall project roadmap.
*   `docs/phase1_stress_meter_plan.md`: Detailed plan for Phase 1.
*   `docs/phase2_dashboard_plan.md`: Detailed plan for Phase 2.
*   `docs/phase3_focus_guardian_plan.md`: Detailed plan for Phase 3.
*   `docs/phase4_advanced_indicators_plan.md`: Detailed plan for Phase 4 (Stretch Goal).
*   `docs/phase5_web_ui_plan.md`: Detailed plan for Phase 5 (Future Enhancement).
*   `docs/web_ui_integration_plan.md`: Detailed plan for integrating the web UI, including troubleshooting steps.
*   `docs/muse_s_osc_setup_guide.md`: Guide for setting up Muse Direct and OSC.

(Note: Motor imagery related files have been moved to the `old/` directory).