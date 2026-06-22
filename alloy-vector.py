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
            
            # 2. Extract paths (handles both __path__ = "..." and "__path__" = "...")
            paths = re.findall(r'(?:__path__|"__path__")\s*=\s*"([^"]+)"', block)
            if not paths:
                continue
                
            paths_str = ", ".join(f'"{p}"' for p in set(paths))
            
            self.vector_config["sources"][source_name] = {
                "type": '"file"',
                "include": f"[{paths_str}]"
            }
            
            # 3. Extract static labels (e.g., application_name = "testapp")
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
                self.log_pipeline_tails.append(transform_name)
            else:
                self.log_pipeline_tails.append(source_name)

    def _map_log_transforms(self):
        """Extracts stage.regex and maps to Vector VRL."""
        pattern = r'stage\.regex\s*\{.*?expression\s*=\s*"([^"]+)".*?\}'
        matches = list(re.finditer(pattern, self.alloy_config, re.DOTALL))
        
        if not matches or not self.log_pipeline_tails:
            return

        # Python < 3.12 Safe String Formatting
        formatted_tails = [f'"{t}"' for t in self.log_pipeline_tails]
        inputs_str = f"[{', '.join(formatted_tails)}]"
        
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
            
            self.log_pipeline_tails = [transform_name]

    def _map_log_sinks(self):
        """Maps Alloy loki.write to Vector loki sinks."""
        pattern = r'loki\.write\s+"([^"]+)".*?url\s*=\s*"([^"]+)"'
        matches = re.finditer(pattern, self.alloy_config, re.DOTALL)
        
        # Python < 3.12 Safe String Formatting
        formatted_tails = [f'"{t}"' for t in self.log_pipeline_tails]
        inputs_str = f"[{', '.join(formatted_tails)}]" if formatted_tails else '["<TODO: Add Inputs>"]'
        
        for match in matches:
            label, url = match.groups()
            base_url = url.replace("/loki/api/v1/push", "").replace("/api/prom/push", "")
            
            self.vector_config["sinks"][f"loki_{label}"] = {
                "type": '"loki"',
                "inputs": inputs_str,
                "endpoint": f
