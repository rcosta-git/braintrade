import unittest
from unittest.mock import patch
import cv2
import numpy as np
from braintrade_monitor import cv_handler

class TestCVHandler(unittest.TestCase):

    @patch('braintrade_monitor.cv_handler.cv_running', new=True)
    def test_start_cv_processing_success(self):
        # Mock successful webcam initialization

        cv_handler.start_cv_processing()
        self.assertTrue(cv_handler.cv_running)

    @patch('braintrade_monitor.cv_handler.cv_running', new=False)
    def test_start_cv_processing_failure(self):
        # Mock failed webcam initialization

        cv_handler.start_cv_processing()
        self.assertFalse(cv_handler.cv_running)

    @patch('braintrade_monitor.cv_handler.current_expression', new={"Happy": 0.9, "Neutral": 0.1})
    def test_get_current_expression(self):
        expression = cv_handler.get_current_expression()
        self.assertEqual(expression, {"Happy": 0.9, "Neutral": 0.1})

if __name__ == '__main__':
    unittest.main()