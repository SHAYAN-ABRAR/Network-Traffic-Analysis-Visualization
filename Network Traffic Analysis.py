import pandas as pd
import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from tkcalendar import DateEntry

# Global variables to store data for each frame
frame_data = {
    'frame1': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': []},
    'frame2': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': []}
}

# Function to fetch data for the first frame
def fetch_data_frame1(date_str):
    update_frame_data('frame1', date_str, "SELECT * FROM log_{date_str}")

# Function to fetch data for the second frame (single query fetching dstport and dst counts)
def fetch_data_frame2(date_str):
    try:
        engine = mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        )
        # Fetching both dstport counts and dst counts for each dstport in one query
        query = f"""
            SELECT dstport, dst, COUNT(*) as count
            FROM log_{date_str}
            WHERE dstport != '0'
            GROUP BY dstport, dst
            ORDER BY dstport, count DESC
        """
        df = pd.read_sql(query, engine)
        engine.close()

        # Store the data for both dstport counts and IP counts
        frame_data['frame2']['dst_counts'] = df
        frame_data['frame2']['unique_dstports'] = sorted(df['dstport'].unique())
        
        print(f"Debug: Frame 2 dst_counts shape: {df.shape}, columns: {df.columns.tolist()}")
        
        # Populate the dropdown for dstport
        port_combo['values'] = frame_data['frame2']['unique_dstports']
        port_combo.set("Select dstport" if frame_data['frame2']['unique_dstports'] else "No dstports available")
        
    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching data for {date_str}: {e}")
        frame_data['frame2']['dst_counts'] = None
        frame_data['frame2']['unique_dstports'] = []

# Helper function to update frame data
def update_frame_data(frame_key, date_str, query_template):
    frame = frame_data[frame_key]
    try:
        engine = mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        )
        query = query_template.format(date_str=date_str)
        df = pd.read_sql(query, engine)
        if frame_key == 'frame1':
            frame['dst_counts'] = df.groupby(['dst', 'dstport']).size().reset_index(name='count')
        else:  # frame2
            frame['dst_counts'] = df  # Direct from query, two columns: dstport, count
        print(f"Debug: {frame_key} dst_counts shape: {frame['dst_counts'].shape}, columns: {frame['dst_counts'].columns.tolist()}, data: {frame['dst_counts'].head()}")  # Enhanced debug print
        engine.close()
    except Exception as e:
        messagebox.showerror("Database Error", f"Database connection lost or table not found for {date_str}: {e}")
        frame['dst_counts'] = None
        frame['unique_ips'] = []
        frame['unique_dstports'] = []
    
    # Update unique IPs and dstports
    if frame['dst_counts'] is not None:
        if frame_key == 'frame1':
            frame['unique_ips'] = sorted(frame['dst_counts']['dst'].unique())
            frame['unique_dstports'] = sorted(frame['dst_counts']['dstport'].unique())
        else:  # frame2
            frame['unique_ips'] = []  # Not needed for frame2
            frame['unique_dstports'] = sorted(frame['dst_counts']['dstport'].unique())
        num_items = len(frame['unique_ips']) if frame_key == 'frame1' else len(frame['unique_dstports'])
        print(f"Number of unique {'IPs' if frame_key == 'frame1' else 'dstports'} for {date_str} in {frame_key}: {num_items}")
    else:
        frame['unique_ips'] = []
        frame['unique_dstports'] = []
        print(f"No data available for {date_str} in {frame_key}")
    
    # Update respective dropdown
    if frame_key == 'frame1':
        combo['values'] = frame['unique_ips']
        combo.set("Select an IP")
        ax.clear()
        canvas.draw()
    elif frame_key == 'frame2':
        port_combo['values'] = frame['unique_dstports']
        port_combo.set("Select dstport" if frame['unique_dstports'] else "No dstports available")
        ax_bar.clear()
        canvas_bar.draw()

# Create main Tkinter window (first frame)
root = tk.Tk()
root.title("Destination IP Scatter Plot")
root.geometry("800x600")

# Define dynamic date range for first frame
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
calendar_label_frame1 = f"Select Date ({min_date.strftime('%B %d, %Y')} to {max_date.strftime('%B %d, %Y')})"

