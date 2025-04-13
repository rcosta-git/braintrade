import argparse
import os
import time
import numpy as np
import mne
from collections import deque
import threading
from pythonosc import dispatcher, osc_server
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Global Data Storage (Thread-Safe) ---
NUM_EEG_CHANNELS = 4
EEG_BUFFER_SIZE = 1500
eeg_data_buffers = [deque(maxlen=EEG_BUFFER_SIZE) for _ in range(NUM_EEG_CHANNELS)]
latest_horseshoe = deque(maxlen=1)
data_collection_active = False
data_lock = threading.Lock()

LEFT_MARKER = 1
RIGHT_MARKER = 2

def handle_eeg(address, *args):
    global data_collection_active, eeg_data_buffers
    if data_collection_active and len(args) >= NUM_EEG_CHANNELS:
        with data_lock:
            for i in range(NUM_EEG_CHANNELS):
                try:
                    eeg_data_buffers[i].append(float(args[i]))
                except (ValueError, TypeError):
                    eeg_data_buffers[i].append(np.nan)

def handle_horseshoe(address, *args):
    global latest_horseshoe
    if len(args) == NUM_EEG_CHANNELS:
        with data_lock:
            latest_horseshoe.clear()
            latest_horseshoe.append(list(args))

def handle_default(address, *args):
    pass

def start_osc_server(ip, port):
    disp = dispatcher.Dispatcher()
    disp.map("/muse/eeg", handle_eeg)
    disp.map("/eeg", handle_eeg)
    disp.map("/muse/elements/horseshoe", handle_horseshoe)
    disp.map("/hsi", handle_horseshoe)
    disp.set_default_handler(handle_default)
    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"OSC Server listening on {server.server_address}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def main():
    parser = argparse.ArgumentParser(description='Motor Imagery EEG Data Collector (OSC)')
    parser.add_argument('--osc-ip', type=str, default="0.0.0.0")
    parser.add_argument('--osc-port', type=int, default=5001)
    parser.add_argument('--session-name', type=str, required=True, help='Base name for output files (e.g., "session1")')
    parser.add_argument('--output-dir', type=str, default="training_data", help='Directory to save epoch data (default: training_data)')
    parser.add_argument('--num-trials', type=int, default=20, help='Number of trials per class (Left/Right, default: 20)')
    parser.add_argument('--cue-duration', type=float, default=2.0, help='Cue display duration (seconds, default: 2.0)')
    parser.add_argument('--imagery-duration', type=float, default=4.0, help='Motor imagery duration (seconds, default: 4.0)')
    parser.add_argument('--rest-duration', type=float, default=3.0, help='Rest duration between trials (seconds, default: 3.0)')
    parser.add_argument('--sampling-rate', type=float, required=True, help='Sampling rate of the EEG data in Hz (e.g., 256 for Muse S)')
    parser.add_argument('--filter-low', type=float, default=8.0, help='Lower cutoff frequency for bandpass filter (Hz, default: 8.0)')
    parser.add_argument('--filter-high', type=float, default=30.0, help='Higher cutoff frequency for bandpass filter (Hz, default: 30.0)')
    parser.add_argument('--tmin', type=float, default=0.5, help='Epoch start time relative to cue onset (seconds, default: 0.5)')
    parser.add_argument('--tmax', type=float, default=3.5, help='Epoch end time relative to cue onset (seconds, default: 3.5)')

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    osc_server_instance, osc_thread = start_osc_server(args.osc_ip, args.osc_port)
    all_imagery_segments = []
    all_labels = []
    global data_collection_active

    try:
        total_trials = args.num_trials * 2
        trial_labels = ([LEFT_MARKER] * args.num_trials) + ([RIGHT_MARKER] * args.num_trials)
        np.random.shuffle(trial_labels)
        print("Starting data acquisition paradigm. Ensure Muse Direct is streaming.")
        print(f"Total trials: {total_trials}")
        time.sleep(2)
        for trial_num, label in enumerate(trial_labels):
            print(f"\nTrial {trial_num + 1}/{total_trials}: Get Ready...")
            time.sleep(args.cue_duration)
            cue_text = "LEFT" if label == LEFT_MARKER else "RIGHT"
            print(f"Trial {trial_num + 1}/{total_trials}: Cue: {cue_text}. Imagine the feeling of moving your {cue_text.lower()} hand/arm...")
            with data_lock:
                for buf in eeg_data_buffers:
                    buf.clear()
                data_collection_active = True
            time.sleep(args.imagery_duration)
            with data_lock:
                data_collection_active = False
                current_segment_list = [list(buf) for buf in eeg_data_buffers]
                if not any(current_segment_list):
                    print("Warning: No EEG data collected for this trial. Check OSC stream.")
                    segment_data = None
                else:
                    min_len = min(len(ch) for ch in current_segment_list)
                    if min_len == 0:
                        print("Warning: Collected EEG data buffers have zero minimum length. Skipping trial.")
                        segment_data = None
                    else:
                        segment_data = np.array([ch[:min_len] for ch in current_segment_list])
                        print(f"Collected segment shape: {segment_data.shape}")
                        all_imagery_segments.append(segment_data)
                        all_labels.append(label)
                if latest_horseshoe:
                    status = latest_horseshoe[0]
                    if any(s >= 3 for s in status):
                        print(f"!!! HEADBAND STATUS WARNING: {status} !!!")
                else:
                    print("Warning: No headband status received yet.")
            print(f"Trial {trial_num + 1}/{total_trials}: Rest...")
            time.sleep(args.rest_duration)
        print("\nData acquisition complete.")
        if not all_imagery_segments:
            print("Error: No data segments were collected. Exiting.")
            return

        min_segment_len = min(seg.shape[1] for seg in all_imagery_segments)
        epochs_data_list = [seg[:, :min_segment_len] for seg in all_imagery_segments]
        epochs_data_np = np.stack(epochs_data_list, axis=0)
        ch_names = [f'EEG {i+1}' for i in range(NUM_EEG_CHANNELS)]
        ch_types = ['eeg'] * NUM_EEG_CHANNELS
        sfreq = args.sampling_rate
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
        try:
            montage = mne.channels.make_standard_montage('standard_1020')
            info.set_montage(montage, match_case=False)
        except Exception as e:
            print(f"Warning: Could not set montage for CSP plotting: {e}")
        events_list = [[i * min_segment_len, 0, label] for i, label in enumerate(all_labels)]
        events_np = np.array(events_list)
        event_id = {'Left': LEFT_MARKER, 'Right': RIGHT_MARKER}
        epochs = mne.EpochsArray(epochs_data_np, info, events=events_np, tmin=0, event_id=event_id)
        print("EpochsArray created.")
        print(f"Applying bandpass filter ({args.filter_low} - {args.filter_high} Hz) to epochs...")
        epochs.filter(l_freq=args.filter_low, h_freq=args.filter_high, picks='eeg', method='iir', phase='zero')
        print("Bandpass filter applied.")

        epoch_filename = os.path.join(args.output_dir, f"{args.session_name}_epo.fif")
        try:
            epochs.save(epoch_filename, overwrite=True)
            print(f"Saved filtered session epochs to: {epoch_filename}")
        except Exception as e:
            print(f"Error saving epochs to {epoch_filename}: {e}")


    except KeyboardInterrupt:
        print("\nData collector script stopped by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Shutting down OSC server...")
        if osc_server_instance:
            osc_server_instance.shutdown()
        print("Server stopped.")


if __name__ == "__main__":
    main()