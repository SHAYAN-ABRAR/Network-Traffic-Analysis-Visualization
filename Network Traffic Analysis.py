import pandas as pd
import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from tkcalendar import DateEntry

# Global variables to store data
dst_counts = None
unique_ips = []

# Function to fetch data for a given date
def fetch_data(date_str):
    global dst_counts, unique_ips
    try:
        engine = mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        )
        query = f"SELECT * FROM log_{date_str}"
        df = pd.read_sql(query, engine)
        dst_counts = df.groupby(['dst', 'dstport']).size().reset_index(name='count')
        engine.close()
    except Exception as e:
        messagebox.showerror("Database Error", f"Database connection lost or table not found for {date_str}: {e}")
        dst_counts = None
        unique_ips = []
    
    # Update unique IPs
    if dst_counts is not None:
        unique_ips = sorted(dst_counts['dst'].unique())
        num_ips = len(unique_ips)
        print(f"Number of unique IPs for {date_str}: {num_ips}")
    else:
        unique_ips = []
        print(f"No data available for {date_str}")
    
    # Update dropdown
    combo['values'] = unique_ips
    combo.set("Select an IP")
    
    # Clear scatter plot
    ax.clear()
    canvas.draw()

# Create main Tkinter window
root = tk.Tk()
root.title("Destination IP Scatter Plot")
root.geometry("800x600")

# Define dynamic date range
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
calendar_label = f"Select Date ({min_date.strftime('%B %d, %Y')} to {max_date.strftime('%B %d, %Y')})"

# Create date entry widget
tk.Label(root, text=calendar_label, font=("Arial", 12, "bold")).pack(pady=10)
date_entry = DateEntry(root, width=30, date_pattern="yyyy-mm-dd",
                       mindate=min_date, maxdate=max_date,
                       year=today.year, month=today.month, day=today.day)
date_entry.pack(pady=5)

# Button to fetch data
def on_date_submit():
    date_str = date_entry.get().strip()
    print(f"Attempting to process date from DateEntry: '{date_str}'")  # Debug print
    if not date_str:
        messagebox.showerror("Invalid Date", "Please select a date from the calendar first.")
        return
    try:
        # Convert date to YYYYMMDD for fetch_data
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        date_str_ymd = selected_date.strftime("%Y%m%d")
        print(f"Converted to YYYYMMDD: {date_str_ymd}")  # Debug print
        # Validate date range (redundant with DateEntry but robust)
        if selected_date < min_date:
            messagebox.showerror("Invalid Date", f"Selected date is before {min_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        if selected_date > max_date:
            messagebox.showerror("Invalid Date", f"Selected date is after {max_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        fetch_data(date_str_ymd)
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}'. Please select a valid date. Error: {e}")
        return

tk.Button(root, text="Get Date", command=on_date_submit).pack(pady=10)

# Create dropdown (Combobox)
tk.Label(root, text="Select Destination IP:", font=("Arial", 12)).pack(pady=10)
combo = ttk.Combobox(root, values=unique_ips, state='readonly', width=30)
combo.pack(pady=5)
combo.set("Select an IP")

# Create Matplotlib figure
fig, ax = plt.subplots(figsize=(6, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Function to update scatter plot
def update_plot(event):
    ax.clear()
    selected_ip = combo.get()
    if selected_ip and selected_ip != "Select an IP" and dst_counts is not None:
        filtered_data = dst_counts[dst_counts['dst'] == selected_ip]
        ax.scatter(filtered_data['dstport'], filtered_data['count'], s=100)
        ax.set_xlabel('Destination Port (dstport)')
        ax.set_ylabel('Count')
        ax.set_title(f'Count vs dstport for IP: {selected_ip}')
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
    canvas.draw()

# Bind dropdown selection to update_plot
combo.bind("<<ComboboxSelected>>", update_plot)

# Fetch initial data for today's date
fetch_data(today.strftime("%Y%m%d"))

# Start the Tkinter event loop
root.mainloop()