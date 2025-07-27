import pandas as pd
import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import socket
import requests
import json
import time

# Function to resolve IP to domain name with error handling
def get_domain_name(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, OSError):
        return ip_address

# Function to fetch IP info from ipinfo.io API and insert into LOG_DNS if not exists
def insert_ip_info(ip_address, count, domain):
    start_time = time.time()
    try:
        url = f"https://api.ipinfo.io/lite/{ip_address}?token=cf9348bd3ea2ab"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        ip = data.get('ip', 'N/A')
        asn = data.get('asn', 'N/A')
        as_name = data.get('as_name', 'N/A')
        as_domain = data.get('as_domain', 'N/A')
        country_code = data.get('country_code', 'N/A')
        country = data.get('country', 'N/A')
        continent_code = data.get('continent_code', 'N/A')
        continent = data.get('continent', 'N/A')
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        unique_id = int(time.time() * 1000000)
        
        if not domain or domain == ip_address:
            domain = as_domain if as_domain and as_domain != 'N/A' else get_domain_name(ip_address)
        
        try:
            with mysql.connector.connect(
                host="192.168.100.25",
                user="sysuser",
                password="DT1Y9Q0EtBwI0",
                database="syslog"
            ) as engine:
                cursor = engine.cursor()
                cursor.execute("SELECT ip FROM LOG_DNS WHERE ip = %s", (ip,))
                if cursor.fetchone() is None:
                    insert_query = """
                        INSERT INTO LOG_DNS (ID, ip, asn, NAME, DOMAIN, country_code, country, continent_code, continent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (unique_id, ip, asn, as_name, domain, country_code, country, continent_code, continent))
                    engine.commit()
        except mysql.connector.Error as e:
            print(f"Error inserting IP info for {ip_address} into LOG_DNS: {e}")
        
        return {'domain': domain, 'data': data}
    except requests.RequestException as e:
        print(f"Error fetching IP info for {ip_address}: {e}")
        return {'domain': ip_address, 'data': None}

# Global variables to store data for each frame
frame_data = {
    'frame1': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': []},
    'frame2': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': []}
}

# Function to fetch data for the first frame
def fetch_data_frame1(date_str):
    update_frame_data('frame1', date_str, "SELECT * FROM log_{date_str}")

# Function to fetch data for the second frame
def fetch_data_frame2(date_str):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            query = f"""
                SELECT dstport, dst, COUNT(*) as count
                FROM log_{date_str}
                WHERE dstport != '0'
                GROUP BY dstport, dst
                ORDER BY dstport, count DESC
            """
            df = pd.read_sql(query, engine)
            frame_data['frame2']['dst_counts'] = df
            frame_data['frame2']['unique_dstports'] = sorted(df['dstport'].unique())
        
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
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            query = query_template.format(date_str=date_str)
            df = pd.read_sql(query, engine)
            if frame_key == 'frame1':
                frame['dst_counts'] = df.groupby(['dst', 'dstport']).size().reset_index(name='count')
            else:
                frame['dst_counts'] = df
    except Exception as e:
        messagebox.showerror("Database Error", f"Database connection lost or table not found for {date_str}: {e}")
        frame['dst_counts'] = None
        frame['unique_ips'] = []
        frame['unique_dstports'] = []
    
    if frame['dst_counts'] is not None:
        if frame_key == 'frame1':
            frame['unique_ips'] = sorted(frame['dst_counts']['dst'].unique())
            frame['unique_dstports'] = sorted(frame['dst_counts']['dstport'].unique())
        else:
            frame['unique_ips'] = []
            frame_data['frame2']['unique_dstports'] = sorted(frame['dst_counts']['dstport'].unique())
    else:
        frame['unique_ips'] = []
        frame['unique_dstports'] = []
    
    if frame_key == 'frame1':
        combo['values'] = frame['unique_ips']
        combo.set("Select an IP")
        ax.clear()
        canvas.draw()
    elif frame_key == 'frame2':
        port_combo['values'] = frame_data['frame2']['unique_dstports']
        port_combo.set("Select dstport" if frame_data['frame2']['unique_dstports'] else "No dstports available")
        ax_bar.clear()
        canvas_bar.draw()

# Function to insert data into PLOT_DATA
def insert_plot_data(date_str, selected_port):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            counter = 0  # Counter to ensure unique IDs within the same microsecond
            
            if frame_data['frame2']['dst_counts'] is not None:
                filtered_data = frame_data['frame2']['dst_counts'][frame_data['frame2']['dst_counts']['dstport'] == selected_port]
                top_20_ips = filtered_data.groupby('dst').sum().nlargest(20, 'count').reset_index()
                ip_from_df = [ip for ip in top_20_ips['dst'].tolist() if isinstance(ip, str) and ip]
                
                # Fetch domains
                domains = {}
                if ip_from_df:
                    placeholders = ','.join(['%s'] * len(ip_from_df))
                    cursor.execute(f"SELECT ip, DOMAIN FROM LOG_DNS WHERE ip IN ({placeholders})", ip_from_df)
                    existing_domains = {row[0]: row[1] for row in cursor.fetchall()}
                    for ip in ip_from_df:
                        if ip in existing_domains and existing_domains[ip]:
                            domains[ip] = existing_domains[ip]
                        else:
                            info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                            domains[ip] = info['domain']
                
                # Aggregate counts by domain and insert
                domain_counts = {}
                for ip, domain in domains.items():
                    if domain:
                        count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                        domain_counts[domain] = domain_counts.get(domain, 0) + count
                
                for domain, count in domain_counts.items():
                    unique_id = int(time.time() * 1000000) + counter
                    counter += 1
                    log_id = f"log_{date_str}"
                    cursor.execute(
                        """
                        INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (unique_id, log_id, "PORT", domain, selected_port, str(count))
                    )
            
            engine.commit()
    except mysql.connector.Error as e:
        print(f"Error inserting into PLOT_DATA: {e}")

