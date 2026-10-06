"""Local checks for HYPER-AI application profiles.

Encoded from the official DSL reference pages (ide-tutorial.hyperai.di.uoa.gr/dsl/native-apps/ and
/dsl/devices/, read 2026-10-06). The IDE backend validator remains the authority: this module only
catches violations that are certain from the published spec, so obviously broken YAML never reaches
the workspace. Anything the spec leaves ambiguous is reported as a warning, not an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import yaml


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ProfileKind(StrEnum):
    NATIVE = "native"
    DEVICE = "device"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Issue:
    field: str
    message: str
    severity: Severity
    rule: str = "spec"

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message, "severity": self.severity.value, "rule": self.rule}


@dataclass(frozen=True)
class SpecReport:
    kind: ProfileKind
    issues: tuple[Issue, ...]
    parse_error: str | None = None

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def ok(self) -> bool:
        return self.parse_error is None and not self.errors


LIFECYCLE_PHASES = {"development", "testing", "production"}
CPU_MILLICORES = re.compile(r"^(\d+)m$")
SIZE_UNITS = re.compile(r"^\d+(\.\d+)?(Mi|Gi|Ti)$")
BANDWIDTH = re.compile(r"^\d+(\.\d+)?\s?(Mbps|Gbps)$")
LATENCY_MS = re.compile(r"^\d+(\.\d+)?\s?ms$")
SECONDS = re.compile(r"^\d+(\.\d+)?\s?s$")
PERCENT = re.compile(r"^\d+(\.\d+)?\s?%$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")

DEVICE_WORKLOADS = {"AndroidApk": "androidApk", "DockerImage": "dockerImage", "esp32Binary": "esp32Binary"}
ESP32_CHIPS = {"esp32", "esp32s2", "esp32s3", "esp32c3", "esp32c6", "esp32h2"}
PULL_POLICIES = {"Always", "IfNotPresent", "Never"}
CPU_UNITS = {"cores", "millicores"}
LATENCY_UNITS = {"ms", "s"}
ENERGY_UNITS = {"mW", "W"}
MONEY_PER = {"second", "minute", "hour", "day"}
BANDWIDTH_UNITS = {"bps", "Kbps", "Mbps", "Gbps"}
TASK_STATUS = {"IDLE", "RUNNING", "SCHEDULED"}


def parse_profile(text: str) -> tuple[Any, str | None]:
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"


def detect_kind(doc: Any) -> ProfileKind:
    if isinstance(doc, dict):
        if "applicationProfile" in doc:
            return ProfileKind.NATIVE
        if doc.get("kind") == "Application" or "apiVersion" in doc:
            return ProfileKind.DEVICE
    return ProfileKind.UNKNOWN


def check_profile(text: str) -> SpecReport:
    doc, err = parse_profile(text)
    if err:
        return SpecReport(ProfileKind.UNKNOWN, (), parse_error=err)
    kind = detect_kind(doc)
    if kind is ProfileKind.NATIVE:
        return SpecReport(kind, tuple(_check_native(doc)))
    if kind is ProfileKind.DEVICE:
        return SpecReport(kind, tuple(_check_device(doc)))
    return SpecReport(
        kind,
        (Issue("<root>", "Not a HYPER-AI profile: expected `applicationProfile:` (native) or "
               "`apiVersion: hyper.ai/v1` + `kind: Application` (device).", Severity.ERROR),),
    )


# --- helpers -------------------------------------------------------------------------------------

class _Ctx:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def err(self, field: str, msg: str) -> None:
        self.issues.append(Issue(field, msg, Severity.ERROR))

    def warn(self, field: str, msg: str) -> None:
        self.issues.append(Issue(field, msg, Severity.WARNING))

    def section(self, parent: Any, key: str, path: str, required: bool = True) -> dict | None:
        value = parent.get(key) if isinstance(parent, dict) else None
        if value is None:
            if required:
                self.err(path, "is required")
            return None
        if not isinstance(value, dict):
            self.err(path, "must be a mapping")
            return None
        return value

    def required_str(self, obj: dict, key: str, path: str) -> str | None:
        if key not in obj or obj[key] in (None, ""):
            self.err(path, "is required")
            return None
        if not isinstance(obj[key], str):
            self.err(path, f"must be a string (got {type(obj[key]).__name__})")
            return None
        return obj[key]

    def enum(self, obj: dict, key: str, path: str, allowed: set[str], required: bool = True) -> None:
        if key not in obj:
            if required:
                self.err(path, "is required")
            return
        if obj[key] not in allowed:
            self.err(path, f"must be one of {sorted(allowed)} (got {obj[key]!r})")

    def pattern(self, obj: dict, key: str, path: str, rx: re.Pattern, example: str, required: bool = False) -> None:
        if key not in obj:
            if required:
                self.err(path, "is required")
            return
        if not isinstance(obj[key], str) or not rx.match(obj[key]):
            self.err(path, f"has invalid format {obj[key]!r}; expected e.g. {example}")

    def non_negative_int(self, obj: dict, key: str, path: str) -> None:
        if key in obj and (not isinstance(obj[key], int) or isinstance(obj[key], bool) or obj[key] < 0):
            self.err(path, "must be an integer >= 0")

    def boolean(self, obj: dict, key: str, path: str, required: bool = False) -> None:
        if key not in obj:
            if required:
                self.err(path, "is required")
            return
        if not isinstance(obj[key], bool):
            self.err(path, f"must be true/false (got {obj[key]!r})")

    def string_list(self, obj: dict, key: str, path: str, required: bool = False) -> None:
        if key not in obj:
            if required:
                self.err(path, "is required")
            return
        value = obj[key]
        if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
            self.err(path, "must be a non-empty list of strings")


# --- native --------------------------------------------------------------------------------------

def _check_native(doc: dict) -> list[Issue]:
    c = _Ctx()
    root = doc["applicationProfile"]
    if not isinstance(root, dict):
        c.err("applicationProfile", "must be a mapping")
        return c.issues

    meta = c.section(root, "metadata", "applicationProfile.metadata")
    if meta is not None:
        p = "applicationProfile.metadata"
        c.enum(meta, "type", f"{p}.type", {"native"})
        for key in ("schemaVersion", "name", "version", "owner"):
            c.required_str(meta, key, f"{p}.{key}")
        c.enum(meta, "lifecyclePhase", f"{p}.lifecyclePhase", LIFECYCLE_PHASES)
        for key in ("createdAt", "updatedAt"):
            c.pattern(meta, key, f"{p}.{key}", RFC3339, "2026-10-06T10:00:00Z")
        annotations = meta.get("annotations")
        if annotations is not None and isinstance(annotations, dict) and "dependencies" in annotations:
            if not isinstance(annotations["dependencies"], list):
                c.err(f"{p}.annotations.dependencies", "must be a list")

    specs = c.section(root, "specs", "applicationProfile.specs")
    if specs is None:
        return c.issues
    s = "applicationProfile.specs"

    runtime = c.section(specs, "runtime", f"{s}.runtime")
    if runtime is not None:
        r = f"{s}.runtime"
        c.enum(runtime, "executionType", f"{r}.executionType", {"container", "vm"})
        c.required_str(runtime, "entryPoint", f"{r}.entryPoint")
        if "args" not in runtime:
            c.err(f"{r}.args", "is required (use [] when there are no arguments)")
        elif not isinstance(runtime["args"], list):
            c.err(f"{r}.args", "must be a list")
        base = c.section(runtime, "baseOS", f"{r}.baseOS")
        if base is not None:
            c.required_str(base, "name", f"{r}.baseOS.name")
            _required_scalar_str(c, base, "version", f"{r}.baseOS.version")
        image = c.section(runtime, "containerImage", f"{r}.containerImage")
        if image is not None:
            c.required_str(image, "uri", f"{r}.containerImage.uri")
            _required_scalar_str(c, image, "tag", f"{r}.containerImage.tag")
        c.enum(runtime, "hypervisor", f"{r}.hypervisor", {"qemu", "kvm", "xen", "vmware"}, required=False)

    resources = c.section(specs, "resources", f"{s}.resources")
    if resources is not None:
        r = f"{s}.resources"
        cpu = resources.get("cpu")
        if cpu is None:
            c.err(f"{r}.cpu", "is required")
        elif not isinstance(cpu, str) or not CPU_MILLICORES.match(cpu) or int(CPU_MILLICORES.match(cpu).group(1)) <= 0:
            c.err(f"{r}.cpu", f"must be millicores > 0 like \"2000m\" (got {cpu!r})")
        c.pattern(resources, "memory", f"{r}.memory", SIZE_UNITS, '"512Mi" or "10Gi"', required=True)
        c.pattern(resources, "storage", f"{r}.storage", SIZE_UNITS, '"1Gi"', required=True)
        for key in ("gpu", "tpu", "accelerators"):
            c.non_negative_int(resources, key, f"{r}.{key}")

    network = c.section(specs, "network", f"{s}.network", required=False)
    if network is not None:
        n = f"{s}.network"
        _check_ports(c, network, n)
        for idx, port in enumerate(network.get("ports") or []):
            if isinstance(port, dict):
                c.boolean(port, "publicExposure", f"{n}.ports[{idx}].publicExposure")
        if "protocols" in network and not isinstance(network["protocols"], list):
            c.err(f"{n}.protocols", "must be a list")
        c.pattern(network, "networkBandwidthMin", f"{n}.networkBandwidthMin", BANDWIDTH, '"100Mbps"')

    constraints = c.section(specs, "constraints", f"{s}.constraints")
    if constraints is not None:
        k = f"{s}.constraints"
        c.string_list(constraints, "supportedArchitectures", f"{k}.supportedArchitectures", required=True)
        c.boolean(constraints, "isHighlyAvailable", f"{k}.isHighlyAvailable")
        # The native spec documents securityLevel as "1".."3", but the device spec and the official native
        # cookbook use words like "high". The docs disagree, so this is a warning; the IDE validator decides.
        if "securityLevel" in constraints and str(constraints["securityLevel"]) not in {"1", "2", "3"}:
            c.warn(f"{k}.securityLevel",
                   f"native spec documents \"1\", \"2\" or \"3\" (3=high); got {constraints['securityLevel']!r}")
        if "trustScore" in constraints and str(constraints["trustScore"]) not in {"1", "2", "3", "4", "5"}:
            c.warn(f"{k}.trustScore", f"native spec documents \"1\" to \"5\"; got {constraints['trustScore']!r}")

    qos = c.section(specs, "qos", f"{s}.qos", required=False)
    if qos is not None:
        q = f"{s}.qos"
        c.pattern(qos, "latencyToleranceMax", f"{q}.latencyToleranceMax", LATENCY_MS, '"150ms"')
        c.pattern(qos, "availability", f"{q}.availability", PERCENT, '"99.0%"')
        c.pattern(qos, "startupTime", f"{q}.startupTime", SECONDS, '"10s"')
        if "resilience" in qos:
            c.issues.append(Issue(f"{q}.resilience",
                                  "is deprecated (redundant with constraints.faultTolerance); prefer faultTolerance",
                                  Severity.INFO))

    if "status" in root:
        c.warn("applicationProfile.status", "is runtime state maintained by the platform; do not author it")
    return c.issues


def _required_scalar_str(c: _Ctx, obj: dict, key: str, path: str) -> None:
    if key not in obj or obj[key] in (None, ""):
        c.err(path, "is required")
    elif not isinstance(obj[key], str):
        c.warn(path, f"should be quoted as a string (got {type(obj[key]).__name__} {obj[key]!r})")


def _check_ports(c: _Ctx, network: dict, n: str) -> None:
    ports = network.get("ports")
    if ports is None:
        return
    if not isinstance(ports, list):
        c.err(f"{n}.ports", "must be a list")
        return
    for idx, port in enumerate(ports):
        p = f"{n}.ports[{idx}]"
        if not isinstance(port, dict):
            c.err(p, "must be a mapping with port and protocol")
            continue
        value = port.get("port")
        if value is None:
            c.err(f"{p}.port", "is required")
        elif not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
            c.err(f"{p}.port", f"must be an integer 1-65535 (got {value!r})")
        if not port.get("protocol"):
            c.err(f"{p}.protocol", "is required")


# --- device --------------------------------------------------------------------------------------

def _value_unit(c: _Ctx, obj: dict, key: str, path: str, units: set[str], required: bool,
                value_range: tuple[float, float] | None = None, unit_key: str = "unit") -> None:
    item = obj.get(key)
    if item is None:
        if required:
            c.err(path, "is required")
        return
    if not isinstance(item, dict):
        c.err(path, f"must be an object like {{ value: 1, {unit_key}: {sorted(units)[0]} }}")
        return
    value = item.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        c.err(f"{path}.value", f"must be a number (got {value!r})")
    elif value_range and not value_range[0] <= value <= value_range[1]:
        c.err(f"{path}.value", f"must be between {value_range[0]} and {value_range[1]} (got {value})")
    if units and item.get(unit_key) not in units:
        c.err(f"{path}.{unit_key}", f"must be one of {sorted(units)} (got {item.get(unit_key)!r})")


def _check_device(doc: dict) -> list[Issue]:
    c = _Ctx()
    if doc.get("apiVersion") != "hyper.ai/v1":
        c.err("apiVersion", f"must be \"hyper.ai/v1\" (got {doc.get('apiVersion')!r})")
    if doc.get("kind") != "Application":
        c.err("kind", f"must be \"Application\" (got {doc.get('kind')!r})")
    meta = c.section(doc, "metadata", "metadata")
    if meta is not None:
        c.required_str(meta, "name", "metadata.name")
        if "annotations" in meta and not isinstance(meta["annotations"], dict):
            c.err("metadata.annotations", "must be a key/value mapping")
    if "status" in doc:
        c.warn("status", "is platform-managed and read-only; do not author it")

    spec = c.section(doc, "spec", "spec")
    if spec is None:
        return c.issues
    if "device_uuid" in spec:
        c.warn("spec.device_uuid", "is set by the platform; do not author it")

    app = c.section(spec, "app", "spec.app")
    if app is not None:
        c.enum(app, "type", "spec.app.type", {"device"})
        for key in ("schemaVersion", "name", "version", "owner"):
            c.required_str(app, key, f"spec.app.{key}")
        c.enum(app, "lifecyclePhase", "spec.app.lifecyclePhase", LIFECYCLE_PHASES)

    workload = c.section(spec, "workload", "spec.workload")
    if workload is not None:
        kind = workload.get("kind")
        if kind not in DEVICE_WORKLOADS:
            c.err("spec.workload.kind", f"must be one of {sorted(DEVICE_WORKLOADS)} (got {kind!r})")
        else:
            block_key = DEVICE_WORKLOADS[kind]
            for other in DEVICE_WORKLOADS.values():
                if other != block_key and other in workload:
                    c.err(f"spec.workload.{other}", f"must not be present when kind is {kind}")
            block = c.section(workload, block_key, f"spec.workload.{block_key}")
            if block is not None:
                _check_workload_block(c, kind, block, f"spec.workload.{block_key}")

    exec_ = c.section(spec, "exec", "spec.exec", required=False)
    if exec_ is not None:
        for key in ("parameters", "env"):
            if key in exec_ and not isinstance(exec_[key], dict):
                c.err(f"spec.exec.{key}", "must be a key/value mapping")
        if "command" in exec_ and not isinstance(exec_["command"], list):
            c.err("spec.exec.command", "must be a list of strings")

    resources = c.section(spec, "resources", "spec.resources", required=False)
    if resources is not None:
        _value_unit(c, resources, "cpu", "spec.resources.cpu", CPU_UNITS, required=False)
        for key in ("memory", "storage"):
            _value_unit(c, resources, key, f"spec.resources.{key}", set(), required=False)
        for key in ("gpu", "tpu"):
            c.non_negative_int(resources, key, f"spec.resources.{key}")

    network = c.section(spec, "network", "spec.network")
    if network is not None:
        if not network.get("ports"):
            c.err("spec.network.ports", "is required (at least one port)")
        _check_ports(c, network, "spec.network")
        _value_unit(c, network, "networkBandwidthMin", "spec.network.networkBandwidthMin", BANDWIDTH_UNITS,
                    required=True)

    qos = c.section(spec, "qos", "spec.qos")
    if qos is not None:
        _value_unit(c, qos, "latencyToleranceMax", "spec.qos.latencyToleranceMax", LATENCY_UNITS, required=True)
        _value_unit(c, qos, "energyCost", "spec.qos.energyCost", ENERGY_UNITS, required=True)
        _value_unit(c, qos, "monetaryCost", "spec.qos.monetaryCost", set(), required=True)
        money = qos.get("monetaryCost")
        if isinstance(money, dict):
            if not money.get("currency"):
                c.err("spec.qos.monetaryCost.currency", "is required (e.g. USD)")
            if money.get("per") not in MONEY_PER:
                c.err("spec.qos.monetaryCost.per", f"must be one of {sorted(MONEY_PER)} (got {money.get('per')!r})")
        if not qos.get("resilience"):
            c.err("spec.qos.resilience", "is required (e.g. auto-restart)")
        _value_unit(c, qos, "availability", "spec.qos.availability", {"fraction"}, required=True,
                    value_range=(0, 1))
        _value_unit(c, qos, "startupTime", "spec.qos.startupTime", LATENCY_UNITS, required=True)

    constraints = c.section(spec, "constraints", "spec.constraints")
    if constraints is not None:
        k = "spec.constraints"
        if not isinstance(constraints.get("schedulingPriority"), int) or isinstance(
                constraints.get("schedulingPriority"), bool):
            c.err(f"{k}.schedulingPriority", "is required and must be an integer")
        c.string_list(constraints, "supportedArchitectures", f"{k}.supportedArchitectures", required=True)
        for key in ("geoLocationRequirement", "faultTolerance", "dataClassification"):
            c.required_str(constraints, key, f"{k}.{key}")
        c.boolean(constraints, "isHighlyAvailable", f"{k}.isHighlyAvailable", required=True)
        if "batteryLevelMin" in constraints:
            v = constraints["batteryLevelMin"]
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 100:
                c.err(f"{k}.batteryLevelMin", "must be an integer 0-100")
        if "trustScore" in constraints:
            v = constraints["trustScore"]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                c.err(f"{k}.trustScore", "must be a number >= 0")

    sensors = spec.get("sensors")
    if sensors is not None:
        items = sensors if isinstance(sensors, list) else [sensors]
        for idx, sensor in enumerate(items):
            p = f"spec.sensors[{idx}]" if isinstance(sensors, list) else "spec.sensors"
            if not isinstance(sensor, dict):
                c.err(p, "must be a mapping")
                continue
            c.required_str(sensor, "sensorType", f"{p}.sensorType")
            c.boolean(sensor, "isActive", f"{p}.isActive", required=True)
            c.enum(sensor, "taskStatus", f"{p}.taskStatus", TASK_STATUS)
    return c.issues


def _check_workload_block(c: _Ctx, kind: str, block: dict, p: str) -> None:
    if kind == "DockerImage":
        c.required_str(block, "image", f"{p}.image")
        c.enum(block, "imagePullPolicy", f"{p}.imagePullPolicy", PULL_POLICIES, required=False)
    elif kind == "AndroidApk":
        url = c.required_str(block, "apkUrl", f"{p}.apkUrl")
        if url and not re.match(r"^https?://", url):
            c.err(f"{p}.apkUrl", "must be an http(s) URL")
        c.required_str(block, "packageName", f"{p}.packageName")
        c.enum(block, "installMode", f"{p}.installMode", {"install", "update"}, required=False)
    elif kind == "esp32Binary":
        url = c.required_str(block, "binaryUrl", f"{p}.binaryUrl")
        if url and not re.match(r"^https?://", url):
            c.err(f"{p}.binaryUrl", "must be an http(s) URL")
        c.enum(block, "chip", f"{p}.chip", ESP32_CHIPS)
        flash = c.section(block, "flash", f"{p}.flash")
        if flash is not None:
            c.enum(flash, "method", f"{p}.flash.method", {"serial", "ota"})
            if "baudRate" in flash and (not isinstance(flash["baudRate"], int) or flash["baudRate"] < 1200):
                c.err(f"{p}.flash.baudRate", "must be an integer >= 1200")
            if "offset" in flash and not re.match(r"^0x[0-9a-fA-F]+$", str(flash["offset"])):
                c.err(f"{p}.flash.offset", "must be hex like 0x10000")
