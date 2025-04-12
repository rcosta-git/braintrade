import argparse
import os
import time
import numpy as np
import mne
from mne.time_frequency import psd_array_welch
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import joblib
import threading
from collections import deque, defaultdict # Added deque
from pythonosc import dispatcher, osc_server # Added python-osc

# --- Global Data Storage (Thread-Safe) ---
# Assuming 4 EEG channels (TP9, AF7, AF8, TP10) based on common Muse setups
NUM_EEG_CHANNELS = 4
# Max buffer size per channel (adjust based on expected data rate and imagery duration)
# E.g., 5 seconds of data at 256Hz = 1280 samples
EEG_BUFFER_SIZE = 1500 
eeg_data_buffers = [deque(maxlen=EEG_BUFFER_SIZE) for _ in range(NUM_EEG_CHANNELS)]
latest_horseshoe = deque(maxlen=1)
data_collection_active = False
data_lock = threading.Lock()

# --- Marker Definitions ---
LEFT_MARKER = 1
RIGHT_MARKER = 2
REST_MARKER = 99  # Optional, if needed

# --- OSC Message Handlers ---
def handle_eeg(address, *args):
    """Handles incoming EEG data packets."""
    global data_collection_active, eeg_data_buffers
    # Check if data collection is active and we received at least NUM_EEG_CHANNELS values
    if data_collection_active and len(args) >= NUM_EEG_CHANNELS: 
        with data_lock:
            # Process only the first NUM_EEG_CHANNELS arguments
            for i in range(NUM_EEG_CHANNELS): 
                # Ensure data is float, handle potential errors if needed
                try:
                    eeg_data_buffers[i].append(float(args[i]))
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert EEG data point {args[i]} to float.")
                    # Optionally append NaN or skip this sample
                    eeg_data_buffers[i].append(np.nan) 

def handle_horseshoe(address, *args):
    """Handles incoming headband status (horseshoe) data."""
    global latest_horseshoe
    # Expecting 4 values indicating sensor status (1=good, 2=ok, >=3=bad)
    if len(args) == NUM_EEG_CHANNELS: # Assuming horseshoe also sends 4 values
        with data_lock:
            latest_horseshoe.clear()
            latest_horseshoe.append(list(args))

def handle_default(address, *args):
    """Handles any OSC address not explicitly mapped."""
    # print(f"Received unhandled OSC message: {address} {args}") # Optional: for debugging
    pass

# --- OSC Server Setup ---
def start_osc_server(ip, port):
    """Initializes and starts the OSC server in a separate thread."""
    disp = dispatcher.Dispatcher()

    # Map OSC addresses to handler functions
    # Common addresses for Muse EEG and Horseshoe - verify with your Muse Direct settings
    disp.map("/muse/eeg", handle_eeg)
    disp.map("/eeg", handle_eeg) 
    disp.map("/muse/elements/horseshoe", handle_horseshoe)
    disp.map("/hsi", handle_horseshoe) # Alternative address sometimes used

    # Set a default handler for unmapped messages
    disp.set_default_handler(handle_default)

    # Start the OSC server
    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"OSC Server listening on {server.server_address}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

