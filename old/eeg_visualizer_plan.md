# Project Plan: Real-time EEG Band Power Visualizer (CLI)

**Version:** Includes Filtering and Wavelet Denoising

**1. Goal:**
Create a command-line application that connects to a BrainFlow board (initially the Synthetic Board, adaptable for Muse S), streams EEG data, applies filtering and denoising, calculates the relative power of standard EEG frequency bands (Delta, Theta, Alpha, Beta, Gamma) in near real-time, and displays these values dynamically in the terminal.

**2. Core Functionality:**
*   Establish connection to the specified BrainFlow board.
*   Continuously stream data from the board.
*   Periodically process chunks of the most recent EEG data.
*   Apply filtering (detrend, bandpass, notch) and wavelet denoising to the EEG data.
*   Calculate the power spectral density and derive the average relative power for standard EEG bands across all available EEG channels.
*   Display the calculated relative band powers in the terminal, updating at regular intervals.
*   Allow graceful shutdown via Ctrl+C.

**3. Technical Design:**
*   **Project Structure:**
    *   Main script: `eeg_visualizer.py`
    *   Requirements file: `requirements.txt`
*   **Key Libraries:**
    *   `brainflow`: For board communication and data processing.
    *   `numpy`: For numerical operations on the data array.
    *   `time`: For controlling update intervals.
    *   `argparse`: For handling command-line arguments.
    *   *(Optional)* `rich`: For creating a more sophisticated, live-updating terminal UI (e.g., using tables).
*   **Data Flow & Processing:**
    1.  Parse CLI arguments.
    2.  Initialize `BoardShim` with the target `board_id`.
    3.  `prepare_session()`. Handle potential connection errors.
    4.  Retrieve board metadata: `sampling_rate`, `eeg_channels`.
    5.  `start_stream()`.
    6.  Enter main loop:
        *   Sleep for `update_interval` seconds.
        *   Get the latest data chunk using `board.get_current_board_data(num_samples)`, where `num_samples` corresponds to `window_seconds * sampling_rate`.
        *   Ensure enough data points are available in the retrieved chunk.
        *   For each EEG channel (`channel_data = data[channel_index]`):
            *   **Apply Preprocessing (in-place):**
                *   `DataFilter.detrend(channel_data, DetrendOperations.CONSTANT)` (Removes DC offset)
                *   `DataFilter.perform_highpass(channel_data, sampling_rate, 1.0, 4, FilterTypes.BUTTERWORTH, 0)` (1Hz Highpass)
                *   `DataFilter.perform_lowpass(channel_data, sampling_rate, 50.0, 4, FilterTypes.BUTTERWORTH, 0)` (50Hz Lowpass)
                *   `DataFilter.remove_environmental_noise(channel_data, sampling_rate, noise_type)` (where `noise_type` is `NoiseTypes.SIXTY` or `FIFTY` based on `--powerline-freq` argument)
                *   `DataFilter.perform_wavelet_denoising(channel_data, WaveletTypes.BIOR3_9, 3, WaveletDenoisingTypes.SURESHRINK, ThresholdTypes.HARD, WaveletExtensionTypes.SYMMETRIC, NoiseEstimationLevelTypes.FIRST_LEVEL)`
            *   Calculate Power Spectral Density (PSD) using `DataFilter.get_psd_welch`.
            *   Calculate absolute band power for Delta (1-4Hz), Theta (4-8Hz), Alpha (8-13Hz), Beta (13-30Hz), Gamma (30-50Hz) using `DataFilter.get_band_power`.
        *   Average the absolute band powers across all EEG channels.
        *   Calculate the total power across these bands.
        *   Calculate the relative power for each band (absolute band power / total power).
        *   Update the terminal display with the relative band powers (e.g., formatted percentages).
    7.  Catch `KeyboardInterrupt` (Ctrl+C) to break the loop.
    8.  Use a `finally` block to ensure `stop_stream()` and `release_session()` are called.
*   **Display:** Start with simple `print` statements clearing the console each update. If `rich` is used, employ `rich.live.Live` with a `rich.table.Table`.
*   **Error Handling:** Include `try...except` for `KeyboardInterrupt` and potential `BrainFlowError` during connection or data processing. Ensure session release in a `finally` block.

**4. CLI Arguments (`argparse`):**
*   `--board-id` (int): Target board ID (Default: -1 for `SYNTHETIC_BOARD`).
*   `--update-interval` (float): Frequency (in seconds) for processing data and updating the display (Default: 0.5).
*   `--window-seconds` (float): Duration (in seconds) of the data window used for each PSD/band power calculation (Default: 2.0).
*   `--log` (flag): Enable BrainFlow's verbose logging (Default: False).
*   `--powerline-freq` (int, choices=[50, 60], default=60): Powerline frequency (Hz) for notch filter.
*   *(Optional connection params like `--mac-address`, `--serial-number` if needed for non-synthetic boards)*.

**5. Development Steps:**
    1.  Initialize project: Create `eeg_visualizer.py` and `requirements.txt`.
    2.  Add dependencies to `requirements.txt`: `brainflow`, `numpy`.
    3.  Implement basic argument parsing (`argparse`), including `--powerline-freq`.
    4.  Implement board connection and session management logic using `SYNTHETIC_BOARD`.
    5.  Implement the main data acquisition loop (`get_current_board_data`).
    6.  Integrate filtering steps (detrend, bandpass, notch) and wavelet denoising before PSD calculation.
    7.  Integrate PSD and band power calculations using `DataFilter`.
    8.  Implement averaging across channels and relative power calculation.
    9.  Add basic terminal printing of results.
    10. Implement graceful shutdown and error handling.
    11. *(Optional)* Enhance terminal display using the `rich` library.
    12. Add comments and refine code.
    13. Prepare for testing with `MUSE_S_BOARD` ID (when hardware is available).

**6. Future Considerations:**
*   The core logic (data acquisition, processing) can be refactored into functions/classes reusable in a future web application backend (e.g., Flask/FastAPI with WebSockets).

**7. Workflow Diagram:**

```mermaid
graph TD
    A[Start eeg_visualizer.py] --> B(Parse CLI Arguments);
    B --> C{Enable Logging?};
    C -- Yes --> D[BoardShim.enable_dev_board_logger];
    C -- No --> E;
    D --> E[Initialize BoardShim];
    E --> F[try];
    F --> G[Prepare Session];
    G -- Success --> H[Get Sampling Rate & EEG Channels];
    G -- Failure --> Z(Handle Connection Error);
    H --> I[Start Stream];
    I --> J{Main Loop};
    J -- Wait --> K[Sleep (update_interval)];
    K --> L[Get Current Board Data (window_seconds)];
    L --> M{Data Sufficient?};
    M -- Yes --> N[Apply Filters to EEG Data];
    N --> N2[Apply Wavelet Denoising];
    N2 --> O[Calculate PSD & Band Powers];
    O --> P[Calculate Avg Relative Powers];
    P --> Q[Update Terminal Display];
    Q --> J;
    M -- No --> J;
    J -- Ctrl+C --> R[except KeyboardInterrupt];
    R --> S[finally];
    S --> T[Stop Stream];
    T --> U[Release Session];
    U --> Y[End];
    Z --> Y;