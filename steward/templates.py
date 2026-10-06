"""Deterministic profile builders.

The language model extracts intent into a few parameters; these builders turn them into a complete, spec-correct
profile. This removes the most error-prone part of LLM output (dozens of typed, unit-bearing fields) and keeps
defaults aligned with the official cookbook examples. Every default is visible in the generated YAML, so the user
can see and change what was assumed.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_SLUG = re.compile(r"[^a-z0-9-]+")


def slug(name: str) -> str:
    value = _SLUG.sub("-", name.strip().lower()).strip("-")
    return value or "app"


def _dump(doc: dict[str, Any]) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100)


def _ports(ports: list[Any] | None, default_protocol: str) -> list[dict[str, Any]]:
    out = []
    for p in ports or []:
        if isinstance(p, dict):
            out.append({"port": int(p.get("port")), "protocol": str(p.get("protocol") or default_protocol)})
        else:
            out.append({"port": int(p), "protocol": default_protocol})
    return out


def build_device_profile(
    name: str,
    workload: str = "DockerImage",
    image: str | None = None,
    apk_url: str | None = None,
    package_name: str | None = None,
    binary_url: str | None = None,
    chip: str | None = None,
    device_name: str | None = None,
    architectures: list[str] | None = None,
    ports: list[Any] | None = None,
    latency_ms: float = 500,
    availability: float = 0.9,
    energy_w: float = 1,
    cost_usd_per_hour: float = 0.01,
    bandwidth_mbps: float = 1,
    lifecycle_phase: str = "development",
    owner: str = "HyperAI user",
    description: str | None = None,
    intent: str | None = None,
    parameters: dict[str, str] | None = None,
    command: list[str] | None = None,
    cpu_cores: float | None = None,
    memory_mib: float | None = None,
    highly_available: bool = False,
    data_classification: str = "internal",
    geo: str = "LocalZone",
    fault_tolerance: str = "graceful-degradation",
    scheduling_priority: int = 1,
) -> str:
    app_name = slug(name)
    if workload == "DockerImage":
        if not image:
            raise ValueError("image is required for a DockerImage workload")
        block = {"kind": "DockerImage", "dockerImage": {"image": image, "imagePullPolicy": "IfNotPresent"}}
        archs = architectures or ["amd64", "arm64"]
    elif workload == "AndroidApk":
        if not apk_url or not package_name:
            raise ValueError("apk_url and package_name are required for an AndroidApk workload")
        block = {"kind": "AndroidApk", "androidApk": {"apkUrl": apk_url, "packageName": package_name,
                                                       "installMode": "install"}}
        archs = architectures or ["arm64-v8a"]
    elif workload == "esp32Binary":
        if not binary_url or not chip:
            raise ValueError("binary_url and chip are required for an esp32Binary workload")
        block = {"kind": "esp32Binary", "esp32Binary": {"binaryUrl": binary_url, "chip": chip,
                                                         "flash": {"method": "ota"}}}
        archs = architectures or [chip]
    else:
        raise ValueError(f"unknown workload {workload!r}")

    spec: dict[str, Any] = {}
    if device_name:
        spec["device_name"] = device_name
    spec["app"] = {"type": "device", "schemaVersion": "1.0.0", "name": app_name, "version": "1.0.0",
                   "description": description or f"{app_name} device application.", "owner": owner,
                   "lifecyclePhase": lifecycle_phase}
    spec["workload"] = block
    if parameters or command:
        spec["exec"] = {}
        if parameters:
            spec["exec"]["parameters"] = {str(k): str(v) for k, v in parameters.items()}
        if command:
            spec["exec"]["command"] = [str(c) for c in command]
    if cpu_cores is not None or memory_mib is not None:
        spec["resources"] = {}
        if cpu_cores is not None:
            spec["resources"]["cpu"] = {"value": cpu_cores, "unit": "cores"}
        if memory_mib is not None:
            spec["resources"]["memory"] = {"value": memory_mib, "unit": "MiB"}
    spec["network"] = {"ports": _ports(ports, "HTTP") or [{"port": 80, "protocol": "HTTP"}],
                       "networkBandwidthMin": {"value": bandwidth_mbps, "unit": "Mbps"}}
    spec["qos"] = {
        "latencyToleranceMax": {"value": latency_ms, "unit": "ms"},
        "energyCost": {"value": energy_w, "unit": "W"},
        "monetaryCost": {"value": cost_usd_per_hour, "currency": "USD", "per": "hour"},
        "resilience": "auto-restart",
        "availability": {"value": availability, "unit": "fraction"},
        "startupTime": {"value": 5, "unit": "s"},
    }
    spec["constraints"] = {"schedulingPriority": scheduling_priority, "supportedArchitectures": archs,
                           "geoLocationRequirement": geo, "isHighlyAvailable": highly_available,
                           "faultTolerance": fault_tolerance, "dataClassification": data_classification}
    doc = {"apiVersion": "hyper.ai/v1", "kind": "Application",
           "metadata": {"name": app_name, "annotations": {"intent": intent or description or app_name}},
           "spec": spec}
    return _dump(doc)


def build_native_profile(
    name: str,
    image: str,
    tag: str = "1.0.0",
    entry_point: str | None = None,
    args: list[str] | None = None,
    base_os: str = "debian",
    base_os_version: str = "12",
    execution_type: str = "container",
    cpu_millicores: int = 500,
    memory: str = "512Mi",
    storage: str = "1Gi",
    ports: list[Any] | None = None,
    public: bool = False,
    architectures: list[str] | None = None,
    security_level: str = "2",
    data_classification: str = "internal",
    highly_available: bool = False,
    latency_ms: float | None = None,
    availability_percent: float | None = None,
    startup_s: float | None = None,
    lifecycle_phase: str = "development",
    owner: str = "HyperAI user",
    description: str | None = None,
    intent: str | None = None,
    language: str | None = None,
) -> str:
    if ":" in image.rsplit("/", 1)[-1] and tag == "1.0.0":
        image, tag = image.rsplit(":", 1)
    app_name = slug(name)
    port_list = _ports(ports, "TCP")
    runtime: dict[str, Any] = {"executionType": execution_type,
                               "entryPoint": entry_point or "/docker-entrypoint.sh",
                               "args": [str(a) for a in (args or [])],
                               "baseOS": {"name": base_os, "version": str(base_os_version)},
                               "containerImage": {"uri": image, "tag": str(tag)}}
    specs: dict[str, Any] = {
        "runtime": runtime,
        "resources": {"cpu": f"{int(cpu_millicores)}m", "memory": memory, "storage": storage},
    }
    if port_list:
        specs["network"] = {"ports": [{**p, "publicExposure": public} for p in port_list], "protocols": ["HTTP"]}
    specs["constraints"] = {"supportedArchitectures": architectures or ["x86_64", "arm64"],
                            "securityLevel": str(security_level), "dataClassification": data_classification,
                            "isHighlyAvailable": highly_available}
    qos: dict[str, Any] = {}
    if latency_ms is not None:
        qos["latencyToleranceMax"] = f"{int(latency_ms)}ms"
    if availability_percent is not None:
        qos["availability"] = f"{availability_percent}%"
    if startup_s is not None:
        qos["startupTime"] = f"{int(startup_s)}s"
    if qos:
        specs["qos"] = qos
    annotations: dict[str, Any] = {"intent": intent or description or app_name}
    if language:
        annotations["language"] = language
    doc = {"applicationProfile": {
        "metadata": {"type": "native", "schemaVersion": "1.1.0", "name": app_name, "version": "1.0.0",
                     "description": description or f"{app_name} native application.", "owner": owner,
                     "lifecyclePhase": lifecycle_phase, "annotations": annotations},
        "specs": specs}}
    return _dump(doc)
