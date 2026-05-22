import pandas as pd
import glob
import os

data_dir = r'C:\Temp\InventoryData'

# Load all service CSVs into one list
service_files = glob.glob(os.path.join(data_dir, "*_Services.csv"))
df_services = pd.concat((pd.read_csv(f) for f in service_files), ignore_index=True)

# Analysis: Identify the baseline
# Group by Name and count how many hosts have this service
baseline = df_services.groupby(['Name', 'DisplayName']).size().reset_index(name='HostCount')

# Calculate percentage of fleet
total_hosts = len(service_files)
baseline['PresencePercentage'] = (baseline['HostCount'] / total_hosts) * 100

# Filter for "Core" services present on > 80% of machines
core_baseline = baseline[baseline['PresencePercentage'] > 80]

print("--- Potential Core Baseline Services ---")
print(core_baseline.sort_values(by='PresencePercentage', ascending=False))

# Export the analysis for review
core_baseline.to_csv("Service_Baseline_Report.csv", index=False)
