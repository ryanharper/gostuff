import re

class AlloyToVectorMigrator:
    def __init__(self, alloy_config: str):
        self.alloy_config = alloy_config
        self.vector_config = {
            "sources": {},
            "sinks": {}
        }
        
    def migrate(self) -> str:
        """Executes the extraction and generates the Vector TOML."""
        self._map_log_sources()
        self._map_log_sinks()
        self._map_metric_sources()
        self._map_metric_sinks()
        return self._generate_toml()

    def _map_log_sources(self):
        """Maps Alloy local.file_match to Vector file sources."""
        # Finds: local.file_match "name" { ... "__path__" = "/var/log/*.log" ... }
        pattern = r'local\.file_match\s+"([^"]+)".*?__path__"\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        for match in matches:
            label, path = match.groups()
            self.vector_config["sources"][f"logs_{label}"] = {
                "type": '"file"',
                "include": f'["{path}"]'
            }

    def _map_log_sinks(self):
        """Maps Alloy loki.write to Vector loki sinks."""
        # Finds: loki.write "name" { ... url = "http://endpoint" ... }
        pattern = r'loki\.write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        # Collect all parsed log sources to route to this sink
        log_inputs = [f'"{k}"' for k in self.vector_config["sources"].keys() if k.startswith("logs_")]
        inputs_str = f"[{', '.join(log_inputs)}]" if log_inputs else '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            # Vector expects the base endpoint for Loki, not the full push path
            base_url = url.replace("/loki/api/v1/push", "").replace("/api/prom/push", "")
            
            self.vector_config["sinks"][f"loki_{label}"] = {
                "type": '"loki"',
                "inputs": inputs_str,
                "endpoint": f'"{base_url}"',
                "encoding": '{ codec = "json" }'
            }

    def _map_metric_sources(self):
        """Maps Alloy prometheus.scrape to Vector prometheus_scrape sources."""
        # Finds: prometheus.scrape "name" { ... "__address__" = "localhost:9090" ... }
        pattern = r'prometheus\.scrape\s+"([^"]+)".*?__address__"\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        for match in matches:
            label, address = match.groups()
            # Ensure the address has a protocol
            endpoint = address if address.startswith("http") else f"http://{address}/metrics"
            
            self.vector_config["sources"][f"metrics_{label}"] = {
                "type": '"prometheus_scrape"',
                "endpoints": f'["{endpoint}"]'
            }

    def _map_metric_sinks(self):
        """Maps Alloy prometheus.remote_write to Vector prometheus_remote_write sinks."""
        # Finds: prometheus.remote_write "name" { ... url = "http://endpoint" ... }
        pattern = r'prometheus\.remote_write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        metric_inputs = [f'"{k}"' for k in self.vector_config["sources"].keys() if k.startswith("metrics_")]
        inputs_str = f"[{', '.join(metric_inputs)}]" if metric_inputs else '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            self.vector_config["sinks"][f"prom_write_{label}"] = {
                "type": '"prometheus_remote_write"',
                "inputs": inputs_str,
                "endpoint": f'"{url}"'
            }

    def _generate_toml(self) -> str:
        """Formats the parsed dictionary into a Vector TOML string."""
        lines = []
        
        # Write Sources
        for name, config in self.vector_config["sources"].items():
            lines.append(f"[sources.{name}]")
            for key, val in config.items():
                lines.append(f"{key} = {val}")
            lines.append("")
            
        # Write Sinks
        for name, config in self.vector_config["sinks"].items():
            lines.append(f"[sinks.{name}]")
            for key, val in config.items():
                lines.append(f"{key} = {val}")
            lines.append("")
            
        return "\n".join(lines).strip()

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    alloy_input = """
    local.file_match "app_logs" {
      path_targets = [{"__path__" = "/var/log/app/*.log"}]
    }

    loki.write "central_loki" {
      endpoint {
        url = "http://loki:3100/loki/api/v1/push"
      }
    }

    prometheus.scrape "node_exporter" {
      targets = [{"__address__" = "localhost:9100"}]
      forward_to = [prometheus.remote_write.mimir.receiver]
    }

    prometheus.remote_write "mimir" {
      endpoint {
        url = "http://mimir:9009/api/v1/push"
      }
    }
    """

    migrator = AlloyToVectorMigrator(alloy_input)
    vector_toml = migrator.migrate()
    
    print("### Vector Configuration (TOML) ###\n")
    print(vector_toml)
