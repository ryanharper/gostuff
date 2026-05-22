import pandas as pd
import glob
import os
import re

data_dir = r'C:\Temp\InventoryData'

# --- 1. Process Service & Process Inventory ---
def process_inventories():
    service_files = glob.glob(os.path.join(data_dir, "*_Services.csv"))
    # Load all, drop duplicates if any
    df_services = pd.concat((pd.read_csv(f) for f in service_files), ignore_index=True)
    
    # Generate the baseline report
    baseline = df_services.groupby(['Name', 'DisplayName']).size().reset_index(name='HostCount')
    baseline['PresencePercentage'] = (baseline['HostCount'] / len(service_files)) * 100
    
    baseline.to_csv("Master_Service_Inventory.csv", index=False)
    print("Master inventory saved to Master_Service_Inventory.csv")

# --- 2. Parse the Error Log ---
def parse_errors():
    error_file = os.path.join(data_dir, "ErrorLog.txt")
    if not os.path.exists(error_file):
        print("No error log found to parse.")
        return

    error_data = []
    # Pattern to capture Hostname and the error message
    # Expecting format: "Hostname : Status - Error Message"
    pattern = re.compile(r"^(?P<Hostname>.*?) : (?P<Status>.*?) - (?P<Issue>.*)$")

    with open(error_file, 'r') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                error_data.append(match.groupdict())

    if error_data:
        df_errors = pd.DataFrame(error_data)
        df_errors.to_csv("Host_Connection_Issues.csv", index=False)
        print("Issue report saved to Host_Connection_Issues.csv")

# Run the tasks
if __name__ == "__main__":
    process_inventories()
    parse_errors()
