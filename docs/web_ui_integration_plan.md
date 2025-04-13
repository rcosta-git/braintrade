# BrainTrade Monitor - Web UI Integration Plan

**Goal:** Replace the current Tkinter UI with the React-based web UI located in the `web/` directory, connecting it to the live data from the Python `braintrade_monitor`.

**Core Components & Steps:**

1.  **Backend API Implementation (Python):**
    *   **Framework:** Use FastAPI with Uvicorn.
    *   **Dependencies:** Add `fastapi` and `uvicorn[standard]` to `requirements.txt`.
    *   **Shared State:**
        *   Define a dictionary structure to hold the latest relevant data (e.g., `overall_state`, `alpha_beta_ratio`, `heart_rate`, `expression_dict`, `movement_metric`, `theta_power`, `timestamp`).
        *   Modify `processing.py` to update this dictionary (protected by a `threading.Lock`) in each processing loop iteration after state calculation.
    *   **API Server (`web_server.py`):**
        *   Create `web_server.py` in the project root.
        *   Implement a FastAPI application.
        *   Enable CORS (Cross-Origin Resource Sharing) middleware to allow requests from the frontend development server (likely running on a different port).
        *   Create a GET endpoint `/api/state`.
        *   This endpoint will read the latest data from the shared state dictionary.
        *   **Data Mapping:** Map the backend dictionary fields to the `BiomarkerData` structure expected by the frontend (`emotionalState`, `heartRate`, `brainwaveState`, `accelerometer`). This mapping will require some interpretation (e.g., mapping `overall_state` string to `emotionalState` enum, selecting a primary EEG metric for `brainwaveState`, potentially simplifying `movement_metric` to `accelerometer`).
        *   Return the mapped data as JSON.
2.  **Frontend Modifications (TypeScript/React in `web/`):**
    *   **Modify `web/src/contexts/BiomarkerContext.tsx`:**
        *   Remove the `useEffect` hook containing the `setInterval` data simulation.
        *   Implement data fetching: Use `fetch` within a `useEffect` hook combined with `setInterval` (e.g., polling every 1000ms) to call the backend's `/api/state` endpoint.
        *   Update the `biomarkers` state using `setBiomarkers` with the mapped data received from the API.
        *   Remove or comment out the UI's internal logic for `isOptimalTradingState` and `suggestedPosition` to rely on the backend's state determination.
    *   **Review UI Components:** Briefly check components like `web/src/components/BiomarkerPanel.tsx` to ensure they display the fetched and mapped data correctly. Adjust props or display logic if needed based on the mapping decisions.
3.  **Documentation & Workflow:**
    *   **Update `README.md`:** Add sections explaining how to install dependencies (`pip install -r requirements.txt`, `cd web && npm install`) and run both the backend (`python3 main.py`, `uvicorn web_server:app --reload`) and frontend (`cd web && npm run dev`).
    *   **Testing:** Verify the end-to-end flow: run the backend monitor, run the API server, run the frontend dev server, and check if the web UI updates with data reflecting the backend state.

**Diagram:**

```mermaid
graph TD
    subgraph Python Backend
        A[main.py / processing.py] -- Updates --> B(Shared State Dict + Lock);
        C[web_server.py (FastAPI)];
        C -- Reads --> B;
        C -- Serves --> D[/api/state Endpoint w/ Mapping];
    end

    subgraph Web Frontend (React/Vite @ web/)
        E[BiomarkerContext.tsx] -- Polls (fetch) --> D;
        E -- Updates --> F(React State);
        F -- Renders --> G[UI Components];
    end

    style Python Backend fill:#ccf,stroke:#333,stroke-width:2px
    style Web Frontend fill:#cfc,stroke:#333,stroke-width:2px