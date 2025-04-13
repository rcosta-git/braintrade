# Real-time Blink Detection - Detailed Implementation Plan

---

## 1. Goal

Create a CLI tool that detects eye blinks in real-time from BrainFlow EEG data and reports single or double blinks, potentially triggering simple actions.

---

## 2. Core Features

- EEG streaming (prioritizing frontal channels).
- Real-time signal processing to identify blink artifacts.
- Detection and reporting of single blinks.
- Detection and reporting of double blinks (two blinks within a defined time window).
- CLI output of detected events.
- *(Optional)* Triggering a simple action (e.g., print message, simulate key press).

---

## 3. Technical Design

### Architecture

- Single Thread: For simplicity in this initial version, processing can likely happen in the main thread if kept efficient.

---

### Blink Detection Method (Thresholding)

1.  **Channel Selection:** Use frontal EEG channels (e.g., from `BoardShim.get_eeg_channels()`, potentially selecting specific indices if known for Muse S).
2.  **Filtering:** Apply a bandpass filter (e.g., 1-15 Hz) to the selected EEG channel(s).
3.  **Thresholding:**
    - Monitor the filtered signal amplitude in real-time.
    - Define a positive amplitude threshold (needs tuning, e.g., 50-100 uV).
    - When the signal crosses above the threshold, register a potential blink start.
    - Implement a debounce mechanism (ignore further crossings for ~200ms).
    - A confirmed "blink event" occurs after the debounce period.

---

### Double Blink Detection

- Maintain a timestamp queue (`collections.deque`) of recent blink events.
- When a new blink is confirmed:
  - Add its timestamp.
  - Check if time difference to previous blink is within a window (e.g., 0.2 - 1.0 seconds).
  - If yes, register a "double blink event".

---

### CLI Arguments

- `--board-id` (int, default: -1)
- `--eeg-channel-index` (int, default: 0) - Index of the primary EEG channel.
- `--threshold` (float, default: 75.0) - Amplitude threshold (uV). **Needs tuning.**
- `--debounce-ms` (int, default: 200) - Debounce time (ms).
- `--double-blink-min-ms` (int, default: 200) - Min time for double blink (ms).
- `--double-blink-max-ms` (int, default: 1000) - Max time for double blink (ms).
- `--update-interval-ms` (int, default: 50) - Processing interval (ms).
- `--log` (flag) - Enable debug logging.

---

### Processing Loop

1.  Initialize BoardShim, start streaming.
2.  Get `sampling_rate`. Calculate buffer size.
3.  Initialize state: `last_blink_time = 0`, `blink_timestamps = deque(maxlen=5)`.
4.  Loop:
    - `time.sleep(args.update_interval_ms / 1000.0)`
    - Get latest data chunk.
    - If enough new data:
      - Select target EEG channel data.
      - Apply bandpass filter.
      - Iterate through new samples:
        - Check threshold crossing & debounce condition.
        - If true (Single Blink Detected):
          - Record `current_time`.
          - Print "Blink!".
          - Update `last_blink_time`.
          - Check for Double Blink using `blink_timestamps` and time difference.
          - If Double Blink: Print "Double Blink!". *(Optional)* Trigger action.
          - Add `current_time` to `blink_timestamps`.
5.  Handle `KeyboardInterrupt`.

---

### CLI Display

- Simple text output:
  ```
  Streaming... Monitoring channel X for blinks.
  Blink! (Timestamp: 12345.67)
  Blink! (Timestamp: 12346.01)
  Double Blink!
  Blink! (Timestamp: 12347.89)
  ```

---

## 4. Development Steps

1.  **Setup:** Create `blink_detector.py`, add dependencies.
2.  **Arguments:** Implement `argparse`.
3.  **BrainFlow Init:** Connect, stream, get info.
4.  **Filtering:** Implement bandpass filter.
5.  **Thresholding Logic:** Implement detection loop with debounce.
6.  **Double Blink Logic:** Implement timestamp queue and check.
7.  **Output:** Add `print` statements.
8.  **Main Loop:** Structure data fetching/processing.
9.  **Shutdown:** Implement graceful exit.
10. **Testing & Tuning:** **Tune `--threshold` value** by observing signal. Adjust timings.
11. *(Optional)* Add action triggering.

---

## 5. Workflow Diagram

```mermaid
graph TD
    A[Start Script] --> B(Parse CLI Args)
    B --> C[Initialize BrainFlow & Start Stream]
    C --> D{Main Loop}
    D --> E[Sleep (update_interval)]
    E --> F[Get Latest EEG Data]
    F --> G[Filter EEG Channel]
    G --> H{Iterate Samples}
    H -- Sample --> I{Above Threshold & Debounced?}
    I -- Yes --> J[Register Blink Event]
    J --> K[Check for Double Blink]
    K -- Yes --> L[Register Double Blink Event]
    L --> M[Update Timestamps & Output]
    K -- No --> M
    I -- No --> H
    H -- End of Chunk --> D
    D -- Ctrl+C --> N[Stop Stream & Exit]
```

---

## 6. Future Enhancements

- More robust detection algorithms.
- Trigger complex actions (OSC, API calls).
- Automatic threshold calibration.
- GUI for visualization/configuration.