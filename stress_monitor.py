import argparse
import os
import time
import numpy as np
import threading
import collections
from pythonosc import dispatcher, osc_server
import mne
import scipy
from mne.time_frequency import psd_array_welch
from scipy.signal import butter, filtfilt, find_peaks
from scipy.integrate import trapezoid # Import trapezoid for integration
import logging 

# --- Logging Setup ---
# Configure logging to write to a file
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file_path = os.path.join(log_dir, 'stress_monitor.log')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s') # Added threadName

# Add a handler to also print logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# Avoid adding handler if it already exists (e.g., during re-runs in interactive sessions)
if not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger().handlers):
    logging.getLogger().addHandler(console_handler)


# --- Configuration Constants ---
EEG_SAMPLING_RATE = 256  
PPG_SAMPLING_RATE = 64   
EEG_WINDOW_DURATION = 3  
PPG_WINDOW_DURATION = 10 
UPDATE_INTERVAL = 0.5    
BASELINE_DURATION = 60   
EEG_NFFT = 256           
PPG_FILTER_LOWCUT = 0.5  
PPG_FILTER_HIGHCUT = 4.0 
EEG_FILTER_LOWCUT = 1.0  
EEG_FILTER_HIGHCUT = 40.0 
ALPHA_BAND = (8, 13)     
BETA_BAND = (13, 30)     
PPG_PEAK_MIN_DIST_FACTOR = 0.3 
PPG_PEAK_HEIGHT_FACTOR = 0.5 
STATE_PERSISTENCE_UPDATES = 6 
STALE_DATA_THRESHOLD = 5.0 
RATIO_THRESHOLD = 1.5
HR_THRESHOLD = 1.5
EPSILON = 1e-10 # Small number to avoid division by zero

# --- Global Data Storage (Thread-Safe) ---
NUM_EEG_CHANNELS = 4
# Buffer sizes will be calculated based on args in main()
eeg_data_buffers = None
ppg_data_buffer = None 
baseline_metrics = {} # Store baseline median and std dev
data_lock = threading.Lock()
# These globals will be managed by the main loop and passed to update_stress_state
last_eeg_timestamp = 0
last_ppg_timestamp = 0

# --- Feature Extraction Functions ---

def estimate_bpm_from_ppg(ppg_signal, sampling_rate, args):
    """Estimates BPM from PPG signal using SciPy."""
    if len(ppg_signal) < sampling_rate * 2: # Need at least a few seconds of data
        logging.warning("Not enough PPG data to estimate BPM.")
        return np.nan

    # 1. Bandpass filter
    nyquist_rate = sampling_rate / 2.0
    low = args.ppg_filter_low / nyquist_rate
    high = args.ppg_filter_high / nyquist_rate
    try:
        # Ensure high > low after dividing by nyquist_rate
        if high <= low:
             logging.error(f"PPG filter high cut ({args.ppg_filter_high} Hz) must be greater than low cut ({args.ppg_filter_low} Hz).")
             return np.nan
        b, a = butter(3, [low, high], btype='band')
        ppg_filtered = filtfilt(b, a, ppg_signal)
    except ValueError as e:
        logging.error(f"Error filtering PPG signal in estimate_bpm_from_ppg: {e}")
        return np.nan

    # 2. Peak detection
    min_distance = int(sampling_rate * args.ppg_peak_min_dist_factor)
    # Ensure std dev is not zero before calculating height
    ppg_std = np.std(ppg_filtered)
    if ppg_std < EPSILON: # Check against epsilon
        logging.warning("PPG signal standard deviation is near zero, cannot reliably detect peaks.")
        return np.nan 
    min_height = ppg_std * args.ppg_peak_height_factor
    
    try:
        peaks, _ = find_peaks(ppg_filtered, height=min_height, distance=min_distance)
    except ValueError as e:
        logging.error(f"Error finding PPG peaks in estimate_bpm_from_ppg: {e}")
        return np.nan

    if len(peaks) < 2:
        logging.warning("Not enough peaks found in PPG signal to estimate BPM.")
        return np.nan

    # 3. Calculate Inter-Beat Intervals (IBIs) in seconds
    peak_times = peaks / sampling_rate
    ibis = np.diff(peak_times)

    # Filter unrealistic IBIs (IBIs)
    valid_ibis = ibis[(ibis > 0.3) & (ibis < 2.0)] # Keep this hardcoded for now, relates to physiological limits

    # 4. Convert IBIs to BPM
    if len(valid_ibis) == 0:
        logging.warning("No valid IBIs found after filtering.")
        return np.nan
    mean_ibi = np.mean(valid_ibis)
    if mean_ibi < EPSILON:
        logging.warning("Mean IBI is near zero, cannot calculate BPM.")
        return np.nan
    bpm = 60.0 / mean_ibi
    return bpm

