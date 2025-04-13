import cv2
import threading
import logging
from moviepy.editor import *
from moviepy.editor import *
from fer import FER
# Shared variable for storing the current expression
current_expression = "Neutral"
expression_lock = threading.Lock()
import collections
# Expression history
expression_history = collections.deque(maxlen=5) # Store last 5 expressions
persistent_expression = "Neutral" # The confirmed expression


import threading
cv_running = False
cv_started_event = threading.Event()
def start_cv_processing():
    """Starts the computer vision processing in a separate thread."""
    cv_thread = threading.Thread(target=_cv_loop, daemon=True, name="CVThread")
    cv_thread.start()
    logging.info("Computer vision processing started in background.")
    cv_running = True

import json

def get_current_expression():
    """Returns the current detected facial expression probabilities."""
    with expression_lock:
        return current_expression

def _cv_loop():
    """Main loop for computer vision processing."""
    global current_expression, persistent_expression
    logging.info("Starting computer vision loop...")
    video_capture = None  # Initialize to None for proper cleanup
    try:
        detector = FER()
        video_capture = cv2.VideoCapture(0)  # Use default webcam

        if not video_capture.isOpened():
            logging.error("Could not open webcam")
            return

        while True:
            ret, frame = video_capture.read()
            if not ret:
                logging.error("Could not read frame from webcam")
                break

            # Analyze facial expressions
            try:
                result = detector.detect_emotions(frame)
                if result:
                    # Get emotion probabilities
                    emotions = result[0]['emotions']
                    with expression_lock:
                        current_expression = emotions
                    # Find dominant emotion for logging
                    dominant_emotion = max(emotions, key=emotions.get)
                    expression_history.append(dominant_emotion)
                    if len(expression_history) == expression_history.maxlen and all(x == expression_history[0] for x in expression_history):
                        with expression_lock:
                            persistent_expression = expression_history[0] # Keep track of persistent expression
                    logging.info(f"Detected expression: {dominant_emotion}, Persistent Expression: {persistent_expression}")
                else:
                    logging.info("No face detected")
                    with expression_lock:
                        current_expression = "No Face"
                        persistent_expression = "No Face"
            except Exception as e:
                logging.error(f"Error processing frame: {e}")

    except Exception as e:
        logging.error(f"Error initializing computer vision: {e}")

    finally:
        if video_capture is not None and video_capture.isOpened():
            video_capture.release()
        logging.info("Computer vision loop stopped.")

if __name__ == '__main__':
    # Basic test - just start the CV loop and print expressions
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    start_cv_processing()
    try:
        while True:
            print(f"Current Expression: {get_current_expression()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping CV processing.")