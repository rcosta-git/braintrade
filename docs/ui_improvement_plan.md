# BrainTrade UI Improvement Plan (2025-04-13)

**Goal:** Enhance the BrainTrade web UI based on user feedback, focusing on connection status accuracy, trade notifications, baseline state display, and live market data integration.

## 1. Accurate BCI Connection Status

*   **Problem:** UI might show "Connected" even if no fresh data is received from the Muse device.
*   **Solution:**
    *   **Backend (`processing.py`):** Track the timestamp of the last successfully received OSC message (EEG, PPG, or ACC). Store this `last_osc_timestamp` (ISO string or Unix timestamp) in the shared data store (`data_store.py`).
    *   **API (`web_server.py`):** Include `last_osc_timestamp` in the `/api/state` JSON response.
    *   **Frontend (`BiomarkerContext.tsx`):**
        *   Add state: `isBciConnected` (boolean, default true).
        *   In the API fetch logic (`fetchData`): Calculate the time difference between `Date.now()` and the received `data.last_osc_timestamp`. Update `isBciConnected` state (e.g., `true` if difference < 5000ms).
        *   On API fetch error (`catch` block): Set `isBciConnected` to `false`.
        *   Provide `isBciConnected` in the context value.
    *   **Frontend (UI):** Update relevant UI elements (e.g., a status indicator icon/text) to visually reflect the `isBciConnected` state.

## 2. "Optimal State" Trade Notification (Heuristic Direction)

*   **Problem:** Need to notify the user when their state is optimal for trading and provide a directional suggestion with confidence, per the "vibe trading" concept.
*   **Solution:**
    *   **Backend (Market Data Fetch - New/Modified Module e.g., `market_data.py`):**
        *   Periodically fetch BTC price (e.g., every 1-5 minutes) using a public API (e.g., CoinGecko: `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`).
        *   Calculate a simple market `trend` ('Up', 'Down', 'Flat') based on recent price movement. Store this trend in the shared data store.
    *   **Backend (`state_logic.py`):**
        *   Calculate `is_optimal_for_trading` (boolean) based on physiological state (e.g., 'Optimal' or 'Calm' `overall_state`, low stress metrics).
        *   Implement **Heuristic Logic:** Define rules combining `is_optimal_for_trading`, specific `overall_state`, and the market `trend` to determine:
            *   `suggested_position` ('long', 'short', or null).
            *   `confidence_level` ('Low', 'Medium', or null).
        *   *Example Rule:* If optimal AND state is 'Calm' AND trend is 'Up', suggest 'long' with 'Medium' confidence. If optimal AND state is 'Focused' AND trend is 'Down', suggest 'short' with 'Medium' confidence. Other combinations yield 'Low' confidence or null.
    *   **Backend (`data_store.py`):** Store `is_optimal_for_trading`, `suggested_position`, and `confidence_level`.
    *   **API (`web_server.py`):** Add `is_optimal_for_trading`, `suggested_position`, and `confidence_level` to the `/api/state` response.
    *   **Frontend (`BiomarkerContext.tsx`):**
        *   Update `isOptimalTradingState` based on `data.is_optimal_for_trading`.
        *   Update `suggestedPosition` state based on `data.suggested_position`.
        *   Add state for `confidenceLevel` and update it from `data.confidence_level`.
        *   Provide `confidenceLevel` in the context.
    *   **Frontend (`NotificationPopup.tsx`):**
        *   Trigger logic remains based on `isOptimalTradingState` and `suggestedPosition` being non-null.
        *   Update content to display the `suggestedPosition` and the `confidenceLevel` (e.g., "Suggestion: LONG (Medium Confidence)"). Restore directional icons/colors based on `suggestedPosition`.

## 3. Baseline State Handling

*   **Problem:** UI needs to clearly indicate the initial baseline calculation period.
*   **Solution:**
    *   **Backend/API:** Ensure the `systemPhase` ('Initializing', 'Calculating Baseline', 'Monitoring', 'Unknown') is accurately provided via the `/api/state` endpoint.
    *   **Frontend (`NotificationPopup.tsx`):** The existing `useEffect` hook showing a toast notification during 'Calculating Baseline' is sufficient. (No changes needed here).
    *   **Frontend (UI Panels):** Modify main display components (e.g., `BiomarkerPanel.tsx`, charts) to conditionally render loading indicators or "Calculating baseline..." text instead of data when `systemPhase === 'Calculating Baseline'`.

