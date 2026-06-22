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
        
        for
