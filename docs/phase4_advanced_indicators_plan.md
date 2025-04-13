# Phase 4 Plan: Advanced Indicators (Impulsivity Alert - Stretch Goal)

**Part of Project:** BrainTrade - Mental State Monitor
**Builds Upon:** Phase 3 (Focus & Fatigue Detection)

**Objective:** Explore using Heart Rate Variability (HRV) derived from PPG data as a potential indicator of physiological stress or reduced cognitive control, potentially flagging moments of increased impulsivity risk. *This is considered a stretch goal due to the technical challenges.*

**Core Script:** Continue modifying `stress_monitor.py` (or refactor).

**1. HRV Calculation from PPG:**
    *   **Goal:** Estimate relevant HRV metrics in near real-time from the PPG signal.
    *   **Feasibility Check (CRITICAL):**
        *   *Signal Quality:* Assess if the PPG signal obtained via OSC (`/ppg` middle value) is clean enough for reliable beat-to-beat interval detection after filtering. Noise, movement artifacts, or low sampling rate can make HRV calculation highly inaccurate.
        *   *Library Evaluation:* Thoroughly evaluate candidate libraries (`HeartPy`, `NeuroKit2`, `pyhrv`, custom `SciPy`) for their ability to calculate HRV metrics (specifically time-domain like RMSSD, SDNN) from *short, rolling windows* of potentially noisy PPG data. Test their robustness and computational cost.
    *   **Implementation (If Feasible):**
        *   Select the most promising library or method.
        *   Modify the `get_heart_rate` function (or create a new `get_hrv_metrics` function) to:
            *   Take a longer PPG window (e.g., 60 seconds minimum, updated less frequently like every 15-30s, as HRV needs longer segments).
            *   Perform robust peak detection to get accurate Inter-Beat Intervals (IBIs or RR intervals).
            *   Calculate key time-domain HRV metrics (e.g., RMSSD - Root Mean Square of Successive Differences, often related to parasympathetic activity/calmness; SDNN - Standard Deviation of NN intervals, related to overall variability).
        *   Return calculated HRV metrics (e.g., `current_rmssd`, `current_sdnn`).
    *   **Baseline:** Calculate baseline median/std dev for the chosen HRV metrics during calibration.

**2. State Logic Enhancement (Refined):**
    *   **Goal:** Incorporate HRV changes (primarily RMSSD) to identify periods of potential "Impulsivity Risk".
    *   **Inputs:** Adds `current_rmssd` and its baseline metrics (`baseline_rmssd_median`, `baseline_rmssd_std`). (SDNN can be calculated/displayed but might not be used in core logic).
    *   **Hypothesis:** A significant drop in RMSSD indicates reduced parasympathetic activity (less calm/control), which, when combined with other stress/arousal signs, suggests higher impulsivity risk.
    *   **Intermediate Flags:** Add `is_rmssd_low` (e.g., `current_rmssd < baseline_rmssd_median - HRV_STD_THRESHOLD * baseline_rmssd_std`, where `HRV_STD_THRESHOLD` is tunable, e.g., 1.0-1.5).
    *   **Prioritized Rule Structure Example:**
        *   `tentative_state = "Other/Uncertain"` # Default
        *   `# 1. Check Impulsivity Risk (Highest Priority)`
        *   `if is_rmssd_low and (is_hr_high or is_movement_high or is_expression_negative):`
             `tentative_state = "Impulsivity Risk"`
        *   `# 2. Check Stress/Tilt (If not Impulsive)`
        *   `elif (is_ratio_low and is_hr_high) or \`
             ` (is_expression_negative and (is_hr_high or is_movement_high)):`
        *      `tentative_state = "Stressed/Tilted"`
        *   `# 3. Check Drowsy/Distracted (If not Impulsive or Stressed)`
        *   `elif is_theta_beta_high and (is_blink_rate_high or is_movement_low):`
        *      `tentative_state = "Drowsy/Distracted"`
        *   `# 4. Check Calm/Focused (Requires absence of negative indicators)`
        *   `elif is_physio_calm and is_movement_low and is_expression_neutral and is_theta_beta_normal and is_blink_rate_normal:`
        *      `tentative_state = "Calm/Focused"`
        *   `# Note: Thresholds and rule combinations require tuning.`
    *   **Persistence Logic:** Apply as before (state must persist).

**3. UI Dashboard / Intervention Update:**
    *   Add HRV metrics (e.g., RMSSD) to the dashboard display.
    *   Implement a specific alert or intervention for the "Impulsivity Risk" state.
        *   *Simple Alert:* Clear visual/audio warning: "Impulsivity Risk High! Pause & Reassess."
        *   *Hackathon Demo Intervention:* Briefly disable a simulated "Trade" button in the UI.

**4. Key Libraries (Additions/Considerations):**
    *   Chosen HRV analysis library (`HeartPy`, `NeuroKit2`, `pyhrv`) OR more advanced `SciPy` usage.

**5. Implementation Steps:**
    *   **Crucial:** Perform feasibility check on real-time HRV calculation from Muse PPG data. **Do not proceed if unreliable.**
    *   If feasible, integrate chosen HRV library/method.
    *   Add HRV baseline calculation.
    *   Refine state logic rules to incorporate HRV and the "Impulsivity Risk" state.
    *   Update UI dashboard with HRV info and new alert/intervention.
    *   Extensive testing required due to the sensitivity of HRV metrics.

**Contingency:** If real-time HRV proves infeasible, this phase might be skipped or replaced with exploring other advanced EEG metrics (e.g., more complex band power combinations, connectivity - though also complex).