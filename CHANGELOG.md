# Changelog

## [Unreleased] - 2025-04-13 (Early Morning - Refactoring & Unit Tests)

### Refactored
*   **Modularized Codebase:** Refactored `stress_monitor.py` into a `braintrade_monitor` Python package with modules for config, data store, feature extraction, OSC handling, baseline, state logic, and processing.
*   **Main Script:** Created new `main.py` to orchestrate the modular application.

### Added
*   **Unit Tests:** Added comprehensive unit tests in the `tests/` directory for:
    *   `braintrade_monitor/feature_extraction.py` (9 tests)
    *   `braintrade_monitor/state_logic.py` (11 tests)
    *   `braintrade_monitor/data_store.py` (10 tests)
    *   `braintrade_monitor/baseline.py` (8 tests)

### Fixed
*   **apply_diff Indentation Issues:** Addressed potential indentation problems when using `apply_diff` tool by providing detailed guidelines in `docs/llm_collaboration_preferences.md`.
*   **EEG Data Handling:** Fixed issue in `send_synthetic_osc.py` where EEG data was being sent with incorrect formatting (flattened list), now sends sample-by-sample.
*   **MNE Filtering Error:** Fixed `ValueError` in `extract_alpha_beta_ratio` related to `picks='all'` argument in `mne.filter.filter_data`.
*   **Unit Test Errors:** Addressed `NameError` in `tests/test_feature_extraction.py` and `tests/test_baseline.py`, and `AssertionError` and `TypeError` in `tests/test_data_store.py` and `tests/test_processing.py`, resulting in all unit tests now passing.


*   **ACC Integration:** Successfully integrated accelerometer data for movement detection.

### Status
*   **Phase 3 In Progress:** Started implementing Phase 3, focusing on adding focus and fatigue detection using EEG Theta band analysis and EEG artifact detection for blink detection.

---
## [Unreleased] - 2025-04-13 (Midday - UI Improvements & Troubleshooting)

### Added
*   Implemented heuristic trade suggestions with confidence levels.
*   Integrated live BTC price display in the AssetChart.
*   Improved handling of BCI connection status and data availability in the UI.

### Fixed
*   Addressed a `NameError` in `processing.py` by initializing variables.

### Changed
*   Reduced log verbosity by commenting out frequent `DEBUG` messages in `osc_handler.py`, `data_store.py`, and `processing.py`.

### Known Issues
*   The AssetChart still uses simulated data for the chart line itself, but displays the real BTC price.
*   Further testing and refinement of the heuristic trade suggestion logic is needed.

---
## [Unreleased] - 2025-04-13 (Late Morning - Web UI Integration)

### Added
*   **Web UI Integration:** Integrated a React/TypeScript web UI, replacing the Tkinter UI.
    *   Created `web_server.py` to serve data to the web UI via a FastAPI endpoint.
    *   Modified `processing.py` to share state with the API server.
    *   Modified `web/src/contexts/BiomarkerContext.tsx` to fetch data from the API.

### Fixed
*   **CORS Issue:** Resolved a CORS issue by configuring the FastAPI server to allow requests from the frontend origin.
*   **PPG Data Flow:** Implemented a workaround in `osc_handler.py` to ensure PPG data is correctly received and processed.

### Changed
*   Updated `README.md` to reflect the new web UI and provide updated setup and running instructions.

### Known Issues
*   The unhandled OSC messages are still present and should be investigated.

---
## [Unreleased] - 2025-04-12 (Late Evening - Phase 1 Completion & Debugging)
:start_line:4
:end_line:6
-------

### Changed
*   Updated `README.md` to reflect that Phase 2 is now in progress.

### Added
*   **Debug Logging:** Added print statements and logging in `main()` and `calculate_baseline()` functions in `stress_monitor.py` to diagnose hanging issue.

### Changed
*   **Disabled File Logging:** Modified logging configuration in `stress_monitor.py` to only output to console, disabling file logging to address disk space issues.
*   **Simplified Baseline Loop (Initially):** Temporarily removed `time.sleep()` from the baseline data collection loop in `stress_monitor.py` for debugging (later re-enabled).
*   **Updated README.md:** Updated "Current Status" section to reflect Phase 1 completion, resolved hanging issue, and console logging.

