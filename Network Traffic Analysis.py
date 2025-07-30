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
import numpy as np

# Tries to get the domain name (like google.com) from an IP address. If it fails, returns the IP.
def get_domain_name(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, OSError):
        return ip_address

# Gets info about an IP (like country, provider) from an API and saves it to LOG_DNS table if not already there.
# Uses the API to fetch details, then checks if the IP is in the database. If not, it adds the info.
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

# Stores data for two windows (frames): one for IP scatter plot, one for port/domain charts.
frame_data = {
    'frame1': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': []},
    'frame2': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': [], 'full_dst_counts': None}
}

# Checks if data exists in PLOT_DATA table for a date and type (port or domain).
# Queries the table and returns a DataFrame with port or domain counts if found, else None.
def check_plot_data(date_str, log_type, port=None):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            log_id = f"log_{date_str}"
            if log_type == "PORT":
                query = "SELECT PORT, COUNT FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s"
                cursor.execute(query, (log_id, "PORT"))
                results = cursor.fetchall()
                if results:
                    df = pd.DataFrame(results, columns=['dstport', 'count'])
                    df['count'] = pd.to_numeric(df['count'], errors='coerce')  # Convert to Numeric
                    return df
                return None
            elif log_type == "DOMAIN" and port:
                query = "SELECT DOMAIN, COUNT FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s"
                cursor.execute(query, (log_id, "DOMAIN", port))
                results = cursor.fetchall()
                if results:
                    df = pd.DataFrame(results, columns=['domain', 'count'])
                    df['count'] = pd.to_numeric(df['count'], errors='coerce')  # Convert to numeric
                    return df
                return None
    except mysql.connector.Error as e:
        print(f"Error checking PLOT_DATA for {date_str}: {e}")
        return None

# Fetches data for the first window (scatter plot) from the main database.
# Calls update_frame_data to get all data from log_{date_str} table.
def fetch_data_frame1(date_str):
    update_frame_data('frame1', date_str, "SELECT * FROM log_{date_str}")

# Fetches data for the second window (bar and pie charts) from the main database.
# Queries log_{date_str} for port and IP counts, stores them, and updates the port dropdown.
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
            if df.empty:
                print(f"No data found in log_{date_str}")
            else:
                df['count'] = pd.to_numeric(df['count'], errors='coerce')  # Ensure count is numeric
            frame_data['frame2']['dst_counts'] = df
            frame_data['frame2']['full_dst_counts'] = df.copy()  # Store full data for dropdown
            frame_data['frame2']['unique_dstports'] = sorted(df['dstport'].unique()) if not df.empty else []
        
        port_combo['values'] = frame_data['frame2']['unique_dstports']
        port_combo.set("Select dstport" if frame_data['frame2']['unique_dstports'] else "No dstports available")
        
    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching data for {date_str}: {e}")
        frame_data['frame2']['dst_counts'] = None
        frame_data['frame2']['full_dst_counts'] = None
        frame_data['frame2']['unique_dstports'] = []

# Updates data for a frame (first or second window) from the database.
# Fetches data from log_{date_str}, processes it (groups by IP/port for frame1), and updates dropdowns.
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
                df['count'] = pd.to_numeric(df.groupby(['dst', 'dstport']).size(), errors='coerce').reset_index(name='count')['count']
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

