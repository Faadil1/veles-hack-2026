---
source: https://ide-tutorial.hyperai.di.uoa.gr/dsl/devices/
title: DSL Specification — Device Apps
retrieved: 2026-10-06
fidelity: field tables reproduced by the fetch tool; wording condensed
---
# Device Application structure
Root fields: `apiVersion` (must be hyper.ai/v1), `kind` (must be Application), `metadata`, `spec`, and a read-only platform-managed `status`.

# metadata
- `name` (required); `annotations` key-value map (optional, e.g. intent).

# spec — device selection
- `device_name` (optional): omit it to let the platform scheduler choose a device.
- `device_uuid`: set automatically by the platform; do not modify.

# spec.app
`type` (device), `schemaVersion`, `name`, `version`, `owner`, `lifecyclePhase` (development | testing | production) are required; `description`, `parentApp.name`, `parentApp.uid` optional.

# spec.workload
- `kind` (required): AndroidApk | DockerImage | esp32Binary. Exactly one matching block is required.
- AndroidApk: `androidApk.apkUrl` (required), `androidApk.packageName` (required), `sha256`, `installMode` (install | update), `launch.activity`, `launch.action`, `launch.category`.
- DockerImage: `dockerImage.image` (required), `imagePullPolicy` (Always | IfNotPresent | Never), `imagePullSecretRef`.
- esp32Binary: `esp32Binary.binaryUrl` (required), `chip` (esp32, esp32s2, esp32s3, esp32c3, esp32c6, esp32h2; required), `flash.method` (serial | ota; required), `sha256`, `flash.port`, `flash.baudRate` (>= 1200), `flash.offset` (hex), `flash.partition`, `flash.eraseFlash`.

# spec.exec (optional)
`parameters` (map), `command` (list overriding the entrypoint), `env` (map), `workingDir`.

# spec.resources (optional)
`cpu.value` + `cpu.unit` (cores | millicores), `memory.value` + `memory.unit` (MiB, GiB…), `storage.value` + `storage.unit`, `gpu`, `tpu`, `accelerators` (list such as cuda, tensorrt).

# spec.network (required)
`ports[].port` (1–65535) and `ports[].protocol` (e.g. HTTP, TCP); `networkBandwidthMin.value` + `.unit` (bps | Kbps | Mbps | Gbps).

# spec.qos (required)
`latencyToleranceMax` (value + ms|s), `energyCost` (value + mW|W), `monetaryCost` (value + currency + per second|minute|hour|day), `resilience` (e.g. auto-restart), `availability` (value 0–1, unit fraction), `startupTime` (value + ms|s).

# spec.constraints (required)
`schedulingPriority` (integer), `supportedArchitectures` (e.g. arm64-v8a, amd64), `geoLocationRequirement` (e.g. LocalZone), `isHighlyAvailable`, `faultTolerance` (e.g. graceful-degradation), `dataClassification` are required; `trustScore` (>= 0), `batteryLevelMin` (0–100), `securityLevel` (e.g. high) optional.

# spec.sensors
`sensorType`, `isActive`, `taskStatus` (IDLE | RUNNING | SCHEDULED) required; `sensorIDs`, `platformInfo` optional.

# spec.runtime (optional)
`baseOS.name`, `baseOS.version`, `acceleratorRuntime[].name`, `hypervisor`.

# Miscellaneous
`logs_url`, `metrics_url`, and free-form `config` for application-specific settings (e.g. mqtt_broker, sampling_rate, model_path).

# Deployment status phases (read-only)
pending (awaiting device acknowledgment), scheduled (device selected, workload transmission in progress), deployed (device confirmed), failed (error or timeout), removed (deletion acknowledged).
