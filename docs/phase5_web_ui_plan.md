# Phase 5 Plan: Web UI Migration (Future Enhancement)

**Part of Project:** BrainTrade - Mental State Monitor
**Builds Upon:** Phase 2/3/4 (Core logic implemented with modular UI)

**Objective:** Replace the desktop UI (Tkinter/Rich) with a web-based dashboard, allowing remote viewing and potentially more sophisticated visualizations.

**Assumptions:** The core monitoring script (`stress_monitor.py` or similar) has been designed with separation between the data processing/state logic and the UI update mechanism (as noted in the refined Phase 2 plan).

**Core Components:**

1.  **Backend Web Framework:**
    *   **Choice:** Select a simple Python web framework. **Flask** or **FastAPI** are recommended for their simplicity and ease of integration.
    *   **Implementation:** Create a minimal web server application.

2.  **API Endpoint:**
    *   **Goal:** Expose the latest calculated state and metrics via a simple API.
    *   **Implementation:** Define an endpoint (e.g., `/api/state`) in the Flask/FastAPI app. This endpoint will access the shared state information (calculated by the core monitor script) and return it as JSON.
        ```json
        // Example JSON response
        {
          "timestamp": 1678886400.123,
          "overall_state": "Stressed/Tilted",
          "alpha_beta_ratio": 0.65,
          "heart_rate": 85.2,
          "expression": "Angry",
          "movement_level": "High",
          "theta_beta_ratio": 1.8, // From Phase 3
          "blink_rate": 25.0,     // From Phase 3
          "rmssd": 35.5           // From Phase 4 (if implemented)
          // Add other relevant metrics
        }
        ```

3.  **Communication: Monitor Script <-> Web Backend:**
    *   **Goal:** Allow the web backend to access the latest state calculated by the continuously running monitor script.
    *   **Method Choice:**
        *   **Shared State Variable (Simple):** The monitor script writes the latest state dictionary to a shared variable (protected by a `threading.Lock`). The Flask/FastAPI endpoint reads from this variable when requested. Easiest for hackathon context if running in same process or using simple inter-process communication.
        *   **Queue:** The monitor script puts state updates onto a `queue.Queue`. The Flask/FastAPI backend reads from the queue (might require running backend in separate thread/process).
        *   **WebSocket (Push):** The monitor script pushes state updates directly to connected web clients via a WebSocket server integrated into the backend. More complex but provides real-time push updates.
    *   **Recommendation:** Start with the **Shared State Variable** approach for simplicity.

4.  **Frontend Web Application:**
    *   **Goal:** Display the state information dynamically in a web browser.
    *   **Implementation:**
        *   Create basic HTML structure for the dashboard layout.
        *   Use CSS for styling.
        *   Use JavaScript to:
            *   Periodically fetch data from the `/api/state` endpoint using `fetch` (e.g., every 0.5-1 second).
            *   Update the HTML elements (text values, background colors, simple charts) based on the received JSON data.
            *   (Alternative: If using WebSockets, establish a connection and update the UI when new data is pushed from the server).
    *   **Visualization:** Can use simple text, color changes, or incorporate basic JS charting libraries (e.g., Chart.js) for trends if time permits.

5.  **Running the System:**
    *   The core monitor script (`stress_monitor.py`) runs as one process.
    *   The Flask/FastAPI web server runs as a separate process (e.g., using `flask run` or `uvicorn`).
    *   The user accesses the dashboard via a web browser pointing to the local server address (e.g., `http://127.0.0.1:5000`).

**Key Libraries (Additions):**
    *   `Flask` or `FastAPI`
    *   `uvicorn` (if using FastAPI)
    *   (Frontend libraries are handled by the browser)

**Implementation Steps:**
    *   Set up basic Flask/FastAPI application.
    *   Implement shared state mechanism between monitor script and web backend.
    *   Create `/api/state` endpoint in backend.
    *   Develop basic HTML/CSS/JS frontend.
    *   Implement JS logic for fetching and displaying data.
    *   Test end-to-end flow.