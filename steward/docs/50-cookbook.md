---
source: https://ide-tutorial.hyperai.di.uoa.gr/cookbook/
title: Cookbook & Examples
retrieved: 2026-10-06
fidelity: verbatim examples (web fetch); see tests/fixtures/cookbook for full YAML
---
# Native: Hello World Web Server — nginx
A workflow that deploys an nginx server; the user expresses preferences through constraints and QoS requirements. The published example uses executionType container, entryPoint uvicorn with args main:app --host 0.0.0.0 --port 8000, baseOS python 3.10-slim, containerImage nginx:latest, resources cpu 2000m / memory 10Gi / storage 1Gi, port 8000 TCP publicly exposed, architectures x86_64 and arm64, securityLevel "high", dataClassification private, startupTime 10s, availability 99.0%.
Note from Steward: the example's entry point (uvicorn, a Python server) does not exist inside the nginx image, and its securityLevel uses a word where the native spec documents "1"–"3".

# Device: Hello World — Docker
A minimal Docker application built on the hello-world image. device_name is intentionally omitted so the platform scheduler selects the best device with Docker support. Uses apiVersion hyper.ai/v1, kind Application, workload DockerImage hello-world with imagePullPolicy IfNotPresent, port 80 HTTP, networkBandwidthMin 1 Mbps, latency 500 ms, energy 1 W, cost 0.01 USD per hour, resilience auto-restart, availability 0.90 fraction, startup 5 s, schedulingPriority 1, architectures amd64 and arm64, geoLocationRequirement LocalZone, faultTolerance graceful-degradation, dataClassification internal.

# Device: Hello World — Android APK
Installs a simple Hello World APK from an apkUrl with packageName com.example.testtarget and installMode install. It targets a specific registered Android DeviceNode by setting spec.device_name, and uses supportedArchitectures arm64-v8a.