# --- Feature Extraction Function ---
# (Moved here as it's independent of data acquisition method)
def extract_band_power_features(epochs_data, sampling_rate, filter_low, filter_high, bands):
    n_epochs, n_channels, n_times = epochs_data.shape
    n_bands = len(bands)
    features = np.zeros((n_epochs, n_channels * n_bands))

    for i, epoch_data in enumerate(epochs_data):
        for j, channel_data in enumerate(epoch_data):
            # Calculate PSD using Welch's method
            # Ensure channel_data doesn't contain NaNs introduced during handling
            valid_channel_data = channel_data[~np.isnan(channel_data)]
            if len(valid_channel_data) < 2: # Need at least 2 points for PSD
                 print(f"Warning: Not enough valid data points in epoch {i}, channel {j} after NaN removal. Skipping PSD calculation.")
                 psd = np.zeros_like(np.fft.rfftfreq(n_times, 1./sampling_rate)) # Placeholder PSD
                 freqs = np.fft.rfftfreq(n_times, 1./sampling_rate)
            else:
                 psd, freqs = psd_array_welch(valid_channel_data, sfreq=sampling_rate, fmin=filter_low, fmax=filter_high, n_fft=min(len(valid_channel_data), 256)) # Adjust n_fft if needed

            # Extract band powers
            band_powers = []
            for band_name, (fmin, fmax) in bands.items():
                # Handle cases where PSD calculation might have failed or freqs are empty
                if len(freqs) > 0:
                    freq_mask = (freqs >= fmin) & (freqs <= fmax)
                    if np.any(freq_mask):
                         band_power = np.mean(psd[freq_mask])
                    else:
                         band_power = 0.0 # Or np.nan, if preferred
                else:
                    band_power = 0.0 # Or np.nan
                band_powers.append(band_power)


            # Store band power features
            features[i, j*n_bands:(j+1)*n_bands] = band_powers
    return features

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description='Motor Imagery EEG Data Trainer (OSC Version)')

    # --- OSC Server Settings ---
    parser.add_argument('--osc-ip', type=str, default="0.0.0.0", help='IP address for OSC server to listen on (default: 0.0.0.0)')
    parser.add_argument('--osc-port', type=int, default=5001, help='UDP port for OSC server to listen on (default: 5001)')
    
    # --- Session and File Settings ---
    parser.add_argument('--session-name', type=str, required=True, help='Base name for output files (e.g., "mi_session_01")')
    parser.add_argument('--output-dir', type=str, default="training_data", help='Directory to save model artifacts (default: training_data)')
    # Raw data saving is handled differently now (not a single BrainFlow file)

    # --- Trial Paradigm Settings ---
    parser.add_argument('--num-trials', type=int, default=20, help='Number of trials per class (Left/Right, default: 20)')
    parser.add_argument('--cue-duration', type=float, default=2.0, help='Cue display duration (seconds, default: 2.0)')
    parser.add_argument('--imagery-duration', type=float, default=4.0, help='Motor imagery duration (seconds, default: 4.0)')
    parser.add_argument('--rest-duration', type=float, default=3.0, help='Rest duration between trials (seconds, default: 3.0)')
    
    # --- MNE Processing Settings ---
    # ** Sampling Rate is crucial and must be known for OSC **
    parser.add_argument('--sampling-rate', type=float, required=True, help='Sampling rate of the EEG data in Hz (e.g., 256 for Muse S)')
    parser.add_argument('--filter-low', type=float, default=8.0, help='Lower cutoff frequency for bandpass filter (Hz, default: 8.0)')
    parser.add_argument('--filter-high', type=float, default=30.0, help='Higher cutoff frequency for bandpass filter (Hz, default: 30.0)')
    parser.add_argument('--tmin', type=float, default=0.5, help='Epoch start time relative to cue onset (seconds, default: 0.5)')
    parser.add_argument('--tmax', type=float, default=3.5, help='Epoch end time relative to cue onset (seconds, default: 3.5)')
    # parser.add_argument('--use-ica', action='store_true', help='Enable ICA for artifact removal (experimental, default: False)') # Keep ICA optional if desired
    parser.add_argument('--feature-method', type=str, choices=['bandpower'], default='bandpower', help='Feature extraction method (default: bandpower)') # Only bandpower implemented here
    # parser.add_argument('--csp-components', type=int, default=4, help='Number of CSP components to use (if feature-method=csp, default: 4)') # Remove CSP args for now


    args = parser.parse_args()
    
    # --- Start OSC Server ---
    osc_server_instance, osc_thread = start_osc_server(args.osc_ip, args.osc_port)
    
    all_imagery_segments = []
    all_labels = []
    
    # Use a global variable for the flag
    global data_collection_active 

    try:
        # --- Data Acquisition Paradigm ---
        total_trials = args.num_trials * 2 # Left and Right
        
        # Create a shuffled list of cues (Markers)
        trial_labels = ([LEFT_MARKER] * args.num_trials) + ([RIGHT_MARKER] * args.num_trials)
        np.random.shuffle(trial_labels)

        print("Starting data acquisition paradigm. Ensure Muse Direct is streaming.")
        print(f"Total trials: {total_trials}")
        time.sleep(2) # Give OSC stream time to stabilize if just started

        for trial_num, label in enumerate(trial_labels):
            print(f"\nTrial {trial_num + 1}/{total_trials}: Get Ready...")
            time.sleep(args.cue_duration) # Use cue duration as ready time
            # print(f"data_collection_active before setting True: {data_collection_active}") # Diagnostic print - removed

            cue_text = "LEFT" if label == LEFT_MARKER else "RIGHT"
            print(f"Trial {trial_num + 1}/{total_trials}: Cue: {cue_text}. Imagine...")

            # --- Start collecting data for this trial ---
            with data_lock:
                # Clear buffers before starting collection for this trial
                for buf in eeg_data_buffers:
                    buf.clear()
                data_collection_active = True
                # print(f"data_collection_active set to True") # Diagnostic print - removed
            
            # --- Imagery Period ---
            time.sleep(args.imagery_duration)
            # print(f"data_collection_active before setting False: {data_collection_active}") # Diagnostic print - removed

            # --- Stop collecting data ---
            with data_lock:
                data_collection_active = False
                # print(f"data_collection_active set to False") # Diagnostic print - removed
                # Retrieve collected data immediately after stopping
                # Convert deques to list of lists, then to numpy array (channels x samples)
                current_segment_list = [list(buf) for buf in eeg_data_buffers]
                # print(f"EEG data buffers (lengths): {[len(buf) for buf in eeg_data_buffers]}") # Diagnostic print - removed
                
                # Check if data was actually collected (buffers might be empty if OSC wasn't streaming)
                if not any(current_segment_list):
                     print("Warning: No EEG data collected for this trial. Check OSC stream.")
                     # Decide how to handle: skip trial, error out, etc.
                     # For now, we'll skip adding this trial's data.
                     segment_data = None
                else:
                     # Find the minimum length across channel buffers in case of slight variations
                     min_len = min(len(ch) for ch in current_segment_list)
                     if min_len == 0:
                          print("Warning: Collected EEG data buffers have zero minimum length. Skipping trial.")
                          segment_data = None
                     else:
                          # Trim all channels to the minimum length and convert to NumPy array
                          segment_data = np.array([ch[:min_len] for ch in current_segment_list])
                          print(f"Collected segment shape: {segment_data.shape}")
                          all_imagery_segments.append(segment_data)
                          all_labels.append(label)

                # Check headband status
                if latest_horseshoe:
                    status = latest_horseshoe[0]
                    if any(s >= 3 for s in status): # Check if any sensor is bad (>=3)
                        print(f"!!! HEADBAND STATUS WARNING: {status} !!!")
                else:
                    print("Warning: No headband status received yet.")
            # --- End of data retrieval ---

            print(f"Trial {trial_num + 1}/{total_trials}: Rest...")
            time.sleep(args.rest_duration)
            
        print("\nData acquisition complete.")

        # --- Consolidate Data ---
        if not all_imagery_segments:
            print("Error: No data segments were collected. Exiting.")
            return # Exit if no data was gathered

        # Concatenate segments along the time axis (axis=1)
        # Note: This assumes segments might have slightly different lengths if OSC packets were dropped
        # MNE's Epochs object handles this better, let's build the Raw object first
        
        # --- Create MNE Raw Object from all data ---
        # We need to reconstruct a continuous Raw object to apply filters before epoching
        # This requires careful handling of segment boundaries and timestamps if we want
        # accurate event timing relative to the *start* of the recording.
        # Simpler approach for now: Process each segment somewhat independently?
        # Let's stick to the original plan: create epochs directly from segments.
        # This means filtering happens *after* epoching, which is less ideal but simpler here.

        # --- Create MNE Epochs Array ---
        print("Creating MNE EpochsArray...")
        # MNE expects data as (n_epochs, n_channels, n_times)
        # Need to ensure all segments have the same length for EpochsArray
        min_segment_len = min(seg.shape[1] for seg in all_imagery_segments)
        epochs_data_list = [seg[:, :min_segment_len] for seg in all_imagery_segments]
        epochs_data_np = np.stack(epochs_data_list, axis=0) # Shape: (n_epochs, n_channels, n_times)
        
        ch_names = [f'EEG {i+1}' for i in range(NUM_EEG_CHANNELS)] # Generic names
        # Or use standard Muse names if we are sure about the order from OSC
        # ch_names = ['TP9', 'AF7', 'AF8', 'TP10'] 
        ch_types = ['eeg'] * NUM_EEG_CHANNELS
        sfreq = args.sampling_rate
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
        
        # Create dummy events array - timing relative to epoch start (0)
        events_list = [[i * min_segment_len, 0, label] for i, label in enumerate(all_labels)]
        events_np = np.array(events_list)

        # Define the mapping for event IDs
        event_id = {'Left': LEFT_MARKER, 'Right': RIGHT_MARKER}
        # Create EpochsArray object
        epochs = mne.EpochsArray(epochs_data_np, info, events=events_np, tmin=0, event_id=event_id)
        print("EpochsArray created.")

        # --- Apply Filter (Now applied to Epochs) ---
        print(f"Applying bandpass filter ({args.filter_low} - {args.filter_high} Hz) to epochs...")
        epochs.filter(l_freq=args.filter_low, h_freq=args.filter_high, picks='eeg', method='iir', phase='zero')
        filter_phase = 'zero' # Hardcoded for now, will be saved later
        print("Bandpass filter applied.")

        # --- Extract Band Power Features ---
        print("Extracting band power features...")
        bands = {'Alpha': (8, 13), 'Beta': (13, 30)}
        # Get data *after* filtering
        epochs_data_filtered = epochs.get_data() 
        features = extract_band_power_features(epochs_data_filtered, sfreq, args.filter_low, args.filter_high, bands)
        print(f"Feature shape: {features.shape}")
        print("Band power features extracted.")

        # --- Prepare Data for Classification ---
        labels_for_clf = epochs.events[:, -1] # Get labels from epochs object
        X = features
        y = labels_for_clf

        # Adjust test size calculation based on the number of actual epochs created
        n_samples = len(y)
        n_classes = len(np.unique(y))
        test_size_prop = 0.2 # Desired proportion
        
        if n_samples < n_classes * 2: # Need at least 2 samples per class for train/test split with stratification
             print(f"Warning: Insufficient samples ({n_samples}) for stratified train/test split with {n_classes} classes. Skipping evaluation.")
             # Train on all data instead? Or require more trials?
             # For now, let's train on all data if split is not possible.
             X_train, y_train = X, y
             X_test, y_test = None, None # No test set
             accuracy = None
             class_report = "N/A (Insufficient data for evaluation)"
        else:
             calculated_test_size = int(np.ceil(n_samples * test_size_prop))
             min_test_size = n_classes # Need at least one sample per class in test set
             
             if calculated_test_size < min_test_size:
                 print(f"Warning: Calculated test size ({calculated_test_size}) is smaller than the number of classes ({n_classes}). Adjusting test size to {min_test_size}.")
                 adjusted_test_size = min_test_size 
             else:
                 adjusted_test_size = calculated_test_size

             # Ensure train size is also sufficient (at least n_classes)
             if (n_samples - adjusted_test_size) < n_classes:
                  print(f"Warning: Adjusted test size ({adjusted_test_size}) leaves insufficient samples ({n_samples - adjusted_test_size}) for training with {n_classes} classes. Training on all data.")
                  X_train, y_train = X, y
                  X_test, y_test = None, None
                  accuracy = None
                  class_report = "N/A (Insufficient data for evaluation after test size adjustment)"
             else:
                  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=adjusted_test_size, stratify=y, random_state=42)


        # --- Train Classifier ---
        print("Training classifier...")
        # Using selected_channel_indices = None as we use all channels provided by OSC
        selected_channel_indices = list(range(NUM_EEG_CHANNELS)) 
        pipe = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])
        pipe.fit(X_train, y_train)
        print("Classifier trained.")

        # --- Evaluate Classifier (if possible) ---
        if X_test is not None:
            print("Evaluating classifier...")
            y_pred = pipe.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            class_report = classification_report(y_test, y_pred, target_names=event_id.keys())
            print(f"Accuracy: {accuracy:.4f}")
            print("Classification Report:\n", class_report)
            print("Classifier evaluated.")
        else:
             print("Skipping classifier evaluation due to insufficient data.")


        # --- Save Training Artifacts ---
        model_file = os.path.join(args.output_dir, f"{args.session_name}_model.joblib")
        artifacts = {
            'model': pipe,
            'selected_channel_indices': selected_channel_indices, 
            'sampling_rate': sfreq,
            'filter_low': args.filter_low,
            'filter_high': args.filter_high,
            'filter_phase': filter_phase,
            'tmin': 0, # Epochs start at 0 relative to segment start
            'tmax': (min_segment_len - 1) / sfreq, # Epochs end relative to segment start
            'feature_method': args.feature_method,
            'bands': bands,
            'ch_names': ch_names # Save channel names used
        }
        joblib.dump(artifacts, model_file)
        print(f"Training artifacts saved to: {model_file}")


    except KeyboardInterrupt:
        print("\nTrainer script stopped by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}") # Catch-all for other potential errors
        import traceback
        traceback.print_exc() # Print full traceback for debugging
    finally:
        print("Shutting down OSC server...")
        if osc_server_instance:
            osc_server_instance.shutdown()
            # osc_thread.join() # Optional: wait for thread to finish cleanly
        print("Server stopped.")

def extract_band_power_features(epochs_data, sampling_rate, filter_low, filter_high, bands):
    n_epochs, n_channels, n_times = epochs_data.shape
    n_bands = len(bands)
    features = np.zeros((n_epochs, n_channels * n_bands))

    for i, epoch_data in enumerate(epochs_data):
        for j, channel_data in enumerate(epoch_data):
            # Calculate PSD using Welch's method
            psd, freqs = psd_array_welch(channel_data, sfreq=sampling_rate, fmin=filter_low, fmax=filter_high)

            # Extract band powers
            band_powers = []
            for band_name, (fmin, fmax) in bands.items():
                band_power = np.mean(psd[(freqs >= fmin) & (freqs <= fmax)])
                band_powers.append(band_power)

            # Store band power features
            features[i, j*n_bands:(j+1)*n_bands] = band_powers
    return features


if __name__ == "__main__":
    main()