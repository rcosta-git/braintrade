# BrainTrade Monitor - Handoff Summary (2025-04-13)

This document summarizes the current state of the BrainTrade Monitor project for another LLM to quickly understand the project and continue development.

## Project Goal

To monitor the real-time mental state (stress, fatigue, focus) of a day trader using a Muse S headset (EEG, PPG, Accelerometer) and potentially computer vision (facial expressions). The system aims to provide feedback to help prevent poor trading decisions driven by suboptimal mental states.

## Current Status

*   **Backend:**
    *   The core Python logic is refactored into a modular package (`braintrade_monitor`).
    *   OSC data is received and processed in a background thread.
    *   Baseline metrics are calculated.
    *   Heuristic trade suggestions (Long/Short/None) with confidence levels are calculated based on physiological data and market trend (BTC price from CoinGecko).
    *   A FastAPI backend (`web_server.py`) serves the processed data via an API endpoint (`/api/state`).
*   **Frontend:**
    *   A React/TypeScript web UI (`web/`) displays the biomarker data, connection status, and trade suggestions.
    *   The UI fetches data from the backend API every second.
    *   The UI displays a loading state during baseline calculation.
    *   The UI displays live BTC price data fetched directly from CoinGecko.

## Key Components

*   **`main.py`:** Main application entry point. Starts OSC server, baseline calculation, processing thread, and API server.
*   **`braintrade_monitor/`:** Python package containing core logic:
    *   `osc_handler.py`:** Handles OSC data reception.
    *   `data_store.py`:** Manages shared data buffers and thread safety.
    *   `feature_extraction.py`:** Feature extraction functions (EEG ratio, BPM).
    *   `baseline.py`:** Baseline calculation logic.
    *   `processing.py`:** Main real-time data processing loop.
    *   `state_logic.py`:** Stress state determination and trade suggestion logic.
    *   `market_data.py`:** Fetches BTC price and calculates trend.
*   **`web_server.py`:** FastAPI server to bridge backend and web UI.
*   **`web/`:** Web UI Frontend (React/TypeScript/Vite):
    *   `src/contexts/BiomarkerContext.tsx`:** Manages application state and data fetching.
    *   `src/components/BiomarkerPanel.tsx`:** Displays biomarker data.
    *   `src/components/AssetChart.tsx`:** Displays BTC price chart.
    *   `src/components/NotificationPopup.tsx`:** Displays trade suggestions and system messages.

## Data Flow

1.  Muse Direct streams OSC data (EEG, PPG, ACC) to the Python backend.
2.  The `processing_loop` in `processing.py` processes the data, calculates features, and determines the trader's state.
3.  The `market_data.py` module fetches the current BTC price and calculates the market trend.
4.  The `state_logic.py` module determines the `suggested_position` and `confidence_level` based on the trader's state and the market trend.
5.  The processed data (including state, features, suggestion, confidence, and BTC trend) is stored in a shared data dictionary (`shared_state_dict`).
6.  The FastAPI server (`web_server.py`) exposes an API endpoint (`/api/state`) that reads the data from the shared dictionary.
7.  The React frontend (`web/`) fetches the data from the API endpoint every second.
8.  The UI components display the fetched data.
9.  The `AssetChart.tsx` component fetches BTC price data directly from CoinGecko for the main price display.

## Known Issues & Next Steps

*   **UI Not Updating:** The UI is not updating with the latest data.
*   **Verify Data Flow:** The first step is to verify that the data is flowing correctly from the backend to the frontend.
    *   Check the backend terminal for "Processing loop iteration completed and shared state updated." messages.
    *   Check the browser console for "BiomarkerContext: Data received: { ... }" messages.
    *   If the data is flowing correctly, the issue is likely in the UI component rendering logic.
*   **Asset Chart:** The chart line still uses simulated data. This should be updated to use historical BTC price data.
*   **Heuristic Logic:** The heuristic trade suggestion logic is very basic and needs further testing and refinement.
*   **Logging:** The logging level is currently set to `INFO` in most modules. Reduce verbosity by setting most logs to `DEBUG`.

## Important Notes

*   The project uses a multi-threaded architecture. Ensure thread safety when accessing shared resources.
*   The frontend is a React/TypeScript application built with Vite and Tailwind CSS.
*   The backend is a Python application using FastAPI and Uvicorn.
*   The project uses OSC for data streaming from the Muse headset.
*   The project uses a .rooignore file to prevent access to certain files and directories.

This summary should provide a good starting point for understanding the project and continuing development.