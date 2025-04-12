# Detailed Plan: Motor Imagery (Left vs. Right) - v3.3 (OSC/MNE Focus - Dual Model, Proba Vis)

**Based on:** `docs/motor_imagery_mne_plan.md` (v2.1)

**Goal:** Attempt to train classifiers to distinguish imagined left vs. right hand movement using EEG data, leveraging **MNE-Python for offline analysis/training** and **OSC/Muse Direct for data acquisition**. This version trains and evaluates **both Band Power and CSP** feature-based models from the same session data. The real-time classifier uses probability estimates for visualization.

**Disclaimer:** Reliably detecting motor imagery with consumer EEG like Muse S is challenging. Success is not guaranteed.

---

## Phase 1: Offline Training (`motor_imagery_trainer.py`)

This script handles data acquisition via OSC, trains both Band Power and CSP models using MNE and Scikit-learn, evaluates them using cross-validation, and saves separate artifacts for each.

```mermaid
graph TD
    subgraph Trainer Script (OSC/MNE - Dual Model Training)
        direction LR
        A[Start Trainer] --> B(Parse CLI Args - Incl. cv-folds);
        B --> C[Start OSC Server Thread];
        C --> D{Run Acquisition Paradigm};
        D -- For Each Trial --> E[Display Cue];
        E --> F[Sleep (Imagery Duration)];
        F --> G[Collect Data Segment (from OSC Buffers)];
        G --> H[Store Segment & Label];
        H --> D;
        D -- Loop End --> I[Consolidate Data];
        I --> J(Create MNE EpochsArray);
        J --> K(Preprocess Data - Filter Epochs - MNE);

        subgraph Band Power Path
            K --> L1(Extract Log Band Power - MNE);
            L1 --> M1(Define BP Pipeline);
            M1 --> N1(Evaluate BP Pipeline - CV);
            N1 --> O1(Retrain BP Pipeline - Full Data);
            O1 --> P1[Save BP Artifacts (incl. CV scores)];
        end

        subgraph CSP Path
            K --> L2(Fit & Apply CSP - MNE);
            L2 --> L2_Vis(Visualize CSP Patterns);
            L2_Vis --> M2(Define CSP Pipeline);
            M2 --> N2(Evaluate CSP Pipeline - CV);
            N2 --> O2(Retrain CSP Pipeline - Full Data);
            O2 --> P2[Save CSP Artifacts (incl. CV scores)];
        end

        P1 --> Q[Shutdown OSC Server];
        P2 --> Q;
        Q --> R[End Trainer];
    end
```

**Detailed Steps for `motor_imagery_trainer.py`:**

1.  **Dependencies:** Ensure `python-osc`, `numpy`, `mne`, `scikit-learn`, `joblib`, `matplotlib` are in `requirements.txt`. (Consider setting matplotlib backend to 'Agg' for non-interactive saving).
2.  **CLI Arguments (`argparse`):**
    *   `--osc-ip` (str, default: "0.0.0.0")
    *   `--osc-port` (int, default: 5001)
    *   `--session-name` (str, required)
    *   `--num-trials` (int, default: 20)
    *   `--cue-duration` (float, default: 2.0)
    *   `--imagery-duration` (float, default: 4.0)
    *   `--rest-duration` (float, default: 3.0)
    *   `--output-dir` (str, default: "training_data")
    *   `--sampling-rate` (float, required) - Crucial for OSC data interpretation.
    *   `--filter-low` (float, default: 8.0)
    *   `--filter-high` (float, default: 30.0)
    *   `--tmin` (float, default: 0.5) - *Note: In OSC approach, defines epoch extraction *relative to the start of the collected segment*.*
    *   `--tmax` (float, default: 3.5) - *Note: In OSC approach, defines epoch extraction *relative to the start of the collected segment*.*
    *   `--csp-components` (int, default: 4)
    *   `--cv-folds` (int, default: 5) - Number of folds for cross-validation evaluation.
3.  **OSC Setup:**
    *   Define global data structures (deques for EEG/horseshoe, lock, `data_collection_active` flag).
    *   Implement OSC handlers (`handle_eeg`, `handle_horseshoe`, `handle_default`).
    *   Implement `start_osc_server` function to run the server in a thread.
