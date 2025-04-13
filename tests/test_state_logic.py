import unittest
import numpy as np
import collections
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from braintrade_monitor import state_logic, config

class TestStateLogic(unittest.TestCase):

    def setUp(self):
        """Set up common test fixtures."""
        # Use config for thresholds, but define a clear baseline for tests
        self.baseline_metrics = {
            'ratio_median': 1.5, 'ratio_std': 0.2, # Lower threshold = 1.5 - 1.5*0.2 = 1.2
            'hr_median': 70, 'hr_std': 5,          # Upper threshold = 70 + 1.5*5 = 77.5
            'movement_median': 1.0, 'movement_std': 0.1,
            'theta_median': 0.5, 'theta_std': 0.1 # Added for Phase 3
        }
        # Persistence window size from config
        self.persistence = config.STATE_PERSISTENCE_UPDATES
        self.history = collections.deque(maxlen=self.persistence)
        self.current_state = "Initializing"

    def _run_updates(self, inputs):
        """Helper to run multiple updates and return the final state."""
        final_state = self.current_state
        for ratio, hr, expression in inputs:
            final_state = state_logic.update_stress_state(ratio, hr, expression, 0.0, 0.0, self.baseline_metrics, final_state, self.history)
            self.current_state = final_state
        return final_state
    def test_initial_state_calm(self):
        """Test correct tentative state for calm inputs."""
        # Ratio > 1.2, HR < 77.5
        state = self._run_updates([(1.6, 70, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Calm/Focused") # Corrected expectation based on updated logic
        # State shouldn't change yet due to persistence
        self.assertEqual(state, "Initializing")

    def test_initial_state_warning_ratio(self):
        """Test correct tentative state for warning (low ratio)."""
        # Ratio < 1.2, HR < 77.5
        state = self._run_updates([(1.1, 70, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Warning")
        self.assertEqual(state, "Initializing")

    def test_initial_state_warning_hr(self):
        """Test correct tentative state for warning (high HR)."""
        # Ratio > 1.2, HR > 77.5
        state = self._run_updates([(1.6, 80, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Warning")
        self.assertEqual(state, "Initializing")

    def test_initial_state_stress(self):
        """Test correct tentative state for stress inputs."""
        # Ratio < 1.2, HR > 77.5
        state = self._run_updates([(1.1, 80, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Stress/Tilted") # Corrected expectation for stress condition
        self.assertEqual(state, "Initializing")

    def test_state_nan_input(self):
        """Test handling of NaN input."""
        state = self._run_updates([(np.nan, 70, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Uncertain (NaN)")
        state = self._run_updates([(1.5, np.nan, {"Neutral": 1.0})])
        self.assertEqual(self.history[-1], "Uncertain (NaN)")
        self.assertEqual(state, "Initializing") # State shouldn't change yet

    def test_state_missing_baseline(self):
        """Test handling of missing baseline metrics."""
        state = state_logic.update_stress_state(1.5, 70, "Neutral", 0.0, 0.0, {}, self.current_state, self.history)
        self.assertEqual(self.history[-1], "Initializing")
        self.assertEqual(state, "Initializing")

    def test_persistence_change_to_calm(self):
        """Test state change to Calm after persistent tentative states."""
        self.current_state = "Warning"
        inputs = [(1.6, 70, {"Neutral": 1.0})] * self.persistence # Calm inputs
        final_state = self._run_updates(inputs)
        self.assertEqual(final_state, "Calm/Focused")

    def test_persistence_change_to_warning(self):
        """Test state change to Warning after persistent tentative states."""
        self.current_state = "Calm"
        inputs = [(1.1, 70, {"Neutral": 1.0})] * self.persistence # Warning (low ratio) inputs
        final_state = self._run_updates(inputs)
        self.assertEqual(final_state, "Warning")

    def test_persistence_change_to_stress(self):
        """Test state change to Stress after persistent tentative states."""
        self.current_state = "Calm"
        inputs = [(1.1, 80, {"Neutral": 1.0})] * self.persistence # Stress inputs
        final_state = self._run_updates(inputs)
        self.assertEqual(final_state, "Stress/Tilted")

    def test_persistence_no_change_mixed_states(self):
        """Test state does not change with mixed tentative states in history."""
        self.current_state = "Calm"
        inputs = [(1.6, 70, {"Neutral": 1.0})] * (self.persistence // 2) + \
                 [(1.1, 80, {"Neutral": 1.0})] * (self.persistence - self.persistence // 2) # Mix of Calm and Stress
        final_state = self._run_updates(inputs)
        # State should remain Calm because the history wasn't consistently Stress
        self.assertEqual(final_state, "Calm")
        self.assertEqual(self.history[-1], "Stress/Tilted")

    def test_persistence_change_to_uncertain_nan(self):
        """Test state change to Uncertain (NaN) after persistent NaN inputs."""
        self.current_state = "Calm"
        inputs = [(np.nan, np.nan, {})] * self.persistence
        final_state = self._run_updates(inputs)
        self.assertEqual(final_state, "Uncertain (NaN)")

if __name__ == '__main__':
    unittest.main()
