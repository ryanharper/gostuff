import pandas as pd
import glob
import os
import re

data_dir = r'C:\Temp\InventoryData'

def analyze_csvs(file_pattern, output_name, group_cols):
    """Generic function to aggregate CSVs and calculate presence percentage."""
    files = glob.glob(os.path.join(data_dir, file_pattern))
    if not files:
        print(f"No files found for pattern: {file_pattern}")
        return
    
    # Load and combine data
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    
    # Calculate frequency per host
    baseline = df.groupby(group_cols).size().reset_index(name='HostCount')
    total_hosts = len(files)
    baseline['PresencePercentage'] = (baseline['HostCount'] / total_hosts) * 100
    
    baseline.to_csv(output_name, index=False)
    print(f"Baseline report saved to {output_name}")

def parse_errors():
    error_file = os.path.join(data_dir, "ErrorLog.txt")
    if not os.path.exists(error_file):
        return

    error_data = []
    pattern = re.compile(r"^(?P<Hostname>.*?) : (?P<Status>.*?) - (?P<Issue>.*)$")

    with open(error_file, 'r') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                error_data.append(match.groupdict())

    if error_data:
        pd.DataFrame(error_data).to_csv("Host_Connection_Issues.csv", index=False)
        print("Issue report saved to Host_Connection_Issues.csv")

if __name__ == "__main__":
    # 1. Analyze Services
    analyze_csvs("*_Services.csv", "Service_Baseline_Report.csv", ['Name', 'DisplayName'])
    
    # 2. Analyze Processes
    # Grouping by 'Name' to see how often specific executables are running across the fleet
    analyze_csvs("*_Processes.csv", "Process_Baseline_Report.csv", ['Name'])
    
    # 3. Parse Errors
    parse_errors()
