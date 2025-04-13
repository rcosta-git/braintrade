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

## Current Status (Phase 1 Complete)

Phase 1 is now complete. The stress monitor script (`stress_monitor.py`) is functional and performs real-time stress monitoring based on EEG Alpha/Beta ratio and PPG-derived heart rate.

*   **Resolved Hanging Issue:** The issue causing the script to hang during baseline calculation has been resolved.
*   **Console Logging:** Logging is now configured to output to the console only, addressing disk space concerns.
*   **OSC Data Reception:** Confirmed reception of EEG (`/eeg`) and PPG (`/ppg`) data from Muse Direct via OSC.
*   **Core Script (`stress_monitor.py`):** Basic structure created. OSC listener implemented. Baseline calculation structure implemented (using median/std dev).
*   **Feature Extraction:** Functions for Alpha/Beta ratio (`extract_alpha_beta_ratio`) and BPM estimation from PPG (`estimate_bpm_from_ppg`) added.

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

### 2. Run the Monitor (`stress_monitor.py`)

*   Start streaming from Muse Direct.
*   Run the monitor script:
    ```bash
    python3 stress_monitor.py
    ```
*   The script will first run the baseline calculation (default 60s). Please relax during this time.
*   After baseline calculation, it will enter the real-time monitoring loop.
*   Observe the console output for state information. Press Ctrl+C to stop.

### 3. PPG BPM Test (`test_ppg_bpm.py`)

*   A utility script to test the PPG-to-BPM estimation logic using simulated data.
    ```bash
    python3 test_ppg_bpm.py
    ```

## Documentation

*   `docs/braintrade_monitor_plan.md`: Overall project roadmap.
*   `docs/phase1_stress_meter_plan.md`: Detailed plan for Phase 1.
*   `docs/phase2_dashboard_plan.md`: Detailed plan for Phase 2.
*   `docs/phase3_focus_guardian_plan.md`: Detailed plan for Phase 3.
*   `docs/phase4_advanced_indicators_plan.md`: Detailed plan for Phase 4 (Stretch Goal).
*   `docs/phase5_web_ui_plan.md`: Detailed plan for Phase 5 (Future Enhancement).
*   `docs/muse_s_osc_setup_guide.md`: Guide for setting up Muse Direct and OSC.

(Note: Motor imagery related files have been moved to the `old/` directory).