def extract_alpha_beta_ratio(eeg_data, sampling_rate, args):
    """Calculates Alpha/Beta ratio from EEG data."""
    bands = {'Alpha': args.alpha_band, 'Beta': args.beta_band}
    n_channels, n_times = eeg_data.shape
    
    if n_times < args.nfft: # Check if signal is long enough for FFT
        logging.warning(f"EEG segment too short ({n_times} samples) for FFT (needs {args.nfft}), skipping ratio calculation.")
        return np.nan

    # Filter EEG data first
    try:
        iir_params = dict(order=4, ftype='butter')
        # MNE's filter_data handles padding and potential issues internally
        eeg_filtered = mne.filter.filter_data(eeg_data, sfreq=sampling_rate,
                                              l_freq=args.eeg_filter_low, h_freq=args.eeg_filter_high,
                                              method='iir', iir_params=iir_params, verbose=False,
                                              pad='reflect_limited', # Common padding method
                                              ) 
    except ValueError as e:
        # This might catch cases where filtering is impossible (e.g., all NaN data)
        logging.error(f"Error filtering EEG data in extract_alpha_beta_ratio: {e}")
        return np.nan

    band_powers = {}
    for band_name, (fmin, fmax) in bands.items():
        band_powers[band_name] = np.zeros(n_channels)

    for j in range(n_channels):
        channel_data = eeg_filtered[j, :]
        n_times_ch = len(channel_data)
        # Ensure n_fft is not greater than the channel data length after potential filtering artifacts
        n_fft = min(n_times_ch, args.nfft) 
        if n_fft == 0:
            logging.warning(f"Warning: Empty EEG segment for channel {j}, skipping.")
            continue # Skip this channel if empty

        try:
            # Ensure n_per_seg is not greater than channel data length
            n_per_seg = min(n_fft, n_times_ch) 
            psd, freqs = psd_array_welch(channel_data, sfreq=sampling_rate, 
                                         fmin=args.eeg_filter_low, # Calculate PSD over full filtered range
                                         fmax=args.eeg_filter_high, 
                                         n_fft=n_fft, n_per_seg=n_per_seg, verbose=False,
                                         average='mean', # Explicitly average Welch segments
                                         )
            # Calculate power per band using trapezoidal integration
            for band_name, (fmin, fmax) in bands.items():
                 freq_res = freqs[1] - freqs[0] # Frequency resolution
                 idx_band = np.logical_and(freqs >= fmin, freqs <= fmax)
                 if np.sum(idx_band) > 0:
                     # Integrate PSD over the band frequencies
                     band_powers[band_name][j] = trapezoid(psd[idx_band], dx=freq_res)
                 else:
                     band_powers[band_name][j] = 0 
                     logging.warning(f"No PSD components found for band {band_name} in channel {j}.")

        except ValueError as e:
            logging.error(f"Error calculating PSD for channel {j} in extract_alpha_beta_ratio: {e}")
            # Assign NaN or zero if PSD fails for a channel
            for band_name in bands:
                band_powers[band_name][j] = np.nan # Or zero?


    # Average power across channels, handle potential NaNs
    alpha_power = np.nanmean(band_powers['Alpha'])
    beta_power = np.nanmean(band_powers['Beta'])

    # Improved check for near-zero beta power
    if np.isnan(alpha_power) or np.isnan(beta_power) or beta_power < EPSILON:
        logging.warning(f"Warning: Invalid alpha ({alpha_power}) or beta ({beta_power}) power, returning NaN")
        return np.nan
        
    alpha_beta_ratio = alpha_power / beta_power 
    return alpha_beta_ratio