# Saves or updates the top 20 ports and their counts in PLOT_DATA table.
# Gets top 20 ports from frame2 data, checks if they exist in PLOT_DATA, and inserts or updates them.
def insert_top_20_ports(date_str):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            counter = 0  # Counter to ensure unique IDs within the same microsecond
            today_str = datetime.today().strftime("%Y%m%d")
            log_id = f"log_{date_str}"

            if frame_data['frame2']['full_dst_counts'] is not None:  # Use full data for insertion
                top_20_ports = frame_data['frame2']['full_dst_counts'].groupby('dstport')['count'].sum().nlargest(20)

                # Check existing ports for the given LOG_ID
                cursor.execute(
                    "SELECT PORT, COUNT, ID FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s",
                    (log_id, "PORT")
                )
                existing_ports = {row[0]: {'count': row[1], 'id': row[2]} for row in cursor.fetchall()}

                for port, count in top_20_ports.items():
                    port_str = str(port)
                    count_str = str(int(count))  # Convert to int to ensure no decimals, then to string for SQL
                    if port_str in existing_ports:
                        if date_str == today_str:  # Update only for today's date
                            update_query = """
                                UPDATE PLOT_DATA
                                SET COUNT = %s
                                WHERE ID = %s AND LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s
                            """
                            cursor.execute(update_query, (count_str, existing_ports[port_str]['id'], log_id, "PORT", port_str))
                    else:
                        unique_id = int(time.time() * 1000000) + counter
                        counter += 1
                        insert_query = """
                            INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (unique_id, log_id, "PORT", "N/A", port_str, count_str))

                engine.commit()
    except mysql.connector.Error as e:
        print(f"Error inserting/updating top 20 ports into PLOT_DATA: {e}")

# Saves or updates domain counts for a specific port in PLOT_DATA table.
# Filters IPs for the port, gets their domains, aggregates counts, and inserts or updates in PLOT_DATA.
def insert_specific_port_data(date_str, selected_port):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            counter = 0  # Counter to ensure unique IDs within the same microsecond
            today_str = datetime.today().strftime("%Y%m%d")
            log_id = f"log_{date_str}"

            if frame_data['frame2']['full_dst_counts'] is not None and 'dst' in frame_data['frame2']['full_dst_counts'].columns:
                filtered_data = frame_data['frame2']['full_dst_counts'][frame_data['frame2']['full_dst_counts']['dstport'] == selected_port]
                top_20_ips = filtered_data.groupby('dst')['count'].sum().nlargest(20).reset_index()
                ip_from_df = [ip for ip in top_20_ips['dst'].tolist() if isinstance(ip, str) and ip]

                # Fetch domains for IPs
                domains = {}
                if ip_from_df:
                    placeholders = ','.join(['%s'] * len(ip_from_df))
                    cursor.execute(f"SELECT ip, DOMAIN FROM LOG_DNS WHERE ip IN ({placeholders})", ip_from_df)
                    existing_ip_domains = {row[0]: row[1] for row in cursor.fetchall()}
                    for ip in ip_from_df:
                        if ip in existing_ip_domains and existing_ip_domains[ip]:
                            domains[ip] = existing_ip_domains[ip]
                        else:
                            info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                            domains[ip] = info['domain']

                # Aggregate counts by domain
                domain_counts = {}
                for ip, domain in domains.items():
                    if domain:
                        count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                        domain_counts[domain] = domain_counts.get(domain, 0) + count

                # Fetch existing domains for the given LOG_ID and PORT
                cursor.execute(
                    "SELECT DOMAIN, COUNT, ID FROM PLOT_DATA WHERE LOG_ID = %s AND PORT = %s AND LOG_TYPE = %s",
                    (log_id, selected_port, "DOMAIN")
                )
                existing_domains = {row[0]: {'count': row[1], 'id': row[2]} for row in cursor.fetchall()}

                # Insert or update domain data
                for domain, count in domain_counts.items():
                    count_str = str(int(count))  # Convert to int to ensure no decimals, then to string for SQL
                    if domain in existing_domains:
                        if date_str == today_str:  # Update only for today's date
                            update_query = """
                                UPDATE PLOT_DATA
                                SET COUNT = %s
                                WHERE ID = %s AND LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s AND DOMAIN = %s
                            """
                            cursor.execute(update_query, (count_str, existing_domains[domain]['id'], log_id, "DOMAIN", selected_port, domain))
                    else:
                        unique_id = int(time.time() * 1000000) + counter
                        counter += 1
                        insert_query = """
                            INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (unique_id, log_id, "DOMAIN", domain, selected_port, count_str))

                engine.commit()
    except mysql.connector.Error as e:
        print(f"Error inserting/updating specific port data into PLOT_DATA: {e}")

# Creates the first window for the IP scatter plot.
root = tk.Tk()
root.title("Destination IP Scatter Plot")
root.geometry("800x600")

# Sets date range for the first window (last 10 days).
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
min_date_str = min_date.strftime('%B %d, %Y')
max_date_str = max_date.strftime('%B %d, %Y')
calendar_label_frame1 = f"Select Date ({min_date_str} to {max_date_str})"

# Adds a date picker to the first window for selecting a date.
tk.Label(root, text=calendar_label_frame1, font=("Times New Roman", 12, "bold")).pack(pady=10)
date_entry_frame1 = DateEntry(root, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date, maxdate=max_date,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame1.pack(pady=5)

# Fetches data for the first window when a date is selected.
# Checks if the date is valid, then calls fetch_data_frame1 and updates the plot.
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

# Adds a dropdown to select an IP in the first window.
tk.Label(root, text="Select Destination IP:", font=("Times New Roman", 12)).pack(pady=10)
combo = ttk.Combobox(root, values=frame_data['frame1']['unique_ips'], state='readonly', width=30)
combo.pack(pady=5)
combo.set("Select an IP")

# Sets up the scatter plot area for the first window.
fig, ax = plt.subplots(figsize=(6, 4))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Updates the scatter plot when an IP is selected.
# Shows a plot of ports vs. counts for the chosen IP.
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

# Creates the second window for port and domain charts.
second_window = tk.Toplevel()
second_window.title("Port vs Domain Count")
second_window.geometry("1200x600")

# Sets date range for the second window (last 10 days).
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)
min_date_str_frame2 = min_date.strftime('%B %d, %Y')
max_date_str_frame2 = max_date.strftime('%B %d, %Y')
calendar_label_frame2 = f"Select Date ({min_date_str_frame2} to {max_date_str_frame2})"

# Creates a frame to hold bar and pie charts side by side.
plot_frame = tk.Frame(second_window)
plot_frame.pack(pady=10, fill="both", expand=True)

# Creates subframes for bar plot (left) and pie chart (right).
bar_frame = tk.Frame(plot_frame)
bar_frame.pack(side=tk.LEFT, padx=10, fill="both", expand=True)