# Create date entry widget for first frame
tk.Label(root, text=calendar_label_frame1, font=("Arial", 12, "bold")).pack(pady=10)
date_entry_frame1 = DateEntry(root, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date, maxdate=max_date,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame1.pack(pady=5)

# Button to fetch data for first frame
def on_date_submit_frame1():
    date_str = date_entry_frame1.get().strip()
    print(f"Attempting to process date from DateEntry (Frame 1): '{date_str}'")
    if not date_str:
        messagebox.showerror("Invalid Date", "Please select a date from the calendar first.")
        return
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        date_str_ymd = selected_date.strftime("%Y%m%d")
        print(f"Converted to YYYYMMDD (Frame 1): {date_str_ymd}")
        if selected_date < min_date:
            messagebox.showerror("Invalid Date", f"Selected date is before {min_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        if selected_date > max_date:
            messagebox.showerror("Invalid Date", f"Selected date is after {max_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        fetch_data_frame1(date_str_ymd)
        update_plot(None)  # Update scatter plot with new data
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}' (Frame 1). Error: {e}")
        return

tk.Button(root, text="Get Date (Frame 1)", command=on_date_submit_frame1).pack(pady=10)

# Create dropdown (Combobox) for first frame
tk.Label(root, text="Select Destination IP:", font=("Arial", 12)).pack(pady=10)
combo = ttk.Combobox(root, values=frame_data['frame1']['unique_ips'], state='readonly', width=30)
combo.pack(pady=5)
combo.set("Select an IP")

# Create Matplotlib figure for scatter plot
fig, ax = plt.subplots(figsize=(6, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Function to update scatter plot
def update_plot(event):
    ax.clear()
    selected_ip = combo.get()
    if selected_ip and selected_ip != "Select an IP" and frame_data['frame1']['dst_counts'] is not None:
        filtered_data = frame_data['frame1']['dst_counts'][frame_data['frame1']['dst_counts']['dst'] == selected_ip]
        ax.scatter(filtered_data['dstport'], filtered_data['count'], s=100)
        ax.set_xlabel('Destination Port (dstport)')
        ax.set_ylabel('Count')
        ax.set_title(f'Count vs dstport for IP: {selected_ip} (Frame 1)')
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
    canvas.draw()

# Bind dropdown selection to update_plot
combo.bind("<<ComboboxSelected>>", update_plot)

# Create second frame (Toplevel window)
second_window = tk.Toplevel(root)
second_window.title("Port vs IP Count")
second_window.geometry("800x600")

# Define dynamic date range for second frame
min_date_frame2 = min_date
max_date_frame2 = max_date
calendar_label_frame2 = f"Select Date ({min_date_frame2.strftime('%B %d, %Y')} to {max_date_frame2.strftime('%B %d, %Y')})"

# Create date entry widget for second frame
tk.Label(second_window, text=calendar_label_frame2, font=("Arial", 12, "bold")).pack(pady=10)
date_entry_frame2 = DateEntry(second_window, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date_frame2, maxdate=max_date_frame2,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame2.pack(pady=5)

# Button to fetch data for second frame
def on_date_submit_frame2():
    date_str = date_entry_frame2.get().strip()
    print(f"Attempting to process date from DateEntry (Frame 2): '{date_str}'")
    if not date_str:
        messagebox.showerror("Invalid Date", "Please select a date from the calendar first.")
        return
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        date_str_ymd = selected_date.strftime("%Y%m%d")
        print(f"Converted to YYYYMMDD (Frame 2): {date_str_ymd}")
        if selected_date < min_date_frame2:
            messagebox.showerror("Invalid Date", f"Selected date is before {min_date_frame2.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        if selected_date > max_date_frame2:
            messagebox.showerror("Invalid Date", f"Selected date is after {max_date_frame2.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        fetch_data_frame2(date_str_ymd)
        update_bar_chart()  # Update bar chart after fetching data
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}' (Frame 2). Error: {e}")
        return

tk.Button(second_window, text="Get Date", command=on_date_submit_frame2).pack(pady=10)

# Create dropdown (Combobox) for second frame
tk.Label(second_window, text="Select dstport:", font=("Arial", 12)).pack(pady=10)
port_combo = ttk.Combobox(second_window, values=frame_data['frame2']['unique_dstports'], state='readonly', width=30)
port_combo.pack(pady=5)
port_combo.set("Select dstport")

# Create Matplotlib figure for bar chart
fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
canvas_bar = FigureCanvasTkAgg(fig_bar, master=second_window)
canvas_bar.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Function to update bar chart
def update_bar_chart(event=None):
    if frame_data['frame2']['dst_counts'] is not None and port_combo.get() != "Select dstport":
        selected_port = port_combo.get()
        print(f"Updating bar chart for dstport: {selected_port}")

        # Filter data based on selected dstport
        filtered_data = frame_data['frame2']['dst_counts'][frame_data['frame2']['dst_counts']['dstport'] == selected_port]
        
        # Get the top 20 IPs that hit this port (sorted by the count)
        top_20_ips = filtered_data.groupby('dst').sum().nlargest(20, 'count')
        
        print(f"Filtered data for dstport {selected_port}:\n{top_20_ips.head()}")
        
        if not top_20_ips.empty:
            ax_bar.clear()
            ax_bar.bar(top_20_ips.index, top_20_ips['count'], color='purple')
            ax_bar.set_xlabel('Destination IP (dst)')
            ax_bar.set_ylabel('Count of Hits')
            ax_bar.set_title(f'Top 20 IP Hits for dstport {selected_port} on {date_entry_frame2.get()}')
            ax_bar.tick_params(axis='x', rotation=45)
            fig_bar.tight_layout()
            canvas_bar.draw()
        else:
            print("Warning: No data for selected dstport, bar chart not updated.")
            ax_bar.clear()
            canvas_bar.draw()
    elif frame_data['frame2']['dst_counts'] is not None and port_combo.get() == "Select dstport":
        print(f"Updating bar chart with default top 20 dstport counts: {frame_data['frame2']['dst_counts'].head()}")
        ax_bar.clear()
        # Limit to top 20 dstports based on count
        top_20 = frame_data['frame2']['dst_counts'].groupby('dstport').sum().nlargest(20, 'count')
        ax_bar.bar(top_20.index, top_20['count'], color='purple')
        ax_bar.set_xlabel('Destination Port (dstport)')
        ax_bar.set_ylabel('Count of Hits')
        ax_bar.set_title(f'Top 20 dstport Counts for {date_entry_frame2.get()}')
        ax_bar.tick_params(axis='x', rotation=45)
        fig_bar.tight_layout()
        canvas_bar.draw()

# Bind dropdown selection to update_bar_chart
port_combo.bind("<<ComboboxSelected>>", update_bar_chart)

# Fetch initial data for today's date in both frames and update charts
fetch_data_frame1(today.strftime("%Y%m%d"))
update_plot(None)  # Update scatter plot with initial data
fetch_data_frame2(today.strftime("%Y%m%d"))
update_bar_chart()  # Update bar chart with initial data

# Start the Tkinter event loop
root.mainloop()
