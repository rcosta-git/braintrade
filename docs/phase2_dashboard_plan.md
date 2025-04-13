# Phase 2 Plan: Enhanced Dashboard & Feedback

**Part of Project:** BrainTrade - Mental State Monitor
**Builds Upon:** Phase 1 (Simple Stress Meter)

**Objective:** Enhance the Phase 1 monitor by adding Computer Vision (basic facial expression) and Accelerometer data (movement level) to provide a richer view of the trader's state via a simple dashboard.

**Core Scripts:** Core logic now modularized in `braintrade_monitor` package (Python modules), orchestrated by `main.py`. UI presentation in `dashboard_ui.py`.

**1. Computer Vision Integration (Facial Expression):**
    *   **Goal:** Detect basic emotional expressions from webcam feed.
    *   **Library Choice (Prioritized):** **`fer` (Facial Expression Recognition)**
        *   *Reasoning:* Simple API, directly provides standard emotion detection suitable for the hackathon scope.
        *   *Dependency Note:* Requires installing `tensorflow` alongside `fer`. Ensure compatibility during setup.
        *   *Alternative:* If `tensorflow` installation proves problematic, `deepface` with a lighter backend (e.g., `opencv`) could be considered as a fallback.
    *   **Implementation:**
        *   Add library to `requirements.txt`.
        *   Create a separate thread or process for webcam capture and analysis to avoid blocking the main OSC/processing loop.
        *   Capture frames from the webcam (using `opencv-python`).
        *   Pass frames to the chosen library for expression analysis.
        *   Store the dominant detected expression (e.g., "Neutral", "Angry", "Happy", "Stressed" - may need mapping from library outputs) in a shared variable (use `threading.Lock` for access).
    *   **Error Handling:** Handle cases where no face is detected or the library fails.

**2. Accelerometer Data Integration (Refined):**
    *   **Goal:** Quantify head movement/restlessness level.
    *   **OSC Handling:** Add handler for `/acc` messages (3-axis data, assume ~50Hz rate). Store recent ACC data (e.g., last 4 seconds) in a `deque` (e.g., `maxlen=200`).
    *   **Feature Calculation (`get_movement_metric`):**
        *   Input: Window of ACC data `(n_samples, 3)` (e.g., last 3 seconds, ~150 samples).
        *   Calculate the standard deviation for each axis (X, Y, Z) independently over the window: `sd_x, sd_y, sd_z`.
        *   Calculate the magnitude of the standard deviation vector: `movement_metric = np.sqrt(sd_x**2 + sd_y**2 + sd_z**2)`.
        *   Return `movement_metric`.
    *   **Baseline:** During the initial calibration phase, collect `movement_metric` values. Calculate and store `baseline_movement_median` and `baseline_movement_std`.
    *   **Level Mapping (`get_movement_level`):** Create a function that takes `current_movement_metric`, `baseline_movement_median`, `baseline_movement_std` and returns a qualitative level ("Low", "Medium", "High") based on tuned SD thresholds (e.g., < baseline+1SD = Low, >= baseline+1SD and < baseline+2.5SD = Medium, >= baseline+2.5SD = High).

**3. State Logic Enhancement (Refined):**
    *   **Inputs:**
        *   `current_ratio`, `current_hr` (from Phase 1 features)
        *   `current_expression` (String from CV, e.g., "Neutral", "Angry", "Sad", "Happy", etc.)
        *   `current_movement_level` (String from ACC, e.g., "Low", "Medium", "High")
        *   Baseline metrics (medians and std devs for ratio, hr, movement)
    *   **Intermediate Flags (based on thresholds like `median +/- 1.5 * std`):**
        *   `is_ratio_low`, `is_hr_high`, `is_movement_high`, `is_expression_negative`, `is_expression_neutral`, `is_physio_calm`, `is_movement_low`.
    *   **Core States for Phase 2:** "Stressed/Tilted", "Calm/Focused", "Other/Uncertain".
    *   **Rule-Based Logic Example:**
        *   **IF** (`is_ratio_low` AND `is_hr_high`) OR \
             (`is_expression_negative` AND (`is_hr_high` OR `is_movement_high`)):
            *   Tentative State = "Stressed/Tilted"
        *   **ELIF** `is_physio_calm` AND `is_movement_low` AND `is_expression_neutral`:
            *   Tentative State = "Calm/Focused"
        *   **ELSE:**
            *   Tentative State = "Other/Uncertain"
    *   **Persistence Logic:** Maintain the official `current_state`. Only change `current_state` if the `tentative_state` remains the same for a defined duration (e.g., 3-5 seconds or N consecutive updates). This prevents flickering between states.
    *   **Output:** The persistent `current_state`.

