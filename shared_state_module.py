import threading
import time

# Initialize with placeholder structure and values
shared_dict = {
    "timestamp": time.time(),
    "system_phase": "Initializing",
    "overall_state": "Initializing",
    "alpha_beta_ratio": None,
    "heart_rate": None,
    "expression_dict": None,
    "movement_metric": None,
    "theta_power": None,
    "last_osc_timestamp": None,
    "suggested_position": None,
    "confidence_level": None,
    "market_trend": None,
}
# Using a standard threading Lock should be sufficient if Uvicorn runs in threaded mode by default
shared_lock = threading.Lock()