# --- OSC Handlers ---

def handle_eeg(address, *args):
    global last_eeg_timestamp, eeg_data_buffers # Declare as global to modify
    ts = time.time()
    if len(args) >= NUM_EEG_CHANNELS:
        with data_lock:
            try:
                # logging.debug(f"Received EEG data - Address: {address}, Arguments: {args}") 
                for i in range(NUM_EEG_CHANNELS):
                    # Store timestamp along with value
                    eeg_data_buffers[i].append((ts, float(args[i]))) 
                last_eeg_timestamp = ts # Update last received timestamp
            except (ValueError, TypeError, IndexError) as e:
                logging.error(f"Error processing EEG data: {e}") 
            except Exception as e: # Catch potential issues if buffers not initialized
                 logging.error(f"Unexpected error in handle_eeg: {e}")

def handle_ppg(address, *args):
    global last_ppg_timestamp, ppg_data_buffer # Declare as global to modify
    ts = time.time()
    if len(args) >= 3: # Expecting (sensor_id, value, sensor_id)
        with data_lock:
            try:
                # logging.debug(f"Received PPG data - Address: {address}, Arguments: {args}")
                ppg_value = float(args[1]) # Extract the middle PPG value
                # Store timestamp along with value
                ppg_data_buffer.append((ts, ppg_value)) 
                last_ppg_timestamp = ts # Update last received timestamp
            except (ValueError, TypeError, IndexError) as e:
                logging.error(f"Error processing PPG data: {e}") 
            except Exception as e: # Catch potential issues if buffers not initialized
                 logging.error(f"Unexpected error in handle_ppg: {e}")


def handle_default(address, *args):
    # logging.debug(f"Received OSC message - Address: {address}, Arguments: {args}") 
    pass

# --- OSC Server Setup ---
def server_thread_target(server):
    """Target function for the OSC server thread with error logging."""
    try:
        server.serve_forever()
    except Exception as e:
        logging.exception(f"OSC Server thread encountered an error: {e}")
    finally:
        logging.info("OSC Server thread exiting.")

def start_osc_server(ip, port):
    disp = dispatcher.Dispatcher()
    disp.map("/eeg", handle_eeg)
    disp.map("/ppg", handle_ppg)
    # Add mappings for other addresses if needed later (e.g., /acc)
    disp.set_default_handler(handle_default)
    
    try:
        server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
        logging.info(f"OSC Server listening on {server.server_address}")
        # Pass the server instance to the target function
        thread = threading.Thread(target=server_thread_target, args=(server,), daemon=True, name="OSCServerThread")
        thread.start()
        return server, thread
    except OSError as e:
        logging.error(f"Failed to start OSC server on {ip}:{port} - {e}")
        return None, None
    except Exception as e:
        logging.exception(f"An unexpected error occurred during OSC server setup: {e}")
        return None, None


# --- Baseline Calculation (Revised) ---

