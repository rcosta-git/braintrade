#!/usr/bin/env python3
"""
Simple Facial Expression Analyzer

This script captures video from the webcam, detects faces using OpenCV's Haar Cascade classifier,
and displays the video feed with face rectangles.
"""

import cv2
import numpy as np
import time
import logging
import argparse
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleFacialAnalyzer:
    """Real-time facial analyzer using webcam feed and OpenCV."""
    
    def __init__(self, camera_id=0):
        """
        Initialize the facial analyzer.
        
        Args:
            camera_id (int): Camera device ID (default: 0 for primary webcam)
        """
        self.camera_id = camera_id
        self.cap = None
        self.running = False
        
        # Load the face cascade classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Window name
        self.main_window = "Simple Facial Analyzer"
        
        # Face detection parameters
        self.min_neighbors = 5
        self.scale_factor = 1.1
        self.min_size = (30, 30)
        
        # Colors
        self.face_color = (0, 255, 0)  # Green
        self.text_color = (255, 255, 255)  # White
        
    def start(self):
        """Start the webcam and begin processing."""
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
        logger.info("Facial analyzer started")
        return True
    
    def stop(self):
        """Stop the webcam and processing."""
        self.running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        logger.info("Facial analyzer stopped")
    
    def detect_faces(self, frame):
        """
        Detect faces in the frame.
        
        Args:
            frame (numpy.ndarray): Input frame
            
        Returns:
            list: List of face rectangles (x, y, w, h)
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size
        )
        
        return faces
    
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
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                # Calculate FPS
                frame_count += 1
                elapsed_time = time.time() - start_time
                if elapsed_time >= 1.0:
                    fps = frame_count / elapsed_time
                    frame_count = 0
                    start_time = time.time()
                
                # Draw FPS
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.text_color, 2)
                
                # Process detected faces
                if len(faces) > 0:
                    logger.debug(f"Detected {len(faces)} faces")
                    
                    # Draw rectangles around faces
                    for (x, y, w, h) in faces:
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), self.face_color, 2)
                        
                        # Add face label
                        cv2.putText(display_frame, "Face", (x, y-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.face_color, 2)
                
                # Add instructions
                cv2.putText(display_frame, "Press 'q' to quit", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.text_color, 2)
                
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
    parser = argparse.ArgumentParser(description='Simple Facial Analyzer')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera device ID (default: 0)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the analyzer
    analyzer = SimpleFacialAnalyzer(camera_id=args.camera)
    analyzer.run()

if __name__ == "__main__":
    main()
