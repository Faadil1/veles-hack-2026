---
source: https://ide-tutorial.hyperai.di.uoa.gr/dsl/native-apps/
title: DSL Specification — Native Apps
retrieved: 2026-10-06
fidelity: field tables reproduced by the fetch tool; wording condensed
---
# Native Application profile
A Native Application is defined by an `applicationProfile` YAML document with `metadata` (required), `specs` (required) and `status` (optional, runtime only).

# metadata
- `type`: "native" (required)
- `schemaVersion`: semantic version string, e.g. "1.1.0" (required)
- `name`: globally unique identifier (required)
- `version`: internal version (required)
- `description`: purpose (optional)
- `owner`: responsible party (required)
- `lifecyclePhase`: development | testing | production (required)
- `createdAt`, `updatedAt`: RFC 3339 UTC timestamps (optional)
- `annotations.intent`, `annotations.domain`, `annotations.language`, `annotations.dependencies` (list) — optional

# specs.runtime
- `executionType`: container | vm (required)
- `entryPoint`: main command or script path (required)
- `args`: list of arguments (required)
- `baseOS.name`, `baseOS.version` (required)
- `containerImage.uri` (OCI image URI) and `containerImage.tag` (required)
- `hypervisor`: qemu | kvm | xen | vmware (optional)
- `acceleratorRuntime[].name` / `.version` (optional), e.g. cuda

# specs.resources
- `cpu`: millicores string > 0, e.g. "2000m" (required)
- `memory`: Mi/Gi/Ti string, e.g. "10Gi" (required)
- `storage`: Mi/Gi/Ti string, e.g. "1Gi" (required)
- `gpu`, `tpu`, `accelerators`: integers >= 0 (optional)

# specs.network
- `ports[].port` (integer) and `ports[].protocol` (e.g. "TCP") — required per port
- `ports[].publicExposure`: boolean (optional)
- `protocols`: list such as HTTP, gRPC (optional)
- `networkBandwidthMin`: Mbps/Gbps string (optional)

# specs.constraints
- `supportedArchitectures`: list, e.g. ["x86_64"] (required)
- `trustScore`: string 1–5 (optional)
- `geoLocationRequirement`: string (optional)
- `isHighlyAvailable`: boolean (optional)
- `faultTolerance`: strategy such as "restart" (optional)
- `securityLevel`: string 1–3, where 3=high, 2=medium, 1=low (optional)
- `dataClassification`: data sensitivity level (optional)

# specs.qos
- `latencyToleranceMax` (ms, e.g. "150ms"), `energyCost` (kWh per hour), `monetaryCost` (currency per hour), `resilience` (e.g. "restart"), `availability` (%), `startupTime` (seconds) — all optional.
- `resilience` is redundant with `faultTolerance` and will be removed in future schema versions.

# status (runtime, not authored)
`isOnline`, `lastHeartBeat`, `runtimeState` (e.g. running, failed), `isStateless`, `resourceUsage.cpu/memory/storage/gpu/tpu/accelerators`. These reflect live runtime state and are updated by the platform.
