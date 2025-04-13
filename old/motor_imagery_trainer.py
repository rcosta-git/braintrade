import argparse
import os
import time
import numpy as np
import mne
from mne.time_frequency import psd_array_welch
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_validate
import joblib
import threading
from collections import deque
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

def extract_band_power_features(epochs_data, sampling_rate, bands):
    n_epochs, n_channels, n_times = epochs_data.shape
    n_bands = len(bands)
    features = np.zeros((n_epochs, n_channels * n_bands))
    for i, epoch_data in enumerate(epochs_data):
        for j, channel_data in enumerate(epoch_data):
            n_times = len(channel_data)
            n_fft = min(n_times, 256) # Use segment length if smaller than default n_fft
            if n_fft == 0: continue # Skip if segment is empty
            psd, freqs = psd_array_welch(channel_data, sfreq=sampling_rate, fmin=min(b[0] for b in bands.values()), fmax=max(b[1] for b in bands.values()), n_fft=n_fft, n_per_seg=n_fft) # Pass n_fft and n_per_seg
            band_powers = []
            for band_name, (fmin, fmax) in bands.items():
                band_power = np.mean(psd[(freqs >= fmin) & (freqs <= fmax)])
                band_powers.append(np.log(band_power + 1e-10))
            features[i, j*n_bands:(j+1)*n_bands] = band_powers
    return features