# Create main Tkinter window (first frame)
root = tk.Tk()
root.title("Destination IP Scatter Plot")
root.geometry("800x600")

# Define dynamic date range for first frame
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
min_date_str = min_date.strftime('%B %d, %Y')
max_date_str = max_date.strftime('%B %d, %Y')
calendar_label_frame1 = f"Select Date ({min_date_str} to {max_date_str})"

# Create date entry widget for first frame
tk.Label(root, text=calendar_label_frame1, font=("Times New Roman", 12, "bold")).pack(pady=10)
date_entry_frame1 = DateEntry(root, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date, maxdate=max_date,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame1.pack(pady=5)

# Button to fetch data for first frame
def on_date_submit_frame1():
    date_str = date_entry_frame1.get().strip()
    if not date_str:
        messagebox.showerror("Invalid Date", "Please select a date from the calendar first.")
        return
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")  
        date_str_ymd = selected_date.strftime("%Y%m%d")
        if selected_date < min_date:
            messagebox.showerror("Invalid Date", f"Selected date is before {min_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        if selected_date > max_date:
            messagebox.showerror("Invalid Date", f"Selected date is after {max_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        fetch_data_frame1(date_str_ymd)
        update_plot(None)
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}' (Frame 1). Error: {e}")

tk.Button(root, text="Get Date (Frame 1)", command=on_date_submit_frame1).pack(pady=10)

# Create dropdown (Combobox) for first frame
tk.Label(root, text="Select Destination IP:", font=("Times New Roman", 12)).pack(pady=10)
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
        insert_ip_info(selected_ip, 0, get_domain_name(selected_ip))
        filtered_data = frame_data['frame1']['dst_counts'][frame_data['frame1']['dst_counts']['dst'] == selected_ip]
        ax.scatter(filtered_data['dstport'], filtered_data['count'], s=100)
        ax.set_xlabel('Destination Port (dstport)')
        ax.set_ylabel('Count')
        ax.set_title(f'Count vs dstport for IP: {selected_ip} (Frame 1)')
        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
    canvas.draw()

combo.bind("<<ComboboxSelected>>", update_plot)

# Create second frame (Toplevel window)
second_window = tk.Toplevel()
second_window.title("Port vs Domain Count")
second_window.geometry("1200x600")

# Define dynamic date range for second frame
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
min_date_str_frame2 = min_date.strftime('%B %d, %Y')
max_date_str_frame2 = max_date.strftime('%B %d, %Y')
calendar_label_frame2 = f"Select Date ({min_date_str_frame2} to {max_date_str_frame2})"

# Create frame to hold both plots side by side
plot_frame = tk.Frame(second_window)
plot_frame.pack(pady=10, fill="both", expand=True)

# Create subframes for bar plot and pie chart
bar_frame = tk.Frame(plot_frame)
bar_frame.pack(side=tk.LEFT, padx=10, fill="both", expand=True)

pie_frame = tk.Frame(plot_frame)
pie_frame.pack(side=tk.RIGHT, padx=10, fill="both", expand=True)

# Create date entry widget for second frame (above bar plot)
tk.Label(bar_frame, text=calendar_label_frame2, font=("Times New Roman", 12, "bold")).pack(pady=5)
date_entry_frame2 = DateEntry(bar_frame, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date, maxdate=max_date,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame2.pack(pady=5)

# Button to fetch data for second frame (above bar plot)
def on_date_submit_frame2():
    date_str = date_entry_frame2.get().strip()
    if not date_str:
        messagebox.showerror("Invalid Date", "Please select a date from the calendar first.")
        return
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        date_str_ymd = selected_date.strftime("%Y%m%d")
        if selected_date < min_date:
            messagebox.showerror("Invalid Date", f"Selected date is before {min_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        if selected_date > max_date:
            messagebox.showerror("Invalid Date", f"Selected date is after {max_date.strftime('%B %d, %Y')}. Please choose a date within the last 10 days.")
            return
        fetch_data_frame2(date_str_ymd)
        port_combo.set("Select dstport")
        update_plots()
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}' (Frame 2). Error: {e}")

tk.Button(bar_frame, text="Get Date", command=on_date_submit_frame2).pack(pady=5)

# Create dropdown (Combobox) for second frame (above pie chart)
tk.Label(pie_frame, text="Select dstport:", font=("Times New Roman", 12)).pack(pady=5)
port_combo = ttk.Combobox(pie_frame, values=frame_data['frame2']['unique_dstports'], state='readonly', width=30)
port_combo.pack(pady=5)
port_combo.set("Select dstport")

# Create Matplotlib figures for bar plot and pie chart
fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
canvas_bar = FigureCanvasTkAgg(fig_bar, master=bar_frame)
canvas_bar.get_tk_widget().pack(pady=10, fill="both", expand=True)

fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
canvas_pie = FigureCanvasTkAgg(fig_pie, master=pie_frame)
canvas_pie.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Function to update both bar plot and pie chart
def update_plots(event=None):
    ax_bar.clear()
    if frame_data['frame2']['dst_counts'] is not None:
        top_20 = frame_data['frame2']['dst_counts'].groupby('dstport').sum().nlargest(20, 'count')
        if not top_20.empty:
            ax_bar.bar(top_20.index, top_20['count'], color='purple')
            ax_bar.set_xlabel('Destination Port (dstport)')
            ax_bar.set_ylabel('Count of Hits')
            ax_bar.set_title(f'Top 20 dstport Counts for {date_entry_frame2.get()}')
            ax_bar.tick_params(axis='x', rotation=45)
        else:
            ax_bar.text(0.5, 0.5, 'No data available for bar chart', horizontalalignment='center', verticalalignment='center')
    else:
        ax_bar.text(0.5, 0.5, 'No data available for bar chart', horizontalalignment='center', verticalalignment='center')
    fig_bar.tight_layout()
    canvas_bar.draw()

    ax_pie.clear()
    if frame_data['frame2']['dst_counts'] is not None and port_combo.get() != "Select dstport":
        selected_port = port_combo.get()
        filtered_data = frame_data['frame2']['dst_counts'][frame_data['frame2']['dst_counts']['dstport'] == selected_port]
        top_20_ips = filtered_data.groupby('dst').sum().nlargest(20, 'count').reset_index()
        
        ip_from_df = [ip for ip in top_20_ips['dst'].tolist() if isinstance(ip, str) and ip]
        domains = {}
        if ip_from_df:
            try:
                with mysql.connector.connect(
                    host="192.168.100.25",
                    user="sysuser",
                    password="DT1Y9Q0EtBwI0",
                    database="syslog"
                ) as engine:
                    cursor = engine.cursor()
                    placeholders = ','.join(['%s'] * len(ip_from_df))
                    query = f"SELECT ip, DOMAIN FROM LOG_DNS WHERE ip IN ({placeholders})"
                    cursor.execute(query, ip_from_df)
                    existing_domains = {row[0]: row[1] for row in cursor.fetchall()}
                    for ip in ip_from_df:
                        if ip in existing_domains and existing_domains[ip]:
                            domains[ip] = existing_domains[ip]
                        else:
                            info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                            domains[ip] = info['domain']
            except mysql.connector.Error as e:
                print(f"Error querying LOG_DNS: {e}")
                for ip in ip_from_df:
                    info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                    domains[ip] = info['domain']
        else:
            for ip in top_20_ips['dst']:
                info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                domains[ip] = info['domain']
        
        domain_counts = {}
        for ip, domain in domains.items():
            if domain:
                count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                domain_counts[domain] = domain_counts.get(domain, 0) + count
        
        if domain_counts:
            labels = list(domain_counts.keys())
            sizes = list(domain_counts.values())
            total = sum(sizes)
            percentages = [size / total * 100 for size in sizes]
            ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=60)
            ax_pie.axis('equal')
            ax_pie.set_title(f'Percentage of Domain Hits for dstport {selected_port} on {date_entry_frame2.get()}')
        else:
            ax_pie.text(0.5, 0.5, 'No valid domain data available', horizontalalignment='center', verticalalignment='center')
    else:
        ax_pie.text(0.5, 0.5, 'Please Select a port first, to see its PieChart', horizontalalignment='center', verticalalignment='center')
    
    fig_pie.tight_layout()
    canvas_pie.draw()
    
    # Insert data into PLOT_DATA only when a port is selected
    if port_combo.get() != "Select dstport" and date_entry_frame2.get().strip():
        date_str = date_entry_frame2.get().replace("-", "")
        insert_plot_data(date_str, port_combo.get())

port_combo.bind("<<ComboboxSelected>>", update_plots)

# Fetch initial data for today's date in both frames and update charts
fetch_data_frame1(today.strftime("%Y%m%d"))
update_plot(None)
fetch_data_frame2(today.strftime("%Y%m%d"))
update_plots()

root.mainloop()