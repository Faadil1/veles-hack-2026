"""Local checks for HYPER-AI application profiles.

Errors and warnings come from steward.hyperai_schema, a line-for-line port of the IDE backend's own validator
(validation/native.js, device.js, schema.js from donmichael/ide-backend). A differential test against the real
JavaScript validator keeps the two in agreement (evaluation/validator_parity.py). So a profile that passes here
passes in the IDE, and the messages are the ones the IDE shows. Steward adds a few INFO advisories on top
(platform-managed fields, deprecated fields); they never block.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import yaml

from . import hyperai_schema


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
    rule: str = "ide-validator"

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


def parse_profile(text: str) -> tuple[Any, str | None]:
    try:
        return hyperai_schema.load_yaml(text), None
    except yaml.YAMLError as exc:
        return None, f"Invalid YAML: {exc}"


def detect_kind(doc: Any) -> ProfileKind:
    if isinstance(doc, dict):
        if "applicationProfile" in doc:
            return ProfileKind.NATIVE
        if "apiVersion" in doc or "kind" in doc:
            return ProfileKind.DEVICE
    return ProfileKind.UNKNOWN


def check_profile(text: str) -> SpecReport:
    report = hyperai_schema.validate_profile(text)
    kind = ProfileKind(report.type) if report.type else ProfileKind.UNKNOWN
    if report.parse_error:
        return SpecReport(kind, (), parse_error=report.parse_error)
    issues = [Issue(e.path or "<root>", e.message, Severity.ERROR) for e in report.errors]
    issues += [Issue(w.path, w.message, Severity.WARNING) for w in report.warnings]
    doc, _ = parse_profile(text)
    issues += _advisories(kind, doc)
    return SpecReport(kind, tuple(issues))


def _advisories(kind: ProfileKind, doc: Any) -> list[Issue]:
    """Steward-only notes from the DSL reference pages. Never errors: the IDE validator is the authority."""
    out: list[Issue] = []
    if kind is ProfileKind.NATIVE and isinstance(doc.get("applicationProfile"), dict):
        root = doc["applicationProfile"]
        if "status" in root:
            out.append(Issue("applicationProfile.status", "is runtime state maintained by the platform; "
                             "usually not authored by hand", Severity.INFO, "steward-advice"))
        qos = (root.get("specs") or {}).get("qos") if isinstance(root.get("specs"), dict) else None
        if isinstance(qos, dict) and "resilience" in qos:
            out.append(Issue("applicationProfile.specs.qos.resilience", "is redundant with "
                             "constraints.faultTolerance in the DSL reference; prefer faultTolerance",
                             Severity.INFO, "steward-advice"))
    if kind is ProfileKind.DEVICE and isinstance(doc, dict):
        if "status" in doc:
            out.append(Issue("status", "is platform-managed; usually not authored by hand", Severity.INFO,
                             "steward-advice"))
        spec = doc.get("spec")
        if isinstance(spec, dict) and "device_uuid" in spec:
            out.append(Issue("spec.device_uuid", "is normally assigned by the platform", Severity.INFO,
                             "steward-advice"))
    return out
