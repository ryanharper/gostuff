package main

import (
	"bytes"
	"log"
	"os"
	"text/template"

	"gopkg.in/yaml.v3"
)

// toYaml is a custom template function that marshals data into a YAML string.
func toYaml(v any) (string, error) {
	data, err := yaml.Marshal(v)
	if err != nil {
		return "", err
	}
	return strings.TrimSuffix(string(data), "\n"), nil // Trim trailing newline for cleaner output
}

func main() {
	// 1. Define the data structure you want to convert
	data := struct {
		Name string
		Labels map[string]string
		Ports  []int
	}{
		Name: "my-app",
		Labels: map[string]string{
			"app.kubernetes.io/name":    "MyWebApp",
			"app.kubernetes.io/version": "1.2.3",
		},
		Ports: []int{80, 443},
	}

	// 2. Create a FuncMap to register the custom function
	funcMap := template.FuncMap{
		"toYaml": toYaml,
	}

	// 3. Define the template string that uses the function
	// The 'nindent' part is for demonstration to show indentation.
	// The core functionality is `{{ . | toYaml }}`
	templateString := `
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Name }}-config
data:
  values.yaml: |
    {{ . | toYaml | nindent 4 }}
`
	// 'nindent' isn't built-in, so we'll add it for the example
	funcMap["nindent"] = func(spaces int, v string) string {
		padding := strings.Repeat(" ", spaces)
		return padding + strings.ReplaceAll(v, "\n", "\n"+padding)
	}


	// 4. Parse and execute the template
	tmpl, err := template.New("config").Funcs(funcMap).Parse(templateString)
	if err != nil {
		log.Fatalf("Error parsing template: %v", err)
	}

	err = tmpl.Execute(os.Stdout, data)
	if err != nil {
		log.Fatalf("Error executing template: %v", err)
	}
}
