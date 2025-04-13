# Configuration Constants for BrainTrade Monitor

# Sampling Rates (Hz)
EEG_SAMPLING_RATE = 256
PPG_SAMPLING_RATE = 64
# ACC_SAMPLING_RATE = 50 # Placeholder if needed later

# Window Durations (seconds)
EEG_WINDOW_DURATION = 3
PPG_WINDOW_DURATION = 10
# ACC_WINDOW_DURATION = 3 # Placeholder if needed later

# Processing Intervals
UPDATE_INTERVAL = 0.5    # How often to calculate features (seconds)
BASELINE_DURATION = 60   # Duration of baseline calculation (seconds)

# EEG Analysis Parameters
EEG_NFFT = 256           # FFT length for PSD calculation
EEG_FILTER_LOWCUT = 1.0  # EEG filter lowcut frequency (Hz)
EEG_FILTER_HIGHCUT = 40.0 # EEG filter highcut frequency (Hz)
ALPHA_BAND = (8, 13)     # Alpha band frequency range (Hz)
BETA_BAND = (13, 30)     # Beta band frequency range (Hz)

# PPG Analysis Parameters
PPG_FILTER_LOWCUT = 0.5  # PPG filter lowcut frequency (Hz)
PPG_FILTER_HIGHCUT = 4.0 # PPG filter highcut frequency (Hz)
PPG_PEAK_MIN_DIST_FACTOR = 0.3 # Factor for min distance between peaks (relative to sampling rate)
PPG_PEAK_HEIGHT_FACTOR = 0.5 # Factor for min peak height (relative to std dev)

# State Logic Parameters
STATE_PERSISTENCE_UPDATES = 6 # Number of consecutive updates for state change
STALE_DATA_THRESHOLD = 5.0 # Max age for data to be considered fresh (seconds)
RATIO_THRESHOLD = 1.5      # SD multiplier for ratio threshold
HR_THRESHOLD = 1.5         # SD multiplier for HR threshold

# General
NUM_EEG_CHANNELS = 4
EPSILON = 1e-10            # Small number to avoid division by zero