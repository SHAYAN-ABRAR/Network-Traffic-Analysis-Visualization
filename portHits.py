import sys
import pandas as pd
from sqlalchemy import create_engine
import socket
import requests
import time
from datetime import datetime  # Added missing import

# Stores data for processing (subset of frame_data from NetworkTrafficAnalysis.py)
frame_data = {
    'frame2': {'dst_counts': None, 'unique_ips': [], 'unique_dstports': [], 'full_dst_counts': None}
}

# Tries to get the domain name from an IP address. If it fails, returns the IP.
def get_domain_name(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, OSError):
        return ip_address

# Gets info about an IP from an API and saves it to LOG_DNS table if not already there.
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
            # Use SQLAlchemy for database connection
            engine = create_engine("mysql+mysqlconnector://sysuser:DT1Y9Q0EtBwI0@192.168.100.25/syslog")
            with engine.connect() as conn:
                cursor = conn.connection.cursor()  # Access raw MySQL cursor
                cursor.execute("SELECT ip FROM LOG_DNS WHERE ip = %s", (ip,))
                if cursor.fetchone() is None:
                    insert_query = """
                        INSERT INTO LOG_DNS (ID, ip, asn, NAME, DOMAIN, country_code, country, continent_code, continent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (unique_id, ip, asn, as_name, domain, country_code, country, continent_code, continent))
                    conn.connection.commit()
        except Exception as e:  # Broad exception for SQLAlchemy compatibility
            print(f"Error inserting IP info for {ip_address} into LOG_DNS: {e}")
        
        return {'domain': domain, 'data': data}
    except requests.RequestException as e:
        print(f"Error fetching IP info for {ip_address}: {e}")
        return {'domain': ip_address, 'data': None}

# Fetches data from log_{date_str} table (adapted from fetch_data_frame2).
def fetch_data_frame2(date_str):
    try:
        # Use SQLAlchemy for database connection
        engine = create_engine("mysql+mysqlconnector://sysuser:DT1Y9Q0EtBwI0@192.168.100.25/syslog")
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
            df['count'] = pd.to_numeric(df['count'], errors='coerce')
        frame_data['frame2']['dst_counts'] = df
        frame_data['frame2']['full_dst_counts'] = df.copy()
        frame_data['frame2']['unique_dstports'] = sorted(df['dstport'].unique()) if not df.empty else []
    except Exception as e:
        print(f"Error fetching data for {date_str}: {e}")
        frame_data['frame2']['dst_counts'] = None
        frame_data['frame2']['full_dst_counts'] = None
        frame_data['frame2']['unique_dstports'] = []

# Inserts or updates domain hit counts for a specific port and date in PLOT_DATA.
def insert_port_domain_hits(date_str, selected_port):
    print(f":::: insert_port_domain_hits CALLED for {date_str}, port: {selected_port}")
    fetch_data_frame2(date_str)
    try:
        # Use SQLAlchemy for database connection
        engine = create_engine("mysql+mysqlconnector://sysuser:DT1Y9Q0EtBwI0@192.168.100.25/syslog")
        with engine.connect() as conn:
            cursor = conn.connection.cursor()  # Access raw MySQL cursor
            counter = 0
            today_str = datetime.today().strftime("%Y%m%d")
            log_id = f"log_{date_str}"
            if frame_data['frame2']['full_dst_counts'] is not None and 'dst' in frame_data['frame2']['full_dst_counts'].columns:
                # Filter by the specified port
                filtered_data = frame_data['frame2']['full_dst_counts'][frame_data['frame2']['full_dst_counts']['dstport'] == selected_port]
                
                if filtered_data.empty:
                    print(f":::: No data found for port {selected_port} on {date_str}")
                    return
                
                # Get top 20 IPs by count for the port
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
                    if domain and domain != ip:  # Exclude IPs that couldn't resolve
                        count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                        domain_counts[domain] = domain_counts.get(domain, 0) + count
                
                # Get top 20 domains
                top_20_domains = pd.Series(domain_counts).nlargest(20)
                if top_20_domains.empty:
                    print(":::: No valid domain data found")
                    return
                
                # Check existing domains in PLOT_DATA for the port
                cursor.execute(
                    "SELECT DOMAIN, COUNT, ID FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s",
                    (log_id, "DOMAIN", selected_port)
                )
                existing_domains = {row[0]: {'count': row[1], 'id': row[2]} for row in cursor.fetchall()}
                
                # Insert or update domain data
                for domain, count in top_20_domains.items():
                    count_str = str(int(count))
                    if domain in existing_domains:
                        if date_str == today_str:
                            print(f":::: Updating domain {domain} for port {selected_port}")
                            update_query = """
                                UPDATE PLOT_DATA
                                SET COUNT = %s
                                WHERE ID = %s AND LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s AND DOMAIN = %s
                            """
                            cursor.execute(update_query, (count_str, existing_domains[domain]['id'], log_id, "DOMAIN", selected_port, domain))
                    else:
                        print(f":::: Inserting domain {domain} for port {selected_port}")
                        unique_id = int(time.time() * 1000000) + counter
                        counter += 1
                        insert_query = """
                            INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (unique_id, log_id, "DOMAIN", domain, selected_port, count_str))
                conn.connection.commit()
            print(":::: insert_port_domain_hits CALL END")
    except Exception as e:
        print(f"Error inserting/updating domain hits into PLOT_DATA: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python portHits.py <date_str> <port>")
        sys.exit(1)
    date_str = sys.argv[1]
    selected_port = sys.argv[2]
    print(f"date_str: {date_str}, port: {selected_port}")
    insert_port_domain_hits(date_str, selected_port)