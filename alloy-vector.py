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
        self.log_pipeline_tails = []
        
    def migrate(self) -> str:
        self._map_log_sources()
        self._map_log_transforms()
        self._map_log_sinks()
        self._map_metric_sources()
        self._map_metric_sinks()
        return self._generate_toml()

    def _map_log_sources(self):
        if "local.file_match" not in self.alloy_config:
            return
            
        blocks = self.alloy_config.split("local.file_match")[1:]
        
        for block in blocks:
            name_match = re.search(r'^\s*"([^"]+)"', block)
            if not name_match:
                continue
            label = name_match.group(1)
            source_name = "logs_" + label
            
            paths = re.findall(r'(?:__path__|"__path__")\s*=\s*"([^"]+)"', block)
            if not paths:
                continue
                
            paths_str = ", ".join(['"{}"'.format(p) for p in set(paths)])
            
            self.vector_config["sources"][source_name] = {
                "type": '"file"',
                "include": "[{}]".format(paths_str)
            }
            
            label_matches = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*"([^"]+)"', block)
            custom_labels = {k: v for k, v in label_matches if k not in ["__path__", "url", "expression"]}
            
            if custom_labels:
                transform_name = "add_labels_" + label
                vrl_lines = ['.{} = "{}"'.format(k, v) for k, v in custom_labels.items()]
                vrl_source = "'''\n" + "\n".join(vrl_lines) + "\n'''"
                
                self.vector_config["transforms"][transform_name] = {
                    "type": '"remap"',
                    "inputs": '["{}"]'.format(source_name),
                    "source": vrl_source
                }
                self.log_pipeline_tails.append(transform_name)
            else:
                self.log_pipeline_tails.append(source_name)

    def _map_log_transforms(self):
        pattern = r'stage\.regex\s*\{.*?expression\s*=\s*"([^"]+)".*?\}'
        matches = list(re.finditer(pattern, self.alloy_config, re.DOTALL))
        
        if not matches or not self.log_pipeline_tails:
            return

        formatted_tails = ['"{}"'.format(t) for t in self.log_pipeline_tails]
        inputs_str = "[" + ", ".join(formatted_tails) + "]"
        
        for i, match in enumerate(matches):
            raw_expression = match.group(1)
            cleaned_regex = raw_expression.replace('\\\\', '\\')
            
            # Using basic concatenation to keep the parser happy
            vrl_source = "'''\n. |= parse_regex!(.message, r'" + cleaned_regex + "')\n'''"
            transform_name = "parse_regex_{}".format(i)
            
            self.vector_config["transforms"][transform_name] = {
                "type": '"remap"',
                "inputs": inputs_str,
                "source": vrl_source
            }
            
            self.log_pipeline_tails = [transform_name]

    def _map_log_sinks(self):
        pattern = r'loki\.write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        formatted_tails = ['"{}"'.format(t) for t in self.log_pipeline_tails]
        if formatted_tails:
            inputs_str = "[" + ", ".join(formatted_tails) + "]"
        else:
            inputs_str = '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            base_url = url.replace("/loki/api/v1/push", "").replace("/api/prom/push", "")
            
            self.vector_config["sinks"]["loki_" + label] = {
                "type": '"loki"',
                "inputs": inputs_str,
                "endpoint": '"{}"'.format(base_url),
                "encoding": '{ codec = "json" }'
            }

    def _map_metric_sources(self):
        pattern = r'prometheus\.scrape\s+"([^"]+)".*?__address__"\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        for match in matches:
            label, address = match.groups()
            endpoint = address if address.startswith("http") else "http://{}/metrics".format(address)
            
            self.vector_config["sources"]["metrics_" + label] = {
                "type": '"prometheus_scrape"',
                "endpoints": '["{}"]'.format(endpoint)
            }

    def _map_metric_sinks(self):
        pattern = r'prometheus\.remote_write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        metric_inputs = ['"{}"'.format(k) for k in self.vector_config["sources"].keys() if k.startswith("metrics_")]
        if metric_inputs:
            inputs_str = "[" + ", ".join(metric_inputs) + "]"
        else:
            inputs_str = '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            self.vector_config["sinks"]["prom_write_" + label] = {
                "type": '"prometheus_remote_write"',
                "inputs": inputs_str,
                "endpoint": '"{}"'.format(url)
            }

    def _generate_toml(self) -> str:
        lines = []
        
        if self.vector_config["sources"]:
            for name, config in self.vector_config["sources"].items():
                lines.append(f"[sources.{name}]")
                for key, val in config.items():
                    lines.append(f"{key} = {val}")
                lines.append("")
            
        if self.vector_config["transforms"]:
            for name, config in self.vector_config["transforms"].items():
                lines.append(f"[transforms.{name}]")
                for key, val in config.items():
                    lines.append(f"{key} = {val}")
                lines.append("")

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