def calculate_baseline(duration, args): # Pass args
    print("Entering calculate_baseline function") # Debug print
    global baseline_metrics, eeg_data_buffers, ppg_data_buffer # Need to modify globals
    logging.info(f"Calculating baseline for {duration} seconds... Please relax.")
    start_time = time.time()
    
    # Initialize buffers here based on args
    eeg_buffer_size = int(args.eeg_sampling_rate * (duration + 15)) 
    ppg_buffer_size = int(args.ppg_sampling_rate * (duration + 15)) 
    eeg_data_buffers = [collections.deque(maxlen=eeg_buffer_size) for _ in range(NUM_EEG_CHANNELS)]
    ppg_data_buffer = collections.deque(maxlen=ppg_buffer_size)
    
    # 1. Collect data for the specified duration
    logging.info("Waiting for initial data buffer fill...")
    min_eeg_samples = int(args.eeg_sampling_rate * args.eeg_window_duration) 
    min_ppg_samples = int(args.ppg_sampling_rate * args.ppg_window_duration)
    
    # Wait until enough data is likely buffered for at least one window calculation later
    while True:
        with data_lock:
            eeg_len = len(eeg_data_buffers[0]) if eeg_data_buffers else 0
            ppg_len = len(ppg_data_buffer) if ppg_data_buffer else 0
        if eeg_len >= min_eeg_samples and ppg_len >= min_ppg_samples:
            logging.info("Initial buffer filled sufficiently.")
            break
        if time.time() - start_time > duration + 15: # Increased timeout slightly
             logging.error("Error: Timed out waiting for sufficient initial data.")
             return False
        logging.info(f"Buffering initial data... EEG: {eeg_len}/{min_eeg_samples}, PPG: {ppg_len}/{min_ppg_samples}")
        time.sleep(1)

    logging.info(f"Collecting baseline data for {duration} seconds...")
    baseline_start_time = time.time()
    while time.time() - baseline_start_time < duration:
        # Just sleep, data is collected by the OSC thread
        logging.info(f"Baseline collection progress: {time.time() - baseline_start_time:.1f} / {duration}s")
        time.sleep(args.update_interval) # Re-enable sleep

    logging.info("Baseline data collection finished.")

    # 2. Retrieve collected data
    with data_lock:
        logging.info(f"Retrieving baseline data. EEG buffer size: {len(eeg_data_buffers[0])}, PPG buffer size: {len(ppg_data_buffer)}")
        # Get all data collected during the baseline period (or max buffer size)
        # Extract only the values, discard timestamps for baseline calculation
        eeg_baseline_data = np.array([ [item[1] for item in buf] for buf in eeg_data_buffers])
        ppg_baseline_data = np.array([item[1] for item in ppg_data_buffer])

    # 3. Process the collected data
    logging.info("Processing collected baseline data...")
    if eeg_baseline_data.shape[1] < min_eeg_samples or len(ppg_baseline_data) < min_ppg_samples:
        logging.error(f"Error: Insufficient data collected for baseline processing. EEG shape: {eeg_baseline_data.shape}, PPG length: {len(ppg_baseline_data)}")
        return False

    # Calculate features on sliding windows across the baseline data
    ratios = []
    hrs = []
    eeg_window_samples = int(args.eeg_sampling_rate * args.eeg_window_duration)
    ppg_window_samples = int(args.ppg_sampling_rate * args.ppg_window_duration)
    # Use a step size related to the update interval for consistency
    step_samples_eeg = int(args.eeg_sampling_rate * args.update_interval) 
    step_samples_ppg = int(args.ppg_sampling_rate * args.update_interval) 

    logging.info("Calculating baseline stats using sliding windows...")
    for i in range(0, eeg_baseline_data.shape[1] - eeg_window_samples + 1, step_samples_eeg):
        eeg_window = eeg_baseline_data[:, i:i+eeg_window_samples]
        ratio = extract_alpha_beta_ratio(eeg_window, args.eeg_sampling_rate, args) # Pass args
        if not np.isnan(ratio):
            ratios.append(ratio)
            
    for i in range(0, len(ppg_baseline_data) - ppg_window_samples + 1, step_samples_ppg): 
        ppg_window = ppg_baseline_data[i:i+ppg_window_samples]
        hr = estimate_bpm_from_ppg(ppg_window, args.ppg_sampling_rate, args) # Pass args
        if not np.isnan(hr):
            hrs.append(hr)

    if not ratios or not hrs:
        logging.error(f"Error: No valid feature samples calculated during baseline processing. Ratios calculated: {len(ratios)}, HRs calculated: {len(hrs)}")
        return False

    baseline_metrics['ratio_median'] = np.median(ratios)
    baseline_metrics['ratio_std'] = np.std(ratios)
    baseline_metrics['hr_median'] = np.median(hrs)
    baseline_metrics['hr_std'] = np.std(hrs)

    logging.info("-" * 30)
    logging.info("Baseline Calculation Complete:")
    logging.info(f"  Baseline A/B Ratio: {baseline_metrics['ratio_median']:.2f} +/- {baseline_metrics['ratio_std']:.2f} ({len(ratios)} samples)")
    logging.info(f"  Baseline HR: {baseline_metrics['hr_median']:.1f} +/- {baseline_metrics['hr_std']:.1f} BPM ({len(hrs)} samples)")
    logging.info("-" * 30)
    return True

