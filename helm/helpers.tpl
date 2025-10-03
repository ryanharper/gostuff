{{/*
==============================================================================
Chart Helper Functions
==============================================================================
*/}}

{{/*
mychart.renderMergedFiles
This template traverses 'base' and 'overlay' directories, producing a unified
set of Kubernetes manifests.

Logic:
1. It scans for all YAML files in `base/*.yaml` and `overlay/*.yaml`.
2. It collects all unique filenames from both directories.
3. For each file:
    - If a file exists in both directories, it performs a deep merge of the
      YAML content, with values from the 'overlay' file taking precedence.
    - If a file exists only in 'base' or 'overlay', it's included as-is.
4. The template renders each resulting manifest, separated by '---'.

This allows for a clean and maintainable way to manage environment-specific
configurations on top of a common base.

Usage:
{{- include "mychart.renderMergedFiles" . | nindent 0 }}
*/}}
{{- define "mychart.renderMergedFiles" -}}
{{- $chart := . -}}
{{- $allFiles := dict -}}

{{- /*
First, we build a dictionary of all files.
The key is the filename (e.g., "configmap.yaml"), and the value is another
dictionary containing the raw content from 'base' and/or 'overlay'.
*/}}

{{- /* Collect all files from the 'base' directory */ -}}
{{- range $path := $chart.Files.Glob "base/*.yaml" }}
    {{- $name := base $path -}}
    {{- $_ := set $allFiles $name (dict "base" ($chart.Files.Get $path)) -}}
{{- end -}}

{{- /* Collect all files from the 'overlay' directory, merging with existing entries */ -}}
{{- range $path := $chart.Files.Glob "overlay/*.yaml" }}
    {{- $name := base $path -}}
    {{- $overlayContent := $chart.Files.Get $path -}}
    {{- if not (hasKey $allFiles $name) -}}
        {{- /* This file is new, only in the overlay */ -}}
        {{- $_ := set $allFiles $name (dict "overlay" $overlayContent) -}}
    {{- else -}}
        {{- /* This file also exists in base, add the overlay content */ -}}
        {{- $existing := get $allFiles $name -}}
        {{- $_ := set $existing "overlay" $overlayContent -}}
    {{- end -}}
{{- end -}}

{{- /*
Now, iterate through the collected file dictionary and render the output.
*/}}
{{- range $name, $content := $allFiles -}}
---
{{- if and (hasKey $content "base") (hasKey $content "overlay") -}}
{{- /*
File exists in both 'base' and 'overlay'. We perform a deep merge.
'fromYaml' converts the raw string to a YAML object.
'mergeOverwrite' (same as 'merge') performs a deep merge, with the second
object's values overwriting the first in case of conflicts.
'toYaml' converts the final merged object back into a YAML string.
*/}}
    {{- $baseYaml := fromYaml (get $content "base") -}}
    {{- $overlayYaml := fromYaml (get $content "overlay") -}}
    {{- toYaml (mergeOverwrite (deepCopy $baseYaml) $overlayYaml) -}}
{{- else if (hasKey $content "base") -}}
{{- /* File only exists in 'base', so we render it directly. */ -}}
    {{- (get $content "base") -}}
{{- else if (hasKey $content "overlay") -}}
{{- /* File only exists in 'overlay', so we render it directly. */ -}}
    {{- (get $content "overlay") -}}
{{- end -}}
{{- end -}}
{{- end -}}
