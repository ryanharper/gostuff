import re
import argparse
import sys

class AlloyToVectorMigrator:
    def __init__(self, alloy_config: str):
        self.alloy_config = alloy_config
        self.vector_config = {
            "sources": {},
            "transforms": {},
            "sinks": {}
        }
        
    def migrate(self) -> str:
        """Executes the extraction and generates the Vector TOML."""
        self._map_log_sources()
        self._map_log_transforms()
        self._map_log_sinks()
        self._map_metric_sources()
        self._map_metric_sinks()
        return self._generate_toml()

    def _map_log_sources(self):
        """Maps Alloy local.file_match to Vector file sources."""
        pattern = r'local\.file_match\s+"([^"]+)".*?__path__"\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        for match in matches:
            label, path = match.groups()
            self.vector_config["sources"][f"logs_{label}"] = {
                "type": '"file"',
                "include": f'["{path}"]'
            }

    def _map_log_transforms(self):
        """
        Extracts stage.regex from loki.process and converts to Vector VRL.
        Cleans up Alloy's double-escaped HCL regex into Vector raw strings.
        """
        # Finds: stage.regex { expression = "(?P<time>\\d+)..." }
        pattern = r'stage\.regex\s*\{.*?expression\s*=\s*"([^"]+)".*?\}'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        log_inputs = [f'"{k}"' for k in self.vector_config["sources"].keys() if k.startswith("logs_")]
        inputs_str = f"[{', '.join(log_inputs)}]" if log_inputs else '["<TODO: Add Inputs>"]'

        for i, match in enumerate(matches):
            raw_expression = match.group(1)
            # Convert River/HCL double-escapes (\\d) to standard regex (\d) for VRL
            cleaned_regex = raw_expression.replace('\\\\', '\\')
            
            # Create a VRL remap transform
            vrl_source = f"'''\n. |= parse_regex!(.message, r'{cleaned_regex}')\n'''"
            
            self.vector_config["transforms"][f"parse_regex_{i}"] = {
                "type": '"remap"',
                "inputs": inputs_str,
                "source": vrl_source
            }

    def _map_log_sinks(self):
        """Maps Alloy loki.write to Vector loki sinks."""
        pattern = r'loki\.write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        # If we created transforms, route from the transform to the sink. 
        # Otherwise, route directly from the source.
        if self.vector_config["transforms"]:
            inputs = [f'"{k}"' for k in self.vector_config["transforms"].keys()]
        else:
            inputs = [f'"{k}"' for k in self.vector_config["sources"].keys() if k.startswith("logs_")]
            
        inputs_str = f"[{', '.join(inputs)}]" if inputs else '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            base_url = url.replace("/loki/api/v1/push", "").replace("/api/prom/push", "")
            
            self.vector_config["sinks"][f"loki_{label}"] = {
                "type": '"loki"',
                "inputs": inputs_str,
                "endpoint": f'"{base_url}"',
                "encoding": '{ codec = "json" }'
            }

    def _map_metric_sources(self):
        """Maps Alloy prometheus.scrape to Vector prometheus_scrape sources."""
        pattern = r'prometheus\.scrape\s+"([^"]+)".*?__address__"\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        for match in matches:
            label, address = match.groups()
            endpoint = address if address.startswith("http") else f"http://{address}/metrics"
            
            self.vector_config["sources"][f"metrics_{label}"] = {
                "type": '"prometheus_scrape"',
                "endpoints": f'["{endpoint}"]'
            }

    def _map_metric_sinks(self):
        """Maps Alloy prometheus.remote_write to Vector prometheus_remote_write sinks."""
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
        if self.vector_config["sources"]:
            for name, config in self.vector_config["sources"].items():
                lines.append(f"[sources.{name}]")
                for key, val in config.items():
                    lines.append(f"{key} = {val}")
                lines.append("")
            
        # Write Transforms
        if self.vector_config["transforms"]:
            for name, config in self.vector_config["transforms"].items():
                lines.append(f"[transforms.{name}]")
                for key, val in config.items():
                    lines.append(f"{key} = {val}")
                lines.append("")

        # Write Sinks
        if self.vector_config["sinks"]:
            for name, config in self.vector_config["sinks"].items():
                lines.append(f"[sinks.{name}]")
                for key, val in config.items():
                    lines.append(f"{key} = {val}")
                lines.append("")
            
        return "\n".join(lines).strip()

def main():
    parser = argparse.ArgumentParser(description="Transpile Grafana Alloy configs to Datadog Vector TOML.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input Alloy configuration file")
    parser.add_argument("-o", "--output", required=True, help="Path to the output Vector TOML file")
    
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            alloy_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    migrator = AlloyToVectorMigrator(alloy_content)
    vector_toml = migrator.migrate()

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(vector_toml)
        print(f"Success: Migrated configuration written to {args.output}")
    except Exception as e:
        print(f"Error writing to output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
