import tkinter as tk
import queue
import threading
import time
import logging # Import logging
import numpy as np # Import numpy for isnan check

# Get a logger instance specific to this module
logger = logging.getLogger(__name__)

class DashboardUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BrainTrade Monitor")

        self.state_label = tk.Label(root, text="State: Unknown")
        self.state_label.pack()

        self.expression_label = tk.Label(root, text="Expression: Unknown")
        self.expression_label.pack()

        self.movement_label = tk.Label(root, text="Movement: Unknown")
        self.movement_label.pack()

        self.hr_label = tk.Label(root, text="HR: Unknown")
        self.hr_label.pack()

        self.ratio_label = tk.Label(root, text="Ratio: Unknown")
        self.ratio_label.pack()

    def update_state(self, state):
        self.state_label.config(text=f"State: {state}")

    def update_expression(self, expression):
        self.expression_label.config(text=f"Expression: {expression}")

    def update_movement(self, movement):
        self.movement_label.config(text=f"Movement: {movement}")

    def update_hr(self, hr):
        self.hr_label.config(text=f"HR: {hr}")

    def update_ratio(self, ratio):
        self.ratio_label.config(text=f"Ratio: {ratio}")

def start_ui(update_queue: queue.Queue):
    """Starts the Tkinter UI and polls the update_queue."""
    root = tk.Tk()
    dashboard = DashboardUI(root)

    # Function to check the queue and update UI (runs on main UI thread)
    def check_queue():
        try:
            # Process all available updates in the queue to avoid lag
            while True:
                update_data = update_queue.get_nowait() # Non-blocking get

                # Update labels, formatting numbers nicely
                state = update_data.get("state", "Unknown")
                expression = update_data.get("expression", "N/A")
                movement = update_data.get("movement", "N/A")
                hr_val = update_data.get("hr", np.nan) # Use nan as default for formatting
                ratio_val = update_data.get("ratio", np.nan)

                dashboard.update_state(state)
                dashboard.update_expression(expression)
                dashboard.update_movement(movement)
                dashboard.update_hr(f"{hr_val:.1f}" if not np.isnan(hr_val) else "N/A")
                dashboard.update_ratio(f"{ratio_val:.2f}" if not np.isnan(ratio_val) else "N/A")

        except queue.Empty:
            pass # No more updates in the queue for now
        except Exception as e:
             logger.exception(f"Error updating UI from queue: {e}") # Use logger instance

        # Schedule the next check after 100ms
        # This keeps the UI responsive without busy-waiting
        root.after(100, check_queue)

    # Start the first check
    logger.info("UI: Starting queue check loop.") # Use logger instance
    logging.info("UI: Starting queue check loop.")
    check_queue()

    # Start the Tkinter main event loop (this blocks until the window is closed)
    logger.info("UI: Starting mainloop.") # Use logger instance
    root.mainloop()
    logger.info("UI: Mainloop finished.") # Use logger instance
    logging.info("UI: Mainloop finished.")


if __name__ == '__main__':
    # Example Usage / Test Block
    # Setup basic logging ONLY if run directly for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    test_queue = queue.Queue()

    # Function to simulate putting data into the queue (uses logger now)
    def simulate_data_input(q):
        logger.info("Test Simulator: Starting data simulation.")
        time.sleep(2)
        logger.info("Test Simulator: Sending Calm state.")
        q.put({"state": "Calm", "ratio": 1.5, "hr": 60.5, "expression": "Neutral", "movement": "Low"})
        time.sleep(3)
        logger.info("Test Simulator: Sending Stress state.")
        q.put({"state": "Stress", "ratio": 0.8, "hr": 90.1, "expression": "Angry", "movement": "High"})
        time.sleep(3)
        logger.info("Test Simulator: Sending Warning state.")
        q.put({"state": "Warning", "ratio": 1.0, "hr": 75.9, "expression": "Neutral", "movement": "Medium"})
        logger.info("Test Simulator: Simulation finished.")

    # Start the simulation in a separate thread so it doesn't block the UI
    sim_thread = threading.Thread(target=simulate_data_input, args=(test_queue,), daemon=True)
    sim_thread.start()

    # Start the UI with the test queue (this will block)
    start_ui(test_queue)