# --- State Logic Function ---
def update_stress_state(current_ratio, current_hr, baseline_metrics, current_state, tentative_state_history, args):
    """
    Determines the stress state based on current features and baseline.
    Applies persistence logic to smooth state transitions.

    Returns:
        str: The potentially updated current_state.
    """
    new_state = current_state # Default to current state

    if np.isnan(current_ratio) or np.isnan(current_hr):
        logging.warning("Skipping state update due to NaN feature value.")
        tentative_state = "Uncertain (NaN)" 
    elif 'ratio_median' not in baseline_metrics or 'hr_median' not in baseline_metrics:
        logging.warning("Baseline metrics not available, skipping state update.")
        tentative_state = "Initializing" # Should not happen after baseline calc normally
    else:
        # Determine tentative state based on thresholds
        is_ratio_low = current_ratio < (baseline_metrics['ratio_median'] - args.ratio_threshold * baseline_metrics['ratio_std'])
        is_hr_high = current_hr > (baseline_metrics['hr_median'] + args.hr_threshold * baseline_metrics['hr_std'])

        if is_ratio_low and is_hr_high:
            tentative_state = "Stress"
        elif is_ratio_low or is_hr_high:
            tentative_state = "Warning"
        else:
            tentative_state = "Calm"

    # Apply Persistence
    tentative_state_history.append(tentative_state)
    if len(tentative_state_history) == args.persistence: # Use arg
        first_state = tentative_state_history[0]
        # Only update if all states in history are the same AND it's a change
        if all(s == first_state for s in tentative_state_history) and new_state != first_state: 
            logging.info(f"STATE CHANGE: {new_state} -> {first_state}")
            new_state = first_state # Update official state
        # Handle case where state becomes uncertain consistently
        elif all(s == "Uncertain (NaN)" for s in tentative_state_history) and new_state != "Uncertain (NaN)":
             logging.info(f"STATE CHANGE: {new_state} -> Uncertain (NaN)")
             new_state = "Uncertain (NaN)"
        elif all(s == "Uncertain (Stale Data)" for s in tentative_state_history) and new_state != "Uncertain (Stale Data)":
             # This state is set outside this function, but handle persistence if needed
             logging.info(f"STATE CHANGE: {new_state} -> Uncertain (Stale Data)")
             new_state = "Uncertain (Stale Data)"

    return new_state


# --- Main Application Logic ---