pie_frame = tk.Frame(plot_frame)
pie_frame.pack(side=tk.RIGHT, padx=10, fill="both", expand=True)

# Adds a date picker to the second window for selecting a date.
tk.Label(bar_frame, text=calendar_label_frame2, font=("Times New Roman", 12, "bold")).pack(pady=5)
date_entry_frame2 = DateEntry(bar_frame, width=30, date_pattern="yyyy-mm-dd",
                              mindate=min_date, maxdate=max_date,
                              year=today.year, month=today.month, day=today.day)
date_entry_frame2.pack(pady=5)

# Fetches data for the second window when a date is selected.
# Checks PLOT_DATA; if not found or today, fetches from main database and updates PLOT_DATA.
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
        
        # Check PLOT_DATA for port data
        port_data = check_plot_data(date_str_ymd, "PORT")
        today_str = datetime.today().strftime("%Y%m%d")
        
        if port_data is not None and date_str_ymd != today_str:
            print(f"Data is already in PLOT_DATA for {date_str_ymd}, fetching from PLOT_DATA")
            frame_data['frame2']['dst_counts'] = port_data
            # Use full_dst_counts for dropdown if available
            if frame_data['frame2']['full_dst_counts'] is not None:
                frame_data['frame2']['unique_dstports'] = sorted(frame_data['frame2']['full_dst_counts']['dstport'].unique())
            else:
                frame_data['frame2']['unique_dstports'] = sorted(port_data['dstport'].unique())
            port_combo['values'] = frame_data['frame2']['unique_dstports']
            port_combo.set("Select dstport" if frame_data['frame2']['unique_dstports'] else "No dstports available")
        else:
            print(f"The required data is not in PLOT_DATA for {date_str_ymd}, fetching from log_{date_str_ymd}")
            fetch_data_frame2(date_str_ymd)
            insert_top_20_ports(date_str_ymd)  # Insert or update top 20 ports
        
        port_combo.set("Select dstport")
        update_plots()
    except ValueError as e:
        messagebox.showerror("Invalid Date", f"Failed to process date '{date_str}' (Frame 2). Error: {e}")

tk.Button(bar_frame, text="Get Date", command=on_date_submit_frame2).pack(pady=5)

# Adds a dropdown to select a port for the pie chart in the second window.
tk.Label(pie_frame, text="Select dstport:", font=("Times New Roman", 12)).pack(pady=5)
port_combo = ttk.Combobox(pie_frame, values=frame_data['frame2']['unique_dstports'], state='readonly', width=30)
port_combo.pack(pady=5)
port_combo.set("Select dstport")

# Sets up the bar plot and pie chart areas for the second window.
fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
canvas_bar = FigureCanvasTkAgg(fig_bar, master=bar_frame)
canvas_bar.get_tk_widget().pack(pady=10, fill="both", expand=True)

fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
canvas_pie = FigureCanvasTkAgg(fig_pie, master=pie_frame)
canvas_pie.get_tk_widget().pack(pady=10, fill="both", expand=True)

# Updates the bar and pie charts in the second window.
# Bar chart shows top 20 ports; pie chart shows domain percentages for a selected port.
def update_plots(event=None):
    ax_bar.clear()
    if frame_data['frame2']['dst_counts'] is not None:
        top_20 = frame_data['frame2']['dst_counts'].groupby('dstport')['count'].sum().nlargest(20)
        if not top_20.empty:
            ax_bar.bar(top_20.index, top_20.values, color='purple')
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
        date_str_ymd = date_entry_frame2.get().replace("-", "")
        today_str = datetime.today().strftime("%Y%m%d")
        
        # Check PLOT_DATA for domain data
        domain_data = check_plot_data(date_str_ymd, "DOMAIN", selected_port)
        
        if domain_data is not None and date_str_ymd != today_str:
            print(f"Domain data is already in PLOT_DATA for port {selected_port} on {date_str_ymd}, fetching from PLOT_DATA")
            domain_counts = dict(zip(domain_data['domain'], domain_data['count']))
        else:
            print(f"Domain data is not in PLOT_DATA for port {selected_port} on {date_str_ymd}, fetching from log_{date_str_ymd}")
            if frame_data['frame2']['full_dst_counts'] is not None and 'dst' in frame_data['frame2']['full_dst_counts'].columns:
                filtered_data = frame_data['frame2']['full_dst_counts'][frame_data['frame2']['full_dst_counts']['dstport'] == selected_port]
                if not filtered_data.empty:
                    top_20_ips = filtered_data.groupby('dst')['count'].sum().nlargest(20).reset_index()
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
                    # Insert or update specific port data
                    insert_specific_port_data(date_str_ymd, selected_port)
                else:
                    domain_counts = {}
            else:
                domain_counts = {}
        
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

port_combo.bind("<<ComboboxSelected>>", update_plots)

# Fetches initial data for today's date for both windows and updates their charts.
fetch_data_frame1(today.strftime("%Y%m%d"))
update_plot(None)
fetch_data_frame2(today.strftime("%Y%m%d"))
update_plots()

root.mainloop()