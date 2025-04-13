# Project Plan: BrainTrade - Mental State Monitor

**Goal:** Develop a system using Muse headset data (EEG, PPG, ACC) and potentially Computer Vision (CV) to monitor a day trader's mental state and provide feedback/alerts to mitigate suboptimal trading decisions during a hackathon.

---

## Roadmap

This project will be developed incrementally across four phases:

**Phase 1: MVP - Simple Stress Meter (Complete)**
*   **Objective:** Detect basic signs of stress/tilt using EEG band power ratios and Heart Rate (estimated from PPG).
*   **Core Components:** OSC Listener (EEG, PPG), Baseline Calculation (Median + Std Dev), Real-time Feature Extraction (Alpha/Beta Ratio, Estimated BPM from PPG), State Logic (SD-based thresholds), Simple Console UI (Tkinter).
*   **Signals:** EEG (Bands), PPG (Raw -> Estimated BPM).

**Phase 2: Enhanced Dashboard & Feedback (Complete)**
*   **Objective:** Provide a richer view by adding CV (facial expression) and Accelerometer data, and migrate to a web-based UI.
*   **Core Components:** Basic CV Integration (Facial Expression), Accelerometer Processing (Movement Level), Web-based UI (React/FastAPI) replacing the Tkinter UI, Contextual Alerts.
*   **Signals:** EEG (Bands), PPG (Estimated BPM), CV (Facial Expression), ACC (Movement). The web UI consumes this data via an API.

**Phase 3: Focus & Fatigue Detection (In Progress)**
*   **Objective:** Add detection for loss of focus or drowsiness.
*   **Core Components:** Enhanced EEG Analysis (Theta band, potentially Frontal Asymmetry), Blink Detection (EEG artifact), Refined State Logic for Focus/Drowsiness, Web UI Integration.
*   **Signals:** EEG (Bands, potentially Raw), PPG (Estimated BPM), CV (Facial Expression), ACC (Movement). The web UI consumes this data via an API.

**Phase 4: Advanced Indicators (Stretch Goal - Unlikely for Hackathon)**
*   **Objective:** Explore more advanced physiological markers like HRV (Likely beyond the scope of the hackathon).
*   **Core Components:** HRV Calculation from PPG (Feasibility Check Required), Refined State Logic for Impulsivity Risk, Advanced Intervention Demo (Likely not implemented).
*   **Signals:** All previous + derived HRV (if possible).

---

## Phase 1 Plan Details: Simple Stress Meter

**Objective:** Create a real-time indicator of potential stress/tilt based on EEG Alpha/Beta ratio and Heart Rate changes relative to a baseline, estimating HR from PPG data.

**Core Script:** `stress_monitor.py`

**1. OSC Data Handling:**
*   Listen for `/eeg` (4 channels) and `/ppg` (extract middle value).
*   Store recent data in `deque` buffers (e.g., for EEG, PPG). Use `threading.Lock` for safe access.

**2. Baseline Calculation (Revised):**
*   **Trigger:** Automatic at script start. Print instructions: "Calculating baseline... Please relax for 60 seconds."
*   **Duration:** 60 seconds.
*   **Data Collection:** In a loop (e.g., every 0.5s), get latest data windows (e.g., 2s EEG, 5-10s PPG), calculate Alpha/Beta ratio and estimated BPM (see below). Store all calculated values in lists.
*   **Calculation:**
    *   Calculate `baseline_ratio_median` (median of collected ratios).
    *   Calculate `baseline_hr_median` (median of collected BPMs).
    *   Calculate `baseline_ratio_std` (standard deviation of collected ratios).
    *   Calculate `baseline_hr_std` (standard deviation of collected BPMs).
*   **Storage:** Store these four baseline metrics.

**3. Real-time Feature Extraction:**
*   **Alpha/Beta Ratio:**
    *   Get latest EEG window (e.g., 2 seconds).
    *   Apply bandpass filter (e.g., 1-40 Hz).
    *   Calculate PSD using `mne.time_frequency.psd_array_welch` (ensure `n_fft` is handled for window size).
    *   Calculate average power in Alpha (8-13 Hz) and Beta (13-30 Hz) bands.
    *   Compute ratio (e.g., Alpha/Beta). Handle potential division by zero.
*   **Heart Rate (BPM) from PPG:**
    *   Get latest PPG window (e.g., 5-10 seconds).
    *   Apply bandpass filter (e.g., 0.5-4 Hz using `scipy.signal.butter` + `filtfilt`).
    *   Detect peaks using `scipy.signal.find_peaks` (tune `height`, `distance` parameters).
    *   Calculate Inter-Beat Intervals (IBIs) in seconds from peak indices (`diff(peaks) / sampling_rate`).
    *   Calculate BPM (`60 / mean(IBIs)`). Handle cases with <2 peaks or invalid IBIs.

**4. State Logic (Revised):**
*   Define tunable sensitivity factors (e.g., `RATIO_STD_THRESHOLD = 1.5`, `HR_STD_THRESHOLD = 1.5`).
*   Check conditions:
    *   `is_ratio_low = current_ratio < (baseline_ratio_median - RATIO_STD_THRESHOLD * baseline_ratio_std)`
    *   `is_hr_high = current_hr > (baseline_hr_median + HR_STD_THRESHOLD * baseline_hr_std)`
*   Determine state:
    *   `if is_ratio_low and is_hr_high:` => `state = "Stress"`
    *   `elif is_ratio_low or is_hr_high:` => `state = "Warning"`
    *   `else:` => `state = "Calm"`
*   Consider adding persistence logic (state must hold for X seconds).

**5. UI/Feedback (MVP):**
*   Print current state, ratio, and HR to console periodically.
*   Example: `print(f"State: {state} | A/B Ratio: {current_ratio:.2f} | HR: {current_hr:.1f} BPM")`

**6. Implementation Steps:**
*   Create `stress_monitor.py` structure.
*   Implement OSC listeners.
*   Implement baseline calculation logic (using median/std dev).
*   Implement `get_band_powers` function.
*   Implement `get_heart_rate` function (using SciPy filter/peaks).
*   Implement main loop with state logic.
*   Implement console printing.
*   Test and tune thresholds/parameters.