# Phase 3 Plan: Focus & Fatigue Detection (Focus Guardian)

**Part of Project:** BrainTrade - Mental State Monitor
**Builds Upon:** Phase 2 (Enhanced Dashboard & Feedback)

**Objective:** Enhance the monitor by adding detection for loss of focus or drowsiness, primarily using EEG Theta band analysis and blink detection (either via CV or EEG).

**Core Script:** Continue modifying `stress_monitor.py` (or refactor).

**1. Enhanced EEG Analysis (Refined):**
    *   **Goal:** Extract features relevant to focus, drowsiness, and cognitive load.
    *   **Feature Extraction (`get_band_powers` update):**
        *   Modify the function to calculate average absolute power across all available channels for **Theta (4-8 Hz)**, **Alpha (8-13 Hz)**, and **Beta (13-30 Hz)** bands.
        *   Calculate and return key ratios: **Theta/Beta Ratio** and **Alpha/Beta Ratio**.
        *   *(Channel Mapping Note:* Calculating metrics specifically on frontal channels like AF7/AF8 could provide better focus/load indicators, but requires verifying the OSC stream's channel order from Muse Direct. Assume global average across channels for now unless mapping is confirmed.)*
    *   **Baseline:** During the initial calibration phase, collect values for the chosen metrics (e.g., Theta/Beta Ratio, Alpha/Beta Ratio). Calculate and store the baseline median and standard deviation for each metric (e.g., `baseline_theta_beta_median`, `baseline_theta_beta_std`).
    *   **(Deferred) Frontal Asymmetry:** Calculating frontal alpha asymmetry requires reliable channel mapping and is deferred.

**2. Blink Detection (Refined Strategy):**
    *   **Goal:** Estimate blink rate as an indicator of fatigue/drowsiness.
    *   **Method Choice Strategy:**
        *   **Primary Approach (if feasible): Computer Vision (Eye Aspect Ratio - EAR)**
            *   *Condition:* Requires reliable facial landmark detection, especially eye landmarks, from the CV implementation in Phase 2 (e.g., using `dlib`, `mediapipe` backend in `deepface`, or similar).
            *   *Library:* Leverage the chosen Phase 2 CV library's landmark output. Use `scipy.spatial.distance` to calculate distances needed for EAR.
            *   *Logic:* Calculate EAR for each frame. Detect blinks when EAR drops below a tuned threshold for a minimum number of frames. Calculate blink rate (blinks per minute) over a rolling window (e.g., 30-60 seconds).
            *   *Pros:* Direct measure of eye closure. Leverages existing CV pipeline if landmarks are available.
            *   *Cons:* Dependent on reliable landmark tracking; sensitive to pose, lighting, occlusions.
        *   **Fallback Approach: EEG Artifact Detection**
            *   *Condition:* Use if CV landmarks are unavailable or unreliable.
            *   *Signal:* Use raw EEG data buffers (frontal channels preferred: AF7/AF8 if mapped, otherwise TP9/TP10 or average).
            *   *Logic:* Apply bandpass filter (e.g., 1-10 Hz). Implement a peak detection algorithm (`scipy.signal.find_peaks` or custom thresholding) tuned to identify large-amplitude, sharp deflections typical of blink artifacts. Calculate blink rate over a rolling window.
            *   *Pros:* Uses existing EEG stream. Less sensitive to camera issues.
            *   *Cons:* Indirect measure; prone to false positives from EMG/movement; requires careful filter/threshold tuning per user.
        *   **Simplification:** If both above are too complex/unreliable, consider a simpler CV metric like "% time eyes closed" over a window.
    *   **Implementation:**
        *   Implement the chosen blink detection logic (prioritizing CV EAR).
        *   Calculate rolling blink rate (`current_blink_rate`).
        *   Calculate baseline blink rate (`baseline_blink_rate_median`, `baseline_blink_rate_std`) during calibration.

**3. State Logic Enhancement (Refined):**
    *   **Inputs:** Adds `current_theta_beta_ratio`, `current_blink_rate`, and their baseline metrics (median, std dev).
    *   **Intermediate Flags (based on SD thresholds):** Calculate boolean flags like `is_ratio_low`, `is_hr_high`, `is_movement_high`, `is_expression_negative`, `is_expression_neutral`, `is_physio_calm`, `is_movement_low`, AND NEW: `is_theta_beta_high`, `is_blink_rate_high`, `is_theta_beta_normal`, `is_blink_rate_normal`.
    *   **Core States for Phase 3:** "Drowsy/Distracted", "Stressed/Tilted", "Calm/Focused", "Other/Uncertain".
    *   **Prioritized Rule Structure Example:**
        *   `tentative_state = "Other/Uncertain"` # Default
        *   `# 1. Check Drowsy/Distracted`
        *   `if is_theta_beta_high and (is_blink_rate_high or is_movement_low):`
        *      `tentative_state = "Drowsy/Distracted"`
        *   `# 2. Check Stress/Tilt (Overrides Drowsy if conditions met)`
        *   `elif (is_ratio_low and is_hr_high) or \`
             ` (is_expression_negative and (is_hr_high or is_movement_high)):`
        *      `tentative_state = "Stressed/Tilted"`
        *   `# 3. Check Calm/Focused (Requires absence of negative indicators)`
        *   `elif is_physio_calm and is_movement_low and is_expression_neutral and is_theta_beta_normal and is_blink_rate_normal:`
        *      `tentative_state = "Calm/Focused"`
        *   `# Note: Thresholds and rule combinations require tuning.`
    *   **Persistence Logic:** Maintain the official `current_state`. Only change `current_state` if the `tentative_state` remains the same for a defined duration (e.g., 3-5 seconds or N consecutive updates).

**4. UI Dashboard Update:**
    *   Add indicators for Theta Power/Ratio, Blink Rate, and the new "Drowsy/Distracted" state to the chosen UI (Tkinter/Rich).

**5. Key Libraries (Additions/Considerations):**
    *   Potentially `dlib` or `mediapipe` (if using CV EAR blink detection and not already added in Phase 2).
    *   `scipy.spatial` (for EAR calculation if using CV).

**6. Implementation Steps:**
    *   Modify `get_band_powers` to include Theta.
    *   Add Theta baseline calculation.
    *   Implement chosen Blink Detection method (CV or EEG).
    *   Add blink rate baseline calculation.
    *   Refine state logic rules significantly to incorporate new inputs and states.
    *   Update UI dashboard.
    *   Test and tune thresholds for Theta and Blink Rate.