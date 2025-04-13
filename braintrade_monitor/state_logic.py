import numpy as np
import logging
import collections # Needed for type hinting if used

from . import config

def update_stress_state(current_ratio, current_hr, current_expression, current_movement, current_theta, baseline_metrics, current_state, tentative_state_history: collections.deque):
    """
    Determines the tentative stress state based on current features and baseline metrics,
    and applies persistence logic to update the official current_state.

    Args:
        current_ratio (float): The latest calculated Alpha/Beta ratio.
        current_hr (float): The latest calculated Heart Rate (BPM).
        current_expression (str): The latest detected facial expression.
        current_movement (float): The latest calculated movement metric.
        current_theta (float): The latest calculated Theta power.
        baseline_metrics (dict): Dictionary containing 'ratio_median', 'ratio_std', 'hr_median', 'hr_std', 'theta_median', 'theta_std'.
        current_state (str): The current official state before this update.
        tentative_state_history (collections.deque): A deque (managed by the caller)
                                                     storing recent tentative states.

    Returns:
        str: The potentially updated current_state after applying persistence.
    """
    logging.debug(f"update_stress_state: ratio={current_ratio}, hr={current_hr}, theta={current_theta}, movement={current_movement}, expression={current_expression}, baseline={baseline_metrics}")
    new_state = current_state # Default to current state unless persistence logic changes it

    # 1. Determine Tentative State
    if np.isnan(current_ratio) or np.isnan(current_hr) or current_expression == "N/A" or np.isnan(current_movement) or np.isnan(current_theta):
        # logging.warning("Cannot determine state due to NaN feature value.") # Logged by caller
        tentative_state = "Uncertain (NaN)"
    elif not baseline_metrics or 'ratio_median' not in baseline_metrics or 'hr_median' not in baseline_metrics or 'theta_median' not in baseline_metrics:
        logging.warning("Baseline metrics not available, cannot determine state.")
        tentative_state = "Initializing" # Should only happen briefly at start
    else:
        # Use thresholds from config
        ratio_lower_bound = baseline_metrics['ratio_median'] - config.RATIO_THRESHOLD * baseline_metrics['ratio_std']
        hr_upper_bound = baseline_metrics['hr_median'] + config.HR_THRESHOLD * baseline_metrics['hr_std']
        movement_upper_bound = baseline_metrics['movement_median'] + config.MOVEMENT_THRESHOLD * baseline_metrics['movement_std']

        is_ratio_low = current_ratio < ratio_lower_bound if not np.isnan(current_ratio) else False
        is_hr_high = current_hr > hr_upper_bound if not np.isnan(current_hr) else False
        is_movement_high = current_movement > movement_upper_bound  if not np.isnan(current_movement) else False
        # Calculate weighted expression score
        expression_weights = {"Angry": 0.8, "Sad": 0.6, "Fear": 0.7, "Happy": -0.1, "Neutral": 0.0, "Surprise": 0.3}
        weighted_expression_score = 0
        if isinstance(current_expression, dict):
            for expression, probability in current_expression.items():
                weight = expression_weights.get(expression, 0)  # Default to 0 if expression not found
                weighted_expression_score += probability * weight

        EXPRESSION_STRESS_THRESHOLD = 0.3 # Tune this
        is_expression_stressed = weighted_expression_score > EXPRESSION_STRESS_THRESHOLD
        is_expression_neutral = current_expression == "Neutral"
        is_physio_calm = not is_ratio_low and not is_hr_high
        is_movement_low = current_movement < movement_upper_bound if not np.isnan(current_movement) else False
        theta_upper_bound = baseline_metrics['theta_median'] + config.THETA_THRESHOLD * baseline_metrics['theta_std']
        is_theta_high = current_theta > theta_upper_bound if not np.isnan(current_theta) else False

        logging.debug(f"update_stress_state: is_ratio_low={is_ratio_low}, is_hr_high={is_hr_high}, is_movement_high={is_movement_high}, is_theta_high={is_theta_high}, expression={current_expression}")
        # --- Phase 3 Logic ---
        # Order: Drowsy/Distracted -> Stress -> Warning -> Calm -> Other
        if is_theta_high and is_movement_low:
            tentative_state = "Drowsy/Distracted"
        elif (is_ratio_low and is_hr_high) or (is_expression_stressed and (is_hr_high or is_movement_high)):
            tentative_state = "Stress/Tilted"
        elif is_ratio_low or is_hr_high: # Check for Warning state if not Stress
             tentative_state = "Warning"
        elif is_physio_calm and is_movement_low and weighted_expression_score <= 0.0: # Relaxed Calm condition
            tentative_state = "Calm/Focused"
        else: # Default to Other/Uncertain if none of the above match
            tentative_state = "Other/Uncertain"
        # --- End Phase 3 Logic ---
        # --- End Phase 2 Logic ---


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
    baseline = {'ratio_median': 1.5, 'ratio_std': 0.2, 'hr_median': 65, 'hr_std': 5, 'movement_median': 1.0, 'movement_std': 0.1}
    # Dummy history deque (caller manages this)
    history = collections.deque(maxlen=config.STATE_PERSISTENCE_UPDATES)
    state = "Initializing"

    print(f"Initial State: {state}, History: {list(history)}")

    # Simulate updates
    inputs = [
        (1.6, 66, {"Neutral": 0.8, "Happy": 0.2}, 0.5), # Calm
        (1.7, 64, {"Neutral": 0.9, "Happy": 0.1}, 0.6), # Calm
        (1.55, 67, {"Neutral": 0.7, "Happy": 0.3}, 0.4), # Calm
        (1.0, 80, {"Angry": 0.6, "Fear": 0.4}, 1.5), # Stress
        (0.9, 82, {"Angry": 0.7, "Fear": 0.3}, 1.6), # Stress
        (1.1, 78, {"Angry": 0.5, "Fear": 0.5}, 1.4), # Stress -> Should trigger change
        (1.2, 75, {"Surprise": 0.6, "Neutral": 0.4}, 1.2), # Warning
        (1.6, 65, {"Neutral": 0.8, "Happy": 0.2}, 0.5), # Calm
        (1.7, 63, {"Neutral": 0.9, "Happy": 0.1}, 0.6), # Calm
        (1.5, 66, {"Neutral": 0.7, "Happy": 0.3}, 0.4), # Calm
        (1.6, 64, {"Neutral": 0.8, "Happy": 0.2}, 0.5), # Calm
        (1.55, 65, {"Neutral": 0.9, "Happy": 0.1}, 0.6), # Calm -> Should trigger change
    ]

    for ratio, hr, expression, movement in inputs:
        state = update_stress_state(ratio, hr, expression, movement, 0.0, baseline, state, history)
        print(f"Input (R:{ratio:.1f}, HR:{hr:.0f}, E:{expression}, M:{movement:.1f}) -> Tentative: {history[-1]:<15} | Official State: {state:<15} | History: {list(history)}")