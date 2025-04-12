# Python EEG Tweaks - Motor Imagery BCI

This project explores building a simple Brain-Computer Interface (BCI) for classifying left vs. right hand motor imagery using EEG data, primarily from a Muse S headset.

## Features

*   **Data Acquisition:** Collects EEG data using the Muse S headset via the Muse Direct app and OSC protocol.
*   **Training (`motor_imagery_trainer.py`):**
    *   Guides the user through a motor imagery paradigm (left/right cues).
    *   Processes EEG data using MNE-Python (filtering, epoching).
    *   Extracts features (currently Band Power, CSP planned).
    *   Trains a classifier (currently LDA) using Scikit-learn.
    *   Saves the trained model and processing parameters.
*   **Real-time Classification (`motor_imagery_classifier.py` - Planned):**
    *   Loads a pre-trained model.
    *   Processes live EEG data from OSC stream.
    *   Predicts left/right motor imagery in near real-time.
*   **OSC Stream Check (`check_osc.py`):** A utility script to verify OSC data reception from Muse Direct.

## Setup

1.  **Hardware:**
    *   Muse S Headband
    *   Smartphone/Tablet with Muse Direct app installed.
    *   Computer (Mac/Windows/Linux) with Python 3.x and Wi-Fi.
    *   Ensure computer and phone/tablet are on the **same Wi-Fi network** for OSC.
2.  **Software:**
    *   Clone this repository.
    *   Install Python 3.x if you haven't already.
    *   It's recommended to use a virtual environment:
        ```bash
        python3 -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   Install required Python packages:
        ```bash
        pip install -r requirements.txt
        ```
3.  **Muse Direct Configuration (for OSC):**
    *   Connect Muse S to Muse Direct via Bluetooth.
    *   Find your computer's local IP address.
    *   In Muse Direct Streaming settings:
        *   Enable OSC Streaming.
        *   Set **Target IP Address** to your computer's IP.
        *   Set **Target Port** to `5001` (or match the port used in scripts).
        *   Enable streaming for `/eeg` (or `/muse/eeg`) and `/hsi` (or `/muse/elements/horseshoe`).

## Running the Scripts

### 1. Check OSC Connection (Optional but Recommended)

*   Start streaming from Muse Direct.
*   Run the checker script:
    ```bash
    python3 check_osc.py 
    ```
*   You should see OSC messages printed if the connection is working. Press Ctrl+C to stop.

### 2. Train a Model (`motor_imagery_trainer.py`)

*   Start streaming from Muse Direct.
*   Run the trainer script, providing a session name and the correct sampling rate:
    ```bash
    python3 motor_imagery_trainer.py --session-name my_first_training --sampling-rate 256
    ```
    *   Follow the on-screen prompts for the trials (Left/Right imagery).
    *   The script will save model artifacts (e.g., `training_data/my_first_training_model.joblib`).

### 3. Real-time Classification (Planned)

*   (Once `motor_imagery_classifier.py` is created)
*   Start streaming from Muse Direct.
*   Run the classifier script, pointing to your trained model:
    ```bash
    python3 motor_imagery_classifier.py --model-file training_data/my_first_training_model.joblib
    ```
*   Observe the real-time predictions.

## Documentation

*   `docs/muse_s_osc_setup_guide.md`: Guide for setting up Muse Direct and OSC.
*   `docs/motor_imagery_classifier_plan.md`: Plan for the real-time classifier script.
*   `docs/motor_imagery_mne_plan.md`: Overview plan for MNE-based processing (updated for OSC).
*   `docs/motor_imagery_detailed_plan_v3.md`: Detailed plan (updated for OSC).