# Plan: Real-time Motor Imagery Classifier (`motor_imagery_classifier.py`)

## 1. Goal

Create a Python script that connects to a Muse S headset via OSC (using Muse Direct), loads a pre-trained motor imagery classifier model (trained using either Band Power or CSP features), processes incoming EEG data in real-time using the corresponding feature extraction method, and displays the predicted mental state (Left vs. Right hand imagery).

## 2. Data Flow

```mermaid
graph LR
    A[Muse S Headband] -->|Bluetooth| B(Muse Direct App);
    B -->|OSC/UDP over Wi-Fi| C{Python Script (motor_imagery_classifier.py)};
    C -- acts as --> D[OSC Server];
    D -- continuously updates --> E[Data Buffers];
    C -- loads --> F[Trained Model Artifact (.joblib)];
    F -- contains --> F1(Classifier Pipeline);
    F -- contains --> F2(Preprocessing Params);
    F -- contains --> F3(Feature Method Info);
    F -- contains --> F4(Band Defs / CSP Object);
    C -- periodically runs --> G[Real-time Loop];
    G -- grabs --> H[Latest Data Window];
    G -- uses F2 --> I{Preprocessing (Filtering)};
    I -- uses F3 & F4 --> J{Feature Extraction (Band Power OR CSP Transform)};
    J -- feeds features to --> K[Loaded Classifier Pipeline];
    K -- outputs --> L[Prediction (1 or 2)];
    G -- displays --> M[Output: "Left" / "Right"];
```

## 3. Core Components & Logic

### 3.1. Setup & Configuration
*   **Argument Parsing (`argparse`):**
    *   `--model-file`: (Required) Path to the `.joblib` file containing the trained model and parameters.
    *   `--osc-ip`: IP address for the OSC server to listen on (Default: "0.0.0.0").
    *   `--osc-port`: UDP port for the OSC server (Default: 5001).
    *   `--update-interval`: Frequency (in seconds) for making predictions (Default: 0.5).
*   **Load Model Artifacts (`joblib`):**
    *   Load the dictionary from the specified model file.
    *   Extract necessary components:
        *   `model`: The scikit-learn pipeline object (scaler + classifier).
        *   `sampling_rate`: EEG sampling frequency (Hz).
        *   `filter_low`, `filter_high`, `filter_phase`: Bandpass filter parameters.
        *   `tmin`, `tmax`: Training epoch time window relative to event onset (used to determine real-time window duration).
        *   `feature_method`: The method used ('bandpower' or 'csp').
        *   `bands`: Dictionary defining frequency bands (if feature_method='bandpower').
        *   `csp`: The fitted `mne.decoding.CSP` object (if feature_method='csp').
        *   `csp_components`: Number of CSP components used (if feature_method='csp').
        *   `ch_names`: List of channel names used during training.
        *   `NUM_EEG_CHANNELS`: (Can be derived from `ch_names` or model input).
*   **Calculate Window Parameters:**
    *   `window_duration = tmax - tmin`
    *   `window_samples = int(window_duration * sampling_rate)`
*   **Global Data Structures (`collections.deque`, `threading.Lock`):**
    *   `eeg_data_buffers`: List of deques (one per channel) with `maxlen` slightly larger than `window_samples`.
    *   `latest_horseshoe`: Deque with `maxlen=1` for headband status.
    *   `data_lock`: Thread lock for safe access to buffers.

### 3.2. OSC Server (`python-osc`, `threading`)
*   **Handlers:**
    *   `handle_eeg`: Appends first `NUM_EEG_CHANNELS` float values to `eeg_data_buffers` under lock. Handles potential `ValueError`.
    *   `handle_horseshoe`: Updates `latest_horseshoe` under lock.
    *   `handle_default`: (Optional) Logs unhandled messages.
*   **Server Setup (`start_osc_server`):**
    *   Initialize `dispatcher`.
    *   Map OSC addresses (`/muse/eeg`, `/eeg`, `/muse/elements/horseshoe`, `/hsi`) to handlers.
    *   Create and start `ThreadingOSCUDPServer` in a daemon thread.

### 3.3. Real-time Processing Loop
*   **Initialization:** Start the OSC server.
*   **Main Loop (`while True`):**
    *   `time.sleep(args.update_interval)`
    *   Acquire `data_lock`.
    *   Check if buffers contain at least `window_samples`. If not, print "Buffering..." and `continue`.
    *   Copy the *last* `window_samples` from each `eeg_data_buffer` deque into a NumPy array (`window_data_np` shape: `(n_channels, window_samples)`).
    *   Copy `latest_horseshoe` status.
    *   Release `data_lock`.
    *   **Data Validation:** Check `window_data_np` for NaNs (from potential OSC conversion errors). If NaNs exist, print warning and `continue`.
    *   **Preprocessing:** Apply bandpass filter to `window_data_np` using loaded parameters (`mne.filter.filter_data` or similar).
    *   **Feature Extraction:** (Conditional based on loaded `feature_method`)
        *   Reshape filtered data to `(1, n_channels, window_samples)`.
        *   If `feature_method == 'bandpower'`:
            *   Call `extract_band_power_features` using loaded parameters (`bands`, etc.). Output shape: `(1, n_features)`.
        *   If `feature_method == 'csp'`:
            *   Use the loaded fitted `csp` object: `current_features = loaded_csp.transform(reshaped_filtered_data)`. Output shape: `(1, n_csp_components)`.
    *   **Prediction:**
        *   If features (`current_features`) were extracted successfully:
            *   `prediction_marker = model.predict(current_features)[0]`
            *   Convert marker (1 or 2) to label ("Left" or "Right").
    *   **Display:**
        *   Print the predicted label.
        *   (Optional) Calculate and print prediction confidence/probability if the classifier supports `.predict_proba()`.
        *   Print headband status warning if any sensor value >= 3.
*   **Shutdown:** Use `try...except KeyboardInterrupt...finally` block to gracefully shut down the OSC server on Ctrl+C.

### 3.4. Helper Function
*   **`extract_band_power_features`:** (If needed, identical to the one in the trainer script) Takes `(n_epochs, n_channels, n_times)` data and parameters, returns `(n_epochs, n_features)` array.

## 4. Usage

1.  Ensure Muse Direct is streaming EEG and Headband Status via OSC to the correct IP/Port.
2.  Run the script from the terminal:
    ```bash
    python3 motor_imagery_classifier.py --model-file training_data/your_session_model.joblib 
    ```
    (Optionally add `--update-interval`, `--osc-ip`, `--osc-port` if defaults need changing).
3.  Observe the real-time "Left" / "Right" predictions printed to the console.
4.  Press Ctrl+C to exit.

## 5. Dependencies
*   python-osc
*   numpy
*   mne
*   scikit-learn
*   joblib