def main():
    print("Entering main function")  # Debug print
    logging.info("Entering main function") # Debug log
    global eeg_data_buffers, ppg_data_buffer # Declare globals needed before baseline

    parser = argparse.ArgumentParser(description='Real-time Stress Monitor (OSC)')
    # OSC Args
    parser.add_argument('--osc-ip', type=str, default="0.0.0.0", help='OSC server IP address')
    parser.add_argument('--osc-port', type=int, default=5001, help='OSC server port')
    # Timing Args
    parser.add_argument('--baseline-duration', type=int, default=BASELINE_DURATION, help='Duration of baseline calculation (seconds)')
    parser.add_argument('--update-interval', type=float, default=UPDATE_INTERVAL, help='How often to calculate features and update state (seconds)')
    parser.add_argument('--stale-threshold', type=float, default=STALE_DATA_THRESHOLD, dest='stale_threshold', help='Max age for data to be considered fresh (seconds)')
    # EEG Args
    parser.add_argument('--eeg-sr', type=int, default=EEG_SAMPLING_RATE, dest='eeg_sampling_rate', help='EEG sampling rate (Hz)')
    parser.add_argument('--eeg-window', type=float, default=EEG_WINDOW_DURATION, dest='eeg_window_duration', help='EEG window duration for analysis (seconds)')
    parser.add_argument('--nfft', type=int, default=EEG_NFFT, help='FFT length for PSD calculation')
    parser.add_argument('--eeg-lowcut', type=float, default=EEG_FILTER_LOWCUT, dest='eeg_filter_low', help='EEG filter lowcut frequency (Hz)')
    parser.add_argument('--eeg-highcut', type=float, default=EEG_FILTER_HIGHCUT, dest='eeg_filter_high', help='EEG filter highcut frequency (Hz)')
    parser.add_argument('--alpha-band', type=float, nargs=2, default=ALPHA_BAND, help='Alpha band frequency range (Hz)')
    parser.add_argument('--beta-band', type=float, nargs=2, default=BETA_BAND, help='Beta band frequency range (Hz)')
    # PPG Args
    parser.add_argument('--ppg-sr', type=int, default=PPG_SAMPLING_RATE, dest='ppg_sampling_rate', help='PPG sampling rate (Hz)')
    parser.add_argument('--ppg-window', type=float, default=PPG_WINDOW_DURATION, dest='ppg_window_duration', help='PPG window duration for analysis (seconds)')
    parser.add_argument('--ppg-lowcut', type=float, default=PPG_FILTER_LOWCUT, dest='ppg_filter_low', help='PPG filter lowcut frequency (Hz)')
    parser.add_argument('--ppg-highcut', type=float, default=PPG_FILTER_HIGHCUT, dest='ppg_filter_high', help='PPG filter highcut frequency (Hz)')
    parser.add_argument('--ppg-peak-dist', type=float, default=PPG_PEAK_MIN_DIST_FACTOR, dest='ppg_peak_min_dist_factor', help='PPG peak minimum distance factor')
    parser.add_argument('--ppg-peak-height', type=float, default=PPG_PEAK_HEIGHT_FACTOR, dest='ppg_peak_height_factor', help='PPG peak minimum height factor (relative to std dev)')
    # State Logic Args
    parser.add_argument('--persistence', type=int, default=STATE_PERSISTENCE_UPDATES, help='Number of consecutive updates for state change')
    parser.add_argument('--ratio-threshold', type=float, default=RATIO_THRESHOLD, dest='ratio_threshold', help='SD multiplier for ratio threshold')
    parser.add_argument('--hr-threshold', type=float, default=HR_THRESHOLD, dest='hr_threshold', help='SD multiplier for HR threshold')
    
    args = parser.parse_args()

    # --- Initialize Buffers based on args ---
    # Calculate buffer sizes based on baseline duration and sampling rates from args
    eeg_buffer_size = int(args.eeg_sampling_rate * (args.baseline_duration + 15)) 
    ppg_buffer_size = int(args.ppg_sampling_rate * (args.baseline_duration + 15)) 
    eeg_data_buffers = [collections.deque(maxlen=eeg_buffer_size) for _ in range(NUM_EEG_CHANNELS)]
    ppg_data_buffer = collections.deque(maxlen=ppg_buffer_size)

    osc_server_instance, osc_thread = start_osc_server(args.osc_ip, args.osc_port)
    print("OSC server started (or attempted)") # Debug print
    logging.info("OSC server started (or attempted)") # Debug log
    
    if osc_server_instance is None:
        logging.error("Failed to initialize OSC server. Exiting.")
        return # Exit if server setup failed

    # --- Calculate Baseline ---
    if not calculate_baseline(args.baseline_duration, args): # Pass args
        print("calculate_baseline returned False") # Debug print
        logging.info("calculate_baseline returned False") # Debug log
        logging.error("Exiting due to baseline calculation failure.")
        if osc_server_instance: 
            osc_server_instance.shutdown()
        return

    # --- Initialize state variables for the loop ---
    current_loop_state = "Initializing" # State variable specific to the loop
    loop_tentative_history = collections.deque(maxlen=args.persistence) # Use arg

    # --- Real-time Monitoring Loop ---
    try:
        logging.info("Starting real-time monitoring...")
        while True:
            # Check if OSC server thread is still running
            if osc_thread and not osc_thread.is_alive():
                 logging.error("OSC server thread is no longer running. Exiting.")
                 break # Exit main loop if server thread died unexpectedly

            time.sleep(args.update_interval) # Use arg
            
            current_ratio = np.nan
            current_hr = np.nan
            eeg_window_samples = int(args.eeg_sampling_rate * args.eeg_window_duration) # Use args
            ppg_window_samples = int(args.ppg_sampling_rate * args.ppg_window_duration) # Use args
            
            ts_now = time.time()
            latest_ts = 0 # Track latest timestamp in the current window

            with data_lock:
                 # Check buffer lengths before attempting to grab windows
                 if len(eeg_data_buffers[0]) >= eeg_window_samples and \
                    len(ppg_data_buffer) >= ppg_window_samples:
                    
                    # Grab the most recent window of data
                    eeg_window_tuples = [list(buf)[-eeg_window_samples:] for buf in eeg_data_buffers]
                    ppg_window_tuples = list(ppg_data_buffer)[-ppg_window_samples:]
                    
                    # Extract timestamps and values
                    eeg_timestamps = np.array([t for t, v in eeg_window_tuples[0]]) # Use first channel's timestamps
                    eeg_values = np.array([[v for t, v in chan_tuples] for chan_tuples in eeg_window_tuples])
                    ppg_timestamps = np.array([t for t, v in ppg_window_tuples])
                    ppg_values = np.array([v for t, v in ppg_window_tuples])
                    
                    latest_eeg_ts = eeg_timestamps[-1] if len(eeg_timestamps) > 0 else 0
                    latest_ppg_ts = ppg_timestamps[-1] if len(ppg_timestamps) > 0 else 0
                    latest_ts = max(latest_eeg_ts, latest_ppg_ts)

                    # Check for stale data
                    if ts_now - latest_ts > args.stale_threshold:
                        logging.warning(f"Stale data detected! Last sample age: {ts_now - latest_ts:.1f}s (Threshold: {args.stale_threshold}s)")
                        # Set tentative state to uncertain due to stale data
                        loop_tentative_history.append("Uncertain (Stale Data)") 
                        # Skip feature calculation if data is stale
                        continue 
                    
                    # Calculate features if data is fresh
                    current_ratio = extract_alpha_beta_ratio(eeg_values, args.eeg_sampling_rate, args)
                    current_hr = estimate_bpm_from_ppg(ppg_values, args.ppg_sampling_rate, args)
                 else:
                     logging.info("Waiting for sufficient data buffers...")
                     # Optionally set tentative state to uncertain if buffers aren't full yet
                     loop_tentative_history.append("Initializing") 
                     continue # Skip this update cycle

            # Update state using the dedicated function
            current_loop_state = update_stress_state(
                current_ratio, current_hr, baseline_metrics, 
                current_loop_state, loop_tentative_history, args
            )

            # Log current state and features
            logging.info(f"State: {current_loop_state} | Ratio: {current_ratio:.2f} | HR: {current_hr:.1f} BPM")

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down.")
    except Exception as e:
        logging.exception(f"An unexpected error occurred in the main loop: {e}")
    finally:
        if osc_server_instance:
            logging.info("Shutting down OSC server.")
            osc_server_instance.shutdown()
        logging.info("Stress monitor stopped.")

if __name__ == '__main__':
    main()
