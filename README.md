# Network Traffic Analysis Visualization

## Overview
The "Network Traffic Analysis Visualization" is a Python-based application designed to visualize network traffic data from MySQL logs. Users can select a specific date and view network traffic details, including destination IPs and ports. The data is visualized using scatter plots, which help in identifying trends and patterns in network traffic.

This tool is beneficial for network administrators and security analysts to understand traffic patterns and troubleshoot network-related issues.

## Features
- **Calendar Interface**: Select a date from a calendar widget to retrieve traffic data for that specific day.
- **Dynamic IP Dropdown**: Choose a destination IP address from a dropdown to view the corresponding traffic data.
- **Scatter Plot**: The relationship between destination ports and traffic counts is displayed using scatter plots, making it easier to spot trends.

## Requirements
- Python 
- MySQL Server (for database connectivity)
- Required Python Libraries:
  - `pandas`
  - `mysql-connector-python`
  - `tkinter`
  - `matplotlib`
  - `tkcalendar`
