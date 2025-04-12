graph LR
    subgraph Phone
        MuseS[Muse S Device] -- Bluetooth --> MuseApp[Muse App]
    end
    subgraph Network
        MuseApp -- OSC/UDP --> Mac[Your Mac]
    end
    subgraph Mac
        PythonScript[eeg_visualizer.py] -- Listens on Port 5001 --> OSCServer(OSC Server Logic)
        OSCServer -- Parses Data --> DataStore[(Thread-Safe Data Storage)]
        DataStore -- Reads Data --> VizLogic[Terminal Visualization (plotext)]
    end

    style Phone fill:#lightgrey,stroke:#333,stroke-width:2px
    style Mac fill:#lightblue,stroke:#333,stroke-width:2px