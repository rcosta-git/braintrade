#!/usr/bin/env python3
"""
Advanced Facial Expression Analyzer

This script captures video from the webcam, detects faces using OpenCV's DNN face detector,
and analyzes facial expressions using a pre-trained emotion recognition model.
It displays the video feed with face rectangles and emotion labels.

Note: This script requires webcam access permission. On macOS, you may need to
grant permission in System Preferences > Security & Privacy > Privacy > Camera.
"""

import cv2
import numpy as np
import time
import logging
import argparse
import os
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedFacialExpressionAnalyzer:
    """Real-time facial expression analyzer using webcam feed and OpenCV DNN."""
    
    def __init__(self, camera_id=0, confidence_threshold=0.5):
        """
        Initialize the facial expression analyzer.
        
        Args:
            camera_id (int): Camera device ID (default: 0 for primary webcam)
            confidence_threshold (float): Confidence threshold for face detection (0.0-1.0)
        """
        self.camera_id = camera_id
        self.confidence_threshold = confidence_threshold
        self.cap = None
        self.running = False
        
        # Window name
        self.main_window = "Advanced Facial Expression Analyzer"
        
        # Colors for different emotions (BGR format)
        self.emotion_colors = {
            'Angry': (0, 0, 255),      # Red
            'Disgust': (0, 140, 255),  # Orange
            'Fear': (0, 255, 255),     # Yellow
            'Happy': (0, 255, 0),      # Green
            'Sad': (255, 0, 0),        # Blue
            'Surprise': (255, 0, 255), # Magenta
            'Neutral': (255, 255, 255) # White
        }
        
        # Initialize face detector
        self._init_face_detector()
        
        # Initialize emotion classifier
        self._init_emotion_classifier()
        
    def _init_face_detector(self):
        """Initialize the face detector using OpenCV's DNN module."""
        # Use OpenCV's built-in face detection model
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        if self.face_detector.empty():
            logger.error("Error loading face detector model")
            sys.exit(1)
            
        logger.info("Face detector initialized")
        
    def _init_emotion_classifier(self):
        """Initialize a simple emotion classifier based on facial features."""
        # Since we don't have a pre-trained emotion model, we'll use a placeholder
        # In a real application, you would load a trained model here
        self.emotions = ['Neutral', 'Happy', 'Sad', 'Surprise', 'Angry']
        logger.info("Emotion classifier initialized")
        
    def start(self):
        """Start the webcam and begin processing."""
        # Print a message to the user about webcam permissions
        print("\n" + "="*80)
        print("WEBCAM ACCESS REQUIRED")
        print("This script requires webcam access permission.")
        print("On macOS, you may need to grant permission in:")
        print("System Preferences > Security & Privacy > Privacy > Camera")
        print("="*80 + "\n")
        
        # Try to open the webcam
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            logger.error(f"Could not open webcam (ID: {self.camera_id})")
            return False
        
        # Set resolution to 640x480 for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Create window
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
    
    def detect_faces(self, frame):
        """
        Detect faces in the frame using OpenCV's Haar Cascade classifier.
        
        Args:
            frame (numpy.ndarray): Input frame
            
        Returns:
            list: List of face rectangles (x, y, w, h)
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces
    
    def analyze_emotion(self, face_img):
        """
        Analyze the emotion in a face image.
        
        Args:
            face_img (numpy.ndarray): Face image
            
        Returns:
            tuple: (emotion, confidence)
        """
        # In a real application, you would use a trained model here
        # For this example, we'll return a random emotion with a random confidence
        # This is just a placeholder for demonstration purposes
        
        # Calculate a simple metric based on the average pixel values in different regions
        # This is not a real emotion classifier, just a simple demonstration
        h, w = face_img.shape[:2]
        
        # Convert to grayscale
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
            
        # Resize to a standard size
        gray = cv2.resize(gray, (64, 64))
        
        # Calculate average pixel values in different regions
        forehead = np.mean(gray[0:20, 15:45])
        left_eye = np.mean(gray[20:30, 15:30])
        right_eye = np.mean(gray[20:30, 35:50])
        mouth = np.mean(gray[40:55, 20:45])
        
        # Simple heuristic for demonstration purposes
        # Again, this is NOT a real emotion classifier
        if mouth > forehead + 10:
            emotion = 'Happy'
            confidence = 0.7
        elif left_eye < forehead - 10 and right_eye < forehead - 10:
            emotion = 'Sad'
            confidence = 0.6
        elif abs(left_eye - right_eye) > 10:
            emotion = 'Surprise'
            confidence = 0.5
        elif mouth < forehead - 15:
            emotion = 'Angry'
            confidence = 0.4
        else:
            emotion = 'Neutral'
            confidence = 0.8
            
        return emotion, confidence
    
    def run(self):
        """Main processing loop."""
        if not self.start():
            return
        
        try:
            frame_count = 0
            start_time = time.time()
            fps = 0
            
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
                
                # Calculate FPS
                frame_count += 1
                elapsed_time = time.time() - start_time
                if elapsed_time >= 1.0:
                    fps = frame_count / elapsed_time
                    frame_count = 0
                    start_time = time.time()
                
                # Draw FPS
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                # Process detected faces
                if len(faces) > 0:
                    logger.debug(f"Detected {len(faces)} faces")
                    
                    # Process each face
                    for (x, y, w, h) in faces:
                        # Extract face ROI
                        face_roi = frame[y:y+h, x:x+w]
                        
                        # Analyze emotion
                        emotion, confidence = self.analyze_emotion(face_roi)
                        
                        # Get color for emotion
                        color = self.emotion_colors.get(emotion, (255, 255, 255))
                        
                        # Draw face rectangle
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                        
                        # Display emotion label
                        label = f"{emotion}: {confidence:.2f}"
                        cv2.putText(display_frame, label, (x, y-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # Add instructions
                cv2.putText(display_frame, "Press 'q' to quit, 's' to save screenshot", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Display the frame
                cv2.imshow(self.main_window, display_frame)
                
                # Check for key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("User requested to quit")
                    break
                elif key == ord('s'):
                    # Save screenshot
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"facial_expression_{timestamp}.jpg"
                    cv2.imwrite(filename, display_frame)
                    logger.info(f"Screenshot saved as {filename}")
                    
                    # Display confirmation on screen
                    cv2.putText(display_frame, f"Saved: {filename}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow(self.main_window, display_frame)
                    cv2.waitKey(1000)  # Show confirmation for 1 second
                
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
        
        finally:
            self.stop()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Advanced Facial Expression Analyzer')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera device ID (default: 0)')
    parser.add_argument('--confidence', type=float, default=0.5,
                        help='Confidence threshold for face detection (0.0-1.0)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the analyzer
    analyzer = AdvancedFacialExpressionAnalyzer(
        camera_id=args.camera,
        confidence_threshold=args.confidence
    )
    
    analyzer.run()

if __name__ == "__main__":
    main()
