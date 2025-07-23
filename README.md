# 🔍 Network Traffic Analysis & Visualization Tool

An interactive Python application to **analyze and visualize network log data** using a GUI. It connects to a MySQL database, fetches real-time server log data, resolves IPs to domain names, and displays insightful visualizations for threat monitoring and anomaly detection.

## 💡 Features

- 📅 Dynamic date range selection (past 10 days)
- 📊 Real-time **scatter and bar charts** for destination IPs and ports
- 🌐 IP-to-domain resolution using `socket` and `ipinfo.io` API
- 🛡️ Filters out invalid ports and highlights high-frequency traffic
- 💾 Stores enriched IP info (ASN, country, etc.) into `LOG_DNS` table
- 🧠 Supports deep analysis of port-wise domain traffic patterns


## ⚙️ Tech Stack

- `Python`
- `Tkinter` – for GUI
- `Matplotlib` – for data visualization
- `MySQL` – for log data storage
- `pandas` – for data wrangling
- `socket`, `requests` – for DNS and API queries

## 📁 Database Requirements

- MySQL table format: `log_YYYYMMDD`
- Table: `LOG_DNS` for enriched IP info storage
