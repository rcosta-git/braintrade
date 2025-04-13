import tkinter as tk
import threading
import time

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

def start_ui(update_queue):
    root = tk.Tk()
    dashboard = DashboardUI(root)

    def update_loop():
        while True:
            try:
                update_data = update_queue.get_nowait()
                dashboard.update_state(update_data.get("state", "Unknown"))
                dashboard.update_expression(update_data.get("expression", "Unknown"))
                dashboard.update_movement(update_data.get("movement", "Unknown"))
                dashboard.update_hr(update_data.get("hr", "Unknown"))
                dashboard.update_ratio(update_data.get("ratio", "Unknown"))
            except queue.Empty:
                pass
            time.sleep(0.1)  # Adjust as needed

    update_thread = threading.Thread(target=update_loop)
    update_thread.daemon = True
    update_thread.start()

    root.mainloop()

if __name__ == '__main__':
    import queue
    import time
    update_queue = queue.Queue()
    # Example usage:
    update_queue.put({"state": "Calm", "ratio": 1.5, "hr": 60})
    time.sleep(1)
    update_queue.put({"state": "Stress", "ratio": 0.8, "hr": 90})
    time.sleep(1)
    update_queue.put({"state": "Warning", "ratio": 1.0, "hr": 75})
    start_ui(update_queue)