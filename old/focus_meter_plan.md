# Project Plan: Focus/Relaxation "Meter" CLI Tool

## 1. Goal

Create a command-line application that streams EEG data, calculates a simple cognitive state metric (focus or relaxation) in real-time, and displays it as a live-updating value or bar in the terminal.

---

## 2. Core Features

- Connect to a BrainFlow-compatible board (initially Synthetic Board).
- Stream EEG data continuously.
- Apply filtering and optional denoising to EEG data.
- Calculate a focus or relaxation metric based on EEG band powers.
- Smooth the metric over time (e.g., moving average).
- Display the metric dynamically in the terminal.
- Allow graceful shutdown via Ctrl+C.
- Optional: Save the metric over time to a CSV file for later analysis.

---

## 3. Metric Calculation

### Focus Metric:

\[
\text{Focus} = \frac{\text{Beta Power}}{\text{Alpha Power} + \text{Theta Power}}
\]

- Higher values indicate increased focus or cognitive workload.

### Relaxation Metric:

\[
\text{Relaxation} = \frac{\text{Alpha Power}}{\text{Beta Power}}
\]

- Higher values indicate increased relaxation or calmness.

*We can implement both and let the user select via CLI argument.*

---

## 4. Technical Design

### CLI Arguments

- `--board-id` (default: Synthetic Board)
- `--metric` (choices: `focus`, `relaxation`, default: `focus`)
- `--update-interval` (default: 0.5s)
- `--window-seconds` (default: 2.0s)
- `--powerline-freq` (50 or 60 Hz, default: 60)
- `--log` (enable debug logging)
- `--smooth-window` (number of recent metric values to average, default: 5)
- *(Optional)* `--output-file` (path to save timestamped metric values)

---

### Processing Pipeline

1. Initialize BoardShim and start streaming.
2. Main Loop:
   - Sleep for `update_interval`.
   - Get latest EEG data window.
   - For each EEG channel:
     - Apply detrending, bandpass, notch filtering.
     - *(Optional)* Apply wavelet denoising.
     - Calculate PSD.
     - Calculate band powers: Delta, Theta, Alpha, Beta, Gamma.
   - Average band powers across channels.
   - Calculate focus or relaxation metric.
   - Append metric to a rolling buffer of length `smooth_window`.
   - Calculate smoothed metric (mean of buffer).
   - Display the smoothed metric as:
     - A numeric value.
     - A simple ASCII bar (e.g., `|||||||||`).
     - *(Optional)* Color-coded output.
   - *(Optional)* Save timestamped metric to CSV.
3. Graceful shutdown on Ctrl+C.

---

### Display Options

- Numeric: `Focus: 1.23`
- Bar: `Focus: [|||||||||     ]`
- Color: Green for relaxed, red for stressed (optional, using ANSI codes or `rich` library).

---

## 5. Development Steps

1. Fork or reuse the existing EEG visualizer codebase.
2. Add CLI argument for metric choice and smoothing window.
3. Implement metric calculation formulas.
4. Implement smoothing with a rolling buffer.
5. Implement terminal display of the smoothed metric.
6. Add optional CSV logging.
7. Test with Synthetic Board.
8. Prepare for Muse S integration when hardware is available.

---

## 6. Workflow Diagram

```mermaid
graph TD
    A[Start CLI Tool] --> B(Parse CLI Args)
    B --> C[Initialize BoardShim]
    C --> D[Prepare Session & Start Stream]
    D --> E{Main Loop}
    E --> F[Sleep (update_interval)]
    F --> G[Get EEG Data Window]
    G --> H[Filter & Denoise EEG]
    H --> I[Calculate PSD & Band Powers]
    I --> J[Average Across Channels]
    J --> K[Calculate Focus/Relaxation Metric]
    K --> L[Update Rolling Buffer]
    L --> M[Calculate Smoothed Metric]
    M --> N[Display Metric in Terminal]
    N --> O{Save to CSV?}
    O -- Yes --> P[Append Metric to File]
    O -- No --> E
    E -- Ctrl+C --> Q[Stop Stream & Release Session]
    Q --> R[Exit]
```

---

## 7. Future Enhancements

- Add thresholds and alerts (e.g., beep or color change when focus drops).
- Provide historical plots after session ends.
- Integrate with a web dashboard.
- Add biofeedback (e.g., sound modulation based on metric).