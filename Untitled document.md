# **Grafana Alloy Enterprise Implementation Plan**

**Document Status:** DRAFT

**Target Architecture:** Grafana Alloy (LGTM Stack)

**Scope:** OS, Databases, Hypervisors, Configuration Management

## **Executive Summary**

This document outlines the architectural shift from legacy, static telemetry agents to a dynamic, GitOps-driven deployment using **Grafana Alloy**. By decoupling binary deployment (via SCCM/Satellite) from configuration management (via Git), we enable hot-reloading, eliminate agent sprawl, and centralize our telemetry pipelines for OS, Hypervisor, and Database workloads.

## **Phase 1: Configuration & Architecture Strategy**

### **1.1 Hierarchical Configuration Model**

To manage fleet variations without duplicating code, we utilize a cascading configuration model. Configurations are merged in memory at runtime, with higher-specificity layers overriding base layers.

* **Layer 1 (Base):** Global defaults applied to all instances.  
* **Layer 2 (Environment):** Dev, UAT, Prod specific overrides.  
* **Layer 3 (Application):** Workload-specific modules (e.g., IIS, PostgreSQL).  
* **Layer 4 (Host):** Emergency overrides specific to a single hostname.

🖼️ **\[Insert "Grafana Cascading Config" Diagram Here\]**

### **1.2 Dynamic GitOps vs. Static Templates**

Legacy configuration required Ansible/Chef to template monolithic .yaml or .ini files via Jinja, requiring a service restart on every change.

* **The New Approach:** Ansible deploys a minimal, static config.alloy bootstrap file. Alloy then dynamically evaluates modules from a centralized Git repository and watches local drop-folders for application-specific configurations. No service restarts are required for config updates.

🖼️ **\[Insert "Alloy Dynamic Architecture" Diagram Here\]**

**Reference Documentation:**

* [Alloy Configuration Syntax (HCL)](https://grafana.com/docs/alloy/latest/configure/)  
* [Alloy Component: import.git](https://grafana.com/docs/alloy/latest/reference/components/import.git/)  
* [Alloy Component: local.file\_match](https://grafana.com/docs/alloy/latest/reference/components/local.file_match/)

## **Phase 2: Fleet-Wide Deployment & Systems Management**

We strictly separate **Binary Deployment** (the executable) from **Configuration Deployment** (the logic). This ensures enterprise systems management tools are used for what they do best: managing software lifecycles.

### **2.1 Linux Fleet Management (Red Hat Satellite)**

* **Deployment:** Satellite Content Views push the Grafana Alloy RPM to lifecycle environments.  
* **Execution:** Systemd manages the alloy.service.  
* **Updates:** Handled via standard yum/dnf patching cycles.

### **2.2 Windows Fleet Management (SCCM / MECM)**

* **Deployment:** SCCM Application Model manages the MSI installer using detection methods.  
* **Execution:** Runs as a Windows Service (Alloy).  
* **Updates:** Pushed via Deployment Rings (Ring 0 \-\> Ring 2).

🖼️ **\[Insert "Enterprise Alloy Management" Diagram Here\]**

**Reference Documentation:**

* [Install Alloy on Linux](https://grafana.com/docs/alloy/latest/set-up/install/linux/)  
* [Install Alloy on Windows](https://grafana.com/docs/alloy/latest/set-up/install/windows/)

## **Phase 3: Workload Telemetry Implementation**

### **3.1 Native OS Telemetry (Linux & Windows)**

Alloy runs as a local agent on target VMs, replacing standalone node\_exporter, windows\_exporter, and promtail.

| OS | Metrics Component | Logs Component | Key Capabilities |
| :---- | :---- | :---- | :---- |
| **Linux** | prometheus.exporter.unix | loki.source.journal, local.file\_match | Scrapes Procfs/Sysfs. Tails binary Journald natively. |
| **Windows** | prometheus.exporter.windows | loki.source.windowsevent | Hooks into WMI, PerfMon, and Windows Event Log APIs. |

🖼️ **\[Insert "OS Level Telemetry" Diagram Here\]**

**Reference Documentation:**

* [Component: prometheus.exporter.unix](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.unix/)  
* [Component: prometheus.exporter.windows](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.windows/)  
* [Component: loki.source.windowsevent](https://grafana.com/docs/alloy/latest/reference/components/loki.source.windowsevent/)  
* [Component: loki.source.journal](https://grafana.com/docs/alloy/latest/reference/components/loki.source.journal/)

### **3.2 Database Telemetry**

Alloy natively integrates with database APIs to pull connection, locking, and performance metrics. It also tails audit, slow-query, and backup logs, effectively tracking scheduled Cron/Agent jobs.

| Database Engine | Native Metrics Component | Log / Job Integration Strategy |
| :---- | :---- | :---- |
| **Oracle** | prometheus.exporter.oracledb | Tail .trc and .aud files. prometheus.exporter.process for RMAN. |
| **PostgreSQL** | prometheus.exporter.postgres | Tail Slow Query logs. Monitor WAL archiving via textfile collector. |
| **MySQL** | prometheus.exporter.mysql | Tail General/Slow logs. Process monitoring for mysqldump. |
| **MS SQL Server** | prometheus.exporter.mssql | Integrate with Windows Event Log (Application) for SQL Server Agent backups. |

🖼️ **\[Insert "DB Workload Telemetry" Diagram Here\]**

**Reference Documentation:**

* [Component: prometheus.exporter.postgres](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.postgres/)  
* [Component: prometheus.exporter.mysql](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.mysql/)  
* [Component: prometheus.exporter.mssql](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.mssql/)  
* [Component: prometheus.exporter.process](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.process/)

### **3.3 Agentless Hypervisor Telemetry**

For virtualization platforms, Alloy acts as a centralized polling mechanism and syslog receiver, meaning no third-party software is installed directly on ESXi or AHV hosts.

* **VMware vSphere:** Alloy utilizes prometheus.exporter.vsphere to authenticate against the vCenter API (TCP 443\) to scrape Cluster, Host, Datastore, and VM-level metrics.  
* **Nutanix AHV:** Alloy uses prometheus.scrape to pull metrics from the Prism Central/Element REST APIs.  
* **Syslog Ingestion:** Alloy exposes loki.source.syslog (UDP/TCP 514\) to catch real-time system events, kernel panics, and audits pushed from the hypervisor nodes.

🖼️ **\[Insert "Hypervisor Telemetry" Diagram Here\]**

**Reference Documentation:**

* [Component: prometheus.exporter.vsphere](https://grafana.com/docs/alloy/latest/reference/components/prometheus.exporter.vsphere/)  
* [Component: loki.source.syslog](https://grafana.com/docs/alloy/latest/reference/components/loki.source.syslog/)  
* [Routing metrics: prometheus.remote\_write](https://grafana.com/docs/alloy/latest/reference/components/prometheus.remote_write/)  
* [Routing logs: loki.write](https://grafana.com/docs/alloy/latest/reference/components/loki.write/)

## **Next Steps & Action Items**

1. **Repository Setup:** Create central alloy-modules Git repository for import.git consumption.  
2. **Bootstrap Packaging:** Finalize the minimal config.alloy template for initial Ansible rollout.  
3. **Systems Management:** Work with Windows and Linux endpoint teams to configure SCCM Application detection methods and Satellite Content Views for Alloy v1.x.  
4. **Network/Firewall:** Ensure the central hypervisor Alloy instances have port 514 (Syslog) open inbound, and port 443/9440 outbound to vCenter and Prism.