## 4. Live BTC Data (for UI Display)

*   **Problem:** Need to display live BTC price in the UI chart/components.
*   **Solution:**
    *   **API Choice:** Use CoinGecko free endpoint: `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`.
    *   **Frontend (`BiomarkerContext.tsx`):**
        *   Add state: `btcPrice` (number | null).
        *   Add a *new* `useEffect` hook to fetch from the CoinGecko URL every 60 seconds using `fetch`/`setInterval`, updating `btcPrice`. Include error handling.
        *   Provide `btcPrice` in the context value.
    *   **Frontend (UI):** Ensure components needing the price (like `AssetChart.tsx` and potentially `NotificationPopup.tsx` via props) receive and display `btcPrice` from the context. *(Note: This frontend fetch is separate from the backend fetch needed for the heuristic logic in item #2)*.

## Plan Visualization (Mermaid)

```mermaid
graph TD
    subgraph Frontend (React - web/)
        direction LR
        UI_Panels[UI Panels (BiomarkerPanel, AssetChart)]
        Popup[NotificationPopup.tsx]
        Context[BiomarkerContext.tsx]
        FetchAPI{Fetch /api/state (every 1s)}
        FetchBTC_UI{Fetch CoinGecko BTC (every 60s)}

        FetchAPI -- biomarker data, systemPhase, is_optimal, suggestion, confidence, last_timestamp --> Context
        FetchBTC_UI -- btcPrice (for UI) --> Context
        Context -- State --> UI_Panels
        Context -- State --> Popup
        Popup -- Displays Trade Suggestion, Confidence, Baseline Toast --> User
        UI_Panels -- Displays Biomarkers, Charts, BCI Status, BTC Price --> User
    end

    subgraph Backend (Python)
        direction LR
        FastAPI[web_server.py (/api/state)]
        SharedState[data_store.py (Shared Data: state, phase, optimal, suggestion, confidence, last_timestamp, market_trend)]
        StateLogic[state_logic.py (Calculates state, optimal, heuristic suggestion/confidence)]
        MarketFetcher[market_data.py (Fetches BTC price, calculates trend)] ;; New/Modified Module
        Baseline[baseline.py (Sets phase)]
        Processing[processing.py (Updates last_timestamp, calls others, triggers MarketFetcher)]
        OSCHandler[osc_handler.py]

        OSCHandler -- OSC Data --> Processing
        Processing --> Baseline
        Processing --> MarketFetcher
        MarketFetcher --> SharedState
        Processing -- Biomarker Data --> StateLogic
        SharedState -- Market Trend --> StateLogic ;; StateLogic needs trend
        StateLogic --> SharedState
        Processing --> SharedState ;; For timestamp
        SharedState --> FastAPI
    end

    Muse[Muse Headset (via Muse Direct)] -- OSC --> OSCHandler
    CoinGecko_Backend[CoinGecko API] --> MarketFetcher
    CoinGecko_Frontend[CoinGecko API] --> FetchBTC_UI
    Frontend -- HTTP Request --> FastAPI

    %% Styling
    classDef frontend fill:#D6EAF8,stroke:#3498DB
    classDef backend fill:#D5F5E3,stroke:#2ECC71
    class UI_Panels,Popup,Context,FetchAPI,FetchBTC_UI frontend
    class FastAPI,SharedState,StateLogic,MarketFetcher,Baseline,Processing,OSCHandler backend

## Implementation Status & Next Steps

**Completed:**
*   Implemented accurate BCI connection status display.
*   Implemented heuristic trade suggestions with confidence levels.
*   Added a loading state display during baseline calculation.
*   Integrated live BTC price fetching for the main price display.

**Remaining Issues:**
*   The AssetChart still uses simulated data for the chart line itself.
*   Further testing and refinement of the heuristic trade suggestion logic is needed.

**Next Steps:**
*   Address the remaining issues.
*   Thoroughly test the application with live data from the Muse headset.