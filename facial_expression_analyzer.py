#!/usr/bin/env python3
"""
Facial Expression Analyzer

This script captures video from the webcam, detects faces, and analyzes facial expressions in real-time.
It displays the video feed with facial landmarks and expression probabilities.
"""

import cv2
import numpy as np
import time
import logging
import argparse
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Import FER directly without relying on moviepy
import sys
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow logging

try:
    from fer.fer import FER
except ImportError:
    print("Error importing FER. Using alternative import method...")
    from fer import FER

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacialExpressionAnalyzer:
    """Real-time facial expression analyzer using webcam feed."""
    
    def __init__(self, camera_id=0, display_probabilities=True, display_landmarks=True):
        """
        Initialize the facial expression analyzer.
        
        Args:
            camera_id (int): Camera device ID (default: 0 for primary webcam)
            display_probabilities (bool): Whether to display emotion probabilities chart
            display_landmarks (bool): Whether to display facial landmarks
        """
        self.camera_id = camera_id
        self.display_probabilities = display_probabilities
        self.display_landmarks = display_landmarks
        self.detector = FER(mtcnn=True)  # Use MTCNN for better face detection
        self.cap = None
        self.running = False
        
        # Colors for different emotions (BGR format)
        self.emotion_colors = {
            'angry': (0, 0, 255),      # Red
            'disgust': (0, 140, 255),  # Orange
            'fear': (0, 255, 255),     # Yellow
            'happy': (0, 255, 0),      # Green
            'sad': (255, 0, 0),        # Blue
            'surprise': (255, 0, 255), # Magenta
            'neutral': (255, 255, 255) # White
        }
        
        # Window names
        self.main_window = "Facial Expression Analyzer"
        
    def start(self):
        """Start the webcam and begin processing."""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            logger.error(f"Could not open webcam (ID: {self.camera_id})")
            return False
        
        # Set resolution to 640x480 for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Create windows
        cv2.namedWindow(self.main_window, cv2.WINDOW_NORMAL)
        
        self.running = True
        logger.info("Facial expression analyzer started")
        return True
    
    def stop(self):
        """Stop the webcam and processing."""
        self.running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        logger.info("Facial expression analyzer stopped")
    
    def create_emotion_chart(self, emotions, width=200, height=400):
        """
        Create a bar chart of emotion probabilities.
        
        Args:
            emotions (dict): Dictionary of emotion probabilities
            width (int): Width of the chart in pixels
            height (int): Height of the chart in pixels
            
        Returns:
            numpy.ndarray: Image of the chart
        """
        # Create figure and axis
        fig = Figure(figsize=(4, 8), dpi=50)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        # Sort emotions by probability
        sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_emotions]
        values = [item[1] for item in sorted_emotions]
        
        # Create horizontal bar chart
        colors = [self.bgr_to_rgb(self.emotion_colors.get(emotion, (200, 200, 200))) 
                 for emotion in labels]
        
        ax.barh(labels, values, color=colors)
        ax.set_xlim(0, 1)  # Probabilities range from 0 to 1
        ax.set_title('Emotion Probabilities')
        
        # Adjust layout
        fig.tight_layout()
        
        # Convert to numpy array
        canvas.draw()
        chart_image = np.array(canvas.renderer.buffer_rgba())
        
        # Convert RGBA to BGR (OpenCV format)
        chart_image = cv2.cvtColor(chart_image, cv2.COLOR_RGBA2BGR)
        
        # Resize to desired dimensions
        chart_image = cv2.resize(chart_image, (width, height))
        
        return chart_image
    
    def bgr_to_rgb(self, bgr_color):
        """Convert BGR color tuple to RGB."""
        return (bgr_color[2]/255, bgr_color[1]/255, bgr_color[0]/255)
    
    def run(self):
        """Main processing loop."""
        if not self.start():
            return
        
        try:
            while self.running:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logger.error("Failed to capture frame from webcam")
                    break
                
                # Mirror the frame horizontally for a more natural view
                frame = cv2.flip(frame, 1)
                
                # Create a copy for display
                display_frame = frame.copy()
                
                # Detect faces and emotions
                result = self.detector.detect_emotions(frame)
                
                if result:
                    # Process each detected face
                    for face_idx, face_data in enumerate(result):
                        # Get face box
                        x, y, w, h = face_data['box']
                        
                        # Get emotions
                        emotions = face_data['emotions']
                        
                        # Find dominant emotion
                        dominant_emotion = max(emotions, key=emotions.get)
                        dominant_prob = emotions[dominant_emotion]
                        
                        # Draw face rectangle
                        color = self.emotion_colors.get(dominant_emotion, (255, 255, 255))
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                        
                        # Display emotion label
                        label = f"{dominant_emotion}: {dominant_prob:.2f}"
                        cv2.putText(display_frame, label, (x, y-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                        
                        # Log the detected emotion
                        logger.debug(f"Face {face_idx+1}: {dominant_emotion} ({dominant_prob:.2f})")
                        
                        # Create emotion probability chart
                        if self.display_probabilities:
                            chart = self.create_emotion_chart(emotions)
                            
                            # Calculate position for the chart (right side of the frame)
                            chart_x = display_frame.shape[1] - chart.shape[1] - 10
                            chart_y = 10
                            
                            # Create a region of interest
                            roi = display_frame[chart_y:chart_y+chart.shape[0], 
                                               chart_x:chart_x+chart.shape[1]]
                            
                            # Create a mask for transparent overlay
                            mask = np.ones(chart.shape, dtype=np.float32) * 0.7
                            
                            # Overlay the chart
                            cv2.addWeighted(chart, 0.7, roi, 0.3, 0, roi)
                
                # Add instructions
                cv2.putText(display_frame, "Press 'q' to quit", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Display the frame
                cv2.imshow(self.main_window, display_frame)
                
                # Check for key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("User requested to quit")
                    break
                
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
        
        finally:
            self.stop()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Facial Expression Analyzer')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera device ID (default: 0)')
    parser.add_argument('--no-chart', action='store_true',
                        help='Disable emotion probability chart')
    parser.add_argument('--no-landmarks', action='store_true',
                        help='Disable facial landmarks display')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the analyzer
    analyzer = FacialExpressionAnalyzer(
        camera_id=args.camera,
        display_probabilities=not args.no_chart,
        display_landmarks=not args.no_landmarks
    )
    
    analyzer.run()

if __name__ == "__main__":
    main()
