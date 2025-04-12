# Changelog

## [Unreleased] - 2025-04-12

### Added
*   `check_osc.py` script for verifying OSC stream reception.
*   Plan document for real-time classifier (`docs/motor_imagery_classifier_plan.md`), including CSP option.
*   README.md and CHANGELOG.md files.

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

### Fixed
*   Resolved issues preventing OSC data collection in `motor_imagery_trainer.py` (scope issue with global flag, OSC argument count mismatch).
*   Fixed `NameError` for `event_id` in `motor_imagery_trainer.py`.
*   Corrected `try...except...finally` block structure in `motor_imagery_trainer.py`.
*   Adjusted `train_test_split` logic in `motor_imagery_trainer.py` to handle small sample sizes during testing better.