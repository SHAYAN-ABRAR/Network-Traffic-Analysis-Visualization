
import sys;

from NetworkTrafficAnalysis import insert_top_20_ports;
from portHits import insert_port_domain_hits;

if __name__ == "__main__":
    #if len(sys.argv) != 2:
        #print("Usage: python NetworkTrafficAnalysis.py <date_str>")
        
        #sys.exit(1)
    callFunct = sys.argv[1]
    date_str = sys.argv[2]
    print(f":: args : {callFunct} {date_str}")
    
    match callFunct:
        case "PORTS": #python topTwentyPorts.py "PORTS" 20250730
            print(f"date_str: {date_str}")
            insert_top_20_ports(date_str)
        case "DOMAINS": #python topTwentyPorts.py "DOMAINS" 20250730 443
            selected_port = sys.argv[3]
            insert_port_domain_hits(date_str, selected_port)

        case _:
            print(f"Invalid number of arguments or unknown parameter {callFunct}")


#python topTwentyPorts.py "PORTS" 20250802
#python topTwentyPorts.py "DOMAINS" 20250802 443
    