### Fixed
*   **Resolved Hanging Issue:** Diagnosed and resolved the issue causing `stress_monitor.py` to hang during baseline calculation. The script now runs through baseline and enters real-time monitoring loop.

---

## [Unreleased] - 2025-04-12 (Late Night - Phase 2 Start)

### Added
*   **Project Pivot:** Shifted focus from Motor Imagery BCI to "BrainTrade - Mental State Monitor".
*   **New Goal:** Monitor trader's mental state (stress, focus, fatigue) using Muse EEG/PPG/ACC and potentially CV to provide feedback.
*   **Project Plans:**
    *   Created overall roadmap: `docs/braintrade_monitor_plan.md`.
    *   Created detailed phase plans:
        *   `docs/phase1_stress_meter_plan.md`
        *   `docs/phase2_dashboard_plan.md`
        *   `docs/phase3_focus_guardian_plan.md`
        *   `docs/phase4_advanced_indicators_plan.md` (Stretch Goal)
        *   `docs/phase5_web_ui_plan.md` (Future Enhancement)
*   **Core Script:** Created `stress_monitor.py` for real-time monitoring.
*   **PPG Prototype:** Created `test_ppg_bpm.py` to prototype BPM estimation from PPG.
*   **OSC Handling:** Implemented OSC listeners for `/eeg` and `/ppg` in `stress_monitor.py`. Confirmed data reception.
*   **Baseline Logic:** Implemented baseline calculation structure (median/std dev) in `stress_monitor.py`.
*   **Feature Extraction:** Added `extract_alpha_beta_ratio` and `estimate_bpm_from_ppg` functions to `stress_monitor.py`.

### Changed
*   **Archived Old Files:** Moved previous motor imagery scripts (`motor_imagery_trainer.py`, `motor_imagery_classifier.py`, `combined_trainer.py`, `data_collector.py`) and related plans/logs to the `old/` directory.
*   Updated `README.md` to reflect the new project focus and status.

### Fixed
*   Addressed `RuntimeWarning` in `extract_alpha_beta_ratio` by specifying IIR filter parameters (though this change was interrupted and needs re-verification/fixing).

---

## [Previous] - 2025-04-12 (Afternoon - Motor Imagery)

### Added
*   `check_osc.py` script for verifying OSC stream reception.
*   Plan document for real-time classifier (`docs/motor_imagery_classifier_plan.md`), including CSP option.
*   README.md and CHANGELOG.md files.
*   Multi-session training workflow (`data_collector.py`, `combined_trainer.py`) and documentation updates.
*   Markdown logging to trainer scripts.
*   SVM classifier option to `combined_trainer.py`.

### Changed
*   Refactored `motor_imagery_trainer.py` to use OSC/Muse Direct for data acquisition instead of BrainFlow direct connection.
    *   Removed BrainFlow dependency and related code.
    *   Integrated `python-osc` library for OSC server.
    *   Added `--sampling-rate` as a required argument.
    *   Modified data collection logic to work with OSC handlers and timing flags.
    *   Adapted MNE processing to use `EpochsArray` created from collected segments.
    *   Updated saved model artifacts structure.
*   Updated `docs/motor_imagery_mne_plan.md` and `docs/motor_imagery_detailed_plan_v3.md` to reflect OSC changes.
*   Added `python-osc` to `requirements.txt`.
*   Modified `combined_trainer.py` to handle epoch length differences via cropping.

### Fixed
*   Resolved issues preventing OSC data collection in `motor_imagery_trainer.py` (scope issue with global flag, OSC argument count mismatch).
*   Fixed `NameError` for `event_id` in `motor_imagery_trainer.py`.
*   Corrected `try...except...finally` block structure in `motor_imagery_trainer.py`.
*   Adjusted `train_test_split` logic in `motor_imagery_trainer.py` to handle small sample sizes during testing better.
*   Fixed various `AttributeError` and `NameError` issues in `combined_trainer.py` related to missing arguments and variables during artifact saving.
*   Fixed `ValueError` in `extract_band_power_features` (in trainer scripts) when encountering short epochs by dynamically adjusting `n_fft`.
*   Fixed `NameError` for `csp_plot_filename` during logging in `combined_trainer.py`.