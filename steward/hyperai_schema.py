"""Faithful Python port of the HYPER-AI IDE backend validator (donmichael/ide-backend, validation/*.js).

Source of truth: the backend's own rule tables (native.js, device.js) and rule engine (schema.js), read from the
official image by CI recon (evidence/recon). This module mirrors them line for line so that Steward can check a
profile before it ever touches the workspace, and the result agrees with what the IDE will show. Agreement is
proven by a differential test that runs the real JavaScript validator and this port on the same corpus
(tests/test_validator_parity.py, evaluation/validator_parity.py).

YAML is parsed with YAML 1.2 core-schema semantics, like the backend's `yaml` package: `yes`/`no` stay strings,
timestamps stay strings, duplicate keys are a parse error.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import yaml

# --- YAML 1.2 core schema loader ------------------------------------------------------------------


class Core12Loader(yaml.SafeLoader):
    """SafeLoader with the YAML 1.2 core schema resolvers instead of YAML 1.1 ones."""


Core12Loader.yaml_implicit_resolvers = {}
for _tag, _rx, _first in (
    ("tag:yaml.org,2002:null", r"^(?:~|null|Null|NULL|)$", list("~nN") + [""]),
    ("tag:yaml.org,2002:bool", r"^(?:true|True|TRUE|false|False|FALSE)$", list("tTfF")),
    ("tag:yaml.org,2002:int", r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$", list("-+0123456789")),
    ("tag:yaml.org,2002:float",
     r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$",
     list("-+0123456789.")),
):
    Core12Loader.add_implicit_resolver(_tag, re.compile(_rx), _first)


def _construct_int(loader: yaml.SafeLoader, node: yaml.Node) -> int:
    text = loader.construct_scalar(node)
    if text.startswith("0o"):
        return int(text[2:], 8)
    if text.startswith("0x"):
        return int(text[2:], 16)
    return int(text)


def _construct_float(loader: yaml.SafeLoader, node: yaml.Node) -> float:
    text = str(loader.construct_scalar(node)).lower()
    if text.endswith("inf"):
        return -math.inf if text.startswith("-") else math.inf
    if text.endswith("nan"):
        return math.nan
    return float(text)


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if isinstance(key, (dict, list)):
            continue
        if key in seen:
            raise yaml.constructor.ConstructorError(None, None, "Map keys must be unique", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


Core12Loader.add_constructor("tag:yaml.org,2002:int", _construct_int)
Core12Loader.add_constructor("tag:yaml.org,2002:float", _construct_float)
Core12Loader.add_constructor("tag:yaml.org,2002:map", lambda loader, node: _construct_mapping(loader, node, True))


def load_yaml(text: str) -> Any:
    return yaml.load(text, Loader=Core12Loader)  # noqa: S506 - Core12Loader derives from SafeLoader


# --- rule engine (schema.js) ---------------------------------------------------------------------


@dataclass
class Rule:
    type: str
    required: bool
    enum: tuple | None = None
    pattern: re.Pattern | None = None
    check: Callable[[Any], bool] | None = None
    hint: str = ""
    items: str | None = None
    values: str | None = None
    open: bool = False
    implied: bool = False


def req(type_: str, **extra: Any) -> Rule:
    return Rule(type_, True, **extra)


def opt(type_: str, **extra: Any) -> Rule:
    return Rule(type_, False, **extra)


SEMVER = {"pattern": re.compile(r"^\d+\.\d+\.\d+$"), "hint": 'a semantic version, e.g. "1.1.0"'}
NON_NEGATIVE = {"check": lambda v: v >= 0, "hint": "an integer ≥ 0"}


def is_plain_object(v: Any) -> bool:
    return isinstance(v, dict)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "string": lambda v: isinstance(v, str),
    "number": _is_number,
    "integer": lambda v: _is_number(v) and float(v).is_integer(),
    "boolean": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "object": is_plain_object,
}


def _describe(value: Any) -> str:
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "object"  # JS typeof for anything else the YAML may produce


def _type_error(expected: str, value: Any) -> str:
    tip = " (wrap the value in quotes)" if expected == "string" and _describe(value) in ("number", "boolean") else ""
    return f"must be {expected}, got {_describe(value)}{tip}"


def _js_json(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _with_ancestors(rules: dict[str, Rule]) -> dict[str, Rule]:
    all_rules = dict(rules)
    for path, rule in rules.items():
        segs = path.split(".")
        for k in range(len(segs) - 2, -1, -1):
            ancestor = ".".join(segs[: k + 1])
            is_list = segs[k].endswith("[]")
            implied = all_rules.get(ancestor) or Rule("list" if is_list else "object", False,
                                                      items="object" if is_list else None, implied=True)
            list_between = any(s.endswith("[]") for s in segs[k:-1])
            if implied.implied and rule.required and not list_between:
                implied.required = True
            all_rules[ancestor] = implied
    return all_rules


def _locate(node: Any, segs: list[str], path: str) -> list[tuple[str, Any]]:
    if not is_plain_object(node):
        return []
    seg, rest = segs[0], segs[1:]
    is_list = seg.endswith("[]")
    key = seg[:-2] if is_list else seg
    child_path = f"{path}.{key}" if path else key
    child = node.get(key)
    if not rest:
        return [(child_path, child)]
    if is_list:
        if not isinstance(child, list):
            return []
        out: list[tuple[str, Any]] = []
        for i, el in enumerate(child):
            out.extend(_locate(el, rest, f"{child_path}[{i}]"))
        return out
    return _locate(child, rest, child_path)


@dataclass(frozen=True)
class Finding:
    path: str
    message: str
    target: str = "value"


def _check_value(path: str, value: Any, rule: Rule) -> Finding | None:
    if value is None:
        return Finding(path, "is required") if rule.required else None
    if not TYPE_CHECKS[rule.type](value):
        return Finding(path, _type_error(rule.type, value))
    if rule.enum and value not in rule.enum:
        return Finding(path, f"must be one of: {', '.join(rule.enum)}")
    if (rule.pattern and not rule.pattern.search(value)) or (rule.check and not rule.check(value)):
        return Finding(path, f"invalid value {_js_json(value)}, expected {rule.hint}")
    if rule.items:
        for i, el in enumerate(value):
            if not TYPE_CHECKS[rule.items](el):
                return Finding(f"{path}[{i}]", _type_error(rule.items, el))
    if rule.values:
        for k, v in value.items():
            if not TYPE_CHECKS[rule.values](v):
                return Finding(f"{path}.{k}", _type_error(rule.values, v))
    return None


def _find_unknown(node: Any, norm: str, path: str, rules: dict[str, Rule], warnings: list[Finding]) -> None:
    if isinstance(node, list):
        for i, el in enumerate(node):
            _find_unknown(el, norm, f"{path}[{i}]", rules, warnings)
        return
    if not is_plain_object(node):
        return
    for key, value in node.items():
        base = f"{norm}.{key}" if norm else str(key)
        child_path = f"{path}.{key}" if path else str(key)
        known = base if base in rules else (f"{base}[]" if f"{base}[]" in rules else None)
        if not known:
            warnings.append(Finding(child_path, "unknown field, not part of the schema", "key"))
            continue
        rule = rules[known]
        if (rule.type == "object" and not rule.values and not rule.open) or rule.items == "object":
            _find_unknown(value, known, child_path, rules, warnings)


Validator = Callable[[Any, str], tuple[list[Finding], list[Finding]]]


def create_validator(rules: dict[str, Rule]) -> Validator:
    all_rules = _with_ancestors(rules)

    def validate(root: Any, root_path: str) -> tuple[list[Finding], list[Finding]]:
        errors: list[Finding] = []
        for path, rule in all_rules.items():
            for loc_path, value in _locate(root, path.split("."), root_path):
                err = _check_value(loc_path, value, rule)
                if err:
                    errors.append(err)
        warnings: list[Finding] = []
        _find_unknown(root, "", root_path, all_rules, warnings)
        return errors, warnings

    return validate


# --- native rules (native.js) --------------------------------------------------------------------


def _unit(units: list[str], example: str) -> dict:
    return {"pattern": re.compile(rf"^\d+(\.\d+)?({'|'.join(re.escape(u) for u in units)})$"),
            "hint": f'a number followed by {"/".join(units)}, e.g. "{example}"'}


RFC3339 = {"pattern": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"),
           "hint": 'an RFC 3339 timestamp, e.g. "2026-06-04T12:00:00Z"'}
MILLICORES = {"pattern": re.compile(r"^[1-9]\d*m$"), "hint": 'millicores greater than 0, e.g. "2000m"'}
SIZE = _unit(["Mi", "Gi", "Ti"], "10Gi")
PORT = {"check": lambda v: 1 <= v <= 65535, "hint": "a port between 1 and 65535"}
LIFECYCLE = ("development", "testing", "production")


def _trust_score_ok(v: str) -> bool:
    return bool(re.fullmatch(r"\d+(\.\d+)?", v)) and 1 <= float(v) <= 5


NATIVE_RULES: dict[str, Rule] = {
    "metadata.type": req("string", enum=("native",)),
    "metadata.schemaVersion": req("string", **SEMVER),
    "metadata.name": req("string"),
    "metadata.version": req("string"),
    "metadata.description": opt("string"),
    "metadata.owner": req("string"),
    "metadata.lifecyclePhase": req("string", enum=LIFECYCLE),
    "metadata.createdAt": opt("string", **RFC3339),
    "metadata.updatedAt": opt("string", **RFC3339),
    "metadata.annotations.intent": opt("string"),
    "metadata.annotations.domain": opt("string"),
    "metadata.annotations.language": opt("string"),
    "metadata.annotations.dependencies": opt("list", items="string"),

    "specs.runtime.executionType": req("string", enum=("container", "vm")),
    "specs.runtime.entryPoint": req("string"),
    "specs.runtime.args": req("list", items="string"),
    "specs.runtime.baseOS.name": req("string"),
    "specs.runtime.baseOS.version": req("string"),
    "specs.runtime.containerImage.uri": req("string"),
    "specs.runtime.containerImage.tag": req("string"),
    "specs.runtime.hypervisor": opt("string", enum=("qemu", "kvm", "xen", "vmware")),
    "specs.runtime.acceleratorRuntime[].name": opt("string"),
    "specs.runtime.acceleratorRuntime[].version": opt("string"),

    "specs.resources.cpu": req("string", **MILLICORES),
    "specs.resources.memory": req("string", **SIZE),
    "specs.resources.storage": req("string", **SIZE),
    "specs.resources.gpu": opt("integer", **NON_NEGATIVE),
    "specs.resources.tpu": opt("integer", **NON_NEGATIVE),
    "specs.resources.accelerators": opt("integer", **NON_NEGATIVE),

    "specs.network.ports[].port": req("integer", **PORT),
    "specs.network.ports[].protocol": req("string"),
    "specs.network.ports[].publicExposure": opt("boolean"),
    "specs.network.protocols": opt("list", items="string"),
    "specs.network.networkBandwidthMin": opt("string", **_unit(["Mbps", "Gbps"], "100Mbps")),

    "specs.constraints.supportedArchitectures": req("list", items="string"),
    "specs.constraints.trustScore": opt("string", check=_trust_score_ok, hint='a number from 1 to 5, e.g. "4.5"'),
    "specs.constraints.geoLocationRequirement": opt("string"),
    "specs.constraints.isHighlyAvailable": opt("boolean"),
    "specs.constraints.faultTolerance": opt("string"),
    "specs.constraints.securityLevel": opt("string"),
    "specs.constraints.dataClassification": opt("string"),

    "specs.qos.latencyToleranceMax": opt("string", **_unit(["ms"], "150ms")),
    "specs.qos.energyCost": opt("string", **_unit(["kWh"], "0.5kWh")),
    "specs.qos.monetaryCost": opt("string"),
    "specs.qos.resilience": opt("string"),
    "specs.qos.availability": opt("string", **_unit(["%"], "99.0%")),
    "specs.qos.startupTime": opt("string", **_unit(["s"], "10s")),

    "status": opt("object"),
    "status.isOnline": req("boolean"),
    "status.lastHeartBeat": req("string", **RFC3339),
    "status.runtimeState": req("string"),
    "status.isStateless": opt("boolean"),
    "status.resourceUsage.cpu": req("string"),
    "status.resourceUsage.memory": req("string"),
    "status.resourceUsage.storage": req("string"),
    "status.resourceUsage.gpu": opt("integer", **NON_NEGATIVE),
    "status.resourceUsage.tpu": opt("integer", **NON_NEGATIVE),
    "status.resourceUsage.accelerators": opt("integer", **NON_NEGATIVE),
}

# --- device rules (device.js) --------------------------------------------------------------------

URI = {"pattern": re.compile(r"^[a-z][a-z0-9+.-]*://\S+$", re.I), "hint": 'a URI, e.g. "https://example.com/app.apk"'}
HEX = {"pattern": re.compile(r"^0x[0-9a-fA-F]+$"), "hint": 'a hex value, e.g. "0x10000"'}
TIME_UNITS = ("ms", "s")
SIZE_UNITS = ("KiB", "MiB", "GiB", "TiB")

DEVICE_RULES: dict[str, Rule] = {
    "apiVersion": req("string", enum=("hyper.ai/v1",)),
    "kind": req("string", enum=("Application",)),
    "metadata.name": req("string"),
    "metadata.annotations": opt("object", values="string"),
    "spec.device_name": opt("string"),
    "spec.device_uuid": opt("string"),
    "spec.app.type": req("string", enum=("device",)),
    "spec.app.schemaVersion": req("string", **SEMVER),
    "spec.app.name": req("string"),
    "spec.app.version": req("string"),
    "spec.app.owner": req("string"),
    "spec.app.lifecyclePhase": req("string", enum=LIFECYCLE),
    "spec.app.description": opt("string"),
    "spec.app.parentApp.name": opt("string"),
    "spec.app.parentApp.uid": opt("string"),
    "spec.workload.kind": req("string", enum=("AndroidApk", "DockerImage", "esp32Binary")),
    "spec.workload.androidApk": opt("object"),
    "spec.workload.androidApk.apkUrl": req("string", **URI),
    "spec.workload.androidApk.packageName": req("string"),
    "spec.workload.androidApk.sha256": opt("string"),
    "spec.workload.androidApk.installMode": opt("string", enum=("install", "update")),
    "spec.workload.androidApk.launch.activity": opt("string"),
    "spec.workload.androidApk.launch.action": opt("string"),
    "spec.workload.androidApk.launch.category": opt("string"),
    "spec.workload.dockerImage": opt("object"),
    "spec.workload.dockerImage.image": req("string"),
    "spec.workload.dockerImage.imagePullPolicy": opt("string", enum=("Always", "IfNotPresent", "Never")),
    "spec.workload.dockerImage.imagePullSecretRef": opt("string"),
    "spec.workload.esp32Binary": opt("object"),
    "spec.workload.esp32Binary.binaryUrl": req("string", **URI),
    "spec.workload.esp32Binary.chip": req("string", enum=("esp32", "esp32s2", "esp32s3", "esp32c3", "esp32c6",
                                                          "esp32h2")),
    "spec.workload.esp32Binary.flash.method": req("string", enum=("serial", "ota")),
    "spec.workload.esp32Binary.sha256": opt("string"),
    "spec.workload.esp32Binary.flash.port": opt("string"),
    "spec.workload.esp32Binary.flash.baudRate": opt("integer", check=lambda v: v >= 1200,
                                                    hint="an integer ≥ 1200, e.g. 115200"),
    "spec.workload.esp32Binary.flash.offset": opt("string", **HEX),
    "spec.workload.esp32Binary.flash.partition": opt("string"),
    "spec.workload.esp32Binary.flash.eraseFlash": opt("boolean"),
    "spec.exec.parameters": opt("object", values="string"),
    "spec.exec.command": opt("list", items="string"),
    "spec.exec.env": opt("object", values="string"),
    "spec.exec.workingDir": opt("string"),
    "spec.resources.cpu.value": opt("number"),
    "spec.resources.cpu.unit": opt("string", enum=("cores", "millicores")),
    "spec.resources.memory.value": opt("number"),
    "spec.resources.memory.unit": opt("string", enum=SIZE_UNITS),
    "spec.resources.storage.value": opt("number"),
    "spec.resources.storage.unit": opt("string", enum=SIZE_UNITS),
    "spec.resources.gpu": opt("integer", **NON_NEGATIVE),
    "spec.resources.tpu": opt("integer", **NON_NEGATIVE),
    "spec.resources.accelerators": opt("list", items="string"),
    "spec.network.ports[].port": req("integer", **PORT),
    "spec.network.ports[].protocol": req("string"),
    "spec.network.networkBandwidthMin.value": req("number"),
    "spec.network.networkBandwidthMin.unit": req("string", enum=("bps", "Kbps", "Mbps", "Gbps")),
    "spec.qos.latencyToleranceMax.value": req("number"),
    "spec.qos.latencyToleranceMax.unit": req("string", enum=TIME_UNITS),
    "spec.qos.energyCost.value": req("number"),
    "spec.qos.energyCost.unit": req("string", enum=("mW", "W")),
    "spec.qos.monetaryCost.value": req("number"),
    "spec.qos.monetaryCost.currency": req("string"),
    "spec.qos.monetaryCost.per": req("string", enum=("second", "minute", "hour", "day")),
    "spec.qos.resilience": req("string"),
    "spec.qos.availability.value": req("number", check=lambda v: 0 <= v <= 1, hint="a number from 0 to 1, e.g. 0.95"),
    "spec.qos.availability.unit": req("string", enum=("fraction",)),
    "spec.qos.startupTime.value": req("number"),
    "spec.qos.startupTime.unit": req("string", enum=TIME_UNITS),
    "spec.constraints.schedulingPriority": req("integer"),
    "spec.constraints.supportedArchitectures": req("list", items="string"),
    "spec.constraints.geoLocationRequirement": req("string"),
    "spec.constraints.isHighlyAvailable": req("boolean"),
    "spec.constraints.faultTolerance": req("string"),
    "spec.constraints.dataClassification": req("string"),
    "spec.constraints.trustScore": opt("number", check=lambda v: v >= 0, hint="a number ≥ 0"),
    "spec.constraints.batteryLevelMin": opt("integer", check=lambda v: 0 <= v <= 100,
                                            hint="an integer from 0 to 100"),
    "spec.constraints.securityLevel": opt("string"),
    "spec.sensors": opt("object"),
    "spec.sensors.sensorType": req("string"),
    "spec.sensors.isActive": req("boolean"),
    "spec.sensors.taskStatus": req("string", enum=("IDLE", "RUNNING", "SCHEDULED")),
    "spec.sensors.sensorIDs": opt("list", items="string"),
    "spec.sensors.platformInfo": opt("string"),
    "spec.runtime.baseOS.name": opt("string"),
    "spec.runtime.baseOS.version": opt("string"),
    "spec.runtime.acceleratorRuntime[].name": opt("string"),
    "spec.runtime.hypervisor": opt("string"),
    "spec.logs_url": opt("string", **URI),
    "spec.metrics_url": opt("string", **URI),
    "spec.config": opt("object", open=True),
    "status": opt("object"),
    "status.phase": opt("string", enum=("pending", "scheduled", "deployed", "failed", "removed")),
}

WORKLOAD_BLOCKS = {"AndroidApk": "androidApk", "DockerImage": "dockerImage", "esp32Binary": "esp32Binary"}

_validate_native = create_validator(NATIVE_RULES)
_validate_device_rules = create_validator(DEVICE_RULES)


def _check_workload_block(root: Any, root_path: str) -> list[Finding]:
    spec = root.get("spec") if isinstance(root, dict) else None
    workload = spec.get("workload") if isinstance(spec, dict) else None
    kind = workload.get("kind") if isinstance(workload, dict) else None
    block = WORKLOAD_BLOCKS.get(kind) if isinstance(kind, str) else None
    if not isinstance(workload, dict) or not block:
        return []

    def at(key: str) -> str:
        return ".".join(p for p in (root_path, "spec.workload", key) if p)

    errors = []
    if workload.get(block) is None:
        errors.append(Finding(at(block), f"is required when workload.kind is {kind}"))
    for other in WORKLOAD_BLOCKS.values():
        if other != block and workload.get(other) is not None:
            errors.append(Finding(at(other), f"must not be set when workload.kind is {kind}", "key"))
    return errors


def _validate_device(root: Any, root_path: str) -> tuple[list[Finding], list[Finding]]:
    errors, warnings = _validate_device_rules(root, root_path)
    return errors + _check_workload_block(root, root_path), warnings


# --- validateProfile (index.js), without line positions ---------------------------------------------


@dataclass
class Report:
    type: str | None
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {"type": self.type, "valid": self.valid,
                "errors": [{"field": e.path, "message": e.message} for e in self.errors],
                "warnings": [{"field": w.path, "message": w.message} for w in self.warnings]}


def validate_profile(content: str) -> Report:
    try:
        data = load_yaml(content)
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML: {exc}"
        return Report(None, [Finding("", msg)], parse_error=msg)
    if isinstance(data, dict) and "applicationProfile" in data:
        root = data["applicationProfile"]
        if not is_plain_object(root):
            return Report("native", [Finding("applicationProfile", "must be an object")])
        extra = [Finding(str(k), "unknown field, not part of the schema", "key") for k in data
                 if k != "applicationProfile"]
        errors, warnings = _validate_native(root, "applicationProfile")
        return Report("native", errors, extra + warnings)
    if isinstance(data, dict) and ("apiVersion" in data or "kind" in data):
        errors, warnings = _validate_device(data, "")
        return Report("device", errors, warnings)
    return Report(None, [Finding("", 'unrecognised profile, expected "applicationProfile" (native app) or '
                                     '"apiVersion"/"kind" (device app) at the root')])
