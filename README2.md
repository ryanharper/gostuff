# THE_ThIng

THE_ThIng is a command-line tool designed to simplify your Skaffold workflows by managing environment variables based on configurable targets.

## Features

* **Target-based configuration:** Define multiple targets (e.g., development, staging, production) in a YAML file, each with its own set of environment variables.
* **Environment variable prefixing:** Automatically prefixes all environment variables with `GRAPH_` to avoid conflicts.
* **Seamless Skaffold integration:** Invokes Skaffold with the specified target's environment variables, passing through any additional arguments.
* **Customizable configuration file:** Use the `-c` or `--config` flag to specify a different configuration file path (defaults to `THE_ThIng.yaml`).

## Installation

1. **Prerequisites:** Ensure you have Go installed on your system.
2. **Build from source:**
   ```bash
   git clone https://your-repo-url/THE_ThIng.git
   cd THE_ThIng
   go build
   ```
3. **(Optional) Install globally:**
   ```bash
   sudo mv thething /usr/local/bin 
   ```

## Configuration
Create a thething.yaml file (or specify a different path using the -c flag) with the following structure:
```yaml
targets:
- name: development
  variables:
    MY_VAR1: value1
    MY_VAR2: value2
- name: production
  variables:
    MY_VAR1: prod_value1
    MY_VAR2: prod_value2
```

### Usage

1. **Standard command:**
```bash
thethhing development dev --port-forward
```
2. **Alternate Configuration File:**
The command will append any arguments that you would ordinarily send to skaffold.
```bash
thethhing -c <config_file> development dev --port-forward
```
**_NOTE:_**
This will run skaffold dev --port-forward with the environment variables GRAPH_MY_VAR1=value1 and GRAPH_MY_VAR2=value2 set.

### Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests.

### License
This project is licensed under the 
