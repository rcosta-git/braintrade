# Motor Imagery Lite (Left vs. Right) - Detailed Implementation Plan (v2.1 - OSC/MNE Enhanced Training)

---

## 1. Goal

Attempt to train a classifier to distinguish imagined left vs. right hand movement using EEG data, leveraging **MNE-Python for offline analysis, feature extraction, and model training**. Use the trained model for real-time classification using OSC/Muse Direct.

**Disclaimer:** Reliably detecting motor imagery with consumer EEG like Muse S is very challenging. Success is not guaranteed.

---

## 2. Core Features

- **Data Acquisition Mode (`motor_imagery_trainer.py`):** Record labeled EEG data during cued motor imagery tasks using OSC/Muse Direct.
- **Offline Training Phase (`motor_imagery_trainer.py`):**
  - Load data segments collected via OSC into MNE-Python.
  - Preprocess (filter, optional artifact rejection) using MNE.
  - Epoch data using MNE (likely `EpochsArray` from segments).
  - Extract features (e.g., Log Band Power, CSP) using MNE's tools.
  - Perform channel/feature selection analysis using MNE visualizations or statistics (if applicable).
  - Train a classifier (e.g., LDA) using `scikit-learn` on MNE-derived features.
  - Save the trained model and necessary parameters (e.g., sampling rate, filter params, feature method, CSP object if used, scaling info).
- **Real-time Classification Mode (`motor_imagery_classifier.py` - Planned):**
  - Load the trained model and parameters.
  - Stream live EEG data using OSC/Muse Direct.
  - Apply the *same* preprocessing and feature extraction steps (implemented using MNE/NumPy) as determined during the MNE training phase.
  - Predict the imagined movement using the loaded model.
  - Display the prediction.

---

## 3. Technical Design

### Architecture

- **`motor_imagery_trainer.py`:** OSC/Muse Direct for acquisition, **MNE-Python + Scikit-learn** for offline processing and training.
- **`motor_imagery_classifier.py` (Planned):** **OSC/Muse Direct + MNE + Scikit-learn** for real-time application of the trained model.

---

### Data Acquisition (`motor_imagery_trainer.py`)

- **Paradigm:** Cued trials (LEFT/RIGHT/REST) timed within the script.
- **EEG Recording:** OSC streaming via Muse Direct, associate data segments with timed cues based on collection flags, process segments in memory (raw data not saved centrally by default).

---

### Offline Training Phase (`motor_imagery_trainer.py` - MNE Enhanced)

- **Dependencies:** Add `python-osc`, `mne`, `scikit-learn`, `joblib` to `requirements.txt`. (Remove `brainflow` if no longer used elsewhere).
- **Load Data into MNE:** Collect segments via OSC handler, create `mne.EpochsArray` from segments and manually created events array. Requires known `sampling_rate`.
- **Preprocessing with MNE:** `epochs.filter(l_freq=8, h_freq=30)`, *(Optional)* `mne.preprocessing.ICA` (applied to Epochs).
- **Feature Extraction with MNE:**
    - **Band Power:** Calculate PSD per epoch (`mne.time_frequency.psd_array_welch`), extract Alpha/Beta band power, apply log transform (optional).
    - **CSP (Optional):** Fit `mne.decoding.CSP` on filtered epochs data. `csp.fit_transform(epochs_data, labels)`.
- **Channel/Feature Selection Analysis (MNE):** (May be less critical if using all 4 channels, but could analyze feature importance).
- **Model Training (`scikit-learn`):** Prepare `X` (features), `y` (labels). Apply `StandardScaler`. Train `LinearDiscriminantAnalysis`. Evaluate score.
- **Save Artifacts:** Save `model` (pipeline), `scaler`, `sampling_rate`, filter params, feature params (`bands` or `csp` object), `channel_names`, etc. (`joblib`).

---

### Real-time Classification (`motor_imagery_classifier.py`)

- **Dependencies:** `python-osc`, `numpy`, `mne`, `scikit-learn`, `joblib`.
- **Initialization:** Start OSC Server. Load `model`, `scaler`, `sampling_rate`, filter params, feature params (`bands` or `csp` object), etc. from artifact file. Calculate `window_samples`.
- **Main Loop:**
  - `time.sleep(update_interval)`.
  - Get EEG window (from OSC data buffers).
  - **Apply Preprocessing (MNE):** Implement identical filtering using loaded parameters (`mne.filter.filter_data`).
  - **Extract Features (MNE/NumPy):** Implement identical feature calculation (Band Power or CSP Transform) using loaded parameters/objects. Reshape data to `(1, n_channels, n_times)`.
  - **Scale Features:** `scaler.transform()`.
  - **Predict:** `model.predict()`.
  - **Display:** Show prediction.
- **Shutdown:** Handle `KeyboardInterrupt`.

---

### CLI Arguments

- **Trainer:** `--session-name` (req), `--sampling-rate` (req), `--osc-ip`, `--osc-port`, durations, `--num-trials`, `--output-dir`, `--feature-method`, `--csp-components`.
- **Classifier:** `--model-file` (req), `--osc-ip`, `--osc-port`, `--update-interval`.

---

## 4. Development Steps

1.  **Trainer Script:** Implement OSC acquisition, MNE EpochsArray creation, processing/feature extraction (Band Power/CSP), Scikit-learn training/evaluation, saving artifacts. (Largely Done)
2.  **Classifier Script:** Implement OSC streaming, loading artifacts, real-time windowing, preprocessing/feature extraction (matching training), scaling, prediction, display, shutdown. (To Do)
3.  **Testing & Iteration:** Test trainer with real data. Test real-time classifier. Refine parameters or features if needed.

---

## 5. Workflow Diagrams

### Trainer (OSC/MNE Enhanced)

```mermaid
graph TD
    A[Start Trainer] --> B(Parse Args);
    B --> C[Start OSC Server Thread];
    C --> D{Run Trial Loop};
    D -- For Each Trial --> E[Display Cue];
    E --> F[Sleep (Imagery Duration)];
    F --> G[Collect Data Segment (from OSC Buffers)];
    G --> H[Store Segment & Label];
    H --> D;
    D -- Loop End --> I[Consolidate Data];
    I --> J[Create MNE EpochsArray];
    J --> K[Preprocess (Filter) (MNE)];
    K --> L[Extract Features (Band Power/CSP) (MNE)];
    L --> M[Analyze/Select Channels/Features (MNE Viz/Stats)];
    M --> N[Prepare Feature Matrix X, Labels y];
    N --> O[Split Train/Test Data];
    O --> P[Fit Scaler (sklearn)];
    P --> Q[Train Classifier (LDA) (sklearn)];
    Q --> R[Evaluate Accuracy (sklearn)];
    R --> S[Save Model, Scaler, Params (joblib)];
    S --> T[Shutdown OSC Server];
    T --> U[End];
```

### Classifier

```mermaid
graph TD
    A[Start Classifier] --> B(Parse Args);
    B --> C[Load Model & Params (joblib)];
    C --> D[Start OSC Server Thread];
    D --> E{Real-time Loop};
    E --> F[Get EEG Window (from OSC Buffers)];
    F --> G[Filter & Extract Features (MNE/NumPy - matching training)];
    G --> H[Scale Features (scaler.transform)];
    H --> I[Predict State (model.predict)];
    I --> J[Display Prediction];
    J --> E;
    E -- Ctrl+C --> K[Shutdown OSC Server & Exit];
```

---

## 6. Future Enhancements

- More advanced features (other than Band Power/CSP).
- Different classifiers (SVM, NN).
- Online adaptation.
- Control simple applications.
- More robust handling of OSC data timing/loss.