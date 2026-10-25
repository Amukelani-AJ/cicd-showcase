{{- /* Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Naming and label helpers */ -}}
{{- /* Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Shared pod template and the Rollout-or-Deployment switch */ -}}
{{- define "cicd-showcase.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "cicd-showcase.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "cicd-showcase.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cicd-showcase.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "cicd-showcase.labels" -}}
{{ include "cicd-showcase.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- /* Renders "true" only when rollout.enabled AND the Argo Rollouts CRD is installed. */ -}}
{{- define "cicd-showcase.useRollout" -}}
{{- if and .Values.rollout.enabled (.Capabilities.APIVersions.Has "argoproj.io/v1alpha1/Rollout") -}}true{{- end -}}
{{- end -}}

{{- /* The pod template shared by the Deployment and the Rollout so they can never drift apart. */ -}}
{{- define "cicd-showcase.podTemplate" -}}
metadata:
  labels:
    {{- include "cicd-showcase.selectorLabels" . | nindent 4 }}
spec:
  securityContext:
    {{- toYaml .Values.podSecurityContext | nindent 4 }}
  containers:
    - name: app
      image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
      imagePullPolicy: {{ .Values.image.pullPolicy }}
      ports:
        - name: http
          containerPort: {{ .Values.service.targetPort }}
      {{- with .Values.env }}
      env:
        {{- range $name, $value := . }}
        - name: {{ $name }}
          value: {{ $value | quote }}
        {{- end }}
      {{- end }}
      securityContext:
        {{- toYaml .Values.containerSecurityContext | nindent 8 }}
      livenessProbe:
        httpGet:
          path: {{ .Values.probes.path }}
          port: http
        {{- toYaml .Values.probes.liveness | nindent 8 }}
      readinessProbe:
        httpGet:
          path: {{ .Values.probes.path }}
          port: http
        {{- toYaml .Values.probes.readiness | nindent 8 }}
      resources:
        {{- toYaml .Values.resources | nindent 8 }}
{{- end -}}