def main():
    parser = argparse.ArgumentParser(description='Motor Imagery EEG Data Trainer (OSC Version, Dual Model)')
    parser.add_argument('--osc-ip', type=str, default="0.0.0.0")
    parser.add_argument('--osc-port', type=int, default=5001)
    parser.add_argument('--session-name', type=str, required=True)
    parser.add_argument('--output-dir', type=str, default="training_data")
    parser.add_argument('--num-trials', type=int, default=20)
    parser.add_argument('--cue-duration', type=float, default=2.0)
    parser.add_argument('--imagery-duration', type=float, default=4.0)
    parser.add_argument('--rest-duration', type=float, default=3.0)
    parser.add_argument('--sampling-rate', type=float, required=True)
    parser.add_argument('--filter-low', type=float, default=8.0)
    parser.add_argument('--filter-high', type=float, default=30.0)
    parser.add_argument('--tmin', type=float, default=0.5)
    parser.add_argument('--tmax', type=float, default=3.5)
    parser.add_argument('--csp-components', type=int, default=4)
    parser.add_argument('--cv-folds', type=int, default=5)
    parser.add_argument('--log-file', type=str, default='training_log.md', help='Path to Markdown log file for training sessions')
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
            print(f"Trial {trial_num + 1}/{total_trials}: Cue: {cue_text}. Imagine the feeling of moving your {cue_text.lower()}...")
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
        # Use standard Muse S channel names and montage for CSP plotting
        ch_names = ['TP9', 'AF7', 'AF8', 'TP10']
        ch_types = ['eeg'] * NUM_EEG_CHANNELS
        sfreq = args.sampling_rate
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
        # Set standard 10-20 montage for scalp locations
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
        filter_phase = 'zero'
        print("Bandpass filter applied.")
        bands = {'Alpha': (8, 13), 'Beta': (13, 30)}
        epochs_data_filtered = epochs.get_data()
        y = epochs.events[:, -1]
        # --- Band Power Features ---
        print("Extracting band power features...")
        X_bp = extract_band_power_features(epochs_data_filtered, sfreq, bands)
        print(f"Band power feature shape: {X_bp.shape}")
        # --- CSP Features ---
        print("Extracting CSP features...")
        csp = mne.decoding.CSP(n_components=args.csp_components, reg=None, log=True, norm_trace=False)
        X_csp = csp.fit_transform(epochs_data_filtered, y)
        print(f"CSP feature shape: {X_csp.shape}")
        # --- Visualize CSP Patterns ---
        try:
            fig = csp.plot_patterns(epochs.info, ch_type='eeg', show_names=True, units='Patterns (AU)', size=1.5)
            csp_plot_filename = os.path.join(args.output_dir, f"{args.session_name}_csp_patterns.png")
            fig.savefig(csp_plot_filename)
            plt.close(fig)
            print(f"Saved CSP patterns plot to: {csp_plot_filename}")
        except Exception as e:
            print(f"Warning: Could not plot/save CSP patterns: {e}")
        # --- Define Pipelines ---
        pipe_bp = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])
        pipe_csp = Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())])
        # --- Cross-Validation Evaluation ---
        n_samples = len(y)
        unique, counts = np.unique(y, return_counts=True)
        min_class_count = counts.min() if len(counts) > 0 else 0
        n_splits = min(args.cv_folds, n_samples, min_class_count)
        scoring_metrics = ['accuracy', 'f1', 'roc_auc']
        if n_splits >= 2:
            print(f"Evaluating Band Power pipeline with {n_splits}-fold CV...")
            cv_results_bp = cross_validate(pipe_bp, X_bp, y, cv=n_splits, scoring=scoring_metrics)
            print(f"--- Band Power Evaluation ({n_splits}-Fold CV) ---")
            print(f"  Accuracy: {cv_results_bp['test_accuracy'].mean():.4f} +/- {cv_results_bp['test_accuracy'].std():.4f}")
            print(f"  F1-Score: {cv_results_bp['test_f1'].mean():.4f} +/- {cv_results_bp['test_f1'].std():.4f}")
            print(f"  AUC:      {cv_results_bp['test_roc_auc'].mean():.4f} +/- {cv_results_bp['test_roc_auc'].std():.4f}")
            print(f"Evaluating CSP pipeline with {n_splits}-fold CV...")
            cv_results_csp = cross_validate(pipe_csp, X_csp, y, cv=n_splits, scoring=scoring_metrics)
            print(f"--- CSP Evaluation ({n_splits}-Fold CV) ---")
            print(f"  Accuracy: {cv_results_csp['test_accuracy'].mean():.4f} +/- {cv_results_csp['test_accuracy'].std():.4f}")
            print(f"  F1-Score: {cv_results_csp['test_f1'].mean():.4f} +/- {cv_results_csp['test_f1'].std():.4f}")
            print(f"  AUC:      {cv_results_csp['test_roc_auc'].mean():.4f} +/- {cv_results_csp['test_roc_auc'].std():.4f}")
        else:
            print(f"Not enough samples for cross-validation (n_splits={n_splits}). Skipping CV evaluation.")
            cv_results_bp = {'test_accuracy': np.array([np.nan]), 'test_f1': np.array([np.nan]), 'test_roc_auc': np.array([np.nan])}
            cv_results_csp = {'test_accuracy': np.array([np.nan]), 'test_f1': np.array([np.nan]), 'test_roc_auc': np.array([np.nan])}
        # --- Retrain on Full Data ---
        pipe_bp.fit(X_bp, y)
        pipe_csp.fit(X_csp, y)
        # --- Save Artifacts ---
        bp_model_file = os.path.join(args.output_dir, f"{args.session_name}_bandpower_model.joblib")
        artifacts_bp = {
            'model': pipe_bp,
            'sampling_rate': sfreq,
            'filter_low': args.filter_low,
            'filter_high': args.filter_high,
            'filter_phase': filter_phase,
            'tmin': 0,
            'tmax': (min_segment_len - 1) / sfreq,
            'feature_method': 'bandpower',
            'bands': bands,
            'ch_names': ch_names,
            'cv_accuracy_mean': np.nanmean(cv_results_bp['test_accuracy']),
            'cv_accuracy_std': np.nanstd(cv_results_bp['test_accuracy']),
            'cv_f1_mean': np.nanmean(cv_results_bp['test_f1']),
            'cv_f1_std': np.nanstd(cv_results_bp['test_f1']),
            'cv_auc_mean': np.nanmean(cv_results_bp['test_roc_auc']),
            'cv_auc_std': np.nanstd(cv_results_bp['test_roc_auc'])
        }
        joblib.dump(artifacts_bp, bp_model_file)
        print(f"Band Power model artifacts saved to: {bp_model_file}")
        csp_model_file = os.path.join(args.output_dir, f"{args.session_name}_csp_model.joblib")
        artifacts_csp = {
            'model': pipe_csp,
            'sampling_rate': sfreq,
            'filter_low': args.filter_low,
            'filter_high': args.filter_high,
            'filter_phase': filter_phase,
            'tmin': 0,
            'tmax': (min_segment_len - 1) / sfreq,
            'feature_method': 'csp',
            'csp': csp,
            'csp_components': args.csp_components,
            'ch_names': ch_names,
            'cv_accuracy_mean': np.nanmean(cv_results_csp['test_accuracy']),
            'cv_accuracy_std': np.nanstd(cv_results_csp['test_accuracy']),
            'cv_f1_mean': np.nanmean(cv_results_csp['test_f1']),
            'cv_f1_std': np.nanstd(cv_results_csp['test_f1']),
            'cv_auc_mean': np.nanmean(cv_results_csp['test_roc_auc']),
            'cv_auc_std': np.nanstd(cv_results_csp['test_roc_auc'])
        }
        joblib.dump(artifacts_csp, csp_model_file)

        # --- Logging to Markdown file ---
        log_file = args.log_file
        try:
            with open(log_file, 'a') as f:
                f.write(f"## Session: {args.session_name}\n")
                f.write(f"* Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"* Trials per class: {args.num_trials}\n")
                f.write(f"* Imagery duration: {args.imagery_duration}s\n")
                f.write(f"* Filter band: {args.filter_low}-{args.filter_high} Hz\n")
                f.write(f"* CSP components: {args.csp_components}\n")
                f.write(f"* CV folds: {args.cv_folds}\n")
                f.write("\n")
                f.write(f"**Band Power Model:** `{os.path.basename(bp_model_file)}`\n")
                f.write(f"  * CV Accuracy: {cv_results_bp['test_accuracy'].mean():.4f} +/- {cv_results_bp['test_accuracy'].std():.4f}\n")
                f.write(f"  * CV F1-Score: {cv_results_bp['test_f1'].mean():.4f} +/- {cv_results_bp['test_f1'].std():.4f}\n")
                f.write(f"  * CV AUC: {cv_results_bp['test_roc_auc'].mean():.4f} +/- {cv_results_bp['test_roc_auc'].std():.4f}\n")
                f.write(f"**CSP Model:** `{os.path.basename(csp_model_file)}`\n")
                f.write(f"  * CV Accuracy: {cv_results_csp['test_accuracy'].mean():.4f} +/- {cv_results_csp['test_accuracy'].std():.4f}\n")
                f.write(f"  * CV F1-Score: {cv_results_csp['test_f1'].mean():.4f} +/- {cv_results_csp['test_f1'].std():.4f}\n")
                f.write(f"  * CV AUC: {cv_results_csp['test_roc_auc'].mean():.4f} +/- {cv_results_csp['test_roc_auc'].std():.4f}\n")
                f.write(f"  * CSP Patterns Plot: `")
                if os.path.exists(os.path.join(args.output_dir, f"{args.session_name}_csp_patterns.png")):
                    f.write(f"`{os.path.basename(csp_plot_filename)}`\n")
                else:
                    f.write("Not saved (plotting failed)\n")
                f.write("\n---\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {log_file} - {e}")
        print(f"CSP model artifacts saved to: {csp_model_file}")
    except KeyboardInterrupt:
        print("\nTrainer script stopped by user.")
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