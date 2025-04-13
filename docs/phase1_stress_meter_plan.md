# Phase 1 Plan: Simple Stress Meter

**Part of Project:** BrainTrade - Mental State Monitor

**Objective:** Create a real-time indicator of potential stress/tilt based on EEG Alpha/Beta ratio and Heart Rate changes relative to a baseline, estimating HR from PPG data.

**Core Script:** `stress_monitor.py`

**1. OSC Data Handling:**
    *   Listen for `/eeg` (4 channels assumed, confirm mapping if possible) and `/ppg` (extract middle value, confirm address).
    *   Store recent data in `collections.deque` buffers (e.g., `eeg_buffers`, `ppg_buffer`). Use `threading.Lock` for thread-safe access between the OSC listener thread and the main processing loop.
    *   Determine appropriate buffer sizes (e.g., enough for baseline + longest analysis window).

**2. Baseline Calculation (Revised Method):**
    *   **Trigger:** Automatic at script start. Print instructions: "Calculating baseline... Please relax for 60 seconds."
    *   **Duration:** 60 seconds (tunable parameter).
    *   **Data Collection:** In a loop (e.g., every 0.5s update interval):
        *   Get latest data windows (e.g., 2s EEG, 5-10s PPG). Ensure enough data is buffered before starting calculations.
        *   Calculate Alpha/Beta ratio for the EEG window (using `get_band_powers`).
        *   Estimate BPM for the PPG window (using `get_heart_rate`).
        *   Store valid calculated ratio and BPM values in temporary lists for the baseline period.
    *   **Calculation (End of Baseline Period):**
        *   Calculate `baseline_ratio_median` (median of collected ratios).
        *   Calculate `baseline_hr_median` (median of collected BPMs).
        *   Calculate `baseline_ratio_std` (standard deviation of collected ratios).
        *   Calculate `baseline_hr_std` (standard deviation of collected BPMs).
        *   Handle potential edge cases (e.g., not enough valid data collected during baseline).
    *   **Storage:** Store these four baseline metrics (`baseline_ratio_median`, `baseline_ratio_std`, `baseline_hr_median`, `baseline_hr_std`).

**3. Real-time Feature Extraction Functions:**
    *   **`get_band_powers(eeg_window, sampling_rate)`:**
        *   Input: NumPy array `(n_channels, n_samples)`.
        *   Apply bandpass filter (e.g., 1-40 Hz using `mne.filter.filter_data`).
        *   Calculate PSD using `mne.time_frequency.psd_array_welch`.
            *   Dynamically set `n_fft = min(n_samples, 256)` and pass `n_per_seg=n_fft`.
        *   Calculate average power in Alpha (8-13 Hz) and Beta (13-30 Hz) bands.
        *   Compute ratio (e.g., Alpha/Beta). Return the ratio (or handle division by zero, e.g., return NaN or a default value).
    *   **`get_heart_rate(ppg_window, sampling_rate)`:**
        *   Input: NumPy array `(n_samples,)`. Assume `sampling_rate` is known (e.g., 64 Hz for Muse PPG).
        *   Apply bandpass filter (e.g., 0.5-4 Hz using `scipy.signal.butter` + `filtfilt`).
        *   Detect peaks using `scipy.signal.find_peaks` (tune `height`, `distance` parameters based on filtered signal characteristics and expected HR range).
        *   Calculate Inter-Beat Intervals (IBIs) in seconds from peak indices (`diff(peaks) / sampling_rate`). Filter out unrealistic IBIs (e.g., corresponding to <30 BPM or >200 BPM).
        *   Calculate BPM (`60 / mean(valid_IBIs)`). Return BPM (or NaN if insufficient valid peaks/IBIs).

**4. Main Processing Loop:**
    *   Runs after baseline calculation.
    *   Sleeps for `update_interval` (e.g., 0.5s).
    *   Acquire lock, get latest data windows from deques (e.g., 2s EEG, 5-10s PPG). Release lock. Check if enough data is available.
    *   Call `get_band_powers` to get `current_ratio`.
    *   Call `get_heart_rate` to get `current_hr`.
    *   Handle cases where feature calculation returns NaN (e.g., skip state update).
    *   Apply State Logic (see below).
    *   Call UI update function.

**5. State Logic (Refined):**
    *   **Inputs:** `current_ratio`, `current_hr`, baseline metrics (medians, std devs).
    *   **Parameters:** Tunable sensitivity factors (`RATIO_STD_THRESHOLD = 1.5`, `HR_STD_THRESHOLD = 1.5`), persistence duration (`PERSISTENCE_UPDATES = 6` for 3 seconds at 0.5s interval).
    *   **State Variables:** `current_state` (official), `tentative_state_history` (deque of size `PERSISTENCE_UPDATES`).
    *   **Logic per Update:**
        *   1. **Handle NaNs:** If `current_ratio` or `current_hr` is NaN, skip state update for this cycle (maintain `current_state`).
        *   2. **Calculate Flags:** Determine `is_ratio_low` and `is_hr_high` based on current values and SD thresholds.
        *   3. **Determine Tentative State:**
            *   `if is_ratio_low and is_hr_high:` => `tentative_state = "Stress"`
            *   `elif is_ratio_low or is_hr_high:` => `tentative_state = "Warning"`
            *   `else:` => `tentative_state = "Calm"`
        *   4. **Apply Persistence:**
            *   Add `tentative_state` to `tentative_state_history` deque.
            *   If deque is full AND all elements in deque are identical AND the identical state is different from `current_state`:
                *   Update `current_state` to the new persistent state.
    *   **Output:** The persistent `current_state`.
**6. UI/Feedback (MVP):**
    *   Print current state, ratio, and HR to console periodically.

**7. Key Libraries:**
    *   `python-osc` (for OSC communication)
    *   `numpy` (for numerical operations)
    *   `mne` (for EEG filtering, PSD)
    *   `scipy` (for PPG filtering, peak detection)
    *   `collections` (for `deque`)
    *   `threading` (for OSC server thread, data lock)
    *   `time`
    *   `argparse`

**8. Initial Parameters/Defaults:**
    *   Baseline duration: 60s
    *   Update interval: 0.5s
    *   EEG analysis window: 2s
    *   PPG analysis window: 10s
    *   EEG Filter: 1-40 Hz
    *   PPG Filter: 0.5-4 Hz
    *   Alpha Band: 8-13 Hz
    *   Beta Band: 13-30 Hz
    *   SD Thresholds: 1.5