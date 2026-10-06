"""Runnability checks: will this profile actually run, beyond being schema-valid?

The HYPER-AI validator checks structure. It cannot know that an nginx image has no `uvicorn`, or that a
port the process listens on is never exposed. These rules encode that kind of cross-field knowledge.
Each finding states the evidence it rests on; rules never claim certainty they do not have.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .spec import ProfileKind, detect_kind, parse_profile


class Verdict(StrEnum):
    WILL_NOT_RUN = "will_not_run"
    AT_RISK = "at_risk"
    NO_KNOWN_BLOCKER = "no_known_blocker"
    NOT_ASSESSED = "not_assessed"


@dataclass(frozen=True)
class Finding:
    rule: str
    level: str  # "blocker" | "risk" | "note"
    message: str
    fix: str

    def as_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "level": self.level, "message": self.message, "fix": self.fix}


@dataclass(frozen=True)
class RunnabilityReport:
    verdict: Verdict
    findings: tuple[Finding, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict.value, "findings": [f.as_dict() for f in self.findings]}


# Images that do not ship a Python runtime. Running a Python entry point inside them fails at start.
NON_PYTHON_IMAGES = {
    "nginx", "httpd", "caddy", "traefik", "haproxy", "redis", "postgres", "mysql", "mariadb", "mongo",
    "memcached", "rabbitmq", "busybox", "hello-world", "alpine", "envoyproxy/envoy",
}
PYTHON_ENTRYPOINTS = {"uvicorn", "gunicorn", "python", "python3", "flask", "fastapi", "hypercorn", "daphne", "pip"}
NODE_ENTRYPOINTS = {"node", "npm", "npx", "yarn", "pnpm"}
NODE_FREE_IMAGES = NON_PYTHON_IMAGES | {"python"}
PRIVATE_DATA = {"private", "confidential", "restricted", "secret"}
NATIVE_ARCH = {"x86_64", "arm64", "aarch64", "armv7"}
DEVICE_ARCH = {"amd64", "arm64", "arm64-v8a", "armeabi-v7a", "x86", "x86_64", "esp32"}


def _image_name(ref: str) -> str:
    """'docker.io/library/nginx:1.27' -> 'nginx'; 'ghcr.io/acme/app:1' -> 'ghcr.io/acme/app'."""
    ref = ref.split("@", 1)[0]
    last = ref.rsplit("/", 1)[-1]
    if ":" in last:
        ref = ref[: len(ref) - len(last)] + last.split(":", 1)[0]
    for prefix in ("docker.io/library/", "docker.io/", "library/"):
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
    return ref


def _first_word(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip().split(" ")[0].rsplit("/", 1)[-1]


def _listen_port(args: list[Any]) -> int | None:
    text = " ".join(str(a) for a in args)
    match = re.search(r"--port[ =](\d+)", text) or re.search(r"--bind[ =][^ :]*:(\d+)", text)
    return int(match.group(1)) if match else None


def assess(text: str) -> RunnabilityReport:
    doc, err = parse_profile(text)
    if err or not isinstance(doc, dict):
        return RunnabilityReport(Verdict.NOT_ASSESSED, ())
    kind = detect_kind(doc)
    findings: list[Finding] = []
    if kind is ProfileKind.NATIVE:
        findings = _native(doc.get("applicationProfile") or {})
    elif kind is ProfileKind.DEVICE:
        findings = _device(doc)
    else:
        return RunnabilityReport(Verdict.NOT_ASSESSED, ())
    if any(f.level == "blocker" for f in findings):
        verdict = Verdict.WILL_NOT_RUN
    elif any(f.level == "risk" for f in findings):
        verdict = Verdict.AT_RISK
    else:
        verdict = Verdict.NO_KNOWN_BLOCKER
    return RunnabilityReport(verdict, tuple(findings))


def _get(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _entrypoint_vs_image(entry: str, image: str, where: str) -> list[Finding]:
    out: list[Finding] = []
    name = _image_name(image)
    if entry in PYTHON_ENTRYPOINTS and name in NON_PYTHON_IMAGES:
        out.append(Finding(
            "entrypoint-image-mismatch", "blocker",
            f"{where}: entry point `{entry}` needs a Python runtime, but image `{image}` does not ship one. "
            "The container will fail at start.",
            f"Use an image that contains your app and `{entry}` (e.g. your own image built FROM python:3.x-slim), "
            f"or change the entry point to what `{name}` actually runs.",
        ))
    if entry in NODE_ENTRYPOINTS and name in NODE_FREE_IMAGES:
        out.append(Finding(
            "entrypoint-image-mismatch", "blocker",
            f"{where}: entry point `{entry}` needs Node.js, which image `{image}` does not ship.",
            "Use an image that contains Node.js and your app.",
        ))
    return out


def _native(root: dict) -> list[Finding]:
    out: list[Finding] = []
    runtime = _get(root, "specs", "runtime") or {}
    image_uri = str(_get(runtime, "containerImage", "uri") or "")
    image_tag = str(_get(runtime, "containerImage", "tag") or "")
    entry = _first_word(runtime.get("entryPoint"))
    if image_uri and entry:
        out += _entrypoint_vs_image(entry, image_uri, "specs.runtime")

    base = str(_get(runtime, "baseOS", "name") or "").lower()
    if base and image_uri and base in {"python"} and _image_name(image_uri) in NON_PYTHON_IMAGES:
        out.append(Finding(
            "baseos-image-mismatch", "risk",
            f"specs.runtime.baseOS says `{base}` but the container image is `{image_uri}`. One of them is wrong.",
            "Make baseOS describe the image you actually run.",
        ))

    phase = _get(root, "metadata", "lifecyclePhase")
    if image_tag == "latest" and phase == "production":
        out.append(Finding(
            "mutable-tag-in-production", "risk",
            "A production profile pins the image to `latest`; redeploys can silently change what runs.",
            "Pin an immutable version tag or digest.",
        ))

    ports = _get(root, "specs", "network", "ports") or []
    exposed = {p.get("port") for p in ports if isinstance(p, dict)}
    listen = _listen_port(runtime.get("args") or [])
    if listen is not None and exposed and listen not in exposed:
        out.append(Finding(
            "listen-port-not-exposed", "blocker",
            f"The process listens on port {listen} (from runtime.args) but network.ports exposes {sorted(exposed)}.",
            f"Expose port {listen}, or change the --port argument.",
        ))
    if listen is not None and not exposed:
        out.append(Finding(
            "listen-port-not-exposed", "risk",
            f"The process listens on port {listen} but no network.ports are declared.",
            f"Add a network.ports entry for {listen}.",
        ))

    constraints = _get(root, "specs", "constraints") or {}
    public = any(isinstance(p, dict) and p.get("publicExposure") is True for p in ports)
    data_class = str(constraints.get("dataClassification") or "").lower()
    if public and data_class in PRIVATE_DATA:
        out.append(Finding(
            "public-exposure-of-private-data", "risk",
            f"A port is publicly exposed while dataClassification is `{data_class}`.",
            "Confirm the exposure is intended, or set publicExposure: false.",
        ))

    availability = str(_get(root, "specs", "qos", "availability") or "").rstrip("%").strip()
    if constraints.get("isHighlyAvailable") is False and availability:
        try:
            if float(availability) >= 99.9:
                out.append(Finding(
                    "availability-without-ha", "risk",
                    f"QoS asks for {availability}% availability but isHighlyAvailable is false.",
                    "Enable isHighlyAvailable or lower the availability target.",
                ))
        except ValueError:
            pass

    for arch in constraints.get("supportedArchitectures") or []:
        if isinstance(arch, str) and arch not in NATIVE_ARCH:
            out.append(Finding(
                "architecture-vocabulary", "note",
                f"Architecture `{arch}` is not in the native examples' vocabulary ({sorted(NATIVE_ARCH)}); "
                "the scheduler may not match it.",
                "Use x86_64 or arm64 for native apps.",
            ))
    return out


def _device(doc: dict) -> list[Finding]:
    out: list[Finding] = []
    spec = doc.get("spec") or {}
    workload = spec.get("workload") or {}
    kind = workload.get("kind")
    archs = [a for a in (_get(spec, "constraints", "supportedArchitectures") or []) if isinstance(a, str)]

    if kind == "DockerImage":
        image = str(_get(workload, "dockerImage", "image") or "")
        command = _get(spec, "exec", "command")
        if image and command:
            out += _entrypoint_vs_image(_first_word(command), image, "spec.exec.command")
        if image and "/" in image.split(":")[0] and "." in image.split("/")[0] \
                and not _get(workload, "dockerImage", "imagePullSecretRef") \
                and not image.startswith(("docker.io/", "registry.hub.docker.com/")):
            out.append(Finding(
                "registry-whitelist", "risk",
                f"Image `{image}` is not on Docker Hub. The HYPER-AI quick start requires a public, "
                "whitelisted registry such as Docker Hub.",
                "Push the image to Docker Hub, or confirm the registry is whitelisted (or add imagePullSecretRef).",
            ))
        if image.endswith(":latest") or (":" not in image.rsplit("/", 1)[-1] and image):
            if _get(spec, "app", "lifecyclePhase") == "production":
                out.append(Finding("mutable-tag-in-production", "risk",
                                   f"Production device app uses a mutable image reference `{image}`.",
                                   "Pin a version tag or digest."))
        if any(a in {"arm64-v8a", "armeabi-v7a", "esp32"} for a in archs):
            out.append(Finding("architecture-workload-mismatch", "risk",
                               f"A Docker workload lists {archs}; Android/ESP32 ABIs cannot run containers.",
                               "Use amd64/arm64 for Docker workloads."))

    if kind == "AndroidApk":
        if not spec.get("device_name"):
            out.append(Finding(
                "android-device-name", "risk",
                "Android APK apps are targeted at a registered Android DeviceNode by name (official cookbook); "
                "device_name is missing.",
                "Set spec.device_name to a registered Android device.",
            ))
        if archs and not any(a.startswith(("arm", "x86")) for a in archs):
            out.append(Finding("architecture-workload-mismatch", "risk",
                               f"Android workload with architectures {archs}.", "Use an Android ABI such as arm64-v8a."))

    if kind == "esp32Binary":
        chip = _get(workload, "esp32Binary", "chip")
        flash = _get(workload, "esp32Binary", "flash") or {}
        if flash.get("method") == "serial" and not flash.get("port"):
            out.append(Finding("esp32-serial-port", "risk",
                               "Serial flashing without flash.port; the agent on the device must guess the port.",
                               "Set flash.port (e.g. /dev/ttyUSB0) or use method: ota."))
        if archs and chip and not any(a.startswith("esp32") for a in archs):
            out.append(Finding("architecture-workload-mismatch", "risk",
                               f"ESP32 firmware ({chip}) with architectures {archs}.", f"List `{chip}` as the architecture."))

    qos = spec.get("qos") or {}
    availability = _get(qos, "availability", "value")
    if isinstance(availability, (int, float)) and availability >= 0.999 \
            and _get(spec, "constraints", "isHighlyAvailable") is False:
        out.append(Finding("availability-without-ha", "risk",
                           f"QoS availability {availability} with isHighlyAvailable: false.",
                           "Enable isHighlyAvailable or lower availability."))
    battery = _get(spec, "constraints", "batteryLevelMin")
    if isinstance(battery, int) and battery > 90:
        out.append(Finding("battery-threshold", "note",
                           f"batteryLevelMin {battery} excludes most battery devices most of the time.",
                           "Lower the threshold unless this is intended."))
    return out
