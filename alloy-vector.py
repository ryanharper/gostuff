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
        # Tracks the current active outputs of the log pipeline 
        # so sinks and downstream transforms route correctly.
        self.log_pipeline_tails = []
        
    def migrate(self) -> str:
        self._map_log_sources()
        self._map_log_transforms()
        self._map_log_sinks()
        self._map_metric_sources()
        self._map_metric_sinks()
        return self._generate_toml()

    def _map_log_sources(self):
        """Maps Alloy local.file_match to Vector file sources. Handles bare keys and extracts labels."""
        if "local.file_match" not in self.alloy_config:
            return
            
        # Split by block to isolate environments and avoid regex bleed
        blocks = self.alloy_config.split("local.file_match")[1:]
        
        for block in blocks:
            # 1. Extract block name (e.g., "fer")
            name_match = re.search(r'^\s*"([^"]+)"', block)
            if not name_match:
                continue
            label = name_match.group(1)
            source_name = f"logs_{label}"
            
            # 2. Extract paths (handles both `__path__ = "..."` and `"__path__" = "..."`)
            paths = re.findall(r'(?:__path__|"__path__")\s*=\s*"([^"]+)"', block)
            if not paths:
                continue
                
            paths_str = ", ".join(f'"{p}"' for p in set(paths))
            
            self.vector_config["sources"][source_name] = {
                "type": '"file"',
                "include": f"[{paths_str}]"
            }
            
            # 3. Extract static labels (e.g., application_name = "testapp")
            # We filter for quoted strings to safely build VRL logic
            label_matches = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*"([^"]+)"', block)
            custom_labels = {k: v for k, v in label_matches if k not in ["__path__", "url", "expression"]}
            
            # 4. In Vector, custom labels are appended via a VRL remap transform
            if custom_labels:
                transform_name = f"add_labels_{label}"
                vrl_lines = [f'.{k} = "{v}"' for k, v in custom_labels.items()]
                vrl_source = "'''\n" + "\n".join(vrl_lines) + "\n'''"
                
                self.vector_config["transforms"][transform_name] = {
                    "type": '"remap"',
                    "inputs": f'["{source_name}"]',
                    "source": vrl_source
                }
                # The pipeline tail is now the transform, not the source
                self.log_pipeline_tails.append(transform_name)
            else:
                # The pipeline tail remains the raw source
                self.log_pipeline_tails.append(source_name)

    def _map_log_transforms(self):
        """Extracts stage.regex and maps to Vector VRL."""
        pattern = r'stage\.regex\s*\{.*?expression\s*=\s*"([^"]+)".*?\}'
        matches = list(re.finditer(pattern, self.alloy_config, re.DOTALL))
        
        if not matches or not self.log_pipeline_tails:
            return

        # Connect the inputs from wherever the pipeline currently is (sources or label transforms)
        inputs_str = f"[{', '.join(f'\"{t}\"' for t in self.log_pipeline_tails)}]"
        
        for i, match in enumerate(matches):
            raw_expression = match.group(1)
            cleaned_regex = raw_expression.replace('\\\\', '\\')
            
            vrl_source = f"'''\n. |= parse_regex!(.message, r'{cleaned_regex}')\n'''"
            transform_name = f"parse_regex_{i}"
            
            self.vector_config["transforms"][transform_name] = {
                "type": '"remap"',
                "inputs": inputs_str,
                "source": vrl_source
            }
            
            # Update the pipeline tail to point to this new regex transform
            self.log_pipeline_tails = [transform_name]

    def _map_log_sinks(self):
        """Maps Alloy loki.write to Vector loki sinks."""
        pattern = r'loki\.write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        inputs_str = f"[{', '.join(f'\"{t}\"' for t in self.log_pipeline_tails)}]" if self.log_pipeline_tails else '["<TODO: Add Inputs>"]'
        
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