4.  **Acquisition Paradigm:**
    *   Start OSC server thread.
    *   Define marker values: `LEFT_MARKER = 1`, `RIGHT_MARKER = 2`.
    *   Create and shuffle trial labels.
    *   Loop through trials:
        *   Display cues ("Get Ready", "Cue: Left/Right. Imagine...", "Rest...").
        *   Use `time.sleep` for timing.
        *   Use `data_collection_active` flag and `data_lock` to control data buffering during `imagery_duration`.
        *   After `imagery_duration`, retrieve the collected segment, store it with its label.
        *   Check and print headband status warnings.
5.  **Data Consolidation & MNE Epochs:**
    *   Check if any segments were collected.
    *   Determine minimum segment length.
    *   Create `epochs_data_np` by stacking segments.
    *   Create `mne.Info`.
    *   Create `events_np` array.
    *   Define `event_id = {'Left': LEFT_MARKER, 'Right': RIGHT_MARKER}`.
    *   Create `epochs = mne.EpochsArray(...)`.
6.  **Preprocess Data (MNE):**
    *   Apply bandpass filter *to the epochs object*: `epochs.filter(...)`. Record `filter_phase`.
7.  **Extract Features (MNE):**
    *   Get filtered data: `epochs_data_filtered = epochs.get_data()`.
    *   Get labels: `y = epochs.events[:, -1]`.
    *   **Band Power Path:** Call `extract_band_power_features(epochs_data_filtered, ...)`. Result `X_bp`.
    *   **CSP Path:**
        *   Initialize `csp = mne.decoding.CSP(n_components=args.csp_components, reg=None, log=True, norm_trace=False)`.
        *   Fit and transform: `X_csp = csp.fit_transform(epochs_data_filtered, y)`. Save the *fitted* `csp` object.
        *   **Visualize CSP Patterns:**
            *   `try:`
                *   `fig = csp.plot_patterns(epochs.info, ch_type='eeg', show_names=True, units='Patterns (AU)', size=1.5)`
                *   `csp_plot_filename = f"{args.output_dir}/{args.session_name}_csp_patterns.png"`
                *   `fig.savefig(csp_plot_filename)`
                *   `print(f"Saved CSP patterns plot to: {csp_plot_filename}")`
                *   `plt.close(fig)` # Close figure to free memory
            *   `except Exception as e:`
                *   `print(f"Warning: Could not plot/save CSP patterns: {e}")`
8.  **Define Classifier Pipelines:**
    *   `pipe_bp = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])`.
    *   `pipe_csp = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])`.
9.  **Evaluate Classifiers using Cross-Validation:**
    *   `n_splits = args.cv_folds`.
    *   `scoring_metrics = ['accuracy', 'f1', 'roc_auc']`.
    *   **Evaluate Band Power:**
        *   `cv_results_bp = cross_validate(pipe_bp, X_bp, y, cv=n_splits, scoring=scoring_metrics)`
        *   Print mean/std for accuracy, f1, roc_auc from `cv_results_bp`.
    *   **Evaluate CSP:**
        *   `cv_results_csp = cross_validate(pipe_csp, X_csp, y, cv=n_splits, scoring=scoring_metrics)`
        *   Print mean/std for accuracy, f1, roc_auc from `cv_results_csp`.
10. **Retrain and Save Training Artifacts:**
    *   **Retrain Final Models:** `pipe_bp.fit(X_bp, y)`, `pipe_csp.fit(X_csp, y)`.
    *   **Save Band Power Artifacts:**
        *   Create `artifacts_bp` dictionary including: retrained `pipe_bp`, parameters (`sampling_rate`, `filter_params`, `tmin`, `tmax`, `bands`, `ch_names`), `feature_method='bandpower'`, and mean/std CV scores (`cv_accuracy_mean`, `cv_accuracy_std`, `cv_f1_mean`, `cv_f1_std`, `cv_auc_mean`, `cv_auc_std`) from `cv_results_bp`.
        *   Save to `f"{args.output_dir}/{args.session_name}_bandpower_model.joblib"`.
    *   **Save CSP Artifacts:**
        *   Create `artifacts_csp` dictionary including: retrained `pipe_csp`, the *fitted* `csp` object, parameters (`sampling_rate`, `filter_params`, `tmin`, `tmax`, `csp_components`, `ch_names`), `feature_method='csp'`, and mean/std CV scores from `cv_results_csp`.
        *   Save to `f"{args.output_dir}/{args.session_name}_csp_model.joblib"`.
    *   Print paths to both saved files.
