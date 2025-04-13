import numpy as np
import logging
import collections # Needed for type hinting if used

from . import config

def update_stress_state(current_ratio, current_hr, baseline_metrics, current_state, tentative_state_history: collections.deque):
    """
    Determines the tentative stress state based on current features and baseline metrics,
    and applies persistence logic to update the official current_state.

    Args:
        current_ratio (float): The latest calculated Alpha/Beta ratio.
        current_hr (float): The latest calculated Heart Rate (BPM).
        baseline_metrics (dict): Dictionary containing 'ratio_median', 'ratio_std',
                                 'hr_median', 'hr_std'.
        current_state (str): The current official state before this update.
        tentative_state_history (collections.deque): A deque (managed by the caller)
                                                     storing recent tentative states.

    Returns:
        str: The potentially updated current_state after applying persistence.
    """
    new_state = current_state # Default to current state unless persistence logic changes it

    # 1. Determine Tentative State
    if np.isnan(current_ratio) or np.isnan(current_hr):
        # logging.warning("Cannot determine state due to NaN feature value.") # Logged by caller
        tentative_state = "Uncertain (NaN)"
    elif not baseline_metrics or 'ratio_median' not in baseline_metrics or 'hr_median' not in baseline_metrics:
        logging.warning("Baseline metrics not available, cannot determine state.")
        tentative_state = "Initializing" # Should only happen briefly at start
    else:
        # Use thresholds from config
        ratio_lower_bound = baseline_metrics['ratio_median'] - config.RATIO_THRESHOLD * baseline_metrics['ratio_std']
        hr_upper_bound = baseline_metrics['hr_median'] + config.HR_THRESHOLD * baseline_metrics['hr_std']

        is_ratio_low = current_ratio < ratio_lower_bound
        is_hr_high = current_hr > hr_upper_bound

        # --- Phase 1 Logic ---
        # TODO: Incorporate ACC and CV data here based on Phase 2 plan
        if is_ratio_low and is_hr_high:
            tentative_state = "Stress"
        elif is_ratio_low or is_hr_high:
            tentative_state = "Warning"
        else:
            tentative_state = "Calm"
        # --- End Phase 1 Logic ---

    # 2. Apply Persistence Logic
    tentative_state_history.append(tentative_state) # Add current tentative state

    # Check if history is full (length equals persistence requirement)
    if len(tentative_state_history) == config.STATE_PERSISTENCE_UPDATES:
        first_state_in_history = tentative_state_history[0]

        # Check if all states in the history window are the same
        is_persistent = all(s == first_state_in_history for s in tentative_state_history)

        # Only update the official state if it's persistent AND different from the current state
        if is_persistent and new_state != first_state_in_history:
            logging.info(f"STATE CHANGE: {new_state} -> {first_state_in_history}")
            new_state = first_state_in_history # Update the official state

    # Note: The 'Uncertain (Stale Data)' state is typically set by the processing loop
    # *before* calling this function if data timestamps are too old.
    # Persistence for it could be handled here if needed, but usually not necessary.

    return new_state

if __name__ == '__main__':
    # Example Usage / Test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Dummy baseline
    baseline = {'ratio_median': 1.5, 'ratio_std': 0.2, 'hr_median': 65, 'hr_std': 5}
    # Dummy history deque (caller manages this)
    history = collections.deque(maxlen=config.STATE_PERSISTENCE_UPDATES)
    state = "Initializing"

    print(f"Initial State: {state}, History: {list(history)}")

    # Simulate updates
    inputs = [
        (1.6, 66), # Calm
        (1.7, 64), # Calm
        (1.55, 67), # Calm
        (1.0, 80), # Stress
        (0.9, 82), # Stress
        (1.1, 78), # Stress -> Should trigger change
        (1.2, 75), # Warning
        (1.6, 65), # Calm
        (1.7, 63), # Calm
        (1.5, 66), # Calm
        (1.6, 64), # Calm
        (1.55, 65), # Calm -> Should trigger change
    ]

    for ratio, hr in inputs:
        state = update_stress_state(ratio, hr, baseline, state, history)
        print(f"Input (R:{ratio:.1f}, HR:{hr:.0f}) -> Tentative: {history[-1]:<15} | Official State: {state:<15} | History: {list(history)}")