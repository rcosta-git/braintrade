# Facial Expression Analyzer

This project contains scripts for real-time facial expression analysis using a webcam. The scripts detect faces and analyze facial expressions, displaying the results in a live video feed.

## Scripts

### 1. facial_expression_analyzer.py

The original implementation that uses the FER (Facial Expression Recognition) library. This script may require additional dependencies and permissions.

**Note:** This script has dependency issues with the `moviepy.editor` module and may not work without additional configuration.

### 2. facial_expression_analyzer_simple.py

A simplified version that uses OpenCV's Haar Cascade classifier for face detection. This script only detects faces without analyzing expressions.

**Features:**
- Face detection using OpenCV's Haar Cascade classifier
- Real-time video feed with face rectangles
- FPS counter
- Simple user interface

### 3. facial_expression_analyzer_advanced.py (Recommended)

An advanced implementation that uses OpenCV for face detection and a simple heuristic-based approach for emotion classification.

**Features:**
- Face detection using OpenCV's Haar Cascade classifier
- Basic emotion classification (Happy, Sad, Angry, Surprise, Neutral)
- Color-coded face rectangles based on detected emotion
- Real-time video feed with emotion labels
- FPS counter
- Screenshot capability (press 's' to save)
- Clear user interface with instructions

## Requirements

- Python 3.6+
- OpenCV (`opencv-python`)
- NumPy
- Matplotlib (for visualization)

## Installation

1. Ensure you have Python installed
2. Install the required packages:

```bash
pip install opencv-python numpy matplotlib
```

## Usage

### Running the Advanced Analyzer

```bash
python facial_expression_analyzer_advanced.py
```

### Command-line Options

```
--camera INT       Camera device ID (default: 0)
--confidence FLOAT Confidence threshold for face detection (0.0-1.0)
--debug            Enable debug logging
```

### Controls

- Press 'q' to quit the application
- Press 's' to save a screenshot (advanced version only)

## Webcam Permissions

These scripts require webcam access. On macOS, you may need to grant permission in:
System Preferences > Security & Privacy > Privacy > Camera

## How It Works

### Face Detection

The scripts use OpenCV's Haar Cascade classifier to detect faces in the video feed. This is a machine learning-based approach that uses a cascade of simple features to identify faces.

### Emotion Classification (Advanced Version)

The advanced version uses a simple heuristic-based approach to classify emotions based on pixel intensity in different regions of the face (eyes, mouth, forehead). This is a simplified demonstration and not a production-ready emotion classifier.

In a real-world application, you would use a trained deep learning model for more accurate emotion classification.

## Screenshots

Screenshots are saved in the current directory with filenames like `facial_expression_20250413_093849.jpg` (timestamp format).

## Limitations

- The emotion classification in the advanced version is based on simple heuristics and is not highly accurate
- Face detection may struggle in poor lighting conditions or with unusual face angles
- The scripts require a webcam with proper permissions

## Future Improvements

- Implement a proper deep learning-based emotion classifier
- Add facial landmark detection for more detailed analysis
- Improve the UI with more detailed emotion metrics
- Add recording capability for saving video
- Implement eye blink detection and attention monitoring
