import argparse
import os
import time
import numpy as np
import mne
from mne.time_frequency import psd_array_welch
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_validate
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
    parser = argparse.ArgumentParser(description='Combined Session Motor Imagery EEG Trainer')
    parser.add_argument('--epoch-files', nargs='+', required=True, help='List of paths to session _epo.fif files to combine')
    parser.add_argument('--combined-session-name', type=str, required=True, help='Base name for combined model output files')
    parser.add_argument('--output-dir', type=str, default="training_data")
    parser.add_argument('--csp-components', type=int, default=4)
    parser.add_argument('--cv-folds', type=int, default=5)
    parser.add_argument('--filter-low', type=float, default=8.0, help='Lower cutoff frequency for bandpass filter (Hz, default: 8.0)')
    parser.add_argument('--filter-high', type=float, default=30.0, help='Higher cutoff frequency for bandpass filter (Hz, default: 30.0)')
    parser.add_argument('--tmin', type=float, default=0.5, help='Epoch start time relative to cue onset (seconds, default: 0.5)')
    parser.add_argument('--tmax', type=float, default=3.5, help='Epoch end time relative to cue onset (seconds, default: 3.5)')
    parser.add_argument('--log-file', type=str, default='training_log.md')

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    all_epochs_list = []
    print("Loading epoch files...")
    for fname in args.epoch_files:
        try:
            epochs = mne.read_epochs(fname, preload=True)
            print(f"  Loaded: {fname} ({len(epochs)} epochs)")
            if all_epochs_list and epochs.info['sfreq'] != all_epochs_list[0].info['sfreq']:
                 raise ValueError("Sampling rates differ between epoch files!")
            if all_epochs_list and epochs.ch_names != all_epochs_list[0].ch_names:
                 raise ValueError("Channel names differ between epoch files!")
            all_epochs_list.append(epochs)
        except Exception as e:
            print(f"Error loading {fname}: {e}. Skipping.")
    if not all_epochs_list:
        print("Error: No valid epoch files loaded. Exiting.")
        return

    min_epoch_samples = float('inf') # Initialize to infinity
    for epochs in all_epochs_list:
        min_epoch_samples = min(min_epoch_samples, len(epochs.times))

    cropped_epochs_list = []
    print("Cropping epochs to consistent length...")
    for epochs in all_epochs_list:
        cropped_epochs = epochs.copy().crop(tmin=0, tmax=min_epoch_samples / epochs.info['sfreq'], include_tmax=False) # include_tmax=False to exclude tmax exactly
        cropped_epochs_list.append(cropped_epochs)
    
    print("Concatenating epochs...")
    combined_epochs = mne.concatenate_epochs(cropped_epochs_list)
    print(f"Combined dataset: {len(combined_epochs)} epochs, cropped to {min_epoch_samples} time points.")
    
    epochs_data_filtered = combined_epochs.get_data()
    y = combined_epochs.events[:, -1]
    sfreq = combined_epochs.info['sfreq']
    ch_names = combined_epochs.ch_names
    bands = {'Alpha': (8, 13), 'Beta': (13, 30)}

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
    csp_plot_filename = None # Initialize
    try:
        fig = csp.plot_patterns(combined_epochs.info, ch_type='eeg', show_names=True, units='Patterns (AU)', size=1.5)
        csp_plot_filename = os.path.join(args.output_dir, f"{args.combined_session_name}_csp_patterns.png")
        fig.savefig(csp_plot_filename)
        plt.close(fig)
        print(f"Saved CSP patterns plot to: {csp_plot_filename}")
    except Exception as e:
        print(f"Warning: Could not plot/save CSP patterns: {e}")

    # --- Define Pipelines ---
    pipe_bp = Pipeline([('scaler', StandardScaler()), ('clf', SVC(probability=True))])
    pipe_csp = Pipeline([('scaler', StandardScaler()), ('clf', SVC(probability=True))])

    # --- Cross-Validation Evaluation ---
    n_splits = args.cv_folds
    scoring_metrics = ['accuracy', 'f1', 'roc_auc']

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

    # --- Retrain on Full Data ---
    pipe_bp.fit(X_bp, y)
    pipe_csp.fit(X_csp, y)

    # --- Save Artifacts ---
    bp_model_file = os.path.join(args.output_dir, f"{args.combined_session_name}_bandpower_model.joblib")
    artifacts_bp = {
        'model': pipe_bp,
        'sampling_rate': sfreq,
        'filter_low': args.filter_low, # Assuming filter params are consistent across sessions
        'filter_high': args.filter_high,
        'tmin': args.tmin, # Assuming tmin/tmax are consistent
        'tmax': args.tmax,
        'feature_method': 'bandpower',
        'bands': bands,
        'ch_names': ch_names,
        'cv_accuracy_mean': np.nanmean(cv_results_bp['test_accuracy']),
        'cv_accuracy_std': np.nanstd(cv_results_bp['test_accuracy']),
        'cv_f1_mean': np.nanmean(cv_results_bp['test_f1']),
        'cv_f1_std': np.nanstd(cv_results_bp['test_f1']),
        'cv_auc_mean': np.nanmean(cv_results_bp['test_roc_auc']),
        'cv_auc_std': np.nanstd(cv_results_bp['test_roc_auc'].std()),
        'epoch_files_used': args.epoch_files # Log which epoch files were combined
    }
    joblib.dump(artifacts_bp, bp_model_file)
    print(f"Combined Band Power model artifacts saved to: {bp_model_file}")

    csp_model_file = os.path.join(args.output_dir, f"{args.combined_session_name}_csp_model.joblib")
    artifacts_csp = {
        'model': pipe_csp,
        'sampling_rate': sfreq,
        'filter_low': args.filter_low,
        'filter_high': args.filter_high,
        'tmin': args.tmin,
        'tmax': args.tmax,
        'feature_method': 'csp',
        'csp': csp,
        'csp_components': args.csp_components,
        'ch_names': ch_names,
        'cv_accuracy_mean': np.nanmean(cv_results_csp['test_accuracy']),
        'cv_accuracy_std': np.nanstd(cv_results_csp['test_accuracy']),
        'cv_f1_mean': np.nanmean(cv_results_csp['test_f1']),
        'cv_f1_std': np.nanstd(cv_results_csp['test_f1']),
        'cv_auc_mean': np.nanmean(cv_results_csp['test_roc_auc']),
        'cv_auc_std': np.nanstd(cv_results_csp['test_roc_auc'].std()),
        'epoch_files_used': args.epoch_files # Log which epoch files were combined
    }
    joblib.dump(artifacts_csp, csp_model_file)
    print(f"Combined CSP model artifacts saved to: {csp_model_file}")

    # --- Logging to Markdown file ---
    log_file = args.log_file
    try:
        with open(log_file, 'a') as f:
            f.write(f"## Combined Session Training: {args.combined_session_name}\n")
            f.write(f"* Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("* Combined Epoch Files:\n")
            for file_ in args.epoch_files:
                f.write(f"    * `{file_}`\n")
            f.write(f"* CSP components: {args.csp_components}\n")
            f.write(f"* CV folds: {args.cv_folds}\n")
            f.write("\n")
            f.write(f"**Combined Band Power Model:** `{os.path.basename(bp_model_file)}`\n")
            f.write(f"  * CV Accuracy: {cv_results_bp['test_accuracy'].mean():.4f} +/- {cv_results_bp['test_accuracy'].std():.4f}\n")
            f.write(f"  * CV F1-Score: {cv_results_bp['test_f1'].mean():.4f} +/- {cv_results_bp['test_f1'].std():.4f}\n")
            f.write(f"  * CV AUC: {cv_results_bp['test_roc_auc'].mean():.4f} +/- {cv_results_bp['test_roc_auc'].std():.4f}\n")
            f.write(f"**Combined CSP Model:** `{os.path.basename(csp_model_file)}`\n")
            f.write(f"  * CV Accuracy: {cv_results_csp['test_accuracy'].mean():.4f} +/- {cv_results_csp['test_accuracy'].std():.4f}\n")
            f.write(f"  * CV F1-Score: {cv_results_csp['test_f1'].mean():.4f} +/- {cv_results_csp['test_f1'].std():.4f}\n")
            f.write(f"  * CV AUC: {cv_results_csp['test_roc_auc'].mean():.4f} +/- {cv_results_csp['test_roc_auc'].std():.4f}\n")
            f.write(f"  * CSP Patterns Plot: ")
            if csp_plot_filename and os.path.exists(csp_plot_filename):
                f.write(f"`{os.path.basename(csp_plot_filename)}`\n")
            else:
                f.write("Not saved (plotting failed or file missing)\n")
            f.write("\n---\n")
    except Exception as e:
        print(f"Warning: Could not write to log file: {log_file} - {e}")


if __name__ == "__main__":
    main()
