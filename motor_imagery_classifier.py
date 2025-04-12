import argparse
import time
import numpy as np
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
import collections
import joblib
import mne

def parse_args():
    parser = argparse.ArgumentParser(description="Real-time Motor Imagery Classifier (Muse S, OSC, MNE)")
    parser.add_argument("--model-file", type=str, required=True, help="Path to trained model artifact (.joblib)")
    parser.add_argument("--osc-ip", type=str, default="0.0.0.0", help="OSC server IP to listen on")
    parser.add_argument("--osc-port", type=int, default=5001, help="OSC server port")
    parser.add_argument("--update-interval", type=float, default=0.5, help="Prediction interval (seconds)")
    return parser.parse_args()

def main():
    args = parse_args()
    artifacts = joblib.load(args.model_file)
    model = artifacts["model"]
    sampling_rate = artifacts["sampling_rate"]
    filter_low = artifacts["filter_low"]
    filter_high = artifacts["filter_high"]
    tmin = artifacts["tmin"]
    tmax = artifacts["tmax"]
    feature_method = artifacts["feature_method"]
    ch_names = artifacts["ch_names"]
    window_duration = tmax - tmin
    window_samples = int(window_duration * sampling_rate)
    NUM_EEG_CHANNELS = len(ch_names)
    bands = artifacts.get("bands", None)
    csp = artifacts.get("csp", None)

    # OSC buffers and threading
    eeg_data_buffers = [collections.deque(maxlen=window_samples*2) for _ in range(NUM_EEG_CHANNELS)]
    latest_horseshoe = collections.deque(maxlen=1)
    data_lock = threading.Lock()

    def handle_eeg(address, *args_):
        with data_lock:
            for i in range(NUM_EEG_CHANNELS):
                try:
                    eeg_data_buffers[i].append(float(args_[i]))
                except Exception:
                    pass

    def handle_horseshoe(address, *args_):
        with data_lock:
            latest_horseshoe.clear()
            latest_horseshoe.append(list(args_))

    dispatcher = Dispatcher()
    dispatcher.map("/muse/eeg", handle_eeg)
    dispatcher.map("/eeg", handle_eeg)
    dispatcher.map("/muse/elements/horseshoe", handle_horseshoe)
    dispatcher.map("/hsi", handle_horseshoe)

    server = ThreadingOSCUDPServer((args.osc_ip, args.osc_port), dispatcher)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"OSC server started on {args.osc_ip}:{args.osc_port}")

    bar_width = 20

    try:
        while True:
            time.sleep(args.update_interval)
            with data_lock:
                if all(len(buf) >= window_samples for buf in eeg_data_buffers):
                    window_data_np = np.array([list(buf)[-window_samples:] for buf in eeg_data_buffers])
                    horseshoe = latest_horseshoe[-1] if latest_horseshoe else None
                else:
                    print("Buffering...")
                    continue
            if np.isnan(window_data_np).any():
                print("NaNs in data, skipping this window.")
                continue
            # Preprocessing: bandpass filter
            filtered = mne.filter.filter_data(window_data_np, sfreq=sampling_rate, l_freq=filter_low, h_freq=filter_high, verbose=False)
            # Feature extraction
            features = None
            if feature_method == "bandpower":
                features = extract_band_power_features(filtered, bands, sampling_rate)
            elif feature_method == "csp":
                reshaped = filtered[np.newaxis, :, :]
                features = csp.transform(reshaped)
            else:
                print(f"Unknown feature method: {feature_method}")
                continue
            # Scaling
            scaled_features = model.named_steps["scaler"].transform(features)
            # Predict probabilities
            probabilities = model.named_steps["clf"].predict_proba(scaled_features)[0]
            predicted_class_index = np.argmax(probabilities)
            prediction_label = "Right" if predicted_class_index == 1 else "Left"
            right_probability = probabilities[1]
            # Visualization bar
            right_chars = int(right_probability * bar_width)
            left_chars = bar_width - right_chars
            left_fill = "#" * left_chars
            right_fill = "#" * right_chars
            bar_str = f"[{left_fill}|{right_fill}]"
            print(f"Prediction: {prediction_label}")
            print(f"Confidence: {bar_str} (R: {right_probability:.2f})")
            # Headband status
            if horseshoe and any(h >= 3 for h in horseshoe):
                print("Warning: Poor headband contact detected!")
    except KeyboardInterrupt:
        print("Shutting down OSC server...")
    finally:
        server.shutdown()
        print("OSC server stopped.")

def extract_band_power_features(data, bands, sfreq):
    # data: (n_channels, n_times)
    # returns: (1, n_features)
    from scipy.signal import welch
    n_channels, n_times = data.shape
    features = []
    for ch in range(n_channels):
        f, Pxx = welch(data[ch], fs=sfreq, nperseg=min(256, n_times))
        for band_name, (fmin, fmax) in bands.items():
            idx = np.logical_and(f >= fmin, f <= fmax)
            band_power = np.log(np.sum(Pxx[idx]) + 1e-10)
            features.append(band_power)
    return np.array([features])

if __name__ == "__main__":
    main()