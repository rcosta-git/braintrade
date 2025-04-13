# Detailed Plan: Motor Imagery (Left vs. Right) - v3.4 (OSC/MNE Focus - Multi-Session Option)

**Based on:** `docs/motor_imagery_mne_plan.md` (v2.1)

**Goal:** Attempt to train classifiers to distinguish imagined left vs. right hand movement using EEG data, leveraging **MNE-Python for offline analysis/training** and **OSC/Muse Direct for data acquisition**. This document outlines two primary workflows:
1.  **Single-Session Training:** Collect data and train models within a single script run (`motor_imagery_trainer.py`).
2.  **Multi-Session Training:** Collect data over multiple shorter sessions (`data_collector.py`) and then combine data for training (`combined_trainer.py`).

**Disclaimer:** Reliably detecting motor imagery with consumer EEG like Muse S is challenging. Success is not guaranteed.

---

## Phase 1a: Single-Session Offline Training (`motor_imagery_trainer.py`)

This script handles data acquisition via OSC, trains both Band Power and CSP models using MNE and Scikit-learn, evaluates them using cross-validation, and saves separate artifacts for each, all within a single run.

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
    *   `--log-file` (str, default='training_log.md') - Path to Markdown log file.
3.  **OSC Setup:** Define buffers, lock, handlers, start server thread.
4.  **Acquisition Paradigm:** Run trials, display cues (updated descriptive text), collect segments during imagery, store segments and labels.
5.  **Data Consolidation & MNE Epochs:** Create `epochs = mne.EpochsArray(...)` with standard montage.
6.  **Preprocess Data (MNE):** Apply bandpass filter to `epochs` object.
7.  **Extract Features (MNE):** Calculate Band Power (`X_bp`) and fit/transform CSP (`X_csp`). Visualize CSP patterns.
8.  **Define Classifier Pipelines:** `pipe_bp` and `pipe_csp` (Scaler + LDA).
9.  **Evaluate Classifiers using Cross-Validation:** Use `cross_validate` with `cv=n_splits` (dynamically adjusted). Print Accuracy, F1, AUC results.
10. **Retrain and Save Training Artifacts:** Retrain `pipe_bp` and `pipe_csp` on full dataset. Save separate `_bandpower_model.joblib` and `_csp_model.joblib` files containing models, parameters, and CV scores.
11. **Logging:** Append session parameters, CV results, and model filenames to the Markdown log file.
12. **Shutdown:** Ensure OSC server shutdown.

---

## Phase 1b: Multi-Session Workflow (Alternative)

This workflow separates data collection into multiple shorter sessions and allows combining data afterwards for training. This can help mitigate user fatigue and potentially build more robust models by leveraging more total data.

**Workflow:**

1.  **Collect Data:** Run `data_collector.py` (script to be created) for each desired session. This script runs the paradigm and saves the filtered MNE Epochs object for that session (e.g., `session1_epo.fif`, `session2_epo.fif`).
2.  **Train Combined Model:** Run `combined_trainer.py` (script to be created), providing the paths to the `_epo.fif` files you want to combine. This script loads the epochs, concatenates them, trains models (BP & CSP) on the combined data, evaluates using CV, saves a single set of combined model artifacts (e.g., `combined_model_csp.joblib`), and logs the results.
3.  **Classify:** Use the combined model artifact with the existing `motor_imagery_classifier.py`.

**Plan for `data_collector.py`:**

*   Based on `motor_imagery_trainer.py`.
*   **Arguments:** Keep paradigm, filtering, session naming args. Remove model training args.
*   **Functionality:** OSC setup, paradigm loop, data consolidation, MNE Epochs creation, filtering.
*   **Output:** Saves the filtered `mne.Epochs` object to `<session_name>_epo.fif`.
*   **Removes:** Feature extraction, CV, model training, artifact saving (`.joblib`), logging.

**Plan for `combined_trainer.py`:**

*   New script.
*   **Arguments:** `--epoch-files` (list of `_epo.fif` paths), `--combined-session-name`, `--output-dir`, model params (`--csp-components`, `--cv-folds`), `--log-file`.
*   **Functionality:**
    *   Load specified `_epo.fif` files using `mne.read_epochs()`.
    *   Check compatibility (sfreq, ch_names).
    *   Concatenate epochs using `mne.concatenate_epochs()`.
    *   Extract features (BP & CSP) from combined data.
    *   Visualize CSP patterns from combined data.
    *   Define pipelines.
    *   Evaluate using `cross_validate` on combined data.
    *   Retrain pipelines on full combined data.
    *   Save *single* set of combined model artifacts (`.joblib`) using `--combined-session-name`. Include parameters (like source epoch files) and CV scores.
    *   Append results to log file.

---

## Phase 2: Real-time Classification (`motor_imagery_classifier.py`)

This script loads a trained model artifact (either single-session or combined) and applies it to live OSC data, displaying predictions with a probability-based confidence bar.

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
4.  **OSC Setup:** Define buffers, lock, handlers, start server thread.
5.  **Real-time Loop:**
    *   Calculate `window_duration`, `window_samples`. Define `bar_width`.
    *   Loop:
        *   Sleep, get data window (`window_data_np`), check horseshoe.
        *   Handle NaNs.
        *   Apply Preprocessing (`mne.filter.filter_data`).
        *   Extract Features (Band Power or CSP based on `feature_method`).
        *   Scale Features.
        *   Predict Probabilities (`predict_proba`).
        *   Determine Label & Confidence.
        *   Create Visualization Bar.
        *   Display Prediction & Bar.
6.  **Shutdown:** Catch `KeyboardInterrupt`, shutdown server.

---

## Filter Implementation Verification

*   Still relevant, especially when comparing filtering in `data_collector.py` vs. `motor_imagery_classifier.py`. Differences should be minimal if parameters match.

---