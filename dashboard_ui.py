import tkinter as tk
import queue # Need queue here
import time # Keep time for the __main__ block example

class DashboardUI:
    # ... (no changes inside the class) ...
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

def start_ui(update_queue):
    root = tk.Tk()
    dashboard = DashboardUI(root)

    # Function to check the queue and update UI
    def check_queue():
        try:
            # Process all available updates in the queue
            while True:
                update_data = update_queue.get_nowait()
                dashboard.update_state(update_data.get("state", "Unknown"))
                dashboard.update_expression(update_data.get("expression", "Unknown"))
                dashboard.update_movement(update_data.get("movement", "Unknown"))
                # Format HR and Ratio nicely
                hr_val = update_data.get("hr", "Unknown")
                ratio_val = update_data.get("ratio", "Unknown")
                dashboard.update_hr(f"{hr_val:.1f}" if isinstance(hr_val, (int, float)) else hr_val)
                dashboard.update_ratio(f"{ratio_val:.2f}" if isinstance(ratio_val, (int, float)) else ratio_val)

        except queue.Empty:
            pass # No more updates for now

        # Schedule the next check after 100ms
        root.after(100, check_queue) # 100ms interval

    # Start the first check
    check_queue()

    # Start the Tkinter main loop (this will block the main thread)
    root.mainloop()

# Keep the testing block, but it now relies on the main thread's loop
if __name__ == '__main__':
    # import queue # Already imported above
    # import time # Already imported above
    test_queue = queue.Queue()

    # Function to simulate putting data into the queue
    def simulate_data_input(q):
        time.sleep(1)
        q.put({"state": "Calm", "ratio": 1.5, "hr": 60.5, "expression": "Neutral", "movement": "Low"})
        time.sleep(2)
        q.put({"state": "Stress", "ratio": 0.8, "hr": 90.1, "expression": "Angry", "movement": "High"})
        time.sleep(2)
        q.put({"state": "Warning", "ratio": 1.0, "hr": 75.9, "expression": "Neutral", "movement": "Medium"})

    # Start the simulation in a separate thread so it doesn't block the UI
    import threading
    sim_thread = threading.Thread(target=simulate_data_input, args=(test_queue,), daemon=True)
    sim_thread.start()

    # Start the UI with the test queue
    start_ui(test_queue)