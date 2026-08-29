{{/*
Expand the name of the chart.
*/}}
{{- define "pi-cluster.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pi-cluster.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for a given component
*/}}
{{- define "pi-cluster.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pi-cluster.name" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}
