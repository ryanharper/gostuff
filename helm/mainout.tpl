# This file serves as the entry point to generate all the chart's manifests.
# It calls the helper template defined in _helpers.tpl, which handles all
# the logic for reading, merging, and rendering the files from the 'base'
# and 'overlay' directories.
{{- include "mychart.renderMergedFiles" . | nindent 0 }}