**4. UI Dashboard (Refined for Future Web UI):**
    *   **Goal:** Display multiple indicators clearly in a dedicated view, designed for later migration.
    *   **Implementation Approach (Prioritized):** **Simple GUI using `tkinter` in `dashboard_ui.py`**.
        *   *Reasoning:* Built-in, allows dedicated window, feasible for hackathon, promotes modularity.
        *   *File Structure:* `dashboard_ui.py` will contain the `tkinter` window setup, widgets (labels, display fields using `tkinter.StringVar`), and UI update functions.
        *   **Interaction:** `stress_monitor.py` will calculate the state and metrics, then pass this information (e.g., via a shared dictionary with a lock, or a queue) to the UI update function in `dashboard_ui.py`. `stress_monitor.py` will likely manage the UI lifecycle (e.g., starting the `tkinter` main loop, possibly in a separate thread).
        *   **Modularity:** This separation ensures UI logic is distinct from core processing, simplifying maintenance and future replacement (e.g., with a web UI).
        *   *Fallback:* **Enhanced Console using `rich` in `dashboard_ui.py`**. Apply the same interaction pattern – `stress_monitor.py` calculates state, passes it to an update function in `dashboard_ui.py` that manages the `rich` display.
    *   **Display Content:** Show current overall state (e.g., "Calm", "Focused", "Stressed"), detected expression, movement level (e.g., "Low", "Medium", "High"), HR (BPM), Alpha/Beta ratio.

**5. Key Libraries (Additions):**
    *   `opencv-python` (for webcam access)
    *   Chosen CV library (`fer`, `deepface`, etc.) + its dependencies (e.g., `tensorflow`)
    *   Optional UI library (`rich`, `tkinter`, etc.)

**6. Implementation Steps:**
    *   Integrate ACC OSC handler and feature calculation.
    *   Add ACC baseline calculation.
    *   Choose and integrate CV library for expression detection (run in separate thread).
    *   Refine state logic to incorporate new inputs.
    *   Create `dashboard_ui.py` for UI components.
    *   Implement chosen UI dashboard approach within `dashboard_ui.py`.
    *   Test interactions between components.

---

## Phase 2 Progress Summary (as of 2025-04-13 ~03:30 AM)

**Key Accomplishments:**

1.  **Code Refactoring:**
    *   The original monolithic `stress_monitor.py` script has been successfully refactored into a modular Python package named `braintrade_monitor`.
    *   This package separates concerns into distinct modules: `config.py`, `data_store.py`, `feature_extraction.py`, `osc_handler.py`, `baseline.py`, `state_logic.py`, `processing.py`, `cv_handler.py`, and `logging_setup.py`.
    *   A new `main.py` script serves as the application entry point, orchestrating the modules.
2.  **UI Implementation & Integration:**
    *   A dedicated `dashboard_ui.py` file was created using `tkinter` to display the monitor's output.
    *   The UI was integrated with the core processing logic using a thread-safe `queue.Queue`.
    *   Threading issues specific to macOS UI updates were resolved by ensuring `tkinter` operations run exclusively on the main thread using `root.after()`.
3.  **Synthetic Data Generation:**
    *   A `send_synthetic_osc.py` script was created to simulate EEG, PPG, and ACC OSC data streams, enabling testing without physical hardware.
    *   Issues with data formatting (specifically EEG) in the synthetic sender were identified and corrected.
4.  **Accelerometer Integration:**
    *   Successfully integrated accelerometer data for movement detection.
    *   The real-time processing loop now calculates the movement metric.
    *   The `tkinter` UI displays the updating state, ratio, HR, and movement values.
5.  **Computer Vision Integration (Complete):**
    *   Successfully integrated computer vision for facial expression detection using the `fer` library. The webcam is now initializing, and the system is detecting facial expressions. Persistence logic has been implemented to improve stability.
6.  **State Logic Enhancement (Complete):**
    *   Updated the `state_logic.py` module to accept ACC and CV inputs.
    *   Refined the rules to incorporate these new inputs for determining the "Stress/Tilted", "Calm/Focused", and "Other/Uncertain" states.
    *   Added baseline calculation for movement data.
7.  **Core Functionality Testing:**
    *   The refactored application successfully runs using the synthetic data sender and live webcam input.
    *   Baseline calculation (using EEG ratio, PPG HR, and ACC movement) completes successfully.
    *   The real-time processing loop runs, calculates features (EEG ratio, PPG HR, movement, expression), determines state based on Phase 2 logic, and sends updates to the UI.
    *   The `tkinter` UI displays the updating state, ratio, HR, movement, and expression values.
    *   Unit tests have been added and are passing for `feature_extraction`, `state_logic`, `data_store`, and `baseline` modules.