11. **Shutdown:**
    *   Use `try...except...finally` to ensure `osc_server_instance.shutdown()` is called.

---

## Phase 2: Real-time Classification (`motor_imagery_classifier.py`)

This script loads a trained model artifact and applies it to live OSC data, displaying predictions with a probability-based confidence bar.

```mermaid
graph TD
    subgraph Classifier Script (OSC/MNE)
        direction LR
        A[Start Classifier] --> B(Parse CLI Args);
        B --> C(Load Training Artifacts);
        C --> D[Start OSC Server Thread];
        D --> E{Real-time Loop};
        E --> F[Get EEG Window (OSC Buffers)];
        F --> G(Apply Preprocessing - MNE Filter);
        G --> H{Feature Method?};
        H -- Bandpower --> H1(Extract Log Band Power - MNE Func);
        H -- CSP --> H2(Apply CSP Transform - Loaded CSP Obj);
        H1 --> I(Scale Features);
        H2 --> I;
        I --> J(Predict Proba - Loaded Model);
        J --> K[Display Prediction & Confidence Bar];
        K --> E;
        E -- Ctrl+C --> L[Shutdown OSC Server];
        L --> M[End Classifier];
    end
```

**Detailed Steps for `motor_imagery_classifier.py`:**

1.  **Dependencies:** Ensure `python-osc`, `numpy`, `mne`, `scikit-learn`, `joblib` are installed.
2.  **CLI Arguments (`argparse`):**
    *   `--model-file` (str, required)
    *   `--osc-ip` (str, default: "0.0.0.0")
    *   `--osc-port` (int, default: 5001)
    *   `--update-interval` (float, default: 0.5)
3.  **Load Training Artifacts:**
    *   Load dictionary: `artifacts = joblib.load(args.model_file)`.
    *   Extract all parameters (model pipeline, sampling_rate, filter params, feature_method, bands/csp object, tmin, tmax, etc.). *(Optionally print loaded CV scores)*
4.  **OSC Setup:**
    *   Define global data structures (deques, lock).
    *   Implement OSC handlers (`handle_eeg`, `handle_horseshoe`).
    *   Start OSC server thread using `start_osc_server`.
5.  **Real-time Loop:**
    *   Calculate `window_duration = tmax - tmin`.
    *   Calculate `window_samples = int(window_duration * sampling_rate)`.
    *   Define visualization parameters (e.g., `bar_width = 20`).
    *   Loop:
        *   `time.sleep(args.update_interval)`.
        *   Acquire lock, check buffer length, get latest `window_samples` into `window_data_np`. Check horseshoe. Release lock.
        *   Handle potential NaNs in `window_data_np`.
        *   **Apply Preprocessing (MNE):** Filter `window_data_np` using `mne.filter.filter_data` with loaded parameters.
        *   **Extract Features (Method-Dependent):**
            *   Reshape filtered window to `(1, n_channels, window_samples)`.
            *   If `feature_method == 'bandpower'`: Call `extract_band_power_features`.
            *   If `feature_method == 'csp'`: Apply `loaded_csp.transform()`.
        *   **Scale Features:** `scaled_features = model.named_steps['scaler'].transform(features)`.
        *   **Predict Probabilities:** `probabilities = model.named_steps['clf'].predict_proba(scaled_features)[0]` (Result: `[prob_left, prob_right]`).
        *   **Determine Label & Confidence:**
            *   `predicted_class_index = np.argmax(probabilities)`
            *   `prediction_label = "Right" if predicted_class_index == 1 else "Left"` (Assuming class 1 is Right)
            *   `right_probability = probabilities[1]`
        *   **Create Visualization Bar:**
            *   Calculate bar fills based on `right_probability` (0.0 to 1.0) and `bar_width`.
            *   Construct `bar_str` (e.g., `[####|##########]`).
        *   **Display Prediction & Bar:**
            *   Print `prediction_label`.
            *   Print `bar_str` and the numeric probability (e.g., `Confidence: [####|##########] (R: {right_probability:.2f})`).
            *   Print headband status warning if needed.
6.  **Shutdown:**
    *   Catch `KeyboardInterrupt`.
    *   In `finally`: `osc_server_instance.shutdown()`.

---

## Filter Implementation Verification

*   Still relevant, but now comparing MNE filtering on epochs vs. MNE filtering on raw windowed data (`mne.filter.filter_data`). Differences should be minimal if parameters match.

---