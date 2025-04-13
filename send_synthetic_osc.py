import argparse
import time
import random
import numpy as np
from pythonosc import udp_client

def generate_eeg(num_channels, sampling_rate):
    """Generates synthetic EEG data (random noise with some sinusoidal components)."""
    data = np.random.normal(0, 5, size=(num_channels, sampling_rate))  # Noise with a range of -5 to 5
    # Add some low-frequency sinusoidal components to mimic brainwaves
    for i in range(num_channels):
        freq = random.uniform(1, 10)  # Random frequency between 1 and 10 Hz
        t = np.linspace(0, 1, sampling_rate, endpoint=False)
        data[i, :] += 2 * np.sin(2 * np.pi * freq * t)  # Amplitude of 2
    return data.tolist()

def generate_ppg(sampling_rate, avg_hr=60):
    """Generates synthetic PPG data (sine wave with noise, simulating heartbeats)."""
    freq = avg_hr / 60.0  # Heart rate in Hz
    t = np.linspace(0, 1, sampling_rate, endpoint=False)
    ppg_signal = 10 * np.sin(2 * np.pi * freq * t)  # Amplitude of 10
    ppg_signal += np.random.normal(0, 2, size=sampling_rate)  # Add noise
    sensor_id = random.randint(1, 3)  # Simulate a sensor ID
    return [sensor_id, ppg_signal.mean(), sensor_id]  # Return sensor_id, value, sensor_id

def generate_acc(sampling_rate):
    """Generates synthetic accelerometer data (random noise around a baseline)."""
    x = np.random.normal(0, 0.5, size=sampling_rate)  # Noise around 0
    y = np.random.normal(0, 0.5, size=sampling_rate)  # Noise around 0
    z = np.random.normal(9.8, 0.5, size=sampling_rate)  # Noise around gravity (9.8 m/s^2)
    # Simulate occasional movement
    if random.random() < 0.1:
        x += random.uniform(-2, 2)
        y += random.uniform(-2, 2)
        z += random.uniform(-2, 2)
    return [x.mean(), y.mean(), z.mean()]

def main():
    parser = argparse.ArgumentParser(description="Send synthetic OSC data for BrainTrade stress monitor.")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="The ip address to send to")
    parser.add_argument("--port", type=int, default=5001, help="The port to send to")
    args = parser.parse_args()

    client = udp_client.SimpleUDPClient(args.ip, args.port)

    # Target frequencies (Hz)
    eeg_freq = 256
    ppg_freq = 64
    acc_freq = 50

    # Number of EEG channels
    num_eeg_channels = 4

    # Time tracking for each stream
    eeg_last_sent = 0
    ppg_last_sent = 0
    acc_last_sent = 0

    try:
        while True:
            current_time = time.time()

            # Send EEG data
            if current_time - eeg_last_sent >= 1.0 / eeg_freq:
                eeg_data = generate_eeg(num_eeg_channels, eeg_freq)
                client.send_message("/eeg", eeg_data)
                eeg_last_sent = current_time

            # Send PPG data
            if current_time - ppg_last_sent >= 1.0 / ppg_freq:
                ppg_data = generate_ppg(ppg_freq)
                client.send_message("/ppg", ppg_data)
                ppg_last_sent = current_time

            # Send ACC data
            if current_time - acc_last_sent >= 1.0 / acc_freq:
                acc_data = generate_acc(acc_freq)
                client.send_message("/acc", acc_data)
                acc_last_sent = current_time

            time.sleep(0.001)  # Small sleep to prevent busy-waiting

    except KeyboardInterrupt:
        print("Exiting synthetic data sender.")

if __name__ == "__main__":
    main()