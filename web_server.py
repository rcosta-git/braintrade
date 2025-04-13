import threading
import time
import logging
from typing import Dict, Any

# Basic logging setup (can be overridden by main logger)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API Endpoint Function ---
# This function will be imported and used by main.py to define the route.
# It expects the shared dictionary and lock to be passed to it.
async def get_state(
    shared_dict_obj: Dict[str, Any],
    shared_lock_obj: threading.Lock # Can accept multiprocessing.Lock too
):
    """
    Endpoint logic to get the latest state data from the shared dictionary.
    """
    logging.debug("API endpoint /api/state called.")
    with shared_lock_obj:
        # Create a copy to avoid issues if the state is updated while reading
        current_data = shared_dict_obj.copy()

    # --- Data Mapping ---
    # Convert Python timestamp (seconds) to JS timestamp (milliseconds)
    last_osc_ts_ms = None
    last_osc_ts_py = current_data.get("last_osc_timestamp")
    if last_osc_ts_py is not None:
        try:
            last_osc_ts_ms = int(last_osc_ts_py * 1000)
        except (ValueError, TypeError):
            logging.warning(f"Could not convert last_osc_timestamp '{last_osc_ts_py}' to milliseconds.")

    frontend_data = {
        "emotionalState": current_data.get("overall_state", "neutral").lower(),
        "heartRate": current_data.get("heart_rate"),
        "brainwaveState": "alpha", # Placeholder
        "accelerometer": {"x": 0, "y": 0, "z": current_data.get("movement_metric", 0)}, # Placeholder
        "timestamp": current_data.get("timestamp"), # Keep original timestamp if needed elsewhere
        "alpha_beta_ratio": current_data.get("alpha_beta_ratio"),
        "theta_power": current_data.get("theta_power"),
        "expression": current_data.get("expression_dict"),
        "systemPhase": current_data.get("system_phase", "Unknown"),
        "last_osc_timestamp": last_osc_ts_ms, # Send milliseconds
        "suggestedPosition": current_data.get("suggested_position"),
        "confidenceLevel": current_data.get("confidence_level"),
        "market_trend": current_data.get("market_trend")
    }
    # --- End Data Mapping ---

    logging.debug(f"API returning data: {frontend_data}")
    return frontend_data

# No FastAPI app creation or Uvicorn execution here.
# This file now only contains the endpoint logic.