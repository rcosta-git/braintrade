# BrainFlow API Overview

## Summary & Capabilities

*   **Core Purpose:** BrainFlow provides a unified interface to acquire, parse, and analyze data (EEG, EMG, ECG, Accelerometer, Gyro, PPG, etc.) from a wide variety of biosensor devices.
*   **Board Abstraction:** It uses a `BoardShim` class that abstracts the specifics of each supported device. You interact with the `BoardShim` using a consistent API, regardless of the underlying hardware (e.g., Muse S, Cyton, Synthetic Board). Board selection is done via `BoardIds` enum.
*   **Connection:** Handles different connection types (Bluetooth LE, WiFi, Serial) based on the board. Connection details are passed via a `BrainFlowInputParams` object. For Muse S (using `BoardIds.MUSE_S_BOARD`), it uses native Bluetooth LE, and connection parameters like MAC address are often optional due to auto-discovery.
*   **Session Management:** Provides methods to prepare the connection (`prepare_session`), start/stop data streaming (`start_stream`, `stop_stream`), and release resources (`release_session`).
*   **Data Acquisition:** Data is retrieved using `get_board_data()` or `get_current_board_data()`. It returns a 2D NumPy array (`[channels x samples]`).
*   **Data Structure:** The specific layout of channels in the data array is board-dependent. BrainFlow provides helper methods (`get_eeg_channels`, `get_accel_channels`, `get_timestamp_channel`, etc.) to get the correct row indices for specific data types for any given board ID. `get_board_descr()` gives a full description.
*   **Signal Processing (`DataFilter`):** Although we didn't explicitly read its documentation, the architecture diagram and API reference hint at a `DataFilter` class. This likely contains functions for common biosignal processing tasks like filtering, denoising, downsampling, and calculating metrics (e.g., band power for EEG). The `python_api_reference.txt` likely contains details on these methods further down.
*   **Machine Learning (`MLModel`):** The architecture also shows an `MLModel` component, suggesting built-in capabilities for classification or other ML tasks on the biosignals.
*   **Development Support:** Includes a `SYNTHETIC_BOARD` for generating simulated data, allowing development and testing without physical hardware. It also provides logging capabilities for debugging.
*   **Language Support:** While we focused on Python, BrainFlow offers packages for various languages (Java, C#, C++, Matlab, etc.), all built upon a common C++ core library.

## Architecture Diagram

```mermaid
graph TD
    subgraph HighLevelAPI [High-Level API (Python/Java/etc.)]
        HL_Package[BrainFlow Package] --> HL_BoardShim[BoardShim];
        HL_Package --> HL_DataFilter[DataFilter];
        HL_Package --> HL_MLModel[MLModel];
    end

    subgraph LowLevelAPI [Low-Level API (C/C++)]
        LL_BoardController[BoardController (src/board_controller)];
        LL_DataHandler[DataHandler (src/data_handler)];
        LL_MLModule[MLModule (src/ml)];

        LL_BC_Factory[BoardController Factory (board_controller.cpp)];
        LL_BoardController --> LL_BC_Factory;
        LL_BC_Factory --> LL_Board1[Board 1];
        LL_BC_Factory --> LL_Board2[Board 2];
        LL_BC_Factory --> LL_Board3[Board 3];
        note for LL_BC_Factory "Board Classes inherit from abstract Board Class.<br/>May use helper libs (DynLibBoard, BTLibBoard, etc.)";


        LL_DataHandler --> LL_DH_Method1[Method 1];
        LL_DataHandler --> LL_DH_Method2[Method 2];
        LL_DataHandler --> LL_DH_Method3[Method 3];

        LL_ML_Factory[MLModule Factory (ml_module.cpp)];
        LL_MLModule --> LL_ML_Factory;
        LL_ML_Factory --> LL_Classifier1[Classifier 1];
        LL_ML_Factory --> LL_Classifier2[Classifier 2];
        LL_ML_Factory --> LL_Classifier3[Classifier 3];
        note for LL_ML_Factory "Classifiers inherit from abstract BaseClassifier Class.";

    end

    HL_BoardShim -- Calls methods from --> LL_BoardController;
    HL_DataFilter -- Calls methods from --> LL_DataHandler;
    HL_MLModel -- Calls methods from --> LL_MLModule;

    style HighLevelAPI fill:#e6f2ff,stroke:#b3d9ff
    style LowLevelAPI fill:#fff8e1,stroke:#ffe082