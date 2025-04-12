# Detailed Plan: Motor Imagery (Left vs. Right) - v3.1 (OSC/MNE Focus)

**Based on:** `docs/motor_imagery_mne_plan.md` (v2.1)

**Goal:** Attempt to train a classifier to distinguish imagined left vs. right hand movement using EEG data, leveraging **MNE-Python for offline analysis/training** and **OSC/Muse Direct for data acquisition** in both training and real-time classification.

**Disclaimer:** Reliably detecting motor imagery with consumer EEG like Muse S is challenging. Success is not guaranteed.

---

## Phase 1: Offline Training (`motor_imagery_trainer.py`)

This script handles data acquisition via OSC and model training using MNE.

```mermaid
graph TD
    subgraph Trainer Script (OSC/MNE)
        direction LR
        A[Start Trainer] --> B(Parse CLI Args);
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
        K --> L{Feature Method?};
        L -- Bandpower --> L1(Extract Log Band Power - MNE);
        L -- CSP --> L2(Fit & Apply CSP - MNE);
        L1 --> M(Select Features/Channels);
        L2 --> M;
        M --> N(Train Classifier - Sklearn);
        N --> O(Evaluate Classifier);
        O --> P[Save Training Artifacts];
        P --> Q[Shutdown OSC Server];
        Q --> R[End Trainer];
    end
```

**Detailed Steps for `motor_imagery_trainer.py`:**

1.  **Dependencies:** Ensure `python-osc`, `numpy`, `mne`, `scikit-learn`, `joblib` are in `requirements.txt`.
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
    *   `--tmin` (float, default: 0.5) - *Note: In OSC approach, this defines epoch extraction *relative to the start of the collected segment*, not an external marker.*
    *   `--tmax` (float, default: 3.5) - *Note: In OSC approach, this defines epoch extraction *relative to the start of the collected segment*.*
    *   `--feature-method` (str, choices=['bandpower', 'csp'], default='bandpower')
    *   `--csp-components` (int, default: 4)
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
        *   Use `time.sleep` for timing (`cue_duration`, `imagery_duration`, `rest_duration`).
        *   Use `data_collection_active` flag and `data_lock` to control when `handle_eeg` stores data into buffers (only during `imagery_duration`).
        *   After `imagery_duration`, retrieve the collected segment from buffers, store it with its label.
        *   Check and print headband status warnings.
5.  **Data Consolidation & MNE Epochs:**
    *   Check if any segments were collected.
    *   Determine minimum segment length across all collected trials.
    *   Create `epochs_data_np` by stacking segments (trimmed to min length). Shape `(n_epochs, n_channels, n_times)`.
    *   Create `mne.Info` (using generic or known channel names, `--sampling-rate`).
    *   Create `events_np` array (sample number is index * min_segment_len, event ID is the stored label).
    *   Define `event_id = {'Left': LEFT_MARKER, 'Right': RIGHT_MARKER}`.
    *   Create `epochs = mne.EpochsArray(...)`.
6.  **Preprocess Data (MNE):**
    *   Apply bandpass filter *to the epochs object*: `epochs.filter(...)`. Record `filter_phase`.
    *   *(Optional)* ICA would also be applied to the `epochs` object.
7.  **Extract Features (MNE):**
    *   Get filtered data: `epochs_data_filtered = epochs.get_data()`.
    *   **If `args.feature_method == 'bandpower'`:**
        *   Call `extract_band_power_features(epochs_data_filtered, ...)`. Let result be `X`.
    *   **If `args.feature_method == 'csp'`:**
        *   Initialize `csp = mne.decoding.CSP(...)`.
        *   Fit and transform: `X = csp.fit_transform(epochs_data_filtered, epochs.events[:, -1])`.
8.  **Select Features/Channels (Analysis):**
    *   *(Initial)* Use all channels/components. `selected_channel_indices = list(range(NUM_EEG_CHANNELS))`.
9.  **Train Classifier (Scikit-learn):**
    *   Get labels: `y = epochs.events[:, -1]`.
    *   Prepare feature matrix `X`.
    *   Split data (handle small N): `train_test_split(X, y, ...)`.
    *   Create pipeline: `pipe = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])`.
    *   Fit pipeline: `pipe.fit(X_train, y_train)`.
10. **Evaluate Classifier:**
    *   Predict on test data (if available): `y_pred = pipe.predict(X_test)`.
    *   Calculate and print accuracy score and classification report.
11. **Save Training Artifacts:**
    *   Create `artifacts` dictionary (see previous plan). Include `csp` object if used.
    *   Save using `joblib.dump()`.
12. **Shutdown:**
    *   Use `try...except...finally` to ensure `osc_server_instance.shutdown()` is called.

---

## Phase 2: Real-time Classification (`motor_imagery_classifier.py`)

This script loads the trained model and applies it to live OSC data.

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
        I --> J(Predict - Loaded Model);
        J --> K[Display Prediction];
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
    *   Extract all parameters (model pipeline, sampling_rate, filter params, feature_method, bands/csp object, tmin, tmax, etc.).
4.  **OSC Setup:**
    *   Define global data structures (deques, lock).
    *   Implement OSC handlers (`handle_eeg`, `handle_horseshoe`).
    *   Start OSC server thread using `start_osc_server`.
5.  **Real-time Loop:**
    *   Calculate `window_duration = tmax - tmin`.
    *   Calculate `window_samples = int(window_duration * sampling_rate)`.
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
        *   **Predict:** `prediction = model.named_steps['clf'].predict(scaled_features)[0]`.
        *   **Display Prediction:** Convert marker to label and print. Print headband status warning if needed.
6.  **Shutdown:**
    *   Catch `KeyboardInterrupt`.
    *   In `finally`: `osc_server_instance.shutdown()`.

---

## Filter Implementation Verification

*   Still relevant, but now comparing MNE filtering on epochs vs. MNE filtering on raw windowed data (`mne.filter.filter_data`). Differences should be minimal if parameters match.

---