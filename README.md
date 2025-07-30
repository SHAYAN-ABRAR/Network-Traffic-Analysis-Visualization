# Network Traffic Analysis Tool

This Python-based tool analyzes network traffic data stored in a MySQL database, providing visualizations of IP and port activity. It includes two main scripts for processing and a GUI for visualizing data, leveraging pandas, tkinter, and matplotlib.

## Features
- **Scatter Plot (Frame 1)**: Displays destination ports vs. hit counts for a selected IP.
- **Bar and Pie Charts (Frame 2)**: Shows top 20 ports by hit count and domain distribution for a selected port.
- **IP Resolution**: Fetches domain and geolocation data for IPs using the ipinfo.io API.
- **Database Integration**: Stores and retrieves data from MySQL tables (`LOG_DNS`, `PLOT_DATA`).
- **Command-Line Interface**: Processes top 20 ports or domains for a specific date/port.

## Files
- **`NetworkTrafficAnalysis.py`**: Main script with GUI for visualizing IP/port data and database interactions.
- **`portHits.py`**: Handles domain hit counts for a specific port and date, storing results in `PLOT_DATA`.
- **`topTwentyPorts.py`**: CLI script to call functions for top 20 ports or domains analysis.

## Requirements
- Python 3.x
- Libraries: `pandas`, `mysql-connector-python`, `tkinter`, `matplotlib`, `requests`, `tkcalendar`, `numpy`, `sqlalchemy`
- MySQL database with `syslog` schema and tables (`log_{date_str}`, `LOG_DNS`, `PLOT_DATA`)
- ipinfo.io API token (replace `cf9348bd3ea2ab` in code with your token)

